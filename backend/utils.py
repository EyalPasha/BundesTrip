import asyncio
import functools
import pandas as pd
from datetime import datetime, timedelta
from models import Game
from data.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums
from typing import Optional, List, Dict
import itertools
from config import TRAIN_TIMES_FILE, DEFAULT_CITIES
from common import is_request_cancelled, get_processed_start_date
import logging
logger = logging.getLogger("trip-planner")

# ────────────────────────────────
# 🛠️ Helper Functions
# ────────────────────────────────
@functools.lru_cache(maxsize=2048)
def parse_date_string(date_str):    
    # Parse date with year (e.g., "28 March 2025")
    return datetime.strptime(date_str, "%d %B %Y")


def make_trip_hashable(trip):
    """Convert a trip dictionary to a hashable structure (tuple) for caching"""
    if "Itinerary" not in trip and not isinstance(trip, list):
        return ()
        
    itinerary = trip.get("Itinerary", trip) if isinstance(trip, dict) else trip
    result = []
    
    for day in itinerary:
        if isinstance(day, dict):
            day_items = []
            for key, value in sorted(day.items()):
                if key == 'matches' and value:
                    # Convert matches to tuple of tuples
                    matches_tuple = tuple(
                        tuple((k, v) for k, v in sorted(m.items()) if isinstance(v, (str, int, bool, float)))
                        for m in value
                    )
                    day_items.append((key, matches_tuple))
                else:
                    # Only include hashable types
                    if isinstance(value, (str, int, bool, float)):
                        day_items.append((key, value))
            result.append(tuple(day_items))
    
    return tuple(result)

@functools.lru_cache(maxsize=16384)
def generate_trip_signature(trip_key):
    match_signature = []
    
    for day_tuple in trip_key:
        day_value = ""
        # Get day directly
        for k, v in day_tuple:
            if k == "day":
                day_value = v
                break
        
        # Process matches directly from the tuple
        for k, v in day_tuple:
            if k == "matches" and isinstance(v, tuple):
                for match_tuple in v:
                    match_value = ""
                    for mk, mv in match_tuple:
                        if mk == "match":
                            match_value = mv
                            break
                    if match_value:
                        match_signature.append((day_value, match_value))
    
    return tuple(sorted(match_signature))

def memoize_travel_time(func, maxsize=10000):
    from collections import OrderedDict
    cache = OrderedDict()
    
    @functools.wraps(func)
    def wrapper(train_times, from_loc, to_loc):
        key = (from_loc.lower(), to_loc.lower())
        if key in cache:
            value = cache.pop(key)
            cache[key] = value  # Move to end (most recently used)
            return value
            
        result = func(train_times, from_loc, to_loc)
        cache[key] = result
        
        # Limit cache size
        if len(cache) > maxsize:
            cache.popitem(last=False)  # Remove oldest item
            
        return result
    
    return wrapper

@memoize_travel_time
def get_travel_minutes_utils(train_times: Dict, from_loc: str, to_loc: str) -> Optional[int]:
    """Get travel time between locations, handling missing data and same-location"""
    # Return 0 for same location (case-insensitive comparison)
    if from_loc.lower() == to_loc.lower():
        return 0
    
    # Try direct lookup and reverse first (most common cases)
    minutes = train_times.get((from_loc, to_loc))
    if minutes is not None:
        return minutes
    
    minutes = train_times.get((to_loc, from_loc))
    if minutes is not None:
        return minutes
    
    # Cache lowercase versions for suffix checking
    from_loc_lower = from_loc.lower()
    to_loc_lower = to_loc.lower()
    
    # Special suffixes that preclude adding HBF
    special_suffixes = ["mitte", "bahnhof"]
    
    # Check if special suffixes exist
    from_has_special = any(suffix in from_loc_lower for suffix in special_suffixes)
    to_has_special = any(suffix in to_loc_lower for suffix in special_suffixes)
    
    # Generate variants efficiently
    variants = []
    
    # Add "hbf" variants only when appropriate
    if not from_has_special:
        variants.append((from_loc + " hbf", to_loc))
        if not to_has_special:
            variants.append((from_loc + " hbf", to_loc + " hbf"))
    
    if not to_has_special:
        variants.append((from_loc, to_loc + " hbf"))
    
    # Remove "hbf" if present (only compute cleaned versions when needed)
    if " hbf" in from_loc or " hbf" in to_loc:
        from_clean = from_loc.replace(" hbf", "")
        to_clean = to_loc.replace(" hbf", "")
        variants.append((from_clean, to_clean))
    
    # Try all variants and their reverse
    for variant in variants:
        minutes = train_times.get(variant)
        if minutes is not None:
            return minutes
        
        # Try reverse variant
        reverse = (variant[1], variant[0])
        minutes = train_times.get(reverse)
        if minutes is not None:
            return minutes
    
    return None

def convert_to_minutes(time_str: str) -> int:
    """Convert time string formats like '5h 30m', '4h', '45m' to minutes."""
    if not time_str:
        raise ValueError("Invalid time string: Input is empty or None.")
        
    time_str = time_str.strip()
    
    # Case 1: Both hours and minutes (e.g., "5 h 38m")
    if "h" in time_str and "m" in time_str:
        try:
            hours_part = time_str.split("h")[0].strip()
            minutes_part = time_str.split("h")[1].split("m")[0].strip()
            hours = int(hours_part) if hours_part else 0
            minutes = int(minutes_part) if minutes_part else 0
            return (hours * 60) + minutes
        except ValueError:
            raise ValueError(f"Invalid time format: '{time_str}'")
    
    # Case 2: Only hours (e.g., "4 h")
    elif "h" in time_str:
        try:
            hours_part = time_str.split("h")[0].strip()
            hours = int(hours_part) if hours_part else 0
            return hours * 60
        except ValueError:
            raise ValueError(f"Invalid hour format: '{time_str}'")
    
    # Case 3: Only minutes (e.g., "45m")
    elif "m" in time_str:
        try:
            minutes_part = time_str.split("m")[0].strip()
            minutes = int(minutes_part) if minutes_part else 0
            return minutes
        except ValueError:
            raise ValueError(f"Invalid minute format: '{time_str}'")
    
    # Case 4: Just a number (assume minutes)
    else:
        try:
            return int(time_str)
        except ValueError:
            raise ValueError(f"Invalid time string: '{time_str}'")

def load_train_times(file_path: str) -> dict:
    """Load train travel times between locations from CSV file."""
    df = pd.read_csv(file_path)
    train_times = {}
    for _, row in df.iterrows():
        travel_minutes = convert_to_minutes(row["Fastest Train Time"])
        train_times[(row["From"], row["To"])] = travel_minutes
        train_times[(row["To"], row["From"])] = travel_minutes
    return train_times

def add_missing_same_city_travel_times(train_times):
    """Add missing same-city travel times (0 minutes) to the train_times dictionary."""
    all_cities = set()
    
    # Collect all unique cities from the train_times keys
    for from_loc, to_loc in train_times.keys():
        all_cities.add(from_loc)
        all_cities.add(to_loc)
    
    # Add 0-minute travel times for all cities to themselves
    for city in all_cities:
        train_times[(city, city)] = 0
    
    return train_times

def load_games(file_path: str) -> tuple:
    """Load football games from CSV file, separating regular and TBD games."""
    df = pd.read_csv(file_path, encoding="utf-8", skipinitialspace=True)
    df.columns = df.columns.str.strip()

    games = []
    tbd_games = []

    for _, row in df.iterrows():
        try:
            date_str = row["Date"].strip()
            # Parse with year already included
            date_main = datetime.strptime(date_str, "%d %B %Y")
            
            # Check for explicit location, fall back to home team's location
            location = None
            if "Location" in df.columns:
                location_value = row["Location"]
                if pd.notna(location_value) and str(location_value).strip() not in ["", "TBD", "Unknown"]:
                    location = str(location_value).strip()
            
            # If no explicit location or invalid location, use home team's location
            if not location:
                if row["Home Team"].strip() == "TBD":
                    location = "Unknown"
                else:
                    location = map_team_to_hbf(row["Home Team"])
            
            game = Game(
                league=row["League"].strip(),
                date=date_main,
                time=row["Time"],
                home_team=row["Home Team"].strip(),
                away_team=row["Away Team"].strip(),
                hbf_location=location
            )
            
            if str(row["Time"]).lower() == "tbd":
                tbd_games.append(game)
            else:
                games.append(game)
                
        except Exception as e:
            logger.error(f"Error parsing row {row}: {e}")
            continue

    return games, tbd_games

