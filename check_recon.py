# -*- coding: utf-8 -*-
"""check_recon.py — 中运通达 8 月账单 应扣引擎 v1
覆盖模式：美国包税海卡(正班)[费率带] / 大陆UPS-红单小货[查表] / 大陆UPS包税(美国)[查表]
输出：data/recon.json（含应扣核对与差异票）
铁律：账单/价格表只读，结果写 data/recon.json
"""
import sys, os, json, math
sys.path.insert(0, r'D:\WB文件\2026-09-09-11-43-53\.secrets\pylibs')
import openpyxl
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BILL = os.path.join(HERE, "bills", "JW PEI LIMITED（2026-09-03）.xlsx")
PRICE = os.path.join(HERE, "bills", "中运通达 价格表Vip（2026-8-25）.xlsx")

def num(v):
    try: return float(v)
    except: return None

# ---------- 1) 账单逐票 ----------
wb = openpyxl.load_workbook(BILL, read_only=True, data_only=True)
ws = wb["快件账单"]
tickets = []
for r in ws.iter_rows(min_row=6, values_only=True):
    if r[0] is None or not str(r[0]).isdigit(): continue
    tickets.append({"mode": str(r[4] or "-"), "dest": str(r[5] or ""), "kg": num(r[10]) or 0.0,
                    "amount": num(r[11]) or 0.0, "no": str(r[2] or ""), "fee_note": str(r[13] or "")})

# ---------- 2) 价格表 ----------
pw = openpyxl.load_workbook(PRICE, read_only=True, data_only=True)

# 2a) 美国包税海卡 → 美森正班卡派(CLX) 费率带（12KG+/51KG+ min-max）
ws = pw["美国包税海卡"]
grid = [list(r) for r in ws.iter_rows(min_row=3, max_row=16, values_only=True)]
band_hacka = {12: [1e9, -1e9], 51: [1e9, -1e9]}
for row in grid[1:]:
    for base in (1, 6):  # 正班面板列 2,3 / 加班面板列 7,8（只取正班）
        pass
for row in grid[1:]:
    a, b = num(row[2]), num(row[3])
    if a is not None: band_hacka[12][0] = min(band_hacka[12][0], a); band_hacka[12][1] = max(band_hacka[12][1], a)
    if b is not None: band_hacka[51][0] = min(band_hacka[51][0], b); band_hacka[51][1] = max(band_hacka[51][1], b)

# 2b) 大陆UPS-红单小货 → (国家, 0.5kg档) → 每票价
ws = pw["大陆UPS-红单小货"]
grid = [list(r) for r in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True)]
countries, weight_col = {}, None
for row in grid[:5]:
    for ci, c in enumerate(row):
        if c and str(c) in ("日本","美国","加拿大","澳大利亚","英国","德国","法国","意大利","西班牙"):
            countries[ci] = str(c)
        if c and str(c) == "分区": weight_col = ci
ups_small = {}
w = None
for row in grid:
    for ci, c in enumerate(row):
        t = str(c).strip() if c is not None else ""
        if ci == weight_col and t: w = t
        elif ci in countries and w:
            v = num(c)
            if v is not None: ups_small[(countries[ci], round(float(w.replace("KG","").replace("kg","")) if w.replace("KG","").replace("kg","").replace(".","",1).isdigit() else 0, 1))] = v
    # 逐行：col1=重量档
def parse_w(t):
    try: return float(str(t).replace("KG","").replace("kg","").strip())
    except: return None
rows_small = []
for row in grid:
    wv = parse_w(row[weight_col]) if weight_col is not None and weight_col < len(row) else None
    if wv is not None:
        for ci, cn in countries.items():
            if ci < len(row):
                v = num(row[ci])
                if v is not None: rows_small.append((cn, wv, v))
ups_small = {}
for cn, wv, v in rows_small:
    k = (cn, round(math.ceil(wv*2)/2, 1))
    ups_small.setdefault(k, v)  # 取最小档

# 2c) 大陆UPS包税(美国) → (国家, 0.5kg档) → 每票价
ws = pw["大陆UPS包税(美国)"]
grid = [list(r) for r in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True)]
ups_tax = {}
col_country = {}
for row in grid[:6]:
    for ci, c in enumerate(row):
        if c and str(c) in ("加拿大","美国"): col_country[ci] = str(c)
for row in grid:
    for ci, c in enumerate(row):
        wv = None
        t = str(c).strip() if c is not None else ""
        if t.endswith("KG"):
            wv = parse_w(t)
        if wv is not None:
            for cj in range(ci+1, ci+3):
                if cj < len(row) and cj in col_country:
                    v = num(row[cj])
                    if v is not None:
                        k = (col_country[cj], round(math.ceil(wv*2)/2, 1))
                        ups_tax.setdefault(k, v)

