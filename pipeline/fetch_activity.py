"""Count each member's speeches in the Diet minutes API (kokkai.ndl.go.jp).

Usage: python3 -I fetch_activity.py ROSTER_JSON CACHE_JSONL FROM UNTIL [SHARD NSHARDS]
(all *.jsonl caches next to CACHE_JSONL are read so shards never redo work)

- The API's `speaker` filter is a partial match, so every returned record is
  checked for an exact speaker-name match. If the first page has no foreign
  names, the API total is used; otherwise all pages are scanned and only exact
  matches are counted.
- Old/variant kanji (髙/高 etc.) are retried when nothing matches.
- Resumable: finished (name, kind) pairs in CACHE_JSONL are skipped.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://kokkai.ndl.go.jp/api/speech"
PAGE = 30
WAIT = 1.2
VARIANTS = str.maketrans({"髙": "高", "﨑": "崎", "德": "徳", "濵": "浜", "邊": "辺", "邉": "辺",
                          "齋": "斎", "齊": "斉", "櫻": "桜", "眞": "真", "廣": "広", "籠": "篭", "嶋": "島"})
REVERSE = str.maketrans({"高": "髙", "崎": "﨑", "辺": "邊", "斎": "齋", "島": "嶋"})
KINDS = {"all": None, "money": "政治資金"}


def call(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "politics-os-research/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            time.sleep(WAIT)
            return data
        except Exception as e:  # network hiccup or rate limit
            time.sleep(5 * (attempt + 1))
            last = e
    raise last


def count(name, kana, any_word, frm, until):
    base = {"speaker": name, "from": frm, "until": until, "maximumRecords": PAGE, "recordPacking": "json"}
    if any_word:
        base["any"] = any_word
    d = call({**base, "startRecord": 1})
    total = int(d.get("numberOfRecords") or 0)
    recs = d.get("speechRecord", [])
    exact = [r for r in recs if r.get("speaker") == name]
    foreign = [r for r in recs if r.get("speaker") != name]
    yomi_ok = all((r.get("speakerYomi") or kana) == kana for r in exact)
    if not foreign:
        return {"count": total, "method": "api_total", "yomiOk": yomi_ok}
    n, start = len(exact), 1 + PAGE
    while start <= total:
        d = call({**base, "startRecord": start})
        n += sum(1 for r in d.get("speechRecord", []) if r.get("speaker") == name)
        start += PAGE
    return {"count": n, "method": "exact_scan", "yomiOk": yomi_ok, "apiTotal": total}


def main():
    roster, cache = Path(sys.argv[1]), Path(sys.argv[2])
    frm, until = sys.argv[3], sys.argv[4]
    data = json.loads(roster.read_text(encoding="utf-8"))
    members = data["shu"] + data["san"]
    shard, nshards = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (0, 1)
    members = [m for i, m in enumerate(members) if i % nshards == shard]
    done, zero = set(), set()
    for f in cache.parent.glob("activity*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["house"], r["profileId"], r["kind"]))
            if r["kind"] == "all" and r["count"] == 0:
                zero.add((r["house"], r["profileId"]))
    with cache.open("a", encoding="utf-8") as out:
        for i, m in enumerate(members, 1):
            for kind, word in KINDS.items():
                key = (m["house"], m["profileId"], kind)
                if key in done:
                    continue
                if kind == "money" and (m["house"], m["profileId"]) in zero:
                    # no speeches at all -> none containing the keyword
                    out.write(json.dumps({"house": m["house"], "profileId": m["profileId"], "kind": kind, "name": m["name"],
                                          "matchedName": m["name"], "from": frm, "until": until, "count": 0,
                                          "method": "implied_by_zero_total", "yomiOk": True}, ensure_ascii=False) + "\n")
                    continue
                res = count(m["name"], m["kana"], word, frm, until)
                used = m["name"]
                if m.get("legalName"):  # 通称[本名]: minutes may use either
                    r2 = count(m["legalName"], m["kana"], word, frm, until)
                    if r2["count"] > 0 and res["count"] > 0:
                        res = {**res, "count": res["count"] + r2["count"], "method": "alias_sum"}
                        used = m["name"] + "|" + m["legalName"]
                    elif r2["count"] > 0:
                        res, used = r2, m["legalName"]
                if res["count"] == 0:
                    for alt in {m["name"].translate(VARIANTS), m["name"].translate(REVERSE)} - {m["name"]}:
                        r2 = count(alt, m["kana"], word, frm, until)
                        if r2["count"] > 0:
                            res, used = r2, alt
                            break
                row = {"house": m["house"], "profileId": m["profileId"], "kind": kind, "name": m["name"],
                       "matchedName": used, "from": frm, "until": until, **res}
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                if kind == "all" and res["count"] == 0:
                    zero.add((m["house"], m["profileId"]))
            if i % 25 == 0:
                print(f"{i}/{len(members)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
