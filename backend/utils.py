import pandas as pd
from datetime import datetime, timedelta
from backend.models import Game
from scrapers.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums
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
    
    for trip_idx, trip in enumerate(sorted_trips):
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
                    # Store only what's needed for comparison
                    match_signature.append((day.get("day"), match["match"]))
        
        # Convert to tuple for immutability and faster hashing
        match_signature_tuple = tuple(sorted(match_signature))  # Sort to ensure consistent ordering
        
        # Direct dictionary lookup instead of linear search
        group_index = signature_to_group_index.get(match_signature_tuple)
        
        if group_index is not None:
            # Match found - add to existing group
            trip_groups[group_index]["Variations"].append(trip)
        else:
            # No match - create new group
            new_group = {"Base": trip, "Variations": [trip]}
            trip_groups.append(new_group)
            trip["Trip Number"] = len(trip_groups)  # Add trip number for identification
            
            # Store the index for future lookups
            signature_to_group_index[match_signature_tuple] = len(trip_groups) - 1
    
    return trip_groups

def calculate_total_travel_time(trip):
    """Calculate total travel time including all segments."""
    total_time = 0
    
    # Check if trip is a list (direct itinerary) or a dict (wrapped itinerary)
    days = trip if isinstance(trip, list) else trip.get("Itinerary", [])
    
    # Simply sum all travel times from all segments - both outbound and return
    for day in days:
        # Add outbound travel time
        if "outbound_travel" in day and day["outbound_travel"] and "time" in day["outbound_travel"]:
            total_time += day["outbound_travel"]["time"]
        
        # Add return travel time
        if "return_travel" in day and day["return_travel"] and "time" in day["return_travel"]:
            total_time += day["return_travel"]["time"]
                
    return total_time

def filter_best_options_by_hotel_changes(all_trips, trip_duration):
    """
    Filter trips to show only the fastest option for each number of hotel changes.
    
    Args:
        all_trips: List of all trip variations
        trip_duration: Maximum number of days in the trip
        
    Returns:
        List containing only the fastest trip for each possible number of hotel changes
    """
    # Group trips by number of hotel changes
    trips_by_changes = {}
    
    for trip in all_trips:
        # Skip incomplete trips
        if not trip or not trip[-1].get("hotel_summary"):
            continue
            
        hotel_changes = trip[-1]["hotel_summary"].get("total_hotel_changes", 0)
        unique_hotels = trip[-1]["hotel_summary"].get("unique_hotels", 0)
        
        # Only include trips where hotel_changes + 1 = unique_hotels
        # This ensures we have exactly one hotel per segment
        if unique_hotels != hotel_changes + 1:
            continue
            
        # Calculate total travel time for this trip
        total_time = calculate_total_travel_time(trip)
        
        # Store trip by hotel changes
        if hotel_changes not in trips_by_changes:
            trips_by_changes[hotel_changes] = (total_time, trip)
        else:
            # Replace if this trip is faster
            current_time, _ = trips_by_changes[hotel_changes]
            if total_time < current_time:
                trips_by_changes[hotel_changes] = (total_time, trip)
    
    # Get the best trip for each number of changes
    filtered_trips = []
    
    # Add trips in order of hotel changes (0 first, then 1, etc.)
    for changes in range(trip_duration):  # Can't have more changes than days
        if changes in trips_by_changes:
            _, best_trip = trips_by_changes[changes]
            filtered_trips.append(best_trip)
    
    return filtered_trips

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

