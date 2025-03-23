import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# We'll assume all matches happen in the year 2025 (adjust if needed).
YEAR = 2025
START = 26
END = 35

# Path to the output file
file_path = r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\bundes_1_2_games.txt"

# Overwrite the file with a header row to begin
with open(file_path, "w", encoding="utf-8") as f:
    f.write("League, Date, Time, Day, Home Team, Away Team\n")

# We will gather all the match data in a list, then sort by date at the end
all_matches = []

# Define the leagues to scrape
leagues = ["bundesliga", "2bundesliga"]

# Range of matchdays
for league in leagues:
    for matchday in range(START, END):
        url = f"https://www.bundesliga.com/en/{league}/matchday/2024-2025/{matchday}"
        print(f"\nFetching {league}, matchday {matchday}: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Could not load page for {league} matchday {matchday}, skipping.")
            continue

        soup = BeautifulSoup(response.content, "html.parser")
        match_sections = soup.find_all("div", class_="matchRow elevation-t-card ng-star-inserted")

        if not match_sections:
            print(f"No matches found for {league} matchday {matchday}.")
            continue

        # ---- 1) Check if the first match of this matchday is in the past ----
        first_match = match_sections[0]
        date_header = first_match.find_previous("match-date-header", class_="ng-star-inserted")
        if not date_header:
            print(f"No date header for {league} matchday {matchday}, skipping.")
            continue

        # Extract date and time for the first match
        day_span = date_header.find("span", class_="day ng-star-inserted")
        time_span = date_header.find("span", class_="time ng-star-inserted")

        day_text = "Unknown"
        date_part = "Unknown"
        time_text = "00:00"  # fallback

        if day_span:
            bold = day_span.find("span", class_="bold")
            if bold:
                # e.g. <span class="bold">Friday</span> 14 March
                day_text = bold.get_text(strip=True)
                full_day_str = day_span.get_text(strip=True)
                # e.g. "Friday 14 March" => remove "Friday" => "14 March"
                date_part = full_day_str.replace(day_text, "", 1).strip()
            else:
                # fallback if there's no nested <span>
                combined = day_span.get_text(strip=True)
                parts = combined.split(maxsplit=1)
                if len(parts) == 2:
                    day_text, date_part = parts[0], parts[1]
                else:
                    day_text = combined

        if time_span:
            time_text = time_span.get_text(strip=True)

        # Parse datetime for the first match
        first_match_dt_str = f"{date_part} {YEAR} {time_text}"
        try:
            first_match_dt = datetime.strptime(first_match_dt_str, "%d %B %Y %H:%M")
            # If the first match is in the past, skip this matchday
            if first_match_dt < datetime.now():
                print(f"First kickoff for {league} matchday {matchday} ({first_match_dt}) is in the past, skipping.")
                continue
        except ValueError:
            print(f"Could not parse date/time for {league} matchday {matchday}, skipping.")
            continue

        # ---- 2) Gather all matches for this (future) matchday in a temporary list ----
        daily_matches = []

        for match in match_sections:
            # Find the date header for each match (some matchdays can span multiple days)
            dh = match.find_previous("match-date-header", class_="ng-star-inserted")
            original_day_text = "Unknown"
            original_date_part = "Unknown"
            original_time_text = "Time not found"

            if dh:
                d_span = dh.find("span", class_="day ng-star-inserted")
                t_span = dh.find("span", class_="time ng-star-inserted")

                if d_span:
                    b_span = d_span.find("span", class_="bold")
                    if b_span:
                        original_day_text = b_span.get_text(strip=True)
                        all_text = d_span.get_text(strip=True)
                        # e.g. "Friday 14 March"
                        original_date_part = all_text.replace(original_day_text, "", 1).strip()
                    else:
                        combined = d_span.get_text(strip=True)
                        parts = combined.split(maxsplit=1)
                        if len(parts) == 2:
                            original_day_text, original_date_part = parts[0], parts[1]
                        else:
                            original_day_text = combined

                if t_span:
                    original_time_text = t_span.get_text(strip=True)

            # Extract home/away teams
            teams = match.find_all("div", class_="name d-none d-lg-none d-xl-none d-md-block")
            if len(teams) >= 2:
                home_team = teams[0].get_text(strip=True)
                away_team = teams[1].get_text(strip=True)
            else:
                home_team = "Home not found"
                away_team = "Away not found"

            # --- 2a) Parse the match date/time, then add 1 hour ---
            match_dt = None
            dt_str = f"{original_date_part} {YEAR} {original_time_text}"
            try:
                match_dt = datetime.strptime(dt_str, "%d %B %Y %H:%M")
                # Add 1 hour to the parsed datetime
                match_dt += timedelta(hours=1)
                new_date_part = match_dt.strftime("%d %B")  # e.g. "15 March"
                new_time_text = match_dt.strftime("%H:%M")  # e.g. "22:30"
                new_day_text  = match_dt.strftime("%A")     # e.g. "Friday"
            except ValueError:
                # If parse failed, keep the original
                match_dt = datetime.max  # so it sorts last
                new_date_part = original_date_part
                new_time_text = original_time_text
                new_day_text  = original_day_text

            # Store everything in daily_matches
            match_info = {
                "league": league,
                "date_str": new_date_part,
                "time_str": new_time_text,
                "day_str":  new_day_text,
                "home_team": home_team,
                "away_team": away_team,
                "match_datetime": match_dt
            }
            daily_matches.append(match_info)

        print(f"Collected future matches for {league} matchday {matchday}.")

        # ---- 2b) If every match has the same time, label it "TBD" ----
        if daily_matches:
            # Gather distinct times from final "time_str"
            distinct_times = {m["time_str"] for m in daily_matches}
            if len(distinct_times) == 1:
                # All matches share the same time => set them to "TBD"
                only_time = next(iter(distinct_times))  # just for reference
                # If the time was "Time not found" or something, we still do "TBD"
                for m in daily_matches:
                    m["time_str"] = "TBD"

            # Add them to the global list
            all_matches.extend(daily_matches)

# ---- 3) Sort all matches by date/time (those that failed to parse go last) ----
all_matches.sort(key=lambda m: m["match_datetime"])

# ---- 4) Write sorted data to file ----
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

print(f"\nAll matchdays processed and sorted. See final file at: {file_path}")
