import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re

START_MD         = 1 # starts on 1, ends on 6 (for 6 need to write 7)
END_MD           = 7   
file_path = r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\dfb_pokal_games.txt"

# We want only home teams if their trailing league is in:
ALLOWED_LEAGUES = {"Bundesliga", "2. Bundesliga", "3. Liga"}

# Consider matches older than 1 month (30 days) “too old.”
ONE_MONTH_AGO = datetime.now() - timedelta(days=30)

# We do DFB-Pokal matchdays 1..6
COMPETITION_NAME = "DFB-Pokal"
BASE_SLUG        = "dfb-pokal"

# Overwrite the file with a header row
with open(file_path, "w", encoding="utf-8") as f:
    f.write("League, Date, Time, Day, Home Team, Away Team\n")

all_matches = []

time_pattern = re.compile(r"^\d{1,2}:\d{2}$")

# This regex will capture a trailing league from the team name:
#   e.g. "Bielefeld3. Liga" => group(1)="Bielefeld", group(2)="3. Liga"
#   e.g. "LeverkusenBundesliga" => group(1)="Leverkusen", group(2)="Bundesliga"
# We will use group(1) as the final “pure” team name.
league_pattern = re.compile(r"^(.*?)(Bundesliga|2\. Bundesliga|3\. Liga)$", flags=re.IGNORECASE)

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

def fix_date_string(date_str: str) -> str:
    """
    If kicker shows '08.04.' (missing year), remove trailing '.' if present,
    then append '.2025' if no 4-digit year => '08.04.2025'.
    """
    date_str = date_str.strip()
    if date_str.endswith("."):
        date_str = date_str[:-1]
    if not re.search(r"\b20\d{2}\b", date_str):
        date_str += ".2025"
    return date_str


