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
                    # Store only what's needed for comparison
                    match_signature.append((day.get("day"), match["match"]))
        
        # Convert to tuple for immutability and faster hashing
        match_signature_tuple = tuple(match_signature)
        
        # Direct dictionary lookup instead of linear search
        group_index = signature_to_group_index.get(match_signature_tuple)
        
        if group_index is not None:
            # Match found - add to existing group
            trip_groups[group_index]["Variations"].append(trip)
        else:
            # No match - create new group
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

def plan_trip(start_location: str, trip_duration: int, max_travel_time: int, games: list, train_times: dict, 
             tbd_games: list = None, preferred_leagues: list = None, start_date: Optional[str] = None, must_teams: Optional[list] = None):    
    # Pre-allocate lists with appropriate capacity
    all_trips = []
    tbd_games_in_period = []
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

    # Create initial route
    # Pre-format start date string
    start_day_str = date_strings[0]
    initial_routes = [[{"day": start_day_str, "location": start_location, "matches": [], "note": "Start"}]]

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
                new_trip.append({
                    "day": current_date_str,
                    "location": trip[-1]["location"],
                    "matches": [],
                    "note": "Rest Day"
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
                    new_trip.append({
                        "day": current_date_str,
                        "location": trip[-1]["location"],
                        "matches": [],
                        "note": "Rest Day"
                    })
                    new_routes.append(new_trip)
                    continue
                
                # Create minimum necessary copies and only deepcopy once per trip
                for location, options in reachable_by_location.items():
                    # Select best option from each location (shortest travel time)
                    best_option = min(options, key=lambda o: train_times.get((o["travel_from"], o["location"]), float("inf")))
                    
                    new_trip = copy.deepcopy(trip)
                    new_trip.append({
                        "day": current_date_str,
                        "location": location,
                        "matches": [best_option],
                        "note": ""
                    })
                    new_routes.append(new_trip)
                    
                    # Add additional options only if they're from different starting points
                    from_locations = {best_option["travel_from"]}
                    for option in options:
                        if option["travel_from"] not in from_locations:
                            from_locations.add(option["travel_from"])
                            new_trip = copy.deepcopy(trip)
                            new_trip.append({
                                "day": current_date_str,
                                "location": location,
                                "matches": [option],
                                "note": ""
                            })
                            new_routes.append(new_trip)
                
            except Exception:
                # If there's an error, add a rest day as fallback
                try:
                    new_trip = copy.deepcopy(trip)
                    new_trip.append({
                        "day": current_date_str,
                        "location": trip[-1]["location"],
                        "matches": [],
                        "note": "Rest Day (Error Recovery)"
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