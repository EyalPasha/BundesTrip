import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re

# Output file
file_path = r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\liga3_games.txt"
START = 29 # starts on 1, ends on 38 (for 38 need to write 39)
END = 39

# Overwrite the file with a header row
with open(file_path, "w", encoding="utf-8") as f:
    f.write("League, Date, Time, Day, Home Team, Away Team\n")

all_matches = []

# Define USER_AGENTS before it's used
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

def get_fresh_session():
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.kicker.de/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1"
    })
    return session

def update_headers_for_request(session):
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive"
    })

# Reset session every 5 requests
request_counter = 0
MAX_REQUESTS_PER_SESSION = 5

# Initialize session once
session = get_fresh_session()

time_pattern = re.compile(r"^\d{1,2}:\d{2}$")

for matchday in range(START, END):
    url = f"https://www.kicker.de/3-liga/spieltag/2024-25/{matchday}"
    print(f"\n--- Attempting to fetch 3. Liga matchday {matchday} ---")
    print(f"URL: {url}")

    # Brief random sleep
    time.sleep(random.uniform(5, 10))  # 5-10 second delay

    request_counter += 1
    if request_counter >= MAX_REQUESTS_PER_SESSION:
        print("Creating fresh session...")
        session = get_fresh_session()
        request_counter = 0
    else:
        # Just update headers if we're keeping the same session
        update_headers_for_request(session)

    try:
        resp = session.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[INFO] Request error: {e} — skipping matchday {matchday}.")
        continue

    if resp.status_code != 200:
        print(f"[INFO] Got status code {resp.status_code}, skipping matchday {matchday}.")
        continue

    soup = BeautifulSoup(resp.text, "html.parser")

    # All match rows
    game_rows = soup.find_all("div", class_=re.compile("kick__v100-gameList__gameRow"))
    if not game_rows:
        print(f"[INFO] No matches found for matchday {matchday}.")
        continue

    # 1) Check if the first match is already in the past
    first_row = game_rows[0]
    first_header = first_row.find_previous("div", class_="kick__v100-gameList__header")
    if first_header:
        header_text = first_header.get_text(strip=True)
        parts = header_text.split(",", 1)
        if len(parts) == 2:
            date_str = parts[1].strip()
            time_found = None
            holders = first_row.find_all("div", class_="kick__v100-scoreBoard__dateHolder")
            for h in holders:
                t = h.get_text(strip=True)
                if time_pattern.match(t):
                    time_found = t
                    break
            if not time_found:
                time_found = "13:00"

            dt_str = f"{date_str} {time_found}"
            try:
                first_dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
                if first_dt < datetime.now():
                    print(f"[INFO] First match on {first_dt} is in the past. Skipping matchday {matchday}.")
                    continue
            except ValueError:
                pass

    # 2) Gather all matches for this matchday in a temporary list
    #    We'll check if they all share the same time => "TBD"
    row_data = []
    seen_matches = set()
    distinct_times = set()

    for row in game_rows:
        # Find the nearest date header above
        row_header_div = row.find_previous("div", class_="kick__v100-gameList__header")
        if not row_header_div:
            continue

        row_header_text = row_header_div.get_text(strip=True)
        parts = row_header_text.split(",", 1)
        if len(parts) != 2:
            continue

        block_date_str = parts[1].strip()

        # Extract home/away teams via CSS selector
        teams = row.select("div.kick__v100-gameCell__team__shortname")
        if len(teams) < 2:
            continue

        home_team = teams[0].get_text(strip=True)
        away_team = teams[1].get_text(strip=True)

        # Look for time or default to 13:00
        match_time = None
        holders = row.find_all("div", class_="kick__v100-scoreBoard__dateHolder")
        for h in holders:
            t = h.get_text(strip=True)
            if time_pattern.match(t):
                match_time = t
                break
        if not match_time:
            match_time = "13:00"

        # Deduplicate by date/time/home/away
        match_key = (block_date_str, match_time, home_team, away_team)
        if match_key in seen_matches:
            continue
        seen_matches.add(match_key)

        distinct_times.add(match_time)

        row_data.append({
            "date_str_raw": block_date_str,  # e.g. "28.03.2025"
            "time_raw": match_time,          # e.g. "13:30"
            "home": home_team,
            "away": away_team
        })

    # If we found no valid rows, skip
    if not row_data:
        print(f"[INFO] No valid matches for matchday {matchday}.")
        continue

    # 3) If all times are the same => "TBD" for this matchday
    all_same_time = (len(distinct_times) == 1)
    # We'll store the final (date, time, day, teams) for each row in the master list

    for info in row_data:
        block_date_str = info["date_str_raw"]
        match_time     = info["time_raw"]
        home_team      = info["home"]
        away_team      = info["away"]

        # If the entire matchday is "TBD," we won't parse an actual time
        if all_same_time:
            # Keep date as is, but set time to "TBD"
            final_time = "TBD"
            # For the day, let's parse the date with "00:00" so we can get a day name
            try:
                date_obj = datetime.strptime(block_date_str + " 00:00", "%d.%m.%Y %H:%M")
                day_display = date_obj.strftime("%A")
                date_display = date_obj.strftime("%d %B")
            except ValueError:
                # Fallback if parsing fails
                day_display = "Unknown"
                date_display = block_date_str
        else:
            # Otherwise, parse and add +1 hour
            dt_str = f"{block_date_str} {match_time}"
            try:
                match_dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
            except ValueError:
                # If parse fails, store them way at the end
                match_dt = datetime.max

            match_dt_plus_one = match_dt + timedelta(hours=1)
            date_display = match_dt_plus_one.strftime("%d %B")
            final_time   = match_dt_plus_one.strftime("%H:%M")
            day_display  = match_dt_plus_one.strftime("%A")

        match_info = {
            "league": "3-liga",
            "date_str": date_display,
            "time_str": final_time,
            "day_str":  day_display,
            "home_team": home_team,
            "away_team": away_team
        }
        # We'll attach a sort key
        if all_same_time:
            # If TBD, let's treat date midnight as the datetime (for sorting).
            try:
                match_info["match_datetime"] = datetime.strptime(block_date_str + " 00:00", "%d.%m.%Y %H:%M")
            except ValueError:
                match_info["match_datetime"] = datetime.max
        else:
            match_info["match_datetime"] = match_dt_plus_one

        all_matches.append(match_info)

    print(f"[INFO] Collected {len(row_data)} matches for matchday {matchday}.")

# Sort all matches by datetime
all_matches.sort(key=lambda x: x["match_datetime"])

# Write final data
with open(file_path, "a", encoding="utf-8") as f:
    for m in all_matches:
        line = (
            f"{m['league']}, "
            f"{m['date_str']}, "
            f"{m['time_str']}, "
            f"{m['day_str']}, "
            f"{m['home_team']}, "
            f"{m['away_team']}"
        )
        f.write(line + "\n")

print(f"\nAll done! {len(all_matches)} total matches written to: {file_path}")
