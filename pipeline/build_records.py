"""Attach bills / Councillors votes / political-org records / photos / party pledges to the site data.

Run after build.py (which writes data/members.json from scratch).
Usage: python3 -I build_records.py PIPELINE_DIR DATA_DIR PHOTO_DIR
Reads:  bills_shu.json, bills_shu_old.json, san_bills.json, san_votes_all.json,
        transparency.json, party_pledges.json, photos.json, roster.json
Writes: DATA_DIR/members.json (adds summary counts), DATA_DIR/records.json (lazy-loaded details),
        DATA_DIR/pledges.json, and updates DATA_DIR/meta.json (coverage notes).
Matching is by (house, exact name); same-name members within one house are skipped.
"""
import collections
import json
import re
import sys
from pathlib import Path

norm = lambda s: re.sub(r"[\s　]", "", s or "").removesuffix("君")  # noqa: E731


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip(" ／")


def last_part(s):
    return re.sub(r".*／\s*", "", s or "").strip()


def bill_status(b):
    """Coarse stage of a bill from its official progress fields. Never infers a rejection."""
    shu, san = last_part(b.get("shuResult")), last_part(b.get("sanResult")) or clean(b.get("sanResult"))
    if clean(b.get("promulgated")):
        return "成立"
    if "否決" in (shu + san):
        return "否決"
    if b["kind"] in ("決議", "規則", "規程") and shu in ("可決", "議決", "修正"):
        return "可決"
    if shu in ("可決", "修正") or san in ("可決", "修正"):
        return "一院で可決"
    return "未成立"


def last_official(b):
    """The latest progress text exactly as the official page shows it (e.g. 閉会中審査). Not re-interpreted."""
    for f in ("sanResult", "shuResult", "shuCommitteeResult"):
        t = last_part(b.get(f))
        if t:
            return t
    return clean(b.get("continued")) or "議決の記録なし"


GOV = ("大臣", "副大臣", "政務官", "長官", "副長官", "総理")


def speech_role(pos):
    """Coarse role from the minutes' speakerPosition. Committee chairs and bill submitters have no position
    in the API (it is empty), so they cannot be told apart from questioners and stay in the last group."""
    pos = pos or ""
    if any(k in pos for k in GOV):
        return "政府側の答弁（大臣など）"
    if "議長" in pos:
        return "議長・副議長として"
    return "それ以外（質問・討論、委員長の進行、提出者の答弁など）"


def session_of(url):
    """'https://kokkai.ndl.go.jp/txt/122105254X02020260526/12' -> '221' (issueID = 1 + session(3) + ...)."""
    m = re.search(r"/txt/1(\d{3})", url or "")
    return m.group(1) if m else None


def short_role(pos):
    """'経済産業大臣・内閣府特命担当大臣（…）' -> '経済産業大臣'."""
    return (pos or "").split("・")[0].split("（")[0]