train_times = load_train_times(TRAIN_TIMES_FILE)
train_times = add_missing_same_city_travel_times(train_times)

def map_team_to_hbf(team_name: str) -> str:
    """Map team name to nearest train station (Hauptbahnhof)."""
    all_teams = bundesliga_1_stadiums + bundesliga_2_stadiums + third_liga_stadiums
    for team in all_teams:
        if team["team"].lower() == team_name.lower():
            return team["hbf"]["name"]
    return "Unknown"

def identify_similar_trips(sorted_trips: List[Dict]) -> List[Dict]:
    """Group trips by the matches they include, ignoring travel routes."""
    trip_groups = []
    signature_to_group_index = {}
    
    for trip in sorted_trips:
        if "Itinerary" not in trip:
            continue
        
        match_count = sum(1 for day in trip["Itinerary"] if day.get("matches"))
        if match_count == 0:
            continue
        
        # Use cached signature generation
        trip_key = make_trip_hashable(trip)
        match_signature_tuple = generate_trip_signature(trip_key)
        
        group_index = signature_to_group_index.get(match_signature_tuple)
        
        if group_index is not None:
            trip_groups[group_index]["Variations"].append(trip)
        else:
            new_group = {"Base": trip, "Variations": [trip]}
            trip_groups.append(new_group)
            signature_to_group_index[match_signature_tuple] = len(trip_groups) - 1
    
    return trip_groups

