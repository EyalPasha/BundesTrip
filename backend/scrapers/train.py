import time
import random
import pandas as pd
import itertools
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums

# Set up Selenium for Microsoft Edge
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent bot detection
options.add_argument("--headless")  # Set False to debug UI
options.add_argument("--disable-gpu")
options.add_argument("--use-gl=swiftshader")  # Forces software rendering to avoid GPU problems
options.add_argument("--disable-software-rasterizer")  # Prevents GPU rendering issues
options.add_argument("--disable-background-networking")  # Stops background tasks
options.add_argument("--disable-background-timer-throttling")
options.add_argument("--disable-backgrounding-occluded-windows")
options.add_argument("--disable-breakpad")
options.add_argument("--disable-client-side-phishing-detection")
options.add_argument("--disable-crash-reporter")
options.add_argument("--disable-extensions")
options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
options.add_argument("--disable-sync")
options.add_argument("--metrics-recording-only")
options.add_argument("--mute-audio")
options.add_argument("--no-first-run")
options.add_argument("--safebrowsing-disable-auto-update")
options.add_argument("--enable-automation") 
options.add_argument("--window-size=1920x1080")
options.add_argument("--lang=he") 
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.77",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.139 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.130 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.85 Safari/537.36 Edg/121.0.2277.53",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6255.0 Safari/537.36"
]

service = Service(EdgeChromiumDriverManager().install())
driver = webdriver.Edge(service=service, options=options)

def refresh_user_agent():
    """Randomly changes the user agent during execution to reduce detection risk."""
    new_agent = random.choice(user_agents)
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": new_agent})
    print(f"🔄 Switched User-Agent to: {new_agent}")


def human_like_delay(short=True):
    """Mimic human-like delays with optional short or long wait times."""
    if short:
        time.sleep(random.uniform(1.5, 3))  # Short delay for normal requests
    else:
        time.sleep(random.uniform(10, 20))  # Longer delay after saving or restart


def convert_time_format(time_str):
    """Convert extracted time format to English (e.g., '5 שע׳ 35 דק׳' → '5h 35m')"""
    hebrew_to_english = {
        "ש’": "h", "שע’": "h", "שעה": "h", "שעות": "h",
        "דק’": "m", "דק׳": "m", "דקות": "m", "דקה": "m",
        " min": "m", " hr": "h", "שע׳": "h"
    }
    for heb, eng in hebrew_to_english.items():
        time_str = time_str.replace(heb, eng)
    time_str = time_str.strip()
    time_str = re.sub(r"(\d+)h\s*(\d*)", r"\1h \2", time_str)
    time_str = re.sub(r"\s*m", "m", time_str)  # Remove unnecessary spaces before 'm'
    return time_str


def extract_fastest_time():
    """Extract the fastest travel time, prioritizing jGDjJb.MBeuO.RES9jf."""
    def time_to_minutes(time_str):
        hours, minutes = 0, 0
        match = re.match(r'(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?', time_str.strip())
        if match:
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
        return hours * 60 + minutes

    time_elements = []

    # Priority element
    try:
        element = driver.find_element(By.CLASS_NAME, "jGDjJb.MBeuO.RES9jf")
        time_elements.append(element.text)
    except:
        pass

    # If priority element is not found, check alternatives
    if not time_elements:
        alternative_classes = ["tdu-time-delta"]
        for cls in alternative_classes:
            try:
                elements = driver.find_elements(By.CLASS_NAME, cls)
                time_elements.extend([el.text for el in elements])
            except:
                continue

    if not time_elements:
        return "Not Found"

    converted_times = [convert_time_format(t) for t in time_elements]
    fastest_time = min(converted_times, key=lambda t: time_to_minutes(t))
    return fastest_time


def get_fastest_train_time(home_city, away_city, retries=3):
    """Scrapes Google for the fastest train time between two cities."""
    attempt = 0
    while attempt < retries:
        try:
            search_query = f"{home_city} to {away_city} trains march 22"
            google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            driver.get(google_url)
            human_like_delay()
            return extract_fastest_time()
        except Exception as e:
            print(f"Error fetching {home_city} to {away_city}: {e}, retrying...")
            time.sleep(random.uniform(5, 10))  # Wait a bit longer before retrying
            attempt += 1
    return "Not Found"


