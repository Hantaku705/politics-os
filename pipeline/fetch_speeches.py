"""Collect per-member speech metadata from the Diet minutes API (kokkai.ndl.go.jp) for the detail view.

Usage: python3 -I fetch_speeches.py ACTIVITY_JSONL OUT_JSONL FROM UNTIL [SHARD NSHARDS]
- Uses the exact speaker names that fetch_activity.py matched (`matchedName`, "A|B" = alias sum).
- Keeps only records whose `speaker` equals the name exactly (the API filter is a partial match).
- Stores metadata only (date, house, meeting, issue, position, URL, 60-char snippet); full text is not kept.
- Resumable: members already in OUT_JSONL (or sibling speeches*.jsonl shards) are skipped.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://kokkai.ndl.go.jp/api/speech"
PAGE = 100
WAIT = 1.0


def call(params):
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "politics-os-research/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.load(r)
            time.sleep(WAIT)
            return data
        except Exception as e:  # network hiccup or rate limit
            last = e
            time.sleep(5 * (attempt + 1))
    raise last


def fetch(name, frm, until):
    out, start, total = [], 1, None
    while total is None or start <= total:
        d = call({"speaker": name, "from": frm, "until": until, "maximumRecords": PAGE,
                  "startRecord": start, "recordPacking": "json"})
        total = int(d.get("numberOfRecords") or 0)
        for r in d.get("speechRecord", []):
            if r.get("speaker") != name:
                continue
            body = (r.get("speech") or "").split("　", 1)[-1]  # drop the leading "○氏名君"
            out.append({"date": r.get("date"), "house": r.get("nameOfHouse"), "meeting": r.get("nameOfMeeting"),
                        "issue": r.get("issue"), "position": r.get("speakerPosition"), "url": r.get("speechURL"),
                        "snippet": " ".join(body.split())[:60]})
        start += PAGE
        if total == 0:
            break
    return out


def main():
    act, out = Path(sys.argv[1]), Path(sys.argv[2])
    frm, until = sys.argv[3], sys.argv[4]
    shard, nshards = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (0, 1)
    rows = {}
    for line in act.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["kind"] == "all":
            rows[(r["house"], r["profileId"])] = r
    todo = [r for i, r in enumerate(sorted(rows.values(), key=lambda r: (r["house"], r["profileId"]))) if i % nshards == shard]
    done = set()
    for f in out.parent.glob("speeches*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            x = json.loads(line)
            done.add((x["house"], x["profileId"]))
    with out.open("a", encoding="utf-8") as fh:
        for i, r in enumerate(todo, 1):
            key = (r["house"], r["profileId"])
            if key in done:
                continue
            recs = []
            if r["count"] > 0:
                for name in r["matchedName"].split("|"):
                    recs += fetch(name, frm, until)
            fh.write(json.dumps({"house": r["house"], "profileId": r["profileId"], "name": r["name"],
                                 "expected": r["count"], "records": recs}, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 20 == 0:
                print(f"{shard}: {i}/{len(todo)}", flush=True)
    print(f"{shard}: done", flush=True)


if __name__ == "__main__":
    main()
