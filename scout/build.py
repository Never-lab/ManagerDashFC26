"""Build a local HTML scout from the latest career save. Read-only."""

from __future__ import annotations

import json
import webbrowser
from collections import defaultdict
from pathlib import Path

from scout.career import latest_career_save, open_career
from scout.names import load_catalog, load_ea_names
from scout.score import (
    FORMATIONS,
    POS,
    ROLE_LABELS,
    SLOTS,
    all_fits,
    best_slot,
    preferred_positions,
    preferred_roles,
)
from scout.snapshot import previous_mine, save_snapshot
from scout.value import age_from_birth, current_value, fmt_eur

OUT = Path(__file__).resolve().parent / "out" / "index.html"

ROLE = {-1: "", 0: "", 1: "titolare", 2: "importante", 3: "rotazione", 4: "sporadico", 5: "prospetto"}


def _dc_map(world) -> dict[int, str]:
    return {r["nameid"]: r["name"] for r in world.get_table("dcplayernames")}


def _edited_map(world) -> dict[int, str]:
    out = {}
    for r in world.get_table("editedplayernames"):
        pid = r.get("playerid")
        if pid is None:
            continue
        common = (r.get("commonname") or "").strip()
        name = common or f"{r.get('firstname') or ''} {r.get('surname') or ''}".strip()
        if name:
            out[int(pid)] = name
    return out


SPECIAL_HINTS = (
    "classic xi",
    "soccer aid",
    "historic",
    "free agent",
    "world xi",
    "icons",
    "heroes",
    "ultimate team",
    "ng - fa",
    "5v5",
)


def player_name(p: dict, dc: dict[int, str], edited: dict[int, str], ea: dict[str, str]) -> str:
    pid = int(p.get("playerid") or 0)
    if pid in edited:
        return edited[pid]
    ea_name = ea.get(str(pid), "")
    if ea_name:
        return ea_name
    common_id = p.get("commonnameid") or 0
    if common_id and common_id in dc:
        return dc[common_id]
    first = dc.get(p.get("firstnameid") or -1, "")
    last = dc.get(p.get("lastnameid") or -1, "")
    jersey = dc.get(p.get("playerjerseynameid") or -1, "")
    combo = f"{first} {last}".strip() or jersey
    if combo:
        return combo
    return f"ID {pid}"


def is_special(club: str, league: str) -> bool:
    blob = f"{club} {league}".lower()
    return any(h in blob for h in SPECIAL_HINTS)


