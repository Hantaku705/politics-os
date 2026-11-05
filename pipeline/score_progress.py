"""② 進捗率: link each personal pledge (選挙公報の公約) to what the member actually did in the Diet after that election.

Stages per pledge (shown on the site; 3 = 効いた is not judged here):
  0 言った : the pledge exists, no related action found
  1 動いた : the member themself spoke/asked about it in the Diet, submitted a related bill, or a 質問主意書 about it
  2 通った : a related bill the member submitted (筆頭 or 共同, 衆法/参法) was enacted (成立)
Evidence window: from the member's election day (for speeches) / from the first Diet session after it (bills, 質問主意書).
  shu2026 (2026-02-08) -> 第221回〜, san2025 (2025-07-20) -> 第218回〜, san2022 (2022-07-10) -> 第209回〜. Until 2026-10-31.

Per member:
  A. Gemini: 1-2 search words per pledge (specific nouns; none if the pledge is too vague to search)
  B. 国会会議録検索API: speaker = the member, any = word, from = election day. Government (大臣など) and 議長 speeches are dropped.
  C. Candidates: the member's own bills (lead/co) and 質問主意書 in the window (from records.json)
  D. Gemini: judge each pledge with only that evidence -> stage, evidence ids, one short reason. Stage claims are re-checked in code:
     stage 2 must cite an enacted 衆法/参法 the member submitted; stage 1 must cite at least one existing evidence item.
Output: JSONL, one row per member (resumable: members already in OUT are skipped).
Usage: ~/anyagents/.venv/bin/python -I pipeline/score_progress.py DATA_DIR OUT_JSONL --budget-usd N [--workers 4] [--ids s001,c7010001]
  DATA_DIR must contain members.json, records.json, pledges_personal.json (e.g. a pull.sh work dir's data/).
Auth: Vertex AI (personal GCP politics-os-2026) with gcloud account $POS_GCS_ACCOUNT (or the active one).
"""
import argparse, json, os, re, subprocess, threading, time, unicodedata, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials

MODEL = "gemini-3-flash-preview"
PRICE_IN, PRICE_OUT = 0.50, 3.00  # USD per 1M tokens (same as score_pledges.py)
ACCOUNT_ARGS = [f"--account={os.environ['POS_GCS_ACCOUNT']}"] if os.environ.get("POS_GCS_ACCOUNT") else []
UNTIL = "2026-10-31"
FIRST_SESSION = {"shu2026": 221, "san2025": 218, "san2022": 209}
KOKKAI = "https://kokkai.ndl.go.jp/api/speech"
UA = {"User-Agent": "politics-os/0.1 (civic research; https://github.com/Hantaku705/politics-os)"}
GOV = re.compile(r"大臣|副大臣|大臣政務官|政務官|長官|副長官|補佐官|議長|副議長")
PER_WORD = 3      # speeches kept per search word
EXCERPT = 160     # characters on each side of the word

S = types.Schema
KW_SCHEMA = S(type="OBJECT", properties={"items": S(type="ARRAY", items=S(type="OBJECT", properties={
    "i": S(type="INTEGER"), "kw": S(type="ARRAY", items=S(type="STRING"))}, required=["i", "kw"]))}, required=["items"])
JUDGE_SCHEMA = S(type="OBJECT", properties={"items": S(type="ARRAY", items=S(type="OBJECT", properties={
    "i": S(type="INTEGER"), "stage": S(type="INTEGER"), "ev": S(type="ARRAY", items=S(type="STRING")), "why": S(type="STRING")},
    required=["i", "stage", "ev", "why"]))}, required=["items"])

KW_PROMPT = """次は国会議員が選挙公報に書いた公約です（番号つき）。それぞれについて、国会の会議録でこの議員の発言を探すための検索語を0〜2個返してください。
- 公約に出てくる具体的な名詞（道路名・制度名・税の名前・施設名・病名・地名＋事業など）を、そのままの表記で使う。
- 「経済」「日本」「地域」「推進」「安心」「未来」のような、どんな発言にも出る一般的な語は使わない。
- 具体的な名詞がなく、検索しても当たり外れが判断できない公約（スローガンだけのもの）は空の配列にする。
返す配列は入力と同じ件数・同じ順番で、各要素に i（入力の番号）を入れる。"""