def months_between(frm, until):
    y, m = int(frm[:4]), int(frm[5:7])
    out = []
    while f"{y:04d}-{m:02d}" <= until[:7]:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def build_exchanges(pipe, members, url_pos):
    """meetings.jsonl (speaker order per meeting) -> who answered whom.
    Chair = speaker of the first speech (order 1). For a member's non-government speech, the next speaker who is
    neither the member nor the chair is the answerer. For a member's government speech, the previous such speaker is
    the questioner. Labels come from the minutes' position of that exact speech when known."""
    f = pipe / "meetings.jsonl"
    if not f.exists():
        return {}
    name_to_id = collections.defaultdict(set)
    for m in members:
        if m["activityStatus"] != "homonym":
            name_to_id[(m.get("speakerQuery") or m["name"])].add(m["id"])
    kaiha = {m["id"]: m["kaihaName"] for m in members}
    uniq = {k: next(iter(v)) for k, v in name_to_id.items() if len(v) == 1}

    def label(name, url):
        pos = url_pos.get(url)
        if pos and any(k in pos for k in GOV):
            return short_role(pos)
        if name in uniq:
            return f"議員（{kaiha[uniq[name]]}）"
        return "議員以外（政府参考人など）"

    acc = collections.defaultdict(lambda: {"asked": collections.defaultdict(list), "answered": collections.defaultdict(list)})
    for line in f.read_text(encoding="utf-8").splitlines():
        mt = json.loads(line)
        seq = [x for x in sorted(mt["speeches"], key=lambda x: x[0]) if x[0] > 0]
        if len(seq) < 3:
            continue
        chair = seq[0][1]
        for i, (_, spk, url) in enumerate(seq):
            mid = uniq.get(spk)
            if not mid or spk == chair:
                continue
            gov = any(k in (url_pos.get(url) or "") for k in GOV)
            rng = range(i - 1, -1, -1) if gov else range(i + 1, len(seq))
            for j in rng:
                o_spk, o_url = seq[j][1], seq[j][2]
                if o_spk in (spk, chair):
                    continue
                key = "answered" if gov else "asked"
                acc[mid][key][mt["issueID"]].append((o_spk, label(o_spk, o_url), url))
                break
    meta = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        mt = json.loads(line)
        meta[mt["issueID"]] = (mt["date"], mt["house"], mt["meeting"])
    out = {}
    for mid, kinds in acc.items():
        res = {}
        for key, per in kinds.items():
            if not per:
                continue
            partners = collections.Counter()
            plabel = {}
            for rows in per.values():
                for n, lab, _ in rows:
                    partners[n] += 1
                    plabel[n] = lab
            recent = sorted(per.items(), key=lambda kv: (meta[kv[0]][0], kv[0]), reverse=True)[:10]
            res[key] = {
                "pairs": sum(len(v) for v in per.values()), "meetings": len(per),
                "partners": [[n, plabel[n], c] for n, c in partners.most_common(8)],
                "recent": [[*meta[iid], len(rows),
                            [[n, plabel[n], c] for n, c in collections.Counter(r[0] for r in rows).most_common(3)], rows[0][2]]
                           for iid, rows in recent],
            }
        out[mid] = res
    return out


def session_spans(pipe):
    """Per session: first/last meeting date and number of distinct meeting days in meetings.jsonl (counting window)."""
    f = pipe / "meetings.jsonl"
    if not f.exists():
        return {}
    days = collections.defaultdict(set)
    for line in f.read_text(encoding="utf-8").splitlines():
        mt = json.loads(line)
        sess = mt["issueID"][1:4]
        days[sess].add(mt["date"])
    return {s: {"from": min(d), "until": max(d), "days": len(d)} for s, d in sorted(days.items())}


CHAIR_LABEL = "委員長などとして議事の進行（その会議の最初の発言者）"


def meeting_chairs(pipe):
    """issueID -> speaker of the first speech. Checked against the minutes text: the first speaker is the presiding
    member (委員長 / 委員長代理 / 年長委員 before the chair election). 25/25 sampled meetings, 2026-11-02."""
    f = pipe / "meetings.jsonl"
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            mt = json.loads(line)
            seq = sorted(x for x in mt["speeches"] if x[0] > 0)
            if seq:
                out[mt["issueID"]] = seq[0][1]
    return out


def issue_of(url):
    m = re.search(r"/txt/([0-9A-Z]+)", url or "")
    return m.group(1) if m else None


def build_x_reactions(pipe):
    """x_reactions.jsonl (fetch_x_reactions.py) -> {id: summary}. Reference only, never part of a score.
    Post links are kept only when the status ID appears in that conversation's search citations; no post text is kept."""
    f = pipe / "x_reactions.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        res = r.get("result") or {}
        if res.get("parse_error"):
            continue
        cited = {m.group(1) for u in r.get("citations", []) for m in [re.search(r"status/(\d+)", u)] if m}
        themes, counts, dropped = {}, {}, 0
        for k in ("positive", "neutral", "negative"):
            themes[k] = []
            for t in res.get(k, []) or []:
                ids = [m.group(1) for u in t.get("example_urls", []) for m in [re.search(r"status/(\d+)", u)] if m]
                keep = [i for i in dict.fromkeys(ids) if i in cited]
                dropped += len(ids) - len(keep)
                themes[k].append({"theme": t.get("theme", ""), "count": int(t.get("count") or 0),
                                  "links": [f"https://x.com/i/status/{i}" for i in keep]})
            counts[k] = sum(t["count"] for t in themes[k])
        out[r["id"]] = {"from": r["from"], "until": r["until"], "model": r["model"], "fetchedAt": r["fetchedAt"],
                        "reviewed": int(res.get("posts_reviewed") or 0), "counts": counts, "themes": themes,
                        "topics": res.get("main_topics", [])[:5], "caveats": res.get("caveats", [])[:3],
                        "droppedLinks": dropped}
    return out


