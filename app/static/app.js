// Il banco di taratura: legge la configurazione, tara la soglia, ne misura il costo.
"use strict";

const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
const $ = (id) => document.getElementById(id);
let ultima = null;

const numero = (x, cifre = 1) =>
  typeof x === "number" ? x.toLocaleString("it-IT", { maximumFractionDigits: cifre }) : x;

async function chiedi(url, corpo) {
  const r = await fetch(url, corpo === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  if (!r.ok) throw new Error((await r.text()) || `errore ${r.status}`);
  return r.json();
}

function elemento(tag, testo, classe) {
  const e = document.createElement(tag);
  e.textContent = testo;
  if (classe) e.className = classe;
  return e;
}

function scelti(contenitore) {
  return [...contenitore.querySelectorAll("input:checked")].map((i) => i.value);
}

function casella(valore, etichetta, nome) {
  const id = `${nome}-${valore}`;
  const div = document.createElement("div");
  div.className = "form-check form-check-inline";
  div.innerHTML = `<input class="form-check-input" type="checkbox" id="${id}" value="${valore}">
    <label class="form-check-label" for="${id}">${etichetta}</label>`;
  return div;
}

async function avvio() {
  const c = await chiedi("api/config");
  if (c.ente) {
    $("ente").textContent = c.ente;
    document.title = `${c.ente} · banco di taratura`;
  }
  $("bollettino").href = c.bollettino;
  $("fonte").textContent = c.fonte;
  $("versione").textContent = c.versione;
  for (const r of c.regioni) {
    const o = new Option(r, r, false, r === c.regione);
    $("regioni").add(o);
  }
  MESI.forEach((m, i) => $("mesi").appendChild(casella(i + 1, m, "mese")));
  for (const [k, v] of Object.entries(c.tipi)) $("tipi").appendChild(casella(k, v, "tipo"));
}

function eventiEnte() {
  return $("eventi-ente").value.split("\n").map((r) => r.trim()).filter(Boolean)
    .map((r) => r.split(/[;,\s]+/).map(Number));
}

async function tara() {
  $("errore").classList.add("d-none");
  const ente = eventiEnte();
  const corpo = {
    percentile: Number($("percentile").value),
    regioni: [...$("regioni").selectedOptions].map((o) => o.value),
    mesi: scelti($("mesi")).map(Number),
    tipi: scelti($("tipi")),
  };
  if (ente.length) corpo.eventi_ente = ente;
  try {
    ultima = await chiedi("api/taratura", corpo);
  } catch (e) {
    $("errore").textContent = `La soglia non si può tarare: ${e.message}`;
    $("errore").classList.remove("d-none");
    return;
  }
  mostra(ultima);
}

function mostra(r) {
  const s = r.soglia;
  $("sintesi").innerHTML = `Su <strong>${numero(r.frane, 0)}</strong> frane (${r.origine}),
    la soglia T${numero(r.percentile, 0)} è <strong>I = ${numero(s.alpha, 3)} · D<sup>−${numero(s.beta, 4)}</sup></strong>
    (mm/h, ore). Restano sotto ${numero(r.sotto_soglia.frane, 0)} frane, il
    ${numero(100 * r.sotto_soglia.quota, 1)} %.`;
  $("nome-riferimento").textContent = `Nazionale ${r.riferimento.nome}`;
  $("tabella").innerHTML = s.pioggia.map((p, i) => {
    const n = r.riferimento.pioggia[i];
    return `<tr><td>${p.durata_h} h</td><td>${numero(p.pioggia_mm)} mm (${numero(p.intensita_mm_h, 2)} mm/h)</td>
      <td>${numero(n.pioggia_mm)} mm (${numero(n.intensita_mm_h, 2)} mm/h)</td></tr>`;
  }).join("");
  $("avvertenze").replaceChildren(...r.avvertenze.map((a) => elemento("li", a)));
  $("stato-costo").textContent = r.costo.stato;
  $("perche-costo").textContent = r.costo.perche;
  grafico(r);
  $("risultato").classList.remove("d-none");
  $("misura").disabled = false;
  const q = new URLSearchParams({ alpha: s.alpha, beta: s.beta, percentile: r.percentile,
    frane: r.frane, origine: r.origine });
  $("esporta").href = `api/esporta?${q}`;
  $("esporta").classList.remove("disabled");
  $("esporta").removeAttribute("aria-disabled");
}

function grafico(r) {
  const W = 640, H = 420, m = { l: 56, r: 16, t: 12, b: 44 };
  const x0 = 0, x1 = Math.log10(1000), y0 = -2, y1 = 2; // 1-1000 h, 0.01-100 mm/h
  const X = (d) => m.l + (Math.log10(d) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = (i) => H - m.b - (Math.log10(i) - y0) / (y1 - y0) * (H - m.t - m.b);
  const dentro = (v, a, b) => v >= 10 ** a && v <= 10 ** b;
  let svg = "";
  for (let e = 0; e <= 3; e++) {
    svg += `<line x1="${X(10 ** e)}" x2="${X(10 ** e)}" y1="${m.t}" y2="${H - m.b}" class="griglia"/>
      <text x="${X(10 ** e)}" y="${H - m.b + 16}" text-anchor="middle">${10 ** e}</text>`;
  }
  for (let e = -2; e <= 2; e++) {
    svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(10 ** e)}" y2="${Y(10 ** e)}" class="griglia"/>
      <text x="${m.l - 6}" y="${Y(10 ** e) + 4}" text-anchor="end">${10 ** e}</text>`;
  }
  svg += `<text x="${(W + m.l) / 2}" y="${H - 6}" text-anchor="middle">durata (ore)</text>
    <text x="14" y="${(H - m.b) / 2}" transform="rotate(-90 14 ${(H - m.b) / 2})" text-anchor="middle">intensità media (mm/h)</text>`;
  for (const [d, e] of r.punti) {
    const i = e / d;
    if (dentro(d, x0, x1) && dentro(i, y0, y1)) svg += `<circle cx="${X(d)}" cy="${Y(i)}" r="2" class="punto"/>`;
  }
  const linea = (s, cls) => {
    const p = [];
    for (let k = 0; k <= 60; k++) {
      const d = 10 ** (x1 * k / 60), i = s.alpha * d ** -s.beta;
      if (dentro(i, y0, y1)) p.push(`${X(d)},${Y(i)}`);
    }
    return `<polyline points="${p.join(" ")}" class="${cls}"/>`;
  };
  svg += linea(r.riferimento, "riferimento") + linea(r.soglia, "soglia");
  $("grafico").innerHTML = svg;
}

async function misura() {
  $("errore-costo").classList.add("d-none");
  if (!ultima) return;
  const corpo = {
    alpha: ultima.soglia.alpha, beta: ultima.soglia.beta,
    serie: $("serie").value,
    frane: $("frane").value.split("\n"),
  };
  let c;
  try {
    c = await chiedi("api/costo", corpo);
  } catch (e) {
    $("errore-costo").textContent = `Il costo non si può misurare: ${e.message}`;
    $("errore-costo").classList.remove("d-none");
    return;
  }
  const righe = [
    ["Periodo", `${c.periodo[0]} → ${c.periodo[1]}`],
    ["Eventi di pioggia", numero(c.eventi_di_pioggia, 0)],
    ["Allerte (eventi sopra soglia)", numero(c.allerte, 0)],
    ["Quota di eventi in allerta", typeof c.quota_eventi_in_allerta === "number"
      ? `${numero(100 * c.quota_eventi_in_allerta, 1)} %` : c.quota_eventi_in_allerta],
    ["Frane nel periodo", numero(c.frane, 0)],
    ["Frane colte", numero(c.frane_colte, 0)],
    ["Frane mancate", numero(c.frane_mancate, 0)],
    ["Frane senza pioggia misurata", numero(c.frane_senza_pioggia_misurata, 0)],
    ["Allerte per frana colta", numero(c.allerte_per_frana_colta, 2)],
    ["Ore non misurate nella serie", numero(c.ore_non_misurate, 0)],
  ];
  $("costo").replaceChildren(...righe.flatMap(([k, v]) => [
    elemento("dt", k, "col-sm-5"), elemento("dd", String(v), "col-sm-7"),
  ]));
  $("costo").classList.remove("d-none");
  $("stato-costo").textContent = "misurato sui dati caricati";
}

$("tara").addEventListener("click", tara);
$("misura").addEventListener("click", misura);
avvio().catch((e) => {
  $("errore").textContent = `La pagina non riesce a leggere la configurazione: ${e.message}`;
  $("errore").classList.remove("d-none");
});
