import pandas as pd
from datetime import datetime, timedelta
from backend.models import Game
from backend.scrapers.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums
from typing import Optional
import copy

def convert_to_minutes(time_str: str) -> int:
    # Handle empty or None inputs
    if not time_str:
        raise ValueError("Invalid time string: Input is empty or None.")
        
    time_str = time_str.strip()
    
    # Case 1: Both hours and minutes specified (e.g., "5 h 38m")
    if "h" in time_str and "m" in time_str:
        try:
            hours_part = time_str.split("h")[0].strip()
            minutes_part = time_str.split("h")[1].split("m")[0].strip()
            hours = int(hours_part) if hours_part else 0
            minutes = int(minutes_part) if minutes_part else 0
            return (hours * 60) + minutes
        except ValueError:
            raise ValueError(f"Invalid time format: '{time_str}'")
    
    # Case 2: Only hours specified (e.g., "4 h")
    elif "h" in time_str:
        try:
            hours_part = time_str.split("h")[0].strip()
            hours = int(hours_part) if hours_part else 0
            return hours * 60
        except ValueError:
            raise ValueError(f"Invalid hour format: '{time_str}'")
    
    # Case 3: Only minutes specified (e.g., "45m")
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
    df = pd.read_csv(file_path)
    train_times = {}
    for _, row in df.iterrows():
        travel_minutes = convert_to_minutes(row["Fastest Train Time"])
        train_times[(row["From"], row["To"])] = travel_minutes
        train_times[(row["To"], row["From"])] = travel_minutes
    return train_times

def load_games(file_path: str) -> tuple:
    df = pd.read_csv(file_path, encoding="utf-8", skipinitialspace=True)
    df.columns = df.columns.str.strip()

    games = []
    tbd_games = []  # Separate list for TBD games
    current_year = datetime.now().year  # Ensure we use the correct year

    for _, row in df.iterrows():
        try:
            date_str = row["Date"] + f" {current_year}"  # Append correct year
            date_main = datetime.strptime(date_str, "%d %B %Y")  
            
            game = Game(
                league=row["League"].strip(),
                date=date_main,
                time=row["Time"],
                home_team=row["Home Team"].strip(),
                away_team=row["Away Team"].strip(),
                hbf_location=map_team_to_hbf(row["Home Team"])
            )
            
            # Add to appropriate list based on whether time is TBD
            if str(row["Time"]).lower() == "tbd":
                tbd_games.append(game)
            else:
                games.append(game)
                
        except Exception as e:
            print(f"Error parsing row {row}: {e}")
            continue  # Skip this row instead of raising an error

    return games, tbd_games

def map_team_to_hbf(team_name: str) -> str:
    all_teams = bundesliga_1_stadiums + bundesliga_2_stadiums + third_liga_stadiums
    for team in all_teams:
        if team["team"].lower() == team_name.lower():
            return team["hbf"]["name"]
    return "Unknown"

def identify_similar_trips(sorted_trips):
    """Group trips by the matches they include, ignoring travel routes."""
    trip_groups = []
    
    # Use a dictionary to map signatures to group indices for O(1) lookup
    signature_to_group_index = {}
    
    for trip in sorted_trips:
        # Skip invalid trips early
        if "Itinerary" not in trip:
            continue
        
        # Count matches early to skip empty trips efficiently
        match_count = sum(1 for day in trip["Itinerary"] if day.get("matches"))
        if match_count == 0:
            continue
            
        # Create a match signature for each trip (the games being watched)
        match_signature = []
        for day in trip["Itinerary"]:
            if day.get("matches"):
                for match in day["matches"]:
                    # Store only what's needed for comparison (match name and day)
                    match_signature.append((day.get("day"), match["match"]))
        
        # Convert to tuple for immutability and faster hashing
        match_signature_tuple = tuple(sorted(match_signature))
        
        # Direct dictionary lookup instead of linear search
        group_index = signature_to_group_index.get(match_signature_tuple)
        
        if group_index is not None:
            # Match found - add to existing group
            trip_groups[group_index]["Variations"].append(trip)
        else:
            # No match - create new group
            # Select best hotel strategy as base
            new_group = {"Base": trip, "Variations": [trip]}
            trip_groups.append(new_group)
            
            # Store the index for future lookups
            signature_to_group_index[match_signature_tuple] = len(trip_groups) - 1
    
    return trip_groups

