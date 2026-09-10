/* 物流监控中心 SPA — M1
   页面：指挥舱 / 价格中心 / 小包达标 / 账单对账(壳) / 在途(壳) / 仓库 / 合规(壳) / 质量与告警
   数据：data/*.json 快照（bake_data.py 产出）*/
var App = (function(){
  var PAGES = [
    ["dashboard","指挥舱"],["price","价格中心"],["xiaobao","小包达标"],
    ["recon","账单对账"],["transit","在途监控"],["warehouse","仓库看板"],
    ["compliance","合规中心"],["quality","质量与告警"]
  ];
  var D = {}; // data cache
  function fetchJSON(f){ return fetch("data/"+f).then(r=>r.json()).catch(()=>null); }

  function pill(level){ return '<span class="pill '+({红:"red",不达标:"red",黄:"amber",观察:"amber",达标:"green",绿:"green",gray:"gray"}[level]||"gray")+'">'+level+"</span>"; }

  /* ---------- pages ---------- */
  function dashboard(){
    var k = D.kpi || {};
    var domains = (k.domains||[]).map(d=>'<div class="card" style="margin:0"><div class="flex"><span class="dot '+d.level+'"></span><b style="font-size:13px">'+d.name+'</b></div><div class="muted" style="margin-top:4px">'+d.note+"</div></div>").join("");
    var alerts = (k.alerts||[]).map(a=>'<tr><td style="width:44px">'+pill(a.level)+'</td><td>'+a.text+'</td><td style="width:110px;color:var(--tx2)">'+a.src+' · '+a.rule+'</td><td style="width:52px;color:var(--blue)">去处理</td></tr>').join("");
    return '<h2 class="pt">指挥舱</h2><p class="sub">快照 '+k.generated_at+'</p>'
      + '<div class="kpis">'
      + '<div class="kpi"><div class="l">今日异常</div><div class="v red">'+(k.today_alerts||0)+"</div></div>"
      + '<div class="kpi"><div class="l">超期线路</div><div class="v amber">'+(k.overdue_lanes||0)+"</div></div>"
      + '<div class="kpi"><div class="l">渠道达标</div><div class="v green">'+(k.channels_ok||0)+" / "+(k.channels_total||0)+"</div></div>"
      + '<div class="kpi"><div class="l">未完结异常单</div><div class="v">'+(k.open_tickets||0)+"</div></div>"
      + '<div class="kpi"><div class="l">暂存待确认</div><div class="v amber">'+(k.staging_pending||0)+"</div></div></div>"
      + '<h3 style="font-size:13.5px;margin-bottom:8px">八域健康度</h3><div class="grid2" style="margin-bottom:16px">'+domains+"</div>"
      + '<div class="card"><h3>今日异常清单</h3><table><tr><th style="width:44px">级别</th><th>异常</th><th style="width:110px">来源</th><th style="width:52px">操作</th></tr>'+(alerts||'<tr><td colspan=4 class="muted">暂无异常 🎉</td></tr>')+"</table></div>";
  }

  function price(){
    var q = (D.quotes&&D.quotes.quotes)||{};
    function chg(v){
      if (v===null||v===undefined) return '<span style="color:var(--tx3)">-</span>';
      var c = v>0?"var(--red)":v<0?"var(--green)":"var(--tx2)";
      return '<span style="color:'+c+'">'+(v>0?"+":"")+v+"%</span>";
    }
    function rows(arr,unit){
      return (arr||[]).slice(0,12).map(x=>"<tr><td>"+(x.channel||"-")+'</td><td>'+(x.region||"-")+'</td><td>'+(x.p21||"-")+"</td><td>"+chg(x.chg21)+'</td><td>'+(x.p101||"-")+"</td><td>"+chg(x.chg101)+'</td><td style="color:var(--tx2)">'+(x.updated||"-").slice(0,10)+"</td></tr>").join("");
    }
    return '<h2 class="pt">价格中心</h2><p class="sub">大货报价最新快照（来源：周报 Base 报价表，带更新日期）· 环比版本对比随管道二期接入</p>'
      + '<div class="card"><h3>美国空派（¥/kg，21KG+ / 101KG+）</h3><table><tr><th>渠道</th><th>分区</th><th>21KG+</th><th>环比</th><th>101KG+</th><th>环比</th><th>更新日期</th></tr>'+rows(q.air_us)+"</table></div>"
      + '<div class="card"><h3>美森海运（¥/kg）</h3><table><tr><th>渠道</th><th>分区</th><th>21KG+</th><th>环比</th><th>101KG+</th><th>环比</th><th>更新日期</th></tr>'+rows(q.sea_us)+"</table></div>"
      + '<div class="card"><h3>英国渠道</h3><table><tr><th>渠道</th><th>生效日</th><th>21kg+</th><th>101kg+</th></tr>'+rows(q.uk)+"</table></div>";
  }

  function xiaobao(){
    var rows = (D.xiaobao&&D.xiaobao.rows)||[];
    var tr = rows.slice(0,40).map(x=>'<tr><td'+(x.status==="不达标"?' style="color:var(--red);font-weight:500"':x.status==="观察"?' style="color:var(--amber)"':'')+">"+x.channel+'</td><td>'+x.country+'</td><td>'+x.pkg+'</td><td>'+(x.std_days||"-")+'</td><td style="color:'+(x.ontime_rate<80?"var(--red)":x.ontime_rate<85?"var(--amber)":"var(--green)")+'">'+x.ontime_rate+"%</td><td>"+x.over30_rate+"%</td><td>"+pill(x.status)+"</td></tr>").join("");
    var bl = (D.baseline&&D.baseline.baseline)||[];
    var suspicious = bl.filter(b=>b.pkg>0).map(b=>b.pkg);
    var dup = suspicious.length>2 && suspicious.filter(v=>v===suspicious[1]).length>=2;
    var tr2 = bl.map(b=>{
      var color = b.ontime_rate<85?"var(--red)":b.ontime_rate<90?"var(--amber)":"var(--green)";
      return '<tr><td style="width:56px">'+b.month+'</td><td>'+b.pkg+'</td>'
        + '<td><div class="bar"><i style="width:'+Math.min(100,b.ontime_rate)+'%;background:'+color+'"></i></div></td>'
        + '<td style="color:'+color+'">'+b.ontime_rate+"%</td><td>"+b.lanes+'</td><td style="color:'+(b.bad_lanes>50?"var(--amber)":"var(--tx2)")+'">'+b.bad_lanes+"</td></tr>";
    }).join("");
    var trend = '<div class="card"><h3>月度趋势（KPI 基线 N3 · 双口径对比）</h3>'
      + '<table><tr><th>月份</th><th>包裹</th><th style="width:24%">口径A 时效内签收率(按包裹加权)</th><th>口径B 线路达标率(按线路)</th><th>线路</th><th>不达标</th></tr>'+tr2+"</table>"
      + (dup?'<p class="muted" style="margin-top:8px">⚠ 数据质量疑点：26-03/04/05 三个月包裹数完全相同（26,729），疑似月度表复制未更新——已列入治理清单，基线以 25-10~26-02 与 26-06/07 为准。</p>':"")
      + '<p class="muted" style="margin-top:4px">📌 口径已定（双轨制，2026-09-10）：北极星 N3 用口径A 按包裹加权（当前 92.8%，客户体验），运营考核用口径B 按线路达标（当前 64%，渠道覆盖面）——已写入指标字典，如需调整随时改。</p>'
      + "</div>";
    return '<h2 class="pt">小包时效达标</h2><p class="sub">口径：时效内签收率 = 时效内签收 ÷ 包裹数；判定 A15（<85% 黄）/ A16（<80% 或超30天>5% 红）· 当前月：26年7月时效表</p>'
      + '<div class="card"><table><tr><th>渠道</th><th>国家</th><th>包裹</th><th>标准(天)</th><th>时效内签收</th><th>超30天占比</th><th>判定</th></tr>'+tr+"</table></div>";
  }

  function warehouse(){
    var list = (D.warehouse&&D.warehouse.warehouses)||[];
    var tr = list.map(w=>{
      var cap = w.ending + w.transit;
      return '<tr><td>'+w.warehouse+'</td><td>'+w.ym+'</td><td>'+w.ending+'</td><td>'+w.transit+'</td><td>'+w.outbound+'</td><td>'+(w.turnover_days||"-")+"</td></tr>";
    }).join("");
    var fee = (D.fee&&D.fee.rows)||[];
    var fk = ["0-30天","31-60天","61-90天","91-120天","121-180天","181-270天天","271-360天","360天以上"];
    var fr = fee.slice(0,10).map(x=>'<tr><td>'+esc(x["海外仓"])+'</td><td>'+esc(x["计费单位"])+'</td><td>'+esc(x["币种"])+'</td>'+fk.map(k=>"<td>"+esc(x[k])+"</td>").join("")+"</tr>").join("");
    return '<h2 class="pt">仓库看板</h2><p class="sub">海外仓库存与周转（东莞6子仓库容数据走人工导入模板，M2 接入）</p>'
      + '<div class="card"><table><tr><th>仓库</th><th>月份</th><th>期末库存</th><th>在途</th><th>本月出库</th><th>周转天数</th></tr>'+tr+"</table></div>"
      + '<div class="card"><h3>仓储费计费标准（库龄段，对账基准 · M2 启用核对）</h3><div style="overflow-x:auto"><table><tr><th>海外仓</th><th>计费单位</th><th>币种</th>'+fk.map(k=>"<th>"+k+"</th>").join("")+"</tr>"+fr+"</table></div></div>";
  }

  function shell(title, note){
    return '<h2 class="pt">'+title+'</h2><p class="sub">'+note+"</p>"+'<div class="soon">本模块按台账排期于 M2/M3 上线<br>规格见《物流监控中心PRD-v1.3.md》</div>';
  }

  function quality(){
    var rows = (D.quality&&D.quality.rows)||[];
    var tr = rows.slice(0,15).map(x=>'<tr><td>'+x.provider+'</td><td>'+x.problems+'</td><td>'+x.closed+'</td><td>'+x.open+"</td><td>"+(x.close_rate||0)+"%</td></tr>").join("");
    var alerts = ((D.kpi&&D.kpi.alerts)||[]).map(a=>'<tr><td style="width:44px">'+pill(a.level)+"</td><td>"+a.text+'</td><td style="width:60px">'+a.rule+"</td></tr>").join("");
    var stg = ((D.staging&&D.staging.rows)||[]).map(x=>'<tr><td style="width:56px">'+esc(x.no)+'</td><td style="width:44px">'+pill(esc(x.level))+'</td><td>'+esc(x.desc)+'</td><td style="width:60px;color:var(--tx2)">'+esc(x.rule)+'</td><td style="width:76px">'+pill(esc(x.status||"待确认"))+"</td></tr>").join("");
    return '<h2 class="pt">质量与告警中心</h2><p class="sub">异常按物流商聚合（来源：B2C异常问题表）· 逐票工单走跨部门异常单体系</p>'
      + '<div class="card"><h3>暂存异常（自动发现 · 核对后转登记表）</h3><table><tr><th>编号</th><th>级别</th><th>描述</th><th>规则</th><th>状态</th></tr>'+(stg||'<tr><td colspan=5 class="muted">暂无</td></tr>')+"</table></div>"
      + '<div class="card"><h3>告警历史（A 系列规则触发）</h3><table><tr><th style="width:44px">级别</th><th>告警</th><th style="width:60px">规则</th></tr>'+(alerts||'<tr><td colspan=3 class="muted">暂无</td></tr>')+"</table></div>"
      + (function(){
          var dd = D.dictionary||{};
          function pills(list){
            var clean = (list||[]).filter(x=>x && x.length<=12 && !/^\d{4}\//.test(x));
            var dirty = (list||[]).length - clean.length;
            var ps = clean.map(x=>'<span class="pill gray" style="margin:2px">'+esc(x)+"</span>").join("");
            return ps + (dirty>0?'<p class="muted" style="margin-top:6px">⚠ 检测到 '+dirty+' 个被污染的选项（日期/长文本误存为选项）——已列入月度盘点治理清单</p>':"");
          }
          return '<div class="card"><h3>问题类型字典（M2-4 · 取自现有字段选项）</h3>'
            + '<p class="muted">跟进类型：</p><div>'+pills(dd["跟进类型"])+"</div>"
            + '<p class="muted" style="margin-top:8px">跟进状态：</p><div>'+pills(dd["跟进状态"])+"</div></div>";
        })()
      + '<div class="card"><h3>物流商异常聚合</h3><table><tr><th>物流商</th><th>问题数</th><th>已完结</th><th>未完结</th><th>完结率</th></tr>'+tr+"</table></div>";
  }

  function recon(){
    var rc = D.recon||{};
    var rows = (rc.rows||[]).map(x=>'<tr><td>'+x.mode+'</td><td>'+x.tickets+'</td><td style="color:var(--tx2)">'+(x.should!=null?x.should:"—")+'</td><td style="color:var(--tx)">'+x.amount+'</td><td>'+(x.should!=null?pill(x.viol>0?"黄":"green"):pill("gray"))+(x.should!=null?' <span class="muted">'+x.viol+'票</span>':'')+'</td><td style="color:var(--tx2)">'+(x.viol_amt!=null&&x.viol_amt!=0?(x.viol_amt>0?"+":"")+Math.round(x.viol_amt):'—')+'</td></tr>').join("");
    var viols = (rc.violations||[]).slice(0,15).map(v=>'<tr><td style="color:var(--tx2)">'+(v.no||"").slice(0,18)+'</td><td>'+v.mode+'</td><td>'+v.dest+'</td><td>'+v.kg+'</td><td>'+v.actual+'</td><td style="color:var(--tx2)">'+v.should+'</td><td style="color:'+(v.diff>0?"var(--red)":"var(--green)")+'">'+(v.diff>0?"+":"")+v.diff+'</td><td class="muted">'+(v.note||"查表差异")+'</td></tr>').join("");
    var viol_amt = (rc.violations||[]).reduce((s,x)=>s+x.diff,0);
    return '<h2 class="pt">账单对账</h2><p class="sub">'+(rc.bill||"")+' · 自动抓取解析 · 应扣引擎 v1（覆盖3模式75%金额）· 注意：当前用9-8版价格表核对8月账单，存在版本错位，复核用8-25版进行中</p>'
      + '<div class="kpis"><div class="kpi"><div class="l">账单总额（实扣）</div><div class="v">¥'+(rc.total_amount||0)+'</div></div>'
      + '<div class="kpi"><div class="l">引擎覆盖</div><div class="v">¥'+(rc.checked_total||0)+'</div></div>'
      + '<div class="kpi"><div class="l">差异票</div><div class="v amber">'+(rc.violations||[]).length+'</div></div>'
      + '<div class="kpi"><div class="l">差异净额</div><div class="v amber">'+(viol_amt>0?"+":"")+Math.round(viol_amt)+'</div></div></div>'
      + '<div class="card"><h3>按运输方式汇总（应扣引擎核对）</h3><table><tr><th>运输方式</th><th>票数</th><th>应扣(参考)</th><th>实扣(元)</th><th>核对</th><th>差异额</th></tr>'+rows+"</table></div>"
      + (function(){
          var cs = (D.carriers&&D.carriers.carriers)||[];
          var tr = cs.map(c=>'<tr><td>'+c.carrier+'</td><td>'+c.period+'</td><td>'+c.tickets+'</td><td style="color:var(--tx)">¥'+c.total_amount+'</td><td class="muted">应扣待适配</td></tr>').join("");
          return '<div class="card"><h3>其他承运商账单（实扣侧）</h3><table><tr><th>承运商</th><th>账期</th><th>票数</th><th>金额</th><th>核对状态</th></tr>'+tr+"</table></div>";
        })()
      + '<div class="card"><h3>差异票明细（Top15）</h3><table><tr><th>单号</th><th>运输方式</th><th>目的国</th><th>计费重</th><th>实扣</th><th>应扣参考</th><th>差异</th><th>备注</th></tr>'+viols+"</table></div>"
      + (function(){
          var rs = (D.reconSummary&&D.reconSummary.months)||[];
          var tr = rs.map(x=>'<tr><td>'+x.month+'</td><td>¥'+x.total+'</td><td>'+x.coverage+'%</td><td>'+x.viol+'</td><td style="color:'+(x.pos>0?"var(--red)":"var(--tx2)")+'">'+(x.pos||"0")+'</td><td style="color:var(--tx2)">'+(x.neg||"0")+'</td><td style="color:'+(x.net>0?"var(--red)":"var(--green)")+'">'+x.net+'</td><td class="muted">'+x.pv+"</td></tr>").join("");
          return '<div class="card"><h3>历史核验汇总（中运通达 · 逐月）</h3><table><tr><th>账期</th><th>账单总额</th><th>引擎覆盖</th><th>差异票</th><th>正差异</th><th>负差异(退费/赔偿)</th><th>净差异</th><th>核验用价格表</th></tr>'+tr+"</table>"
            + '<p class="muted" style="margin-top:6px">5月高差异主因：整月横跨多个周版价格表而 v2 用单一版本核验——v3 已按每票收货日期匹配当周生效版本。</p></div>';
        })();
  }
  function transit(){
    var st = (D.transit&&D.transit.stats)||{};
    var rows = (D.transit&&D.transit.rows)||[];
    var tr = rows.map(x=>'<tr><td style="width:44px">'+pill(x.level||"灰")+'</td><td>'+esc(x.fba)+'</td><td>'+esc(x.channel||"-")+'</td><td style="color:var(--tx2)">'+esc(x.carrier||"-")+'</td><td>'+esc(x.dest||"-")+'</td><td style="color:var(--tx2)">'+esc(x.atd||"-")+'</td><td>'+esc(x.eta||"-")+'</td><td style="color:'+(x.delay_days>0?"var(--red)":"var(--tx2)")+'">'+(x.delay_days!=null&&x.delay_days>0?("+ "+x.delay_days+" 天"):(x.ata?"已签收":"在途"))+'</td><td>'+((x.check||"").indexOf("是")>=0?pill("红"):"—")+"</td></tr>").join("");
    return '<h2 class="pt">在途监控 · FBA 线</h2><p class="sub">ATD 已发出未签收的货件 · 延误=ETA 已过 · 查验票自动标红 · 数据源：FBA发货明细（脚本同步，快照 '+((D.transit&&D.transit.generated_at)||"")+'）</p>'
      + '<div class="kpis">'
      + '<div class="kpi"><div class="l">在途批次</div><div class="v">'+(st.intransit||0)+'</div></div>'
      + '<div class="kpi"><div class="l">ETA 已超</div><div class="v amber">'+(st.delayed||0)+'</div></div>'
      + '<div class="kpi"><div class="l">查验</div><div class="v red">'+(st.chaxun||0)+'</div></div>'
      + '<div class="kpi"><div class="l">已签收</div><div class="v green">'+(st.arrived||0)+'</div></div></div>'
      + '<div class="card"><table><tr><th>状态</th><th>FBA 货件号</th><th>渠道</th><th>物流商</th><th>目的国</th><th>ATD</th><th>ETA</th><th>时效</th><th>查验</th></tr>'+tr+"</table></div>"
      + '<p class="muted">半月账单/DPEX 线与云途轨迹 API（逐票 14 节点归因）按台账 M3 接入。</p>';
  }
  function compliance(){
    var rows = (D.compliance&&D.compliance.rows)||[];
    var tr = rows.map(x=>'<tr><td style="width:44px">'+pill(x.level||"灰")+'</td><td>'+esc(x.todo)+'</td><td style="width:80px;color:var(--tx2)">'+esc(x.deadline||"-")+'</td><td style="width:70px">'+(x.days_left!=null?x.days_left+" 天":"-")+'</td><td style="width:60px">'+esc(x.priority||"-")+'</td><td style="width:76px">'+esc(x.owner||"-")+"</td></tr>").join("");
    return '<h2 class="pt">合规中心</h2><p class="sub">物流新政策/证照待办倒计时（A8：<15 天红 · <30 天黄）· 数据源：物流新政策跟进表 · 已完成项不显示</p>'
      + '<div class="card"><table><tr><th>级别</th><th>待办事项</th><th>截止日期</th><th>剩余</th><th>优先级</th><th>执行人</th></tr>'+(tr||'<tr><td colspan=6 class="muted">暂无待办 🎉</td></tr>')+"</table></div>";
  }

  var R = {dashboard:dashboard, price:price, xiaobao:xiaobao, recon:recon, transit:transit, warehouse:warehouse, compliance:compliance, quality:quality};

  function route(){
    var h = (location.hash||"#dashboard").slice(1);
    if (!R[h]) h = "dashboard";
    document.getElementById("page").innerHTML = R[h]();
    document.querySelectorAll("#nav a").forEach(a=>a.classList.toggle("on", a.hash==="#"+h));
  }

  async function load(){
    var rs = await Promise.all([fetchJSON("kpi.json"),fetchJSON("quotes.json"),fetchJSON("xiaobao.json"),fetchJSON("warehouse.json"),fetchJSON("quality.json"),fetchJSON("staging.json"),fetchJSON("fee.json"),fetchJSON("dictionary.json"),fetchJSON("baseline.json"),fetchJSON("recon.json"),fetchJSON("recon_summary.json"),fetchJSON("carriers.json"),fetchJSON("compliance.json"),fetchJSON("transit.json")]);
    D.kpi=rs[0]; D.quotes=rs[1]; D.xiaobao=rs[2]; D.warehouse=rs[3]; D.quality=rs[4]; D.staging=rs[5]; D.fee=rs[6]; D.dictionary=rs[7]; D.baseline=rs[8]; D.recon=rs[9]; D.reconSummary=rs[10]; D.carriers=rs[11]; D.compliance=rs[12]; D.transit=rs[13];
    document.getElementById("gen-time").textContent = (D.kpi&&D.kpi.generated_at)||"-";
    var fb = document.getElementById("fresh-badge");
    if (D.kpi&&D.kpi.generated_at){ fb.textContent="数据已加载"; fb.className="badge ok"; } else { fb.textContent="数据未加载"; fb.className="badge stale"; }
    route();
  }

  function initNav(){
    document.getElementById("nav").innerHTML = PAGES.map(p=>'<a href="#'+p[0]+'">'+p[1]+"</a>").join("");
  }

  function openReport(){ document.getElementById("modal").classList.remove("hidden"); }
  function closeReport(){ document.getElementById("modal").classList.add("hidden"); }
  function submitReport(){
    var desc = document.getElementById("r-desc").value.trim();
    var msg = document.getElementById("r-msg");
    if (!desc){ msg.textContent = "请填写异常描述"; return; }
    msg.textContent = "已记录到本地队列。M1 联调后：提交 → 自动写「自动异常暂存表」→ 飞书推送。当前为前端演示路径。";
  }

  window.addEventListener("hashchange", route);
  return { init: function(){ initNav(); load(); }, route: route, openReport: openReport, closeReport: closeReport, submitReport: submitReport };
})();

App.init();
