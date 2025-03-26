import pandas as pd
from datetime import datetime, timedelta
from backend.models import Game
from backend.scrapers.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums
from typing import Optional, List, Dict, Tuple
import copy
from backend.config import TRAIN_TIMES_FILE

def get_travel_minutes_utils(train_times: Dict, from_loc: str, to_loc: str) -> Optional[int]:
    """Get travel time between locations, handling missing data and same-location"""
    # Return 0 for same location
    if from_loc == to_loc:
        return 0
    
    # Try direct lookup
    minutes = train_times.get((from_loc, to_loc))
    if minutes is not None:
        return minutes
    
    # Some stations like Leverkusen Mitte shouldn't have hbf appended
    special_suffixes = ["Mitte", "süd", "nord", "ost", "west", "hbf", "Bahnhof"]
    
    # Only try adding hbf if no special suffix already exists
    from_has_suffix = any(suffix in from_loc.lower() for suffix in special_suffixes)
    to_has_suffix = any(suffix in to_loc.lower() for suffix in special_suffixes)
    
    # Try with hbf suffix for 'from' location if appropriate
    if not from_has_suffix:
        minutes = train_times.get((from_loc + " hbf", to_loc))
        if minutes is not None:
            return minutes
    
    # Try with hbf suffix for 'to' location if appropriate
    if not to_has_suffix:
        minutes = train_times.get((from_loc, to_loc + " hbf"))
        if minutes is not None:
            return minutes
    
    # Try with hbf suffix for both locations if appropriate
    if not from_has_suffix and not to_has_suffix:
        minutes = train_times.get((from_loc + " hbf", to_loc + " hbf"))
        if minutes is not None:
            return minutes
    
    # Try removing hbf from both locations
    from_clean = from_loc.replace(" hbf", "")
    to_clean = to_loc.replace(" hbf", "")
    minutes = train_times.get((from_clean, to_clean))
    if minutes is not None:
        return minutes
    
    # Try reverse direction (sometimes train_times only has one direction)
    minutes = train_times.get((to_loc, from_loc))
    if minutes is not None:
        return minutes
    
    # Not found
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

