"""Collect House of Councillors plenary individual votes (押しボタン/記名投票) for sessions.

Usage: python3 -I fetch_san_votes.py OUT_JSON RAW_DIR SESSION [SESSION ...]
Source: https://www.sangiin.go.jp/japanese/touhyoulist/{session}/vote_ind.htm
Only HTML detail pages are parsed (a few early votes are PDF-only and are listed as such).
"""
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.sangiin.go.jp/japanese/touhyoulist/"
UA = {"User-Agent": "politics-os/0.1 (civic research)"}


def get(url, path):
    if path.exists() and path.stat().st_size > 500:
        return path.read_text(encoding="utf-8", errors="replace")
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
            path.write_bytes(b)
            time.sleep(0.7)
            return b.decode("utf-8", errors="replace")
        except Exception:
            time.sleep(3 * (i + 1))
    return ""


def txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def main():
    out, raw = Path(sys.argv[1]), Path(sys.argv[2])
    raw.mkdir(parents=True, exist_ok=True)
    votes, pdf_only = [], []
    for s in sys.argv[3:]:
        idx = get(f"{BASE}{s}/vote_ind.htm", raw / f"vote_ind_{s}.htm")
        date = None
        for tr in re.findall(r"<TR[^>]*>(.*?)</TR>", idx, re.S | re.I):
            d = re.search(r'class="touhyo_date">([^<]+)<', tr)
            if d:
                date = txt(d.group(1))
            m = re.search(r'HREF="([^"]+\.(htm|pdf))">(.*?)</A>', tr, re.S | re.I)
            if not m:
                continue
            href, ext, title = m.group(1), m.group(2).lower(), txt(m.group(3))
            if ext == "pdf":
                pdf_only.append({"session": s, "date": date, "title": title, "url": f"{BASE}{s}/{href}"})
                continue
            t = get(f"{BASE}{s}/{href}", raw / f"{s}_{href}")
            tot = re.search(r"投票総数\s*(\d+)\s*賛成票\s*(\d+)\s*反対票\s*(\d+)", txt(t))
            members = {}
            # legacy table format (<=216): <TD class="pro">..</TD><TD class="con">..</TD><TD .. class="nam">name</TD>
            for pro, con, nm in re.findall(r'<TD[^>]*class="pro"[^>]*>(.*?)</TD>\s*<TD[^>]*class="con"[^>]*>(.*?)</TD>\s*<TD[^>]*class="nam"[^>]*>(.*?)</TD>', t, re.S | re.I):
                nm = re.sub(r"[\s　]", "", txt(nm))
                if nm:
                    members[nm] = "賛成" if "<img" in pro.lower() else "反対" if "<img" in con.lower() else "投票なし"
            for li in re.findall(r'<li class="giin">(.*?)</li>', t, re.S):
                pro = txt(re.search(r'class="pros">(.*?)</span>', li, re.S).group(1)) if 'class="pros"' in li else ""
                con = txt(re.search(r'class="cons">(.*?)</span>', li, re.S).group(1)) if 'class="cons"' in li else ""
                nm = re.sub(r"[\s　]", "", txt(re.search(r'class="names">(.*?)</span>', li, re.S).group(1)))
                members[nm] = "賛成" if pro else "反対" if con else "投票なし"
            standing = bool(re.search(r"起立採決", txt(t))) and not members
            votes.append({
                "session": s, "date": date, "title": title, "url": f"{BASE}{s}/{href}",
                "method": "起立採決（個人の賛否の記録なし）" if standing else "押しボタン式投票",
                "total": int(tot.group(1)) if tot else None,
                "yes": int(tot.group(2)) if tot else None,
                "no": int(tot.group(3)) if tot else None,
                "members": members,
            })
        print(s, len(votes), flush=True)
    out.write_text(json.dumps({"votes": votes, "pdfOnly": pdf_only}, ensure_ascii=False), encoding="utf-8")
    print("votes", len(votes), "pdf-only", len(pdf_only))


if __name__ == "__main__":
    main()
