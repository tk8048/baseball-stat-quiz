import json
import time
import urllib.request
import pandas as pd
from pybaseball import bwar_bat, bwar_pitch

MIN_PLAYERS = 100  # Refuse to write JSON if fewer than this many players collected

def fetch_json(url):
    """Utility to fetch JSON from a URL."""
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_modern_mlb_ids(bat_war_df, pitch_war_df):
    """
    Return sets of mlb_IDs for players who appeared in any season >= 2000.
    Any player with at least one row in a year_ID >= 2000 qualifies.
    """
    modern_bat_ids = set(
        bat_war_df.loc[bat_war_df['year_ID'] >= 2000, 'mlb_ID']
        .dropna().astype(int).unique()
    )
    modern_pitch_ids = set(
        pitch_war_df.loc[pitch_war_df['year_ID'] >= 2000, 'mlb_ID']
        .dropna().astype(int).unique()
    )
    return modern_bat_ids, modern_pitch_ids

def get_current_mlb_ids():
    """
    Return a set of mlb_IDs for players currently on active MLB rosters.
    Fetches 40-man rosters for all 30 teams from the MLB Stats API.
    """
    current_ids = set()
    # Fetch all MLB teams
    teams_url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    teams_data = fetch_json(teams_url)
    if not teams_data or 'teams' not in teams_data:
        print("Warning: Could not fetch MLB teams list.")
        return current_ids

    team_ids = [t['id'] for t in teams_data['teams']]
    print(f"Fetching rosters for {len(team_ids)} MLB teams...")

    for tid in team_ids:
        roster_url = f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster?rosterType=40Man"
        roster_data = fetch_json(roster_url)
        if roster_data and 'roster' in roster_data:
            for entry in roster_data['roster']:
                pid = entry.get('person', {}).get('id')
                if pid:
                    current_ids.add(int(pid))

    print(f"Found {len(current_ids)} players on current 40-man rosters.")
    return current_ids

def hydrate_hitters(top_bats):
    """Fetch career stats from MLB Stats API for a set of hitters."""
    players = []
    for idx, row in top_bats.iterrows():
        mlb_id = int(row['mlb_ID'])
        war = round(float(row['WAR']), 1)

        detail_url = f"https://statsapi.mlb.com/api/v1/people/{mlb_id}?hydrate=stats(group=[hitting],type=[career])"
        details = fetch_json(detail_url)
        if not details or not details.get('people'):
            continue

        person = details['people'][0]
        name = person.get('fullName')
        stats_list = person.get('stats', [])

        if not stats_list or not stats_list[0].get('splits'):
            continue

        stat = stats_list[0]['splits'][0]['stat']

        players.append({
            "name": name,
            "type": "hitter",
            "war": war,
            "stats": {
                "Home Runs": int(stat.get('homeRuns', 0)),
                "Hits": int(stat.get('hits', 0)),
                "Batting Average": round(float(stat.get('avg', 0)), 4)
            }
        })
        if len(players) % 25 == 0:
            print(f"  Processed {len(players)} hitters...")
        time.sleep(0.1)  # Rate-limit API calls
    return players

def hydrate_pitchers(top_pitch):
    """Fetch career stats from MLB Stats API for a set of pitchers."""
    players = []
    for idx, row in top_pitch.iterrows():
        mlb_id = int(row['mlb_ID'])
        war = round(float(row['WAR']), 1)

        detail_url = f"https://statsapi.mlb.com/api/v1/people/{mlb_id}?hydrate=stats(group=[pitching],type=[career])"
        details = fetch_json(detail_url)
        if not details or not details.get('people'):
            continue

        person = details['people'][0]
        name = person.get('fullName')
        stats_list = person.get('stats', [])

        if not stats_list or not stats_list[0].get('splits'):
            continue

        stat = stats_list[0]['splits'][0]['stat']

        players.append({
            "name": name,
            "type": "pitcher",
            "war": war,
            "stats": {
                "ERA": round(float(stat.get('era', 0)), 2),
                "Wins": int(stat.get('wins', 0)),
                "Strikeouts": int(stat.get('strikeOuts', 0))
            }
        })
        if len(players) % 25 == 0:
            print(f"  Processed {len(players)} pitchers...")
        time.sleep(0.1)  # Rate-limit API calls
    return players

