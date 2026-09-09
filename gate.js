/* gate.js — SHA-256 口令门禁（同比价易模式）
   口令哈希：LogiView@2026 的 SHA-256，修改口令=换哈希 */
(function(){
  var HASH = "dd4f17d0395c2e94ff61a0239bdd614cf1c05af3fe3feb0e7d98f01a0d2a27b6"; // LogiView@2026
  var KEY = "lmc_gate_ok";
  function hex(buf){
    return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,"0")).join("");
  }
  function sha256(s){
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)).then(hex);
  }
  window.Gate = {
    check: function(){
      if (sessionStorage.getItem(KEY) === "1") return true;
      return false;
    },
    unlock: async function(pwd){
      var h = await sha256(pwd);
      if (h === HASH){ sessionStorage.setItem(KEY,"1"); return true; }
      return false;
    },
    HASH: HASH
  };
})();
