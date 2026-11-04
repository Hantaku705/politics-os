"""How people on X talk about Diet members (positive / neutral / negative), via Grok x_search. Reference only.

Usage: ~/anyagents/.venv/bin/python fetch_x_reactions.py MEMBERS_JSON OUT_JSONL FROM UNTIL [--model grok-4.3] (--ids s123,c456 | --top-action N)
- One x_search conversation per member; results appended to OUT_JSONL (resumable: ids already in OUT_JSONL are skipped).
- Only themes are kept (no post text). Example post links are later filtered to IDs present in the search citations.
- Cost guide (2026-11-02): ~15k tokens + 2-3 searches per member (about $0.1). Ask for approval before large runs.
Env: XAI_API_KEY.
"""
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
import json
import os
import time
from datetime import datetime
from pathlib import Path

from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import x_search

SYS = """あなたは日本の政治に関するSNS調査の分析者です。x_search ツールで、指定期間のX（旧Twitter）の実際の投稿を検索して答えます。
規則：
- 対象は「その議員について他の人が書いた投稿」。本人のアカウントの投稿、ボットや自動投稿、同一文面の繰り返し、広告は除外する。
- 実際に検索で確認できた投稿だけを根拠にする。確認できない数字や投稿は作らない。件数は「確認した投稿の数」であり、全体の推計ではない。
- 侮辱・差別・中傷の言葉は引用しない。「人格への批判」「容姿への言及」など話題として要約する。
- 政治的な立場で評価を偏らせない。賛否どちらの投稿も同じ基準で分類する。
- 出力は指定のJSONのみ（前後に文章を付けない）。"""
SCHEMA = """{
 "member": "氏名",
 "posts_reviewed": 確認した投稿の数(整数),
 "own_account": "本人のXアカウント（確認できた場合のみ。なければnull）",
 "positive": [{"theme": "話題（30字以内）", "count": 確認件数, "example_urls": ["https://x.com/..."]}],
 "neutral":  [{"theme": "...", "count": n, "example_urls": ["..."]}],
 "negative": [{"theme": "...", "count": n, "example_urls": ["..."]}],
 "main_topics": ["期間中によく話題になった出来事・政策（最大5）"],
 "caveats": ["偏り・組織的投稿・同姓同名など分析上の注意（最大3）"]
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("members")
    ap.add_argument("out")
    ap.add_argument("frm")
    ap.add_argument("until")
    ap.add_argument("--model", default="grok-4.3")
    ap.add_argument("--ids")
    ap.add_argument("--top-action", type=int)
    ap.add_argument("--ids-file", help="file with one member id per line (processing order = file order)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--budget-usd", type=float, required=True, help="stop starting new members once actual spend reaches this")
    a = ap.parse_args()
    M = json.loads(Path(a.members).read_text(encoding="utf-8"))
    by_id = {m["id"]: m for m in M}
    if a.ids_file:
        targets = [by_id[i] for i in Path(a.ids_file).read_text().split() if i in by_id]
    elif a.ids:
        want = set(a.ids.split(","))
        targets = [m for m in M if m["id"] in want]
    else:
        ok = [m for m in M if m.get("sp") and m["activityStatus"] != "homonym"]
        targets = sorted(ok, key=lambda m: -m["sp"]["meet"])[: a.top_action or 10]
    out = Path(a.out)
    done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    frm, until = datetime.fromisoformat(a.frm), datetime.fromisoformat(a.until)
    client = Client(api_key=os.environ["XAI_API_KEY"])
    lock = threading.Lock()
    spent = {"usd": 0.0, "n": 0, "stopped": False}

    def one(m):
        with lock:
            if spent["usd"] >= a.budget_usd:
                spent["stopped"] = True
                return
        meeting = (m.get("mainMeeting") or {}).get("name", "")
        q = (f"{m['house']}議員「{m['name']}」（{m['kaihaName']}、主な会議：{meeting}）について、{a.frm}〜{a.until}のXの投稿を検索し、"
             f"他の人の投稿をポジティブ／ニュートラル／ネガティブに分けて、それぞれの主な話題を根拠の投稿URLつきでまとめてください。"
             f"x_search ツールは1回だけ使ってください。同姓同名の別人の投稿は除外してください。次のJSON形式で答えてください：\n{SCHEMA}")
        t0 = time.time()
        chat = client.chat.create(model=a.model, tools=[x_search(from_date=frm, to_date=until)])
        chat.append(system(SYS))
        chat.append(user(q))
        try:
            resp = chat.sample()
        except Exception as e:  # noqa: BLE001
            print(m["name"], "ERROR", e, flush=True)
            return
        text = resp.content.strip()
        try:
            parsed = json.loads(text[text.find("{"): text.rfind("}") + 1])
        except Exception as e:  # noqa: BLE001
            parsed = {"parse_error": str(e)}
        usage = getattr(resp, "usage", None)
        cost = (getattr(usage, "cost_in_usd_ticks", 0) or 0) / 1e10  # API-reported actual cost (1 tick = 1e-10 USD)
        row = {"id": m["id"], "name": m["name"], "model": a.model, "from": a.frm, "until": a.until,
               "fetchedAt": datetime.now().isoformat(timespec="seconds"), "elapsed_s": round(time.time() - t0, 1),
               "result": parsed, "citations": list(getattr(resp, "citations", []) or []),
               "usage": {k: getattr(usage, k, None) for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens")} if usage else None,
               "cost_usd": round(cost, 6),
               "server_side_tool_usage": str(getattr(resp, "server_side_tool_usage", "")) or None}
        with lock:
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            spent["usd"] += cost
            spent["n"] += 1
            print(f'{spent["n"]:>4} {m["name"]} posts {parsed.get("posts_reviewed")} cost ${cost:.4f} total ${spent["usd"]:.2f}', flush=True)

    todo = [m for m in targets if m["id"] not in done]
    print(f"targets {len(targets)} todo {len(todo)} budget ${a.budget_usd}", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one, todo))
    print(f'done: {spent["n"]} members, actual spend ${spent["usd"]:.2f}', "(budget reached, stopped)" if spent["stopped"] else "", flush=True)

if __name__ == "__main__":
    main()