def get_players():
    """
    Fetches real bWAR data from Baseball-Reference via pybaseball,
    then produces THREE player lists:
      - alltime:  top-150 hitters + top-150 pitchers by career WAR (all eras)
      - modern:   top-150 hitters + top-150 pitchers by career WAR,
                  filtered to only players who appeared in a season >= 2000
      - current:  top-150 hitters + top-150 pitchers by career WAR,
                  filtered to only players on active MLB 40-man rosters
    """
    print("Loading bWAR data from pybaseball (Baseball-Reference)...")
    try:
        bat_war_df = bwar_bat()
        pitch_war_df = bwar_pitch()

        # Clean mlb_ID
        bat_war_df = bat_war_df.dropna(subset=['mlb_ID'])
        bat_war_df['mlb_ID'] = bat_war_df['mlb_ID'].astype(int)
        pitch_war_df = pitch_war_df.dropna(subset=['mlb_ID'])
        pitch_war_df['mlb_ID'] = pitch_war_df['mlb_ID'].astype(int)

        # Get sets of modern player IDs (any season >= 2000)
        modern_bat_ids, modern_pitch_ids = get_modern_mlb_ids(bat_war_df, pitch_war_df)
        print(f"Found {len(modern_bat_ids)} modern hitters and {len(modern_pitch_ids)} modern pitchers (played in 2000+).")

        # Get current active MLB player IDs
        current_ids = get_current_mlb_ids()

        # Aggregate career WAR by mlb_ID
        bat_career = bat_war_df.groupby('mlb_ID')['WAR'].sum().reset_index()
        pitch_career = pitch_war_df.groupby('mlb_ID')['WAR'].sum().reset_index()

        # ── All-time: top 150 each ──
        top_bats_alltime = bat_career.sort_values('WAR', ascending=False).head(150)
        top_pitch_alltime = pitch_career.sort_values('WAR', ascending=False).head(150)

        # ── Modern: filter to modern IDs, then top 150 each ──
        bat_career_modern = bat_career[bat_career['mlb_ID'].isin(modern_bat_ids)]
        pitch_career_modern = pitch_career[pitch_career['mlb_ID'].isin(modern_pitch_ids)]
        top_bats_modern = bat_career_modern.sort_values('WAR', ascending=False).head(150)
        top_pitch_modern = pitch_career_modern.sort_values('WAR', ascending=False).head(150)

        # ── Current: filter to active roster IDs, then top 150 each ──
        bat_career_current = bat_career[bat_career['mlb_ID'].isin(current_ids)]
        pitch_career_current = pitch_career[pitch_career['mlb_ID'].isin(current_ids)]
        top_bats_current = bat_career_current.sort_values('WAR', ascending=False).head(150)
        top_pitch_current = pitch_career_current.sort_values('WAR', ascending=False).head(150)

        print(f"All-time pool: {len(top_bats_alltime)} hitters, {len(top_pitch_alltime)} pitchers.")
        print(f"Modern pool:   {len(top_bats_modern)} hitters, {len(top_pitch_modern)} pitchers.")
        print(f"Current pool:  {len(top_bats_current)} hitters, {len(top_pitch_current)} pitchers.")
    except Exception as e:
        print(f"Error processing bWAR data: {e}")
        return None, None, None

    # ── Hydrate all-time ──
    print("\n=== Hydrating ALL-TIME Hitters ===")
    alltime_hitters = hydrate_hitters(top_bats_alltime)
    print(f"  Total all-time hitters: {len(alltime_hitters)}")

    print("\n=== Hydrating ALL-TIME Pitchers ===")
    alltime_pitchers = hydrate_pitchers(top_pitch_alltime)
    print(f"  Total all-time pitchers: {len(alltime_pitchers)}")

    # ── Hydrate modern ──
    print("\n=== Hydrating MODERN Hitters ===")
    modern_hitters = hydrate_hitters(top_bats_modern)
    print(f"  Total modern hitters: {len(modern_hitters)}")

    print("\n=== Hydrating MODERN Pitchers ===")
    modern_pitchers = hydrate_pitchers(top_pitch_modern)
    print(f"  Total modern pitchers: {len(modern_pitchers)}")

    # ── Hydrate current ──
    print("\n=== Hydrating CURRENT Hitters ===")
    current_hitters = hydrate_hitters(top_bats_current)
    print(f"  Total current hitters: {len(current_hitters)}")

    print("\n=== Hydrating CURRENT Pitchers ===")
    current_pitchers = hydrate_pitchers(top_pitch_current)
    print(f"  Total current pitchers: {len(current_pitchers)}")

    alltime = alltime_hitters + alltime_pitchers
    modern = modern_hitters + modern_pitchers
    current = current_hitters + current_pitchers

    return alltime, modern, current

if __name__ == "__main__":
    try:
        alltime, modern, current = get_players()

        for label, data, filename in [
            ('All-time', alltime, 'players_alltime.json'),
            ('Modern',   modern,  'players_modern.json'),
            ('Current',  current, 'players_current.json'),
        ]:
            if not data:
                print(f"\nNo {label.lower()} data collected. Check your internet connection.")
            elif len(data) < MIN_PLAYERS:
                print(f"\nWARNING: Only got {len(data)} {label.lower()} players "
                      f"(minimum {MIN_PLAYERS}). Keeping existing {filename}.")
            else:
                with open(filename, 'w') as f:
                    json.dump(data, f, separators=(',', ':'))
                print(f"Success! Generated {filename} with {len(data)} players.")
    except Exception as e:
        print(f"\nError: {e}")
