import requests
from bs4 import BeautifulSoup
import re

url = "https://www.kicker.de/dfb-pokal/spieltag/2025-26/1"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/110.0.0.0 Safari/537.36"
    )
}

response = requests.get(url, headers=headers)
if response.status_code != 200:
    raise Exception(f"Could not load page (status {response.status_code}).")

soup = BeautifulSoup(response.text, "html.parser")

# Each team is often shown in a div with class "kick__v100-gameCell__team__shortname"
team_divs = soup.find_all("div", class_=re.compile("kick__v100-gameCell__team__shortname"))

teams = set()  # to avoid duplicates
for div in team_divs:
    name = div.get_text(strip=True)
    if name:
        teams.add(name)

# Convert to a sorted list
unique_teams = sorted(teams)
print("\nFound Teams:")
for t in unique_teams:
    print(t)