# ----------------------------
#   NEW FUNCTION FOR SAME CITY
# ----------------------------
def add_same_city_time(city, csv_path):
    """
    Adds a same-city travel time record (0h 0m) to the CSV.
    """
    data = {"From": city, "To": city, "Fastest Train Time": "0h 0m"}
    df_data = pd.DataFrame([data])

    # Append to existing CSV (create if doesn't exist), with or without header
    df_data.to_csv(csv_path, mode='a', header=not os.path.exists(csv_path), index=False)
    print(f"Added same-city pair: {city} to {city} with 0h 0m.")


csv_file = r"C:\Users\Eyalp\Desktop\Bundes\backend\data\fastest_train_times.csv"
if os.path.exists(csv_file):
    try:
        df_existing = pd.read_csv(csv_file)
        if {"From", "To"}.issubset(df_existing.columns):
            existing_pairs = set(zip(df_existing["From"], df_existing["To"]))
            existing_pairs.update(set(zip(df_existing["To"], df_existing["From"])))
        else:
            print("CSV exists but lacks proper columns. Starting fresh.")
            df_existing = pd.DataFrame(columns=["From", "To", "Fastest Train Time"])
            existing_pairs = set()
    except pd.errors.EmptyDataError:
        print("CSV file is empty. Starting fresh.")
        df_existing = pd.DataFrame(columns=["From", "To", "Fastest Train Time"])
        existing_pairs = set()
else:
    df_existing = pd.DataFrame(columns=["From", "To", "Fastest Train Time"])
    existing_pairs = set()

# Combine all Bundesliga 1 and 2 teams with their respective Hauptbahnhof locations
all_teams = bundesliga_1_stadiums + bundesliga_2_stadiums + third_liga_stadiums

# Extract unique city names from Hbf entries
city_hbf_mapping = {team["hbf"]["name"]: team["hbf"]["name"] for team in all_teams}

# If you want pairs (home != away), use combinations:
#city_pairs = list(itertools.combinations(city_hbf_mapping.keys(), 2))

# If you also want to include (home == away) calls, use product:
city_pairs = list(itertools.product(city_hbf_mapping.keys(), repeat=2))

train_times = []
BATCH_SIZE = 1
batch_entries = []

for idx, (home, away) in enumerate(city_pairs):
    # --------------------------------
    #    Same-city scenario
    # --------------------------------
    if home == away:
        # Instead of skipping, call the function to add same-city time:
        add_same_city_time(home, csv_file)
        # Mark it in existing_pairs if you like:
        existing_pairs.update([(home, away)])
        continue

    # --------------------------------
    #    Different city scenario
    # --------------------------------
    if (home, away) in existing_pairs or (away, home) in existing_pairs:
        print(f"Skipping {home} to {away}, already in CSV.")
        continue

    # Change user agent every 20 requests
    if idx % 20 == 0:
        refresh_user_agent()

    # Restart the driver every 100 queries to prevent session issues
    if idx % 100 == 0 and idx > 0:
        print("🔄 Restarting browser to prevent detection...")
        driver.quit()
        time.sleep(random.uniform(10, 20))  # Longer delay after restart
        driver = webdriver.Edge(service=service, options=options)

    print(f"Fetching train time from {home} to {away}...")
    human_like_delay()
    travel_time = get_fastest_train_time(home, away)
    print(f"✔️ {home} to {away}: {travel_time}")

    new_entries = [
        {"From": home, "To": away, "Fastest Train Time": travel_time},
        {"From": away, "To": home, "Fastest Train Time": travel_time}
    ]
    batch_entries.extend(new_entries)

    existing_pairs.update([(home, away), (away, home)])

    # Save after each batch
    if len(batch_entries) >= BATCH_SIZE or (idx + 1) == len(city_pairs):
        df_new = pd.DataFrame(batch_entries)
        df_new.to_csv(csv_file, mode='a', header=not os.path.exists(csv_file), index=False)
        batch_entries = []
        human_like_delay(short=False)  # Longer delay after saving

# Close the browser at the end
driver.quit()
print("✅ Train times fetching complete!")
