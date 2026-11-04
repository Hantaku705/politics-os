"""Extract current members' own pledges from election-bulletin (選挙公報) PDFs with Gemini (Vertex AI).

Usage: ~/anyagents/.venv/bin/python extract_pledges.py GCS_PREFIX MEMBERS_JSON OUT_JSONL --budget-usd N [--only-file ...] [--workers 4]
Auth: a gcloud access token for $POS_GCS_ACCOUNT (or the active gcloud account; personal project politics-os-2026, billing stays off company
projects), refreshed every 40 minutes because a token lives one hour. Model: gemini-3-flash-preview @ global.

Two steps per page (PDFs and page images stay in memory; nothing is written to the local disk):
  1. The page is rendered at 200 dpi (Ghostscript). A downscaled copy is sent to find each candidate's block (name + box).
  2. Only blocks whose name matches a CURRENT member are cropped at full resolution and read for pledges.
     Losing candidates are never read or stored (their names are kept only as a count).
Why crops (tested on 東京都第20区, 2026-11-02): reading the whole PDF, even at high resolution, paraphrased large vertical
headings (「大国のエゴから日本を守る」 -> 「大震災のゴマから…」). A crop gives each block ~4x the pixels and the body text is read.
PR (比例) bulletins are party pages and are skipped: their text is a party's pledge, never an individual's.
Each output row = one PDF: {file, url, election, pref, label, pages, candidates:[{..., memberId, matchedBy, page, box}], ...}.
"""
import argparse
import os
import difflib
import io
import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from PIL import Image

MODEL = "gemini-3-flash-preview"
# USD per 1M tokens (Vertex AI list price for Gemini 3 Flash preview; updated if billing shows otherwise)
PRICE_IN, PRICE_OUT = 0.50, 3.00
ACCOUNT_ARGS = [f"--account={os.environ['POS_GCS_ACCOUNT']}"] if os.environ.get("POS_GCS_ACCOUNT") else []  # gcloud account (default: the active one)

BOX_PROMPT = ("選挙公報のこのページで、候補者ごとの掲載欄（氏名・写真・政策文を含む枠全体）を全部挙げ、"
              "氏名（公報の表記）・氏名の読み（ひらがな。ふりがながなければ通常の読み）・位置 box_2d [ymin, xmin, ymax, xmax]（0-1000）を返してください。"
              "政党の欄（候補者個人でないもの）は含めないでください。")
PROMPT = """これは日本の国政選挙の選挙公報のうち、1人の候補者の掲載欄の画像です。本人の公約・政策を抽出してください。
規則：
- 公報に書かれている文言だけを使う。要約や言い換えはしない。quote は原文の連続した文字列から50字以内で切り出す（長い文は前から50字まで）。
- 公約・政策・約束にあたる項目と、本人が実績として書いた項目を、あわせて最大15件。経歴・推薦の言葉・スローガンだけの文・他党批判だけの文は除く。
- kind は、これからやると約束・提案している項目なら "公約"、すでにやった・実現したと書いている項目（「主な実績」「実現しました」「〜を創設」など）なら "実績"。
- 読めない・判別できない部分は推測しない。欄の外にはみ出した別の候補者の文は使わない。
- area は政策分野（例：経済・物価、子育て・教育、医療・介護、外交・安全保障、政治改革、地域）。
- verifiable は対象と内容が具体的なら true。deadline は期限・数値目標があれば true。
- criterion は政治とカネの4基準に当たれば 1公開／2領収書／3監査／4罰則・返還 の番号、なければ null。"""

_S = types.Schema
BOX_SCHEMA = _S(type="OBJECT", properties={"blocks": _S(type="ARRAY", items=_S(type="OBJECT", properties={
    "name": _S(type="STRING"), "kana": _S(type="STRING"), "box_2d": _S(type="ARRAY", items=_S(type="INTEGER"))},
    required=["name", "kana", "box_2d"]))}, required=["blocks"])
_PLEDGE = _S(type="OBJECT", properties={"quote": _S(type="STRING"), "kind": _S(type="STRING", enum=["公約", "実績"]),
                                        "area": _S(type="STRING"), "verifiable": _S(type="BOOLEAN"),
                                        "deadline": _S(type="BOOLEAN"), "criterion": _S(type="INTEGER", nullable=True)},
             required=["quote", "kind", "area", "verifiable", "deadline"])
SCHEMA = _S(type="OBJECT", properties={"name": _S(type="STRING"), "party": _S(type="STRING"),
                                       "pledges": _S(type="ARRAY", items=_PLEDGE)}, required=["name", "pledges"])
