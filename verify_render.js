// verify_render.js — 真实浏览器端到端渲染验证（登录→指挥舱→账单对账→小包达标）
const path = require("path");
const fs = require("fs");
const GAB = path.join(process.env.USERPROFILE || "C:\\Users\\cn", ".workbuddy");
let pw;
try { pw = require(path.join(GAB, "binaries", "node", "versions", "22.22.2", "node_modules", "@larksuite", "cli", "node_modules", "playwright-core")); }
catch (e) {
  try { pw = require(path.join(GAB, "binaries", "node", "versions", "22.22.2", "node_modules", "playwright-core")); }
  catch (e2) { console.error("playwright-core not found"); process.exit(2); }
}
const candidates = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
];
const exe = candidates.find(p => fs.existsSync(p));
if (!exe) { console.error("no browser exe found"); process.exit(2); }
console.log("browser:", exe.split("\\").pop());

(async () => {
  const browser = await pw.chromium.launch({ executablePath: exe, headless: true });
  const page = await browser.newPage({ viewport: { width: 1180, height: 900 } });
  const errors = [];
  page.on("pageerror", e => errors.push("PAGEERROR: " + e.message));
  page.on("console", m => { if (m.type() === "error") errors.push("CONSOLE: " + m.text().slice(0, 150)); });

  await page.goto("https://heryma99.github.io/logistics-monitor/", { waitUntil: "networkidle", timeout: 45000 }).catch(()=>{});
  await page.waitForTimeout(2000);
  // 登录
  const gateVisible = await page.isVisible("#gate-pwd").catch(()=>false);
  if (gateVisible) {
    await page.fill("#gate-pwd", "0000");
    await page.click("#gate-btn");
    await page.waitForTimeout(1500);
  }
  // 指挥舱渲染断言
  const navCount = await page.locator("#nav a").count();
  const kpiCount = await page.locator(".kpi").count();
  const genTime = await page.textContent("#gen-time").catch(() => "");
  await page.screenshot({ path: "shot_dashboard.png", fullPage: false });
  console.log("指挥舱: nav链接 =", navCount, "| KPI卡 =", kpiCount, "| 快照时间 =", (genTime||"").trim());

  // 账单对账
  await page.goto("https://heryma99.github.io/logistics-monitor/#recon");
  await page.waitForTimeout(1200);
  const reconCards = await page.locator("#page .card h3").allTextContents().catch(()=>[]);
  await page.screenshot({ path: "shot_recon.png", fullPage: false });
  console.log("账单对账卡片:", JSON.stringify(reconCards));

  // 小包达标
  await page.goto("https://heryma99.github.io/logistics-monitor/#xiaobao");
  await page.waitForTimeout(1200);
  await page.screenshot({ path: "shot_xiaobao.png", fullPage: false });
  const xrows = await page.locator("#page table tr").count();
  console.log("小包达标表行数:", xrows);

  // 合规中心
  await page.goto("https://heryma99.github.io/logistics-monitor/#compliance");
  await page.waitForTimeout(1000);
  await page.screenshot({ path: "shot_compliance.png", fullPage: false });

  console.log("JS 错误数:", errors.length);
  errors.slice(0, 5).forEach(e => console.log(" ", e));
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})();
