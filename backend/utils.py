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
    # Pre-allocate lists with appropriate capacity
    tbd_games_in_period = []
    current_year = datetime.now().year
    actual_start_date = None  # Initialize variable
    all_optimized_trips = []
    
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
    
    # FIXED: Filter games by league but NOT by trip date (crucial for finding all trips)
    valid_games = [
        g for g in games 
        if hasattr(g, 'league') and hasattr(g, 'date') and hasattr(g, 'hbf_location') and 
        (not preferred_leagues_lower or g.league.lower() in preferred_leagues_lower)
    ]
    
    # Further filter games by date for use
    valid_games_in_period = [
        g for g in valid_games
        if start_date.date() <= g.date.date() < trip_end_date.date()
    ]
    
    # Process TBD games in one pass
    valid_tbd_games = []
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

    # Create initial route with hotel information
    start_day_str = date_strings[0]
    initial_routes = [[{
        "day": start_day_str, 
        "location": start_location, 
        "matches": [], 
        "note": "Start",
        "hotel_location": start_location  # Start with hotel in initial location
    }]]

    # Group games by date for faster access
    games_by_date = {}
    for game in valid_games_in_period:
        game_date = game.date.date()
        if game_date not in games_by_date:
            games_by_date[game_date] = []
        games_by_date[game_date].append(game)
    
    # Process each date in sequence to build possible routes
    for date_idx, current_date in enumerate(full_date_range):
        current_date_str = date_strings[date_idx]
        new_routes = []
        
        # Get games for current date
        current_date_games = games_by_date.get(current_date.date(), [])
        
        # Skip expensive reachability check if no games today
        if not current_date_games:
            for trip in initial_routes:
                new_trip = copy.deepcopy(trip)
                # For rest days, keep same hotel and location
                last_location = trip[-1]["location"]
                new_trip.append({
                    "day": current_date_str,
                    "location": last_location,
                    "matches": [],
                    "note": "Rest Day",
                    "hotel_location": last_location  # Default hotel same as location
                })
                new_routes.append(new_trip)
            initial_routes = new_routes
            continue

        # For each existing route, find possible extensions
        for trip in initial_routes:
            # FIXED: Use ALL locations in the trip to find reachable games - this was the critical fix
            # Using only the last location missed potential connections like Berlin -> Kiel
            current_locations = {day.get("location", start_location) for day in trip}
            
            # Find reachable games from all current locations
            reachable_by_location = {}
            
            for loc in current_locations:
                for game in current_date_games:
                    travel_time = train_times.get((loc, game.hbf_location), float("inf"))
                    if travel_time <= max_travel_time:
                        # Format travel time
                        travel_time_str = f"{travel_time // 60}h {travel_time % 60}m"
                        match_str = f"{game.home_team} vs {game.away_team} ({game.time})"
                        
                        # Track if this match contains a must_team
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
                    "hotel_location": trip[-1]["location"]  # Default hotel same as location
                })
                new_routes.append(new_trip)
                continue
                
            # For each reachable location, create a new route option
            for match_location, options in reachable_by_location.items():
                for option in options:
                    new_trip = copy.deepcopy(trip)
                    new_trip.append({
                        "day": current_date_str,
                        "location": match_location,
                        "matches": [option],
                        "note": "",
                        "hotel_location": match_location,  # Default: stay at match location
                        "travel_data": {
                            "from": option["travel_from"],  # Use the specific starting location
                            "to": match_location,
                            "time": option["raw_travel_time"],
                            "time_str": option["travel_time"]
                        }
                    })
                    new_routes.append(new_trip)
        
        # Update routes for next iteration
        initial_routes = new_routes
    
    # PHASE 2: GENERATE OPTIMIZED HOTEL VARIATIONS FOR EACH TRIP
    # -----------------------------------------------------------------------------
    
    # Filter out trips with no matches
    valid_trip_routes = [trip for trip in initial_routes 
                         if any(len(day.get("matches", [])) > 0 for day in trip)]
    
    # Initialize all_optimized_trips outside any conditionals
    all_optimized_trips = []

    # Process valid routes regardless of must_teams
    if valid_trip_routes:
        # Only filter for must_teams if it's provided
        filtered_trips = valid_trip_routes
        if must_teams_lower:
            filtered_trips = [
                trip for trip in valid_trip_routes
                if any(match.get("contains_must_team", False) 
                      for day in trip 
                      for match in day.get("matches", []))
            ]
        
        # Process each trip to generate ALL POSSIBLE hotel variations
        for base_trip in filtered_trips:
            # Always keep the base trip (usually staying at match locations)
            simplified_trip = []
            
            for day in base_trip:
                new_day = copy.deepcopy(day)
                if "travel_data" in new_day:
                    # Replace travel_data with outbound_travel for consistency
                    new_day["outbound_travel"] = {
                        "from": new_day["travel_data"]["from"],
                        "to": new_day["travel_data"]["to"],
                        "time": new_day["travel_data"]["time"]
                    }
                    del new_day["travel_data"]
                simplified_trip.append(new_day)
                
            # Collect ALL possible variations without restrictions
            reasonable_variations = [simplified_trip]  # Start with the basic trip
            
            # Identify all potential hotel locations for variations
            potential_hotel_locations = set()
            for day in base_trip:
                potential_hotel_locations.add(day["location"])
            
            # For each day in the trip, create all possible hotel combinations
            match_locations = [day["location"] for day in base_trip if day.get("matches")]
            
            # Generate all possible hotel strategies for each match location
            for hotel_base in potential_hotel_locations:
                # Try using this location as a base
                hotel_variation = copy.deepcopy(simplified_trip)
                
                # Modify each day to use this location as hotel where feasible
                for i, day in enumerate(hotel_variation):
                    if i == 0:  # Don't change first day
                        continue
                        
                    current_loc = day["location"]
                    if not day.get("matches"):  # For rest days, use the hotel base
                        day["hotel_location"] = hotel_base
                        day["hotel_change"] = day["hotel_location"] != hotel_variation[i-1]["hotel_location"]
                        continue
                        
                    # Check if returning to hotel_base is feasible
                    return_time = train_times.get((current_loc, hotel_base), float("inf"))
                    
                    if return_time <= max_travel_time:
                        # Fix outbound travel to start from where we actually spent the night
                        prev_hotel_loc = hotel_variation[i-1]["hotel_location"]
                        if "outbound_travel" in day:
                            day["outbound_travel"]["from"] = prev_hotel_loc
                            new_travel_time = train_times.get((prev_hotel_loc, current_loc), float("inf"))
                            if new_travel_time <= max_travel_time:
                                day["outbound_travel"]["time"] = new_travel_time
                            else:
                                # Can't reach match location from previous hotel
                                day["invalid_travel"] = True
                                break
                        
                        # This match can be visited from hotel_base
                        day["hotel_location"] = hotel_base
                        day["hotel_change"] = day["hotel_location"] != hotel_variation[i-1]["hotel_location"]
                        
                        # Only add return travel info if different from match location
                        if current_loc != hotel_base:
                            day["return_travel"] = {
                                "from": current_loc,
                                "to": hotel_base,
                                "time": return_time
                            }
                    else:
                        # Must stay at match location
                        day["hotel_location"] = current_loc
                        day["hotel_change"] = day["hotel_location"] != hotel_variation[i-1]["hotel_location"]
                
                # Add this variation if it doesn't have invalid travel
                if not any(day.get("invalid_travel") for day in hotel_variation):
                    reasonable_variations.append(hotel_variation)
            
            # Generate additional variations where you switch hotels strategically
            # For trips with more than 2 locations
            if len(match_locations) >= 2:
                # Try variations where we stay in each match location for a while
                for pivot_idx in range(1, len(simplified_trip)):
                    # Create variation where we change hotel strategy at this point
                    pivot_variation = copy.deepcopy(simplified_trip)
                    
                    # Before pivot: stay at first hotel location
                    first_hotel = pivot_variation[0]["hotel_location"]
                    for i in range(1, pivot_idx):
                        day = pivot_variation[i]
                        
                        # Can we stay at first hotel?
                        if day.get("matches"):
                            current_loc = day["location"]
                            travel_time = train_times.get((first_hotel, current_loc), float("inf"))
                            return_time = train_times.get((current_loc, first_hotel), float("inf"))
                            
                            if travel_time <= max_travel_time and return_time <= max_travel_time:
                                # Fix outbound travel
                                if "outbound_travel" in day:
                                    day["outbound_travel"]["from"] = first_hotel
                                    day["outbound_travel"]["time"] = travel_time
                                    
                                # Set hotel and return travel
                                day["hotel_location"] = first_hotel
                                day["hotel_change"] = False
                                
                                if current_loc != first_hotel:
                                    day["return_travel"] = {
                                        "from": current_loc,
                                        "to": first_hotel,
                                        "time": return_time
                                    }
                            else:
                                # Must stay at match location
                                day["hotel_location"] = current_loc
                                day["hotel_change"] = day["hotel_location"] != pivot_variation[i-1]["hotel_location"]
                        else:
                            # For rest days, keep hotel
                            day["hotel_location"] = first_hotel
                            day["hotel_change"] = False
                            
                    # After pivot: ONLY USE LOGICAL HOTEL LOCATIONS
                    # For the part after the pivot, we'll consider only:
                    # 1. Match locations where games are actually played
                    # 2. The original start location (returning to start)
                    logical_hotel_locations = {start_location}  # Start with the original start location
                    
                    # Add all match locations AFTER the pivot
                    for j in range(pivot_idx, len(pivot_variation)):
                        if pivot_variation[j].get("matches") and pivot_variation[j]["location"] not in logical_hotel_locations:
                            logical_hotel_locations.add(pivot_variation[j]["location"])
                    
                    # Try each logical hotel location
                    for hotel_base in logical_hotel_locations:
                        if hotel_base == first_hotel:
                            continue  # Skip if same as first part
                            
                        # Create a new copy for this hotel base
                        hotel_base_variation = copy.deepcopy(pivot_variation)
                            
                        for i in range(pivot_idx, len(hotel_base_variation)):
                            day = hotel_base_variation[i]
                            
                            if not day.get("matches"):  # For rest days
                                day["hotel_location"] = hotel_base
                                day["hotel_change"] = day["hotel_location"] != hotel_base_variation[i-1]["hotel_location"]
                                continue
                                
                            current_loc = day["location"]
                            
                            # Check if staying at hotel_base is feasible
                            travel_time = train_times.get((hotel_base, current_loc), float("inf"))
                            return_time = train_times.get((current_loc, hotel_base), float("inf"))
                            
                            if travel_time <= max_travel_time and return_time <= max_travel_time:
                                # Fix outbound travel
                                prev_hotel_loc = hotel_base_variation[i-1]["hotel_location"]
                                if "outbound_travel" in day:
                                    day["outbound_travel"]["from"] = prev_hotel_loc
                                    new_travel_time = train_times.get((prev_hotel_loc, current_loc), float("inf"))
                                    if new_travel_time <= max_travel_time:
                                        day["outbound_travel"]["time"] = new_travel_time
                                    else:
                                        # Can't reach match from previous hotel
                                        day["invalid_travel"] = True
                                        break
                                
                                # Set hotel location
                                day["hotel_location"] = hotel_base
                                day["hotel_change"] = day["hotel_location"] != hotel_base_variation[i-1]["hotel_location"]
                                

                                if current_loc != hotel_base:
                                    # Always add return travel when staying at a different location than the match
                                    # This ensures the return journey is counted in the total travel time
                                    day["return_travel"] = {
                                        "from": current_loc,
                                        "to": hotel_base,
                                        "time": return_time
                                    }
                                    
                                    # Add a special note if returning to start location
                                    if hotel_base == start_location:
                                        day["hotel_note"] = "Return to start location"
                            else:
                                # Must stay at match location
                                day["hotel_location"] = current_loc
                                day["hotel_change"] = day["hotel_location"] != hotel_base_variation[i-1]["hotel_location"]
                                
                                # For the last day, we don't need any return travel
                                if i == len(hotel_base_variation) - 1:
                                    day.pop("return_travel", None)  # Remove any return travel on last day
                        
                        # Add this variation if it doesn't have invalid travel
                        if not any(day.get("invalid_travel") for day in hotel_base_variation):
                            reasonable_variations.append(hotel_base_variation)

            # Verify travel consistency for ALL variations
            valid_variations = []
            for variation in reasonable_variations:
                valid = True
                
                # Walk through each day and ensure travel is consistent with hotel stays
                for i in range(1, len(variation)):
                    day = variation[i]
                    prev_day = variation[i-1]
                    
                    # Skip days without matches or travel
                    if not day.get("matches") or not day.get("outbound_travel"):
                        continue
                    
                    # The previous night's hotel is where we must travel from
                    actual_start_location = prev_day["hotel_location"]
                    
                    # If current outbound travel doesn't match where we spent the night, fix it
                    if day["outbound_travel"]["from"] != actual_start_location:
                        # Fix the travel route to start from the correct hotel
                        current_destination = day["outbound_travel"]["to"]
                        
                        # Get the correct travel time from hotel to destination
                        correct_time = train_times.get((actual_start_location, current_destination), float("inf"))
                        if correct_time > max_travel_time:
                            # If we can't reach the destination from the hotel in time,
                            # this variation is invalid
                            valid = False
                            break
                        
                        # Update the travel route with correct starting point and time
                        day["outbound_travel"]["from"] = actual_start_location
                        day["outbound_travel"]["time"] = correct_time
                
                if valid:
                    valid_variations.append(variation)
            
            # Add hotel statistics to all valid variations
            for trip in valid_variations:
                # Recalculate hotel changes based on the final itinerary
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
            
            # Add all variations to final results - NO LIMITS!
            all_optimized_trips.extend(valid_variations)

        # Only deduplication - keep all unique trips without other filtering
        unique_trips = []
        trip_signatures = set()

        for trip in all_optimized_trips:
            # Create a trip signature based on key attributes
            signature_parts = []
            
            for day in trip:
                # Include key data in signature
                hotel = day.get("hotel_location", "")
                outbound = tuple(sorted(day.get("outbound_travel", {}).items())) if "outbound_travel" in day else ()
                return_travel = tuple(sorted(day.get("return_travel", {}).items())) if "return_travel" in day else ()
                matches = tuple(sorted((m.get("match", ""), m.get("location", "")) 
                                for m in day.get("matches", [])))
                
                day_sig = (hotel, outbound, return_travel, matches)
                signature_parts.append(day_sig)
                
            # Convert to immutable tuple for hashing
            trip_signature = tuple(signature_parts)
            
            if trip_signature not in trip_signatures:
                trip_signatures.add(trip_signature)
                unique_trips.append(trip)

        all_optimized_trips = unique_trips

    # Return the results
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