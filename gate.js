/* gate.js — SHA-256 口令门禁（含 UI 接线）
   口令：0000（SHA-256 存哈希，改口令=换哈希） */
(function(){
  var HASH = "9af15b336e6a9619928537df30b2e6a2376569fcf9d7e773eccede65606529a0";
  var KEY = "lmc_gate_ok";

  function hex(buf){
    return Array.from(new Uint8Array(buf)).map(function(b){return b.toString(16).padStart(2,"0");}).join("");
  }
  function sha256(s){
    if (!(window.crypto && crypto.subtle)) return Promise.reject(new Error("no-subtle"));
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)).then(hex);
  }
  function showGate(show){
    var g = document.getElementById("gate"), a = document.getElementById("app");
    g.style.display = show ? "flex" : "none";
    a.classList.toggle("hidden", show);
  }
  function init(){
    if (sessionStorage.getItem(KEY) === "1"){ showGate(false); return; }
    showGate(true);
    var btn = document.getElementById("gate-btn"),
        pwd = document.getElementById("gate-pwd"),
        err = document.getElementById("gate-err");
    function tryIn(){
      var v = (pwd.value || "").trim();
      if (!v){ err.textContent = "请输入口令"; return; }
      sha256(v).then(function(h){
        if (h === HASH){
          sessionStorage.setItem(KEY, "1");
          showGate(false); pwd.value = ""; err.textContent = "";
        } else {
          err.textContent = "口令不正确";
        }
      }).catch(function(){
        err.textContent = "当前浏览器不支持加密校验，请用系统 Chrome/Edge 打开";
      });
    }
    btn.addEventListener("click", tryIn);
    pwd.addEventListener("keydown", function(e){ if (e.key === "Enter") tryIn(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
