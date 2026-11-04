"""Copy election-bulletin (選挙公報) PDFs listed in pipeline/config/kouhou_sources.json straight into GCS.

Usage: python3 -I fetch_kouhou.py SOURCES_JSON GCS_PREFIX [--only 東京都,北海道]
  e.g. GCS_PREFIX = gs://politics-os-data-2026/v1/raw/20261102/kouhou
Nothing is written to the local disk: each PDF is held in memory and streamed to
GCS_PREFIX/<election-key>/<pref>/<nn>_<hash>.pdf. GCS_PREFIX/manifest.json lists
{file, url, election, electionName, pref, label, bytes, pages, sha1}. Resumable (URLs already in the manifest are skipped).
Polite: 1 request/second, official sites only.
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import time
import http.cookiejar
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (politics-os civic research; contact https://github.com/Hantaku705/politics-os)"}
# Sites behind bot protection (愛知: Imperva) answer 403 to scripts. Open the page once in a browser, then pass that
# session's cookie and the browser's User-Agent here (env only, never stored): KOUHOU_COOKIE / KOUHOU_UA.
if os.environ.get("KOUHOU_COOKIE"):
    UA = {"User-Agent": os.environ.get("KOUHOU_UA", UA["User-Agent"]), "Cookie": os.environ["KOUHOU_COOKIE"]}
ACCOUNT_ARGS = [f"--account={os.environ['POS_GCS_ACCOUNT']}"] if os.environ.get("POS_GCS_ACCOUNT") else []  # gcloud account (default: the active one)
# Some prefectures (e.g. 愛知) redirect to set a cookie first; a cookie jar avoids the redirect loop.
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def safe_url(u):
    """Percent-encode non-ASCII characters (e.g. Japanese file names on 秋田's site) without double-encoding."""
    return urllib.parse.quote(u, safe=":/?#[]@!$&'()*+,;=%~")


def gcs_put(data: bytes, dest: str):
    subprocess.run(["gcloud", "storage", "cp", "-", dest, *ACCOUNT_ARGS, "--quiet"], input=data, check=True, capture_output=True)


def gcs_get(src: str):
    r = subprocess.run(["gcloud", "storage", "cat", src, *ACCOUNT_ARGS], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def pages_of(b: bytes):
    try:
        from pypdf import PdfReader  # optional
        return len(PdfReader(io.BytesIO(b)).pages)
    except Exception:  # noqa: BLE001
        return len(re.findall(rb"/Type\s*/Page[^s]", b)) or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources")
    ap.add_argument("gcs")
    ap.add_argument("--only")
    a = ap.parse_args()
    gcs = a.gcs.rstrip("/")
    assert gcs.startswith("gs://"), "GCS_PREFIX must be gs://..."
    src = json.load(open(a.sources, encoding="utf-8"))
    only = set(a.only.split(",")) if a.only else None
    got = gcs_get(f"{gcs}/manifest.json")
    manifest = json.loads(got) if got else []
    have = {m["url"] for m in manifest}

    def save_manifest():
        gcs_put(json.dumps(manifest, ensure_ascii=False, indent=0).encode(), f"{gcs}/manifest.json")

    for el in src["elections"]:
        for p in el["prefectures"]:
            if only and p["pref"] not in only:
                continue
            added = 0
            for i, pdf in enumerate(p.get("pdfs", []), 1):
                if pdf["url"] in have:
                    continue
                key = hashlib.sha1(pdf["url"].encode()).hexdigest()[:8]
                rel = f'{el["key"]}/{p["pref"]}/{i:02d}_{key}.pdf'
                b, err = None, ""
                for attempt in range(3):
                    try:
                        with OPENER.open(urllib.request.Request(safe_url(pdf["url"]), headers=UA), timeout=180) as r:
                            b = r.read()
                        if not b.startswith(b"%PDF"):
                            raise ValueError("not a PDF")
                        break
                    except Exception as e:  # noqa: BLE001
                        b, err = None, str(e)
                        if "CERTIFICATE_VERIFY_FAILED" in err:  # 栃木: server omits its intermediate cert; curl (system trust) copes
                            r = subprocess.run(["curl", "-sfL", "-A", UA["User-Agent"], safe_url(pdf["url"])], capture_output=True)
                            if r.returncode == 0 and r.stdout.startswith(b"%PDF"):
                                b = r.stdout
                                break
                        time.sleep(3 * (attempt + 1))
                if b is None:
                    print("FAIL", el["key"], p["pref"], pdf["label"], err, flush=True)
                    continue
                gcs_put(b, f"{gcs}/{rel}")
                manifest.append({"file": rel, "url": pdf["url"], "election": el["key"], "electionName": el["election"],
                                 "pref": p["pref"], "label": pdf["label"], "bytes": len(b), "pages": pages_of(b),
                                 "sha1": hashlib.sha1(b).hexdigest()})
                have.add(pdf["url"])
                added += 1
                del b
                time.sleep(1.0)
            if added:
                save_manifest()
                print(el["key"], p["pref"], "added", added, flush=True)
    save_manifest()
    print("total", len(manifest), "files", sum(m["bytes"] for m in manifest) // 1_000_000, "MB", "pages",
          sum(m["pages"] or 0 for m in manifest), flush=True)


if __name__ == "__main__":
    main()