#########################
# 2) Main Loop
#########################
for matchday in range(START_MD, END_MD):
    url = f"https://www.kicker.de/{BASE_SLUG}/spieltag/2024-25/{matchday}"
    print(f"\n--- {COMPETITION_NAME}, matchday {matchday} ---")
    print(f"URL: {url}")

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
        print(f"[INFO] Request error: {e} — skipping {COMPETITION_NAME} MD {matchday}.")
        continue

    if resp.status_code != 200:
        print(f"[INFO] Got status code {resp.status_code}, skipping {COMPETITION_NAME} MD {matchday}.")
        continue

    soup = BeautifulSoup(resp.text, "html.parser")
    game_rows = soup.find_all("div", class_=re.compile("kick__v100-gameList__gameRow"))
    if not game_rows:
        print(f"[INFO] No matches found for {COMPETITION_NAME} MD {matchday}.")
        continue

    # 1) Check the first match. If older than 30 days => skip entire page
    first_row = game_rows[0]
    first_header = first_row.find_previous("div", class_="kick__v100-gameList__header")
    if first_header:
        splitted = first_header.get_text(strip=True).split(",", 1)
        if len(splitted) == 2:
            date_str_no_year = splitted[1].strip()
            date_str_fixed = fix_date_string(date_str_no_year)
            # scoreboard time or default "13:00"
            time_found = None
            holders = first_row.find_all("div", class_="kick__v100-scoreBoard__dateHolder")
            for h in holders:
                maybe_time = h.get_text(strip=True)
                if time_pattern.match(maybe_time):
                    time_found = maybe_time
                    break
            if not time_found:
                time_found = "13:00"

            dt_str = f"{date_str_fixed} {time_found}"
            try:
                first_dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
                if first_dt < ONE_MONTH_AGO:
                    print(f"[INFO] First match {first_dt} is >30d old. Skipping {COMPETITION_NAME} MD {matchday}.")
                    continue
            except ValueError:
                pass

    # 2) Collect valid matches
    row_data = []
    seen_matches = set()

    for row in game_rows:
        # Each row has a date header above it
        row_header = row.find_previous("div", class_="kick__v100-gameList__header")
        if not row_header:
            continue

        splitted = row_header.get_text(strip=True).split(",", 1)
        if len(splitted) != 2:
            continue

        date_str_no_year = splitted[1].strip()
        date_str_fixed = fix_date_string(date_str_no_year)

        teams = row.select("div.kick__v100-gameCell__team__shortname")
        if len(teams) < 2:
            continue

        raw_home = teams[0].get_text(strip=True)
        raw_away = teams[1].get_text(strip=True)

        # Parse home side => must end in "Bundesliga" / "2. Bundesliga" / "3. Liga"
        home_match = league_pattern.match(raw_home)
        if not home_match:
            # If we can't parse e.g. 'AalenOberliga...' => skip
            continue

        home_name = home_match.group(1).strip()     # e.g. "Bielefeld"
        home_league = home_match.group(2).strip()   # e.g. "3. Liga"

        # We only keep the row if home_league is in ALLOWED_LEAGUES
        if home_league not in ALLOWED_LEAGUES:
            continue

        # Parse away side similarly, but we do NOT require them to be in any particular league
        away_match = league_pattern.match(raw_away)
        if away_match:
            # If it matches, use just the team name (without the league)
            away_name = away_match.group(1).strip()
        else:
            # If away doesn't match pattern, keep it as-is
            away_name = raw_away

        # scoreboard time or "TBD"
        match_time = None
        holders = row.find_all("div", class_="kick__v100-scoreBoard__dateHolder")
        for h in holders:
            txt = h.get_text(strip=True)
            if time_pattern.match(txt):
                match_time = txt
                break
        if not match_time:
            match_time = "TBD"

        # Check if match is older than 30 days
        if match_time == "TBD":
            dt_check_str = f"{date_str_fixed} 00:00"
        else:
            dt_check_str = f"{date_str_fixed} {match_time}"
        try:
            match_dt_unshifted = datetime.strptime(dt_check_str, "%d.%m.%Y %H:%M")
        except ValueError:
            # If parse fails, skip
            continue

        if match_dt_unshifted < ONE_MONTH_AGO:
            # skip only this match
            continue

        # Deduplicate
        match_key = (date_str_fixed, match_time, home_name, away_name)
        if match_key in seen_matches:
            continue
        seen_matches.add(match_key)

        row_data.append({
            "league": COMPETITION_NAME,
            "date_str_raw": date_str_fixed,
            "time_raw": match_time,
            "home": home_name,  # e.g. "Bielefeld"
            "away": away_name   # e.g. "Leverkusen"
        })

    if not row_data:
        print(f"[INFO] No valid matches for {COMPETITION_NAME} MD {matchday}.")
        continue

    # 3) Build final records
    for info in row_data:
        league  = info["league"]
        dstr    = info["date_str_raw"]
        tstr    = info["time_raw"]
        h       = info["home"]
        a       = info["away"]

        if tstr == "TBD":
            try:
                date_obj = datetime.strptime(dstr + " 00:00", "%d.%m.%Y %H:%M")
                day_display  = date_obj.strftime("%A")
                date_display = date_obj.strftime("%d %B")
                match_datetime = date_obj
            except ValueError:
                day_display  = "Unknown"
                date_display = dstr
                match_datetime = datetime.max
            final_time = "TBD"
        else:
            dt_str = f"{dstr} {tstr}"
            try:
                match_dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
            except ValueError:
                match_dt = datetime.max

            # +1 hour
            match_dt_plus_one = match_dt + timedelta(hours=1)
            day_display  = match_dt_plus_one.strftime("%A")
            date_display = match_dt_plus_one.strftime("%d %B")
            final_time   = match_dt_plus_one.strftime("%H:%M")
            match_datetime = match_dt_plus_one

        match_info = {
            "league": league,
            "date_str": date_display,
            "time_str": final_time,
            "day_str": day_display,
            "home_team": h,      # e.g. "Bielefeld"
            "away_team": a,      # e.g. "Leverkusen"
            "match_datetime": match_datetime
        }
        all_matches.append(match_info)

    print(f"[INFO] Collected {len(row_data)} matches for {COMPETITION_NAME} MD {matchday}.")

#########################
# 4) Sort + Write
#########################
all_matches.sort(key=lambda x: x["match_datetime"])

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

print(f"\nAll done! {len(all_matches)} total DFB-Pokal matches saved to: {file_path}")
