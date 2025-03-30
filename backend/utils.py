import functools
import pandas as pd
from datetime import datetime, timedelta
from models import Game
from scrapers.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums
from typing import Optional, List, Dict, Tuple
import copy
from config import TRAIN_TIMES_FILE

# ────────────────────────────────
# 🛠️ Helper Functions
# ────────────────────────────────
def memoize_travel_time(func):
    cache = {}
    
    @functools.wraps(func)
    def wrapper(train_times, from_city, to_city):
        key = (from_city.lower(), to_city.lower())
        if key not in cache:
            cache[key] = func(train_times, from_city, to_city)
        return cache[key]
    
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
    current_year = datetime.now().year

    for _, row in df.iterrows():
        try:
            date_str = row["Date"] + f" {current_year}"
            date_main = datetime.strptime(date_str, "%d %B %Y")  
            
            game = Game(
                league=row["League"].strip(),
                date=date_main,
                time=row["Time"],
                home_team=row["Home Team"].strip(),
                away_team=row["Away Team"].strip(),
                hbf_location=map_team_to_hbf(row["Home Team"])
            )
            
            if str(row["Time"]).lower() == "tbd":
                tbd_games.append(game)
            else:
                games.append(game)
                
        except Exception as e:
            print(f"Error parsing row {row}: {e}")
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
            
        match_signature = []
        for day in trip["Itinerary"]:
            if day.get("matches"):
                for match in day["matches"]:
                    match_signature.append((day.get("day"), match["match"]))
        
        match_signature_tuple = tuple(sorted(match_signature))
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

    for day in sorted(hotel_by_day.keys(), key=lambda d: datetime.strptime(d + " 2025", "%d %B %Y")):
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
        key=lambda x: datetime.strptime(x.get("day") + " 2025", "%d %B %Y")
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

def get_reachable_games(locations: list, games: list, train_times: dict, max_travel_time: int, current_date: datetime) -> list:
    """Find games reachable within max_travel_time from any of the provided locations."""
    if not locations or not games:
        return []
        
    current_date_only = current_date.date()
    
    todays_games = [game for game in games if hasattr(game, 'date') and game.date.date() == current_date_only]
    
    if not todays_games:
        return []
    
    unique_locations = set(locations)
    reachable = []
    
    for loc in unique_locations:
        for game in todays_games:
            if hasattr(game, 'hbf_location'):
                # Use helper function instead of direct lookup
                travel_time = get_travel_minutes_utils(train_times, loc, game.hbf_location)
                if travel_time is not None and travel_time <= max_travel_time:
                    reachable.append({
                        "game": game,
                        "from": loc,
                        "travel_time": travel_time
                    })
    
    return reachable

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

def create_hotel_variation(base_trip: list, hotel_base: str, start_idx=0, 
                           preserve_first_day=True, train_times=None, max_travel_time=None) -> list:
    """
    Create a trip variation using a specific hotel base, rebuilding travel segments to match.
    This updated version enforces that a hotel change cannot occur on a game day.
    """
    variation = copy.deepcopy(base_trip)
    is_valid = True

    # Ensure the first day has a hotel value; if missing, use the day's location or hotel_base
    if variation and isinstance(variation[0], dict):
        if not variation[0].get("hotel"):
            variation[0]["hotel"] = variation[0].get("location", hotel_base)

    # First pass: Set hotel locations
    for i, day in enumerate(variation):
        # Skip days before start_idx or preserve the first day if needed
        if i < start_idx or (i == 0 and preserve_first_day):
            continue

        # *** NEW: If day has matches, do not allow a hotel change on the same day.
        if day.get("matches"):
            # For game days, force the hotel to be the same as the previous day's hotel.
            # (If this is the first day, use hotel_base as fallback.)
            day["hotel"] = variation[i-1].get("hotel") if i > 0 else hotel_base
            continue

        current_loc = day.get("location")

        # For rest days or days without matches, assign hotel according to feasibility
        if not day.get("matches"):
            day["hotel"] = hotel_base
            continue

        # (The following logic is kept for completeness but will not trigger because
        # days with matches are already handled above.)
        if current_loc == hotel_base:
            day["hotel"] = hotel_base
            continue

        travel_time = train_times.get((hotel_base, current_loc), float("inf"))
        return_time = train_times.get((current_loc, hotel_base), float("inf"))

        if travel_time <= max_travel_time and return_time <= max_travel_time:
            day["hotel"] = hotel_base
        else:
            day["hotel"] = current_loc

    # Second pass: Update travel segments based on hotel locations
    for i, day in enumerate(variation):
        if i == 0:
            continue

        if day.get("matches"):
            current_match_loc = day.get("location")
            previous_hotel = variation[i-1].get("hotel")
            current_hotel = day.get("hotel")
            travel_time = train_times.get((previous_hotel, current_match_loc), float("inf"))
            if travel_time > max_travel_time:
                is_valid = False
                break
            for match in day.get("matches", []):
                match["travel_from"] = previous_hotel
                match["travel_time"] = format_travel_time(travel_time)
    # Third pass: Check hotel-to-hotel transitions between days
    sorted_days = sorted([d for d in variation if isinstance(d, dict) and d.get("day")],
                         key=lambda x: x.get("day", ""))
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
                is_valid = False
                break

    return variation if is_valid else None