def build_personal_pledges(pipe, members):
    """pledges_personal_raw.jsonl (extract_pledges.py) -> ({id: detail}, {id: summary}). Personal pledges from election bulletins.
    衆 = 第51回 (2026). 参 = the most recent of 第27回 (2025) / 第26回 (2022) in which the member's own block was found
    (a member re-elected in 2025 is shown with the 2025 bulletin even if the roster's term-end looks older).
    No score: counts only (PHILOSOPHY 6-3). Members without a personal entry get a reason, never 0."""
    f = pipe / "pledges_personal_raw.jsonl"
    if not f.exists():
        return {}, {}
    src = load(Path(__file__).parent / "config" / "kouhou_sources.json")
    status = {(e["key"], p["pref"]): p.get("status") for e in src["elections"] for p in e["prefectures"]}
    meta_el = {e["key"]: {"name": e["election"], "date": e["date"]} for e in src["elections"]}
    best = {}
    term_of = {m["id"]: (m.get("termEnd") or "") for m in members}
    read_ok = set()  # (election, pref) with a bulletin of the right election actually read
    # 4 checks per promise (score_pledges.py): t 何を / a どうする / dl いつまでに / ms どこまで
    sf = pipe / "pledges_spec.jsonl"
    spec = {r["q"]: r for r in map(json.loads, sf.read_text(encoding="utf-8").splitlines())} if sf.exists() else {}
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if "比例" in r["label"]:
            continue  # PR bulletins are party pages: their text is the party's pledge, never an individual's (PHILOSOPHY)
        if r["election"].startswith("san") and r["candidates"]:
            # a "2022" file that names only 2025 winners (or vice versa) is the other election's bulletin: ignore it
            want = "令和10" if r["election"] == "san2022" else "令和13"
            if not any(term_of.get(c["memberId"], "").startswith(want) for c in r["candidates"]):
                continue
        read_ok.add((r["election"], r["pref"]))
        for c in r["candidates"]:
            items = []
            for x in c.get("pledges") or []:
                q = (x.get("quote") or "").strip()
                if q and q not in {i["q"] for i in items}:
                    items.append({"q": q, "k": "実績" if x.get("kind") == "実績" else "公約", "area": (x.get("area") or "").strip(), "v": bool(x.get("verifiable")),
                                  "d": bool(x.get("deadline")), "c": x.get("criterion") if x.get("criterion") in (1, 2, 3, 4) else None})
            if not items:
                continue
            k = (c["memberId"], r["election"])
            if k not in best or len(items) > len(best[k]["items"]):
                best[k] = {"election": r["election"], "electionName": r["electionName"], "date": meta_el[r["election"]]["date"],
                           "pref": r["pref"], "label": r["label"], "url": r["url"], "page": c.get("page"),
                           "name": c.get("name"), "party": c.get("party"), "items": items[:15], "model": r["model"]}
    detail, summary = {}, {}
    for m in members:
        if m["house"] == "衆議院":
            el = "shu2026"
        else:
            el = "san2025" if (m.get("termEnd") or "").startswith("令和13") else "san2022"
        found = [best[(m["id"], k)] for k in ("san2025", "san2022", "shu2026") if (m["id"], k) in best
                 and (k == "shu2026") == (m["house"] == "衆議院")]
        if m["house"] == "参議院" and m["electionType"] == "比例":
            found = []  # a 参 PR member found in a district bulletin ran there in another election (e.g. 2022), not for this seat
        d = found[0] if found else None
        if d:
            el = d["election"]
            detail[m["id"]] = d
            pl = [i for i in d["items"] if i["k"] == "公約"]  # promises only; past achievements are counted apart
            for i in pl:
                g = spec.get(i["q"])
                if g:
                    i.update({k: bool(g[k]) for k in ("t", "a", "dl", "ms")})
            summary[m["id"]] = {"n": len(pl), "v": sum(i["v"] for i in pl), "d": sum(i["d"] for i in pl),
                                "a": len(d["items"]) - len(pl), "el": meta_el[el]["name"]}
            graded = [i for i in pl if "t" in i]
            if spec and len(graded) == len(pl):
                # 公約の具体性 = mean points (0-4) / 4 x 100; fewer than 3 promises -> no score (counts only)
                pts = [i["t"] + i["a"] + i["dl"] + i["ms"] for i in pl]
                summary[m["id"]]["ck"] = {k: sum(i[k] for i in pl) for k in ("t", "a", "dl", "ms")}  # own key: "a" above = achievements
                summary[m["id"]]["spec"] = round(sum(pts) / len(pts) / 4 * 100) if len(pl) >= 3 else None
            continue
        if m["electionType"] == "比例":
            why = ("比例代表で当選。小選挙区の公報に本人の欄が見つからない（比例単独の候補者には個人の公報がない）" if m["house"] == "衆議院"
                   else "比例代表で当選（参議院の比例の公報は政党ごとで、個人の公約欄がない）")
        else:
            prefs = m.get("prefectures") or []
            if prefs and not any((el, p) in read_ok for p in prefs):
                if all(status.get((el, p)) in ("no_pdf", "page_not_found") for p in prefs):
                    why = "選挙公報の公開が終了しているため未収録（" + "・".join(prefs) + "の選挙管理委員会）"
                else:
                    why = "選挙管理委員会のサイトから公報を取得できず未収録（" + "・".join(prefs) + "）"
            else:
                why = "選挙公報から本人の欄を読み取れず未収録（補欠選挙での当選・読み取りの誤りなど）"
        summary[m["id"]] = {"n": None, "why": why, "el": meta_el[el]["name"]}
    return detail, summary


