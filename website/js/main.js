/* ============================================================
   MoonBite — main.js
   One orchestrated moment (the Counter resolve), then silence.
   No ambient motion, no trackers, no external calls.
   ============================================================ */
(function () {
  "use strict";

  // Footer year.
  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());

  // The single orchestrated moment: the number resolves from blur to crisp
  // and the one gold underline draws in — once, on load. Then nothing moves.
  var counter = document.getElementById("counter");
  var num = document.getElementById("counterNum");
  if (counter && num) {
    // Defer one frame so the transition actually runs from the blurred state.
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        num.classList.add("resolved");
        counter.classList.add("resolved");
      });
    });
  }
})();
