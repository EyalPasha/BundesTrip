import os
import subprocess
from datetime import datetime
import re
from synonyms import TEAM_SYNONYMS 

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


def parse_line_to_record(line: str):
    """
    Given a line like:
      "bundesliga, 28 March, 20:30, Friday, Leverkusen, Bochum"
    parse out each field and return a dictionary with a parsed datetime object for sorting.
    If 'TBD', parse time as "00:00" but keep 'TBD' to display later.
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

    # Standardize teams
    home_team = normalize_team_name(home_team_raw)
    away_team = normalize_team_name(away_team_raw)

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
        "match_dt": match_dt
    }


def record_to_line(record: dict) -> str:
    """Convert record back to a single CSV line."""
    return (
        f"{record['league']}, {record['date_str']}, {record['time_str']}, "
        f"{record['day_str']}, {record['home_team']}, {record['away_team']}"
    )


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
    out.write("League, Date, Time, Day, Home Team, Away Team\n")
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

print("\n✅ All done! Unwanted files removed, only 'man.txt' remains.")