JUDGE_PROMPT = """あなたは国会の記録を確かめる係です。国会議員が選挙で約束した公約ごとに、当選後にこの議員本人が国会で関係する行動をしたかを、下の「根拠の候補」だけで判定してください。推測で補わないこと。
段階（stage）:
- 0：根拠の候補に、この公約の中身に直接かかわる行動がない（言葉がたまたま出てくるだけ、あいさつや別の話題の中で触れただけは 0）
- 1：本人が、この公約の中身について国会で質問・意見を述べた（S）、関係する法案を出した（B）、関係する質問主意書を出した（Q）
- 2：本人が出した法案（B）のうち「成立」のものが、この公約の中身を直接実現する（法案の主な目的が、公約と同じ対象・同じ中身であること）
厳しく判定すること：
- 根拠は、公約と「同じ対象」について「同じ方向」のことを言っている場合だけ使う。同じ言葉が出てきても、対象や分野が違えば使わない（例：公約「AIの時代に対応した教育」に、選挙でのAI生成物を規制する法案は別の話なので 0）。
- 公約がスローガンだけで対象がはっきりしない場合（例：「みんなが豊かになる経済」「安心できる社会」）は、その目的そのものをはっきり掲げた質問や法案がない限り 0。財政や経済一般の質問をしただけでは 1 にしない。
- 政府の答弁を引き出しただけでなく、本人がその公約の中身を求めた・提案したことが読み取れること。
ev には判定に使った根拠のID（S3, B1, Q2 など）を最大3つ入れる。stage 0 なら空。
why には、判定の理由を40字以内の日本語で、です・ます調で書く（例：「名古屋三河道路の早期整備を国土交通委員会で求めました。」）。stage 0 なら「関係する質問や法案は見つかりませんでした。」とする。
返す配列は公約と同じ件数・同じ順番で、各要素に i（公約の番号）を入れる。"""


def gcloud_token():
    return subprocess.run(["gcloud", "auth", "print-access-token", *ACCOUNT_ARGS], capture_output=True, text=True, check=True).stdout.strip()