def calculate_total_travel_time(trip):
    """Calculates the total travel time based on the actual travel segments shown in the trip."""
    
    # Find the starting location
    start_location = None
    for day in trip["Itinerary"]:
        if "matches" in day and day["matches"]:
            start_location = day["matches"][0]["travel_from"]
            break
    
    # If no matches found, return 0
    if not start_location:
        return 0
    
    # Keep track of displayed travel segments
    total_time = 0
    current_location = start_location
    travel_segments = []
    
    # Store previous days to refer to when adding return journeys
    previous_days = {}
    previous_match_travel_times = {}
    
    # Pre-process to collect days and travel times for reference
    for day in trip["Itinerary"]:
        if day.get("matches"):
            for match in day["matches"]:
                previous_days[match["location"]] = day["day"]
                previous_match_travel_times[match["location"]] = match.get("travel_time", "0h 0m")
    
    # Process each day in the itinerary
    for day in trip["Itinerary"]:
        for match in day.get("matches", []):
            from_loc = match.get("travel_from", current_location)
            to_loc = match["location"]
            travel_time = match.get("travel_time", "0h 0m")
            
            # If travel_from is different from our current location, add an implicit journey
            if from_loc != current_location:
                # This is an implicit journey to get to the starting point of the next explicit journey
                implicit_travel_time = previous_match_travel_times.get(current_location, travel_time)
                
                # Add this segment to our list and calculate time
                travel_segments.append((current_location, from_loc, implicit_travel_time))
                
                if implicit_travel_time != "Unknown":  # Skip unknown times
                    try:
                        hours, minutes = map(int, implicit_travel_time.replace("h", "").replace("m", "").split())
                        total_time += (hours * 60) + minutes
                    except:
                        pass  # Handle any parsing errors gracefully
                        
                # Update current location
                current_location = from_loc
            
            # Add the explicit journey to the match location
            travel_segments.append((from_loc, to_loc, travel_time))
            
            if travel_time != "Unknown":  # Skip unknown times
                try:
                    hours, minutes = map(int, travel_time.replace("h", "").replace("m", "").split())
                    total_time += (hours * 60) + minutes
                except:
                    pass  # Handle any parsing errors gracefully
                    
            # Update current location to where we end up
            current_location = to_loc
    
    return total_time

def get_reachable_games(locations: list, games: list, train_times: dict, max_travel_time: int, current_date: datetime):
    """
    Find games reachable within max_travel_time from any of the provided locations.
    Optimized for performance while maintaining the same functionality.
    """
    #  Early return for empty inputs
    if not locations or not games:
        return []
        
    # Convert date to date object once to avoid repeated conversions
    current_date_only = current_date.date()
    
    # Pre-filter games by date with direct attribute access
    # This avoids repeated date.date() calls in the list comprehension
    todays_games = []
    for game in games:
        if hasattr(game, 'date') and game.date.date() == current_date_only:
            todays_games.append(game)
    
    # Early return if no games today
    if not todays_games:
        return []
    
    # Use set for faster lookup of locations (if there are duplicates)
    # Convert to set immediately to avoid repeated conversions
    unique_locations = set(locations)
    
    # Pre-allocate results list with estimated capacity
    # This avoids multiple list reallocations
    estimated_capacity = min(len(unique_locations) * len(todays_games), 100)
    reachable = []
    reachable.reserve = lambda x: None  # Dummy function for non-CPython implementations
    try:
        reachable.reserve(estimated_capacity)  # This is a CPython optimization
    except:
        pass
    
    # Pre-fetch hbf_locations to avoid repeated attribute access
    game_locations = [(game, game.hbf_location) for game in todays_games if hasattr(game, 'hbf_location')]
    
    # Process each location with game pairs efficiently
    for loc in unique_locations:
        # Process in bulk with direct dictionary access
        for game, game_location in game_locations:
            # Direct dictionary lookup with default
            travel_time = train_times.get((loc, game_location), float("inf"))
            if travel_time <= max_travel_time:
                reachable.append({
                    "game": game,
                    "from": loc,
                    "travel_time": travel_time
                })
    # Uncomment if needed: reachable.sort(key=lambda x: x["travel_time"])
    
    return reachable

