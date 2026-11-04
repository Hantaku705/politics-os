"""Build site data (members.json / meta.json) from roster.json + activity.jsonl.

Usage: python3 -I build.py ROSTER_JSON ACTIVITY_JSONL OUT_DIR FETCHED_DATE
"""
import collections
import json
import sys
from pathlib import Path

PREFS = ("北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 "
         "新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 "
         "和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 "
         "大分県 宮崎県 鹿児島県 沖縄県").split()
SHORT = {p if p == "北海道" else p[:-1]: p for p in PREFS}

KAIHA = {
    "衆議院": {"自民": "自由民主党・無所属の会", "中道": "中道", "維新": "日本維新の会", "国民": "国民民主党・無所属クラブ",
            "参政": "参政党", "みらい": "チームみらい", "共産": "日本共産党", "志士": "志士の会", "無": "無所属"},
    "参議院": {"自民": "自由民主党・無所属の会", "立憲": "立憲民主・無所属", "民主": "国民民主党・新緑風会", "公明": "公明党",
            "維新": "日本維新の会", "参政": "参政党", "共産": "日本共産党", "い党": "いのちの党", "保守": "日本保守党",
            "沖縄": "沖縄の風", "みら": "チームみらい・無所属の会", "社民": "社会民主党", "無所属": "各派に属しない議員",
            "碧水": "碧水会"},
}

SOURCES = {
    "衆議院": "https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/1giin.htm",
    "参議院": "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/current/giin.htm",
    "衆議院会派": "https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/shiryo/kaiha_m.htm",
    "参議院会派": "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/222/giinsu.htm",
    "会議録": "https://kokkai.ndl.go.jp/",
}

# Existing hand-checked case records in app.js, keyed by member name.
CASES = {"金子恭之": "kaneko", "塩川鉄也": "shiokawa"}


def district_info(house, district):
    if house == "衆議院":
        if district.startswith("（比）"):
            return [], "比例" + district[3:] + "ブロック", "比例"
        name = district.rstrip("0123456789")
        return [SHORT[name]], None, "小選挙区"
    if district == "比例":
        return [], "参議院 全国比例", "比例"
    return [SHORT[p] for p in district.split("・")], None, "選挙区"


def main():
    roster = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    acts = collections.defaultdict(dict)
    src = Path(sys.argv[2])  # a cache file; every activity*.jsonl beside it is merged (shards)
    for f in sorted(src.parent.glob("activity*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                acts[(r["house"], r["profileId"])][r["kind"]] = r
    out_dir, fetched = Path(sys.argv[3]), sys.argv[4]
    out_dir.mkdir(parents=True, exist_ok=True)

    everyone = roster["shu"] + roster["san"]
    name_count = collections.Counter(m["name"] for m in everyone)
    members, missing = [], 0
    for m in everyone:
        prefs, block, kind = district_info(m["house"], m["district"])
        a = acts.get((m["house"], m["profileId"]), {})
        homonym = name_count[m["name"]] > 1
        if homonym or "all" not in a:
            speeches = money = None
            status = "homonym" if homonym else "missing"
            missing += 0 if homonym else 1
        else:
            speeches, money = a["all"]["count"], a.get("money", {}).get("count")
            status = "ok" if speeches > 0 else "zero"
            if not (a["all"].get("yomiOk", True)):
                status = "yomi_mismatch"
        prefix = "s" if m["house"] == "衆議院" else "c"
        members.append({
            "id": f"{prefix}{m['profileId']}",
            "name": m["name"],
            "kana": m["kana"],
            "legalName": m.get("legalName"),
            "house": m["house"],
            "kaiha": m["kaiha"],
            "kaihaName": KAIHA[m["house"]].get(m["kaiha"], m["kaiha"]),
            "district": m["district"],
            "electionType": kind,
            "prefectures": prefs,
            "block": block,
            "terms": m.get("terms"),
            "termEnd": m.get("termEnd"),
            "speeches": speeches,
            "moneySpeeches": money,
            "activityStatus": status,
            "speakerQuery": (a.get("all") or {}).get("matchedName", m["name"]).split("|")[0],
            "profileUrl": m["profileUrl"],
            "caseId": CASES.get(m["name"]),
        })
    members.sort(key=lambda x: x["kana"])
    act_any = next(iter(next(iter(acts.values())).values())) if acts else {}
    meta = {
        "fetchedAt": fetched,
        "rosterAsOf": {"衆議院": "令和8年9月28日現在（衆議院ホームページ）", "参議院": "令和8年11月1日現在（参議院ホームページ）"},
        "activityPeriod": {"from": act_any.get("from"), "until": act_any.get("until")},
        "counts": {
            "衆議院": sum(1 for x in members if x["house"] == "衆議院"),
            "参議院": sum(1 for x in members if x["house"] == "参議院"),
            "欠員": {"衆議院": 1, "参議院": 1},
            "activityMissing": missing,
        },
        "kaiha": KAIHA,
        "sources": SOURCES,
        "notes": [
            "発言件数は国会会議録検索システムで発言者名が完全一致した発言の数。活動の量であり、成果や質ではない。",
            "「政治資金」発言件数は、発言本文に「政治資金」を含む発言の数。立場（賛否）は示さない。",
            "同姓同名の議員は会議録で区別できないため件数を出さない。",
            "会議録は取得時点（2026-11-02）で2026-10-05開催分までが公開済み。公開には数週間の遅れがある。",
            "直近1年の発言0件の58人のうち50人は同じ氏名で過去の発言記録があり、残る8人は初当選で記録なし（表記揺れではないことを確認）。",
            "比例代表選出議員は都道府県に含めず、ブロック別に表示する。",
            "赤札・白紙・アクション率・結果率は判定基準の確定後に算出する。",
        ],
    }
    (out_dir / "members.json").write_text(json.dumps(members, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"members {len(members)} / activity missing {missing}")
    pref_cover = {p for x in members for p in x["prefectures"]}
    print("prefectures covered", len(pref_cover), "missing", [p for p in PREFS if p not in pref_cover])


if __name__ == "__main__":
    main()