# A fixed schema lets thinking stay "low": without it, low thinking dropped candidates and medium cost 20x more.
LOW = types.ThinkingConfig(thinking_level="low")


def gcs_get(src):
    r = subprocess.run(["gcloud", "storage", "cat", src, *ACCOUNT_ARGS], capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"gcs read failed: {src}")
    return r.stdout


def n_pages(pdf):
    from pypdf import PdfReader
    return len(PdfReader(io.BytesIO(pdf)).pages)


def unlock(pdf):
    """Some bulletins are encrypted with an empty user password (viewable, but Ghostscript refuses): re-save decrypted, in memory."""
    from pypdf import PdfReader, PdfWriter
    rd = PdfReader(io.BytesIO(pdf))
    if not rd.is_encrypted:
        return pdf
    rd.decrypt("")
    w = PdfWriter()
    for pg in rd.pages:
        w.add_page(pg)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def render(pdf, page, dpi=200):
    """One PDF page -> PIL image, entirely in memory (Ghostscript reads stdin, writes PNG to stdout)."""
    r = subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", f"-r{dpi}",
                        f"-dFirstPage={page}", f"-dLastPage={page}", "-sOutputFile=-", "-"], input=pdf, capture_output=True)
    if not r.stdout.startswith(b"\x89PNG"):
        raise RuntimeError(f"render failed page {page}: {r.stderr[:200]!r}")
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def jpeg(im, max_side=None, q=88):
    if max_side:
        im = im.copy()
        im.thumbnail((max_side, max_side))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q)
    return b.getvalue()