def is_efficient_route(new_trip, new_location, trip_locations):
    """Check if adding this location creates an efficient route"""
    # Avoid backtracking (A → B → A pattern)
    if len(trip_locations) >= 2:
        last = trip_locations[-1]
        second_last = trip_locations[-2]
        if new_location == second_last and last != second_last:
            return False
    
    # Avoid unnecessary detours when staying in a location
    if len(trip_locations) >= 1 and trip_locations[-1] == new_location:
        # No need to create a separate route for staying in the same place
        has_match_today = any(len(day.get("matches", [])) > 0 for day in new_trip[-1:])
        if not has_match_today:
            return False
    
    return True

def filter_best_variations_by_hotel_changes(trips):
    """
    For each distinct trip (same matches), show only the fastest route per number of hotel changes
    E.g., top 1 for 0 changes, top 1 for 1 change, etc.
    """
    # Group trips by match signature
    trip_groups = {}
    
    for trip in trips:
        # Create match signature based on the games attended
        match_signature = []
        for day in trip:
            if isinstance(day, dict) and "matches" in day:
                for match in day["matches"]:
                    # Store a tuple of (day, match) to preserve order
                    match_signature.append((day.get("day", ""), match.get("match", "")))
        
        # Convert to tuple for immutability to use as dict key
        signature = tuple(sorted(match_signature))
        
        if signature not in trip_groups:
            trip_groups[signature] = []
            
        trip_groups[signature].append(trip)
    
    # For each trip group, get the fastest route per hotel change count
    filtered_trips = []
    
    for trip_list in trip_groups.values():
        # Group by hotel change count
        by_change_count = {}
        
        for trip in trip_list:
            # Find the hotel stats dict (last element)
            hotel_stats = next((item for item in trip if isinstance(item, dict) and 
                              "hotel_changes" in item), {"hotel_changes": 0})
                
            change_count = hotel_stats.get("hotel_changes", 0)
            
            if change_count not in by_change_count:
                by_change_count[change_count] = []
                
            # Calculate total travel time if not already present
            travel_time = 0
            for day in trip:
                if isinstance(day, dict) and "matches" in day:
                    for match in day["matches"]:
                        if "travel_time" in match and match["travel_time"] != "Unknown":
                            try:
                                time_parts = match["travel_time"].split('h ')
                                hours = int(time_parts[0])
                                minutes = int(time_parts[1].replace('m', ''))
                                travel_time += (hours * 60) + minutes
                            except:
                                pass
            
            by_change_count[change_count].append((travel_time, trip))
        
        # Get the fastest trip per hotel change count
        for change_count, trip_list in by_change_count.items():
            if trip_list:
                # Sort by travel time and pick the fastest
                fastest_trip = min(trip_list, key=lambda x: x[0])[1]
                filtered_trips.append(fastest_trip)
    
    return filtered_trips

