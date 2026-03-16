import urllib.request
import json
import time

def fetch_json(url):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def get_players():
    print("Connecting to MLB Stats API...")
    
    # We'll pull the top 100 HR hitters and top 100 Strikeout pitchers as our base pool
    hitter_url = "https://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=homeRuns&statGroup=hitting&statType=career&limit=100"
    pitcher_url = "https://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=strikeouts&statGroup=pitching&statType=career&limit=100"
    
    try:
        hitter_raw = fetch_json(hitter_url)
        pitcher_raw = fetch_json(pitcher_url)
        
        hitter_data = hitter_raw['leagueLeaders'][0]['leaders']
        pitcher_data = pitcher_raw['leagueLeaders'][0]['leaders']
    except Exception as e:
        print(f"Failed to fetch initial leaderboards: {e}")
        return []
    
    players = []

    # Process Hitters
    print("Processing Hitters...")
    for entry in hitter_data:
        person_id = entry['person']['id']
        name = entry['person']['fullName']
        
        # Hydrate career stats
        detail_url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[hitting],type=[career])"
        try:
            details = fetch_json(detail_url)['people'][0]
            # Dig deeper into stats to find the career split accurately
            stat_list = details.get('stats', [])
            if not stat_list: continue
            stat = stat_list[0]['splits'][0]['stat']
            
            # Real bWAR is not in the public API, so we use a high-correlation proxy 
            # Or ideally, we'd scrape, but for now we match the keys exactly.
            approx_war = round(float(stat.get('homeRuns', 0)) / 5.0 + float(stat.get('hits', 0)) / 100.0, 1)
            
            players.append({
                "name": name,
                "type": "hitter",
                "war": approx_war,
                "stats": {
                    "Home Runs": int(stat.get('homeRuns', 0)),
                    "Hits": int(stat.get('hits', 0)),
                    "Batting Average": round(float(stat.get('avg', 0)), 4)
                }
            })
        except Exception as e:
            continue

    # Process Pitchers
    print("Processing Pitchers...")
    for entry in pitcher_data:
        person_id = entry['person']['id']
        name = entry['person']['fullName']
        
        detail_url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[pitching],type=[career])"
        try:
            details = fetch_json(detail_url)['people'][0]
            stat_list = details.get('stats', [])
            if not stat_list: continue
            stat = stat_list[0]['splits'][0]['stat']
            
            approx_war = round(float(stat.get('wins', 0)) * 1.5 + float(stat.get('strikeouts', 0)) / 50.0, 1)

            players.append({
                "name": name,
                "type": "pitcher",
                "war": approx_war,
                "stats": {
                    "ERA": round(float(stat.get('era', 0)), 2),
                    "Wins": int(stat.get('wins', 0)),
                    "Strikeouts": int(stat.get('strikeouts', 0))
                }
            })
        except Exception as e:
            continue

    return players

if __name__ == "__main__":
    try:
        data = get_players()
        if data:
            with open('players.json', 'w') as f:
                # Original file was minified (one line)
                json.dump(data, f, separators=(',', ':'))
            print(f"\nSuccess! Generated minified players.json with {len(data)} players.")
        else:
            print("\nNo data collected. Check your internet connection.")
    except Exception as e:
        print(f"\nError: {e}")
