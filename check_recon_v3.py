# -*- coding: utf-8 -*-
"""check_recon_v3.py — 应扣引擎 v3：按每票收货日期匹配当周生效的价格表版本
用法: python check_recon_v3.py <账单文件名> <输出json名> [账期标签]
铁律: 账单/价格表只读，结果写 data/
"""
import sys, os, json, math, re, datetime
sys.path.insert(0, r'D:\WB文件\2026-09-09-11-43-53\.secrets\pylibs')
import openpyxl
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BILLS = os.path.join(HERE, "bills")
DATA = os.path.join(HERE, "data")

def num(v):
    try: return float(v)
    except: return None

def pdate(s):
    m = re.search(r"(\d{4})-(\d+)-(\d+)", str(s))
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

# ---------- 版本索引：bills/ 下所有价格表Vip ----------
versions = []
for f in sorted(os.listdir(BILLS)):
    m = re.search(r"价格表Vip（(\d{4})-(\d+)-(\d+)）", f)
    if m and f.endswith(".xlsx"):
        versions.append((datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), os.path.join(BILLS, f)))
versions.sort(key=lambda x: x[0])

_cache = {}
def version_lookups(path):
    """解析一张价格表 → (band_hacka, ups_small, ups_tax)，带缓存"""
    if path in _cache: return _cache[path]
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    # 海卡费率带（正班面板 col2,3）
    band = {12: [1e9, -1e9], 51: [1e9, -1e9]}
    if "美国包税海卡" in wb.sheetnames:
        for row in wb["美国包税海卡"].iter_rows(min_row=4, max_row=16, values_only=True):
            a, b = num(row[2] if len(row) > 2 else None), num(row[3] if len(row) > 3 else None)
            if a is not None: band[12][0] = min(band[12][0], a); band[12][1] = max(band[12][1], a)
            if b is not None: band[51][0] = min(band[51][0], b); band[51][1] = max(band[51][1], b)
    # UPS-红单小货 (国家,0.5档)->每票价
    ups_small = {}
    if "大陆UPS-红单小货" in wb.sheetnames:
        grid = [list(r) for r in wb["大陆UPS-红单小货"].iter_rows(values_only=True)]
        countries, wcol = {}, None
        for row in grid[:5]:
            for ci, c in enumerate(row):
                if c and str(c).strip() in ("日本","美国","加拿大","澳大利亚","英国","德国","法国","意大利","西班牙","墨西哥","瑞典","荷兰"):
                    countries[ci] = str(c).strip()
                if c and str(c).strip() == "分区": wcol = ci
        for row in grid:
            wv = None
            if wcol is not None and wcol < len(row): wv = num(row[wcol])
            if wv is None: continue
            for ci, cn in countries.items():
                if ci < len(row):
                    v = num(row[ci])
                    if v is not None:
                        k = (cn, round(math.ceil(wv*2)/2, 1))
                        ups_small.setdefault(k, v)
    # UPS包税(美国) (国家,0.5档)->每票总价
    ups_tax = {}
    if "大陆UPS包税(美国)" in wb.sheetnames:
        grid = [list(r) for r in wb["大陆UPS包税(美国)"].iter_rows(values_only=True)]
        colc = {}
        for row in grid[:6]:
            for ci, c in enumerate(row):
                if c and str(c).strip() in ("加拿大","美国"): colc[ci] = str(c).strip()
        for row in grid:
            for ci, c in enumerate(row):
                t = str(c).strip() if c else ""
                if t.endswith("KG"):
                    wv = num(t[:-2])
                    if wv is not None:
                        for cj in range(ci+1, ci+3):
                            if cj < len(row) and cj in colc:
                                v = num(row[cj])
                                if v is not None:
                                    k = (colc[cj], round(math.ceil(wv*2)/2, 1))
                                    ups_tax.setdefault(k, v)
    # 欧洲包税：子产品块（国家分组 per-kg / 仓库 band）
    eu_blocks = []
    if "欧洲包税" in wb.sheetnames:
        cur = None
        for row in wb["欧洲包税"].iter_rows(values_only=True):
            c1 = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            if c1.startswith("欧洲包税-"):
                cur = {"title": c1, "rows": [], "band": {21: [1e9,-1e9], 51: [1e9,-1e9], 101: [1e9,-1e9], 301: [1e9,-1e9]}, "warehouses": False}
                eu_blocks.append(cur)
            elif cur is not None:
                c0 = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                if c0.startswith("一、") or c0.startswith("附"): cur = None; continue
                r21, r51, r101, r301 = num(row[2] if len(row)>2 else None), num(row[3] if len(row)>3 else None), num(row[4] if len(row)>4 else None), num(row[5] if len(row)>5 else None)
                if c1 and c1 != "国家" and (r21 or r51 or r101 or r301):
                    cur["rows"].append((c1.replace("\n",""), r21, r51, r101, r301))
                    for br, v in ((21,r21),(51,r51),(101,r101),(301,r301)):
                        if v is not None:
                            cur["band"][br][0] = min(cur["band"][br][0], v); cur["band"][br][1] = max(cur["band"][br][1], v)
                    if not any(ch in c1 for ch in ("国",)) and ("(" in c1 or "仓" in c1): cur["warehouses"] = True
    # 日本
    jp = {}
    if "日本自税空海派" in wb.sheetnames:
        for row in wb["日本自税空海派"].iter_rows(values_only=True):
            ch = str(row[2]).strip() if len(row)>2 and row[2] else ""
            if "ACP" in ch or "海运" in ch or "空运" in ch:
                r21, r51, r101, r301 = num(row[3] if len(row)>3 else None), num(row[4] if len(row)>4 else None), num(row[5] if len(row)>5 else None), num(row[6] if len(row)>6 else None)
                if any(x is not None for x in (r21,r51,r101,r301)):
                    jp[ch] = (r21, r51, r101, r301)
    # 英国VAT递延
    uk = {}
    if "英国VAT递延" in wb.sheetnames:
        for row in wb["英国VAT递延"].iter_rows(values_only=True):
            c1 = str(row[1]).strip() if len(row)>1 and row[1] else ""
            if c1.startswith("英国VAT递延-"):
                r10, r101, r301 = num(row[2]), num(row[3]), num(row[4])
                clr = num(str(row[5]).replace("RMB/票","")) if row[5] else None
                if r10 is not None:
                    uk[c1[len("英国VAT递延-"):]] = (r10, r101, r301, clr or 0)
    # 加拿大包税海派：整表按档 min-max 带
    ca_band = {21: [1e9,-1e9], 51: [1e9,-1e9], 101: [1e9,-1e9], 301: [1e9,-1e9]}
    if "加拿大包税海派" in wb.sheetnames:
        hdr_rows = []
        for row in wb["加拿大包税海派"].iter_rows(values_only=True):
            for ci, c in enumerate(row):
                if c and str(c).strip() == "21KG+": hdr_rows.append(ci)
        for row in wb["加拿大包税海派"].iter_rows(values_only=True):
            for ci0 in hdr_rows:
                for off, br in ((0,21),(1,51),(2,101),(3,301)):
                    v = num(row[ci0+off]) if ci0+off < len(row) else None
                    if v is not None and 5 < v < 200:
                        ca_band[br][0] = min(ca_band[br][0], v); ca_band[br][1] = max(ca_band[br][1], v)
    # 澳洲包税海派：海运包税 band
    au_band = {21: [1e9,-1e9], 100: [1e9,-1e9], 300: [1e9,-1e9]}
    if "澳洲包税海派" in wb.sheetnames:
        for row in wb["澳洲包税海派"].iter_rows(min_row=4, values_only=True):
            if not (row[0] and "仓" in str(row[0])): continue
            for off, br in ((1,21),(2,100),(3,300)):
                v = num(row[off]) if off < len(row) else None
                if v is not None:
                    au_band[br][0] = min(au_band[br][0], v); au_band[br][1] = max(au_band[br][1], v)
    _cache[path] = (band, ups_small, ups_tax, eu_blocks, jp, uk, ca_band, au_band)
    return _cache[path]

