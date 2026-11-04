"""Grade each personal pledge (選挙公報の公約) on 4 checks with Gemini, from the quote text only.

Usage: ~/anyagents/.venv/bin/python -I score_pledges.py DATA_DIR/pledges_personal.json OUT_JSONL --budget-usd N [--workers 4]
Checks (true/false each, 1 point each, 4 points max -> 「公約の具体性」 = mean points / 4 x 100 per member):
  t  何を     : the target is clear (who / what field / which system)
  a  どうする : a concrete action is written (not just a value or a slogan)
  dl いつまでに: a deadline or time frame is written
  ms どこまで : a number or a condition that tells whether it was achieved
Output: one JSON row per unique quote: {"q": quote, "t":bool, "a":bool, "dl":bool, "ms":bool}. Resumable (skips quotes already in OUT).
Auth / project / model are the same as extract_pledges.py (personal GCP politics-os-2026, gcloud account $POS_GCS_ACCOUNT).
"""
import argparse
import os
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials

MODEL = "gemini-3-flash-preview"
PRICE_IN, PRICE_OUT = 0.50, 3.00  # USD per 1M tokens (same list price as extract_pledges.py)
ACCOUNT_ARGS = [f"--account={os.environ['POS_GCS_ACCOUNT']}"] if os.environ.get("POS_GCS_ACCOUNT") else []  # gcloud account (default: the active one)
BATCH = 50

PROMPT = """次は日本の国会議員が選挙公報に書いた公約の原文です（番号つき）。1件ずつ、書かれている文字だけで次の4つを判定してください。推測で補わない。
- t（何を）：対象がはっきりしている。制度・税・施設・人の集団など、何についての約束かが特定できる。「経済の再生」「日本を守る」のような大きな言葉だけなら false。
- a（どうする）：具体的な行動が書いてある（創設・廃止・引き下げ・無償化・法改正・建設など）。「推進」「充実」「強化」「取り組む」「目指す」だけなら false。
- dl（いつまでに）：期限・時期が書いてある（「2027年度までに」「任期中に」「5年以内」など）。
- ms（どこまで）：達成したか確かめられる数値や条件が書いてある（「時給1500円」「5%に」「ゼロに」「無償化」「廃止」など、達成かどうかが判定できるもの）。
返す配列は入力と同じ件数・同じ順番で、各要素に i（入力の番号）を入れてください。"""

S = types.Schema
SCHEMA = S(type="OBJECT", properties={"items": S(type="ARRAY", items=S(type="OBJECT", properties={
    "i": S(type="INTEGER"), "t": S(type="BOOLEAN"), "a": S(type="BOOLEAN"), "dl": S(type="BOOLEAN"), "ms": S(type="BOOLEAN")},
    required=["i", "t", "a", "dl", "ms"]))}, required=["items"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pledges")
    ap.add_argument("out")
    ap.add_argument("--budget-usd", type=float, required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    d = json.loads(Path(a.pledges).read_text(encoding="utf-8"))
    quotes = sorted({i["q"] for v in d.values() for i in v["items"] if i["k"] == "公約"})
    out = Path(a.out)
    done = {json.loads(l)["q"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    todo = [q for q in quotes if q not in done]
    print(f"quotes {len(quotes)} / done {len(done)} / todo {len(todo)}", flush=True)
    lock = threading.Lock()
    auth = {"client": None, "at": 0.0}
    spent = {"usd": 0.0}

    def client():
        with lock:
            if time.time() - auth["at"] > 10 * 60:
                tok = subprocess.run(["gcloud", "auth", "print-access-token", *ACCOUNT_ARGS], capture_output=True, text=True, check=True).stdout.strip()
                auth["client"] = genai.Client(vertexai=True, project="politics-os-2026", location="global", credentials=Credentials(tok),
                                              http_options=types.HttpOptions(timeout=180_000))
                auth["at"] = time.time()
            return auth["client"]

    def run(batch):
        with lock:
            if spent["usd"] >= a.budget_usd:
                return
        text = PROMPT + "\n\n" + "\n".join(f"{n}. {q}" for n, q in enumerate(batch))
        cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=SCHEMA, temperature=0.0,
                                          thinking_config=types.ThinkingConfig(thinking_level="low"))
        for attempt in range(4):
            try:
                r = client().models.generate_content(model=MODEL, contents=text, config=cfg)
                res = json.loads(r.text)["items"]
                got = {x["i"]: x for x in res if isinstance(x.get("i"), int) and 0 <= x["i"] < len(batch)}
                if len(got) != len(batch):
                    raise ValueError(f"returned {len(got)}/{len(batch)}")
                u = r.usage_metadata
                cost = (u.prompt_token_count or 0) / 1e6 * PRICE_IN + ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) / 1e6 * PRICE_OUT
                with lock:
                    spent["usd"] += cost
                    with out.open("a", encoding="utf-8") as f:
                        for n, q in enumerate(batch):
                            x = got[n]
                            f.write(json.dumps({"q": q, "t": x["t"], "a": x["a"], "dl": x["dl"], "ms": x["ms"]}, ensure_ascii=False) + "\n")
                    print(f"+{len(batch)} cost ${cost:.4f} total ${spent['usd']:.3f}", flush=True)
                return
            except Exception as e:  # noqa: BLE001 - retry any API / parse error, then give up on this batch
                print(f"retry {attempt + 1}: {e}", flush=True)
                time.sleep(2 * (attempt + 1))

    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(run, batches))
    n = len(out.read_text(encoding="utf-8").splitlines()) if out.exists() else 0
    print(f"done: {n}/{len(quotes)} graded, spent ${spent['usd']:.3f}")


if __name__ == "__main__":
    main()
