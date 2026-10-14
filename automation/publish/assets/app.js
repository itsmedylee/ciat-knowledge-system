/* 학습 위키 HTML: 목록·테마·검색·목차·표지 이동·Mermaid·인쇄 */
(function () {
  var ROOT = window.__ROOT || "";
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  // 테마
  var saved = store.get("wiki-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  var btnTheme = document.querySelector(".btn-theme");
  if (btnTheme) btnTheme.addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme");
    var dark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    store.set("wiki-theme", next);
  });

  // 모바일 문서 목록
  var btnNav = document.querySelector(".btn-nav");
  if (btnNav) btnNav.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
  var scrim = document.querySelector(".scrim");
  if (scrim) scrim.addEventListener("click", function () { document.body.classList.remove("nav-open"); });
  var cur = document.querySelector(".side a.cur");
  if (cur) cur.scrollIntoView({ block: "center" });

  // 목차 현재 위치 표시
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (tocLinks.length && "IntersectionObserver" in window) {
    var map = {};
    tocLinks.forEach(function (a) { map[decodeURIComponent(a.getAttribute("href").slice(1))] = a; });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting && map[e.target.id]) {
          tocLinks.forEach(function (a) { a.classList.remove("on"); });
          map[e.target.id].classList.add("on");
        }
      });
    }, { rootMargin: "-60px 0px -70% 0px" });
    document.querySelectorAll(".content h2[id], .content h3[id]").forEach(function (h) { obs.observe(h); });
  }

  // 표지 순서대로 이동 (확인 필요·강사견해·LLM·개정안)
  var pos = {};
  document.querySelectorAll(".status a[data-jump]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      ev.preventDefault();
      var k = a.getAttribute("data-jump");
      var els = document.querySelectorAll(".content .mk-" + k);
      if (!els.length) return;
      pos[k] = ((pos[k] === undefined ? -1 : pos[k]) + 1) % els.length;
      var el = els[pos[k]];
      var d = el.closest("details"); if (d) d.open = true;
      el.scrollIntoView({ block: "center", behavior: "smooth" });
      el.classList.add("flash"); setTimeout(function () { el.classList.remove("flash"); }, 1600);
      a.setAttribute("title", (pos[k] + 1) + " / " + els.length);
    });
  });

  // 검색 (색인은 처음 입력할 때 불러온다)
  var q = document.getElementById("q"), box = document.getElementById("results"), loading = false, sel = -1;
  function loadIdx(cb) {
    if (window.__IDX) return cb();
    if (loading) return;
    loading = true;
    var s = document.createElement("script");
    s.src = ROOT + "assets/search-index.js";
    s.onload = cb;
    document.head.appendChild(s);
  }
  function esc(t) { return t.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function hl(t, terms) {
    var out = esc(t);
    terms.forEach(function (w) {
      if (!w) return;
      out = out.replace(new RegExp(esc(w).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), function (m) { return "<mark>" + m + "</mark>"; });
    });
    return out;
  }
  function run() {
    var v = q.value.trim().toLowerCase();
    if (!v) { box.hidden = true; return; }
    var terms = v.split(/\s+/);
    var res = [];
    window.__IDX.forEach(function (d) {
      var title = d.t.toLowerCase(), heads = d.h.join(" ").toLowerCase(), tags = d.g.join(" ").toLowerCase(), body = d.x.toLowerCase();
      var score = 0, ok = true;
      terms.forEach(function (w) {
        var s = 0;
        if (title.indexOf(w) >= 0) s += 30;
        if (heads.indexOf(w) >= 0) s += 12;
        if (tags.indexOf(w) >= 0) s += 8;
        var c = body.split(w).length - 1;
        if (c) s += Math.min(c, 20);
        if (!s) ok = false;
        score += s;
      });
      if (ok) res.push([score, d]);
    });
    res.sort(function (a, b) { return b[0] - a[0]; });
    sel = -1;
    if (!res.length) { box.innerHTML = '<div class="r-none">검색 결과가 없습니다.</div>'; box.hidden = false; return; }
    box.innerHTML = res.slice(0, 30).map(function (r) {
      var d = r[1], body = d.x, i = body.toLowerCase().indexOf(terms[0]);
      var snip = i >= 0 ? (i > 40 ? "…" : "") + body.slice(Math.max(0, i - 40), i + 90) + "…" : body.slice(0, 120) + "…";
      return '<a href="' + ROOT + d.p + '"><span class="r-t">' + hl(d.t, terms) + '</span><span class="r-l">' + d.l +
        '</span><span class="r-s">' + hl(snip, terms) + "</span></a>";
    }).join("");
    box.hidden = false;
  }
  if (q) {
    q.addEventListener("input", function () { loadIdx(run); });
    q.addEventListener("focus", function () { loadIdx(function () { if (q.value) run(); }); });
    q.addEventListener("keydown", function (e) {
      var items = box.querySelectorAll("a");
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
        items.forEach(function (a, i) { a.classList.toggle("on", i === sel); });
        if (items[sel]) items[sel].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && items.length) {
        location.href = items[sel >= 0 ? sel : 0].href;
      } else if (e.key === "Escape") { box.hidden = true; q.blur(); }
    });
    document.addEventListener("click", function (e) { if (!e.target.closest(".search")) box.hidden = true; });
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    });
  }

  // Mermaid
  window.addEventListener("load", function () {
    if (!window.mermaid) return;
    var dark = document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    window.mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "neutral", securityLevel: "strict",
      flowchart: { htmlLabels: true, useMaxWidth: true }, fontFamily: "inherit" });
    window.mermaid.run({ querySelector: "pre.mermaid" }).catch(function (err) { console.warn("mermaid", err); });
  });

  // 인쇄할 때 접힌 상자를 모두 펼친다
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll(".content details").forEach(function (d) { d.setAttribute("data-was", d.open ? "1" : "0"); d.open = true; });
  });
  window.addEventListener("afterprint", function () {
    document.querySelectorAll(".content details[data-was]").forEach(function (d) { d.open = d.getAttribute("data-was") === "1"; });
  });
})();
