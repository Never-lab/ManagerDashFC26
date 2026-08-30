const state = {
  tab: "squad",
  formation: "4-3-3",
  pages: { squad: 1, market: 1, growth: 1 },
  sort: {
    squad: { key: "value", dir: "desc" },
    market: { key: "ovr", dir: "desc" },
    growth: { key: "d_value", dir: "desc" },
  },
  slots: [],
};

const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function nz(v) {
  return v == null ? "" : v;
}

function delta(v) {
  if (v == null) return "";
  return (v > 0 ? "+" : "") + v;
}

function dClass(v) {
  if (v == null || v === 0) return "";
  return v > 0 ? "up" : "down";
}

function showError(msg) {
  const el = $("error");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

async function api(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function renderMeta(meta) {
  if (!meta) return;
  $("meta").textContent = `${meta.manager || "Manager"} · ${meta.club || "?"} · stagione ${
    meta.season ?? "?"
  } · ${meta.league || ""} · save ${meta.save || ""}`;
}

function fillFormations(formations) {
  const sel = $("formation");
  const keys = Object.keys(formations || { "4-3-3": [] });
  sel.innerHTML = keys.map((k) => `<option value="${esc(k)}">${esc(k)}</option>`).join("");
  sel.value = state.formation in (formations || {}) ? state.formation : keys[0];
  state.formation = sel.value;
}

function fillSlots(slots) {
  state.slots = slots || [];
  const sel = $("slot");
  const cur = sel.value;
  sel.innerHTML =
    '<option value="">tutti</option>' +
    state.slots.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("");
  if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
}

function th(label, key, tab) {
  const s = state.sort[tab];
  const on = s.key === key;
  const mark = on ? (s.dir === "asc" ? " ▲" : " ▼") : "";
  return `<th class="sortable${on ? " on" : ""}" data-sort="${esc(key)}" data-tab="${esc(
    tab
  )}" title="Ordina">${esc(label)}${mark}</th>`;
}

function tableHtml(tab, rows, slots, extraKeys) {
  let h = "<table><thead><tr>";
  h += th("Nome", "name", tab);
  h += th("OVR", "ovr", tab);
  h += th("POT", "pot", tab);
  h += th("Età", "age", tab);
  h += th("Valore", "value", tab);
  h += th("Δ val", "d_value", tab);
  h += th("Pos", "pos", tab);
  h += th("Best", "best", tab);
  h += th("Club", "club", tab);
  h += th("Lega", "league", tab);
  (slots || []).forEach((s) => {
    h += th(s, `fit:${s}`, tab);
  });
  (extraKeys || []).forEach(([label, key]) => {
    h += th(label, key, tab);
  });
  h += "</tr></thead><tbody>";
  rows.forEach((p) => {
    h += `<tr><td class="name">${esc(p.name)}</td><td>${nz(p.ovr)}</td><td>${nz(p.pot)}</td><td>${nz(
      p.age
    )}</td><td>${esc(p.value_txt)}</td><td class="${dClass(p.d_value)}">${esc(
      p.d_value_txt || ""
    )}</td><td><span class="pill">${esc(p.pos)}</span></td><td>${esc(p.best)}</td><td>${esc(
      p.club
    )}</td><td>${esc(p.league)}</td>`;
    (slots || []).forEach((s) => {
      h += `<td class="fit">${p.fits?.[s] ?? ""}</td>`;
    });
    if (extraKeys) {
      for (const [label, key] of extraKeys) {
        if (key === "loan_txt") {
          h += `<td class="loan ${p.loan_in ? "in" : p.loan_out ? "out" : ""}">${esc(
            p.loan_txt || ""
          )}${p.loan_buy ? ' <span class="pill">L2B</span>' : ""}</td>`;
        } else if (key === "d_ovr" || key === "d_pot") {
          h += `<td class="${dClass(p[key])}">${delta(p[key])}</td>`;
        } else if (key === "role") {
          h += `<td>${esc(p.role)}</td>`;
        } else if (key === "wage") {
          h += `<td>${nz(p.wage)}</td>`;
        } else {
          h += `<td>${esc(p[key])}</td>`;
        }
      }
    }
    h += "</tr>";
  });
  return h + "</tbody></table>";
}

function pagerHtml(tab, page, pages, total) {
  return `
    <span>${total} risultati · pag. ${page}/${pages}</span>
    <button type="button" data-tab="${tab}" data-dir="-1" ${page <= 1 ? "disabled" : ""}>←</button>
    <button type="button" data-tab="${tab}" data-dir="1" ${page >= pages ? "disabled" : ""}>→</button>
  `;
}

function sortParams(tab) {
  const s = state.sort[tab];
  return { sort: s.key, dir: s.dir };
}

async function loadSquad() {
  const q = new URLSearchParams({
    formation: state.formation,
    page: String(state.pages.squad),
    limit: "80",
    ...sortParams("squad"),
  });
  const data = await api(`/api/squad?${q}`);
  renderMeta(data.meta);
  fillSlots(data.slots);
  $("squad-table").innerHTML = tableHtml("squad", data.rows, data.slots, [
    ["Prestito", "loan_txt"],
    ["ΔOVR", "d_ovr"],
    ["Ruolo", "role"],
    ["Stipendio", "wage"],
  ]);
  $("squad-pager").innerHTML = pagerHtml("squad", data.page, data.pages, data.total);
}

async function loadMarket() {
  const q = new URLSearchParams({
    formation: state.formation,
    page: String(state.pages.market),
    limit: "50",
    slot: $("slot").value,
    league: $("league").value,
    ovr: $("ovr").value || "0",
    pot: $("pot").value || "0",
    q: $("q").value,
    real: $("real").checked ? "1" : "0",
    women: $("women").checked ? "1" : "0",
    named: $("named").checked ? "1" : "0",
    ...sortParams("market"),
  });
  const data = await api(`/api/market?${q}`);
  renderMeta(data.meta);
  fillSlots(data.slots);
  const leagueSel = $("league");
  const cur = leagueSel.value;
  if (data.leagues?.length && leagueSel.options.length <= 1) {
    leagueSel.innerHTML =
      '<option value="">tutti</option>' +
      data.leagues.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
    if ([...leagueSel.options].some((o) => o.value === cur)) leagueSel.value = cur;
  }
  $("market-table").innerHTML = tableHtml("market", data.rows, data.slots, [
    ["Prestito", "loan_txt"],
  ]);
  $("market-pager").innerHTML = pagerHtml("market", data.page, data.pages, data.total);
}

async function loadGrowth() {
  const q = new URLSearchParams({
    formation: state.formation,
    page: String(state.pages.growth),
    limit: "80",
    ...sortParams("growth"),
  });
  const data = await api(`/api/growth?${q}`);
  renderMeta(data.meta);
  fillSlots(data.slots);
  $("growth-table").innerHTML = tableHtml("growth", data.rows, data.slots, [
    ["ΔOVR", "d_ovr"],
    ["ΔPOT", "d_pot"],
  ]);
  $("growth-pager").innerHTML = pagerHtml("growth", data.page, data.pages, data.total);
}

async function loadTab() {
  showError("");
  try {
    if (state.tab === "squad") await loadSquad();
    else if (state.tab === "market") await loadMarket();
    else await loadGrowth();
  } catch (e) {
    showError(e.message);
  }
}

async function boot() {
  try {
    const meta = await api(`/api/meta?formation=${encodeURIComponent(state.formation)}`);
    fillFormations(meta.formations);
    fillSlots(meta.slots);
    renderMeta(meta.meta);
    await loadTab();
  } catch (e) {
    showError(
      e.message +
        " — Controlla che FC 26 abbia un save career in %LOCALAPPDATA%\\EA SPORTS FC 26\\settings e che `pip install -r requirements.txt` sia ok."
    );
  }
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("on"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("on"));
    btn.classList.add("on");
    state.tab = btn.dataset.tab;
    $(state.tab).classList.add("on");
    loadTab();
  });
});

