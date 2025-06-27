import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar

# Season logic: July-June spans two years
# If month >= July, use current year; if month < July, use next year
CURRENT_YEAR = 2025
START = 1
END = 5

def get_season_year(month_name):
    """Return the correct year based on season logic (July-June)"""
    month_num = datetime.strptime(month_name, "%B").month
    if month_num >= 7:  # July to December
        return CURRENT_YEAR
    else:  # January to June
        return CURRENT_YEAR + 1

def get_middle_date(start_date_str, end_date_str):
    """Get the middle date between two date strings, handling month boundaries"""
    try:
        start_parts = start_date_str.strip().split()
        end_parts = end_date_str.strip().split()
        
        if len(start_parts) >= 2 and len(end_parts) >= 2:
            start_day = int(start_parts[0])
            start_month = start_parts[1]
            end_day = int(end_parts[0])
            end_month = end_parts[1]
            
            start_year = get_season_year(start_month)
            end_year = get_season_year(end_month)
            
            start_dt = datetime(start_year, datetime.strptime(start_month, "%B").month, start_day)
            end_dt = datetime(end_year, datetime.strptime(end_month, "%B").month, end_day)
            
            # Calculate middle date
            diff = end_dt - start_dt
            middle_dt = start_dt + (diff // 2)
            
            return middle_dt.strftime("%d %B")
        else:
            return start_date_str  # fallback to first date
    except (ValueError, IndexError):
        return start_date_str  # fallback to first date

def parse_date_info(date_header):
    """Parse date information from various formats"""
    day_text = "Unknown"
    date_part = "Unknown"
    
    if not date_header:
        return day_text, date_part
    
    # Check for the first format: <span class="day"><span class="bold">Friday</span> 22 August</span>
    day_span = date_header.find("span", class_="day ng-star-inserted")
    if day_span:
        bold = day_span.find("span", class_="bold")
        if bold:
            # Format: "Friday 22 August"
            day_text = bold.get_text(strip=True)
            full_day_str = day_span.get_text(strip=True)
            date_part = full_day_str.replace(day_text, "", 1).strip()
        else:
            # Fallback if no nested span
            combined = day_span.get_text(strip=True)
            parts = combined.split(maxsplit=1)
            if len(parts) == 2:
                day_text, date_part = parts[0], parts[1]
            else:
                day_text = combined
        return day_text, date_part
    
    # Check for the second format: <div>22 August - 24 August</div>
    date_div = date_header.find("div", class_="ng-star-inserted")
    if date_div:
        date_range = date_div.get_text(strip=True)
        if " - " in date_range:
            # Format: "22 August - 24 August", take the middle date
            parts = date_range.split(" - ")
            if len(parts) == 2:
                start_date = parts[0].strip()
                end_date = parts[1].strip()
                middle_date = get_middle_date(start_date, end_date)
                date_part = middle_date
                
                # Calculate the day of week dynamically for the middle date
                try:
                    date_parts = middle_date.split()
                    if len(date_parts) >= 2:
                        day_num = int(date_parts[0])
                        month_name = date_parts[1]
                        year = get_season_year(month_name)
                        
                        temp_date = datetime(year, datetime.strptime(month_name, "%B").month, day_num)
                        day_text = temp_date.strftime("%A")  # Get day name (e.g., "Friday")
                except (ValueError, IndexError):
                    day_text = "Unknown"
            else:
                # Fallback to first date if split fails
                first_date = date_range.split(" - ")[0].strip()
                date_part = first_date
                try:
                    parts = first_date.split()
                    if len(parts) >= 2:
                        day_num = int(parts[0])
                        month_name = parts[1]
                        year = get_season_year(month_name)
                        
                        temp_date = datetime(year, datetime.strptime(month_name, "%B").month, day_num)
                        day_text = temp_date.strftime("%A")
                except (ValueError, IndexError):
                    day_text = "Unknown"
        else:
            # Single date in div format
            date_part = date_range
            try:
                parts = date_range.split()
                if len(parts) >= 2:
                    day_num = int(parts[0])
                    month_name = parts[1]
                    year = get_season_year(month_name)
                    
                    temp_date = datetime(year, datetime.strptime(month_name, "%B").month, day_num)
                    day_text = temp_date.strftime("%A")
            except (ValueError, IndexError):
                day_text = "Unknown"
    
    return day_text, date_part

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
        url = f"https://www.bundesliga.com/en/{league}/matchday/2025-2026/{matchday}"
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

        # Extract date and time for the first match using new parsing logic
        day_text, date_part = parse_date_info(date_header)
        
        time_span = date_header.find("span", class_="time ng-star-inserted")
        time_text = "00:00"  # fallback
        if time_span:
            time_text = time_span.get_text(strip=True)

        # Parse datetime for the first match with season year logic
        try:
            parts = date_part.split()
            if len(parts) >= 2:
                day_num = int(parts[0])
                month_name = parts[1]
                year = get_season_year(month_name)
                
                first_match_dt_str = f"{day_num} {month_name} {year} {time_text}"
                first_match_dt = datetime.strptime(first_match_dt_str, "%d %B %Y %H:%M")
                
                # If the first match is in the past, skip this matchday
                if first_match_dt < datetime.now():
                    print(f"First kickoff for {league} matchday {matchday} ({first_match_dt}) is in the past, skipping.")
                    continue
            else:
                raise ValueError("Could not parse date parts")
        except (ValueError, IndexError):
            print(f"Could not parse date/time for {league} matchday {matchday}, skipping.")
            continue

        # ---- 2) Gather all matches for this (future) matchday in a temporary list ----
        daily_matches = []

        for match in match_sections:
            # Find the date header for each match (some matchdays can span multiple days)
            dh = match.find_previous("match-date-header", class_="ng-star-inserted")
            original_day_text, original_date_part = parse_date_info(dh)
            
            original_time_text = "TBD"  # Default to TBD instead of "Time not found"
            if dh:
                t_span = dh.find("span", class_="time ng-star-inserted")
                if t_span:
                    time_value = t_span.get_text(strip=True)
                    # Convert "Time not found" to "TBD"
                    original_time_text = "TBD" if time_value == "Time not found" else time_value

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
            try:
                parts = original_date_part.split()
                if len(parts) >= 2:
                    day_num = int(parts[0])
                    month_name = parts[1]
                    year = get_season_year(month_name)
                    
                    # Only add 1 hour if we have a valid time (not TBD)
                    if original_time_text != "TBD":
                        dt_str = f"{day_num} {month_name} {year} {original_time_text}"
                        match_dt = datetime.strptime(dt_str, "%d %B %Y %H:%M")
                        # Add 1 hour to the parsed datetime
                        match_dt += timedelta(hours=1)
                        new_date_part = match_dt.strftime("%d %B")  # e.g. "15 March"
                        new_time_text = match_dt.strftime("%H:%M")  # e.g. "22:30"
                        new_day_text  = match_dt.strftime("%A")     # e.g. "Friday"
                    else:
                        # For TBD times, use original date without adding hour
                        match_dt = datetime(year, datetime.strptime(month_name, "%B").month, day_num)
                        new_date_part = original_date_part
                        new_time_text = "TBD"
                        new_day_text = original_day_text
                else:
                    raise ValueError("Could not parse date parts")
            except (ValueError, IndexError):
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