def plan_trip(start_location: str, trip_duration: int, max_travel_time: int, games: list, train_times: dict, 
             tbd_games: list = None, preferred_leagues: list = None, start_date: Optional[str] = None, must_teams: Optional[list] = None):
    """
    Plan a multi-day trip to watch Bundesliga football matches.
    
    Args:
        start_location: Starting city (e.g., "Berlin hbf")
        trip_duration: Number of days for the trip
        max_travel_time: Maximum allowed travel time in minutes
        games: List of Game objects representing all available matches
        train_times: Dictionary mapping (from, to) tuples to travel times in minutes
        tbd_games: Optional list of games with TBD times
        preferred_leagues: Optional list of leagues to filter by
        start_date: Optional start date string (format: "28 March")
        must_teams: Optional list of teams that must be included
        
    Returns:
        Dictionary containing trip options or error information
    """
    # Initialize variables and helper functions
    tbd_games_in_period = []
    current_year = datetime.now().year
    actual_start_date = None
    all_optimized_trips = []
    
    # Convert filtering parameters to lowercase for case-insensitive comparison
    preferred_leagues_lower = set(league.lower() for league in preferred_leagues) if preferred_leagues else None
    must_teams_lower = set(team.lower() for team in must_teams) if must_teams else None
    
    #---------------------------------------------------------------------------
    # HELPER FUNCTIONS
    #---------------------------------------------------------------------------
    
    def is_must_team_match(team_name, must_teams_set):
        """Check if a team matches any must-include team, handling reserve teams properly"""
        if not must_teams_set:
            return False
            
        team_name_lower = team_name.lower()
        is_reserve_team = any(suffix in team_name_lower for suffix in 
                              [" ii", " 2", " u23", " u21", " u19", " amateure"])
        
        for must_team in must_teams_set:
            # Check if must_team is specifically looking for a reserve team
            is_must_reserve = any(suffix in must_team for suffix in 
                                 [" ii", " 2", " u23", " u21", " u19", " amateure"])
            
            # Exact match
            if must_team == team_name_lower:
                return True
                
            # Skip if must_team isn't for reserves but team_name is a reserve team
            if not is_must_reserve and is_reserve_team:
                base_team = team_name_lower
                for suffix in [" ii", " 2", " u23", " u21", " u19", " amateure"]:
                    base_team = base_team.replace(suffix, "")
                
                if base_team.strip() == must_team:
                    continue
            
            # Regular substring matching with word boundaries
            if must_team in team_name_lower and (
                team_name_lower.startswith(must_team) or
                team_name_lower.endswith(must_team) or
                f" {must_team} " in f" {team_name_lower} "
            ):
                return True
        
        return False
    
    def create_hotel_variation(base_trip, hotel_base, start_idx=0, pivot=False):
        """Create a hotel variation using a specific hotel base from a given start index"""
        variation = copy.deepcopy(base_trip)
        is_valid = True
        
        for i, day in enumerate(variation):
            if i < start_idx:  # Skip days before start_idx
                continue
                
            current_loc = day["location"]
            
            # For rest days, use hotel_base
            if not day.get("matches"):
                day["hotel_location"] = hotel_base
                if i > 0:
                    day["hotel_change"] = day["hotel_location"] != variation[i-1]["hotel_location"]
                continue
            
            # For match days, check travel feasibility
            # Special case when match is at the same location as hotel
            if current_loc == hotel_base:
                day["hotel_location"] = hotel_base
                if i > 0:
                    day["hotel_change"] = day["hotel_location"] != variation[i-1]["hotel_location"]
                continue
                
            # Check if travel to/from hotel_base is feasible
            travel_time = train_times.get((hotel_base, current_loc), float("inf"))
            return_time = train_times.get((current_loc, hotel_base), float("inf"))
            
            if travel_time <= max_travel_time and return_time <= max_travel_time:
                # Update outbound travel if needed
                if i > 0 and "outbound_travel" in day:
                    prev_hotel_loc = variation[i-1]["hotel_location"]
                    day["outbound_travel"]["from"] = prev_hotel_loc
                    new_travel_time = train_times.get((prev_hotel_loc, current_loc), float("inf"))
                    
                    if new_travel_time <= max_travel_time:
                        day["outbound_travel"]["time"] = new_travel_time
                    else:
                        # Can't reach match from previous hotel
                        is_valid = False
                        break
                
                # Set hotel location and add return travel
                day["hotel_location"] = hotel_base
                if i > 0:
                    day["hotel_change"] = day["hotel_location"] != variation[i-1]["hotel_location"]
                
                day["return_travel"] = {
                    "from": current_loc,
                    "to": hotel_base,
                    "time": return_time
                }
            else:
                # Must stay at match location
                day["hotel_location"] = current_loc
                if i > 0:
                    day["hotel_change"] = day["hotel_location"] != variation[i-1]["hotel_location"]
        
        # Return the variation only if it's valid
        return variation if is_valid else None
    
    def add_hotel_summary(trip):
        """Add hotel summary statistics to a trip"""
        if not trip:
            return trip
            
        hotel_changes = 0
        hotel_locations = []
        
        for i, day in enumerate(trip):
            if i > 0:  # Skip first day
                if day.get("hotel_location") != trip[i-1].get("hotel_location"):
                    hotel_changes += 1
                    day["hotel_change"] = True
                else:
                    day["hotel_change"] = False
            
            if "hotel_location" in day:
                hotel_city = day["hotel_location"].replace(" hbf", "")
                if hotel_city not in hotel_locations:
                    hotel_locations.append(hotel_city)
        
        # Add summary to the last day
        if trip:
            trip[-1]["hotel_summary"] = {
                "total_hotel_changes": hotel_changes,
                "unique_hotels": len(hotel_locations),
                "hotel_cities": hotel_locations
            }
        
        return trip
    
    def get_trip_signature(trip):
        """Create a unique signature for a trip based on its key attributes"""
        signature_parts = []
        
        for day in trip:
            hotel = day.get("hotel_location", "")
            outbound = tuple(sorted(day.get("outbound_travel", {}).items())) if "outbound_travel" in day else ()
            return_travel = tuple(sorted(day.get("return_travel", {}).items())) if "return_travel" in day else ()
            matches = tuple(sorted((m.get("match", ""), m.get("location", "")) 
                            for m in day.get("matches", [])))
            
            signature_parts.append((hotel, outbound, return_travel, matches))
            
        return tuple(signature_parts)
    
    def get_match_signature(trip):
        """Create a signature based only on matches in a trip"""
        match_sig = []
        for day in trip:
            for match in day.get("matches", []):
                match_sig.append(match.get("match", ""))
        
        return tuple(sorted(match_sig))
    
    #---------------------------------------------------------------------------
    # PHASE 1: SETUP AND DATE PROCESSING
    #---------------------------------------------------------------------------
    
    # Parse and validate start date
    if start_date:
        try:
            parsed_date = datetime.strptime(f"{start_date} {current_year}", "%d %B %Y")
            start_date = parsed_date
            actual_start_date = parsed_date.strftime("%d %B")
        except ValueError:
            return {"error": "Invalid start date format. Use '28 March' format."}
    else:
        # Find the earliest game date that matches filters
        earliest_date = None
        for game in games:
            if (preferred_leagues_lower and hasattr(game, 'league') and 
                game.league.lower() not in preferred_leagues_lower):
                continue
                
            if not (hasattr(game, 'date') and hasattr(game, 'hbf_location')):
                continue
                
            if game.date.date() < datetime.now().date():
                continue
                
            if earliest_date is None or game.date < earliest_date:
                earliest_date = game.date
                
        start_date = earliest_date if earliest_date else datetime.now()
        actual_start_date = start_date.strftime("%d %B")
    
    # Calculate full date range for trip
    trip_end_date = start_date + timedelta(days=trip_duration)
    full_date_range = [start_date + timedelta(days=i) for i in range(trip_duration)]
    date_strings = [d.strftime("%d %B") for d in full_date_range]
    
    #---------------------------------------------------------------------------
    # PHASE 2: FILTER GAMES
    #---------------------------------------------------------------------------
    
    # Filter games by league preference
    valid_games = [
        g for g in games 
        if hasattr(g, 'league') and hasattr(g, 'date') and hasattr(g, 'hbf_location') and 
        (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
    ]
    
    # Further filter games by trip date range
    valid_games_in_period = [
        g for g in valid_games
        if start_date.date() <= g.date.date() < trip_end_date.date()
    ]
    
    # Group games by date for faster lookup
    games_by_date = {}
    for game in valid_games_in_period:
        game_date = game.date.date()
        if game_date not in games_by_date:
            games_by_date[game_date] = []
        games_by_date[game_date].append(game)
    
    # Handle "Any" start location
    if start_location.lower() == "any":
        try:
            all_hbfs = {g.hbf_location for g in valid_games if g.hbf_location != "Unknown"}
                
            if all_hbfs:
                reachable_counts = {}
                for city in all_hbfs:
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
    
    # Process TBD games
    if tbd_games:
        potential_locations = {start_location}.union(g.hbf_location for g in valid_games)
        
        for tbd_game in tbd_games:
            try:
                # Skip games without required attributes or outside preferences
                if not (hasattr(tbd_game, 'league') and hasattr(tbd_game, 'date') and 
                       hasattr(tbd_game, 'hbf_location')):
                    continue
                
                if preferred_leagues_lower and tbd_game.league.lower() not in preferred_leagues_lower:
                    continue
                
                # Skip games outside trip date range
                if not (start_date.date() <= tbd_game.date.date() < trip_end_date.date()):
                    continue
                
                # Check if a must_team is present
                tbd_match_contains_must_team = False
                if must_teams_lower:
                    tbd_match_contains_must_team = (
                        is_must_team_match(tbd_game.home_team, must_teams_lower) or
                        is_must_team_match(tbd_game.away_team, must_teams_lower)
                    )
                
                # Check if game is reachable from any potential location
                for potential_loc in potential_locations:
                    travel_time = train_times.get((potential_loc, tbd_game.hbf_location), float("inf"))
                    if travel_time <= max_travel_time:
                        tbd_games_in_period.append({
                            "match": f"{tbd_game.home_team} vs {tbd_game.away_team}",
                            "date": tbd_game.date.strftime("%d %B"),
                            "location": tbd_game.hbf_location,
                            "league": tbd_game.league,
                            "has_must_team": tbd_match_contains_must_team
                        })
                        break
            except Exception:
                continue
    
    #---------------------------------------------------------------------------
    # PHASE 3: GENERATE INITIAL ROUTES
    #---------------------------------------------------------------------------
    
    # Process first day separately to ensure start location is respected
    first_day_games = games_by_date.get(full_date_range[0].date(), [])
    start_day_str = date_strings[0]
    initial_routes = []
    
    if not first_day_games:
        # No games on first day - start with rest day
        initial_routes = [[{
            "day": start_day_str, 
            "location": start_location, 
            "matches": [], 
            "note": "Rest Day",
            "hotel_location": start_location
        }]]
    else:
        # Process games reachable on first day
        first_day_routes = []
        
        for game in first_day_games:
            travel_time = train_times.get((start_location, game.hbf_location), float("inf"))
            
            if travel_time <= max_travel_time:
                # For matches not at start location, check return feasibility 
                if game.hbf_location != start_location:
                    return_time = train_times.get((game.hbf_location, start_location), float("inf"))
                    if return_time > max_travel_time:
                        continue
                
                # Format travel information
                travel_time_str = f"{travel_time // 60}h {travel_time % 60}m"
                match_str = f"{game.home_team} vs {game.away_team} ({game.time})"
                
                # Check for must-team matches
                contains_must_team = False
                if must_teams_lower:
                    contains_must_team = (
                        is_must_team_match(game.home_team, must_teams_lower) or
                        is_must_team_match(game.away_team, must_teams_lower)
                    )
                
                # Create route with this match
                route = [{
                    "day": start_day_str,
                    "location": game.hbf_location,
                    "matches": [{
                        "match": match_str,
                        "location": game.hbf_location,
                        "date": start_day_str,
                        "travel_from": start_location,
                        "travel_time": travel_time_str,
                        "raw_travel_time": travel_time,
                        "contains_must_team": contains_must_team
                    }],
                    "note": "",
                    "hotel_location": start_location,  # Always stay at start location on first night
                    "outbound_travel": {
                        "from": start_location,
                        "to": game.hbf_location,
                        "time": travel_time
                    }
                }]
                
                # Add return travel if not at start location
                if game.hbf_location != start_location:
                    return_time = train_times.get((game.hbf_location, start_location), float("inf"))
                    route[0]["return_travel"] = {
                        "from": game.hbf_location,
                        "to": start_location,
                        "time": return_time
                    }
                
                first_day_routes.append(route)
        
        # Use first day routes if any found, otherwise start with rest day
        initial_routes = first_day_routes if first_day_routes else [[{
            "day": start_day_str, 
            "location": start_location, 
            "matches": [], 
            "note": "Rest Day",
            "hotel_location": start_location
        }]]
    
    # Generate routes for remaining days (day-by-day expansion)
    for date_idx, current_date in enumerate(full_date_range[1:], start=1):
        current_date_str = date_strings[date_idx]
        new_routes = []
        
        # Get games for current date
        current_date_games = games_by_date.get(current_date.date(), [])
        
        # If no games today, add rest day to all routes
        if not current_date_games:
            for trip in initial_routes:
                new_trip = copy.deepcopy(trip)
                last_location = trip[-1]["location"]
                new_trip.append({
                    "day": current_date_str,
                    "location": last_location,
                    "matches": [],
                    "note": "Rest Day",
                    "hotel_location": last_location
                })
                new_routes.append(new_trip)
            
            initial_routes = new_routes
            continue
        
        # For each existing route, find possible extensions
        for trip in initial_routes:
            # Consider all previous locations for connections
            current_locations = {day.get("location", start_location) for day in trip}
            reachable_by_location = {}
            
            # Find all reachable games from all previous locations
            for loc in current_locations:
                for game in current_date_games:
                    travel_time = train_times.get((loc, game.hbf_location), float("inf"))
                    
                    if travel_time <= max_travel_time:
                        # Format travel info
                        travel_time_str = f"{travel_time // 60}h {travel_time % 60}m"
                        match_str = f"{game.home_team} vs {game.away_team} ({game.time})"
                        
                        # Check if match contains a must-team
                        contains_must_team = False
                        if must_teams_lower:
                            contains_must_team = (
                                is_must_team_match(game.home_team, must_teams_lower) or
                                is_must_team_match(game.away_team, must_teams_lower)
                            )
                        
                        # Group by location
                        if game.hbf_location not in reachable_by_location:
                            reachable_by_location[game.hbf_location] = []
                            
                        reachable_by_location[game.hbf_location].append({
                            "match": match_str,
                            "location": game.hbf_location,
                            "date": current_date_str,
                            "travel_from": loc,
                            "travel_time": travel_time_str,
                            "raw_travel_time": travel_time,
                            "contains_must_team": contains_must_team
                        })
            
            # If no reachable games, add a rest day
            if not reachable_by_location:
                new_trip = copy.deepcopy(trip)
                new_trip.append({
                    "day": current_date_str,
                    "location": trip[-1]["location"],
                    "matches": [],
                    "note": "Rest Day",
                    "hotel_location": trip[-1]["location"]
                })
                new_routes.append(new_trip)
                continue
            
            # For each reachable location, create a new route
            for match_location, options in reachable_by_location.items():
                for option in options:
                    new_trip = copy.deepcopy(trip)
                    new_trip.append({
                        "day": current_date_str,
                        "location": match_location,
                        "matches": [option],
                        "note": "",
                        "hotel_location": match_location,  # Default: stay at match location
                        "outbound_travel": {
                            "from": option["travel_from"],
                            "to": match_location,
                            "time": option["raw_travel_time"]
                        }
                    })
                    new_routes.append(new_trip)
        
        # Update routes for next iteration
        initial_routes = new_routes
    
    #---------------------------------------------------------------------------
    # PHASE 4: GENERATE OPTIMIZED HOTEL VARIATIONS
    #---------------------------------------------------------------------------
    
    # Filter out trips with no matches
    valid_trip_routes = [trip for trip in initial_routes 
                         if any(len(day.get("matches", [])) > 0 for day in trip)]
    
    # Apply must-team filter if specified
    if not valid_trip_routes:
        # No valid routes found
        if tbd_games_in_period:
            return {"no_trips_available": True, "TBD_Games": tbd_games_in_period, "actual_start_date": actual_start_date}
        return {"no_trips_available": True, "actual_start_date": actual_start_date}
    
    # Filter for must-teams if specified
    filtered_trips = valid_trip_routes
    if must_teams_lower:
        filtered_trips = [
            trip for trip in valid_trip_routes
            if any(match.get("contains_must_team", False) 
                  for day in trip 
                  for match in day.get("matches", []))
        ]
        
        if not filtered_trips:
            # No trips with must-teams found
            if tbd_games_in_period:
                return {"no_trips_available": True, "TBD_Games": tbd_games_in_period, "actual_start_date": actual_start_date}
            return {"no_trips_available": True, "actual_start_date": actual_start_date}
    
    # For each base trip, generate hotel variations
    all_variations = []
    
    for base_trip in filtered_trips:
        # Create a simplified trip with consistent structure
        simplified_trip = []
        for day in base_trip:
            new_day = copy.deepcopy(day)
            # Standardize outbound travel format
            if "travel_data" in new_day:
                new_day["outbound_travel"] = {
                    "from": new_day["travel_data"]["from"],
                    "to": new_day["travel_data"]["to"],
                    "time": new_day["travel_data"]["time"]
                }
                del new_day["travel_data"]
            simplified_trip.append(new_day)
        
        # Always include the basic trip (default hotel strategy)
        variations = [add_hotel_summary(simplified_trip)]
        
        # Collect all potential hotel locations
        match_locations = [day["location"] for day in base_trip if day.get("matches")]
        potential_hotel_locations = {start_location}.union(match_locations)
        
        # Add nearby cities that could serve as good hotel bases
        if len(match_locations) >= 2:
            all_train_cities = set()
            for loc_pair in train_times.keys():
                all_train_cities.add(loc_pair[0])
                all_train_cities.add(loc_pair[1])
            
            for city in all_train_cities:
                # Only consider cities reachable from all match locations
                if all(train_times.get((city, match_loc), float("inf")) <= max_travel_time 
                      for match_loc in match_locations):
                    potential_hotel_locations.add(city)
        
        # Generate single-base variations (stay in same hotel throughout)
        for hotel_base in potential_hotel_locations:
            variation = create_hotel_variation(simplified_trip, hotel_base)
            if variation:
                variations.append(add_hotel_summary(variation))
        
        # Generate pivot variations (change hotel strategy mid-trip)
        if len(match_locations) >= 2:
            for pivot_idx in range(1, len(simplified_trip)):
                first_hotel = simplified_trip[0]["hotel_location"]
                
                # For second part of trip, try all logical hotel locations
                logical_hotel_locations = {start_location}.union(
                    simplified_trip[i]["location"] for i in range(pivot_idx, len(simplified_trip))
                    if simplified_trip[i].get("matches")
                )
                
                # Create first part variation (before pivot)
                pivot_variation = create_hotel_variation(simplified_trip, first_hotel, 0, pivot_idx)
                if not pivot_variation:
                    continue
                
                # Try each logical hotel for second part
                for second_hotel in logical_hotel_locations:
                    if second_hotel == first_hotel:
                        continue
                    
                    # Create full pivoted variation
                    second_part = create_hotel_variation(pivot_variation, second_hotel, pivot_idx)
                    if second_part:
                        variations.append(add_hotel_summary(second_part))
        
        # Add all valid variations to final collection
        all_variations.extend(variations)
    
    # Remove duplicate trips
    unique_variations = []
    trip_signatures = set()
    
    for trip in all_variations:
        signature = get_trip_signature(trip)
        if signature not in trip_signatures:
            trip_signatures.add(signature)
            unique_variations.append(trip)
    
    #---------------------------------------------------------------------------
    # PHASE 5: FILTER TO BEST OPTIONS BY HOTEL CHANGES
    #---------------------------------------------------------------------------
    
    if unique_variations:
        # Group by match combinations
        match_signatures = {}
        
        for trip in unique_variations:
            match_sig = get_match_signature(trip)
            if match_sig not in match_signatures:
                match_signatures[match_sig] = []
            match_signatures[match_sig].append(trip)
        
        # Select best options for each match combination
        filtered_trips = []
        for match_group in match_signatures.values():
            best_options = filter_best_options_by_hotel_changes(match_group, trip_duration)
            filtered_trips.extend(best_options)
        
        all_optimized_trips = filtered_trips
    else:
        all_optimized_trips = []
    
    #---------------------------------------------------------------------------
    # PHASE 6: RETURN RESULTS
    #---------------------------------------------------------------------------
    
    # Handle various return conditions
    if not all_optimized_trips and tbd_games_in_period:
        return {"no_trips_available": True, "TBD_Games": tbd_games_in_period, "actual_start_date": actual_start_date}
    
    if not all_optimized_trips:
        return {"no_trips_available": True, "actual_start_date": actual_start_date}

    if tbd_games_in_period:
        return {
            "trips": all_optimized_trips,
            "TBD_Games": tbd_games_in_period,
            "actual_start_date": actual_start_date
        }
    
    return {"trips": all_optimized_trips, "actual_start_date": actual_start_date}