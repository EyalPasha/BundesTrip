import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re
from synonyms import TEAM_SYNONYMS
from synonyms import bundesliga_1_stadiums
import calendar

START_CL_EL = 1 # starts on 1, ends on 13 (for 13 need to write 14)
END_CL_EL = 14
START_CF = 1 # starts on 1, ends on 11 (for 11 need to write 12)
END_CF = 12


CURRENT_YEAR = 2025

def get_season_year(month_name):
    """Return the correct year based on season logic (July-June)"""
    month_num = datetime.strptime(month_name, "%B").month
    if month_num >= 7:  # July to December
        return CURRENT_YEAR
    else:  # January to June
        return CURRENT_YEAR + 1

file_path = r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\uefa_games.txt"
# Build a set of canonical German team names – all in lowercase
GERMAN_TEAMS = {entry["team"].lower() for entry in bundesliga_1_stadiums}

def strip_country_suffix(raw_team: str) -> str:
    """
    Removes country suffix (e.g. 'Deutschland', 'Spanien', 'Italien', etc.)
    from the team name if present.
    """
    pattern = r"(?: ?(Deutschland|Spanien|Italien|England|Frankreich))$"
    return re.sub(pattern, "", raw_team.strip(), flags=re.IGNORECASE).strip()

def is_explicitly_german(raw_team: str) -> bool:
    """
    If the original string ends with 'Deutschland',
    treat it as a German side, even if synonyms or slash logic fail.
    """
    return bool(re.search(r"(Deutschland)$", raw_team.strip(), flags=re.IGNORECASE))

def normalize_team_name(raw_name: str) -> str:
    """
    Convert raw name to lowercase, then apply synonyms. 
    If no match, return the lowercased name.
    """
    name_lower = raw_name.lower().strip()
    return TEAM_SYNONYMS.get(name_lower, name_lower)

def pick_german_team_if_slash(raw_home: str) -> str:
    """
    If raw_home has a slash (e.g. 'Barca/BVB'), check if exactly one side 
    is recognized as German. If so, return that side's canonical name; 
    otherwise, fallback to the first part.
    """
    no_extra_space = re.sub(r"\s*/\s*", "/", raw_home)
    parts = no_extra_space.split("/")
    if len(parts) == 1:
        return raw_home  # no slash

    recognized_parts = []
    for p in parts:
        if is_explicitly_german(p):
            # e.g. 'BayernDeutschland'
            stripped = strip_country_suffix(p)
            recognized_parts.append(normalize_team_name(stripped))
        else:
            p_fixed = strip_country_suffix(p)
            norm = normalize_team_name(p_fixed)
            if norm in GERMAN_TEAMS:
                recognized_parts.append(norm)

    if len(recognized_parts) == 1:
        return recognized_parts[0]
    else:
        # fallback to first portion
        fallback_part = parts[0].strip()
        fallback_fixed = strip_country_suffix(fallback_part)
        return normalize_team_name(fallback_fixed)

def fix_date_string(date_str: str) -> str:
    """
    If Kicker shows something like '08.04.', remove trailing '.' if present,
    then append the correct season year based on month.
    """
    date_str = date_str.strip()
    if date_str.endswith("."):
        date_str = date_str[:-1]
    
    # Only add year if no 4-digit year is present
    if not re.search(r"\b20\d{2}\b", date_str):
        # Parse the month to determine correct year
        try:
            # Parse date to get month (expecting format like "08.04")
            parts = date_str.split(".")
            if len(parts) >= 2:
                month_num = int(parts[1])
                month_name = calendar.month_name[month_num]
                correct_year = get_season_year(month_name)
                date_str += f".{correct_year}"
            else:
                # Fallback to default year if parsing fails
                date_str += f".{CURRENT_YEAR}"
        except (ValueError, IndexError):
            # Fallback to default year if parsing fails
            date_str += f".{CURRENT_YEAR}"
    
    return date_str

# We'll consider anything more than 7 days old as "too old".
SEVEN_DAYS_AGO = datetime.now() - timedelta(days=7)

#########################
# Competitions to scrape
#########################
competitions = [
    ("Champions League",         "champions-league",         START_CL_EL, END_CL_EL),  # 1..13
    ("Europa League",            "europa-league",            START_CL_EL, END_CL_EL),  # 1..13
    ("Europa Conference League", "europa-conference-league", START_CF, END_CF),  # 1..11
]

# Overwrite with a header row
with open(file_path, "w", encoding="utf-8") as f:
    f.write("League, Date, Time, Day, Home Team, Away Team\n")

all_matches = []

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

