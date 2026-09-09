# -*- coding: utf-8 -*-
"""write_alerts.py — 把 kpi.json 的告警写入平台暂存表（去重）
铁律：唯一可写对象 = 自建暂存 Base Kowab5aR9ab9Sps6dLcc4A9ynfg
"""
import subprocess, json, os, sys, datetime

NODE = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node.exe"
JS   = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node_modules\@larksuite\cli\scripts\run.js"
BASE = "Kowab5aR9ab9Sps6dLcc4A9ynfg"
TBL  = "tblsy8dX4uLtwisk"
HERE = os.path.dirname(os.path.abspath(__file__))

def lark_json(args):
    r = subprocess.run([NODE, JS] + args + ["--as", "user"], capture_output=True, text=True, encoding="utf-8")
    try: return json.loads(r.stdout)
    except Exception:
        print("LARK FAIL:", r.stdout[:300]); return None

kpi = json.load(open(os.path.join(HERE, "data", "kpi.json"), encoding="utf-8"))
alerts = kpi.get("alerts") or []
snap = (kpi.get("generated_at") or "")[:10]

# 读已有记录做去重键：来源规则编号 + 异常描述 + 数据快照日期
def page(pt=None):
    args = ["base", "+record-list", "--base-token", BASE, "--table-id", TBL,
            "--format", "json", "--limit", "200"]
    if pt: args += ["--page-token", pt]
    return lark_json(args)

existing = set()
pt = None
while True:
    d = page(pt)
    if not d or not d.get("ok"): break
    dd = d["data"]
    fids = dd.get("field_id_list") or []
    names = {}
    # field id -> name 映射
    fl = lark_json(["base", "+field-list", "--base-token", BASE, "--table-id", TBL, "--format", "json"])
    names = {f["id"]: f["name"] for f in fl["data"]["fields"]}
    for row in dd.get("data") or []:
        rec = {names.get(fid, fid): v for fid, v in zip(fids, row)}
        key = (rec.get("来源规则编号") or "", rec.get("异常描述") or "", str(rec.get("数据快照日期") or "")[:10])
        existing.add(key)
    if not dd.get("has_more"): break
    pt = dd.get("page_token")
    if not pt: break

new_rows, skipped = [], 0
for a in alerts:
    key = (a.get("rule"), a.get("text"), snap)
    if key in existing:
        skipped += 1
        continue
    new_rows.append([a.get("level"), a.get("rule"), a.get("text"), "", "待确认", snap])
    existing.add(key)

if not new_rows:
    print(f"no new alerts (skipped {skipped} dup); staging unchanged")
    sys.exit(0)

# 分批写（每批 <=200）
def chunks(l, n):
    for i in range(0, len(l), n): yield l[i:i+n]

written = 0
FIELDS = ["异常级别","来源规则编号","异常描述","涉及渠道","状态","数据快照日期"]
for batch in chunks(new_rows, 100):
    body = {"fields": FIELDS, "rows": [r[:4] + [r[4], r[5]] for r in batch]}
    d = lark_json(["base", "+record-batch-create", "--base-token", BASE, "--table-id", TBL,
                   "--json", json.dumps(body, ensure_ascii=False)])
    if d and d.get("ok"):
        written += len(batch)
    else:
        print("WRITE FAIL:", json.dumps(d, ensure_ascii=False)[:300] if d else "none")

print(f"staging written={written} skipped_dup={skipped} snapshot={snap}")
