/**
 * ManagerDash FC26 — Express serves UI + JSON API.
 * Career save parsing stays in Python (scout/export.py).
 */
const { spawn } = require("child_process");
const express = require("express");
const path = require("path");

const PORT = Number(process.env.PORT) || 3847;
const PYTHON = process.env.PYTHON || "python";
const ROOT = __dirname;

let cache = null;
let loading = null;
let lastError = null;

function runExport(formation = "4-3-3") {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, ["-m", "scout.export", formation], {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" },
      windowsHide: true,
    });
    let stdout = Buffer.alloc(0);
    let stderr = "";
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (c) => {
      stdout = Buffer.concat([stdout, Buffer.isBuffer(c) ? c : Buffer.from(c)]);
    });
    child.stderr.on("data", (c) => {
      stderr += c;
      process.stderr.write(c);
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr.trim() || `export exit ${code}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout.toString("utf8")));
      } catch (e) {
        reject(new Error(`JSON parse failed: ${e.message}\n${stderr.slice(0, 500)}`));
      }
    });
  });
}

async function ensureData(force = false, formation) {
  if (loading) return loading;
  if (cache && !force) {
    if (formation && cache.meta?.formation !== formation) {
      // soft: only change active formation slots client-side; data has all fits
      cache.meta.formation = formation;
      if (cache.formations?.[formation]) cache.slots = cache.formations[formation];
    }
    return cache;
  }
  loading = (async () => {
    lastError = null;
    try {
      cache = await runExport(formation || "4-3-3");
      return cache;
    } catch (e) {
      lastError = String(e.message || e);
      throw e;
    } finally {
      loading = null;
    }
  })();
  return loading;
}

function paginate(rows, page, limit) {
  const p = Math.max(1, Number(page) || 1);
  const lim = Math.min(200, Math.max(1, Number(limit) || 50));
  const start = (p - 1) * lim;
  return {
    total: rows.length,
    page: p,
    limit: lim,
    pages: Math.max(1, Math.ceil(rows.length / lim)),
    rows: rows.slice(start, start + lim),
  };
}

function cellValue(p, key) {
  if (!key) return null;
  if (key.startsWith("fit:")) {
    const v = p.fits?.[key.slice(4)];
    return v == null ? Number.NEGATIVE_INFINITY : Number(v);
  }
  const v = p[key];
  if (v == null || v === "") return key === "name" || key === "club" || key === "league" || key === "pos" || key === "best" || key === "role" || key === "loan_txt" ? "" : Number.NEGATIVE_INFINITY;
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  const n = Number(v);
  if (key === "wage" || key === "value" || key === "ovr" || key === "pot" || key === "age" || key.startsWith("d_")) {
    return Number.isFinite(n) ? n : Number.NEGATIVE_INFINITY;
  }
  return String(v).toLowerCase();
}

function sortRows(rows, sort, dir, fallback) {
  const key = sort || fallback;
  const asc = String(dir || "desc").toLowerCase() === "asc";
  const mult = asc ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const av = cellValue(a, key);
    const bv = cellValue(b, key);
    let cmp = 0;
    if (typeof av === "string" || typeof bv === "string") {
      cmp = String(av).localeCompare(String(bv), "it", { sensitivity: "base" });
    } else {
      cmp = av === bv ? 0 : av < bv ? -1 : 1;
    }
    if (cmp !== 0) return cmp * mult;
    return String(a.name || "").localeCompare(String(b.name || ""), "it");
  });
}

const app = express();
app.use(express.json());
app.use(express.static(path.join(ROOT, "public")));

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    hasCache: !!cache,
    players: cache?.players?.length || 0,
    error: lastError,
  });
});

app.post("/api/refresh", async (req, res) => {
  try {
    const formation = req.body?.formation || "4-3-3";
    const data = await ensureData(true, formation);
    res.json({
      ok: true,
      meta: data.meta,
      players: data.players.length,
      formations: Object.keys(data.formations || {}),
    });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e.message || e) });
  }
});

app.get("/api/meta", async (req, res) => {
  try {
    const data = await ensureData(false, req.query.formation);
    res.json({
      meta: data.meta,
      slots: data.slots,
      all_roles: data.all_roles,
      role_labels: data.role_labels,
      formations: data.formations,
      snapshot_id: data.snapshot_id,
    });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/squad", async (req, res) => {
  try {
    const data = await ensureData(false, req.query.formation);
    const slots = data.formations?.[req.query.formation] || data.slots;
    const role = req.query.role || req.query.slot || "";
    const natural = req.query.natural === "1";
    let rows = data.players.filter((p) => p.mine);
    if (role) {
      if (natural) {
        rows = rows.filter(
          (p) => p.pos === role || (p.roles || []).includes(role)
        );
      } else {
        rows = rows.filter((p) => (p.fits?.[role] || 0) > 0);
      }
    }
    const fallback = role ? `fit:${role}` : "value";
    rows = sortRows(rows, req.query.sort, req.query.dir, fallback);
    const dir = (req.query.dir || "desc").toLowerCase() === "asc" ? "asc" : "desc";
    const viewSlots = role ? [role, ...slots.filter((s) => s !== role)] : slots;
    res.json({
      meta: data.meta,
      slots: viewSlots,
      all_roles: data.all_roles,
      role_labels: data.role_labels,
      sort: req.query.sort || fallback,
      dir,
      ...paginate(rows, req.query.page, req.query.limit || 100),
    });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/market", async (req, res) => {
  try {
    const data = await ensureData(false, req.query.formation);
    const slots = data.formations?.[req.query.formation] || data.slots;
    const role = req.query.role || req.query.slot || "";
    const league = req.query.league || "";
    const ovr = Number(req.query.ovr || 0);
    const pot = Number(req.query.pot || 0);
    const fitMin = Number(req.query.fitMin || 0);
    const q = (req.query.q || "").toLowerCase();
    const real = req.query.real !== "0";
    const women = req.query.women === "1";
    const namedOnly = req.query.named !== "0";
    // default ON when a role is selected — only natural TS/TD/… for substitutes
    const natural = role ? req.query.natural !== "0" : req.query.natural === "1";
    const primaryOnly = req.query.primary === "1";

    let rows = data.players.filter((p) => !p.mine);
    if (real) rows = rows.filter((p) => !p.special);
    if (!women) rows = rows.filter((p) => !p.women);
    if (namedOnly) rows = rows.filter((p) => p.named);
    if (league) rows = rows.filter((p) => p.league === league);
    if (ovr) rows = rows.filter((p) => (p.ovr || 0) >= ovr);
    if (pot) rows = rows.filter((p) => (p.pot || 0) >= pot);
    if (q) rows = rows.filter((p) => `${p.name} ${p.club}`.toLowerCase().includes(q));
    if (role) {
      if (natural) {
        rows = rows.filter((p) =>
          primaryOnly ? p.pos === role : p.pos === role || (p.roles || []).includes(role)
        );
      }
      if (fitMin) rows = rows.filter((p) => (p.fits?.[role] || 0) >= fitMin);
    }

    const fallback = role ? `fit:${role}` : "ovr";
    rows = sortRows(rows, req.query.sort, req.query.dir, fallback);
    // Prefer primary natural role first when filtering substitutes
    if (role && !req.query.sort) {
      rows = rows.slice().sort((a, b) => {
        const ap = a.pos === role ? 1 : 0;
        const bp = b.pos === role ? 1 : 0;
        if (bp !== ap) return bp - ap;
        return (b.fits?.[role] || 0) - (a.fits?.[role] || 0);
      });
    }

    const leagues = [...new Set(data.players.map((p) => p.league).filter(Boolean))].sort();
    const viewSlots = role ? [role, ...slots.filter((s) => s !== role)] : slots;
    res.json({
      meta: data.meta,
      slots: viewSlots,
      all_roles: data.all_roles,
      role_labels: data.role_labels,
      leagues,
      sort: req.query.sort || fallback,
      dir: (req.query.dir || "desc").toLowerCase() === "asc" ? "asc" : "desc",
      ...paginate(rows, req.query.page, req.query.limit || 50),
    });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/growth", async (req, res) => {
  try {
    const data = await ensureData(false, req.query.formation);
    const slots = data.formations?.[req.query.formation] || data.slots;
    let rows = data.players.filter(
      (p) => p.mine && (p.d_ovr != null || p.d_value != null || p.d_pot != null)
    );
    const sort = req.query.sort || "d_value";
    const dir = req.query.dir || "desc";
    rows = sortRows(rows, sort, dir, "d_value");
    res.json({
      meta: data.meta,
      slots,
      all_roles: data.all_roles,
      role_labels: data.role_labels,
      sort,
      dir: dir.toLowerCase() === "asc" ? "asc" : "desc",
      ...paginate(rows, req.query.page, req.query.limit || 100),
    });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.listen(PORT, () => {
  console.log(`ManagerDash FC26 → http://localhost:${PORT}`);
  // warm cache in background
  ensureData(true).catch((e) => console.error("Warm load failed:", e.message));
});
