"""Party HQ money: 政党本部の収支（官報「政治団体の収支報告書の要旨」, 総務大臣届出分）.

Source: 総務省「政治資金収支報告書の要旨（官報）」 — one PDF per year with every party HQ.
The PDF has a text layer, but its font has no Unicode map: digits come out as the glyphs
"÷øùúûüýþÿĀ" (= 0-9, "ó" = thousands comma) and Japanese labels as other stray code points.
The layout is fixed, so we decode numbers exactly and recognise labels by their (stable) glyph strings.
Every party is checked with the report's own arithmetic:
  収入総額 = 前年繰越額 + 本年収入額
  本年収入額 = sum of the income categories
  支出総額 = 経常経費 + 政治活動費 = sum of the spending categories
Any party failing a check is dropped (and printed), never shown with unchecked numbers.
Donor names (寄附の内訳) are not read.

PDFs are not stored on this machine: fetched into memory, copied to gs://politics-os-data-2026/v1/raw/<DATE>/party_finance/.
Usage: python3 -I pipeline/fetch_party_finance.py OUT.json [--no-raw]
Needs: pypdf (use ~/anyagents/.venv/bin/python), gcloud for the raw copy.
"""
import io, json, os, re, subprocess, sys, urllib.request
from datetime import date

BASE = "https://www.soumu.go.jp"
YEARS = [  # (報告年, 官報の要旨ページ, 政党本部のPDF)
    ("令和6年", 2024, "/senkyo/seiji_s/kanpo/shikin/r05_yoshi_251128.html", "/main_content/001046234.pdf", "2025-11-28"),
    ("令和5年", 2023, "/senkyo/seiji_s/kanpo/shikin/r05_yoshi_241129.html", "/main_content/000982087.pdf", "2024-11-29"),
    ("令和4年", 2022, "/senkyo/seiji_s/kanpo/shikin/r04_yoshi_231124.html", "/main_content/000918206.pdf", "2023-11-24"),
]
BUCKET = "gs://politics-os-data-2026/v1/raw"
ACCOUNT_ARGS = [f"--account={os.environ['POS_GCS_ACCOUNT']}"] if os.environ.get("POS_GCS_ACCOUNT") else []  # gcloud account (default: the active one)
UA = "Mozilla/5.0 (politics-os research; public records)"

DIG = "÷øùúûüýþÿĀ"
NUMLINE = re.compile(r"^[%s][%só ]*$" % (DIG, DIG))
TAILNUM = re.compile(r"^(.*?\S)\s+([%s][%só ]*)$" % (DIG, DIG))
REP = "\u0e43\u0802\u0ce5\u0744\u0cd4"  # 報告年月日 (starts every party block; the line before it is the party name)
# Labels are written as escapes: the PDF's glyph strings contain invisible/odd code points that do not survive copy & paste.
H_IN = "\u030f \u0e8a\u0ce5\u0929\u0cd6\u0377\u0cba\u0f01"   # ３ 本年収入の内訳 (glued to the first item)
H_OUT = "\u0310 \u08a7\u095a\u0377\u0cba\u0f01"                # ４ 支出の内訳
H_DON = "\u0311"                                                   # ５ 寄附の内訳 (donor names: not read)
IN_TOTAL = {"\u030d \u0929\u0cd6\u0aef\u05b9": "total",        # １ 収入総額
            "\u0ab2\u0ce5\u0701\u04fd\u05b9": "carry",         # 前年繰越額
            "\u0e8a\u0ce5\u0929\u0cd6\u05b9": "income"}        # 本年収入額
OUT_TOTAL = {"\u030e \u08a7\u095a\u0aef\u05b9": "spend"}       # ２ 支出総額
FEES = "\u0778\u0a13\u0377\u0c58"                                # 個人の党費・会費（N人） (prefix)
INCOME = {  # top-level income categories (their sum must equal 本年収入額)
    "\u062f\u0ddf": "donations",                                   # 寄附
    "\u08bd\u08b4\u0614\u063b\u0377\u0d43\u07e6\u0366\u0377\u0b1e\u0377\u06c0\u08c4\u0374\u0391\u0394\u0929\u0cd6": "business",  # 機関紙誌の発行その他の事業による収入
    "\u0906\u0cd6\u06da": "loans",                                # 借入金
    "\u0e8a\u0de6\u0ea2\u0378\u08a7\u0de6\u0354\u0392\u0699\u0f29\u035e\u0395\u0368\u07a6\u0dc7\u06da\u0374\u070e\u0394\u0929\u0cd6": "transfers",  # 本部又は支部から供与された交付金に係る収入
    "\u0366\u0377\u0b1e\u0377\u0929\u0cd6": "other",            # その他の収入
}
INCOME_SUB = {"\u0778\u0a13\u0dfc": "don_person",                 # 個人分
              "\u0b82\u0b2e\u0dfc": "don_corp",                   # 団体分（法人その他の団体）
              "\u0a53\u08cf\u0b82\u0b2e\u0dfc": "don_political",  # 政治団体分
              "\u0a53\u0c58\u0c97\u0eca\u062f\u0ddf": "don_anon",  # 政党匿名寄附
              "\u0a53\u0c58\u07a6\u0dc7\u06da": "subsidy"}      # 政党交付金
