"""Collect House of Councillors member bills (参法) for given sessions.

Usage: python3 -I fetch_san_bills.py OUT_JSON RAW_DIR SESSION [SESSION ...]
Source: https://www.sangiin.go.jp/japanese/joho1/kousei/gian/{session}/gian.htm -> meisai pages.
The HTML lists only the lead proposer (発議者「○○君 外N名」); co-proposers are in PDFs and are NOT collected.
Resumable (raw HTML cached under RAW_DIR).
"""
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/"
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


def sections(t):
    """Return {(section_heading, field): value} walking th/td rows in order."""
    out, head = {}, ""
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        ths = re.findall(r"<th[^>]*>(.*?)</th>", tr, re.S | re.I)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)
        if ths and not tds:
            head = txt(ths[0])
        elif ths and tds:
            out[(head, txt(ths[0]))] = txt(tds[0])
    return out


def main():
    out, raw = Path(sys.argv[1]), Path(sys.argv[2])
    raw.mkdir(parents=True, exist_ok=True)
    bills = []
    for s in sys.argv[3:]:
        t = get(f"{BASE}{s}/gian.htm", raw / f"gian_{s}.htm")
        m = re.search(r"法律案（参法）一覧(.*?)</table>", t, re.S)
        if not m:
            print(s, "no 参法 list", flush=True)
            continue
        for row in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S):
            a = re.search(r'href="\./meisai/(m\d+\.htm)"[^>]*>(.*?)</a>', row, re.S)
            tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if not a or len(tds) < 2:
                continue
            page = get(f"{BASE}{s}/meisai/{a.group(1)}", raw / f"{s}_{a.group(1)}")
            kv = sections(page)
            g = lambda h, f: kv.get((h, f), "")  # noqa: E731
            lead_label = next((v for (h, f), v in kv.items() if f == "発議者"), "")
            lead = re.sub(r"[\s　]", "", re.split(r"君", lead_label)[0]) if lead_label else ""
            bills.append({
                "key": f"san-{a.group(1)[:-4]}",
                "url": f"{BASE}{s}/meisai/{a.group(1)}",
                "kind": "参法",
                "session": txt(tds[0]),
                "number": txt(tds[1]),
                "title": txt(a.group(2)),
                "submitterLabel": lead_label,
                "lead": lead,
                "submittedOn": next((v for (h, f), v in kv.items() if f == "提出日"), ""),
                "sanResult": g("参議院本会議経過", "議決"),
                "sanResultDate": g("参議院本会議経過", "議決日"),
                "shuResult": g("衆議院本会議経過", "議決"),
                "promulgated": g("その他", "公布年月日"),
                "continued": next((v for (h, f), v in kv.items() if f == "継続区分"), ""),
                "listedIn": s,
            })
        print(s, len(bills), flush=True)
    out.write_text(json.dumps(bills, ensure_ascii=False, indent=0), encoding="utf-8")
    print("san bills", len(bills))


if __name__ == "__main__":
    main()