def kokkai(speaker, word, frm):
    word = re.sub(r"[%％\"'()（）\[\]{}<>＜＞=＝&＆|｜*＊?？!！^]", "", word).strip()  # the API rejects some symbols (400)
    if len(word) < 2:
        return 0, []
    q = {"speaker": speaker, "any": word, "from": frm, "until": UNTIL, "maximumRecords": "10", "recordPacking": "json"}
    url = KOKKAI + "?" + urllib.parse.urlencode(q)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 400:  # the word itself is not searchable: skip it, do not fail the member
                return 0, []
            if attempt == 4:
                raise RuntimeError(f"kokkai {word}: {e}")
            time.sleep(2 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                raise RuntimeError(f"kokkai {word}: {e}")
            time.sleep(2 * (attempt + 1))
    total = int(d.get("numberOfRecords") or 0)
    out = []
    for s in d.get("speechRecord") or []:
        if GOV.search(s.get("speakerPosition") or ""):
            continue
        text = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", s.get("speech") or ""))  # 会議録 writes ＡＩ／１５００ in full width
        k = text.find(unicodedata.normalize("NFKC", word))
        if k < 0:
            continue
        out.append({"date": s["date"], "meeting": f"{s['nameOfHouse']} {s['nameOfMeeting']}", "url": s["speechURL"],
                    "text": text[max(0, k - EXCERPT):k + len(word) + EXCERPT]})
        if len(out) >= PER_WORD:
            break
    return total, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out")
    ap.add_argument("--budget-usd", type=float, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    D = Path(a.data)
    members = {m["id"]: m for m in json.loads((D / "members.json").read_text(encoding="utf-8"))}
    rec = json.loads((D / "records.json").read_text(encoding="utf-8"))
    pp = json.loads((D / "pledges_personal.json").read_text(encoding="utf-8"))
    out = Path(a.out)
    done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    ids = [i for i in (a.ids.split(",") if a.ids else pp.keys()) if i in pp and i not in done and i in members]
    print(f"members with pledges {len(pp)} / done {len(done)} / todo {len(ids)}", flush=True)
    lock = threading.Lock()
    auth = {"client": None, "at": 0.0}
    spent = {"usd": 0.0}

    def client():
        with lock:
            if time.time() - auth["at"] > 10 * 60:
                auth["client"] = genai.Client(vertexai=True, project="politics-os-2026", location="global", credentials=Credentials(gcloud_token()),
                                              http_options=types.HttpOptions(timeout=180_000))
                auth["at"] = time.time()
            return auth["client"]

    def ask(prompt, schema, n):
        cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=0.0,
                                          thinking_config=types.ThinkingConfig(thinking_level="low"))
        for attempt in range(4):
            try:
                r = client().models.generate_content(model=MODEL, contents=prompt, config=cfg)
                got = {x["i"]: x for x in json.loads(r.text)["items"] if isinstance(x.get("i"), int) and 0 <= x["i"] < n}
                if len(got) != n:
                    raise ValueError(f"returned {len(got)}/{n}")
                u = r.usage_metadata
                cost = (u.prompt_token_count or 0) / 1e6 * PRICE_IN + ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) / 1e6 * PRICE_OUT
                return got, cost
            except Exception as e:  # noqa: BLE001
                print(f"  retry {attempt + 1}: {e}", flush=True)
                if "401" in str(e):
                    auth["at"] = 0.0
                time.sleep(2 * (attempt + 1))
        raise RuntimeError("gemini failed")

    def run(mid):
        with lock:
            if spent["usd"] >= a.budget_usd:
                return
        m, d = members[mid], pp[mid]
        items = [(n, x) for n, x in enumerate(d["items"]) if x.get("k") != "実績"]
        if not items:
            row = {"id": mid, "election": d["election"], "items": [], "cost": 0}
        else:
            try:
                first = FIRST_SESSION[d["election"]]
                # A. search words
                kw, c1 = ask(KW_PROMPT + "\n\n" + "\n".join(f"{i}. {x['q']}" for i, (_, x) in enumerate(items)), KW_SCHEMA, len(items))
                # B. speeches (skip members whose name is shared: the API cannot tell them apart)
                ev, per = [], {}
                if m.get("activityStatus") != "homonym":
                    cache = {}
                    for i in range(len(items)):
                        per[i] = []
                        for w in [w.strip() for w in kw[i]["kw"] if w.strip()][:2]:
                            if w not in cache:
                                cache[w] = kokkai(m["speakerQuery"], w, d["date"])
                            for s in cache[w][1]:
                                ev.append({"id": f"S{len(ev) + 1}", "t": "S", "w": w, **s})
                                per[i].append(ev[-1]["id"])
                # C. own bills / questions in the window
                r = rec["members"].get(mid, {})
                bill_ids = (r.get("b") or {}).get("lead", []) + (r.get("b") or {}).get("co", [])
                bills = [rec["bills"][j] for j in dict.fromkeys(bill_ids) if int(rec["bills"][j]["session"]) >= first]
                bl = [{"id": f"B{k + 1}", "t": "B", "title": b["title"], "status": b["status"], "kind": b["kind"], "url": b["url"], "session": b["session"]} for k, b in enumerate(bills)]
                qs = [rec["questions"][j] for j in (r.get("q") or []) if int(rec["questions"][j]["session"]) >= first]
                ql = [{"id": f"Q{k + 1}", "t": "Q", "title": q["title"], "url": q["url"], "session": q["session"]} for k, q in enumerate(qs)]
                byid = {e["id"]: e for e in ev + bl + ql}
                # D. judge (speeches are listed under the pledge they were searched for; bills/questions are shared)
                lines = [JUDGE_PROMPT, "", f"議員：{m['name']}（{m['house']}・{m['kaihaName']}）。当選した選挙：{d['electionName']}（{d['date']}）。", "", "■ 本人が出した法案（当選後）"]
                lines += [f"{b['id']} [{b['kind']}・{b['status']}] {b['title']}" for b in bl] or ["（なし）"]
                lines += ["", "■ 本人が出した質問主意書（当選後）"] + ([f"{q['id']} {q['title']}" for q in ql] or ["（なし）"])
                lines += ["", "■ 公約と、この議員の発言の候補（検索語を含む発言の抜粋）"]
                for i, (_, x) in enumerate(items):
                    lines.append(f"{i}. 公約：{x['q']}")
                    for sid in per.get(i, []):
                        s = byid[sid]
                        lines.append(f"   {sid} {s['date']} {s['meeting']}：…{s['text']}…")
                jd, c2 = ask("\n".join(lines), JUDGE_SCHEMA, len(items))
                out_items = []
                for i, (n, x) in enumerate(items):
                    j = jd[i]
                    cited = [e for e in j.get("ev", []) if e in byid][:3]
                    st = j["stage"] if j["stage"] in (0, 1, 2) else 0
                    if st == 2 and not any(byid[e]["t"] == "B" and byid[e]["status"] == "成立" and byid[e]["kind"] in ("衆法", "参法") for e in cited):
                        st = 1
                    if st >= 1 and not cited:
                        st = 0
                    evs = [{k: byid[e][k] for k in ("t", "url") } | ({"date": byid[e]["date"], "meeting": byid[e]["meeting"], "w": byid[e]["w"]} if byid[e]["t"] == "S" else {"title": byid[e]["title"], **({"status": byid[e]["status"]} if byid[e]["t"] == "B" else {})}) for e in cited] if st else []
                    out_items.append({"i": n, "q": x["q"], "kw": kw[i]["kw"][:2], "st": st, "ev": evs, "why": (j.get("why") or "")[:60] if st else ""})
                row = {"id": mid, "election": d["election"], "items": out_items, "nSpeechHits": len(ev), "nBills": len(bl), "nQuestions": len(ql), "cost": round(c1 + c2, 5)}
            except Exception as e:  # noqa: BLE001 - one member failing must not stop the run; it is retried on the next run
                print(f"FAIL {mid} {m['name']}: {e}", flush=True)
                return
        with lock:
            spent["usd"] += row["cost"]
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            act = sum(1 for x in row["items"] if x["st"] >= 1)
            print(f"{m['name']}: pledges {len(row['items'])} moved {act} cost ${row['cost']:.4f} total ${spent['usd']:.3f}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(run, ids))
    n = len(out.read_text(encoding="utf-8").splitlines()) if out.exists() else 0
    print(f"done: {n}/{len(pp)} members, spent ${spent['usd']:.3f}")


if __name__ == "__main__":
    main()