def optimize_trip_variations(base_trip: list, train_times: dict, max_travel_time: int, start_location: str = None) -> list:
    """
    Generate optimized variations of a trip with different hotel strategies,
    ensuring all travel segments are feasible.
    """
    # Always include the original trip
    variations = [copy.deepcopy(base_trip)]
    
    # Extract match locations and dates for validation
    match_locations = []
    match_days = {}
    
    for i, day in enumerate(base_trip):
        if isinstance(day, dict):
            day_str = day.get("day")
            location = day.get("location")
            
            if location and day.get("matches"):
                match_locations.append(location)
                match_days[i] = {"day": day_str, "location": location}
    
    if not match_locations:
        return variations
    
    # Prepare trip for variations
    filtered_trip = [day for day in base_trip if isinstance(day, dict) and "day" in day]
    
    # Get all potential hotel bases (match locations + cities with good connections)
    potential_hotel_locations = set(match_locations)
    
    # Add cities that are within max_travel_time of all match locations
    all_train_cities = set()
    for loc_pair in train_times.keys():
        all_train_cities.add(loc_pair[0])
        all_train_cities.add(loc_pair[1])
    
    # NEW: Identify cities that are reachable from the start location
    reachable_from_start = set()
    if start_location:
        for city in all_train_cities:
            travel_time = train_times.get((start_location, city), 
                                        train_times.get((city, start_location), float("inf")))
            if travel_time <= max_travel_time:
                reachable_from_start.add(city)
        
        # Make sure start location itself is included
        reachable_from_start.add(start_location)
    
    for city in all_train_cities:
        # Only consider cities reachable from all match locations
        if all(train_times.get((city, match_loc), float("inf")) <= max_travel_time 
              for match_loc in match_locations):
            potential_hotel_locations.add(city)
    
    # Strategy 1: Generate single-base variations (stay in same hotel throughout)
    for hotel_base in potential_hotel_locations:
        # NEW: Check if hotel base is reachable from start location for first night
        if start_location and hotel_base != start_location and hotel_base not in reachable_from_start:
            # Hotel is too far from start location, skip this base entirely for single-hotel stays
            continue
            
        # Use first match location as a consideration for the first day's hotel
        if match_days and 0 in match_days:
            first_match_location = match_days[0]["location"]
            if hotel_base == first_match_location:
                preserve_first_day = False
            else:
                # Check if travel from hotel_base to first match is feasible
                travel_time = train_times.get((hotel_base, first_match_location), float("inf"))
                preserve_first_day = travel_time > max_travel_time
        else:
            preserve_first_day = False
            
        # Create variation with this hotel base
        variation = create_hotel_variation(
            filtered_trip, hotel_base, 0, preserve_first_day, train_times, max_travel_time
        )
        
        if variation:
            variations.append(variation)
    
    # Strategy 2: Generate pivot variations (change hotel mid-trip)
    if len(filtered_trip) >= 3:
        # Find logical pivot points (before match days)
        pivot_points = []
        for i in range(1, len(filtered_trip) - 1):
            if i in match_days or i+1 in match_days:
                pivot_points.append(i)
                
        if not pivot_points and len(match_days) >= 2:
            # Fallback: use midpoint between first and last match
            match_indices = sorted(match_days.keys())
            pivot_points = [match_indices[len(match_indices)//2]]
            
        for pivot_idx in pivot_points:
            # Get potential hotels for first segment
            first_segment_matches = [match_days[i]["location"] for i in match_days if i < pivot_idx]
            
            # First hotel bases: must be reachable from start_location and all first segment matches
            potential_first_hotels = set(first_segment_matches)
            for city in all_train_cities:
                if (city in reachable_from_start or not start_location) and all(
                    train_times.get((city, loc), float("inf")) <= max_travel_time 
                    for loc in first_segment_matches
                ):
                    potential_first_hotels.add(city)
            
            # Get potential hotels for second segment
            second_segment_matches = [match_days[i]["location"] for i in match_days if i >= pivot_idx]
            
            # Second hotel bases: either at second segment match or reachable from all second matches
            potential_second_hotels = set(second_segment_matches)
            for city in all_train_cities:
                if all(train_times.get((city, loc), float("inf")) <= max_travel_time 
                      for loc in second_segment_matches):
                    potential_second_hotels.add(city)
            
            # Create pivot variations
            for first_hotel in potential_first_hotels:
                for second_hotel in potential_second_hotels:
                    if second_hotel == first_hotel:
                        continue
                    
                    # First create variation with first_hotel for first segment
                    pivot_variation = create_hotel_variation(
                        filtered_trip, first_hotel, 0, False, train_times, max_travel_time
                    )
                    
                    if not pivot_variation:
                        continue
                    
                    # Then apply second_hotel for second segment
                    second_part = create_hotel_variation(
                        pivot_variation, second_hotel, pivot_idx, False, train_times, max_travel_time
                    )
                    
                    if second_part:
                        variations.append(second_part)

    # Final validation: ensure all trips respect max_travel_time for every segment
    valid_variations = []
    for trip in variations:
        # Validate against max_travel_time
        is_valid = True
        
        # NEW: Check initial travel from start_location to first hotel
        if start_location:
            first_hotel = None
            for day in trip:
                if isinstance(day, dict) and day.get("hotel"):
                    first_hotel = day.get("hotel")
                    break
                    
            if first_hotel and first_hotel.lower() != start_location.lower():
                initial_travel_time = train_times.get((start_location, first_hotel), 
                                                      train_times.get((first_hotel, start_location), float('inf')))
                if initial_travel_time > max_travel_time:
                    is_valid = False
                    continue  # Skip this variation entirely
        
        # Check hotel-to-hotel transitions and match travel
        sorted_days = sorted([d for d in trip if isinstance(d, dict) and d.get("day")], 
                             key=lambda x: x.get("day", ""))
        
        for i in range(1, len(sorted_days)):
            prev_day = sorted_days[i-1]
            curr_day = sorted_days[i]
            
            # Check hotel-to-hotel transitions
            prev_hotel = prev_day.get("hotel")
            curr_hotel = curr_day.get("hotel")
            
            if prev_hotel and curr_hotel and prev_hotel != curr_hotel:
                transition_time = get_travel_minutes_utils(train_times, prev_hotel, curr_hotel)
                if transition_time is None:
                    transition_time = float("inf")
                if transition_time > max_travel_time:
                    is_valid = False
                    break
            
            # Check hotel-to-match travel
            if curr_day.get("matches"):
                match_loc = curr_day.get("location")
                hotel_to_match = train_times.get((prev_hotel, match_loc), float("inf"))
                if hotel_to_match > max_travel_time:
                    is_valid = False
                    break
                
                # Check match-to-hotel return travel if staying elsewhere
                if curr_hotel != match_loc:
                    match_to_hotel = train_times.get((match_loc, curr_hotel), float("inf"))
                    if match_to_hotel > max_travel_time:
                        is_valid = False
                        break
        
        if is_valid:
            valid_variations.append(trip)
    
    return valid_variations

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
                                key=lambda x: x.get("day", ""))
            
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

def get_processed_start_date(start_date: Optional[str] = None) -> Tuple[datetime, str]:
    """Process and validate the start date."""
    current_year = datetime.now().year
    
    if start_date:
        try:
            parsed_date = datetime.strptime(f"{start_date} {current_year}", "%d %B %Y")
            return parsed_date, parsed_date.strftime("%d %B")
        except ValueError:
            raise ValueError("Invalid start date format. Use '28 March' format.")
    else:
        today = datetime.now()
        return today, today.strftime("%d %B")

def process_tbd_games(tbd_games: list, start_date: datetime, trip_duration: int, 
                    preferred_leagues: list, potential_locations: set,
                    must_teams_lower: set, train_times: dict, max_travel_time: int) -> list:
    """Process TBD games and find ones within the trip period."""
    tbd_games_in_period = []
    trip_end_date = start_date + timedelta(days=trip_duration)
    preferred_leagues_lower = {league.lower() for league in preferred_leagues} if preferred_leagues else None
    
    for tbd_game in tbd_games:
        try:
            # Skip games without required attributes
            if not all(hasattr(tbd_game, attr) for attr in ('league', 'date', 'hbf_location')):
                continue
            
            # Skip games not in preferred leagues
            if preferred_leagues_lower and tbd_game.league.lower() not in preferred_leagues_lower:
                continue
                
            # Skip games outside trip duration
            if not (start_date.date() <= tbd_game.date.date() < trip_end_date.date()):
                continue
            
            # Check if a must_team is present
            tbd_match_contains_must_team = False
            if must_teams_lower:
                tbd_match_contains_must_team = (
                    is_must_team_match(tbd_game.home_team, must_teams_lower) or
                    is_must_team_match(tbd_game.away_team, must_teams_lower)
                )
            
            # Check travel time from any potential location
            for loc in potential_locations:
                travel_time = train_times.get((loc, tbd_game.hbf_location), float("inf"))
                if travel_time <= max_travel_time:
                    date_str = tbd_game.date.strftime("%d %B")
                    tbd_games_in_period.append({
                        "match": f"{tbd_game.home_team} vs {tbd_game.away_team}",
                        "date": date_str,
                        "location": tbd_game.hbf_location,
                        "league": tbd_game.league,
                        "has_must_team": tbd_match_contains_must_team
                    })
                    break
        except Exception:
            continue
            
    return tbd_games_in_period

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
            start_date = datetime.strptime(f"{start_date} 2025", "%d %B %Y")
        except:
            start_date = datetime.now()
    elif not start_date:
        start_date = datetime.now()
    
    trip_end_date = start_date + timedelta(days=trip_duration)
    
    # Get games in the trip period
    trip_games = [g for g in games if hasattr(g, 'date') and start_date.date() <= g.date.date() < trip_end_date.date()]
    
    if not trip_games:
        return ["Berlin", "Frankfurt", "Munich"]  # Default major cities as fallback
    
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

def enhance_trip_planning_for_any_start(start_location, trip_duration, max_travel_time, games, train_times, **other_params):
    """Enhanced planning when 'Any' start location is chosen"""
    if start_location.lower() != "any":
        # Use regular planning for specific start locations
        return plan_trip(start_location, trip_duration, max_travel_time, games, train_times, **other_params)
    
    # 1. Identify potential starting cities
    potential_starts = identify_potential_start_cities(games, train_times, trip_duration, max_travel_time, **other_params)
    
    # 2. Generate trips for each potential start
    all_potential_trips = []
    trip_results_by_start = {}
    
    for potential_start in potential_starts:
        try:
            trip_result = plan_trip(potential_start, trip_duration, max_travel_time, games, train_times, **other_params)
            
            # Store the entire result to preserve TBD games and other metadata
            trip_results_by_start[potential_start] = trip_result
            
            # Extract trips and tag with start location
            if "trips" in trip_result and trip_result["trips"]:
                for trip in trip_result["trips"]:
                    trip_copy = copy.deepcopy(trip)
                    # Tag trips with their start location for reference
                    trip_copy.append({"start_location": potential_start})
                    all_potential_trips.append(trip_copy)
        except Exception as e:
            print(f"Error planning trip from {potential_start}: {e}")
            continue
    
    # 3. Sort and filter the trips to find the best options
    if not all_potential_trips:
        # If no trips found, return the result from first city with TBD games, or error
        for start, result in trip_results_by_start.items():
            if "TBD_Games" in result and result["TBD_Games"]:
                return result
        
        return {"no_trips_available": True, "actual_start_date": other_params.get("start_date", "")}
    
    # Group trips by their game attendance pattern
    trip_groups = group_trips_by_matches(all_potential_trips)
    
    # Find optimal start location for each unique trip pattern
    best_trips = []
    for group in trip_groups:
        # For each distinct set of games, find the trip with:
        optimal_trip = find_optimal_trip_in_group(group)
        if optimal_trip:
            best_trips.append(optimal_trip)
    
    # Extract TBD games from any result (they should be the same)
    tbd_games = None
    actual_start_date = ""
    for start, result in trip_results_by_start.items():
        if "TBD_Games" in result and result["TBD_Games"]:
            tbd_games = result["TBD_Games"]
        if "actual_start_date" in result:
            actual_start_date = result["actual_start_date"]
        if tbd_games and actual_start_date:
            break
    
    # Return the best options
    result = {"trips": best_trips, "actual_start_date": actual_start_date}
    if tbd_games:
        result["TBD_Games"] = tbd_games
    
    return result

def group_trips_by_matches(trips):
    """Group trips by the set of matches they include"""
    groups = {}
    
    for trip in trips:
        # Create signature based on attended matches
        match_signature = []
        for day in trip:
            if isinstance(day, dict) and "matches" in day:
                for match in day.get("matches", []):
                    match_signature.append((day.get("day", ""), match.get("match", "")))
        
        signature = tuple(sorted(match_signature))
        
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
             tbd_games: list = None, preferred_leagues: list = None, start_date: Optional[str] = None, must_teams: Optional[list] = None):    
    """
    Main function to plan football trips based on available games.
    
    Args:
        start_location: Starting city for the trip
        trip_duration: Length of trip in days
        max_travel_time: Maximum travel time in minutes
        games: List of available games
        train_times: Dictionary of travel times between locations
        tbd_games: List of games with TBD times
        preferred_leagues: List of preferred leagues to filter games
        start_date: Optional start date string in format "28 March"
        must_teams: List of teams that must be included in the trip
    
    Returns:
        Dictionary containing trip options or error message
    """    
    # Initialize variables
    all_trips = []
    tbd_games_in_period = []
    
    # Process start date
    try:
        parsed_start_date, actual_start_date = get_processed_start_date(start_date)
        start_date = parsed_start_date
    except ValueError as e:
        return {"error": str(e)}
    
    # Filter games by preferred leagues
    preferred_leagues_lower = {league.lower() for league in preferred_leagues} if preferred_leagues else None
    valid_games = [
        g for g in games 
        if all(hasattr(g, attr) for attr in ('league', 'date', 'hbf_location')) and 
        (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
    ]
    
    # Add this after loading valid_games
    trip_end_date = start_date + timedelta(days=trip_duration)
    valid_trip_games = [g for g in valid_games if start_date.date() <= g.date.date() < trip_end_date.date()]

    # Find earliest valid game date if no specific start date
    if not start_date:
        earliest_date = None
        for game in valid_games:
            if game.date.date() < datetime.now().date():
                continue
                
            if earliest_date is None or game.date < earliest_date:
                earliest_date = game.date
                
        if earliest_date:
            start_date = earliest_date
            actual_start_date = earliest_date.strftime("%d %B")
    
    # Determine best start location if "Any" is specified
    start_location = determine_best_start_location(
        start_location, valid_games, start_date, train_times, max_travel_time
    )
    
    # Convert must_teams to lowercase set for efficient lookups
    must_teams_lower = {team.lower() for team in must_teams} if must_teams else None
    
    # Process TBD games
    if tbd_games:
        potential_locations = {start_location} | {g.hbf_location for g in valid_games if hasattr(g, 'hbf_location')}
        tbd_games_in_period = process_tbd_games(
            tbd_games, start_date, trip_duration, preferred_leagues, 
            potential_locations, must_teams_lower, train_times, max_travel_time
        )
    
    # Generate date range for the trip
    full_date_range = [start_date + timedelta(days=i) for i in range(trip_duration)]
    date_strings = [d.strftime("%d %B") for d in full_date_range]
    
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
                new_trip = copy.deepcopy(trip)
                hotel_location = trip[-1]["hotel"]
                new_trip.append({
                    "day": current_date_str,
                    "location": trip[-1]["location"],
                    "matches": [],
                    "note": "Rest Day",
                    "hotel": hotel_location
                })
                new_routes.append(new_trip)
            initial_routes = new_routes
            continue

        # Process each potential trip route
        for trip in initial_routes:
            try:
                # Get current locations from trip for route planning
                current_locations = {day.get("location", start_location) for day in trip}
                
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
                new_trip = copy.deepcopy(trip)
                hotel_location = trip[-1]["hotel"]
                new_trip.append({
                    "day": current_date_str,
                    "location": trip[-1]["location"],
                    "matches": [],
                    "note": "Rest Day (Skipped Match)",  # Note that we skipped available matches
                    "hotel": hotel_location
                })
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
                        new_trip = copy.deepcopy(trip)
                        new_trip.append({
                            "day": current_date_str,
                            "location": location,
                            "matches": [best_option],
                            "note": "",
                            "hotel": location
                        })
                        new_routes.append(new_trip)
                    
                    # Add alternate routes from different starting points
                    from_locations = {best_option["travel_from"]}
                    for option in options:
                        if option["travel_from"] not in from_locations and is_efficient_route(trip, location, trip_locations):
                            from_locations.add(option["travel_from"])
                            new_trip = copy.deepcopy(trip)
                            new_trip.append({
                                "day": current_date_str,
                                "location": location,
                                "matches": [option],
                                "note": "",
                                "hotel": location
                            })
                            new_routes.append(new_trip)
                
            except Exception:
                # Add rest day as fallback if error occurs
                try:
                    new_trip = copy.deepcopy(trip)
                    hotel_location = trip[-1]["hotel"]
                    new_trip.append({
                        "day": current_date_str,
                        "location": trip[-1]["location"],
                        "matches": [],
                        "note": "Rest Day (Error Recovery)",
                        "hotel": hotel_location
                    })
                    new_routes.append(new_trip)
                except:
                    continue

        initial_routes = new_routes

    # Filter trips based on having matches
    all_trips = [trip for trip in initial_routes 
                if sum(len(day.get("matches", [])) > 0 for day in trip) >= 2]
    
    # Filter trips to include only those with required teams
    if must_teams_lower and all_trips:
        all_trips = [
            trip for trip in all_trips
            if any(match.get("contains_must_team", False) 
                  for day in trip 
                  for match in day.get("matches", []))
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
    key=lambda d: datetime.strptime(d + " 2025", "%d %B %Y")
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
    if not all_trips and tbd_games_in_period:
        return {"no_trips_available": True, "TBD_Games": tbd_games_in_period, "actual_start_date": actual_start_date}
    
    if not all_trips:
        return {"no_trips_available": True, "actual_start_date": actual_start_date}

    if tbd_games_in_period:
        return {
            "trips": all_trips,
            "TBD_Games": tbd_games_in_period,
            "actual_start_date": actual_start_date
        }
    
    return {"trips": all_trips, "actual_start_date": actual_start_date}