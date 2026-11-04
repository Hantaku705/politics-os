"""Collect House of Representatives bill records (衆議院 議案情報) for given sessions.

Usage: python3 -I fetch_bills.py OUT_JSON RAW_DIR SESSION [SESSION ...]
Reads kaiji{N}.htm list pages, follows every 経過 (keika) link, parses the key/value table.
Raw HTML is saved under RAW_DIR. Resumable (skips keika pages already saved).
"""
import concurrent.futures as cf
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/"
UA = {"User-Agent": "politics-os/0.1 (civic research)"}


def get(url, path):
    if path.exists() and path.stat().st_size > 500:
        return path.read_bytes().decode("cp932", errors="replace")
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
            path.write_bytes(b)
            time.sleep(0.7)
            return b.decode("cp932", errors="replace")
        except Exception:
            time.sleep(3 * (i + 1))
    return ""


def cells(t):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()
             for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        if any(c):
            out.append(c)
    return out


def names(s):
    return [re.sub(r"君$", "", re.sub(r"[\s　]", "", x)) for x in re.split(r"[;；、]", s or "") if x.strip()]


def parse_keika(t):
    kv = {}
    for c in cells(t):
        if len(c) >= 2 and c[0] not in ("項目",):
            kv[c[0]] = c[1]
    return kv


def main():
    out, raw = Path(sys.argv[1]), Path(sys.argv[2])
    raw.mkdir(parents=True, exist_ok=True)
    links = {}
    for s in sys.argv[3:]:
        t = get(f"{BASE}kaiji{s}.htm", raw / f"kaiji{s}.htm")
        # section headers like 衆法の一覧 / 参法の一覧 / 閣法の一覧 ...
        for sec in re.split(r"(?=<caption|<h3|<H3|<CAPTION)", t):
            kind = re.search(r"(衆法|参法|閣法|予算|条約|承認|承諾|決算|国有財産|ＮＨＫ決算|決議|規程|規則|憲法改正)", sec[:400])
            for href in re.findall(r'href="\./keika/([0-9A-F]+)\.htm"', sec):
                links.setdefault(href, {"listedIn": s, "section": kind.group(1) if kind else None})
    print("keika pages", len(links), flush=True)

    def work(key):
        t = get(f"{BASE}keika/{key}.htm", raw / f"keika_{key}.htm")
        return key, parse_keika(t)

    bills = []
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for i, (key, kv) in enumerate(ex.map(work, links), 1):
            if not kv:
                continue
            bills.append({
                "key": key,
                "url": f"{BASE}keika/{key}.htm",
                "kind": kv.get("議案種類"),
                "session": kv.get("議案提出回次"),
                "number": kv.get("議案番号"),
                "title": kv.get("議案件名"),
                "submitterLabel": kv.get("議案提出者"),
                "submitterKaiha": [x.strip() for x in re.split(r"[;；]", kv.get("議案提出会派") or "") if x.strip()],
                "submitters": names(kv.get("議案提出者一覧")),
                "supporters": names(kv.get("議案提出の賛成者")),
                "shuCommitteeResult": kv.get("衆議院審査終了年月日／衆議院審査結果"),
                "shuResult": kv.get("衆議院審議終了年月日／衆議院審議結果"),
                "shuStance": kv.get("衆議院審議時会派態度"),
                "shuFor": [x.strip() for x in re.split(r"[;；]", kv.get("衆議院審議時賛成会派") or "") if x.strip()],
                "shuAgainst": [x.strip() for x in re.split(r"[;；]", kv.get("衆議院審議時反対会派") or "") if x.strip()],
                "sanResult": kv.get("参議院審議終了年月日／参議院審議結果"),
                "promulgated": kv.get("公布年月日／法律番号"),
                "listedIn": links[key]["listedIn"],
            })
            if i % 100 == 0:
                print(i, flush=True)
    out.write_text(json.dumps(bills, ensure_ascii=False, indent=0), encoding="utf-8")
    print("bills", len(bills))


if __name__ == "__main__":
    main()