def pick_version(d):
    """收货日期 → 生效价格表（发布日≤收货日的最新版）"""
    cand = [v for v in versions if v[0] <= d]
    return cand[-1] if cand else (versions[0] if versions else None)

# ---------- 账单 ----------
bill_file = os.path.join(BILLS, sys.argv[1] if len(sys.argv) > 1 else "JW PEI LIMITED（2026-09-03）.xlsx")
out_name = sys.argv[2] if len(sys.argv) > 2 else "recon.json"
label = sys.argv[3] if len(sys.argv) > 3 else ""

wb = openpyxl.load_workbook(bill_file, read_only=True, data_only=True)
ws = wb["快件账单"]
tickets = []
for r in ws.iter_rows(min_row=6, values_only=True):
    if r[0] is None or not str(r[0]).isdigit(): continue
    tickets.append({"mode": str(r[4] or "-"), "dest": str(r[5] or ""), "recv": str(r[1] or ""),
                    "kg": num(r[10]) or 0.0, "amount": num(r[11]) or 0.0,
                    "no": str(r[2] or ""), "fee_note": str(r[13] or "")})

mode_stat = defaultdict(lambda: {"tickets":0,"kg":0.0,"amount":0.0,"should":0.0,"checked":0,"viol":0,"viol_amt":0.0})
violations, ver_stat = [], defaultdict(lambda: [0, 0.0])
no_version = 0
comp_rows = []  # 赔偿/退费负票单独归档，不进逐票核验
for t in tickets:
    if t["amount"] < 0:
        comp_rows.append({"no": t["no"], "mode": t["mode"], "kg": t["kg"],
                          "amount": t["amount"], "note": (t.get("fee_note") or "")[:60]})
        continue
    m = t["mode"]; ms = mode_stat[m]
    ms["tickets"] += 1; ms["kg"] += t["kg"]; ms["amount"] += t["amount"]
    d = pdate(t["recv"])
    ver = pick_version(d) if d else None
    if ver is None:
        no_version += 1; continue
    ver_stat[ver[0].isoformat()][0] += 1; ver_stat[ver[0].isoformat()][1] += t["amount"]
    band, ups_small, ups_tax, eu_blocks, jp, uk, ca_band, au_band = version_lookups(ver[1])
    should, checked = None, False
    if m == "美国包税海卡(正班)" and t["kg"] > 0:
        br = 51 if t["kg"] >= 51 else 12
        lo, hi = band[br]
        if lo < 1e8:
            lo_amt, hi_amt = lo*t["kg"], hi*t["kg"]
            checked = True
            inband = (lo_amt - 50) <= t["amount"] <= (hi_amt + 50)
            should = t["amount"] if inband else round((lo_amt + hi_amt)/2, 1)
    elif m.startswith("日本海运ACP") and t["kg"] > 0:
        for ch, rates in jp.items():
            if "海运" in ch:
                r21, r51, r101, r301 = rates
                br = 301 if t["kg"]>=301 else 101 if t["kg"]>=101 else 51 if t["kg"]>=51 else 21
                rate = {21:r21,51:r51,101:r101,301:r301}[br]
                if rate is not None: should = rate*t["kg"]; checked = True
                break
    elif m.startswith("英国VAT递延(") and t["kg"] > 0:
        suf = m[m.find("(")+1:-1]
        for key, (r10, r101, r301, clr) in uk.items():
            if suf in key:
                rate = r301 if t["kg"]>=301 else r101 if t["kg"]>=101 else r10
                should = rate*t["kg"] + clr; checked = True
                break
    elif m.startswith("澳洲包税海派") and t["kg"] > 0:
        br = 300 if t["kg"]>=300 else 100 if t["kg"]>=100 else 21
        lo, hi = au_band[br]
        if lo < 1e8:
            lo_amt, hi_amt = lo*t["kg"], hi*t["kg"]
            checked = True
            should = t["amount"] if (lo_amt-50) <= t["amount"] <= (hi_amt+50) else round((lo_amt+hi_amt)/2,1)
    elif m.startswith("加拿大包税卡派") and t["kg"] > 0:
        br = 301 if t["kg"]>=301 else 101 if t["kg"]>=101 else 51 if t["kg"]>=51 else 21
        lo, hi = ca_band[br]
        if lo < 1e8:
            lo_amt, hi_amt = lo*t["kg"], hi*t["kg"]
            checked = True
            should = t["amount"] if (lo_amt-50) <= t["amount"] <= (hi_amt+50) else round((lo_amt+hi_amt)/2,1)
    elif m.startswith("欧洲包税") and t["kg"] > 0:
        br = 301 if t["kg"]>=301 else 101 if t["kg"]>=101 else 51 if t["kg"]>=51 else 21
        key = m[m.find("(")+1:-1] if "(" in m else ""
        blk = None
        for b in eu_blocks:
            kt = b["title"].split("-")[-1]
            if key.replace(" ","") in kt.replace(" ","") or (key=="卡航卡派" and "卡航卡派" in kt) or (key=="卡航" and kt=="卡航") or (key and key in kt):
                blk = b; break
        if blk and blk.get("warehouses"):
            lo, hi = blk["band"][br]
            if lo < 1e8:
                lo_amt, hi_amt = lo*t["kg"], hi*t["kg"]
                checked = True
                should = t["amount"] if (lo_amt-50) <= t["amount"] <= (hi_amt+50) else round((lo_amt+hi_amt)/2,1)
        elif blk:
            dest = t["dest"]
            for label_g, r21, r51, r101, r301 in blk["rows"]:
                lg = label_g.replace("、","").replace(" ","")
                if dest in lg:
                    rate = {21:r21,51:r51,101:r101,301:r301}[br]
                    if rate is not None: should = rate*t["kg"]; checked = True
                    break
    elif m == "大陆UPS-红单小货" and t["kg"] > 0:
        for k in [(t["dest"], round(math.ceil(t["kg"]*2)/2, 1)), (t["dest"], round(math.floor(t["kg"]*2)/2, 1))]:
            if k in ups_small: should = ups_small[k]; checked = True; break
    elif m == "大陆UPS包税(美国)" and t["kg"] > 0:
        for k in [(t["dest"], round(math.ceil(t["kg"]*2)/2, 1)), (t["dest"], round(math.floor(t["kg"]*2)/2, 1))]:
            if k in ups_tax: should = ups_tax[k]; checked = True; break
    if not checked: continue
    ms["checked"] += 1; ms["should"] += should
    # 费用说明分解 v3.2：运费项=速递/自动计费/运费(非赔偿)，其余全部视为已声明附加项
    comps = re.findall(r'([^;；:：]+)[:：]\s*(-?\d+\.?\d*)', t["fee_note"])
    base, surcharges, sur_total = t["amount"], [], 0.0
    for name, amt in comps:
        n = name.strip()
        v = num(amt)
        if v is None: continue
        if ("速递" in n or "自动计费" in n or ("运费" in n and "赔偿" not in n)):
            base = v  # 该项即运费本身（不论占比）
        else:
            surcharges.append((n[:16], v))
            sur_total += v
    # v3.2 核心：运费 = 总金额 − 已声明附加项（关税/产品附加费/退件费等），再与价格表应扣对比
    if surcharges:
        base = t["amount"] - sur_total
    diff = base - should
    tol = max(20, abs(should)*0.02)
    if abs(diff) > tol:
        ms["viol"] += 1; ms["viol_amt"] += diff
        violations.append({"no": t["no"], "mode": m, "dest": t["dest"], "kg": t["kg"],
                           "recv": t["recv"], "actual": t["amount"], "should": round(should, 1),
                           "diff": round(diff, 1),
                           "note": ("附加费:" + json.dumps(surcharges, ensure_ascii=False)[:70]) if surcharges else "运费基准差异"})