for league_name, kicker_slug, start_md, end_md in competitions:
    for matchday in range(start_md, end_md):
        url = f"https://www.kicker.de/{kicker_slug}/spieltag/2025-26/{matchday}"
        print(f"\n--- {league_name}, matchday {matchday} ---")
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
            print(f"[INFO] Request error: {e} — skipping {league_name} MD {matchday}.")
            continue

        if resp.status_code != 200:
            print(f"[INFO] Got status code {resp.status_code}, skipping {league_name} MD {matchday}.")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        game_rows = soup.find_all("div", class_=re.compile("kick__v100-gameList__gameRow"))
        if not game_rows:
            print(f"[INFO] No matches found for {league_name} MD {matchday}.")
            continue

        # ---------------------------------------------
        # 1) Check only the first match date/time.
        # If it's older than 7 days => skip entire page
        # ---------------------------------------------
        first_row = game_rows[0]
        first_header = first_row.find_previous("div", class_="kick__v100-gameList__header")
        if first_header:
            splitted = first_header.get_text(strip=True).split(",", 1)
            if len(splitted) == 2:
                # parse first match date
                date_str_no_year = splitted[1].strip()
                date_str_fixed = fix_date_string(date_str_no_year)
                # find scoreboard time or default to "13:00"
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
                    # If first_dt < 7 days ago => skip the entire page
                    if first_dt < SEVEN_DAYS_AGO:
                        print(f"[INFO] First match {first_dt} is >7d old. Skipping {league_name} MD {matchday}.")
                        continue
                except ValueError:
                    pass

        # We only reach here if first_dt wasn't more than 7 days old. 
        # So let's parse each match individually, skipping only those older than 7 days.

        row_data = []
        seen_matches = set()

        for row in game_rows:
            row_header = row.find_previous("div", class_="kick__v100-gameList__header")
            if not row_header:
                continue
            splitted = row_header.get_text(strip=True).split(",", 1)
            if len(splitted) != 2:
                continue

            raw_date_str = splitted[1].strip()
            fixed_date_str = fix_date_string(raw_date_str)

            teams = row.select("div.kick__v100-gameCell__team__shortname")
            if len(teams) < 2:
                continue

            raw_home = teams[0].get_text(strip=True)
            raw_away = teams[1].get_text(strip=True)

            # German-home logic
            if is_explicitly_german(raw_home):
                home_team = "fallback-german"
            else:
                raw_home_no_suffix = strip_country_suffix(raw_home)
                raw_away_no_suffix = strip_country_suffix(raw_away)
                possibly_german_home = pick_german_team_if_slash(raw_home_no_suffix)
                home_team = normalize_team_name(possibly_german_home)
                away_team = normalize_team_name(raw_away_no_suffix)

            if home_team == "fallback-german":
                stripped_home = strip_country_suffix(raw_home)
                final_home_norm = normalize_team_name(stripped_home)
                if final_home_norm in GERMAN_TEAMS:
                    home_team = final_home_norm
                else:
                    home_team = stripped_home.lower()
                away_team = strip_country_suffix(raw_away)
                away_team = normalize_team_name(away_team)
            else:
                # if we didn't do fallback, we still need to finalize away_team
                away_team = normalize_team_name(strip_country_suffix(raw_away))

            # Check if recognized as German
            if home_team not in GERMAN_TEAMS:
                # If original ended with 'Deutschland', we forcibly treat it as German
                if not is_explicitly_german(raw_home):
                    continue

            # scoreboard time or TBD
            match_time = None
            holders = row.find_all("div", class_="kick__v100-scoreBoard__dateHolder")
            for h in holders:
                maybe_time = h.get_text(strip=True)
                if time_pattern.match(maybe_time):
                    match_time = maybe_time
                    break

            if not match_time:
                match_time = "TBD"

            # Parse the match's unshifted date/time => used to skip if >7 days old
            if match_time == "TBD":
                dt_check_str = f"{fixed_date_str} 00:00"
            else:
                dt_check_str = f"{fixed_date_str} {match_time}"

            try:
                match_dt_unshifted = datetime.strptime(dt_check_str, "%d.%m.%Y %H:%M")
            except ValueError:
                # If parse fails, skip
                continue

            if match_dt_unshifted < SEVEN_DAYS_AGO:
                # skip only this match
                continue

            match_key = (fixed_date_str, match_time, home_team, away_team)
            if match_key in seen_matches:
                continue
            seen_matches.add(match_key)

            row_data.append({
                "league": league_name,
                "date_str_raw": fixed_date_str,
                "time_raw": match_time,
                "home": home_team,
                "away": away_team
            })

        if not row_data:
            print(f"[INFO] No valid (German-home) matches for {league_name} MD {matchday}.")
            continue

        # 3) Build final records (now we parse with +1 hour if scoreboard time known)
        for info in row_data:
            league = info["league"]
            block_date_str = info["date_str_raw"]
            match_time = info["time_raw"]
            home_team = info["home"]
            away_team = info["away"]

            if match_time == "TBD":
                try:
                    date_obj = datetime.strptime(block_date_str + " 00:00", "%d.%m.%Y %H:%M")
                    day_display = date_obj.strftime("%A")
                    date_display = date_obj.strftime("%d %B")
                    match_datetime = date_obj
                except ValueError:
                    day_display = "Unknown"
                    date_display = block_date_str
                    match_datetime = datetime.max
                final_time = "TBD"
            else:
                dt_str = f"{block_date_str} {match_time}"
                try:
                    match_dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
                except ValueError:
                    match_dt = datetime.max

                match_dt_plus_one = match_dt + timedelta(hours=1)
                date_display = match_dt_plus_one.strftime("%d %B")
                final_time = match_dt_plus_one.strftime("%H:%M")
                day_display = match_dt_plus_one.strftime("%A")
                match_datetime = match_dt_plus_one

            match_info = {
                "league": league,
                "date_str": date_display,
                "time_str": final_time,
                "day_str": day_display,
                "home_team": home_team,
                "away_team": away_team,
                "match_datetime": match_datetime
            }
            all_matches.append(match_info)

        print(f"[INFO] Collected {len(row_data)} matches for {league_name} MD {matchday}.")

# 4) Sort & write out
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

print(f"\nAll done! {len(all_matches)} total German-home UEFA matches written to: {file_path}")
