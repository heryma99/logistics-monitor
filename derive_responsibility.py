# -*- coding: utf-8 -*-
"""derive_responsibility.py — 从异常单登记表真实数据推导 物流商→跟单客服 映射
方法：拉近 N 条登记记录，按 物流商 分组统计 66负责客服 出现频次，取众数为该物流商跟单
铁律: 只读数据源，结果写 data/responsibility_map.json
"""
import subprocess, json, os
from collections import Counter, defaultdict

NODE = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node.exe"
JS   = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node_modules\@larksuite\cli\scripts\run.js"
BASE = "BKcQb1LfXanySRsERH4cLlfZnwd"
TBL  = "tblzbhh0UU3eCGTF"
HERE = os.path.dirname(os.path.abspath(__file__))

def lark(args):
    r = subprocess.run([NODE, JS] + args + ["--as", "user"], capture_output=True, text=True, encoding="utf-8")
    try: return json.loads(r.stdout)
    except: return {"ok": False, "raw": r.stdout[:150]}

fl = lark(["base", "+field-list", "--base-token", BASE, "--table-id", TBL, "--format", "json"])
names = {f["id"]: f["name"] for f in fl["data"]["fields"]}
F_LOGI = next((k for k, v in names.items() if v == "物流商"), None)
F_CS   = next((k for k, v in names.items() if "负责客服" in v), None)
print("物流商字段:", F_LOGI, "| 负责客服字段:", F_CS)

# 拉最近 1200 条（近期工单足以代表当前分工）
records, pt, pages = [], None, 0
while pages < 6:
    pages += 1
    args = ["base", "+record-list", "--base-token", BASE, "--table-id", TBL, "--format", "json", "--limit", "200"]
    if pt: args += ["--page-token", pt]
    d = lark(args)
    if not d.get("ok"): print("READ FAIL:", str(d)[:150]); break
    dd = d["data"]
    fids = dd.get("field_id_list") or []
    for row in dd.get("data") or []:
        rec = {names.get(fid, fid): v for fid, v in zip(fids, row)}
        records.append(rec)
    if not dd.get("has_more"): break
    pt = dd.get("page_token")
print("读取记录:", len(records))

tally = defaultdict(Counter)
no_logi = 0
for rec in records:
    logi = rec.get("物流商")
    if isinstance(logi, list): logi = logi[0] if logi else None
    logi = str(logi or "").strip()
    cs = rec.get("66负责客服")
    cname = None
    if isinstance(cs, list) and cs:
        cname = cs[0].get("name") if isinstance(cs[0], dict) else str(cs[0])
    elif isinstance(cs, dict): cname = cs.get("name")
    if not logi: no_logi += 1; continue
    if cname: tally[logi][cname] += 1

mapping = []
for logi, counter in sorted(tally.items(), key=lambda x: -sum(x[1].values())):
    total = sum(counter.values())
    top, cnt = counter.most_common(1)[0]
    others = ", ".join(f"{n}({c})" for n, c in counter.most_common(3)[1:])
    mapping.append({"物流商": logi, "跟单客服": top, "票数": total, "占比": round(cnt/total*100, 1), "其他人": others})
    print(f"{logi}: {top} ({cnt}/{total}, {round(cnt/total*100)}%) {others[:40]}")

json.dump({"generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "source": "跨部门异常单登记表·近1200条 66负责客服 统计",
           "no_logistics_tickets": no_logi, "mapping": mapping},
          open(os.path.join(HERE, "data", "responsibility_map.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("saved data/responsibility_map.json")