SPEND = {"\u0726\u09d7\u0726\u0d85": "running",                  # 経常経費
         "\u0a53\u05c6\u08cf\u0c88\u0d85": "political"}         # 政治活動費
SPEND_SUB = {  # parts of 政治活動費 (sum must equal it)
    "\u0aca\u09eb\u05c6\u0c88\u0d85": "organization",           # 組織活動費
    "\u0aac\u070e\u0614\u068d\u0d85": "election",               # 選挙関係費
    "\u08bd\u08b4\u0614\u063b\u0377\u0d43\u07e6\u0366\u0377\u0b1e\u0377\u06c0\u08c4\u0d85": "business_cost",  # 機関紙誌の発行その他の事業費
    "\u0bd0\u0680\u075a\u082a\u0d85": "research",               # 調査研究費
    "\u062f\u0ddf\u027e\u07a6\u0dc7\u06da": "grants",          # 寄附・交付金
    "\u0366\u0377\u0b1e\u0377\u0726\u0d85": "other_cost",       # その他の経費
}
RUNNING_SUB = {"\u0a13\u0745\u0d85": "staff", "\u07ab\u0ce4\u0a2b\u0d85": "utilities",
               "\u0d8b\u0dbc\u027e\u09ab\u0ee3\u0dbc\u0d85": "supplies", "\u08c4\u0ebf\u0974\u0d85": "office"}
TO_BRANCH = "\u02a4\u034f\u036a\u0e8a\u0de6\u0ea2\u0378\u08a7\u0de6\u0374\u0b30\u0360\u036f\u0699\u0f29\u0360\u0368\u07a6\u0dc7\u06da\u0374\u070e\u0394\u08a7\u095a\u02a5"  # （うち本部又は支部に対して供与した交付金に係る支出）


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def party_list(index_path, pdf_path):
    """Party names in page order, from the 官報 index page (authoritative names)."""
    b = get(BASE + index_path)
    for enc in ("utf-8", "cp932"):
        try:
            s = b.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    names = []
    for h, t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', s, re.S):
        if h.split("#")[0] == pdf_path:
            names.append(re.sub("<[^>]+>", "", t).strip())
    return names


def num(s):
    return int("".join(str(DIG.index(c)) for c in s if c in DIG))


PUA = re.compile("[\ue000-\uf8ff]")


def is_page_header(line):
    """官報 running header (e.g. 令和7年11月28日 金曜日 官報（号外第N号）) — it would glue onto the next label."""
    return "\u0fa9\u0fe8" in line and "\u0744" in line and "\u0cd4" in line and "\u07f8" in line and "\u058e" in line


def tokens(pdf_bytes):
    import pypdf
    out = []
    for page in pypdf.PdfReader(io.BytesIO(pdf_bytes)).pages:
        for line in (page.extract_text() or "").splitlines():
            if is_page_header(line):
                continue
            line = PUA.sub("", line).strip()  # page numbers are private-use glyphs glued to the first label of a page
            if not line:
                continue
            m = TAILNUM.match(line)
            if NUMLINE.match(line):
                out.append(("N", num(line)))
            elif m and NUMLINE.match(m.group(2)):
                out.append(("L", m.group(1)))
                out.append(("N", num(m.group(2))))
            else:
                out.append(("L", line))
    return out


def blocks(tok, n):
    """First n party blocks: list of (label, value) pairs; wrapped labels are joined."""
    starts = [i for i, (k, v) in enumerate(tok) if k == "L" and v.startswith(REP)]
    res = []
    for j, s in enumerate(starts[:n]):
        end = starts[j + 1] - 1 if j + 1 < len(starts) else len(tok)  # line before next REP = next name
        pairs, label = [], []
        for k, v in tok[s + 1:end]:
            if k == "L":
                label.append(v)
            else:
                pairs.append(("".join(label), v))
                label = []
        res.append(pairs)
    return res


