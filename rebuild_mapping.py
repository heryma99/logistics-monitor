# -*- coding: utf-8 -*-
"""rebuild_mapping.py — 责任人映射表重构为「业务线 × 物流商」矩阵
每一行 = 一个 (业务线, 物流商) 组合，跟单员列由用户填
铁律: 只动平台自有 Base 的映射表
"""
import subprocess, json, os, sys

NODE = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node.exe"
JS   = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node_modules\@larksuite\cli\scripts\run.js"
BASE = "Kowab5aR9ab9Sps6dLcc4A9ynfg"
TBL  = "tbl5gOxyVkjQS4PZ"

def lark(args):
    r = subprocess.run([NODE, JS] + args + ["--as", "user"], capture_output=True, text=True, encoding="utf-8")
    try: return json.loads(r.stdout)
    except: return {"ok": False, "raw": r.stdout[:300]}

# 1) 删旧行
d = lark(["base", "+record-list", "--base-token", BASE, "--table-id", TBL, "--format", "json", "--limit", "200"])
rids = (d.get("data") or {}).get("record_id_list") or []
if rids:
    for i in range(0, len(rids), 50):
        batch = rids[i:i+50]
        args = ["base", "+record-delete", "--base-token", BASE, "--table-id", TBL, "--yes"]
        for rid in batch: args += ["--record-id", rid]
        lark(args)
print("旧行已删:", len(rids))

# 2) 物流商清单（来自账单实况）
LOGISTICS = ["中运通达", "云途", "DPEX澳洲(隆锦祥)", "香港合联", "广州易连", "捷邮", "德翼(璞景/亚丰)", "大陆UPS", "DHL/联邦", "其他"]
# 业务线：2B 物流商可跨线；B2C 按物流商分组
LINES = ["FBA海运", "FBA空运", "自发货小货(B2C)", "WHS批发(2B)", "商业快递(2B)"]

rows = []
for line in LINES:
    for lg in LOGISTICS:
        note = ""
        if line.startswith("自发货"): note = "B2C Shopify：按物流商分跟单组" if lg != "其他" else ""
        if line.startswith(("WHS", "商业", "FBA")): note = "2B：同一物流商可跨业务线，跟单可不同"
        rows.append([line, lg, "", note])

# 3) 批量写入（分批 50）
written = 0
for i in range(0, len(rows), 50):
    batch = rows[i:i+50]
    body = {"fields": ["业务线", "物流商", "跟单员", "职责说明"], "rows": batch}
    d = lark(["base", "+record-batch-create", "--base-token", BASE, "--table-id", TBL, "--json", json.dumps(body, ensure_ascii=False)])
    if d.get("ok"): written += len(batch)
    else: print("FAIL:", json.dumps(d, ensure_ascii=False)[:200])
print(f"矩阵写入 {written} 行（{len(LINES)} 业务线 × {len(LOGISTICS)} 物流商），跟单员列待填")
