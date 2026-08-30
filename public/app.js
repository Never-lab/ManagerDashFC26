const state = {
  tab: "squad",
  formation: "4-3-3",
  pages: { squad: 1, market: 1, growth: 1 },
  sort: {
    squad: { key: "value", dir: "desc" },
    market: { key: "ovr", dir: "desc" },
    growth: { key: "d_value", dir: "desc" },
  },
  role: { squad: "", market: "" },
  slots: [],
  allRoles: [],
  roleLabels: {},
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

function roleName(code) {
  const full = state.roleLabels[code];
  return full ? `${code} — ${full}` : code;
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

function rememberRoles(data) {
  if (data.all_roles?.length) state.allRoles = data.all_roles;
  if (data.role_labels) state.roleLabels = data.role_labels;
  if (data.slots) state.slots = data.slots;
}

function fillRoleSelect(selId, selected) {
  const sel = $(selId);
  const cur = selected ?? sel.value;
  const roles = state.allRoles.length ? state.allRoles : state.slots;
  sel.innerHTML =
    '<option value="">tutti</option>' +
    roles.map((s) => `<option value="${esc(s)}">${esc(roleName(s))}</option>`).join("");
  if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
}

function renderRoleChips(containerId, tab) {
  const el = $(containerId);
  if (!el) return;
  const roles = state.allRoles.length ? state.allRoles : state.slots;
  const active = state.role[tab] || "";
  el.innerHTML =
    `<button type="button" data-tab="${tab}" data-role="" class="${!active ? "on" : ""}">tutti</button>` +
    roles
      .map(
        (r) =>
          `<button type="button" data-tab="${tab}" data-role="${esc(r)}" class="${
            active === r ? "on" : ""
          }" title="${esc(state.roleLabels[r] || r)}">${esc(r)}</button>`
      )
      .join("");
}

function th(label, key, tab) {
  const s = state.sort[tab];
  const on = s.key === key;
  const mark = on ? (s.dir === "asc" ? " ▲" : " ▼") : "";
  return `<th class="sortable${on ? " on" : ""}" data-sort="${esc(key)}" data-tab="${esc(
    tab
  )}" title="Ordina">${esc(label)}${mark}</th>`;
}

function rolesCell(p) {
  const roles = p.roles?.length ? p.roles : p.pos ? [p.pos] : [];
  return roles
    .map(
      (r, i) =>
        `<span class="pill role${i === 0 ? "" : ""}" title="${esc(state.roleLabels[r] || r)}">${esc(
          r
        )}</span>`
    )
    .join("");
}

function tableHtml(tab, rows, slots, extraKeys, focusRole) {
  let h = "<table><thead><tr>";
  h += th("Nome", "name", tab);
  h += th("OVR", "ovr", tab);
  h += th("POT", "pot", tab);
  h += th("Età", "age", tab);
  h += th("Valore", "value", tab);
  h += th("Δ val", "d_value", tab);
  h += th("Ruoli", "pos", tab);
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
    )}</td><td>${rolesCell(p)}</td><td>${esc(p.best)}</td><td>${esc(p.club)}</td><td>${esc(
      p.league
    )}</td>`;
    (slots || []).forEach((s) => {
      const focus = focusRole && s === focusRole ? " focus" : "";
      h += `<td class="fit${focus}">${p.fits?.[s] ?? ""}</td>`;
    });
    if (extraKeys) {
      for (const [, key] of extraKeys) {
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

function setRole(tab, role) {
  state.role[tab] = role || "";
  state.pages[tab] = 1;
  if (role) state.sort[tab] = { key: `fit:${role}`, dir: "desc" };
  if (tab === "squad") $("squad-role").value = state.role.squad;
  if (tab === "market") $("slot").value = state.role.market;
  loadTab();
}

async function loadSquad() {
  const role = state.role.squad || $("squad-role").value;
  state.role.squad = role;
  const q = new URLSearchParams({
    formation: state.formation,
    page: String(state.pages.squad),
    limit: "80",
    role,
    natural: $("squad-natural").checked ? "1" : "0",
    ...sortParams("squad"),
  });
  const data = await api(`/api/squad?${q}`);
  rememberRoles(data);
  renderMeta(data.meta);
  fillRoleSelect("squad-role", role);
  fillRoleSelect("slot", state.role.market);
  renderRoleChips("squad-roles", "squad");
  $("squad-table").innerHTML = tableHtml(
    "squad",
    data.rows,
    data.slots,
    [
      ["Prestito", "loan_txt"],
      ["ΔOVR", "d_ovr"],
      ["Ruolo rosa", "role"],
      ["Stipendio", "wage"],
    ],
    role
  );
  $("squad-pager").innerHTML = pagerHtml("squad", data.page, data.pages, data.total);
}

async function loadMarket() {
  const role = state.role.market || $("slot").value;
  state.role.market = role;
  const q = new URLSearchParams({
    formation: state.formation,
    page: String(state.pages.market),
    limit: "50",
    role,
    slot: role,
    league: $("league").value,
    ovr: $("ovr").value || "0",
    pot: $("pot").value || "0",
    fitMin: $("fitMin").value || "0",
    q: $("q").value,
    natural: $("natural").checked ? "1" : "0",
    primary: $("primary").checked ? "1" : "0",
    real: $("real").checked ? "1" : "0",
    women: $("women").checked ? "1" : "0",
    named: $("named").checked ? "1" : "0",
    ...sortParams("market"),
  });
  const data = await api(`/api/market?${q}`);
  rememberRoles(data);
  renderMeta(data.meta);
  fillRoleSelect("slot", role);
  fillRoleSelect("squad-role", state.role.squad);
  renderRoleChips("market-roles", "market");
  const leagueSel = $("league");
  const cur = leagueSel.value;
  if (data.leagues?.length && leagueSel.options.length <= 1) {
    leagueSel.innerHTML =
      '<option value="">tutti</option>' +
      data.leagues.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
    if ([...leagueSel.options].some((o) => o.value === cur)) leagueSel.value = cur;
  }
  $("market-table").innerHTML = tableHtml(
    "market",
    data.rows,
    data.slots,
    [["Prestito", "loan_txt"]],
    role
  );
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
  rememberRoles(data);
  renderMeta(data.meta);
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
    rememberRoles(meta);
    fillFormations(meta.formations);
    fillRoleSelect("slot", state.role.market);
    fillRoleSelect("squad-role", state.role.squad);
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

$("squad-role").addEventListener("change", () => setRole("squad", $("squad-role").value));
$("squad-natural").addEventListener("change", () => {
  state.pages.squad = 1;
  loadSquad().catch((e) => showError(e.message));
});

["slot", "league", "ovr", "pot", "fitMin", "q", "real", "women", "named", "natural", "primary"].forEach(
  (id) => {
    const el = $(id);
    const go = () => {
      if (id === "slot") {
        setRole("market", $("slot").value);
        return;
      }
      state.pages.market = 1;
      if (state.tab === "market") loadMarket().catch((e) => showError(e.message));
    };
    el.addEventListener("change", go);
    el.addEventListener("input", go);
  }
);

document.addEventListener("click", (ev) => {
  const chip = ev.target.closest(".role-chips button");
  if (chip) {
    setRole(chip.dataset.tab, chip.dataset.role || "");
    return;
  }
  const sortTh = ev.target.closest("th.sortable");
  if (sortTh) {
    const tab = sortTh.dataset.tab;
    const key = sortTh.dataset.sort;
    const cur = state.sort[tab];
    if (cur.key === key) cur.dir = cur.dir === "asc" ? "desc" : "asc";
    else {
      const textKeys = new Set(["name", "club", "league", "pos", "best", "role", "loan_txt"]);
      state.sort[tab] = { key, dir: textKeys.has(key) ? "asc" : "desc" };
    }
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
