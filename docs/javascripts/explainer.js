// The interactive intensity-duration plane of docs/explainer.md. No library,
// no network beyond its own data file: everything runs in the browser.
(() => {
  "use strict";
  const root = document.querySelector(".rt-explainer");
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const W = 640, H = 420, M = { l: 56, r: 16, t: 12, b: 44 };
  const X0 = 0, X1 = Math.log10(1000), Y0 = -2, Y1 = 2;
  const X = (d) => M.l + ((Math.log10(d) - X0) / (X1 - X0)) * (W - M.l - M.r);
  const Y = (i) => H - M.b - ((Math.log10(i) - Y0) / (Y1 - Y0)) * (H - M.t - M.b);
  const fmt = (x, n = 1) => x.toLocaleString("en-GB", { maximumFractionDigits: n });
  let data = null;

  function node(tag, attrs, text) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function threshold(key) {
    const t = data.thresholds[key];
    return {
      ...t,
      intensity: (d) => t.alpha * d ** -t.beta,
      cumulated: (d) => t.alpha * d ** (1 - t.beta),
    };
  }

  function draw() {
    const region = $("rt-region").value;
    const key = region === "italy" ? "italy" : data.regions[region];
    const t = threshold(key);
    const d = 10 ** Number($("rt-d").value);
    const e = 10 ** Number($("rt-e").value);
    const i = e / d;
    $("rt-d-out").textContent = fmt(d, d < 10 ? 1 : 0);
    $("rt-e-out").textContent = fmt(e, e < 10 ? 1 : 0);

    const svg = $("rt-plane");
    svg.replaceChildren();
    for (let k = 0; k <= 3; k++) {
      svg.append(node("line", { x1: X(10 ** k), x2: X(10 ** k), y1: M.t, y2: H - M.b, class: "rt-grid" }));
      svg.append(node("text", { x: X(10 ** k), y: H - M.b + 16, "text-anchor": "middle" }, String(10 ** k)));
    }
    for (let k = -2; k <= 2; k++) {
      svg.append(node("line", { x1: M.l, x2: W - M.r, y1: Y(10 ** k), y2: Y(10 ** k), class: "rt-grid" }));
      svg.append(node("text", { x: M.l - 6, y: Y(10 ** k) + 4, "text-anchor": "end" }, String(10 ** k)));
    }
    svg.append(node("text", { x: (W + M.l) / 2, y: H - 6, "text-anchor": "middle" }, "duration (hours)"));
    svg.append(node("text", { x: 14, y: (H - M.b) / 2, "text-anchor": "middle",
      transform: `rotate(-90 14 ${(H - M.b) / 2})` }, "mean intensity (mm/h)"));

    const which = key === "italy" ? null : data.macroregions.indexOf(key);
    const mine = data.landslides.filter(([m]) => which === null || m === which);
    for (const [, dd, ee] of mine) {
      const ii = ee / dd;
      if (dd >= 1 && dd <= 1000 && ii >= 0.01 && ii <= 100) {
        svg.append(node("circle", { cx: X(dd), cy: Y(ii), r: 1.8, class: "rt-dot" }));
      }
    }
    const pts = [];
    for (let k = 0; k <= 60; k++) {
      const dd = 10 ** ((X1 * k) / 60), ii = t.intensity(dd);
      if (ii >= 0.01 && ii <= 100) pts.push(`${X(dd)},${Y(ii)}`);
    }
    svg.append(node("polyline", { points: pts.join(" "), class: "rt-line" }));
    const sx = X(d), sy = Y(Math.min(100, Math.max(0.01, i)));
    const star = [];
    for (let k = 0; k < 10; k++) {
      const r = k % 2 ? 4 : 10, a = (Math.PI / 5) * k - Math.PI / 2;
      star.push(`${sx + r * Math.cos(a)},${sy + r * Math.sin(a)}`);
    }
    svg.append(node("polygon", { points: star.join(" "), class: "rt-star" }));

    const x = Math.log10(i / t.intensity(d));
    const similar = mine.filter(([, dd]) => dd >= d / 2 && dd <= d * 2);
    const less = similar.filter(([, dd, ee]) => ee / dd < i).length;
    const name = key === "italy" ? "Italy" : `${key} Italy`;
    const where = x > 0
      ? `<strong>above</strong> the threshold: ${fmt(10 ** x, 1)} times its intensity`
      : `<strong>below</strong> the threshold: ${fmt(10 ** -x, 1)} times less intense`;
    const share = similar.length
      ? `Of the ${fmt(similar.length, 0)} landslides of ${name} triggered by rain lasting
         ${fmt(d / 2, 0)}–${fmt(d * 2, 0)} h, ${fmt((100 * less) / similar.length, 0)} % had a lower
         intensity than this.`
      : `No landslide of ${name} in the catalogue was triggered by rain lasting
         ${fmt(d / 2, 0)}–${fmt(d * 2, 0)} h.`;
    $("rt-answer").innerHTML = `
      <p>${fmt(e)} mm in ${fmt(d)} h is ${fmt(i, 2)} mm/h on average. Over ${fmt(d)} h the T5
      threshold of ${name} asks ${fmt(t.cumulated(d))} mm (${fmt(t.intensity(d), 2)} mm/h).</p>
      <p>Exceedance <strong>${x >= 0 ? "+" : "−"}${fmt(Math.abs(x), 2)} decades</strong>: ${where}.</p>
      <p>${share}</p>
      <p class="rt-rule">Like the rain of past landslides, or not: never an alert. The official
      alert is the <a href="${data.alert_url}">bulletin of the Civil Protection</a>.</p>`;
  }

  async function start() {
    const url = new URL("data/explainer.json", document.querySelector("script[src*='explainer.js']").src.replace(/javascripts\/explainer\.js.*$/, ""));
    data = await (await fetch(url)).json();
    const select = $("rt-region");
    select.append(new Option("Italy (national threshold)", "italy"));
    for (const r of Object.keys(data.regions).sort()) select.append(new Option(r, r));
    select.value = "Calabria";
    for (const id of ["rt-region", "rt-d", "rt-e"]) $(id).addEventListener("input", draw);
    draw();
  }

  start().catch((err) => {
    $("rt-answer").textContent = `The page could not load its data: ${err.message}`;
  });
})();
