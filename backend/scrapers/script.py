import os
import subprocess
from datetime import datetime
import re
from synonyms import TEAM_SYNONYMS 
import os
from synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums

# Year assumption
YEAR = 2025

# Paths to the source files
files_to_combine = [
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\dfb_pokal_games.txt",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\bundes_1_2_games.txt",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\liga3_games.txt",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\uefa_games.txt",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\data\man.txt",
]

excluded_file = r"C:\Users\Eyalp\Desktop\Bundes\backend\data\man.txt"

# Paths to scripts that fetch data
scripts_to_run = [
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\bundes.py",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\champions.py",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\liga.py",
    r"C:\Users\Eyalp\Desktop\Bundes\backend\scrapers\pokal.py",
]

# Output file
output_path = r"C:\Users\Eyalp\Desktop\Bundes\backend\data\allgames.txt"

# Regex to detect times like "18:30"
time_pattern = re.compile(r"^\d{1,2}:\d{2}$")


def normalize_team_name(team_raw: str) -> str:
    """
    1) If the team string has '/', we do NOT unify it via synonyms (just return as-is).
    2) Else, we lowercase, strip, and check if it’s in TEAM_SYNONYMS. If so, unify it.
    """
    if "/" in team_raw:
        return team_raw.strip()

    lower_team = team_raw.lower().strip()
    return TEAM_SYNONYMS.get(lower_team, lower_team)


# Create a lookup dictionary for train stations
def create_station_lookup():
    station_lookup = {}
    
    # Process all stadium lists
    for team_data in bundesliga_1_stadiums + bundesliga_2_stadiums + third_liga_stadiums:
        team_name = team_data["team"].lower()
        station_name = team_data["hbf"]["name"]
        station_lookup[team_name] = station_name
    
    return station_lookup

# Create the lookup once
TEAM_TO_STATION = create_station_lookup()

def get_team_station(team_name):
    """Get the train station for a team, or None if not found"""
    if team_name.lower() == "tbd":
        return "Unknown"
    
    # Try direct lookup in our dictionary
    return TEAM_TO_STATION.get(team_name.lower(), None)

def parse_line_to_record(line: str):
    """
    Given a line like:
      "bundesliga, 28 March, 20:30, Friday, Leverkusen, Bochum"
    Or with explicit location:
      "Champions League, 31 May, 21:00, Saturday, TBD, TBD, München hbf"
    parse out each field and return a dictionary with a parsed datetime object for sorting.
    """
    line = line.strip()
    if not line:
        return None

    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 6:
        return None  # malformed line

    league = parts[0]
    date_str = parts[1]
    time_str = parts[2]
    day_str = parts[3]
    home_team_raw = parts[4]
    away_team_raw = parts[5]
    
    # Handle optional location field (part 6)
    location = parts[6] if len(parts) > 6 and parts[6].strip() else None

    # Standardize teams
    home_team = normalize_team_name(home_team_raw)
    away_team = normalize_team_name(away_team_raw)

    # Look up the home team's station if location not already provided
    if not location:
        location = get_team_station(home_team)

    # Handle time
    pass_time = time_str if time_pattern.match(time_str) else "00:00"

    # Format date for sorting
    dt_str = f"{date_str} {YEAR} {pass_time}"
    try:
        match_dt = datetime.strptime(dt_str, "%d %B %Y %H:%M")
    except ValueError:
        match_dt = datetime.max

    return {
        "league": league,
        "date_str": date_str,
        "time_str": time_str,
        "day_str": day_str,
        "home_team": home_team,
        "away_team": away_team,
        "match_dt": match_dt,
        "location": location
    }


def record_to_line(record: dict) -> str:
    """Convert record back to a single CSV line."""
    base_line = (
        f"{record['league']}, {record['date_str']}, {record['time_str']}, "
        f"{record['day_str']}, {record['home_team']}, {record['away_team']}"
    )
    
    # Add location if present
    if 'location' in record and record['location']:
        return f"{base_line}, {record['location']}"
    
    return base_line


#########################
# 1) Run All Scripts First
#########################
print("Running scripts to fetch the latest data...\n")

