"""Download Wikimedia Commons thumbnails listed in photos.json into OUT_DIR/{id}.{jpg|png|webp} (self-hosted; no hotlinking).

Usage: python3 -I fetch_photos.py PHOTOS_JSON OUT_DIR
Resumable. Each photo keeps license/artist/filePage for the credit line shown on the site.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

UA = {"User-Agent": "politics-os/0.1 (civic research; contact https://github.com/Hantaku705/politics-os)"}


def main():
    photos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for mid, v in photos.items():
        if any(x.stat().st_size > 1000 for x in out.glob(f"{mid}.*")):
            ok += 1
            continue
        for i in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(v["thumb"], headers=UA), timeout=60) as r:
                    b = r.read()
                ext = "jpg" if b[:3] == b"\xff\xd8\xff" else "png" if b[:8] == b"\x89PNG\r\n\x1a\n" else \
                    "webp" if b[:4] == b"RIFF" and b[8:12] == b"WEBP" else None
                if not ext:
                    raise ValueError("not an image")
                (out / f"{mid}.{ext}").write_bytes(b)
                ok += 1
                break
            except Exception as e:  # noqa: BLE001
                time.sleep(5 * (i + 1))
        else:
            fail += 1
            print("fail", mid, flush=True)
        time.sleep(0.4)
    print("photos ok", ok, "fail", fail)


if __name__ == "__main__":
    main()
