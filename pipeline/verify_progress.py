"""Second, stricter check of ② 進捗率 "moved" judgments (stage >= 1) from score_progress.py.

Why: a 30-item human audit of the first pass found 60-73% precision for stage 1 (self-introductions, other topics,
slogan pledges matched to generic remarks). Each stage>=1 pledge is re-checked one by one with the full evidence text
(speech excerpts are fetched again from the 国会会議録検索API) and a more careful model setting.
A pledge keeps its stage only if at least one evidence item shows the member asking for / proposing / submitting
the specific content of the pledge (same target, same direction). Otherwise it becomes stage 0.
Usage: ~/anyagents/.venv/bin/python -I pipeline/verify_progress.py DATA_DIR IN_JSONL OUT_JSONL --budget-usd N [--workers 6]
Output has the same format as IN; each changed item gets "v": "downgraded" and kept items "v": "kept".
"""
import argparse, json, os, re, subprocess, threading, time, unicodedata, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials

MODEL = "gemini-3-flash-preview"
PRICE_IN, PRICE_OUT = 0.50, 3.00
ACCOUNT_ARGS = [f"--account={os.environ['POS_GCS_ACCOUNT']}"] if os.environ.get("POS_GCS_ACCOUNT") else []
UA = {"User-Agent": "politics-os/0.1 (civic research; https://github.com/Hantaku705/politics-os)"}
S = types.Schema
SCHEMA = S(type="OBJECT", properties={"keep": S(type="BOOLEAN"), "ev": S(type="ARRAY", items=S(type="INTEGER")), "why": S(type="STRING")},
           required=["keep", "ev", "why"])
PROMPT = """国会議員の選挙公約と、その議員本人の国会での行動の候補です。公約が「当選後に国会で動いた」と言えるかを厳しく判定してください。
keep = true にしてよいのは、候補のどれかが次のどれかに当たるときだけです：
- 本人が、公約と同じ対象について、同じ方向のこと（実現・拡充・導入・廃止など）を政府に求めた・問うた・提案した発言
- 本人が出した、公約の中身そのものを実現する法案、または公約の中身についての質問主意書
次のどれかなら keep = false：
- 自己紹介や「関心がある」「取り組んできた」と述べただけ。過去の経歴の紹介だけ
- 公約と別の話題の中で、言葉が出てきただけ（例：基礎控除の公約に、医療費の負担の話）
- 公約がスローガンだけ（「医療福祉」「持続可能な財政」「ふるさとの発展」など）で、候補もその分野の一般的な話にとどまる
- 公約が分野の名前だけで、どうするか（方向）が書いていない（例：「医療福祉」「外交・安全保障」「農林水産業」）。その分野のどんな発言でも当たってしまうため
- 公約と反対の方向の発言、政府の説明を聞いただけで本人の求めが読み取れない
ev には keep の根拠にした候補の番号（0から）を入れる。why は、です・ます調40字以内で、本人が何をしたかを具体的に書く（keep=false なら空文字）。"""


def tok():
    return subprocess.run(["gcloud", "auth", "print-access-token", *ACCOUNT_ARGS], capture_output=True, text=True, check=True).stdout.strip()


def excerpt(m, e):
    q = {"speaker": m["speakerQuery"], "any": e["w"], "from": e["date"], "until": e["date"], "maximumRecords": "10", "recordPacking": "json"}
    for attempt in range(4):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request("https://kokkai.ndl.go.jp/api/speech?" + urllib.parse.urlencode(q), headers=UA), timeout=60).read())
            break
        except urllib.error.HTTPError as ex:
            if ex.code == 400:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:  # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    else:
        return None
    for s in d.get("speechRecord") or []:
        if s["speechURL"] == e["url"]:
            t = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", s["speech"]))
            k = max(0, t.find(unicodedata.normalize("NFKC", e["w"])))
            return t[max(0, k - 400):k + 400]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--budget-usd", type=float, required=True); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    members = {m["id"]: m for m in json.loads((Path(a.data) / "members.json").read_text(encoding="utf-8"))}
    rows = {}
    for l in Path(a.inp).read_text(encoding="utf-8").splitlines():
        r = json.loads(l); rows[r["id"]] = r
    out = Path(a.out)
    done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    todo = [i for i in rows if i not in done]
    lock = threading.Lock(); auth = {"c": None, "at": 0.0}; spent = {"usd": 0.0}

    def client():
        with lock:
            if time.time() - auth["at"] > 600:
                auth["c"] = genai.Client(vertexai=True, project="politics-os-2026", location="global", credentials=Credentials(tok()),
                                         http_options=types.HttpOptions(timeout=180_000))
                auth["at"] = time.time()
            return auth["c"]

    def check(m, x):
        cands, lines = [], []
        for e in x["ev"]:
            if e["t"] == "S":
                t = excerpt(m, e)
                if t:
                    cands.append(e); lines.append(f"{len(cands) - 1}. 発言 {e['date']} {e['meeting']}：…{t}…")
            else:
                cands.append(e); lines.append(f"{len(cands) - 1}. {'法案' if e['t'] == 'B' else '質問主意書'}：{e['title']}{'（' + e['status'] + '）' if e.get('status') else ''}")
        if not cands:
            return {"keep": False, "ev": [], "why": ""}, 0.0, cands
        text = f"{PROMPT}\n\n議員：{m['name']}\n公約：{x['q']}\n\n候補：\n" + "\n".join(lines)
        cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=SCHEMA, temperature=0.0,
                                          thinking_config=types.ThinkingConfig(thinking_level="medium"))
        for attempt in range(4):
            try:
                r = client().models.generate_content(model=MODEL, contents=text, config=cfg)
                j = json.loads(r.text); u = r.usage_metadata
                cost = (u.prompt_token_count or 0) / 1e6 * PRICE_IN + ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) / 1e6 * PRICE_OUT
                return j, cost, cands
            except Exception as ex:  # noqa: BLE001
                if "401" in str(ex):
                    auth["at"] = 0.0
                time.sleep(2 * (attempt + 1))
        raise RuntimeError("gemini failed")

    def run(mid):
        with lock:
            if spent["usd"] >= a.budget_usd:
                return
        r, m, cost = rows[mid], members[mid], 0.0
        try:
            for x in r["items"]:
                if x["st"] < 1:
                    continue
                j, c, cands = check(m, x)
                cost += c
                keep = [cands[i] for i in j.get("ev", []) if isinstance(i, int) and 0 <= i < len(cands)]
                if j.get("keep") and keep:
                    if x["st"] == 2 and not any(e["t"] == "B" and e.get("status") == "成立" for e in keep):
                        x["st"] = 1
                    x["ev"], x["why"], x["v"] = keep[:3], (j.get("why") or x["why"])[:60], "kept"
                else:
                    x["st"], x["ev"], x["why"], x["v"] = 0, [], "", "downgraded"
        except Exception as ex:  # noqa: BLE001
            print(f"FAIL {mid} {m['name']}: {ex}", flush=True); return
        r["verifyCost"] = round(cost, 5)
        with lock:
            spent["usd"] += cost
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"{m['name']}: kept {sum(1 for x in r['items'] if x.get('v') == 'kept')} down {sum(1 for x in r['items'] if x.get('v') == 'downgraded')} ${cost:.4f} total ${spent['usd']:.3f}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(run, todo))
    print(f"done {len(out.read_text(encoding='utf-8').splitlines()) if out.exists() else 0}/{len(rows)} spent ${spent['usd']:.3f}")


if __name__ == "__main__":
    main()