def norm(s):
    s = re.sub(r"[\s　・]", "", s or "")
    s = "".join(chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch for ch in s)  # katakana -> hiragana
    return s.translate(str.maketrans({"髙": "高", "﨑": "崎", "德": "徳", "濵": "浜", "邊": "辺", "邉": "辺", "齋": "斎",
                                      "齊": "斉", "櫻": "桜", "眞": "真", "廣": "広", "嶋": "島", "惠": "恵", "澤": "沢"}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gcs")
    ap.add_argument("members")
    ap.add_argument("out")
    ap.add_argument("--budget-usd", type=float, required=True)
    ap.add_argument("--only-file", help="process only manifest entries whose file path contains one of these (comma)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--reread", help="previous OUT_JSONL: re-read only the member blocks found there (reuses page + box, skips the box step)")
    a = ap.parse_args()
    gcs = a.gcs.rstrip("/")
    manifest = json.loads(gcs_get(f"{gcs}/manifest.json"))
    manifest = [m for m in manifest if "比例" not in m["label"]]
    if a.only_file:
        keys = a.only_file.split(",")
        manifest = [m for m in manifest if any(k in m["file"] for k in keys)]
    seen, uniq = set(), []
    for m in manifest:  # identical files posted twice (e.g. 合区 on both prefectures' sites) are read once
        if m.get("sha1") not in seen or not m.get("sha1"):
            seen.add(m.get("sha1"))
            uniq.append(m)
    manifest = uniq
    M = json.loads(Path(a.members).read_text(encoding="utf-8"))
    by_name, by_kana = {}, {}
    for m in M:
        for n in {m["name"], m.get("legalName") or "", m.get("speakerQuery") or ""} - {""}:
            by_name.setdefault(norm(n), []).append(m)
        by_kana.setdefault(norm(m["kana"]), []).append(m)
    out = Path(a.out)
    done = {json.loads(l)["file"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    lock = threading.Lock()
    auth = {"client": None, "at": 0.0}

    def client():
        with lock:
            if time.time() - auth["at"] > 10 * 60:  # gcloud may hand back a cached token with little life left
                tok = subprocess.run(["gcloud", "auth", "print-access-token", *ACCOUNT_ARGS], capture_output=True, text=True, check=True).stdout.strip()
                auth["client"] = genai.Client(vertexai=True, project="politics-os-2026", location="global", credentials=Credentials(tok),
                                              http_options=types.HttpOptions(timeout=180_000))  # ms; a dead connection must not hang a worker
                auth["at"] = time.time()
            return auth["client"]
    spent = {"usd": 0.0, "n": 0}

    def match(c, house, pref):
        """Name first, then reading (bulletins often write given names in kana: 山田みき). Same house only; a tie is broken
        by the bulletin's prefecture (伊藤孝江/伊藤孝恵). Last: the single member of that house and prefecture whose name or
        reading is close (>= 0.8; misread kana such as くまがいひろひと). 衆 also needs the same district number."""
        local = lambda ms: [m for m in ms if pref in (m.get("prefectures") or [])]
        for cands in (by_name.get(norm(c.get("name")), []), by_kana.get(norm(c.get("kana")), []) if c.get("kana") else [],
                      by_kana.get(norm(c.get("name")), [])):
            cands = [m for m in cands if m["house"] == house]
            if len(cands) > 1:
                cands = local(cands)
            if len(cands) == 1:
                return cands[0], "exact"
        sim = lambda x, y: difflib.SequenceMatcher(None, norm(x), norm(y)).ratio() if x and y else 0
        num = lambda t: (re.findall(r"\d+", (t or "").translate(str.maketrans("０１２３４５６７８９", "0123456789"))) or [None])[0]
        pool = [m for m in local(x for x in M if x["house"] == house)
                if house != "衆議院" or num(c.get("district")) in (None, num(m.get("district")))]
        scored = sorted(((max(sim(c.get("name"), m["name"]), sim(c.get("kana"), m["kana"]), sim(c.get("name"), m["kana"])), m["id"], m)
                         for m in pool), key=lambda t: -t[0])
        if scored and scored[0][0] >= 0.8 and (len(scored) == 1 or scored[1][0] < 0.8):
            return scored[0][2], "similar"
        return None, None

    def call(parts, schema, res=None):
        err = ""
        for attempt in range(3):
            try:
                cfg = dict(response_mime_type="application/json", response_schema=schema, temperature=0.0, thinking_config=LOW)
                if res:
                    cfg["media_resolution"] = res
                r = client().models.generate_content(model=MODEL, contents=parts, config=types.GenerateContentConfig(**cfg))
                u = r.usage_metadata
                return json.loads(r.text), (u.prompt_token_count or 0), (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                if "401" in err or "UNAUTHENTICATED" in err:
                    with lock:
                        auth["at"] = 0.0  # force a fresh token on the next try
                time.sleep(5 * (attempt + 1))
        print("ERR", err, flush=True)
        return None

    def read_block(im, box, name=""):
        """Crop one candidate's block at full resolution and read it. A box drawn too tight reads nothing: retry wider once."""
        W, H = im.size
        y0, x0, y1, x1 = box
        tin = tout = 0
        for pad in (12, 60):
            crop = im.crop((max(0, (x0 - pad) * W // 1000), max(0, (y0 - pad) * H // 1000),
                            min(W, (x1 + pad) * W // 1000), min(H, (y1 + pad) * H // 1000)))
            got = call([types.Part.from_bytes(data=jpeg(crop), mime_type="image/jpeg"), PROMPT], SCHEMA, "MEDIA_RESOLUTION_HIGH")
            if got is None:
                return None
            d, i_, o_ = got
            tin, tout = tin + i_, tout + o_
            if d.get("pledges"):
                break
        n_promise = lambda dd: sum((p.get("kind") or "公約") == "公約" for p in dd.get("pledges") or [])
        if (len(d.get("pledges") or []) < 3 or n_promise(d) < 2) and x1 - x0 < 600:
            # The box sometimes covers only the name column (北海道7区: right quarter of a full-width block).
            # Read the full-width band at the same height and keep whichever reading found more items.
            band = im.crop((0, max(0, (y0 - 12) * H // 1000), W, min(H, (y1 + 12) * H // 1000)))
            got = call([types.Part.from_bytes(data=jpeg(band), mime_type="image/jpeg"),
                        PROMPT + "\n- この画像に複数の候補者の欄が写っている場合は、氏名が「" + name + "」の欄だけを読む。"],
                       SCHEMA, "MEDIA_RESOLUTION_HIGH")
            if got is not None:
                d2, i_, o_ = got
                tin, tout = tin + i_, tout + o_
                if (n_promise(d2), len(d2.get("pledges") or [])) > (n_promise(d), len(d.get("pledges") or [])):
                    d = d2
        return d, tin, tout

    def reread(row):
        """Same file, same member blocks as a previous run; only the block reading is redone (e.g. after a prompt change)."""
        try:
            pdf = unlock(gcs_get(f'{gcs}/{row["file"]}'))
            tin = tout = 0
            pages, kept = {}, []
            for c in row["candidates"]:
                if c["page"] not in pages:
                    pages[c["page"]] = render(pdf, c["page"])
                got = read_block(pages[c["page"]], c["box"], c["name"])
                if got is None:
                    print("FAIL crop", row["file"], c["page"], c["name"], flush=True)
                    return
                d, i_, o_ = got
                tin, tout = tin + i_, tout + o_
                kept.append({**c, "party": d.get("party") or c.get("party"),
                             "pledges": [{**p, "quote": (p.get("quote") or "")[:50]} for p in d.get("pledges", [])]})
            cost = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
            new = {**row, "candidates": kept, "method": row.get("method", "") + "; reread", "usage": {"in": tin, "out": tout},
                   "cost_usd": round(cost, 6)}
            with lock:
                with out.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(new, ensure_ascii=False) + "\n")
                spent["usd"] += cost
                spent["n"] += 1
                print(f'{spent["n"]:>4} {row["pref"]} {row["label"]} members {len(kept)} cost ${cost:.4f} total ${spent["usd"]:.2f}', flush=True)
        except Exception as e:  # noqa: BLE001
            print("FAIL", row["file"], str(e)[:200], flush=True)

    if a.reread:
        prev = [json.loads(l) for l in Path(a.reread).read_text(encoding="utf-8").splitlines()]
        prev = list({r["file"]: r for r in prev if r["candidates"] and r["file"] not in done}.values())
        print(f"reread files {len(prev)} blocks {sum(len(r['candidates']) for r in prev)} budget ${a.budget_usd}", flush=True)
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            list(ex.map(lambda r: None if spent["usd"] >= a.budget_usd else reread(r), prev))
        print(f'done {spent["n"]} files, est. spend ${spent["usd"]:.2f}', flush=True)
        return

    def one(entry):
        try:
            one_(entry)
        except Exception as e:  # noqa: BLE001  one bad file must not stop the run; nothing is saved, so a rerun retries it
            print("FAIL", entry["file"], str(e)[:200], flush=True)

    def one_(entry):
        with lock:
            if spent["usd"] >= a.budget_usd:
                return
        house = "衆議院" if "shu" in entry["election"] else "参議院"
        t0 = time.time()
        pdf = unlock(gcs_get(f'{gcs}/{entry["file"]}'))
        tin = tout = 0
        kept, others = [], 0
        district = entry["label"]
        for page in range(1, n_pages(pdf) + 1):
            im = render(pdf, page)
            W, H = im.size
            got = call([types.Part.from_bytes(data=jpeg(im, 1600), mime_type="image/jpeg"), BOX_PROMPT], BOX_SCHEMA)
            if got is None:
                print("FAIL boxes", entry["file"], page, flush=True)
                return
            boxes, i_, o_ = got
            tin, tout = tin + i_, tout + o_
            for bl in boxes.get("blocks", []):
                m, how = match({**bl, "district": district}, house, entry["pref"])
                if not m or len(bl.get("box_2d") or []) != 4:
                    others += 1
                    continue
                got = read_block(im, bl["box_2d"], bl["name"])
                if got is None:
                    print("FAIL crop", entry["file"], page, bl["name"], flush=True)
                    return  # nothing saved for this file, so a rerun retries it whole
                d, i_, o_ = got
                tin, tout = tin + i_, tout + o_
                kept.append({"name": bl["name"], "kana": bl.get("kana"), "party": d.get("party"), "page": page, "box": bl["box_2d"],
                             "memberId": m["id"], "matchedBy": how,
                             "pledges": [{**p, "quote": (p.get("quote") or "")[:50]} for p in d.get("pledges", [])]})
        ids = [k["memberId"] for k in kept]  # a member matched only by similarity more than once in one file is ambiguous
        kept = [k for k in kept if not (k["matchedBy"] == "similar" and ids.count(k["memberId"]) > 1)]
        cost = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
        row = {**{k: entry[k] for k in ("file", "url", "election", "electionName", "pref", "label", "pages")},
               "candidates": kept, "otherBlocks": others, "model": MODEL, "method": "page-boxes+crop@200dpi",
               "usage": {"in": tin, "out": tout}, "cost_usd": round(cost, 6), "elapsed_s": round(time.time() - t0, 1)}
        with lock:
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            spent["usd"] += cost
            spent["n"] += 1
            print(f'{spent["n"]:>4} {entry["pref"]} {entry["label"]} members {len(kept)} cost ${cost:.4f} total ${spent["usd"]:.2f}', flush=True)

    todo = [m for m in manifest if m["file"] not in done]
    print(f"pdfs {len(manifest)} todo {len(todo)} budget ${a.budget_usd}", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one, todo))
    print(f'done {spent["n"]} pdfs, est. spend ${spent["usd"]:.2f}', flush=True)


if __name__ == "__main__":
    main()