def parse(pairs):
    sec, d, unknown_in, unknown_out = None, {}, [], []
    for lab, v in pairs:
        if lab.startswith(H_IN):
            sec, lab = "in", lab[len(H_IN):]
        elif lab.startswith(H_OUT):
            sec, lab = "out", lab[len(H_OUT):]
        elif lab.startswith(H_DON):
            break  # 寄附の内訳 (donor names): not read
        if lab in IN_TOTAL:
            d[IN_TOTAL[lab]] = v
        elif lab in OUT_TOTAL:
            d[OUT_TOTAL[lab]] = v
        elif sec == "in":
            key = "fees" if lab.startswith(FEES) else INCOME.get(lab)
            if key:
                d[key] = d.get(key, 0) + v
            elif lab in INCOME_SUB:
                d[INCOME_SUB[lab]] = d.get(INCOME_SUB[lab], 0) + v
        elif sec == "out":
            if lab in SPEND:
                d[SPEND[lab]] = v
            elif lab in SPEND_SUB:
                d[SPEND_SUB[lab]] = d.get(SPEND_SUB[lab], 0) + v
            elif lab in RUNNING_SUB:
                d[RUNNING_SUB[lab]] = v
            elif lab == TO_BRANCH:
                d["to_branch"] = v
    return d


def check(d):
    errs = []
    if d.get("total") != d.get("carry", 0) + d.get("income", -1):
        errs.append("収入総額≠繰越+本年収入")
    if d.get("income") != sum(d.get(k, 0) for k in ("fees", *INCOME.values())):
        errs.append(f"本年収入≠内訳の合計（差 {d.get('income', 0) - sum(d.get(k, 0) for k in ("fees", *INCOME.values())):,}）")
    if d.get("spend") != d.get("running", 0) + d.get("political", 0):
        errs.append(f"支出総額≠経常経費+政治活動費（差 {d.get('spend', 0) - d.get('running', 0) - d.get('political', 0):,}）")
    if d.get("political", 0) != sum(d.get(k, 0) for k in SPEND_SUB.values()):
        errs.append(f"政治活動費≠内訳の合計（差 {d.get('political', 0) - sum(d.get(k, 0) for k in SPEND_SUB.values()):,}）")
    if d.get("donations", 0) and d.get("donations") != sum(d.get(k, 0) for k in ("don_person", "don_corp", "don_political", "don_anon")):
        errs.append("寄附≠個人分+法人等+政治団体分+匿名")
    return errs


def main():
    out_path = sys.argv[1]
    raw = "--no-raw" not in sys.argv
    today = date.today().strftime("%Y%m%d")
    years, failed = [], []
    for label, y, idx, pdf, pub in YEARS:
        names = party_list(idx, pdf)
        b = get(BASE + pdf)
        if raw:
            dest = f"{BUCKET}/{today}/party_finance/{pdf.rsplit('/', 1)[1]}"
            subprocess.run(["gcloud", "storage", "cp", "-", dest, *ACCOUNT_ARGS, "--quiet"], input=b, check=True)
        bl = blocks(tokens(b), len(names))
        if len(bl) != len(names):
            raise SystemExit(f"{label}: {len(bl)} blocks for {len(names)} parties")
        parties = []
        for name, pairs in zip(names, bl):
            d = parse(pairs)
            errs = check(d)
            if errs:
                failed.append((label, name, errs))
                print("NG", label, name, errs, file=sys.stderr)
                continue
            parties.append({"name": name, **d})
            print("ok", label, name, f"収入{d['income']:,} 支出{d['spend']:,} 交付金{d.get('subsidy', 0):,}", file=sys.stderr)
        years.append({"year": y, "label": f"{label}分", "published": pub,
                      "source": {"title": f"総務省 政治資金収支報告書の要旨（{label}分・官報）", "url": BASE + idx, "pdf": BASE + pdf},
                      "parties": parties})
    out = {"fetchedAt": date.today().isoformat(), "unit": "円", "scope": "政党本部（総務大臣届出分）。政党支部・政治資金団体・議員の団体は含まない。",
           "checks": ["収入総額＝前年からの繰越額＋本年の収入額", "本年の収入額＝収入の項目の合計", "支出総額＝経常経費＋政治活動費", "政治活動費＝その内訳の合計", "寄附＝個人分＋法人その他の団体分＋政治団体分＋政党匿名寄附"],
           "failed": [{"year": a, "name": b, "errors": c} for a, b, c in failed], "years": years}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}: {sum(len(y['parties']) for y in years)} party-years, failed {len(failed)}", file=sys.stderr)


if __name__ == "__main__":
    main()
