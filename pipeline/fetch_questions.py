"""Collect written questions (質問主意書) for given sessions from both Houses' official lists.

Usage: python3 -I fetch_questions.py OUT_JSON RAW_DIR SESSION [SESSION ...]
Sources:
  衆: https://www.shugiin.go.jp/internet/itdb_shitsumon.nsf/html/shitsumon/kaiji{N}_l.htm (cp932)
  参: https://www.sangiin.go.jp/japanese/joho1/kousei/syuisyo/{N}/syuisyo.htm (utf-8)
Output rows: {house, session, number, title, submitter, url, list}. Raw HTML saved under RAW_DIR (resumable).
"""
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

SHU = "https://www.shugiin.go.jp/internet/itdb_shitsumon.nsf/html/shitsumon/"
SAN = "https://www.sangiin.go.jp/japanese/joho1/kousei/syuisyo/"
UA = {"User-Agent": "politics-os/0.1 (civic research)"}


def get(url, path, enc):
    if path.exists() and path.stat().st_size > 500:
        return path.read_bytes().decode(enc, errors="replace")
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
            path.write_bytes(b)
            time.sleep(0.8)
            return b.decode(enc, errors="replace")
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return ""


def txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def name(s):
    """'田村智子君外三名' -> '田村智子' (lead submitter; co-submitters are not listed on the index page)."""
    return re.split(r"君", re.sub(r"[\s　]", "", txt(s)))[0]


def shu(session, raw):
    url = f"{SHU}kaiji{session}_l.htm"
    t = get(url, raw / f"shu_kaiji{session}_l.htm", "cp932")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        num = re.search(r'SHITSUMON\.NUMBER"[^>]*>(.*?)</TD>', tr, re.S | re.I)
        if not num or not txt(num.group(1)).isdigit():
            continue
        title = re.search(r'SHITSUMON\.KENMEI"[^>]*>(.*?)</TD>', tr, re.S | re.I)
        sub = re.search(r'SHITSUMON\.TEISHUTSUSHA"[^>]*>(.*?)</TD>', tr, re.S | re.I)
        status = re.search(r'SHITSUMON\.STATUS"[^>]*>(.*?)</TD>', tr, re.S | re.I)
        q = re.search(r'SHITSUMON\.SLINK"[^>]*>.*?HREF="([^"]+)"', tr, re.S | re.I)
        rows.append({"house": "衆議院", "session": session, "number": int(txt(num.group(1))),
                     "title": txt(title.group(1)) if title else "", "submitterRaw": txt(sub.group(1)) if sub else "",
                     "submitters": [name(x) for x in re.split(r"[、,，]", txt(sub.group(1)))] if sub else [],
                     "status": txt(status.group(1)) if status else "",
                     "url": SHU + q.group(1) if q else url, "list": url})
    return rows


def san(session, raw):
    url = f"{SAN}{session}/syuisyo.htm"
    t = get(url, raw / f"san_syuisyo{session}.htm", "utf-8")
    rows = []
    # each question = a 件名 row (with meisai link) followed by a row holding 提出番号 and 提出者
    for m in re.finditer(r'<a href="meisai/(m\d+\.htm)"[^>]*>(.*?)</a>.*?<td headers="t\d+"[^>]*>\s*(\d+)\s*</td>.*?提出者</th>\s*<td[^>]*>(.*?)</td>(.*?)</tr>',
                         t, re.S):
        qlink = re.search(r'href="(syuh/[^"]+)"', m.group(5))
        rows.append({"house": "参議院", "session": session, "number": int(m.group(3)), "title": txt(m.group(2)),
                     "submitterRaw": txt(m.group(4)), "submitters": [name(x) for x in re.split(r"[、,，]", txt(m.group(4)))],
                     "status": "", "url": f"{SAN}{session}/{qlink.group(1)}" if qlink else f"{SAN}{session}/meisai/{m.group(1)}",
                     "list": url})
    return rows


def main():
    out, raw = Path(sys.argv[1]), Path(sys.argv[2])
    raw.mkdir(parents=True, exist_ok=True)
    allrows = []
    for s in sys.argv[3:]:
        a, b = shu(s, raw), san(s, raw)
        print(s, "衆", len(a), "参", len(b), flush=True)
        allrows += a + b
    out.write_text(json.dumps(allrows, ensure_ascii=False, indent=0), encoding="utf-8")
    print("questions", len(allrows))


if __name__ == "__main__":
    main()