def format_travel_time(minutes: int) -> str:
    """Convert minutes to 'Xh Ym' format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"

def parse_travel_time(time_str: str) -> int:
    """Parse time string in 'Xh Ym' format to minutes."""
    if time_str == "Unknown":
        return 0
        
    try:
        if "h" in time_str and "m" in time_str:
            parts = time_str.split("h ")
            hours = int(parts[0])
            minutes = int(parts[1].replace("m", ""))
            return (hours * 60) + minutes
        elif "h" in time_str:
            hours = int(time_str.replace("h", "").strip())
            return hours * 60
        elif "m" in time_str:
            minutes = int(time_str.replace("m", "").strip())
            return minutes
        else:
            return 0
    except:
        return 0

def calculate_total_travel_time(trip: Dict, train_times_param: Dict = None, start_location: str = None) -> int:
    """Calculate the total travel time for a trip based on actual travel segments."""
    global train_times
    train_times_to_use = train_times_param if train_times_param is not None else train_times

    total_minutes = 0

    # Handle both trip formats
    days = trip.get("Itinerary", trip) if isinstance(trip, dict) else trip

    if not isinstance(days, list):
        return 0

    # Track previous hotel to detect changes
    previous_hotel = None
    hotel_by_day = {}
    match_by_day = {}

    # First pass: collect hotel and match locations by day
    for day in days:
        if not isinstance(day, dict):
            continue

        day_str = day.get("day")
        if not day_str:
            continue

        # Store hotel location
        hotel = day.get("hotel")
        if hotel:
            hotel_by_day[day_str] = hotel

        # Store match location
        if day.get("matches"):
            for match in day.get("matches"):
                if match.get("location"):
                    match_by_day[day_str] = match.get("location")
                    break

    # Find initial location and first hotel for initial travel calculation
    initial_location = None
    first_hotel = None

    for day in days:
        if isinstance(day, dict) and day.get("location"):
            initial_location = day.get("location")
            break

    for day in sorted(hotel_by_day.keys(), key=lambda d: parse_date_string(d)):
            first_hotel = hotel_by_day[day]
            break

    if start_location and first_hotel:
        if start_location.lower() != first_hotel.lower():
            initial_travel_time = get_travel_minutes_utils(train_times_to_use, start_location, first_hotel) or 0
            total_minutes += initial_travel_time
    elif initial_location and first_hotel and initial_location.lower() != first_hotel.lower():
        initial_travel_time = get_travel_minutes_utils(train_times_to_use, initial_location, first_hotel) or 0
        total_minutes += initial_travel_time

    # Second pass: calculate travel time based on daily movements.
    # Use datetime conversion in sorting the days.
    sorted_days = sorted(
    [d for d in days if isinstance(d, dict) and d.get("day")],
    key=lambda x: parse_date_string(x.get("day"))
    )
    
    previous_hotel = None

    for day in sorted_days:
        day_str = day.get("day")
        current_hotel = day.get("hotel")
        match_location = match_by_day.get(day_str)

        if not current_hotel:
            continue

        if match_location and previous_hotel and current_hotel != previous_hotel:
            if match_location.lower() == previous_hotel.lower():
                travel_time = get_travel_minutes_utils(train_times_to_use, match_location, current_hotel) or 0
                total_minutes += travel_time
            elif match_location.lower() == current_hotel.lower():
                travel_time = get_travel_minutes_utils(train_times_to_use, previous_hotel, match_location) or 0
                total_minutes += travel_time
            else:
                to_match_time = get_travel_minutes_utils(train_times_to_use, previous_hotel, match_location) or 0
                to_new_hotel_time = get_travel_minutes_utils(train_times_to_use, match_location, current_hotel) or 0
                total_minutes += to_match_time + to_new_hotel_time
        else:
            if previous_hotel and current_hotel != previous_hotel:
                hotel_change_time = get_travel_minutes_utils(train_times_to_use, previous_hotel, current_hotel) or 0
                total_minutes += hotel_change_time

            if match_location and not (previous_hotel and current_hotel != previous_hotel):
                start_point = previous_hotel if previous_hotel else current_hotel

                if match_location.lower() != start_point.lower():
                    match_travel_time = get_travel_minutes_utils(train_times_to_use, start_point, match_location) or 0
                    total_minutes += match_travel_time

                if match_location.lower() != current_hotel.lower():
                    return_travel_time = get_travel_minutes_utils(train_times_to_use, match_location, current_hotel) or 0
                    total_minutes += return_travel_time

        previous_hotel = current_hotel

    return total_minutes

@functools.lru_cache(maxsize=8192)
def get_reachable_games_cached(location: str, date_str: str, games_tuple, max_travel_time: int, train_times_dict_id: int):
    """Cache reachable games from a location on a specific date"""
    games = list(games_tuple)  # Convert back to list
    current_date = datetime.strptime(date_str, "%Y-%m-%d")
    current_date_only = current_date.date()
    
    # Get the train_times dictionary from the global reference
    global train_times
    train_times_to_use = train_times  # Default
    
    todays_games = [game for game in games if hasattr(game, 'date') and game.date.date() == current_date_only]
    
    if not todays_games:
        return ()
    
    reachable = []
    
    for game in todays_games:
        if hasattr(game, 'hbf_location'):
            # Use helper function instead of direct lookup
            travel_time = get_travel_minutes_utils(train_times_to_use, location, game.hbf_location)
            if travel_time is not None and travel_time <= max_travel_time:
                reachable.append((
                    game,
                    location,
                    travel_time
                ))
    
    return tuple(reachable)  # Return immutable tuple for caching

def get_reachable_games(locations: list, games: list, train_times: dict, max_travel_time: int, current_date: datetime) -> list:
    """Find games reachable within max_travel_time from any of the provided locations."""
    if not locations or not games:
        return []
    
    date_str = current_date.strftime("%Y-%m-%d")
    games_tuple = tuple(games)  # Make immutable for caching
    train_times_dict_id = id(train_times)  # Use ID as reference
    
    unique_locations = set(locations)
    all_reachable = []
    
    for loc in unique_locations:
        # Use the cached function for each location
        cached_results = get_reachable_games_cached(loc, date_str, games_tuple, max_travel_time, train_times_dict_id)
        
        # Convert the immutable tuple results back to dictionaries
        for game, from_loc, travel_time in cached_results:
            all_reachable.append({
                "game": game,
                "from": from_loc,
                "travel_time": travel_time
            })
    
    return all_reachable

def is_efficient_route(new_trip: list, new_location: str, trip_locations: list) -> bool:
    """Check if adding this location creates an efficient route."""
    # Avoid backtracking (A → B → A pattern)
    if len(trip_locations) >= 2:
        last = trip_locations[-1]
        second_last = trip_locations[-2]
        if new_location == second_last and last != second_last:
            return False
    
    # Special case: First day of the trip - always allow staying in the starting location
    if len(trip_locations) == 1 and trip_locations[0] == new_location:
        return True
    
    # Avoid unnecessary detours when staying in a location
    if len(trip_locations) >= 1 and trip_locations[-1] == new_location:
        has_match_today = any(len(day.get("matches", [])) > 0 for day in new_trip[-1:])
        if not has_match_today:
            # Check if we're on the first day of the trip (special case)
            first_day = len(new_trip) <= 1
            if first_day:
                return True  # Allow staying in the same location on first day
            return False
    
    return True

def filter_pareto_optimal_trips(trips: list, train_times: dict = None) -> list:
    """
    Filter trips to create a Pareto frontier based on travel time and hotel changes.
    """
    if not trips:
        return []
        
    # Sort trips by total travel time (fastest first)
    sorted_trips = sorted(trips, key=lambda trip: calculate_total_travel_time(trip, train_times))
    
    # Always include the fastest option
    pareto_optimal = [sorted_trips[0]]
    
    # Get the hotel changes from the last element (hotel stats)
    min_hotel_changes_seen = next((item.get("hotel_changes", 0) 
                                  for item in sorted_trips[0] 
                                  if isinstance(item, dict) and "hotel_changes" in item), 0)
    
    # For each subsequent trip, only keep it if it has fewer hotel changes
    for trip in sorted_trips[1:]:
        current_changes = next((item.get("hotel_changes", 0) 
                              for item in trip 
                              if isinstance(item, dict) and "hotel_changes" in item), 0)
        
        # Only keep this trip if it has strictly fewer hotel changes
        if current_changes < min_hotel_changes_seen:
            pareto_optimal.append(trip)
            min_hotel_changes_seen = current_changes
            
            # If we've reached 0 hotel changes, we can stop (can't get better than that)
            if min_hotel_changes_seen == 0:
                break
    
    return pareto_optimal

def create_hotel_variation(
    base_trip: list,
    hotel_base: str,
    start_idx=0,
    preserve_first_day=True,
    train_times=None,
    max_travel_time=None
) -> list:
    """
    Create a trip variation using a specific hotel base, rebuilding travel segments to match.
    This updated version enforces that a hotel change cannot occur on a game day,
    and replaces the O(n log n) date-parse-and-sort pass with a single O(n) linear scan.
    """
    # --- 1) two-level shallow copy instead of deepcopy ---
    variation = []
    for day in base_trip:
        if isinstance(day, dict):
            new_day = day.copy()
            if "matches" in new_day and isinstance(new_day["matches"], list):
                new_day["matches"] = [m.copy() for m in new_day["matches"]]
            variation.append(new_day)
        else:
            variation.append(day)

    is_valid = True

    # Ensure first day has a hotel
    if variation and isinstance(variation[0], dict) and not variation[0].get("hotel"):
        variation[0]["hotel"] = variation[0].get("location", hotel_base)

    # --- 2) First pass: set hotel on each day ---
    for i, day in enumerate(variation):
        if i < start_idx or (i == 0 and preserve_first_day):
            continue

        # No hotel change on game days
        if day.get("matches"):
            day["hotel"] = variation[i-1].get("hotel", hotel_base) if i > 0 else hotel_base
            continue

        # Rest days: stay at hotel_base
        day["hotel"] = hotel_base

    # --- 3) Second pass: assign travel_from/travel_time on match days ---
    for i, day in enumerate(variation):
        if i == 0 or not day.get("matches"):
            continue

        prev_hotel = variation[i-1].get("hotel")
        match_loc = day.get("location")
        travel = train_times.get((prev_hotel, match_loc), float("inf"))
        if travel > max_travel_time:
            is_valid = False
            break

        # annotate each match
        for match in day["matches"]:
            match["travel_from"] = prev_hotel
            match["travel_time"] = format_travel_time(travel)

    if not is_valid:
        return None

    # --- 4) Optimized third pass: O(n) linear scan over variation ---
    prev_day = None
    for day in variation:
        # skip non-day entries
        if not isinstance(day, dict) or "day" not in day:
            continue

        if prev_day is not None:
            prev_hotel = prev_day.get("hotel")
            curr_hotel = day.get("hotel")
            if prev_hotel and curr_hotel and prev_hotel != curr_hotel:
                transition = get_travel_minutes_utils(train_times, prev_hotel, curr_hotel)
                if transition is None:
                    transition = float("inf")
                if transition > max_travel_time:
                    is_valid = False
                    break

        prev_day = day

    return variation if is_valid else None


def optimize_trip_variations(
    base_trip: list,
    train_times: dict,
    max_travel_time: int,
    start_location: str = None
) -> list:
    """
    Generate optimized variations of a trip with different hotel strategies,
    ensuring all travel segments are feasible.
    This version replaces the O(n log n) sort+parse in final validation
    with a single O(n) linear scan.
    """
    # 1) Always include the original
    variations = [base_trip[:]]

    # 2) Extract match info
    match_locations = []
    match_days = {}
    for i, day in enumerate(base_trip):
        if isinstance(day, dict) and day.get("matches") and day.get("location"):
            match_locations.append(day["location"])
            match_days[i] = {"day": day["day"], "location": day["location"]}

    if not match_locations:
        return variations

    # 3) Filter out any non-day entries for variation building
    filtered_trip = [d for d in base_trip if isinstance(d, dict) and "day" in d]

    # 4) Build set of all cities in train_times
    all_cities = set(c for pair in train_times.keys() for c in pair)

    # 5) Potential hotel bases = match_locations + any city within max_travel_time of every match
    potential_bases = set(match_locations)
    for city in all_cities:
        if all(
            train_times.get((city, loc), train_times.get((loc, city), float("inf"))) 
            <= max_travel_time
            for loc in match_locations
        ):
            potential_bases.add(city)

    # 6) If start_location given, precompute which cities are reachable from it
    reachable_from_start = set()
    if start_location:
        for city in all_cities:
            if train_times.get((start_location, city),
                               train_times.get((city, start_location), float("inf"))
                              ) <= max_travel_time:
                reachable_from_start.add(city)
        reachable_from_start.add(start_location)

    # --- Strategy 1: single-hotel stay variants ---
    for hotel_base in potential_bases:
        # skip bases too far for first-night
        if start_location and hotel_base not in reachable_from_start:
            continue

        # decide whether to preserve first-day hotel
        if 0 in match_days and hotel_base == match_days[0]["location"]:
            preserve_first = False
        else:
            preserve_first = False
            if 0 in match_days:
                first_loc = match_days[0]["location"]
                if train_times.get((hotel_base, first_loc),
                                   train_times.get((first_loc, hotel_base), float("inf"))
                                  ) > max_travel_time:
                    preserve_first = True

        var = create_hotel_variation(
            filtered_trip,
            hotel_base,
            start_idx=0,
            preserve_first_day=preserve_first,
            train_times=train_times,
            max_travel_time=max_travel_time
        )
        if var:
            variations.append(var)

    # --- Strategy 2: pivoting mid-trip ---
    if len(filtered_trip) >= 3:
        # find natural pivot indices
        pivots = [i for i in range(1, len(filtered_trip)-1) if i in match_days or i+1 in match_days]
        if not pivots and len(match_days) >= 2:
            idxs = sorted(match_days.keys())
            pivots = [idxs[len(idxs)//2]]

        for pivot in pivots:
            # first-segment matches & bases
            first_locs = [m["location"] for i,m in match_days.items() if i < pivot]
            first_bases = set(first_locs)
            for city in all_cities:
                if city in reachable_from_start or not start_location:
                    if all(
                        train_times.get((city, loc), train_times.get((loc, city), float("inf")))
                        <= max_travel_time for loc in first_locs
                    ):
                        first_bases.add(city)

            # second-segment same
            second_locs = [m["location"] for i,m in match_days.items() if i >= pivot]
            second_bases = set(second_locs)
            for city in all_cities:
                if all(
                    train_times.get((city, loc), train_times.get((loc, city), float("inf")))
                    <= max_travel_time for loc in second_locs
                ):
                    second_bases.add(city)

            # build each two-hotel variation
            for hb1 in first_bases:
                v1 = create_hotel_variation(
                    filtered_trip, hb1, 0, False, train_times, max_travel_time
                )
                if not v1:
                    continue

                for hb2 in second_bases:
                    if hb2 == hb1:
                        continue
                    v2 = create_hotel_variation(
                        v1, hb2, pivot, False, train_times, max_travel_time
                    )
                    if v2:
                        variations.append(v2)

    # --- Final validation with O(n) scan, no sorting/parsing ---
    valid = []
    for trip in variations:
        ok = True

        # initial travel from start_location
        if start_location:
            first_hotel = next(
                (d["hotel"] for d in trip if isinstance(d, dict) and d.get("hotel")), 
                None
            )
            if first_hotel and first_hotel.lower() != start_location.lower():
                t0 = train_times.get((start_location, first_hotel),
                                     train_times.get((first_hotel, start_location), float("inf")))
                if t0 > max_travel_time:
                    continue  # skip this variant

        prev_day = None
        for day in trip:
            if not isinstance(day, dict) or "day" not in day:
                continue

            if prev_day is not None:
                ph = prev_day.get("hotel")
                ch = day.get("hotel")

                # hotel→hotel
                if ph and ch and ph != ch:
                    th = train_times.get((ph, ch),
                                         train_times.get((ch, ph), float("inf")))
                    if th > max_travel_time:
                        ok = False
                        break

                # hotel→match and match→hotel
                if day.get("matches"):
                    ml = day["location"]
                    t1 = train_times.get((ph, ml),
                                         train_times.get((ml, ph), float("inf")))
                    if t1 > max_travel_time:
                        ok = False
                        break

                    if ch != ml:
                        t2 = train_times.get((ml, ch),
                                             train_times.get((ch, ml), float("inf")))
                        if t2 > max_travel_time:
                            ok = False
                            break

            prev_day = day

        if ok:
            valid.append(trip)

    return valid

def filter_best_variations_by_hotel_changes(trips: list, train_times: dict = None, max_travel_time: int = None) -> list:
    """
    For each distinct trip (same matches), show only the fastest route per number of hotel changes,
    and apply Pareto-optimal filtering to give meaningful choices.
    """
    # Group by match combinations
    match_signatures = {}
    
    for trip in trips:
        # Create a match signature for each trip
        match_signature = []
        for day in trip:
            if isinstance(day, dict) and "matches" in day:
                for match in day.get("matches", []):
                    match_signature.append((day.get("day", ""), match.get("match", "")))
        
        match_signature_tuple = tuple(sorted(match_signature))
        
        if match_signature_tuple not in match_signatures:
            match_signatures[match_signature_tuple] = []
        
        match_signatures[match_signature_tuple].append(trip)
    
    # Process each match group separately
    all_filtered_trips = []
    
    for match_group in match_signatures.values():
        # First filter by hotel changes
        by_change_count = {}
        
        for trip in match_group:
            # Validate all travel segments against max_travel_time
            has_invalid_segment = False
            
            # Check for hotel-to-hotel transitions
            sorted_days = sorted([d for d in trip if isinstance(d, dict) and d.get("day")], 
                    key=lambda x: parse_date_string(x.get("day", "")))
            
            for i in range(1, len(sorted_days)):
                prev_day = sorted_days[i-1]
                curr_day = sorted_days[i]
                
                prev_hotel = prev_day.get("hotel")
                curr_hotel = curr_day.get("hotel")
                
                if prev_hotel and curr_hotel and prev_hotel != curr_hotel:
                    transition_time = get_travel_minutes_utils(train_times, prev_hotel, curr_hotel)
                    if transition_time is None:
                        transition_time = float("inf")
                    if transition_time > max_travel_time:
                        has_invalid_segment = True
                        break
            
            # Skip trips with invalid segments
            if has_invalid_segment:
                continue
                
            # Get hotel change count
            hotel_stats = next((item for item in trip if isinstance(item, dict) and 
                                "hotel_changes" in item), {"hotel_changes": 0})
                
            change_count = hotel_stats.get("hotel_changes", 0)
            
            if change_count not in by_change_count:
                by_change_count[change_count] = []
                
            travel_time = calculate_total_travel_time(trip, train_times)
            by_change_count[change_count].append((travel_time, trip))
        
        # Get the fastest trip per hotel change count
        best_by_changes = []
        for change_count, trip_list in by_change_count.items():
            if trip_list:
                fastest_trip = min(trip_list, key=lambda x: x[0])[1]
                best_by_changes.append(fastest_trip)
        
        # Then apply Pareto-optimal filtering
        pareto_trips = filter_pareto_optimal_trips(best_by_changes, train_times)
        all_filtered_trips.extend(pareto_trips)
    
    return all_filtered_trips

def is_must_team_match(team_name: str, must_teams_set: set) -> bool:
    """Precisely match team names without catching reserve teams."""
    if not must_teams_set:
        return False
        
    team_name_lower = team_name.lower()
    
    # Check for reserve team indicators
    is_reserve_team = any(suffix in team_name_lower for suffix in 
                         [" ii", " 2", " u23", " u21", " u19", " amateure"])
    
    for must_team in must_teams_set:
        # Is the must_team specifically looking for a reserve team?
        is_must_reserve = any(suffix in must_team for suffix in 
                            [" ii", " 2", " u23", " u21", " u19", " amateure"])
        
        # Exact match
        if must_team == team_name_lower:
            return True
            
        # Skip if this is a reserve team but we're not looking for one
        if not is_must_reserve and is_reserve_team:
            base_team = team_name_lower
            for suffix in [" ii", " 2", " u23", " u21", " u19", " amateure"]:
                base_team = base_team.replace(suffix, "")
            base_team = base_team.strip()
            
            if base_team == must_team:
                continue
        
        # Regular matching
        if must_team in team_name_lower and (
            team_name_lower.startswith(must_team) or
            team_name_lower.endswith(must_team) or
            f" {must_team} " in f" {team_name_lower} "
        ):
            return True
    
    return False

def generate_rest_day_options(trip, current_date_str, train_times, max_travel_time, 
                             valid_games, full_date_range, date_idx):
    """
    Generate all possible hotel options for rest days using multiple strategic approaches.
    
    Args:
        trip: Current trip itinerary
        current_date_str: String representation of the current date
        train_times: Dictionary of travel times between locations
        max_travel_time: Maximum allowed travel time in minutes
        valid_games: List of all valid games for the trip
        full_date_range: List of datetime objects representing the entire trip range
        date_idx: Index of current date within full_date_range
        
    Returns:
        List of new trip variations with different rest day options
    """
    new_routes = []
    current_date = full_date_range[date_idx]
    previous_location = trip[-1]["location"]
    previous_hotel = trip[-1].get("hotel", previous_location)
    
    # STRATEGY 1: Stay at the same hotel (always include this as an option)
    new_trip_same_hotel = trip + [{
        "day": current_date_str,
        "location": previous_location,
        "matches": [],
        "note": "Rest Day",
        "hotel": previous_hotel
    }]
    new_routes.append(new_trip_same_hotel)
    
    # STRATEGY 2: Move to strategic locations for future games
    # Look ahead to find upcoming game locations
    future_game_locations = set()
    look_ahead_days = min(3, len(full_date_range) - date_idx - 1)  # Look ahead up to 3 days
    
    for future_day in range(1, look_ahead_days + 1):
        future_date = current_date + timedelta(days=future_day)
        future_games = [g for g in valid_games if g.date.date() == future_date.date()]
        for game in future_games:
            if hasattr(game, 'hbf_location'):
                future_game_locations.add(game.hbf_location)
    
    # Only consider hotel changes if there are future games
    if future_game_locations:
        # Add variations for each strategic future location
        for future_location in future_game_locations:
            # Check if moving to this location is within travel time limits
            travel_time = get_travel_minutes_utils(train_times, previous_hotel, future_location)
            if travel_time is not None and travel_time <= max_travel_time:
                # Create a new variation with hotel change
                new_trip_strategic = trip + [{
                    "day": current_date_str,
                    "location": previous_location,
                    "matches": [],
                    "note": f"Rest Day (Moving closer to {future_location.replace(' hbf', '')})",
                    "hotel": future_location,
                    "hotel_change": previous_hotel != future_location
                }]
                new_routes.append(new_trip_strategic)
    
    # STRATEGY 3: Consider major hub cities that can reach multiple future games
    if len(future_game_locations) >= 2:
        # Get all train cities from the train_times dictionary
        all_train_cities = set()
        for loc_pair in train_times.keys():
            all_train_cities.add(loc_pair[0])
            all_train_cities.add(loc_pair[1])
        
        # Find cities that can reach all future game locations
        potential_hubs = set()
        for city in all_train_cities:
            if all(get_travel_minutes_utils(train_times, city, game_loc) is not None and 
                   get_travel_minutes_utils(train_times, city, game_loc) <= max_travel_time 
                   for game_loc in future_game_locations):
                potential_hubs.add(city)
        
        # Filter out cities too far from current location
        for hub in list(potential_hubs):
            travel_time = get_travel_minutes_utils(train_times, previous_hotel, hub)
            if travel_time is None or travel_time > max_travel_time:
                potential_hubs.remove(hub)
        
        # Add up to 3 major hub options (to avoid too many variations)
        hub_count = 0
        for hub in potential_hubs:
            if hub != previous_hotel and hub not in future_game_locations and hub_count < 3:
                new_trip_hub = trip + [{
                    "day": current_date_str,
                    "location": previous_location,
                    "matches": [],
                    "note": f"Rest Day (Strategic hotel in {hub.replace(' hbf', '')})",
                    "hotel": hub,
                    "hotel_change": previous_hotel != hub
                }]
                new_routes.append(new_trip_hub)
                hub_count += 1
        # STRATEGY 4: Allow moving to any city within max_travel_time (even if not a future game location or hub)
    all_train_cities = set()
    for from_loc, to_loc in train_times.keys():
        all_train_cities.add(from_loc)
        all_train_cities.add(to_loc)
    
    for city in all_train_cities:
        if city == previous_hotel:
            continue
        travel_time = get_travel_minutes_utils(train_times, previous_hotel, city)
        if travel_time is not None and travel_time <= max_travel_time:
            new_trip_any_city = trip + [{
                "day": current_date_str,
                "location": previous_location,
                "matches": [],
                "note": f"Rest Day (Moving to {city})",
                "hotel": city,
                "hotel_change": previous_hotel != city
            }]
            new_routes.append(new_trip_any_city)
    return new_routes

# ────────────────────────────────
# 🛠️ Any Functions
# ────────────────────────────────

def determine_best_start_location(start_location: str, valid_games: list, start_date: datetime, train_times: dict, max_travel_time: int) -> str:
    """Determine the best starting location if 'Any' is specified."""
    if start_location.lower() != "any":
        return start_location
        
    try:
        # Collect all unique train stations
        all_hbfs = {g.hbf_location for g in valid_games if hasattr(g, 'hbf_location') and g.hbf_location != "Unknown"}
            
        if all_hbfs:
            reachable_counts = {}
            for city in all_hbfs:
                # Count reachable games from each city
                count = sum(1 for g in valid_games 
                           if g.date.date() == start_date.date() and
                           train_times.get((city, g.hbf_location), float("inf")) <= max_travel_time)
                reachable_counts[city] = count
            
            best_start = max(all_hbfs, key=lambda city: reachable_counts.get(city, 0))
            return best_start if best_start else "Unknown"
    except Exception:
        pass
        
    return "Unknown"

def identify_potential_start_cities(games, train_times, trip_duration, max_travel_time=120, **params):
    """Identify potential starting cities using various strategies"""
    start_date = params.get('start_date')
    if isinstance(start_date, str):
    # Convert string date to datetime if needed
        try:
            # Parse date with year already included
            start_date = datetime.strptime(start_date, "%d %B %Y")
        except:
            start_date = datetime.now()
    elif not start_date:
        start_date = datetime.now()
    
    trip_end_date = start_date + timedelta(days=trip_duration)
    
    # Get games in the trip period
    trip_games = [g for g in games if hasattr(g, 'date') and start_date.date() <= g.date.date() < trip_end_date.date()]
    
    if not trip_games:
        return DEFAULT_CITIES  # Default major cities as fallback
    
    candidate_cities = set()
    
    # Strategy 1: Include all game locations
    for game in trip_games:
        if hasattr(game, 'hbf_location') and game.hbf_location != "Unknown":
            candidate_cities.add(game.hbf_location)
    
    # Strategy 2: Include major transit hubs
    major_hubs = {"Berlin", "Frankfurt", "Munich", "Hamburg", "Cologne", "Düsseldorf", "Stuttgart"}
    candidate_cities.update(major_hubs)
    
    # Strategy 3: Find midpoints between games (cities that can reach multiple games)
    all_train_cities = set()
    for loc_pair in train_times.keys():
        all_train_cities.add(loc_pair[0])
        all_train_cities.add(loc_pair[1])
    
    game_locations = [g.hbf_location for g in trip_games if hasattr(g, 'hbf_location')]
    
    # NEW: Find cities that can reach at least 2 game locations within max_travel_time
    for city in all_train_cities:
        reachable_count = sum(1 for loc in game_locations if 
                            train_times.get((city, loc), float('inf')) <= max_travel_time)
        if reachable_count >= 2:
            candidate_cities.add(city)
    
    # NEW: Find strategic midpoints using clustering
    if len(game_locations) >= 3:
        # Find cities that minimize average travel time to game locations
        avg_travel_times = {}
        for city in all_train_cities:
            travel_times = [train_times.get((city, loc), float('inf')) for loc in game_locations]
            if all(t <= max_travel_time for t in travel_times):  # All games must be reachable
                avg_travel_times[city] = sum(travel_times) / len(travel_times)
        
        # Add top 5 cities with lowest average travel time
        if avg_travel_times:
            top_cities = sorted(avg_travel_times.items(), key=lambda x: x[1])[:5]
            for city, _ in top_cities:
                candidate_cities.add(city)
    
    # Ensure we don't have too many cities to test
    if len(candidate_cities) > 15:  # Limit to avoid excessive computation
        # Prioritize major hubs and game locations
        priority_cities = major_hubs.union(game_locations)
        additional_cities = list(candidate_cities - priority_cities)
        additional_cities.sort()  # Sort for deterministic behavior
        
        candidate_cities = list(priority_cities) + additional_cities[:15-len(priority_cities)]
    
    return list(candidate_cities)

async def enhance_trip_planning_for_any_start(request_id: str, **params):
    """
    Enhanced planning for 'Any' start location with cancellation support.
    Checks for cancellation periodically during the computation-heavy process.
    """
    # Check early cancellation
    if is_request_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled before 'Any' start processing")
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    # Extract key parameters
    start_location = params.get('start_location')
    if start_location.lower() != "any":
        # For regular start locations, use the cancellation-aware plan_trip wrapper
        return await plan_trip_with_cancellation(request_id=request_id, **params)
    
    logger.info(f"Request {request_id} starting 'Any' start location optimization")
    
    # 1. Identify potential starting cities
    # Create copies of params without keys we'll pass as positional args to avoid conflicts
    games = params.get('games')
    train_times_dict = params.get('train_times')
    trip_duration = params.get('trip_duration')
    max_travel_time = params.get('max_travel_time', 120)
    
    # Create a filtered params dict without the positional arguments
    filtered_params = {k: v for k, v in params.items() 
                     if k not in ('games', 'train_times', 'trip_duration', 'max_travel_time')}
    
    # Check cancellation before computationally intensive identify_potential_start_cities
    if is_request_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled before identifying potential start cities")
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    try:
        # IMPORTANT FIX: Run this with a timeout to prevent blocking
        potential_starts = await asyncio.wait_for(
            asyncio.to_thread(
                identify_potential_start_cities,
                games, 
                train_times_dict,
                trip_duration, 
                max_travel_time,
                **filtered_params
            ),
            timeout=10.0  # 10-second timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Request {request_id} timed out during potential start cities identification")
        # Fall back to a smaller list of default cities
        potential_starts = [
            "Berlin hbf", "Munich hbf", "Frankfurt hbf", "Hamburg hbf", 
            "Cologne hbf", "Stuttgart hbf"
        ]
    except Exception as e:
        logger.error(f"Request {request_id} error identifying potential start cities: {str(e)}")
        # Again fall back to defaults on any error
        potential_starts = [
            "Berlin hbf", "Munich hbf", "Frankfurt hbf", "Hamburg hbf", 
            "Cologne hbf", "Stuttgart hbf"
        ]
    
    logger.info(f"Request {request_id} identified {len(potential_starts)} potential start cities")
    
    # Check for cancellation after identifying start cities
    if is_request_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled after identifying start cities")
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    # 2. Generate trips for each potential start
    all_potential_trips = []
    trip_results_by_start = {}
    
    # Extract min_games from params with default of 2
    min_games = params.get('min_games', 2)
    
    # Process each potential start location with cancellation checks
    for i, potential_start in enumerate(potential_starts):
        # Check for cancellation before each city
        if is_request_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled during start city {i+1}/{len(potential_starts)}")
            return {"cancelled": True, "message": "Trip planning cancelled by user"}
        
        logger.info(f"Request {request_id} processing potential start {i+1}/{len(potential_starts)}: {potential_start}")
        
        try:
            # IMPORTANT FIX: Use non-blocking processing with timeout
            trip_result = {}
            try:
                # Run with a timeout for each city
                trip_result = await asyncio.wait_for(
                    asyncio.to_thread(
                        plan_trip,
                        start_location=potential_start,
                        trip_duration=trip_duration,
                        max_travel_time=max_travel_time,
                        games=games,
                        train_times=train_times_dict,
                        tbd_games=None,  # Explicitly set to None to ignore TBD games
                        preferred_leagues=params.get('preferred_leagues'),
                        start_date=params.get('start_date'),
                        must_teams=params.get('must_teams'),
                        min_games=min_games
                    ),
                    timeout=30.0  # 30-second timeout per city
                )
            except asyncio.TimeoutError:
                logger.warning(f"Request {request_id} - planning for {potential_start} timed out")
                continue
            
            # Store the entire result
            trip_results_by_start[potential_start] = trip_result
            
            # Extract trips and tag with start location
            if "trips" in trip_result and trip_result["trips"]:
                trip_count = len(trip_result["trips"])
                logger.info(f"Request {request_id} - {potential_start} yielded {trip_count} trips")
                
                for trip in trip_result["trips"]:
                    trip_copy = trip + [{"start_location": potential_start}]
                    all_potential_trips.append(trip_copy)
                    
        except Exception as e:
            logger.error(f"Request {request_id} - Error planning from {potential_start}: {str(e)}")
            continue
            
        # Periodically check for cancellation (after every ~25% of cities or at least after each city)
        if i > 0 and i % max(1, len(potential_starts) // 4) == 0:
            if is_request_cancelled(request_id):
                logger.info(f"Request {request_id} cancelled during start city processing at {i+1}/{len(potential_starts)}")
                return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    # Check for cancellation after all cities are processed
    if is_request_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled after processing all start cities")
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    # 3. Process results
    if not all_potential_trips:
        # If no trips found, return error
        return {"no_trips_available": True, "actual_start_date": params.get("start_date", "")}
    
    # Group trips by their game attendance pattern
    from utils import group_trips_by_matches, find_optimal_trip_in_group
    trip_groups = group_trips_by_matches(all_potential_trips)
    
    # Find optimal start location for each unique trip pattern
    best_trips = []
    for i, group in enumerate(trip_groups):
        # Check for cancellation periodically during group processing
        if i > 0 and i % 5 == 0:  # Every 5 groups
            if is_request_cancelled(request_id):
                return {"cancelled": True, "message": "Trip planning cancelled by user"}
                
        optimal_trip = find_optimal_trip_in_group(group)
        if optimal_trip:
            best_trips.append(optimal_trip)
    
    # Final cancellation check before finalizing results
    if is_request_cancelled(request_id):
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    # Extract actual_start_date
    actual_start_date = ""
    for start, result in trip_results_by_start.items():
        if "actual_start_date" in result:
            actual_start_date = result["actual_start_date"]
            break
    
    logger.info(f"Request {request_id} completed 'Any' start optimization with {len(all_potential_trips)} potential trips")
    
    # Final cancellation check
    if is_request_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled at final check in 'Any' start optimization")
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
        
    # Return the best options
    result = {"trips": best_trips, "actual_start_date": actual_start_date}
    
    logger.info(f"Request {request_id} finished 'Any' start optimization with {len(best_trips)} trips")
    return result

def group_trips_by_matches(trips):
    """Group trips by the set of matches they include"""
    groups = {}
    
    for trip in trips:
        # Use cached signature generation
        trip_key = make_trip_hashable(trip)
        signature = generate_trip_signature(trip_key)
        
        if signature not in groups:
            groups[signature] = []
        
        groups[signature].append(trip)
    
    return list(groups.values())

def find_optimal_trip_in_group(trip_group):
    """Find the optimal trip within a group with the same matches"""
    if not trip_group:
        return None
    
    # First prioritize by number of games
    trip_group.sort(key=lambda t: -sum(1 for day in t if isinstance(day, dict) and day.get("matches")))
    max_games = sum(1 for day in trip_group[0] if isinstance(day, dict) and day.get("matches"))
    
    # Filter to keep only trips with max games
    max_game_trips = [t for t in trip_group if 
                     sum(1 for day in t if isinstance(day, dict) and day.get("matches")) == max_games]
    
    # Then sort by total travel time
    max_game_trips.sort(key=lambda t: calculate_total_travel_time(t))
    
    # Finally sort by hotel changes
    max_game_trips.sort(key=lambda t: next((item.get("hotel_changes", 0) 
                                           for item in t 
                                           if isinstance(item, dict) and "hotel_changes" in item), 
                                          float('inf')))
    
    return max_game_trips[0] if max_game_trips else None

# ────────────────────────────────
# 🛠️ Plan Trip
# ────────────────────────────────

def plan_trip(start_location: str, trip_duration: int, max_travel_time: int, games: list, train_times: dict, 
             tbd_games: list = None, preferred_leagues: list = None, start_date: Optional[str] = None, 
             must_teams: Optional[list] = None, min_games: int = 2, one_city_only: Optional[bool] = False):
    """
    Main function to plan football trips based on available games.
    
    Args:
        start_location: Starting city for the trip
        trip_duration: Length of trip in days
        max_travel_time: Maximum travel time in minutes
        games: List of available games
        train_times: Dictionary of travel times between locations
        tbd_games: List of games with TBD times (IGNORED - will be handled separately)
        preferred_leagues: List of preferred leagues to filter games
        start_date: Optional start date string in format "28 March"
        must_teams: List of teams that must be included in the trip
        min_games: Minimum number of games to include in a trip (default 2)
    
    Returns:
        Dictionary containing trip options or error message
    """   

    if one_city_only:
        all_trips = []
        try:
            parsed_start_date, actual_start_date = get_processed_start_date(start_date)
            start_date = parsed_start_date
        except ValueError as e:
            return {"error": str(e)}
        preferred_leagues_lower = {league.lower() for league in preferred_leagues} if preferred_leagues else None
        valid_games = [
            g for g in games 
            if all(hasattr(g, attr) for attr in ('league', 'date', 'hbf_location')) and 
            (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
        ]
        must_teams_lower = {team.lower() for team in must_teams} if must_teams else None
        full_date_range = [start_date + timedelta(days=i) for i in range(trip_duration)]
        date_strings = [d.strftime("%d %B %Y") for d in full_date_range]
    
        # Build options for each day: each option is a dict (not a list of dicts)
        day_options = []
        for date_idx, current_date in enumerate(full_date_range):
            current_date_str = date_strings[date_idx]
            day_games = [
                g for g in valid_games
                if g.date.date() == current_date.date()
                and get_travel_minutes_utils(train_times, start_location, g.hbf_location) is not None
                and get_travel_minutes_utils(train_times, start_location, g.hbf_location) * 2 <= max_travel_time
            ]
            options = []
            for game in day_games:
                travel_time = get_travel_minutes_utils(train_times, start_location, game.hbf_location)
                options.append({
                    "day": current_date_str,
                    "location": start_location,
                    "matches": [{
                        "match": f"{game.home_team} vs {game.away_team} ({game.time})",
                        "location": game.hbf_location,
                        "date": current_date_str,
                        "travel_from": start_location,
                        "travel_time": format_travel_time(travel_time),
                        "contains_must_team": (
                            is_must_team_match(game.home_team, must_teams_lower) or
                            is_must_team_match(game.away_team, must_teams_lower)
                        ) if must_teams_lower else False
                    }],
                    "note": "",
                    "hotel": start_location
                })
            # Always add rest day as an option
            options.append({
                "day": current_date_str,
                "location": start_location,
                "matches": [],
                "note": "Rest Day",
                "hotel": start_location
            })
            day_options.append(options)
    
        # Generate all combinations (cartesian product)
        for trip_days in itertools.product(*day_options):
            trip = list(trip_days)
            if sum(len(day["matches"]) for day in trip) >= min_games:
                all_trips.append(trip)
    
        return {"trips": all_trips, "actual_start_date": actual_start_date}
    # --- END ONE CITY ONLY BLOCK ---

    # Initialize variables
    all_trips = []

    # Process start date
    try:
        parsed_start_date, actual_start_date = get_processed_start_date(start_date)
        start_date = parsed_start_date
    except ValueError as e:
        return {"error": str(e)}
    # ...rest of function...
    
    # Filter games by preferred leagues
    preferred_leagues_lower = {league.lower() for league in preferred_leagues} if preferred_leagues else None
    valid_games = [
        g for g in games 
        if all(hasattr(g, attr) for attr in ('league', 'date', 'hbf_location')) and 
        (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
    ]
    
    # Determine best start location if "Any" is specified
    start_location = determine_best_start_location(
        start_location, valid_games, start_date, train_times, max_travel_time
    )
    
    # Convert must_teams to lowercase set for efficient lookups
    must_teams_lower = {team.lower() for team in must_teams} if must_teams else None
    
    # REMOVED: Process TBD games
    
    # Generate date range for the trip
    full_date_range = [start_date + timedelta(days=i) for i in range(trip_duration)]
    date_strings = [d.strftime("%d %B %Y") for d in full_date_range]
    
    # Initial route with start location
    initial_routes = [[{
        "day": date_strings[0], 
        "location": start_location, 
        "matches": [], 
        "note": "Start", 
        "hotel": start_location
    }]]

    # Build trip routes day by day
    for date_idx, current_date in enumerate(full_date_range):
        current_date_str = date_strings[date_idx]
        new_routes = []

        # Filter games for current date
        current_date_games = [g for g in valid_games if g.date.date() == current_date.date()]
        
        # Handle rest days (no games on this date)
        if not current_date_games:
            for trip in initial_routes:
                # Generate all rest day options for this trip
                trip_options = generate_rest_day_options(
                    trip=trip,
                    current_date_str=current_date_str, 
                    train_times=train_times,
                    max_travel_time=max_travel_time,
                    valid_games=valid_games,
                    full_date_range=full_date_range,
                    date_idx=date_idx
                )
                new_routes.extend(trip_options)
            
            initial_routes = new_routes
            continue

        # Process each potential trip route
        for trip in initial_routes:
            try:
                # Get current locations from trip for route planning
                if len(trip) == 1:
                    # On the first day, use the start location
                    current_locations = {trip[0].get("location", start_location)}
                else:
                    # On subsequent days, use the hotel as the current location
                    current_locations = {day.get("hotel", day.get("location", start_location)) for day in trip}                
                # Find reachable games from each location
                reachable_by_location = {}
                
                for loc in current_locations:
                    for game in current_date_games:
                        
                        # Use get_travel_minutes_utils instead of direct train_times lookup
                        travel_time = get_travel_minutes_utils(train_times, loc, game.hbf_location)
                        if travel_time is not None and travel_time <= max_travel_time:
                            travel_time_str = format_travel_time(travel_time)
                            match_str = f"{game.home_team} vs {game.away_team} ({game.time})"
                            
                            # Check if match contains a must-see team
                            contains_must_team = False
                            if must_teams_lower:
                                contains_must_team = (
                                    is_must_team_match(game.home_team, must_teams_lower) or
                                    is_must_team_match(game.away_team, must_teams_lower)
                                )
                            
                            # Group matches by location
                            if game.hbf_location not in reachable_by_location:
                                reachable_by_location[game.hbf_location] = []
                                
                            reachable_by_location[game.hbf_location].append({
                                "match": match_str,
                                "location": game.hbf_location,
                                "date": current_date_str,
                                "travel_from": loc,
                                "travel_time": travel_time_str,
                                "contains_must_team": contains_must_team
                            })
                
                # ALWAYS add a rest day option (this is the key change)
                hotel_location = trip[-1]["hotel"]
                new_trip = trip + [{
                    "day": current_date_str,
                    "location": trip[-1]["location"],
                    "matches": [],
                    "note": "Rest Day (Skipped Match)",
                    "hotel": hotel_location
                }]
                new_routes.append(new_trip)
                
                # If no reachable games, we've already added the rest day above
                if not reachable_by_location:
                    continue
                
                # Add new routes based on reachable games
                for location, options in reachable_by_location.items():
                    # Select best option (shortest travel time)
                    best_option = min(options, key=lambda o: train_times.get((o["travel_from"], o["location"]), float("inf")))
                    
                    # Get trip locations for route efficiency check
                    trip_locations = [day.get("location") for day in trip if "location" in day]
                    
                    # Add efficient routes only
                    if is_efficient_route(trip, location, trip_locations):
                        new_trip = trip + [{
                            "day": current_date_str,
                            "location": location,
                            "matches": [best_option],
                            "note": "",
                            "hotel": location
                        }]
                        new_routes.append(new_trip)
                    
                    # Add alternate routes from different starting points
                    from_locations = {best_option["travel_from"]}
                    for option in options:
                        if option["travel_from"] not in from_locations and is_efficient_route(trip, location, trip_locations):
                            from_locations.add(option["travel_from"])
                            new_trip = trip + [{
                                "day": current_date_str,
                                "location": location,
                                "matches": [option],
                                "note": "",
                                "hotel": location
                            }]
                            new_routes.append(new_trip)
                
            except Exception:
                # Add rest day as fallback if error occurs
                try:
                    hotel_location = trip[-1]["hotel"]
                    new_trip = trip + [{
                        "day": current_date_str,
                        "location": trip[-1]["location"],
                        "matches": [],
                        "note": "Rest Day (ERROR)",
                        "hotel": hotel_location
                    }]
                    new_routes.append(new_trip)
                except:
                    continue

        initial_routes = new_routes
        

    all_trips = [trip for trip in initial_routes 
                if sum(len(day.get("matches", [])) > 0 for day in trip) >= min_games]
    
    # Filter trips to include only those with required teams
    if must_teams_lower and all_trips:
        all_trips = [
            trip for trip in all_trips
            if all(
                any(
                    match.get("match", "") and (
                        is_must_team_match(match.get("match", "").split(" vs ")[0].split(" (")[0], {required_team}) or
                        is_must_team_match(match.get("match", "").split(" vs ")[1].split(" (")[0], {required_team})
                    )
                    for day in trip 
                    for match in day.get("matches", [])
                )
                for required_team in must_teams_lower
            )
        ]
        
    # Optimize trip variations with different hotel strategies
    optimized_trips = []
    for original_trip in all_trips:
        trip_without_stats = [day for day in original_trip if isinstance(day, dict) and "day" in day]
        variations = optimize_trip_variations(trip_without_stats, train_times, max_travel_time, start_location)
        optimized_trips.extend(variations)
    
    # Replace with optimized trips
    all_trips = optimized_trips

    # Pre-process the trip to ensure hotel consistency
    for trip in all_trips:
        # Organize entries by day
        entries_by_day = {}
        for day in trip:
            if isinstance(day, dict) and day.get("day"):
                day_str = day.get("day")
                if day_str not in entries_by_day:
                    entries_by_day[day_str] = []
                entries_by_day[day_str].append(day)
        
        # For each day with multiple entries, ensure only the last one has hotel info
        for day_str, entries in entries_by_day.items():
            if len(entries) > 1:
                # Sort entries by their position in the original trip
                sorted_entries = sorted(entries, key=lambda e: trip.index(e))
                
                # Get the final hotel location for this day
                final_hotel = sorted_entries[-1].get("hotel")
                
                # Update the first entry for day marker, but without a hotel
                if "hotel" in sorted_entries[0]:
                    sorted_entries[0].pop("hotel")
                
                # Ensure only the last entry has the hotel
                for i, entry in enumerate(sorted_entries[:-1]):
                    if "hotel" in entry:
                        entry.pop("hotel")
                
                if final_hotel:
                    sorted_entries[-1]["hotel"] = final_hotel

    # Calculate hotel statistics for each trip
    for trip in all_trips:
        hotel_stays = []
        hotel_locations = set()
        previous_hotel = None
        hotel_changes = 0
        
        # Check if trip has at least 2 games
        game_count = sum(1 for day in trip if isinstance(day, dict) and day.get("matches"))
        if game_count < 2:
            continue
        
        # First organize days by date, keeping only the last entry for each date
        # (the last entry represents where the traveler actually stays that night)
        days_by_date = {}
        for day in trip:
            if isinstance(day, dict) and day.get("day") and day.get("hotel"):
                days_by_date[day.get("day")] = day
        
        # Sort days chronologically
        sorted_dates = sorted(
            days_by_date.keys(),
            key=lambda d: parse_date_string(d)
        )
        
        # Now process days in chronological order using the final hotel for each day
        for date_str in sorted_dates:
            day = days_by_date[date_str]
            current_hotel = day.get("hotel")
            
            if current_hotel:
                # Count hotel changes
                if previous_hotel and current_hotel != previous_hotel:
                    hotel_changes += 1
                    day["hotel_change"] = True
                else:
                    day["hotel_change"] = False
                
                hotel_locations.add(current_hotel)
                
                # Add to hotel stays
                if not hotel_stays or hotel_stays[-1]["location"] != current_hotel:
                    hotel_stays.append({
                        "location": current_hotel,
                        "check_in_date": date_str,
                        "nights": 1
                    })
                else:
                    hotel_stays[-1]["nights"] += 1
                
                previous_hotel = current_hotel
        
        # Generate detailed hotel info
        hotel_details = []
        previous_hotel = None
        
        for date_str in sorted_dates:
            day = days_by_date[date_str]
            current_hotel = day.get("hotel")
            
            hotel_detail_entry = {
                "date": date_str,
                "location": current_hotel,
                "is_change": previous_hotel is not None and current_hotel != previous_hotel
            }
            hotel_details.append(hotel_detail_entry)
            previous_hotel = current_hotel
        
        # Add hotel stats to the trip
        trip_hotel_stats = {
            "hotel_changes": hotel_changes,
            "unique_hotels": len(hotel_locations),
            "hotel_locations": list(hotel_locations),
            "hotel_stays": hotel_stays,
            "hotel_details": hotel_details
        }
        
        trip.append(trip_hotel_stats)
    
    # Filter to show only best trip per hotel change count
    all_trips = filter_best_variations_by_hotel_changes(all_trips, train_times, max_travel_time)
    
    # Return appropriate response based on results
    if not all_trips:
        return {"no_trips_available": True, "actual_start_date": actual_start_date}

    return {"trips": all_trips, "actual_start_date": actual_start_date}

async def plan_trip_with_cancellation(request_id: str, **planning_params):
    """
    Wrapper for plan_trip that adds cancellation checks at key points in the algorithm.
    """
    # Check for early cancellation
    if is_request_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled before starting trip planning")
        return {"cancelled": True, "message": "Trip planning cancelled by user"}
    
    try:
        # Extract key parameters
        start_location = planning_params.get('start_location')
        trip_duration = planning_params.get('trip_duration')
        max_travel_time = planning_params.get('max_travel_time')
        games = planning_params.get('games')
        train_times_param = planning_params.get('train_times')
        preferred_leagues = planning_params.get('preferred_leagues')
        start_date = planning_params.get('start_date')
        must_teams = planning_params.get('must_teams')
        min_games = planning_params.get('min_games', 2)
        
        logger.info(f"Request {request_id} planning with {start_location}, {trip_duration} days")
        
        # Process start date - this is a quick operation, no cancellation check needed
        try:
            parsed_start_date, actual_start_date = get_processed_start_date(start_date)
        except ValueError as e:
            logger.error(f"Request {request_id} failed parsing start date: {e}")
            return {"error": str(e)}
        
        # Check for cancellation before filtering games
        if is_request_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled before filtering games")
            return {"cancelled": True, "message": "Trip planning cancelled by user"}
            
        # Filter games by preferred leagues
        preferred_leagues_lower = {league.lower() for league in preferred_leagues} if preferred_leagues else None
        valid_games = [
            g for g in games 
            if all(hasattr(g, attr) for attr in ('league', 'date', 'hbf_location')) and 
            (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
        ]
        
        logger.info(f"Request {request_id} filtered to {len(valid_games)} valid games")
        
        # Convert must_teams to lowercase set for efficient lookups
        must_teams_lower = {team.lower() for team in must_teams} if must_teams else None
        
        # Check for cancellation before starting main trip calculation
        if is_request_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled before main trip calculation")
            return {"cancelled": True, "message": "Trip planning cancelled by user"}
        
        # CRITICAL FIX: Run the plan_trip function in a task with cancellation checks
        logger.info(f"Request {request_id} starting main trip planning with {len(valid_games)} games")
        
        # We'll use a loop with cancellation checks to monitor progress
        check_interval = 0.1  # Check every 100ms
        max_time = 120  # Maximum time to allow (seconds)
        start_time = datetime.now()
        
        # Create a future for the trip result
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            plan_trip,
            start_location=start_location,
            trip_duration=trip_duration,
            max_travel_time=max_travel_time,
            games=valid_games,
            train_times=train_times_param,
            tbd_games=None,
            preferred_leagues=preferred_leagues,
            start_date=start_date,
            must_teams=must_teams,
            min_games=min_games,
            one_city_only=planning_params.get('one_city_only', False)  # <-- ADD THIS
        )
        
        # Monitor for completion or cancellation
        while not future.done():
            # Check if cancelled
            if is_request_cancelled(request_id):
                # Cancel the thread and stop processing
                future.cancel()
                logger.info(f"Request {request_id} cancelled during trip planning")
                return {"cancelled": True, "message": "Trip planning cancelled by user"}
            
            # Check for timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_time:
                future.cancel()
                logger.warning(f"Request {request_id} exceeded maximum time limit ({max_time}s)")
                return {"error": "Trip planning timed out", "cancelled": True}
            
            # Wait a bit before checking again
            await asyncio.sleep(check_interval)
        
        # Get the result now that it's done
        trip_result = future.result()
        
        # Final cancellation check before returning
        if is_request_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled after trip planning completed")
            return {"cancelled": True, "message": "Trip planning cancelled by user"}
        
        # Log completion
        trip_count = len(trip_result.get("trips", [])) if isinstance(trip_result, dict) else 0
        logger.info(f"Request {request_id} plan_trip completed with {trip_count} trips")
        
        return trip_result
        
    except Exception as e:
        logger.error(f"Request {request_id} failed in plan_trip_with_cancellation: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}