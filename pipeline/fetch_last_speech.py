"""For members with no speech in the counting window, find their latest speech at any time (Diet minutes API).

Usage: python3 -I fetch_last_speech.py ACTIVITY_JSONL OUT_JSON UNTIL
Writes {"<house>|<profileId>": {"date","house","meeting","position","url"} | null}. Exact speaker-name match only.
The API returns newest first; pages are scanned until an exact match is found (partial-name hits are skipped).
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://kokkai.ndl.go.jp/api/speech"


def call(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "politics-os-research/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            time.sleep(1.0)
            return d
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise last


def latest(name, until):
    start = 1
    while True:
        d = call({"speaker": name, "until": until, "maximumRecords": 100, "startRecord": start, "recordPacking": "json"})
        recs = d.get("speechRecord", [])
        for r in recs:
            if r.get("speaker") == name:
                return {"date": r.get("date"), "house": r.get("nameOfHouse"), "meeting": r.get("nameOfMeeting"),
                        "position": r.get("speakerPosition") or "", "url": r.get("speechURL")}
        start += 100
        if not recs or start > int(d.get("numberOfRecords") or 0):
            return None


def main():
    act, out, until = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    rows = {}
    for line in act.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["kind"] == "all":
            rows[(r["house"], r["profileId"])] = r
    res = {}
    for (house, pid), r in sorted(rows.items()):
        if r["count"] != 0:
            continue
        hit = None
        for name in r["matchedName"].split("|"):
            hit = latest(name, until)
            if hit:
                break
        res[f"{house}|{pid}"] = hit
        print(r["name"], hit["date"] if hit else "-", flush=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print("done", len(res), "found", sum(1 for v in res.values() if v))


if __name__ == "__main__":
    main()
