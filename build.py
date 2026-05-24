#!/usr/bin/env python3
"""
F1CC Wiki — Automated JSON builder
Reads CSVs from data/csv/ and rebuilds races_2026.json + db.json standings.
Run locally or via GitHub Actions on CSV push.
"""

import json, os, re, sys
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR    = os.path.join(os.path.dirname(__file__), 'data')
CSV_2026    = os.path.join(DATA_DIR, 'csv', 'F1CC_2026.csv')
DB_PATH     = os.path.join(DATA_DIR, 'db.json')
OUT_2026    = os.path.join(DATA_DIR, 'races_2026.json')

TEAM_IDS = {
    'VCA':'vcarb','RBR':'red_bull','FER':'ferrari','MCL':'mclaren',
    'MER':'mercedes','AST':'aston_martin','WIL':'williams',
    'HAA':'haas','SAU':'kick_sauber','ALP':'alpine','AUD':'audi',
}
RACE_PTS    = {1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
SPRINT_PTS  = {1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1}
SPRINTS     = {'CHNS','SAUS','AUSS','NETS','USAS','BRAS'}
RACE_META   = {
    'AUS' :{'flag':'🇦🇺','circuit':'Albert Park'},
    'CHNS':{'flag':'🇨🇳','circuit':'Shanghai Sprint'},
    'CHN' :{'flag':'🇨🇳','circuit':'Shanghai'},
    'JPN' :{'flag':'🇯🇵','circuit':'Suzuka'},
    'BAH' :{'flag':'🇧🇭','circuit':'Bahrain International'},
    'SAUS':{'flag':'🇸🇦','circuit':'Jeddah Sprint'},
    'SAU' :{'flag':'🇸🇦','circuit':'Jeddah Street'},
    'MIA' :{'flag':'🇺🇸','circuit':'Miami International'},
    'CAN' :{'flag':'🇨🇦','circuit':'Circuit Gilles Villeneuve'},
    'MON' :{'flag':'🇲🇨','circuit':'Monaco'},
    'SPA' :{'flag':'🇪🇸','circuit':'Circuit de Barcelona'},
    'AUSS':{'flag':'🇦🇺','circuit':'Albert Park Sprint'},
    'BRI' :{'flag':'🇬🇧','circuit':'Silverstone'},
    'BEL' :{'flag':'🇧🇪','circuit':'Spa-Francorchamps'},
    'HUN' :{'flag':'🇭🇺','circuit':'Hungaroring'},
    'NETS':{'flag':'🇳🇱','circuit':'Zandvoort Sprint'},
    'NET' :{'flag':'🇳🇱','circuit':'Zandvoort'},
    'ITA' :{'flag':'🇮🇹','circuit':'Monza'},
    'AZE' :{'flag':'🇦🇿','circuit':'Baku'},
    'SIN' :{'flag':'🇸🇬','circuit':'Marina Bay'},
    'USAS':{'flag':'🇺🇸','circuit':'COTA Sprint'},
    'USA' :{'flag':'🇺🇸','circuit':'Circuit of the Americas'},
    'MEX' :{'flag':'🇲🇽','circuit':'Hermanos Rodriguez'},
    'BRAS':{'flag':'🇧🇷','circuit':'Interlagos Sprint'},
    'BRA' :{'flag':'🇧🇷','circuit':'Interlagos'},
    'LVG' :{'flag':'🇺🇸','circuit':'Las Vegas Street'},
    'ABU' :{'flag':'🇦🇪','circuit':'Yas Marina'},
}

def parse_pos(raw):
    """Parse a position value like '1', '1*', 'DNF', '0' (absent)."""
    s = str(raw).strip()
    if s in ('nan', '0', ''):
        return None, False
    fl = s.endswith('*')
    s = s.rstrip('*')
    if s.upper() in ('DNF','DSQ','RET'):
        return s.upper(), fl
    try:
        return int(s), fl
    except ValueError:
        return None, False

def find_section(df, header_text, col=2):
    """Find the row index of a section header."""
    for i, row in df.iterrows():
        if str(row.iloc[col]).strip().upper() == header_text.upper():
            return i
    return None

def build_2026():
    if not os.path.exists(CSV_2026):
        print(f"CSV not found: {CSV_2026}")
        sys.exit(1)

    df = pd.read_csv(CSV_2026)

    # Race codes from header row (cols 3-30)
    races_raw = list(df.columns[3:31])
    # Fix duplicate names (pandas adds .1 etc) — strip suffix
    races_clean = [re.sub(r'\.\d+$', '', r) for r in races_raw]
    print(f"Races: {races_clean}")

    # ── Locate sections ──────────────────────────────────────────────────────
    # Results: rows 0–19 (driver name in col2, flag in col1)
    pos_rows  = df.iloc[0:20, :]

    # Qualifying: header row says "QUALIFYING", data follows
    quali_header = find_section(df, 'QUALIFYING')
    quali_rows   = df.iloc[quali_header+1 : quali_header+21, :] if quali_header else None

    # Team: header row says "F1CC", data follows
    team_header = find_section(df, 'F1CC')
    # The SECOND occurrence of F1CC is the teams section (first is just results label)
    # Find both and take the second
    f1cc_rows = []
    for i, row in df.iterrows():
        if str(row.iloc[2]).strip() == 'F1CC':
            f1cc_rows.append(i)
    team_header = f1cc_rows[1] if len(f1cc_rows) > 1 else None
    team_rows   = df.iloc[team_header+1 : team_header+21, :] if team_header else None

    print(f"Sections: quali_header={quali_header}, team_header={team_header}")

    # ── Build lookup maps ─────────────────────────────────────────────────────
    def build_map(rows, col_start=3, col_end=31):
        m = {}
        if rows is None:
            return m
        for _, row in rows.iterrows():
            name = str(row.iloc[2]).strip()
            if name in ('nan', ''):
                continue
            m[name] = [str(row.iloc[c]) for c in range(col_start, col_end)]
        return m

    pos_map   = build_map(pos_rows)
    quali_map = build_map(quali_rows) if quali_rows is not None else {}
    team_map  = build_map(team_rows)  if team_rows  is not None else {}

    # ── Build race results ────────────────────────────────────────────────────
    with open(DB_PATH) as f:
        db = json.load(f)

    existing_races = {r['name']: r for r in db['seasons'].get('2026', {}).get('calendar', [])}
    races_out = []

    for rnd_idx, rcode in enumerate(races_clean):
        is_sprint  = rcode in SPRINTS
        meta       = RACE_META.get(rcode, {})
        pts_table  = SPRINT_PTS if is_sprint else RACE_PTS

        entries = []
        for driver, pos_vals in pos_map.items():
            if rnd_idx >= len(pos_vals):
                continue
            pos, fl = parse_pos(pos_vals[rnd_idx])
            if pos is None:
                continue  # absent / not entered

            # Team from team_map
            t_raw = team_map.get(driver, [None]*28)
            t_code = t_raw[rnd_idx] if rnd_idx < len(t_raw) else 'nan'
            team = TEAM_IDS.get(str(t_code).strip())

            # Quali position
            q_vals = quali_map.get(driver, [None]*28)
            q_raw  = q_vals[rnd_idx] if rnd_idx < len(q_vals) else None
            try:
                quali_pos = int(str(q_raw).strip())
                if quali_pos == 0:
                    quali_pos = None
            except (ValueError, TypeError):
                quali_pos = None

            # Points
            if isinstance(pos, int):
                pts = pts_table.get(pos, 0)
                if fl and not is_sprint and pos <= 10:
                    pts += 1
            else:
                pts = 0

            entries.append({
                'driver':     driver,
                'pos':        pos,
                'team':       team,
                'fastest_lap': fl,
                'quali_pos':  quali_pos,
                'points':     pts,
            })

        entries.sort(key=lambda e: e['pos'] if isinstance(e['pos'], int) else 99)

        has_results = any(isinstance(e['pos'], int) or e['pos'] in ('DNF','DSQ') for e in entries)
        races_out.append({
            'round':   rnd_idx + 1,
            'id':      f"{rcode.lower()}_r{rnd_idx+1}",
            'name':    rcode,
            'flag':    meta.get('flag', '🏁'),
            'circuit': meta.get('circuit', rcode),
            'date':    '2026',
            'sprint':  is_sprint,
            'status':  'complete' if has_results else 'upcoming',
            'results': entries,
        })

    # ── Update db.json driver standings ──────────────────────────────────────
    driver_stats = {}
    for race in races_out:
        for e in race['results']:
            d = e['driver']
            if d not in driver_stats:
                driver_stats[d] = {'wins':0,'podiums':0,'fl':0,'poles':0,'races':0,'points':0}
            driver_stats[d]['races']  += 1
            driver_stats[d]['points'] += e['points']
            if isinstance(e['pos'], int) and e['pos'] == 1:
                driver_stats[d]['wins'] += 1
            if isinstance(e['pos'], int) and e['pos'] <= 3:
                driver_stats[d]['podiums'] += 1
            if e['fastest_lap']:
                driver_stats[d]['fl'] += 1
            if e.get('quali_pos') == 1:
                driver_stats[d]['poles'] += 1

    # Update 2026 driver standings in db
    s26 = db['seasons']['2026']
    for row in s26['driver_standings']:
        s = driver_stats.get(row['driver'], {})
        row['wins']         = s.get('wins', 0)
        row['podiums']      = s.get('podiums', 0)
        row['fastest_laps'] = s.get('fl', 0)
        row['poles']        = s.get('poles', 0)
        row['races']        = s.get('races', 0)
        row['points']       = s.get('points', 0)

    # Re-sort standings by points
    s26['driver_standings'].sort(key=lambda x: -x['points'])
    for i, row in enumerate(s26['driver_standings']):
        row['pos'] = i + 1

    # Update constructor standings from race results
    team_pts = {}
    for race in races_out:
        for e in race['results']:
            t = e['team']
            if t:
                team_pts[t] = team_pts.get(t, 0) + e['points']

    s26['constructor_standings'] = sorted(
        [{'team':t,'points':v,'pos':i+1,'wins':0,'podiums':0}
         for i,(t,v) in enumerate(sorted(team_pts.items(), key=lambda x:-x[1]))],
        key=lambda x: x['pos']
    )
    # If no points yet keep pre-season lineup
    if not any(r['points'] for r in s26['constructor_standings']):
        pass  # keep as is

    # ── Write outputs ─────────────────────────────────────────────────────────
    with open(OUT_2026, 'w', encoding='utf-8') as f:
        json.dump({'races': races_out}, f, indent=2, ensure_ascii=False)
    print(f"✓ {OUT_2026}: {len(races_out)} races, "
          f"{sum(1 for r in races_out if r['status']=='complete')} complete")

    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print(f"✓ {DB_PATH}: standings updated")

if __name__ == '__main__':
    build_2026()