mode_rows = [{"mode": m, "tickets": ms["tickets"], "chargeable_kg": round(ms["kg"],1),
              "amount": round(ms["amount"],2),
              "should": round(ms["should"],2) if ms["checked"] else None,
              "checked": ms["checked"], "viol": ms["viol"], "viol_amt": round(ms["viol_amt"],2)}
             for m, ms in sorted(mode_stat.items(), key=lambda x: -x[1]["amount"])]
total = round(sum(ms["amount"] for ms in mode_stat.values()), 2)
checked_total = round(sum(ms["amount"] for ms in mode_stat.values() if ms["checked"]), 2)
out = {"generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
       "bill": os.path.basename(bill_file) + (f" ({label})" if label else ""),
       "price_version": f"v3 按收货日期匹配（{len(versions)} 个周版价格表）",
       "total_amount": total, "checked_total": checked_total,
       "no_version_tickets": no_version,
       "version_usage": {k: {"tickets": v[0], "amount": round(v[1],2)} for k, v in sorted(ver_stat.items())},
       "comp_rows": comp_rows, "rows": mode_rows, "violations": violations}
json.dump(out, open(os.path.join(DATA, out_name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{out_name}: 覆盖 ¥{checked_total}/{total} ({round(checked_total/total*100)}%) | 差异票 {len(violations)} | 净差异 {round(sum(v['diff'] for v in violations),2)} | 无版本票 {no_version}")