def optimize_trip_variations(base_trip, train_times, max_travel_time):
    """
    Generate optimized variations of a trip with different hotel strategies
    without filtering out any trips - just creates better variations.
    """
    variations = []
    match_locations = []
    
    # Extract match locations from the base trip
    for day in base_trip:
        if day.get("matches"):
            for match in day.get("matches", []):
                location = match.get("location")
                if location:
                    match_locations.append(location)
    
    # Skip optimization if no matches
    if not match_locations:
        return [base_trip]
    
    # Strategy 1: Match-based strategy (default - stay where each match is)
    # This is already in the base trip, but we'll create a clean copy
    match_based = copy.deepcopy(base_trip)
    variations.append(match_based)
    
    # Ignore last element which might be hotel stats
    trip_days = [day for day in base_trip if isinstance(day, dict) and "day" in day]
    
    # Strategy 2: Single-base strategy (stay in one place for the whole trip)
    central_locations = find_central_locations(trip_days, match_locations, train_times, max_travel_time)
    
    for central in central_locations[:3]:  # Limit to top 3 central locations for efficiency
        single_base = create_single_base_variation(trip_days, central, train_times)
        if single_base:
            variations.append(single_base)
    
    # Strategy 3: Pivot-based strategy (change hotel at optimal points)
    if len(match_locations) >= 3:  # Only for trips with enough matches
        pivot_variations = create_pivot_variations(trip_days, match_locations, train_times, max_travel_time)
        variations.extend(pivot_variations)
    
    return variations

def find_central_locations(trip_days, match_locations, train_times, max_travel_time):
    """
    Find central locations that minimize total travel time
    Returns locations sorted by suitability as a central base
    """
    unique_locations = list(set(match_locations))
    
    # Score each location by total travel time to all matches
    location_scores = []
    
    for base_loc in unique_locations:
        total_time = 0
        viable = True
        
        # Check if every match is reachable within max_travel_time (round trip)
        for match_loc in match_locations:
            if match_loc == base_loc:
                continue  # No travel needed
                
            # Check outbound journey
            outbound_time = train_times.get((base_loc, match_loc), float("inf"))
            # Check return journey
            return_time = train_times.get((match_loc, base_loc), float("inf"))
            
            # If either journey exceeds max time, this location isn't viable
            if outbound_time > max_travel_time or return_time > max_travel_time:
                viable = False
                break
                
            # Add round-trip time
            total_time += outbound_time + return_time
        
        # Only add viable locations
        if viable:
            location_scores.append((total_time, base_loc))
    
    # Sort by total travel time
    location_scores.sort()
    return [loc for _, loc in location_scores]

def create_single_base_variation(trip_days, central_location, train_times):
    """
    Create variation where you stay in one place for the entire trip
    """
    variation = []
    
    for day in trip_days:
        day_copy = copy.deepcopy(day)
        
        # Set hotel to central location for every day
        day_copy["hotel"] = central_location
        
        # Update travel times for matches
        if day_copy.get("matches"):
            for match in day_copy["matches"]:
                # If traveling from central location to match location
                if match["location"] != central_location:
                    # Find travel time from central location
                    travel_time = train_times.get((central_location, match["location"]), float("inf"))
                    if travel_time != float("inf"):
                        travel_hours = travel_time // 60
                        travel_mins = travel_time % 60
                        match["travel_from"] = central_location
                        match["travel_time"] = f"{travel_hours}h {travel_mins}m"
                else:
                    # Same location - set travel time to 0
                    match["travel_from"] = central_location
                    match["travel_time"] = f"0h 0m"
        
        variation.append(day_copy)
    
    return variation

