"""Fetch the current cabinet roster (閣僚・副大臣・大臣政務官・総理補佐官) from the Prime Minister's Office.

Usage: python3 -I fetch_cabinet.py OUT_JSON RAW_DIR
Source: https://www.kantei.go.jp/jp/105/meibo/ (第2次高市改造内閣). Some names are external-character images; their
reading (alt text / ruby) is kept so they can be matched by kana + house.
"""
import html
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

BASE = "https://www.kantei.go.jp/jp/105/meibo/"
PAGES = [("閣僚", "index.html"), ("副大臣", "fukudaijin.html"), ("大臣政務官", "seimukan.html"), ("総理補佐官", "sourihosakan.html")]
UA = {"User-Agent": "Mozilla/5.0 (politics-os civic research)"}


def get(url, path):
    if path.exists() and path.stat().st_size > 1000:
        return path.read_text(encoding="utf-8", errors="replace")
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
            path.write_bytes(b)
            time.sleep(1.0)
            return b.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    raise SystemExit(f"failed: {url}")


def txt(s):
    """Plain text with full-width digits/letters normalised (NFKC), e.g. '令和８年' -> '令和8年'."""
    return unicodedata.normalize("NFKC", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)))).strip()


def main():
    out, raw = Path(sys.argv[1]), Path(sys.argv[2])
    raw.mkdir(parents=True, exist_ok=True)
    people, as_of = [], {}
    for group, page in PAGES:
        t = get(BASE + page, raw / f"kantei_{page}")
        d = re.search(r"令和\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日\s*現在", txt(t))
        as_of[group] = d.group(0).replace(" ", "") if d else ""
        # the first list on index.html is the cabinet; later items such as former holders are marked with a date range
        for retired, li in re.findall(r'<li class="list-profile__item( list-profile__item--retired)?">(.*?)</li>', t, re.S):
            title = re.search(r'<div class="list-profile__title">(.*?)</div>', li, re.S)
            name = re.search(r'<p class="list-profile__name">(.*?)</p>', li, re.S)
            if not title or not name:
                continue
            ruby = re.search(r'list-profile__name--ruby">（(.*?)）<', name.group(1))
            alt = re.search(r'alt="([^"]+)"', name.group(1))
            name_txt = txt(re.sub(r'<span class="list-profile__name--ruby">.*?</span>', "", name.group(1)))
            house = re.search(r'<p class="label[^"]*">\s*(衆議院|参議院)\s*</p>', li)
            period = re.compile(r"令和\d+年\d+月\d+日\s*[～~〜]\s*令和\d+年\d+月\d+日")
            posts = [txt(x) for x in re.split(r"<br\s*/?>", title.group(1)) if txt(x) and not period.fullmatch(txt(x))]
            span = period.search(txt(li))
            former = (span.group(0) if span else "前任") if retired else None
            link = re.search(r'href="(/jp/105/meibo/[^"]+)"', li)
            people.append({
                "group": group, "posts": posts,
                "name": re.sub(r"\s", "", name_txt) or None,
                "kana": re.sub(r"\s", "", (ruby.group(1) if ruby else (alt.group(1) if alt else ""))),
                "house": house.group(1) if house else None,
                "former": former,
                "url": "https://www.kantei.go.jp" + link.group(1) if link else BASE + page,
                "list": BASE + page,
            })
        print(group, sum(1 for p in people if p["group"] == group), as_of[group], flush=True)
    out.write_text(json.dumps({"asOf": as_of, "source": BASE, "people": people}, ensure_ascii=False, indent=0), encoding="utf-8")
    print("people", len(people), "former", sum(1 for p in people if p["former"]), "no-house", sum(1 for p in people if not p["house"]))


if __name__ == "__main__":
    main()
