"""Parse official Diet member rosters (saved raw HTML) into roster.json.

Usage: python3 -I fetch_roster.py RAW_DIR OUT_JSON
RAW_DIR must contain shu_1.htm..shu_10.htm (Shift_JIS) and san.htm (UTF-8),
downloaded from:
  https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/{n}giin.htm
  https://www.sangiin.go.jp/japanese/joho1/kousei/giin/current/giin.htm (redirects to /{session}/giin.htm)
"""
import html
import json
import re
import sys
from pathlib import Path

SHU_BASE = "https://www.shugiin.go.jp/internet/itdb_giinprof.nsf/html/profile/"
SAN_BASE = "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/profile/"


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("　", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def compact(s):
    return re.sub(r"\s+", "", s)


def parse_shu(raw_dir):
    rows = []
    for i in range(1, 11):
        text = (raw_dir / f"shu_{i}.htm").read_bytes().decode("cp932", errors="replace")
        for tr in re.findall(r"<TR[^>]*>(.*?)</TR>", text, re.S | re.I):
            m = re.search(r"profile/(\d+)\.html'?>(.*?)</a>", tr, re.S | re.I)
            if not m:
                continue
            tds = re.findall(r"<TD[^>]*>(.*?)</TD>", tr, re.S | re.I)
            if len(tds) < 5:
                continue
            name = compact(clean(m.group(2)))
            name = re.sub(r"君$", "", name)
            rows.append({
                "house": "衆議院",
                "profileId": m.group(1),
                "name": name,
                "kana": compact(clean(tds[1])),
                "kaiha": compact(clean(tds[2])),
                "district": compact(clean(tds[3])),
                "terms": compact(clean(tds[4])),
                "profileUrl": SHU_BASE + m.group(1) + ".html",
            })
    return rows


def parse_san(raw_dir):
    text = (raw_dir / "san.htm").read_text(encoding="utf-8", errors="replace")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        m = re.search(r'profile/(\d+)\.htm"[^>]*>(.*?)</a>', tr, re.S | re.I)
        if not m:
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)
        # first td holds the name link; th (kana initial) is not a td
        idx = next(i for i, t in enumerate(tds) if "profile/" in t)
        rest = tds[idx + 1:]
        if len(rest) < 4:
            continue
        full = compact(clean(m.group(2)))
        legal = re.search(r"[\[［](.+?)[\]］]", full)
        rows.append({
            "house": "参議院",
            "profileId": m.group(1),
            "name": re.sub(r"[\[［].*?[\]］]", "", full),
            "legalName": legal.group(1) if legal else None,
            "kana": compact(clean(rest[0])),
            "kaiha": compact(clean(rest[1])),
            "district": compact(clean(rest[2])),
            "termEnd": compact(clean(rest[3])),
            "profileUrl": SAN_BASE + m.group(1) + ".htm",
        })
    return rows


def main():
    raw_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    shu, san = parse_shu(raw_dir), parse_san(raw_dir)
    out.write_text(json.dumps({"shu": shu, "san": san}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"衆議院 {len(shu)}人 / 参議院 {len(san)}人")


if __name__ == "__main__":
    main()