def create_pivot_variations(trip_days, match_locations, train_times, max_travel_time):
    """
    Create variations with strategic hotel changes at optimal points
    """
    variations = []
    
    # For simplicity, we'll try pivot points at 1/3 and 2/3 of the trip
    trip_length = len(trip_days)
    if trip_length < 6:  # Not worth pivoting for short trips
        return variations
        
    pivot_points = [trip_length // 3, (trip_length * 2) // 3]
    
    # Find potential pivot locations (matches on or near pivot days)
    unique_locations = list(set(match_locations))
    
    # Try each combination of 2 locations as hotel bases for a 2-segment trip
    for loc1 in unique_locations:
        for loc2 in unique_locations:
            if loc1 == loc2:
                continue
                
            # Create a pivoted variation
            variation = []
            pivot_idx = pivot_points[0]
            
            for i, day in enumerate(trip_days):
                day_copy = copy.deepcopy(day)
                
                # First segment uses loc1, second segment uses loc2
                hotel_loc = loc1 if i < pivot_idx else loc2
                day_copy["hotel"] = hotel_loc
                
                # Update travel times for matches
                if day_copy.get("matches"):
                    for match in day_copy["matches"]:
                        if match["location"] != hotel_loc:
                            travel_time = train_times.get((hotel_loc, match["location"]), float("inf"))
                            if travel_time != float("inf"):
                                travel_hours = travel_time // 60
                                travel_mins = travel_time % 60
                                match["travel_from"] = hotel_loc
                                match["travel_time"] = f"{travel_hours}h {travel_mins}m"
                
                variation.append(day_copy)
            
            # Check if all travel times are within max_travel_time
            valid_variation = True
            for day in variation:
                if day.get("matches"):
                    for match in day["matches"]:
                        if "travel_time" in match:
                            try:
                                time_parts = match["travel_time"].split('h ')
                                hours = int(time_parts[0])
                                minutes = int(time_parts[1].replace('m', ''))
                                travel_mins = (hours * 60) + minutes
                                if travel_mins > max_travel_time:
                                    valid_variation = False
                                    break
                            except:
                                pass
                if not valid_variation:
                    break
            
            if valid_variation:
                variations.append(variation)
    
    return variations

def plan_trip(start_location: str, trip_duration: int, max_travel_time: int, games: list, train_times: dict, 
             tbd_games: list = None, preferred_leagues: list = None, start_date: Optional[str] = None, must_teams: Optional[list] = None):    
    # Pre-allocate lists with appropriate capacity
    all_trips = []
    tbd_games_in_period = []
    valid_tbd_games = []  # Initialize this variable
    current_year = datetime.now().year
    actual_start_date = None  # Initialize variable
    
    # Helper function for precise team matching
    def is_must_team_match(team_name, must_teams_set):
        """Precisely match team names without catching reserve teams"""
        if not must_teams_set:
            return False
            
        team_name_lower = team_name.lower()
        
        # Check for reserve team indicators in the team name
        is_reserve_team = any(suffix in team_name_lower for suffix in 
                             [" ii", " 2", " u23", " u21", " u19", " amateure"])
        
        for must_team in must_teams_set:
            # Is the must_team specifically looking for a reserve team?
            is_must_reserve = any(suffix in must_team for suffix in 
                                [" ii", " 2", " u23", " u21", " u19", " amateure"])
            
            # Exact match
            if must_team == team_name_lower:
                return True
                
            # If must_team isn't specifically for reserves, but team_name is a reserve team,
            # and the base name matches, then DON'T match
            if not is_must_reserve and is_reserve_team:
                # Extract the base name (without the reserve indicator)
                base_team = team_name_lower
                for suffix in [" ii", " 2", " u23", " u21", " u19", " amateure"]:
                    base_team = base_team.replace(suffix, "")
                base_team = base_team.strip()
                
                # If the base name matches the must_team, don't match
                if base_team == must_team:
                    continue
            
            # Regular matching (only if we haven't determined it's an unwanted reserve match)
            if must_team in team_name_lower and (
                team_name_lower.startswith(must_team) or
                team_name_lower.endswith(must_team) or
                f" {must_team} " in f" {team_name_lower} "
            ):
                return True
        
        return False
    
    # Create lookup set for preferred leagues once for filtering
    preferred_leagues_lower = set(league.lower() for league in preferred_leagues) if preferred_leagues else None
    
    # Use more direct date parsing with error handling
    if start_date:
        try:
            parsed_date = datetime.strptime(f"{start_date} {current_year}", "%d %B %Y")
            start_date = parsed_date
            actual_start_date = parsed_date.strftime("%d %B")  # Format it for display
        except ValueError:
            return {"error": "Invalid start date format. Use '28 March' format."}
    else:
        # Find the earliest game date instead of using current date
        earliest_date = None
        
        # Find earliest game that matches filters
        for game in games:
            # Skip games that don't match preferred leagues
            if preferred_leagues_lower and hasattr(game, 'league') and game.league.lower() not in preferred_leagues_lower:
                continue
                
            # Skip games without required attributes
            if not (hasattr(game, 'date') and hasattr(game, 'hbf_location')):
                continue
                
            # Skip games that are in the past
            if game.date.date() < datetime.now().date():
                continue
                
            # Track earliest valid game date
            if earliest_date is None or game.date < earliest_date:
                earliest_date = game.date
                
        # Use earliest date if found, otherwise fall back to today
        if earliest_date:
            start_date = earliest_date
            # Store the formatted date string for display
            actual_start_date = earliest_date.strftime("%d %B")
        else:
            start_date = datetime.now()
            actual_start_date = start_date.strftime("%d %B")
    
    # Combined validation loops for games and tbd_games
    # Pre-compute trip end date used for filtering
    trip_end_date = start_date + timedelta(days=trip_duration)
    
    # Convert must_teams to lowercase for case-insensitive comparison
    must_teams_lower = set(team.lower() for team in must_teams) if must_teams else None
    
    #  Faster validation with list comprehensions instead of loops
    valid_games = [
        g for g in games 
        if hasattr(g, 'league') and hasattr(g, 'date') and hasattr(g, 'hbf_location') and 
        (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
    ]
    
    # Process TBD games in one pass
    if tbd_games:
        # Pre-compute potential locations set for faster lookups
        potential_locations = {start_location}
        for g in valid_games:
            potential_locations.add(g.hbf_location)
            
        # Process each TBD game once with combined validation
        for tbd_game in tbd_games:
            try:
                # Skip games without required attributes
                if not (hasattr(tbd_game, 'league') and hasattr(tbd_game, 'date') and hasattr(tbd_game, 'hbf_location')):
                    continue
                
                # Skip games not in preferred leagues
                if preferred_leagues_lower and tbd_game.league.lower() not in preferred_leagues_lower:
                    continue
                    
                valid_tbd_games.append(tbd_game)
                
                # Skip games outside trip duration
                if not (start_date.date() <= tbd_game.date.date() < trip_end_date.date()):
                    continue
                
                # Check if a must_team is present in the TBD game - using precise matching
                tbd_match_contains_must_team = False
                if must_teams_lower:
                    tbd_match_contains_must_team = (
                        is_must_team_match(tbd_game.home_team, must_teams_lower) or
                        is_must_team_match(tbd_game.away_team, must_teams_lower)
                    )
                
                # Check travel time efficiently
                for potential_loc in potential_locations:
                    travel_time = train_times.get((potential_loc, tbd_game.hbf_location), float("inf"))
                    if travel_time <= max_travel_time:
                        # Format date string once
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
    
    # Pre-compute full date range as list
    full_date_range = [start_date + timedelta(days=i) for i in range(trip_duration)]
    date_strings = [d.strftime("%d %B") for d in full_date_range]
    
    # Better "Any" location handling
    if start_location.lower() == "any":
        try:
            # Use set comprehension for faster unique location collection
            all_hbfs = {g.hbf_location for g in valid_games if g.hbf_location != "Unknown"}
                
            if all_hbfs:
                reachable_counts = {}
                for city in all_hbfs:
                    # OPTIMIZATION: Count reachable games without creating full lists
                    count = sum(1 for g in valid_games 
                               if g.date.date() == start_date.date() and
                               train_times.get((city, g.hbf_location), float("inf")) <= max_travel_time)
                    reachable_counts[city] = count
                
                best_start = max(all_hbfs, key=lambda city: reachable_counts.get(city, 0))
                start_location = best_start if best_start else "Unknown"
            else:
                start_location = "Unknown"
        except Exception:
            start_location = "Unknown"

    # Create initial route
    # Pre-format start date string
    start_day_str = date_strings[0]
    initial_routes = [[{"day": start_day_str, "location": start_location, "matches": [], "note": "Start", "hotel": start_location}]]

    # Process each date in sequence with more efficient data structures
    for date_idx, current_date in enumerate(full_date_range):
        current_date_str = date_strings[date_idx]
        new_routes = []

        # Filter games for current date
        current_date_games = [g for g in valid_games if g.date.date() == current_date.date()]
        
        # Skip expensive reachability check if no games today
        if not current_date_games:
            for trip in initial_routes:
                new_trip = copy.deepcopy(trip)
                # Stay in the same hotel for rest days
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

        for trip in initial_routes:
            try:
                # Use set for faster lookups of current locations
                current_locations = {day.get("location", start_location) for day in trip}
                
                # Group reachable games by location to avoid redundant trip paths
                reachable_by_location = {}
                
                for loc in current_locations:
                    for game in current_date_games:
                        travel_time = train_times.get((loc, game.hbf_location), float("inf"))
                        if travel_time <= max_travel_time:
                            # Format travel time once
                            travel_time_str = f"{travel_time // 60}h {travel_time % 60}m"
                            match_str = f"{game.home_team} vs {game.away_team} ({game.time})"
                            
                            # Track if this match contains a must_team - using precise matching
                            contains_must_team = False
                            if must_teams_lower:
                                contains_must_team = (
                                    is_must_team_match(game.home_team, must_teams_lower) or
                                    is_must_team_match(game.away_team, must_teams_lower)
                                )
                            
                            # Group by location for more efficient processing
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
                    # Stay in the same hotel for rest days
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
                
                # Create minimum necessary copies and only deepcopy once per trip
                for location, options in reachable_by_location.items():
                    # Select best option from each location (shortest travel time)
                    best_option = min(options, key=lambda o: train_times.get((o["travel_from"], o["location"]), float("inf")))
                    
                    # Get trip locations for efficiency checking
                    trip_locations = [day.get("location") for day in trip if "location" in day]
                    
                    # Apply efficiency filter using the is_efficient_route function
                    if is_efficient_route(trip, location, trip_locations):
                        new_trip = copy.deepcopy(trip)
                        # Set hotel at match location for game days
                        new_trip.append({
                            "day": current_date_str,
                            "location": location,
                            "matches": [best_option],
                            "note": "",
                            "hotel": location
                        })
                        new_routes.append(new_trip)
                    
                    # Add additional options only if they're from different starting points
                    # AND they create efficient routes
                    from_locations = {best_option["travel_from"]}
                    for option in options:
                        if option["travel_from"] not in from_locations:
                            # Only add if the route is efficient
                            if is_efficient_route(trip, location, trip_locations):
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
                # If there's an error, add a rest day as fallback
                try:
                    new_trip = copy.deepcopy(trip)
                    # Stay in the same hotel for error recovery days
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
                    # Worst case - skip this trip path entirely
                    continue

        initial_routes = new_routes

    # Filter trips based on having matches
    all_trips = [trip for trip in initial_routes 
                if any(len(day.get("matches", [])) > 0 for day in trip)]
    
    # Filter trips that must include specified teams (if must_teams is provided)
    if must_teams_lower and all_trips:
        filtered_trips = []
        for trip in all_trips:
            # Check if this trip contains at least one match with a must_team
            contains_must_team = False
            for day in trip:
                for match in day.get("matches", []):
                    if match.get("contains_must_team", False):
                        contains_must_team = True
                        break
                if contains_must_team:
                    break
            
            # Only keep this trip if it contains at least one must_team
            if contains_must_team:
                filtered_trips.append(trip)
        
        # Update all_trips with filtered list
        all_trips = filtered_trips

    optimized_trips = []
    for original_trip in all_trips:
        # Filter out hotel stats dictionary if present
        trip_without_stats = [day for day in original_trip if isinstance(day, dict) and "day" in day]
        
        # Generate variations with different hotel stay strategies
        variations = optimize_trip_variations(trip_without_stats, train_times, max_travel_time)
        for var in variations:
            # Skip duplicates
            variation_key = tuple((day["day"], tuple(sorted((m["match"] for m in day.get("matches", [])))))
                             for day in var if "day" in day)
            optimized_trips.append(var)
    
    # Use optimized trips instead of original
    all_trips = optimized_trips

    # Calculate hotel statistics for each trip
    for trip in all_trips:
        # Extract hotel info for each trip
        hotel_stays = []
        hotel_locations = set()  # Use a set for faster lookups and unique values
        previous_hotel = None
        hotel_changes = 0
        
        # First collect all hotel stays during the trip
        for i, day in enumerate(trip):
            current_date = day.get("day")
            current_hotel = day.get("hotel")
            
            if current_hotel:
                # If this is a new hotel different from the previous one, count a change
                if previous_hotel and current_hotel != previous_hotel:
                    hotel_changes += 1
                
                # Keep track of hotel location
                hotel_locations.add(current_hotel)
                
                # Find or update existing stay
                if not hotel_stays or hotel_stays[-1]["location"] != current_hotel:
                    # Start a new stay
                    hotel_stays.append({
                        "location": current_hotel,
                        "check_in_date": current_date,
                        "nights": 1
                    })
                else:
                    # Continue current stay
                    hotel_stays[-1]["nights"] += 1
                
                # Update previous hotel
                previous_hotel = current_hotel
        
        # Generate detailed hotel stay information
        hotel_details = []
        for i, day in enumerate(trip[:-1]):  # Skip the last element which will be our hotel stats
            day_date = day.get("day")
            hotel_location = day.get("hotel", "Unknown")
            
            hotel_details.append({
                "date": day_date,
                "location": hotel_location,
                "is_change": i > 0 and hotel_location != trip[i-1].get("hotel")
            })
        
        # Add hotel stats to the trip
        trip_hotel_stats = {
            "hotel_changes": hotel_changes,
            "unique_hotels": len(hotel_locations),
            "hotel_locations": list(hotel_locations),  # Convert set back to list
            "hotel_stays": hotel_stays,
            "hotel_details": hotel_details
        }
        
        # Attach the stats to the trip
        trip.append(trip_hotel_stats)
    
    # If we have TBD games but no valid trips, return TBD games without error
    if not all_trips and tbd_games_in_period:
        return {"no_trips_available": True, "TBD_Games": tbd_games_in_period, "actual_start_date": actual_start_date}
    
    # If we have neither valid trips nor TBD games, return empty trip list
    if not all_trips:
        return {"no_trips_available": True, "actual_start_date": actual_start_date}

    # Filter trips to show only the top result per hotel change count
    all_trips = filter_best_variations_by_hotel_changes(all_trips)
    
    # If we have TBD games but no valid trips, return TBD games without error
    if not all_trips and tbd_games_in_period:
        return {"no_trips_available": True, "TBD_Games": tbd_games_in_period, "actual_start_date": actual_start_date}
    
    # If we have neither valid trips nor TBD games, return empty trip list
    if not all_trips:
        return {"no_trips_available": True, "actual_start_date": actual_start_date}

    # Add TBD games to the response if available
    if tbd_games_in_period:
        # Create a structured response with trips and TBD games
        return {
            "trips": all_trips,
            "TBD_Games": tbd_games_in_period,
            "actual_start_date": actual_start_date
        }
    
    return {"trips": all_trips, "actual_start_date": actual_start_date}