$("formation").addEventListener("change", () => {
  state.formation = $("formation").value;
  state.pages.market = 1;
  loadTab();
});

$("refresh").addEventListener("click", async () => {
  const btn = $("refresh");
  btn.disabled = true;
  btn.textContent = "Aggiorno…";
  try {
    await api("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ formation: state.formation }),
    });
    state.pages = { squad: 1, market: 1, growth: 1 };
    await boot();
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Aggiorna save";
  }
});

["slot", "league", "ovr", "pot", "q", "real", "women", "named"].forEach((id) => {
  const el = $(id);
  const go = () => {
    state.pages.market = 1;
    if (id === "slot" && $("slot").value) {
      state.sort.market = { key: `fit:${$("slot").value}`, dir: "desc" };
    }
    if (state.tab === "market") loadMarket().catch((e) => showError(e.message));
  };
  el.addEventListener("change", go);
  el.addEventListener("input", go);
});

document.addEventListener("click", (ev) => {
  const sortTh = ev.target.closest("th.sortable");
  if (sortTh) {
    const tab = sortTh.dataset.tab;
    const key = sortTh.dataset.sort;
    const cur = state.sort[tab];
    if (cur.key === key) cur.dir = cur.dir === "asc" ? "desc" : "asc";
    else state.sort[tab] = { key, dir: key === "name" || key === "club" || key === "league" || key === "pos" || key === "best" || key === "role" || key === "loan_txt" ? "asc" : "desc" };
    state.pages[tab] = 1;
    loadTab();
    return;
  }
  const btn = ev.target.closest(".pager button");
  if (!btn) return;
  const tab = btn.dataset.tab;
  const dir = Number(btn.dataset.dir);
  state.pages[tab] = Math.max(1, (state.pages[tab] || 1) + dir);
  loadTab();
});

boot();