def build_public_cost():
    """config/public_cost.json (衆議院予算の主要5項目, 百万円) -> per-seat yen and shares. Averages, not anyone's income."""
    c = load(Path(__file__).parent / "config" / "public_cost.json")
    seats = c["seats"]
    total = sum(i["budgetMillion"] for i in c["items"])
    for i in c["items"]:
        i["perSeatYen"] = round(i["budgetMillion"] * 1_000_000 / seats)
        i["share"] = round(i["budgetMillion"] / total * 100, 1)
        for part in i.get("parts", []):
            part["perSeatYen"] = round(part["budgetMillion"] * 1_000_000 / seats)
    c["totalMillion"] = total
    c["perSeatYen"] = round(total * 1_000_000 / seats)
    assert abs(sum(i["perSeatYen"] for i in c["items"]) - c["perSeatYen"]) < 10
    return c


def build_speeches(pipe, members):
    """speeches*.jsonl (fetch_speeches.py) -> {member id: {n, expected, roles, meetings, recent}}."""
    files = sorted(pipe.glob("speeches*.jsonl"))
    if not files:
        return None
    rows = {}
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[(r["house"], r["profileId"])] = r
    out = {}
    url_pos = {x["url"]: x["position"] for r in rows.values() for x in r["records"]}
    months = months_between("2025-11", "2026-10")
    exchanges = build_exchanges(pipe, members, url_pos)
    chairs = meeting_chairs(pipe)
    for m in members:
        r = rows.get((m["house"], m["id"][1:]))
        if not r or m["activityStatus"] == "homonym":
            continue
        recs = r["records"]
        qname = m.get("speakerQuery") or m["name"]
        role_of = lambda x: CHAIR_LABEL if (speech_role(x["position"]).startswith("それ以外")  # noqa: E731
                                           and chairs.get(issue_of(x["url"])) == qname) else speech_role(x["position"])
        roles = collections.Counter(role_of(x) for x in recs)
        meetings = collections.Counter(f'{x["house"]} {x["meeting"]}' for x in recs)
        recent = sorted(recs, key=lambda x: (x["date"], x["url"]), reverse=True)[:10]
        chaired = [x for x in recs if role_of(x) == CHAIR_LABEL]
        chair_meetings = {(x["date"], x["house"], x["meeting"], x["issue"]) for x in chaired}
        # meetings chaired by this member are left out of the activity measure (presiding is not asking)
        rest = [x for x in recs if role_of(x).startswith("それ以外")]
        rest_meetings = {(x["date"], x["house"], x["meeting"], x["issue"], session_of(x["url"])) for x in rest}
        out[m["id"]] = {
            "n": len(recs), "expected": r["expected"], "restN": len(rest), "restMeetings": len(rest_meetings),
            "chairN": len(chaired), "chairMeetings": len(chair_meetings),
            "chairMain": (lambda c: {"name": c[0][0], "count": c[0][1]} if c else None)(
                collections.Counter(f"{k[1]} {k[2]}" for k in chair_meetings).most_common(1)),
            "months": months,
            "monthlyMeet": [len({k for k in rest_meetings if k[0][:7] == mo}) for mo in months],
            "monthlyGov": [sum(1 for x in recs if x["date"][:7] == mo and speech_role(x["position"]).startswith("政府側")) for mo in months],
            "bySession": {sess: [len({k for k in rest_meetings if k[4] == sess}),
                                 sum(1 for x in recs if session_of(x["url"]) == sess and speech_role(x["position"]).startswith("政府側"))]
                          for sess in sorted({session_of(x["url"]) for x in recs} - {None})},
            "mainMeeting": (lambda c: {"name": c[0][0], "count": c[0][1]} if c else None)(
                collections.Counter(f"{k[1]} {k[2]}" for k in rest_meetings).most_common(1)),
            "role": (lambda g: {"label": short_role(g["position"]), "full": g["position"], "date": g["date"]} if g else None)(
                max((x for x in recs if speech_role(x["position"]).startswith("政府側")), key=lambda x: x["date"], default=None)),
            "ex": exchanges.get(m["id"], {}),
            "roles": roles.most_common(),
            "meetings": meetings.most_common(12),
            "meetingCount": len(meetings),
            "recent": [[x["date"], x["house"], x["meeting"], x["position"] or "", x["snippet"], x["url"]] for x in recent],
        }
    return out


