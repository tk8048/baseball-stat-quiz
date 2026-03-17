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

def get_players():
    """
    Fetches real bWAR data from Baseball-Reference via pybaseball
    and hydrates career stats from the MLB Stats API.
    """
    players = []

    print("Loading bWAR data from pybaseball (Baseball-Reference)...")
    try:
        # These functions download the entire bWAR datasets from pybaseball's cache
        bat_war_df = bwar_bat()
        pitch_war_df = bwar_pitch()
        
        # Aggregate career WAR by mlb_ID
        bat_war_df = bat_war_df.dropna(subset=['mlb_ID'])
        bat_war_df['mlb_ID'] = bat_war_df['mlb_ID'].astype(int)
        bat_career = bat_war_df.groupby('mlb_ID')['WAR'].sum().reset_index()
        
        pitch_war_df = pitch_war_df.dropna(subset=['mlb_ID'])
        pitch_war_df['mlb_ID'] = pitch_war_df['mlb_ID'].astype(int)
        pitch_career = pitch_war_df.groupby('mlb_ID')['WAR'].sum().reset_index()
        
        # Take the top 150 of each by career WAR
        top_bats = bat_career.sort_values('WAR', ascending=False).head(150)
        top_pitch = pitch_career.sort_values('WAR', ascending=False).head(150)
        
        print(f"Pool prepared: {len(top_bats)} hitters and {len(top_pitch)} pitchers.")
    except Exception as e:
        print(f"Error processing bWAR data: {e}")
        return []

    # Process Hitters
    print("Hydrating Hitters from MLB Stats API...")
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

    # Process Pitchers
    print("Hydrating Pitchers from MLB Stats API...")
    pitcher_count = 0
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
        pitcher_count += 1
        if pitcher_count % 25 == 0:
            print(f"  Processed {pitcher_count} pitchers...")

    return players

if __name__ == "__main__":
    try:
        data = get_players()
        if data:
            with open('players.json', 'w') as f:
                json.dump(data, f, separators=(',', ':'))
            print(f"\nSuccess! Generated players.json with {len(data)} players.")
        else:
            print("\nNo data collected. Check your internet connection.")
    except Exception as e:
        print(f"\nError: {e}")
