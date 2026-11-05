"""Merge ② 進捗率 (pipeline/score_progress.py output) into the site data.

Usage: python3 -I pipeline/build_progress.py DATA_DIR PROGRESS_JSONL
  - DATA_DIR/members.json      : adds m.pp.pg = {"n": pledges judged, "act": stage>=1, "done": stage>=2, "na": pledges not judged}
  Pledges whose target is not written (4-check 何を = false, e.g. 「災害に強い国土づくり」) cannot be checked against the record:
  they are left out of n (the rate's denominator) and counted as "na". Vagueness is already scored by ① 公約の具体性.
  - DATA_DIR/pledges_progress.json : {member id: [[item index, stage, why, [evidence...]], ...]} (read when a member is opened)
Run AFTER build.py / build_records.py (they rewrite members.json).
"""
import json, sys
from pathlib import Path

data, src = Path(sys.argv[1]), Path(sys.argv[2])
rows = {}
for line in src.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    rows[r["id"]] = r  # last row wins (re-runs append)
members = json.loads((data / "members.json").read_text(encoding="utf-8"))
pp_all = json.loads((data / "pledges_personal.json").read_text(encoding="utf-8")) if (data / "pledges_personal.json").exists() else {}
out, n_mem, n_items = {}, 0, 0
for m in members:
    r = rows.get(m["id"])
    pp = m.get("pp")
    if not r or not pp or pp.get("n") is None:
        if pp is not None:
            pp.pop("pg", None)
        continue
    src_items = (pp_all.get(m["id"]) or {}).get("items") or []
    vague = lambda x: x["i"] < len(src_items) and src_items[x["i"]].get("t") is False  # noqa: E731
    items = [x for x in r["items"] if not vague(x)]
    na = len(r["items"]) - len(items)
    pp["pg"] = {"n": len(items), "act": sum(1 for x in items if x["st"] >= 1), "done": sum(1 for x in items if x["st"] >= 2), "na": na}
    out[m["id"]] = [[x["i"], x["st"], x["why"], x["ev"]] for x in items] + [[x["i"], -1, "", []] for x in r["items"] if vague(x)]
    n_mem += 1
    n_items += len(items)
(data / "members.json").write_text(json.dumps(members, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(data / "pledges_progress.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"progress merged: {n_mem} members, {n_items} pledges; missing for {sum(1 for m in members if m.get('pp') and m['pp'].get('n') is not None and m['id'] not in rows)} members with pledges")
