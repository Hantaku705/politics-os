"""Fetch the speaker sequence of every Diet meeting in a window (kokkai.ndl.go.jp meeting_list API; no speech text).

Usage: python3 -I fetch_meeting_list.py OUT_JSONL FROM UNTIL
One line per meeting: {issueID, house, meeting, issue, date, url, speeches: [[order, speaker, speechURL], ...]}.
Used to derive question/answer exchanges (who spoke right after whom). Resumable by issueID.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://kokkai.ndl.go.jp/api/meeting_list"
PAGE = 100


def call(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "politics-os-research/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            time.sleep(1.0)
            return d
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise last


def main():
    out, frm, until = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    done = set()
    if out.exists():
        done = {json.loads(l)["issueID"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    start, total, n = 1, None, 0
    with out.open("a", encoding="utf-8") as fh:
        while total is None or start <= total:
            d = call({"from": frm, "until": until, "maximumRecords": PAGE, "startRecord": start, "recordPacking": "json"})
            total = int(d.get("numberOfRecords") or 0)
            for m in d.get("meetingRecord", []):
                if m["issueID"] in done:
                    continue
                fh.write(json.dumps({"issueID": m["issueID"], "house": m["nameOfHouse"], "meeting": m["nameOfMeeting"],
                                     "issue": m["issue"], "date": m["date"], "url": m["meetingURL"],
                                     "speeches": [[s["speechOrder"], s["speaker"], s["speechURL"]] for s in m.get("speechRecord", [])]},
                                    ensure_ascii=False) + "\n")
                done.add(m["issueID"])
                n += 1
            print(f"{min(start + PAGE - 1, total)}/{total}", flush=True)
            start += PAGE
    print("meetings written", n, "total", len(done))


if __name__ == "__main__":
    main()