# ---------- 3) 逐票核验 ----------
MODE_BAND = {"美国包税海卡(正班)": ("band", band_hacka)}
MODE_TABLE = {"大陆UPS-红单小货": ups_small, "大陆UPS包税(美国)": ups_tax}
violations, checked = [], 0
mode_stat = defaultdict(lambda: {"tickets":0,"kg":0.0,"amount":0.0,"should":0.0,"checked":0,"viol":0,"viol_amt":0.0})
for t in tickets:
    m = t["mode"]; ms = mode_stat[m]
    ms["tickets"] += 1; ms["kg"] += t["kg"]; ms["amount"] += t["amount"]
    should = None
    if m in MODE_BAND and t["kg"] > 0:
        kind, band = MODE_BAND[m]
        br = 51 if t["kg"] >= 51 else 12
        lo, hi = band[br]
        if lo < 1e8:
            should = (lo + hi) / 2  # 带中值参考（费率带无仓库明细）
            ok = (lo - 0.5) <= (t["amount"]/t["kg"] if t["kg"] else 0) <= (hi + 0.5)
            # 海卡按 kg 计价：应扣区间 = band[kg档] * kg
            lo_amt, hi_amt = lo*t["kg"], hi*t["kg"]
            ok = (lo_amt - 50) <= t["amount"] <= (hi_amt + 50)
            should = round((lo_amt + hi_amt)/2, 1)
            if not ok:  # 费率带模式：仅出带算差异
                ms["checked"] += 1; ms["should"] += t["amount"]  # 带内视为应扣=实扣
                diff = t["amount"] - should
                ms["viol"] += 1; ms["viol_amt"] += diff
                if True:
                    violations.append({"no": t["no"], "mode": m, "dest": t["dest"], "kg": t["kg"],
                                       "actual": t["amount"], "should": round(should,1),
                                       "diff": round(diff,1), "note": "出费率带"})
            else:
                ms["checked"] += 1; ms["should"] += t["amount"]
            checked = True
        else:
            checked = False
    elif m in MODE_TABLE and t["kg"] > 0:
        tbl = MODE_TABLE[m]
        k = (t["dest"], round(math.ceil(t["kg"]*2)/2, 1))
        if k in tbl:
            should = tbl[k]; checked = True
        else:
            # 容错：就近档位（向下取0.5）
            k2 = (t["dest"], round(math.floor(t["kg"]*2)/2, 1))
            should = tbl.get(k2); checked = should is not None
    if should is not None and m not in MODE_BAND:
        ms["checked"] += 1; ms["should"] += should
        # v2: 解析费用说明构成项，运费基准=自动计费项，其余(产品附加费等)单列归因
        import re as _re
        comps = _re.findall(r'([^;；:：]+)[:：]\s*(-?\d+\.?\d*)', t.get("fee_note") or "")
        base, surcharges = t["amount"], []
        for name, amt in comps:
            n = name.strip()
            if ("速递" in n or "自动计费" in n or ("运费" in n and "赔偿" not in n)) and abs(num(amt) or 0) >= abs(base)*0.3:
                base = num(amt)
            elif num(amt):
                surcharges.append((n[:16], num(amt)))
        diff = base - should
        tol = max(20, abs(should)*0.02)
        if abs(diff) > tol:
            ms["viol"] += 1; ms["viol_amt"] += diff
            if True:
                violations.append({"no": t["no"], "mode": m, "dest": t["dest"], "kg": t["kg"],
                                   "actual": t["amount"], "should": round(should,1),
                                   "diff": round(diff,1),
                                   "note": "运费基准差异 · 附加费:" + json.dumps(surcharges, ensure_ascii=False)[:70]})

# ---------- 4) 输出 ----------
mode_rows = []
for m, ms in sorted(mode_stat.items(), key=lambda x: -x[1]["amount"]):
    mode_rows.append({"mode": m, "tickets": ms["tickets"], "chargeable_kg": round(ms["kg"],1),
                      "amount": round(ms["amount"],2),
                      "should": round(ms["should"],2) if ms["checked"] else None,
                      "checked": ms["checked"], "viol": ms["viol"], "viol_amt": round(ms["viol_amt"],2)})
out = {"generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
       "bill": "中运通达 2026年08月对账单 (JW PEI LIMITED, 2026-09-03)",
       "price_version": "价格表Vip 2026-8-25（8月生效版）",
       "total_amount": round(sum(ms["amount"] for ms in mode_stat.values()), 2),
       "checked_total": round(sum(ms["amount"] for ms in mode_stat.values() if ms["checked"]), 2),
       "engine": "v1 覆盖3模式（海卡费率带 / UPS两表查表）；其余模式待适配",
       "rows": mode_rows, "violations": violations}
json.dump(out, open(os.path.join(HERE, "data", "recon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
cov_amt = out["checked_total"]
print(f"覆盖模式金额: ¥{cov_amt} / 总 ¥{out['total_amount']} ({round(cov_amt/out['total_amount']*100)}%)")
print(f"差异票: {sum(ms['viol'] for ms in mode_stat.values())} | 差异金额: {round(sum(ms['viol_amt'] for ms in mode_stat.values()),2)}")
for v in violations[:8]: print(" ", v["mode"], v["dest"], v["kg"], "kg 实扣", v["actual"], "应扣", v["should"], "差", v["diff"])