for script_path in scripts_to_run:
    print(f"Executing: {script_path}")
    try:
        subprocess.run(["python", script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed running {script_path}: {e}")

print("\nAll scripts executed. Now merging results...\n")

#########################
# 2) Merge and Sort Data
#########################

all_records = []

# Read each file
for file_path in files_to_combine:
    print(f"Reading {file_path} ...")
    if not os.path.exists(file_path):
        print(f"[WARNING] File {file_path} not found, skipping.")
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        continue

    # Skip header
    for line in lines[1:]:
        rec = parse_line_to_record(line)
        if rec is not None:
            all_records.append(rec)

# Sort by match date
all_records.sort(key=lambda r: r["match_dt"])

# Write to "allgames.txt"
with open(output_path, "w", encoding="utf-8") as out:
    out.write("League, Date, Time, Day, Home Team, Away Team, Location\n")
    for r in all_records:
        out.write(record_to_line(r) + "\n")

print(f"\n✅ Done! Merged and standardized records written to {output_path}")

# Delete the original smaller files
for file_path in files_to_combine:
    if file_path == excluded_file:
        print(f"Skipped (excluded file): {file_path}")
        continue
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        else:
            print(f"Skipped (not found): {file_path}")
    except Exception as e:
        print(f"[ERROR] Could not delete {file_path}: {e}")

def fix_dates(file_path):
    """Add appropriate years to dates and capitalize team names in the games file"""
    # Get today's date
    today = datetime.now()
    current_year = today.year
    next_year = current_year + 1
    
    # Create a temp file for writing
    temp_file = file_path + ".temp"
    
    # Read header and data from original file
    with open(file_path, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    
    # Process the file
    updated_lines = []
    header_processed = False
    teams_capitalized = 0
    
    for line in lines:
        if not header_processed and line.strip().startswith('League'):
            # Keep the header as is
            updated_lines.append(line)
            header_processed = True
            continue
            
        if ',' not in line:
            # Keep non-data lines as is
            updated_lines.append(line)
            continue
        
        # Split the line into all its parts
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 6:
            # Not enough parts, keep as is
            updated_lines.append(line)
            continue
        
        league = parts[0]
        date_str = parts[1]
        time_str = parts[2]
        day_str = parts[3]
        home_team = parts[4]
        away_team = parts[5]
        location = parts[6] if len(parts) > 6 else None
        
        # Fix date year
        try:
            # Parse the date (day and month)
            if date_str == "TBD":
                # Keep TBD dates as is
                updated_date = date_str
            else:
                date_parts = date_str.split()
                if len(date_parts) == 2:  # Format: "28 March"
                    day = int(date_parts[0])
                    month_str = date_parts[1]
                    
                    # Convert month name to month number
                    month_names = ["January", "February", "March", "April", "May", "June", 
                                   "July", "August", "September", "October", "November", "December"]
                    month = month_names.index(month_str) + 1
                    
                    # Create date with current year to check if it's past
                    date_with_current_year = datetime(current_year, month, day)
                    
                    # Determine which year to use
                    if date_with_current_year < today:
                        # Date has passed this year, use next year
                        year_to_use = next_year
                    else:
                        # Date is still in the future this year
                        year_to_use = current_year
                    
                    # Create new date string with year
                    updated_date = f"{day} {month_str} {year_to_use}"
                else:
                    # Unexpected format, keep as is
                    updated_date = date_str
        except (ValueError, IndexError):
            # Error in parsing, keep original
            updated_date = date_str
            
        # Capitalize first letter of team names if needed
        if home_team and len(home_team) > 0 and home_team[0].islower():
            home_team = home_team[0].upper() + home_team[1:]
            teams_capitalized += 1
            
        if away_team and len(away_team) > 0 and away_team[0].islower():
            away_team = away_team[0].upper() + away_team[1:]
            teams_capitalized += 1
        
        # Reconstruct the line
        updated_line = f"{league}, {updated_date}, {time_str}, {day_str}, {home_team}, {away_team}"
        if location:
            updated_line += f", {location}"
        updated_line += "\n"
        
        updated_lines.append(updated_line)
    
    # Write updated content to temp file
    with open(temp_file, 'w', encoding='utf-8') as outfile:
        outfile.writelines(updated_lines)
    
    # Replace original with temp
    os.replace(temp_file, file_path)
    
    print(f"Updated {len(updated_lines)} lines in {file_path}")
    print(f"Capitalized {teams_capitalized} team names")
    
fix_dates(output_path)
print("Date fixing completed successfully!")
print("\n✅ All done! Unwanted files removed, only 'man.txt' remains.")
