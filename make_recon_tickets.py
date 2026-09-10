# -*- coding: utf-8 -*-
"""make_recon_tickets.py — 应扣差异聚合成对账工单写入暂存表
规则(A5)：按 账期×运输方式 聚合，净差异 >¥500 成单；红>¥5000，黄>¥500
去重键：来源规则编号+异常描述（跨天不重复）
铁律：唯一可写对象 = 暂存 Base Kowab5aR9ab9Sps6dLcc4A9ynfg
"""
import subprocess, json, os, sys, datetime

NODE = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node.exe"
JS   = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node_modules\@larksuite\cli\scripts\run.js"
BASE = "Kowab5aR9ab9Sps6dLcc4A9ynfg"
TBL  = "tblsy8dX4uLtwisk"
HERE = os.path.dirname(os.path.abspath(__file__))

def lark(args):
    r = subprocess.run([NODE, JS] + args + ["--as", "user"], capture_output=True, text=True, encoding="utf-8")
    try: return json.loads(r.stdout)
    except: return {"ok": False, "raw": r.stdout[:200]}

# 1) 聚合四期差异
TODAY = datetime.date.today().isoformat()
groups = {}
for label, f in [("8月", "recon.json"), ("7月", "recon_07.json"), ("6月", "recon_06.json"), ("5月", "recon_05.json")]:
    try:
        r = json.load(open(os.path.join(HERE, "data", f), encoding="utf-8"))
    except: continue
    for v in r.get("violations", []):
        key = (label, v["mode"])
        g = groups.setdefault(key, {"month": label, "mode": v["mode"], "tickets": 0, "net": 0.0,
                                    "kg": 0.0, "actual": 0.0, "sample": v["no"]})
        g["tickets"] += 1; g["net"] += v["diff"]; g["kg"] += v["kg"]; g["actual"] += v["actual"]

rows = []
for (label, mode), g in sorted(groups.items(), key=lambda x: -abs(x[1]["net"])):
    if abs(g["net"]) <= 500: continue
    level = "红" if abs(g["net"]) > 5000 else "黄"
    desc = (f"{label}账单 {mode} {g['tickets']} 票与价格表不符："
            f"应扣核对差异 {'+' if g['net']>0 else ''}{round(g['net'],2)} 元"
            f"（计费重 {round(g['kg'],0)}kg，实扣合计 {round(g['actual'],2)}），"
            f"疑似燃油/附加口径差异，需与中运通达核对")
    rows.append([level, "A5-对账", desc, f"中运通达·{mode}", "待确认", TODAY])

if not rows:
    print("无 >¥500 的差异组，不生成工单"); sys.exit(0)

# 2) 去重读暂存表
fl = lark(["base", "+field-list", "--base-token", BASE, "--table-id", TBL, "--format", "json"])
names = {f["id"]: f["name"] for f in fl["data"]["fields"]}
existing, pt = set(), None
while True:
    args = ["base", "+record-list", "--base-token", BASE, "--table-id", TBL, "--format", "json", "--limit", "200"]
    if pt: args += ["--page-token", pt]
    d = lark(args)
    if not d.get("ok"): break
    dd = d["data"]
    for row in dd.get("data") or []:
        rec = {names.get(fid, fid): v for fid, v in zip(dd.get("field_id_list") or [], row)}
        existing.add((rec.get("来源规则编号") or "", rec.get("异常描述") or ""))
    if not dd.get("has_more"): break
    pt = dd.get("page_token")

new_rows = []
for r in rows:
    key = ("A5-对账", r[2])
    if key in existing: continue
    existing.add(key)
    new_rows.append(r)

if not new_rows:
    print(f"差异组 {len(rows)} 个均已成单，跳过"); sys.exit(0)

written = 0
for i in range(0, len(new_rows), 100):
    batch = new_rows[i:i+100]
    body = {"fields": FIELDS if False else ["异常级别","来源规则编号","异常描述","涉及渠道","状态","数据快照日期"],
            "rows": batch}
    d = lark(["base", "+record-batch-create", "--base-token", BASE, "--table-id", TBL,
              "--json", json.dumps(body, ensure_ascii=False)])
    if d.get("ok"): written += len(batch)
    else: print("WRITE FAIL:", json.dumps(d, ensure_ascii=False)[:250])
print(f"对账工单写入 {written} 张（候选 {len(new_rows)}，全部差异组 {len(rows)}）")
