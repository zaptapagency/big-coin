/* ============================================================
   Spark — browser mining REHEARSAL (honest).
   - Real CPU throughput probe via Web Workers (a SHA-256 stand-in
     integer-mix loop). It is NOT the real RandomX PoW and earns
     NO coins. Everything the user sees is literally true.
   - Consent gates every cycle. Stop terminates all workers.
   - On-battery devices auto-pause below 20% (when the API exists).
   No trackers, no network calls.
   ============================================================ */
(function () {
  "use strict";

  var THREAD_STEPS = [1, 2, 4, 8];
  var LABELS = ["LOW", "MEDIUM", "HIGH", "MAX"];

  var maxCores = (navigator.hardwareConcurrency && navigator.hardwareConcurrency > 0)
    ? navigator.hardwareConcurrency : 4;

  // Cap the tick choices to the machine's real core count (never claim more).
  var steps = THREAD_STEPS.filter(function (n) { return n <= maxCores; });
  if (steps.length === 0) steps = [1];
  if (steps[steps.length - 1] !== maxCores && maxCores < 8) steps.push(maxCores);

  var el = function (id) { return document.getElementById(id); };
  el("maxThreads").textContent = String(maxCores);

  var slider = el("intensity");
  slider.max = String(steps.length - 1);
  slider.value = "0";

  function selectedThreads() { return steps[parseInt(slider.value, 10)] || 1; }
  function selectedLabel() {
    var i = parseInt(slider.value, 10);
    return LABELS[Math.min(i, LABELS.length - 1)];
  }
  function syncSlider() {
    el("useThreads").textContent = String(selectedThreads());
    el("intensityLabel").textContent = selectedLabel();
  }
  slider.addEventListener("input", syncSlider);
  syncSlider();

  // ---- Worker source (self-contained via Blob) ----
  var workerSrc = [
    "var running=true;",
    "self.onmessage=function(e){ if(e.data && e.data.cmd==='stop'){ running=false; } };",
    "function mix(x){ x^=x<<13; x^=x>>>7; x^=x<<17; return x>>>0; }",
    "var x=(Math.random()*4294967295)>>>0, count=0, last=performance.now();",
    "function chunk(){",
    "  if(!running) return;",
    "  for(var i=0;i<150000;i++){ x=mix(x); count++; }",
    "  var now=performance.now();",
    "  if(now-last>200){ self.postMessage(count); count=0; last=now; }",
    "  setTimeout(chunk,0);",
    "}",
    "chunk();"
  ].join("\n");
  var workerUrl = URL.createObjectURL(new Blob([workerSrc], { type: "text/javascript" }));

  var workers = [];
  var running = false;
  var sessionCycles = 0;
  var windowCycles = 0;
  var windowStart = 0;
  var rafId = null;

  function fmt(n) { return Math.round(n).toLocaleString(); }

  function startMining() {
    var n = selectedThreads();
    running = true;
    sessionCycles = 0; windowCycles = 0; windowStart = performance.now();

    for (var i = 0; i < n; i++) {
      var w = new Worker(workerUrl);
      w.onmessage = function (e) {
        if (!running) return;
        sessionCycles += e.data;
        windowCycles += e.data;
      };
      workers.push(w);
    }

    el("consent").hidden = true;
    el("mining").hidden = false;
    el("stopBtn").hidden = false;
    var t = el("thermal"); t.hidden = false;
    setThermal(n);
    tick();
    watchBattery();
  }

  function setThermal(n) {
    var dots = document.querySelectorAll(".thermal__dot");
    var lit = n <= steps[0] ? 1 : (n >= maxCores ? 3 : 2);
    dots.forEach(function (d, i) {
      d.classList.toggle("on", i < lit && lit < 3);
      d.classList.toggle("warn", lit === 3 && i < lit);
    });
  }

  function tick() {
    el("probeNum").textContent = fmt(sessionCycles);
    var now = performance.now();
    var dt = (now - windowStart) / 1000;
    if (dt >= 0.5) {
      el("rate").textContent = fmt(windowCycles / dt);
      windowCycles = 0; windowStart = now;
    }
    if (running) rafId = requestAnimationFrame(tick);
  }

  function stopMining(reason) {
    running = false;
    workers.forEach(function (w) { try { w.postMessage({ cmd: "stop" }); w.terminate(); } catch (e) {} });
    workers = [];
    if (rafId) cancelAnimationFrame(rafId);
    el("stopBtn").hidden = true;
    el("thermal").hidden = true;
    if (reason) {
      showToast(reason);
    } else {
      // Return to consent, honestly reset.
      el("mining").hidden = true;
      el("consent").hidden = false;
    }
  }

  function showToast(msg) {
    var t = el("toast");
    t.textContent = msg;
    t.hidden = false;
  }

  // ---- Battery guard (honest, only if the API exists) ----
  function watchBattery() {
    if (!navigator.getBattery) return;
    navigator.getBattery().then(function (batt) {
      function check() {
        if (running && !batt.charging && batt.level < 0.2) {
          stopMining("Battery under 20% — Spark paused to protect your device. Resume when charging.");
        }
      }
      batt.addEventListener("levelchange", check);
      batt.addEventListener("chargingchange", check);
      check();
      // Also surface a real battery reading on the consent line for next time.
      var pct = Math.round(batt.level * 100);
      el("battLine").textContent =
        "This device is at " + pct + "% " + (batt.charging ? "(charging)" : "(on battery)") +
        "; on battery, Spark pauses below 20%.";
    }).catch(function () {});
  }
  // Populate battery line on load too.
  watchBattery();

  el("startBtn").addEventListener("click", startMining);
  el("stopBtn").addEventListener("click", function () { stopMining(null); });
  el("declineBtn").addEventListener("click", function () {
    el("consent").querySelectorAll("input,button").forEach(function (n) {
      if (n.id !== "declineBtn") n.setAttribute("disabled", "disabled");
    });
    el("declinedMsg").hidden = false;
  });

  // ============================================================
  // Mine to the LIVE chain — asks the explorer to mine one block
  // to your address (the node does the real proof-of-work).
  // ============================================================
  (function liveMine() {
    var urlInput = el("explorerUrl");
    var addrInput = el("mineAddress");
    var btn = el("mineLiveBtn");
    var status = el("liveStatus");
    if (!urlInput || !addrInput || !btn) return;

    // Prefill explorer URL from ?api=..., then localStorage, then the live default.
    var DEFAULT_EXPLORER = "https://moonbite-production.up.railway.app";
    var params = new URLSearchParams(location.search);
    var apiParam = params.get("api");
    if (apiParam) {
      urlInput.value = apiParam;
      try { localStorage.setItem("moonbite_explorer", apiParam); } catch (e) {}
    } else {
      try {
        var saved = localStorage.getItem("moonbite_explorer");
        if (saved) urlInput.value = saved;
      } catch (e) {}
    }
    if (!urlInput.value) urlInput.value = DEFAULT_EXPLORER;
    try {
      var savedAddr = localStorage.getItem("moonbite_address");
      if (savedAddr) addrInput.value = savedAddr;
    } catch (e) {}

    function setStatus(msg, kind) {
      status.hidden = false;
      status.textContent = msg;
      status.className = "livemine__status mono" + (kind ? " is-" + kind : "");
    }

    function normBase(u) {
      u = (u || "").trim().replace(/\/+$/, "");
      if (u && !/^https?:\/\//i.test(u)) u = "https://" + u;
      return u;
    }

    var busy = false;
    btn.addEventListener("click", function () {
      if (busy) return;
      var base = normBase(urlInput.value);
      var addr = addrInput.value.trim();
      if (!base) { setStatus("Enter your explorer URL first.", "err"); return; }
      if (!addr) { setStatus("Enter your MoonBite reward address.", "err"); return; }
      try {
        localStorage.setItem("moonbite_explorer", base);
        localStorage.setItem("moonbite_address", addr);
      } catch (e) {}

      busy = true;
      btn.setAttribute("disabled", "disabled");
      setStatus("Mining… the node is doing the proof-of-work.", "busy");

      fetch(base + "/api/mine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: addr })
      }).then(function (r) {
        return r.json().then(function (body) { return { ok: r.ok, body: body }; });
      }).then(function (res) {
        if (!res.ok) {
          setStatus("Node says: " + (res.body.error || "mining failed") , "err");
        } else if (res.body.found) {
          setStatus("Block #" + res.body.height + " mined to you ✓  " + res.body.hashes[0], "ok");
        } else {
          setStatus("No block this round — click again to keep trying.", "busy");
        }
      }).catch(function (e) {
        setStatus("Could not reach explorer at " + base + " (" + e.message + ").", "err");
      }).then(function () {
        busy = false;
        btn.removeAttribute("disabled");
      });
    });
  })();
})();
