# -*- coding: utf-8 -*-
"""push_alerts.py — 每日告警摘要推送飞书群（机器人身份）
群：「物流监控告警」oc_d72d215430964bb9c22be6d60b9c7ec1（bot 为群主）
"""
import subprocess, json, os

NODE = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node.exe"
JS   = r"C:\Users\cn\.workbuddy\binaries\node\versions\22.22.2\node_modules\@larksuite\cli\scripts\run.js"
CHAT = "oc_d72d215430964bb9c22be6d60b9c7ec1"
HERE = os.path.dirname(os.path.abspath(__file__))

kpi = json.load(open(os.path.join(HERE, "data", "kpi.json"), encoding="utf-8"))
stg = json.load(open(os.path.join(HERE, "data", "staging.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "data", "staging.json")) else {"rows": []}
alerts = kpi.get("alerts") or []
pending = [x for x in stg.get("rows", []) if x.get("status") == "待确认"]

lines = [f"【物流监控告警】快照 {kpi.get('generated_at','')}",
         f"渠道达标 {kpi.get('channels_ok')}/{kpi.get('channels_total')} · 今日异常 {kpi.get('today_alerts')} · 暂存待确认 {len(pending)}", ""]
for a in alerts[:5]:
    lines.append(f"{a['level']}｜{a['text']}")
if len(alerts) > 5: lines.append(f"…另有 {len(alerts)-5} 条，详见看板")
if pending:
    lines.append("")
    lines.append("暂存待确认（跟单员核对后转登记表）：")
    for p in pending[:5]:
        lines.append(f"{p.get('no')}｜{p.get('level')}｜{(p.get('desc') or '')[:40]}")
lines.append("")
lines.append("看板：https://heryma99.github.io/logistics-monitor/")
msg = "\n".join(lines)

body = json.dumps({"text": msg}, ensure_ascii=False)
r = subprocess.run([NODE, JS, "im", "+messages-send", "--as", "bot", "--chat-id", CHAT,
                    "--msg-type", "text", "--content", body],
                   capture_output=True, text=True, encoding="utf-8")
out = r.stdout[:200]
print("PUSH:", "OK" if '"ok": true' in out else out)
