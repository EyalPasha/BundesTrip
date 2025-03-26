import pandas as pd
from datetime import datetime, timedelta
from backend.models import Game
from backend.scrapers.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums
from typing import Optional, List, Dict, Tuple
import copy


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


def calculate_total_travel_time(trip: Dict) -> int:
    """Calculate the total travel time for a trip based on actual travel segments."""
    total_minutes = 0
    
    for day in trip:
        if isinstance(day, dict) and "matches" in day:
            for match in day["matches"]:
                if "travel_time" in match and match["travel_time"] != "Unknown":
                    total_minutes += parse_travel_time(match["travel_time"])
    
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


def find_central_locations(match_locations: list, train_times: dict, max_travel_time: int) -> list:
    """Find central locations that minimize total travel time."""
    unique_locations = list(set(match_locations))
    location_scores = []
    
    for base_loc in unique_locations:
        total_time = 0
        viable = True
        
        for match_loc in match_locations:
            if match_loc == base_loc:
                continue
                
            outbound_time = train_times.get((base_loc, match_loc), float("inf"))
            return_time = train_times.get((match_loc, base_loc), float("inf"))
            
            if outbound_time > max_travel_time or return_time > max_travel_time:
                viable = False
                break
                
            total_time += outbound_time + return_time
        
        if viable:
            location_scores.append((total_time, base_loc))
    
    location_scores.sort()
    return [loc for _, loc in location_scores]


def create_single_base_variation(trip_days: list, central_location: str, train_times: dict) -> list:
    """Create variation where you stay in one place for the entire trip."""
    variation = []
    
    for day in trip_days:
        day_copy = copy.deepcopy(day)
        day_copy["hotel"] = central_location
        
        if day_copy.get("matches"):
            for match in day_copy["matches"]:
                if match["location"] != central_location:
                    travel_time = train_times.get((central_location, match["location"]), float("inf"))
                    if travel_time != float("inf"):
                        match["travel_from"] = central_location
                        match["travel_time"] = format_travel_time(travel_time)
                else:
                    match["travel_from"] = central_location
                    match["travel_time"] = "0h 0m"
        
        variation.append(day_copy)
    
    return variation


def create_pivot_variations(trip_days: list, match_locations: list, train_times: dict, max_travel_time: int) -> list:
    """Create variations with strategic hotel changes at optimal points."""
    variations = []
    
    trip_length = len(trip_days)
    if trip_length < 6:
        return variations
        
    pivot_idx = trip_length // 3
    unique_locations = list(set(match_locations))
    
    for loc1 in unique_locations:
        for loc2 in unique_locations:
            if loc1 == loc2:
                continue
                
            variation = []
            
            for i, day in enumerate(trip_days):
                day_copy = copy.deepcopy(day)
                hotel_loc = loc1 if i < pivot_idx else loc2
                day_copy["hotel"] = hotel_loc
                
                if day_copy.get("matches"):
                    for match in day_copy["matches"]:
                        if match["location"] != hotel_loc:
                            travel_time = train_times.get((hotel_loc, match["location"]), float("inf"))
                            if travel_time != float("inf"):
                                match["travel_from"] = hotel_loc
                                match["travel_time"] = format_travel_time(travel_time)
                
                variation.append(day_copy)
            
            # Validate all travel times are within max limit
            valid_variation = True
            for day in variation:
                if day.get("matches"):
                    for match in day["matches"]:
                        travel_mins = parse_travel_time(match.get("travel_time", "0h 0m"))
                        if travel_mins > max_travel_time:
                            valid_variation = False
                            break
                if not valid_variation:
                    break
            
            if valid_variation:
                variations.append(variation)
    
    return variations


def optimize_trip_variations(base_trip: list, train_times: dict, max_travel_time: int) -> list:
    """Generate optimized variations of a trip with different hotel strategies."""
    variations = []
    match_locations = []
    
    # Extract match locations
    for day in base_trip:
        if day.get("matches"):
            for match in day.get("matches", []):
                location = match.get("location")
                if location:
                    match_locations.append(location)
    
    if not match_locations:
        return [base_trip]
    
    # Strategy 1: Match-based (default - stay where each match is)
    match_based = copy.deepcopy(base_trip)
    variations.append(match_based)
    
    # Filter trip days, excluding hotel stats
    trip_days = [day for day in base_trip if isinstance(day, dict) and "day" in day]
    
    # Strategy 2: Single-base (stay in one place for the whole trip)
    central_locations = find_central_locations(match_locations, train_times, max_travel_time)
    for central in central_locations[:3]:  # Limit to top 3 central locations
        single_base = create_single_base_variation(trip_days, central, train_times)
        if single_base:
            variations.append(single_base)
    
    # Strategy 3: Pivot-based (change hotel at optimal points)
    if len(match_locations) >= 3:
        pivot_variations = create_pivot_variations(trip_days, match_locations, train_times, max_travel_time)
        variations.extend(pivot_variations)
    
    return variations


def filter_best_variations_by_hotel_changes(trips: list) -> list:
    """For each distinct trip (same matches), show only the fastest route per number of hotel changes."""
    trip_groups = {}
    
    for trip in trips:
        match_signature = []
        for day in trip:
            if isinstance(day, dict) and "matches" in day:
                for match in day["matches"]:
                    match_signature.append((day.get("day", ""), match.get("match", "")))
        
        signature = tuple(sorted(match_signature))
        
        if signature not in trip_groups:
            trip_groups[signature] = []
            
        trip_groups[signature].append(trip)
    
    filtered_trips = []
    
    for trip_list in trip_groups.values():
        by_change_count = {}
        
        for trip in trip_list:
            hotel_stats = next((item for item in trip if isinstance(item, dict) and 
                              "hotel_changes" in item), {"hotel_changes": 0})
                
            change_count = hotel_stats.get("hotel_changes", 0)
            
            if change_count not in by_change_count:
                by_change_count[change_count] = []
                
            travel_time = calculate_total_travel_time(trip)
            by_change_count[change_count].append((travel_time, trip))
        
        # Get the fastest trip per hotel change count
        for change_count, trip_list in by_change_count.items():
            if trip_list:
                fastest_trip = min(trip_list, key=lambda x: x[0])[1]
                filtered_trips.append(fastest_trip)
    
    return filtered_trips


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

    # Calculate hotel statistics for each trip
    for trip in all_trips:
        hotel_stays = []
        hotel_locations = set()
        previous_hotel = None
        hotel_changes = 0
        
        for i, day in enumerate(trip):
            current_date = day.get("day")
            current_hotel = day.get("hotel")
            
            if current_hotel:
                # Count hotel changes
                if previous_hotel and current_hotel != previous_hotel:
                    hotel_changes += 1
                
                hotel_locations.add(current_hotel)
                
                # Track hotel stays
                if not hotel_stays or hotel_stays[-1]["location"] != current_hotel:
                    hotel_stays.append({
                        "location": current_hotel,
                        "check_in_date": current_date,
                        "nights": 1
                    })
                else:
                    hotel_stays[-1]["nights"] += 1
                
                previous_hotel = current_hotel
        
        # Generate detailed hotel info
        hotel_details = []
        for i, day in enumerate(trip):
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
            "hotel_locations": list(hotel_locations),
            "hotel_stays": hotel_stays,
            "hotel_details": hotel_details
        }
        
        trip.append(trip_hotel_stats)
    
    # Filter to show only best trip per hotel change count
    all_trips = filter_best_variations_by_hotel_changes(all_trips)
    
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