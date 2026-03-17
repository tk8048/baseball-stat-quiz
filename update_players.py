import json
import urllib.request
import pandas as pd
from pybaseball import bwar_bat, bwar_pitch

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
    return players

def get_players():
    """
    Fetches real bWAR data from Baseball-Reference via pybaseball,
    then produces TWO player lists:
      - alltime:  top-150 hitters + top-150 pitchers by career WAR (all eras)
      - modern:   top-150 hitters + top-150 pitchers by career WAR,
                  filtered to only players who appeared in a season >= 2000
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

        print(f"All-time pool: {len(top_bats_alltime)} hitters, {len(top_pitch_alltime)} pitchers.")
        print(f"Modern pool:   {len(top_bats_modern)} hitters, {len(top_pitch_modern)} pitchers.")
    except Exception as e:
        print(f"Error processing bWAR data: {e}")
        return None, None

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

    alltime = alltime_hitters + alltime_pitchers
    modern = modern_hitters + modern_pitchers

    return alltime, modern

if __name__ == "__main__":
    try:
        alltime, modern = get_players()

        if alltime:
            with open('players_alltime.json', 'w') as f:
                json.dump(alltime, f, separators=(',', ':'))
            print(f"\nSuccess! Generated players_alltime.json with {len(alltime)} players.")
        else:
            print("\nNo all-time data collected. Check your internet connection.")

        if modern:
            with open('players_modern.json', 'w') as f:
                json.dump(modern, f, separators=(',', ':'))
            print(f"Success! Generated players_modern.json with {len(modern)} players.")
        else:
            print("\nNo modern data collected. Check your internet connection.")
    except Exception as e:
        print(f"\nError: {e}")