def rows_from_world(career, world, ea: dict[str, str], catalog: dict[str, dict]) -> tuple[list[dict], dict]:
    users = career.get_table("career_users")
    user = users[0]
    club_id = int(user["clubteamid"])
    contracts = {int(r["playerid"]): r for r in career.get_table("career_playercontract")}
    ranking = {int(r["playerid"]): r for r in career.get_table("career_squadranking")}

    dc = _dc_map(world)
    edited = _edited_map(world)
    teams = {int(t["teamid"]): t for t in world.get_table("teams")}
    leagues = {int(l["leagueid"]): l for l in world.get_table("leagues")}
    ltl = world.get_table("leagueteamlinks")
    team_league = {int(r["teamid"]): int(r["leagueid"]) for r in ltl}
    intl_leagues = {lid for lid, lg in leagues.items() if lg.get("isinternationalleague")}
    intl_teams = {tid for tid, lid in team_league.items() if lid in intl_leagues}

    links_by_pid: dict[int, list[int]] = defaultdict(list)
    for link in world.get_table("teamplayerlinks"):
        links_by_pid[int(link["playerid"])].append(int(link["teamid"]))

    loans = {int(r["playerid"]): r for r in world.get_table("playerloans")}

    players = []
    for p in world.get_table("players"):
        pid = int(p["playerid"])
        club = None
        for tid in links_by_pid.get(pid, []):
            if tid not in intl_teams:
                club = tid
                break
        if club is None and links_by_pid.get(pid):
            club = links_by_pid[pid][0]
        team = teams.get(club or -1, {})
        lid = team_league.get(club or -1)
        league = leagues.get(lid or -1, {})
        fits = all_fits(p)
        pos_ids = preferred_positions(p)
        roles = preferred_roles(p)
        c = contracts.get(pid)
        club_name = team.get("teamname") or ""
        league_name = league.get("leaguename") or ""
        name = player_name(p, dc, edited, ea)
        ovr = p.get("overallrating")
        pot = p.get("potential")
        cat = catalog.get(str(pid))
        age = age_from_birth(p.get("birthdate"), user.get("seasoncount") or 1)
        gk = bool(pos_ids and pos_ids[0] == 0)
        value = current_value(ovr, pot, age, cat, gk)
        wage = (c.get("wage") if c else None) or (cat or {}).get("wage")
        loan_row = loans.get(pid)
        loan_from_id = int(loan_row["teamidloanedfrom"]) if loan_row else None
        at_club = club == club_id
        # Out: we are the parent club; player currently elsewhere.
        loan_out = bool(loan_row and loan_from_id == club_id and not at_club)
        # In: at our club, but parent club is someone else.
        loan_in = bool(loan_row and at_club and loan_from_id is not None and loan_from_id != club_id)
        # Rosa = currently here OR our player out on loan (drop sold ghosts with stale contracts).
        mine = at_club or loan_out
        other_id = (loan_from_id if loan_in else club) if (loan_in or loan_out) else None
        other_name = teams.get(other_id or -1, {}).get("teamname") or ""
        if loan_in:
            loan_txt = f"in ← {other_name}" if other_name else "in"
        elif loan_out:
            loan_txt = f"out → {other_name}" if other_name else "out"
        else:
            loan_txt = ""
        players.append(
            {
                "id": pid,
                "name": name,
                "named": not name.startswith("ID "),
                "ovr": ovr,
                "pot": pot,
                "age": age,
                "pos": roles[0] if roles else (POS.get(pos_ids[0], "?") if pos_ids else "?"),
                "roles": roles,
                "club": club_name,
                "club_id": club,
                "league": league_name,
                "league_id": lid,
                "women": bool(league.get("iswomencompetition")),
                "special": is_special(club_name, league_name),
                "mine": mine,
                "wage": wage,
                "value": value,
                "value_txt": fmt_eur(value),
                "role": ROLE.get(c.get("playerrole"), "") if c else "",
                "months": c.get("duration_months") if c else None,
                "loan": bool(loan_in or loan_out),
                "loan_in": loan_in,
                "loan_out": loan_out,
                "loan_other": other_name,
                "loan_txt": loan_txt,
                "loan_buy": bool(loan_row and loan_row.get("isloantobuy")),
                "fits": fits,
                "best": best_slot(p),
                "rank_ovr": (ranking.get(pid) or {}).get("curroverall"),
                "d_ovr": None,
                "d_pot": None,
                "d_value": None,
                "d_value_txt": "",
            }
        )

    meta = {
        "manager": f"{user.get('firstname') or ''} {user.get('surname') or ''}".strip(),
        "club": teams.get(club_id, {}).get("teamname") or str(club_id),
        "club_id": club_id,
        "season": user.get("seasoncount"),
        "league": leagues.get(team_league.get(club_id, -1), {}).get("leaguename") or "",
        "formation": "4-3-3",
        "formations": list(FORMATIONS.keys()),
    }
    return players, meta


def apply_growth(players: list[dict], prev: dict[int, dict]) -> None:
    for p in players:
        old = prev.get(p["id"])
        if not old:
            continue
        if p.get("ovr") is not None and old.get("ovr") is not None:
            p["d_ovr"] = int(p["ovr"]) - int(old["ovr"])
        if p.get("pot") is not None and old.get("pot") is not None:
            p["d_pot"] = int(p["pot"]) - int(old["pot"])
        if p.get("value") is not None and old.get("value") is not None:
            dv = int(p["value"]) - int(old["value"])
            p["d_value"] = dv
            sign = "+" if dv > 0 else ""
            p["d_value_txt"] = f"{sign}{fmt_eur(dv)}" if dv else "0"


def write_html(players: list[dict], meta: dict, dest: Path = OUT) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"meta": meta, "players": players, "slots": list(SLOTS)}, ensure_ascii=False)
    dest.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    return dest


HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>FC 26 Scout 4-3-3</title>
<style>
body { font-family: Segoe UI, sans-serif; margin: 0; background: #111; color: #eee; }
header { padding: 16px 24px; background: #1c1c1c; border-bottom: 1px solid #333; }
h1 { margin: 0 0 4px; font-size: 20px; }
.sub { color: #aaa; font-size: 13px; }
nav { display: flex; gap: 8px; padding: 12px 24px; }
button.tab { background: #2a2a2a; color: #eee; border: 1px solid #444; padding: 8px 14px; cursor: pointer; }
button.tab.on { background: #3d6; color: #111; }
.panel { display: none; padding: 0 24px 24px; }
.panel.on { display: block; }
label { margin-right: 12px; font-size: 13px; color: #bbb; }
input, select { background: #222; color: #eee; border: 1px solid #444; padding: 4px 8px; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #333; }
th { cursor: pointer; color: #9c9; position: sticky; top: 0; background: #111; }
tr:hover { background: #1a1a1a; }
.fit { font-variant-numeric: tabular-nums; }
.mine { color: #8f8; }
.up { color: #6d6; }
.down { color: #f66; }
</style>
</head>
<body>
<header>
  <h1 id="title">Scout 4-3-3</h1>
  <div class="sub" id="sub"></div>
</header>
<nav>
  <button class="tab on" data-tab="squad">Rosa</button>
  <button class="tab" data-tab="market">Mercato</button>
  <button class="tab" data-tab="growth">Crescita</button>
</nav>
<section id="squad" class="panel on">
  <p class="sub">Valore stimato (il save FC 26 non lo memorizza). Δ rispetto allo snapshot precedente.</p>
  <div id="squad-table"></div>
</section>
<section id="market" class="panel">
  <div>
    <label>Ruolo
      <select id="slot">
        <option value="">tutti</option>
        <option>GK</option><option>LB</option><option>CB</option><option>RB</option>
        <option>CM</option><option>LW</option><option>ST</option><option>RW</option>
      </select>
    </label>
    <label>Campionato <select id="league"><option value="">tutti</option></select></label>
    <label>OVR min <input id="ovr" type="number" value="70" style="width:4em"></label>
    <label>POT min <input id="pot" type="number" value="75" style="width:4em"></label>
    <label><input id="real" type="checkbox" checked> solo campionati reali (no Classic XI / Soccer Aid / FA)</label>
    <label><input id="women" type="checkbox"> femminili</label>
    <label>Cerca <input id="q" placeholder="nome / club"></label>
  </div>
  <div id="market-table"></div>
</section>
<section id="growth" class="panel">
  <p class="sub">Confronto con l’ultimo snapshot SQLite (scout/data/scout.db). Al primo avvio i delta sono vuoti.</p>
  <div id="growth-table"></div>
</section>
<script>
const DATA = __DATA__;
document.getElementById('title').textContent = DATA.meta.club + ' — 4-3-3';
document.getElementById('sub').textContent =
  DATA.meta.manager + ' · stagione ' + DATA.meta.season + ' · ' + DATA.meta.league +
  ' · ' + DATA.players.length + ' giocatori nel save';

const leagues = [...new Set(DATA.players.map(p => p.league).filter(Boolean))].sort();
const ls = document.getElementById('league');
leagues.forEach(n => { const o = document.createElement('option'); o.value = n; o.textContent = n; ls.appendChild(o); });

document.querySelectorAll('button.tab').forEach(b => {
  b.onclick = () => {
    document.querySelectorAll('button.tab').forEach(x => x.classList.remove('on'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    document.getElementById(b.dataset.tab).classList.add('on');
  };
});

function table(rows, extra) {
  const slots = DATA.slots;
  let h = '<table><thead><tr><th>Nome</th><th>OVR</th><th>POT</th><th>Età</th><th>Valore</th><th>Δ val</th><th>Pos</th><th>Best</th><th>Club</th><th>Lega</th>';
  slots.forEach(s => h += '<th>' + s + '</th>');
  if (extra) h += extra.head;
  h += '</tr></thead><tbody>';
  rows.forEach(p => {
    const dval = p.d_value_txt || '';
    const dcls = (p.d_value||0) > 0 ? 'up' : ((p.d_value||0) < 0 ? 'down' : '');
    h += '<tr><td>' + esc(p.name) + '</td><td>' + nz(p.ovr) + '</td><td>' + nz(p.pot) + '</td><td>' + nz(p.age) +
      '</td><td>' + esc(p.value_txt) + '</td><td class="' + dcls + '">' + esc(dval) + '</td><td>' + p.pos +
      '</td><td>' + p.best + '</td><td>' + esc(p.club) + '</td><td>' + esc(p.league) + '</td>';
    slots.forEach(s => h += '<td class="fit">' + p.fits[s] + '</td>');
    if (extra) h += extra.cell(p);
    h += '</tr>';
  });
  return h + '</tbody></table>';
}
function esc(s) { return String(s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function nz(v) { return (v===null||v===undefined) ? '' : v; }
function delta(v) {
  if (v===null||v===undefined) return '';
  return (v>0?'+':'') + v;
}

const mine = DATA.players.filter(p => p.mine).sort((a,b) => (b.value||0)-(a.value||0));
document.getElementById('squad-table').innerHTML = table(mine, {
  head: '<th>ΔOVR</th><th>Ruolo</th><th>Stipendio</th>',
  cell: p => '<td class="' + ((p.d_ovr||0)>0?'up':((p.d_ovr||0)<0?'down':'')) + '">' + delta(p.d_ovr) + '</td><td>' + esc(p.role) + '</td><td>' + (p.wage||'') + '</td>'
});
document.getElementById('growth-table').innerHTML = table(
  mine.filter(p => p.d_ovr!==null || p.d_value!==null),
  { head: '<th>ΔOVR</th><th>ΔPOT</th>', cell: p => '<td>' + delta(p.d_ovr) + '</td><td>' + delta(p.d_pot) + '</td>' }
);

function renderMarket() {
  const slot = document.getElementById('slot').value;
  const league = document.getElementById('league').value;
  const ovr = Number(document.getElementById('ovr').value||0);
  const pot = Number(document.getElementById('pot').value||0);
  const q = document.getElementById('q').value.toLowerCase();
  const real = document.getElementById('real').checked;
  const women = document.getElementById('women').checked;
  let rows = DATA.players.filter(p => !p.mine);
  if (real) rows = rows.filter(p => !p.special);
  if (!women) rows = rows.filter(p => !p.women);
  if (league) rows = rows.filter(p => p.league === league);
  if (ovr) rows = rows.filter(p => (p.ovr||0) >= ovr);
  if (pot) rows = rows.filter(p => (p.pot||0) >= pot);
  if (q) rows = rows.filter(p => (p.name+' '+p.club).toLowerCase().includes(q));
  const score = slot ? (p => p.fits[slot]||0) : (p => p.ovr||0);
  rows.sort((a,b) => (b.named - a.named) || (score(b) - score(a)));
  rows = rows.slice(0, 400);
  document.getElementById('market-table').innerHTML = table(rows);
}
['slot','league','ovr','pot','q','real','women'].forEach(id => {
  document.getElementById(id).addEventListener('input', renderMarket);
  document.getElementById(id).addEventListener('change', renderMarket);
});
renderMarket();
</script>
</body>
</html>
"""


def main() -> None:
    save = latest_career_save()
    print("Save:", save)
    print("Loading name/value catalog...")
    ea = load_ea_names()
    catalog = load_catalog()
    print(f"Names: {len(ea)}  catalog: {len(catalog)}")
    print("Parsing save...")
    path, career, world = open_career(save)
    players, meta = rows_from_world(career, world, ea, catalog)
    sid = save_snapshot(meta, players, save.name)
    apply_growth(players, previous_mine(meta["club"], sid))
    dest = write_html(players, meta)
    print(f"Players: {len(players)}  club={meta['club']}  squad={sum(1 for p in players if p['mine'])}  snapshot={sid}")
    print("Wrote", dest)
    webbrowser.open(dest.as_uri())


if __name__ == "__main__":
    main()