def main():
    pipe, data, photo_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    members = load(data / "members.json")
    meta = load(data / "meta.json")
    by_house = collections.defaultdict(list)
    for m in members:
        by_house[(m["house"], norm(m["name"]))].append(m)
        if m.get("legalName"):
            by_house[(m["house"], norm(m["legalName"]))].append(m)

    def find(house, name):
        hit = {x["id"]: x for x in by_house.get((house, norm(name)), [])}
        return next(iter(hit.values())) if len(hit) == 1 else None

    # lead/co/sup = member-initiated LAW bills (衆法・参法). chair = committee bills credited to the chair by name
    # (委員会提出: 提出者欄が「○○委員長」), kept apart from personal initiative. other = 決議・規則・規程.
    rec = collections.defaultdict(lambda: {"lead": [], "co": [], "sup": [], "chair": [], "other": []})

    # ---- bills ----
    bills = []
    # The Representatives' DB has one progress page per session a bill was listed in (carried-over bills
    # repeat, up to 28 times). Keep one row per bill = (kind, submitted session, number), from the latest listing,
    # which carries the final status.
    latest = {}
    for b in load(pipe / "bills_shu_old.json") + load(pipe / "bills_shu.json"):
        k = (b["kind"], b["session"], b["number"])
        if k not in latest or int(b["listedIn"]) > int(latest[k]["listedIn"]):
            latest[k] = b
    shu_bills = list(latest.values())
    san_bills = load(pipe / "san_bills.json")
    san_keys = {(b["session"], b["number"]) for b in san_bills}
    for b in shu_bills:
        if b["kind"] == "参法" and (b["session"], b["number"]) in san_keys:
            continue  # same 参法 is taken from the Councillors page (which names the lead proposer)
        if b["kind"] not in ("衆法", "参法", "決議", "規則", "規程") and not b["submitters"]:
            continue  # cabinet bills, budgets, treaties etc. are not member actions
        i = len(bills)
        committee = "委員長" in (b.get("submitterLabel") or "")
        law = b["kind"] in ("衆法", "参法")
        bills.append({"kind": b["kind"], "session": b["session"], "number": b["number"], "title": b["title"],
                      "status": bill_status(b), "last": last_official(b), "url": b["url"], "kaiha": b.get("submitterKaiha") or [],
                      "listedIn": b["listedIn"], "committee": b.get("submitterLabel") if committee else None})
        house = "参議院" if b["kind"] == "参法" else "衆議院"
        if committee:
            m = find(house, b["submitters"][0]) if b["submitters"] else None
            if m:
                rec[m["id"]]["chair"].append(i)
            continue
        for j, n in enumerate(b["submitters"]):
            m = find(house, n)
            if m:
                rec[m["id"]][("lead" if j == 0 else "co") if law else "other"].append(i)
        if not law:
            continue
        for n in b["supporters"]:
            m = find(house, n)
            if m:
                rec[m["id"]]["sup"].append(i)
    for b in san_bills:
        i = len(bills)
        bills.append({"kind": "参法", "session": b["session"], "number": b["number"], "title": b["title"],
                      "status": bill_status(b), "last": last_official(b), "url": b["url"], "kaiha": [], "leadOnly": True,
                      "listedIn": b["listedIn"]})
        m = find("参議院", b["lead"]) if b["lead"] else None
        if m:
            rec[m["id"]]["lead"].append(i)

    # ---- Councillors individual votes ----
    sv = load(pipe / "san_votes_all.json")
    ind = [v for v in sv["votes"] if v["members"]]
    standing = [v for v in sv["votes"] if not v["members"]]
    votes = [{"session": v["session"], "date": v["date"], "title": v["title"], "url": v["url"],
              "yes": v["yes"], "no": v["no"]} for v in ind]
    code = {"賛成": "1", "反対": "0", "投票なし": "-"}
    vote_str = {}
    for m in members:
        if m["house"] != "参議院":
            continue
        s = "".join(code[v["members"][k]] if (k := next((n for n in v["members"] if norm(n) in
                    {norm(m["name"]), norm(m.get("legalName"))}), None)) else "." for v in ind)
        vote_str[m["id"]] = s

    # ---- transparency / photos / pledges ----
    tr = load(pipe / "transparency.json")
    photos = load(pipe / "photos.json")
    pledges = load(pipe / "party_pledges.json")
    party_of = {}
    for p in pledges["parties"]:
        for f in p["factions"]:
            party_of.setdefault(f, []).append(p["party"])

    speeches = build_speeches(pipe, members)
    speech_sum = {}
    for k, v in (speeches or {}).items():
        roles = dict(v["roles"])
        speech_sum[k] = {"rest": v["restN"], "meet": v["restMeetings"], "gov": roles.get("政府側の答弁（大臣など）", 0),
                         "presiding": roles.get("議長・副議長として", 0), "chair": v["chairMeetings"], "chairN": v["chairN"],
                         "chairMain": v["chairMain"]}
    pp_detail, pp_sum = build_personal_pledges(pipe, members)
    if pp_sum:
        (data / "pledges_personal.json").write_text(json.dumps(pp_detail, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("personal pledges", len(pp_detail), "/", len(members), collections.Counter(v.get("why", "ok") for v in pp_sum.values()).most_common())
    xr = build_x_reactions(pipe)
    (data / "x_reactions.json").write_text(json.dumps(xr, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("x reactions", len(xr), "links dropped (not in citations)", sum(v["droppedLinks"] for v in xr.values()))
    lsf = pipe / "last_speech.json"
    last_speech = {k: v for k, v in load(lsf).items() if v} if lsf.exists() else {}
    coal = load(Path(__file__).parent / "config" / "coalition.json")
    cf = pipe / "cabinet.json"
    cabinet = load(cf) if cf.exists() else {"people": [], "asOf": {}, "source": None}
    by_kana = collections.defaultdict(list)
    for mm in members:
        by_kana[(mm["house"], re.sub(r"\s", "", mm["kana"]))].append(mm)
    gov_by_id, cab_rows = {}, []
    for c in cabinet["people"]:
        mm = find(c["house"], c["name"]) if c["house"] and c["name"] else None
        if mm is None and c["house"] and len(by_kana.get((c["house"], c["kana"]), [])) == 1:
            mm = by_kana[(c["house"], c["kana"])][0]
        if mm and not c["former"]:
            gov_by_id[mm["id"]] = c
        cab_rows.append({**c, "memberId": mm["id"] if mm else None, "display": mm["name"] if mm else (c["name"] or c["kana"])})
    print("cabinet", len(cabinet["people"]), "matched", sum(1 for r in cab_rows if r["memberId"]),
          "unmatched", [(r["posts"][0], r["display"], r["house"]) for r in cab_rows if not r["memberId"]])
    qf = pipe / "questions.json"
    questions = load(qf) if qf.exists() else []
    qidx = collections.defaultdict(list)
    q_unmatched = []
    for qi, q in enumerate(questions):
        for n in q["submitters"]:
            mm = find(q["house"], n)
            if mm:
                qidx[mm["id"]].append(qi)
            else:
                q_unmatched.append((q["house"], q["session"], q["number"], n))

    out_members = {}
    for m in members:
        r = rec.get(m["id"], {"lead": [], "co": [], "sup": [], "chair": [], "other": []})
        m["bills"] = {
            "lead": len(r["lead"]), "co": len(r["co"]), "sup": len(r["sup"]),
            # result = enacted LAW bills this member submitted (lead or co-submitter, counted once).
            # The Councillors' pages list only the lead proposer, so for 参議院 this is lead-only (stated on screen).
            "passed": len({i for i in r["lead"] + r["co"] if bills[i]["status"] == "成立"}),
            "leadPassed": sum(1 for i in r["lead"] if bills[i]["status"] == "成立"),
            "coPassed": sum(1 for i in r["co"] if bills[i]["status"] == "成立"),
            "chair": len(r["chair"]), "other": len(r["other"]),
            # 超党派: 衆法 submitted by 2+ factions (the Councillors' pages don't list factions -> null for 参)
            "cross": sum(1 for i in r["lead"] + r["co"] if len(bills[i]["kaiha"]) >= 2) if m["house"] == "衆議院" else None,
        }
        m["q"] = len(qidx.get(m["id"], []))
        key = f'{m["house"]}|{m["kaiha"]}'
        m["side"] = "与党" if key in coal["ruling"] else "不明" if key in coal["unknown"] else "野党"
        t = str(m.get("terms") or "")
        n = int(re.match(r"\d+", t).group()) if m["house"] == "衆議院" and re.match(r"\d+", t) else None
        m["band"] = None if n is None else "当選1回" if n == 1 else "当選2〜3回" if n <= 3 else "当選4〜6回" if n <= 6 else "当選7回以上"
        sp = speech_sum.get(m["id"])
        m["sp"] = sp
        spv = (speeches or {}).get(m["id"], {})
        m["govMonths"] = sum(1 for v in spv.get("monthlyGov", []) if v > 0)
        role = spv.get("role")
        if m["id"] in xr:
            x = xr[m["id"]]
            m["xr"] = {**x["counts"], "reviewed": x["reviewed"], "from": x["from"], "until": x["until"]}
        if spv.get("mainMeeting"):
            m["mainMeeting"] = spv["mainMeeting"]
        g = gov_by_id.get(m["id"])
        if g:
            ans = spv.get("ex", {}).get("answered") or {}
            m["gov"] = {"group": g["group"], "posts": g["posts"], "former": g["former"],
                        "answers": m["sp"]["gov"] if m.get("sp") else None, "months": m["govMonths"],
                        "questioners": [[n, c] for n, _, c in ans.get("partners", [])[:3]]}
        if role:
            m["role"] = {"label": role["label"], "date": role["date"]}
        ls = last_speech.get(f'{m["house"]}|{m["id"][1:]}')
        if ls is not None:
            m["lastSpeech"] = ls
        if m["id"] in vote_str:
            s = vote_str[m["id"]]
            m["votes"] = {"n": sum(c != "." for c in s), "yes": s.count("1"), "no": s.count("0"), "none": s.count("-")}
        t = tr["members"].get(m["id"])
        k = (t or {}).get("kankeiDantai") or {}
        m["transp"] = {"listed": bool(k.get("listed")), "orgs": k.get("total"),
                       "reports": ((t or {}).get("shushiR6") or {}).get("reportCount")} if t else {"listed": False}
        ph = photos.get(m["id"])
        found = sorted(photo_dir.glob(f"{m['id']}.*")) if ph else []
        m["photo"] = found[0].suffix[1:] if found else False  # file extension, or False
        m["parties"] = party_of.get(f"{m['house']}|{m['kaiha']}", [])
        if m["id"] in pp_sum:
            m["pp"] = pp_sum[m["id"]]
        out_members[m["id"]] = {
            "b": {k2: v2 for k2, v2 in r.items() if v2},
            "v": vote_str.get(m["id"]),
            "t": t,
            "p": {k2: ph[k2] for k2 in ("license", "artist", "filePage")} if m["photo"] else None,
            "q": qidx.get(m["id"], []),
        }

    records = {"bills": bills, "votes": votes, "members": out_members,
               "questions": [{k: q[k] for k in ("house", "session", "number", "title", "url", "list")} for q in questions]}
    print("questions", len(questions), "matched to members", sum(len(v) for v in qidx.values()), "unmatched", len(q_unmatched), q_unmatched[:8])
    (data / "records.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (data / "members.json").write_text(json.dumps(members, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (data / "pledges.json").write_text(json.dumps(pledges, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if speeches is not None:
        (data / "speeches.json").write_text(json.dumps(speeches, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        mism = [k for k, v in speeches.items() if v["n"] != v["expected"]]
        print("speeches members", len(speeches), "count mismatch vs activity", len(mism), mism[:5])

    sessions = sorted({b["listedIn"] for b in bills}, key=int)  # sessions whose bill lists were collected
    meta["records"] = {
        "billSessions": [sessions[0], sessions[-1]],
        "billCount": len(bills),
        "voteSessions": sorted({v["session"] for v in ind}, key=int),
        "individualVotes": len(ind),
        "standingVotes": len(standing),
        "pdfOnlyVotes": len(sv["pdfOnly"]),
        "transparencyAsOf": tr["asOf"],
        "transparencySources": tr["sources"],
        "transparencyNotOnline": tr["sourcesNotOnline"],
        "pledgesAsOf": pledges["asOf"],
        "publicCost": build_public_cost(),
        "coalition": {"asOf": coal["asOf"], "sources": coal["sources"], "ruling": coal["ruling"], "unknown": coal["unknown"]},
        "questionSessions": sorted({q["session"] for q in questions}, key=int),
        "cabinet": {"asOf": cabinet.get("asOf"), "source": cabinet.get("source"), "people": cab_rows},
        "sessions": session_spans(pipe),
        "photos": sum(1 for m in members if m["photo"]),
        "notes": [
            f"法案は第{sessions[0]}〜{sessions[-1]}回国会の議案一覧に載った議員提出法案（衆法・参法）と決議案等（それ以前に提出され継続したものを含む）。内閣提出法案は議員の行動に数えない。",
            "衆法は衆議院の議案情報で提出者・賛成者の全員名を収録。参法は参議院の議案ページに筆頭発議者しか載らないため、共同発議者は未収録。",
            "委員会が提出した法案（提出者が「○○委員長」）は委員長個人の法律案に数えず「委員長として提出」と分ける。決議・規則・規程は法律案に数えない。結果は、提出者（筆頭・共同）として加わった法律案のうち成立した件数。参議院は議案ページ・提出法律案PDFとも筆頭発議者しか載っていないため筆頭のみ。",
            "行動の点数は、発言のあった会議の回数（同じ日の同じ会議は1回）。会議録の肩書が政府側（大臣・副大臣・政務官・長官など）と議長・副議長の発言は除く。委員長などとして議事を進めた会議（その会議の最初の発言者。会議録本文で抜き取り25/25件確認）も除き、回数を別に示す。",
            "「成立」は公布の記録があるもの。成立・否決のどちらの記録もない法案は「未成立」とし、公式ページ上の最後の状態（閉会中審査など）をそのまま併記する。否決とは扱わない。",
            "参議院の採決は押しボタン式投票の個人記録のみ数える。起立採決（全会一致など）は個人の賛否が残らないため除外。「投票なし」は欠席・棄権などで反対ではない。",
            "衆議院は個人の賛否が残らない採決が多いため、採決欄は表示しない。会派の態度から個人に賛否を付けない。",
            "氏名は院ごとの完全一致で紐付け。同じ院に同姓同名がいる場合は紐付けない。",
            "個人の公約は、いまの議席を得た選挙の選挙公報（都道府県選挙管理委員会が公開したPDF）から、Gemini（Google）で候補者ごとに原文の短い抜き出し（50字以内）を作ったもの。比例代表のみの当選者は個人の公報がない。公開が終わった県は未収録。点数にはしていない。",
            "写真はWikimedia Commons（ライセンス・作者を表示）。Wikidataで氏名と国会議員の経歴を照合済み。写真がない議員は頭文字を表示。",
        ],
    }
    (data / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    c = collections.Counter
    print("bills", len(bills), c(b["status"] for b in bills).most_common())
    print("members with own bills", sum(1 for m in members if m["bills"]["lead"] + m["bills"]["co"]),
          "with support", sum(1 for m in members if m["bills"]["sup"]))
    print("san members with votes", sum(1 for m in members if m.get("votes", {}).get("n")), "/",
          sum(1 for m in members if m["house"] == "参議院"))
    print("transparency listed", sum(1 for m in members if m["transp"]["listed"]), "photos", meta["records"]["photos"])
    print("no party pledges mapping", c(f"{m['house']}|{m['kaiha']}" for m in members if not m["parties"]))
    for f in ("records.json", "members.json", "pledges.json"):
        print(f, (data / f).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