def calculate_total_travel_time(trip: Dict, train_times_param: Dict = None) -> int:
    """Calculate the total travel time for a trip based on actual travel segments."""
    # Use the provided train_times parameter or fall back to the global variable
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
    
    # Second pass: calculate travel time based on daily movements
    sorted_days = sorted([d for d in days if isinstance(d, dict) and d.get("day")], 
                        key=lambda x: x.get("day", ""))
    
    previous_hotel = None
    
    for day in sorted_days:
        day_str = day.get("day")
        current_hotel = day.get("hotel")
        
        if not current_hotel:
            continue
        
        # 1. Add hotel change travel if hotel changed
        if previous_hotel and current_hotel != previous_hotel:
            hotel_change_time = get_travel_minutes_utils(train_times_to_use, previous_hotel, current_hotel) or 0
            total_minutes += hotel_change_time
        
        # 2. Add match travel (outbound and return)
        match_location = match_by_day.get(day_str)
        if match_location and match_location != current_hotel:
            # Travel to match
            match_travel_time = get_travel_minutes_utils(train_times_to_use, current_hotel, match_location) or 0
            total_minutes += match_travel_time
            
            # Return from match
            total_minutes += match_travel_time
        
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
                travel_time = train_times.get((loc, game.hbf_location), float("inf"))
                if travel_time <= max_travel_time:
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
    
    # Avoid unnecessary detours when staying in a location
    if len(trip_locations) >= 1 and trip_locations[-1] == new_location:
        has_match_today = any(len(day.get("matches", [])) > 0 for day in new_trip[-1:])
        if not has_match_today:
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
    """
    variation = copy.deepcopy(base_trip)
    is_valid = True
    
    # First ensure every day has a hotel value, including the first day
    if variation and isinstance(variation[0], dict):
        if not variation[0].get("hotel"):
            # Set the first day's hotel to its location or hotel_base
            variation[0]["hotel"] = variation[0].get("location", hotel_base)
    
    # First pass: Set hotel locations
    for i, day in enumerate(variation):
        # Skip days before start_idx or preserve first day if needed
        if i < start_idx or (i == 0 and preserve_first_day):
            continue
            
        current_loc = day.get("location")
        
        # For rest days, always use hotel_base
        if not day.get("matches"):
            day["hotel"] = hotel_base
            continue
        
        # For match days, check travel feasibility from hotel base
        # Special case when match is at the same location as hotel
        if current_loc == hotel_base:
            day["hotel"] = hotel_base
            continue
            
        # Check if travel to/from hotel_base is feasible with train_times
        travel_time = train_times.get((hotel_base, current_loc), float("inf"))
        return_time = train_times.get((current_loc, hotel_base), float("inf"))
        
        if travel_time <= max_travel_time and return_time <= max_travel_time:
            # Feasible to stay at hotel_base
            day["hotel"] = hotel_base
        else:
            # Must stay at match location instead
            day["hotel"] = current_loc
    
    # Second pass: Update travel segments based on hotel locations
    for i, day in enumerate(variation):
        # Skip first day (no travel to first day)
        if i == 0:
            continue
            
        if day.get("matches"):
            current_match_loc = day.get("location")
            previous_hotel = variation[i-1].get("hotel")
            current_hotel = day.get("hotel")
            
            # Calculate hotel-to-match travel time
            travel_time = train_times.get((previous_hotel, current_match_loc), float("inf"))
            
            # If travel time exceeds max_travel_time, variation is invalid
            if travel_time > max_travel_time:
                is_valid = False
                break
                
            # Update match travel information
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
            transition_time = train_times.get((prev_hotel, curr_hotel), float("inf"))
            if transition_time > max_travel_time:
                is_valid = False
                break
    
    return variation if is_valid else None

def optimize_trip_variations(base_trip: list, train_times: dict, max_travel_time: int) -> list:
    """
    Generate optimized variations of a trip with different hotel strategies,
    ensuring all travel segments are feasible.
    
    Args:
        base_trip: Base trip itinerary
        train_times: Dictionary mapping (from, to) tuples to travel times in minutes
        max_travel_time: Maximum allowed travel time in minutes
        
    Returns:
        List of trip variations with different hotel strategies
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
    
    for city in all_train_cities:
        # Only consider cities reachable from all match locations
        if all(train_times.get((city, match_loc), float("inf")) <= max_travel_time 
              for match_loc in match_locations):
            potential_hotel_locations.add(city)
    
    # Strategy 1: Generate single-base variations (stay in same hotel throughout)
    for hotel_base in potential_hotel_locations:
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
            
            # First hotel bases: either at first match or reachable from all first segment matches
            potential_first_hotels = set(first_segment_matches)
            for city in all_train_cities:
                if all(train_times.get((city, loc), float("inf")) <= max_travel_time 
                      for loc in first_segment_matches):
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
    
    return variations

def filter_best_variations_by_hotel_changes(trips: list, train_times: dict = None) -> list:
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
        pareto_trips = filter_pareto_optimal_trips(best_by_changes)
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
                        travel_time = train_times.get((loc, game.hbf_location), float("inf"))
                        if travel_time <= max_travel_time:
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
                
                # If no reachable games, add a rest day
                if not reachable_by_location:
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
                if any(len(day.get("matches", [])) > 0 for day in trip)]
    
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
        variations = optimize_trip_variations(trip_without_stats, train_times, max_travel_time)
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
        
        # First organize days by date, keeping only the last entry for each date
        # (the last entry represents where the traveler actually stays that night)
        days_by_date = {}
        for day in trip:
            if isinstance(day, dict) and day.get("day") and day.get("hotel"):
                days_by_date[day.get("day")] = day
        
        # Sort days chronologically
        sorted_dates = sorted(days_by_date.keys(), 
                            key=lambda d: datetime.strptime(d + " 2025", "%d %B %Y"))
        
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
    all_trips = filter_best_variations_by_hotel_changes(all_trips, train_times)
    
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