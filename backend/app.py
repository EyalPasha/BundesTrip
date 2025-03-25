import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fastapi import FastAPI, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List 
from datetime import datetime, timedelta
from backend.utils import load_games, load_train_times, plan_trip, calculate_total_travel_time, identify_similar_trips
from backend.models import TripRequest, FormattedResponse, TravelSegment, TripVariation, TripGroup
from scrapers.synonyms import AIRPORT_CITIES, league_priority
from backend.config import BASE_DIR, GAMES_FILE, TRAIN_TIMES_FILE, CORS_ORIGINS

#======================================================
# APP INITIALIZATION
#======================================================

app = FastAPI(
    title="Multi-Game Trip Planner API",
    description="API for planning trips to multiple soccer/football games",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data using config paths
train_times = load_train_times(TRAIN_TIMES_FILE)
games, tbd_games = load_games(GAMES_FILE)

#======================================================
# HELPER FUNCTIONS - TRIP PROCESSING
#======================================================

def determine_end_location(itinerary):
    """Determine the true ending location of a trip"""
    # First try to get the last night's hotel
    for day in reversed(itinerary):
        if "hotel_location" in day:
            return day["hotel_location"]
            
    # Fall back to last location visited
    for day in reversed(itinerary):
        if "location" in day:
            return day["location"]
            
    return "Unknown"

def calculate_airport_distances(start_location, end_location, train_times):
    """Calculate distances to airports from start and end locations"""
    def format_travel_time(minutes):
        if minutes is None:
            return "Unknown"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"
    
    airport_distances = {"start": [], "end": []}
    
    # Process start location airports
    for airport in AIRPORT_CITIES:
        if airport.lower() == start_location.lower():
            travel_time = "0h 0m"
        else:
            minutes = train_times.get((start_location, airport), None)
            travel_time = format_travel_time(minutes)
            
        airport_distances["start"].append({
            "airport": airport.replace(" hbf", ""),
            "travel_time": travel_time
        })
    
    # Process end location airports
    for airport in AIRPORT_CITIES:
        if airport.lower() == end_location.lower():
            travel_time = "0h 0m"
        else:
            minutes = train_times.get((end_location, airport), None)
            travel_time = format_travel_time(minutes)
            
        airport_distances["end"].append({
            "airport": airport.replace(" hbf", ""),
            "travel_time": travel_time
        })
    
    # Sort by travel time
    def get_minutes(time_str):
        if time_str == "0h 0m":
            return 0
        if time_str == "Unknown":
            return float('inf')
        parts = time_str.split('h ')
        hours = int(parts[0])
        minutes = int(parts[1].replace('m', ''))
        return hours * 60 + minutes
    
    airport_distances["start"].sort(key=lambda x: get_minutes(x["travel_time"]))
    airport_distances["end"].sort(key=lambda x: get_minutes(x["travel_time"]))
    
    return airport_distances

def format_travel_time(minutes):
    """Format minutes as hours and minutes string"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"

def generate_travel_segments(itinerary, start_location, train_times):
    """Generate travel segments for a trip"""
    travel_segments = []
    current_location = start_location
    
    for i, day in enumerate(itinerary):
        if not day.get("day"):
            continue
            
        # Update current location based on previous day
        if i > 0:
            prev_day = itinerary[i-1]
            if "hotel_location" in prev_day:
                current_location = prev_day["hotel_location"]
        
        day_str = day["day"]
        day_parts = day_str.split()
        day_formatted = f"{day_parts[0]} {day_parts[1]}" if len(day_parts) >= 2 else day_str
        
        # Process matches
        for match in day.get("matches", []):
            match_location = match["location"]
            
            # Add travel to match if needed
            if match_location != current_location:
                travel_segments.append(TravelSegment(
                    from_location=current_location,
                    to_location=match_location,
                    day=day_formatted,
                    travel_time=format_travel_time(train_times.get((current_location, match_location), 0))
                ))
                current_location = match_location
                
        # Add return to hotel if needed
        if "hotel_location" in day and day["hotel_location"] != current_location:
            travel_segments.append(TravelSegment(
                from_location=current_location,
                to_location=day["hotel_location"],
                day=day_formatted,
                context="After Game",
                travel_time=format_travel_time(train_times.get((current_location, day["hotel_location"]), 0))
            ))
            current_location = day["hotel_location"]
    
    return travel_segments

def build_variant_details(variant, start_location, train_times):
    """Build detailed metadata for a trip variation"""
    # Calculate total travel time
    total_travel_time = calculate_total_travel_time(variant)
    
    # Determine actual start location
    actual_start_location = start_location
    if actual_start_location.lower() == "any":
        # Find first match location
        for day in variant["Itinerary"]:
            if day.get("matches"):
                actual_start_location = day["matches"][0]["location"]
                break
    
    # Extract cities, teams, game count
    cities = set()
    teams = set()
    num_games = 0
    end_location = actual_start_location
    
    # Process itinerary to collect metadata
    for day in variant["Itinerary"]:
        # Track locations
        if "location" in day and day["location"] != "Unknown" and not day["location"].startswith("Any"):
            end_location = day["location"]
            cities.add(end_location.replace(" hbf", ""))
        
        # Process matches
        for match in day.get("matches", []):
            num_games += 1
            
            # Extract teams from match string
            if "match" in match:
                match_parts = match["match"].split(" vs ")
                if len(match_parts) == 2:
                    home_team = match_parts[0].strip()
                    away_team = match_parts[1].split(" (")[0].strip()
                    teams.add(home_team)
                    teams.add(away_team)
    
    # Get actual end location (where traveler ends up)
    true_end_location = determine_end_location(variant["Itinerary"])
    
    # Calculate airport distances
    airport_distances = calculate_airport_distances(actual_start_location, true_end_location, train_times)
    
    # Generate travel segments
    travel_segments = generate_travel_segments(variant["Itinerary"], actual_start_location, train_times)
    
    return TripVariation(
        total_travel_time=total_travel_time,
        travel_hours=total_travel_time // 60,
        travel_minutes=total_travel_time % 60,
        travel_segments=travel_segments,
        cities=sorted(list(cities)),
        teams=sorted(list(teams)),
        num_games=num_games,
        start_location=actual_start_location.replace(" hbf", ""),
        end_location=true_end_location.replace(" hbf", ""),
        airport_distances=airport_distances
    )

def process_trip_groups(trip_groups, start_location, train_times):
    """Process trip groups to add metadata like airport distances and travel times"""
    structured_groups = []
    
    for group in trip_groups:
        # Fix the base trip data when start_location is "Any"
        if start_location.lower() == "any" and group["Base"]["Itinerary"]:
            # Find the first match location
            first_match_location = next((
                day["matches"][0]["location"] 
                for day in group["Base"]["Itinerary"] 
                if day.get("matches")
            ), None)
                
            # If we found a first match location, update the starting location
            if first_match_location:
                for day in group["Base"]["Itinerary"]:
                    if day.get("note") == "Start":
                        day["location"] = first_match_location
                        break
                        
                # Fix travel_from fields in the first match
                for day in group["Base"]["Itinerary"]:
                    if day.get("matches"):
                        for match in day["matches"]:
                            if match.get("location") == first_match_location:
                                match["travel_from"] = first_match_location
                                match["travel_time"] = "0h 0m"
                        break

        # Process each variation to gather details
        variation_details = []
        
        for variant in group["Variations"]:
            # Calculate travel details
            variation_details.append(build_variant_details(variant, start_location, train_times))
        
        # Add the processed group to results
        structured_groups.append(TripGroup(
            base_trip=group["Base"],
            variations=group["Variations"],
            variation_details=variation_details
        ))
    
    return structured_groups

#======================================================
# HELPER FUNCTIONS - RESPONSE FORMATTING
#======================================================

def _get_hotel_summary(trip_data):
    """Extract hotel summary from trip data"""
    if isinstance(trip_data, dict) and "Itinerary" in trip_data:
        trip_data = trip_data["Itinerary"]
        
    for day in trip_data:
        if "hotel_summary" in day:
            return day["hotel_summary"]
    return None

def _add_airport_info(output, variant_detail, indent=""):
    """Add airport information to the output"""
    if variant_detail.airport_distances and "end" in variant_detail.airport_distances:
        top_airports = variant_detail.airport_distances["end"][:3]
        if top_airports:
            airport_text = ", ".join(
                f"{a['airport']} ({a['travel_time']})"
                for a in top_airports
            )
            output.append(
                f"{indent}✈️  Nearest airports to {variant_detail.end_location}: {airport_text}"
            )

def _add_hotel_details(output, trip_data, indent=""):
    """Add day-by-day hotel information"""
    if isinstance(trip_data, dict) and "Itinerary" in trip_data:
        trip_data = trip_data["Itinerary"]
        
    hotel_days = []
    seen_days = set()
    
    for day in trip_data:
        if "day" in day and "hotel_location" in day and day["day"] not in seen_days:
            seen_days.add(day["day"])
            hotel_days.append({
                "day": day["day"],
                "location": day["hotel_location"].replace(" hbf", ""),
                "change": day.get("hotel_change", False),
                "note": day.get("hotel_note", "")
            })
    
    if hotel_days:
        output.append(f"{indent}🏨 Hotel Details:")
        for hday in hotel_days:
            if hday["change"]:
                output.append(f"{indent}  {hday['day']}: Change hotel to {hday['location']}")
                if hday["note"]:
                    output.append(f"{indent}    Note: {hday['note']}")
            else:
                output.append(f"{indent}  {hday['day']}: Stay in hotel in {hday['location']}")

def _get_travel_segments(trip_data):
    """Generate travel segments text for a trip variation"""
    if isinstance(trip_data, dict) and "Itinerary" in trip_data:
        trip_data = trip_data["Itinerary"]
        
    travel_segments = []
    seen_segments = set()
    current_location = None
    
    # First determine where the person actually stays each night
    location_by_day = {}
    for day in trip_data:
        if "day" in day and "hotel_location" in day:
            location_by_day[day["day"]] = day["hotel_location"]
    
    # Generate travel segments chronologically
    for i, day in enumerate(trip_data):
        if not "day" in day:
            continue
            
        day_str = day["day"]
        
        # Get the actual location at the start of this day
        if i == 0:
            current_location = day["hotel_location"]
        else:
            prev_day = trip_data[i-1]
            current_location = prev_day["hotel_location"]
        
        # If there's a match today, add travel to the match location
        if day.get("matches"):
            match_location = day["matches"][0]["location"]
            if match_location != current_location:
                # Format travel time with correct locations
                travel_minutes = train_times.get((current_location, match_location), 0)
                hours = travel_minutes // 60
                mins = travel_minutes % 60
                travel_time = f"{hours}h {mins}m"
                
                # Clean location names
                from_clean = current_location.replace(' hbf', '')
                to_clean = match_location.replace(' hbf', '')
                
                # Generate segment text
                segment_key = (from_clean, to_clean, day_str)
                if segment_key not in seen_segments:
                    seen_segments.add(segment_key)
                    travel_segments.append(f"{from_clean} → {to_clean} ({day_str}) - {travel_time}")
                
                current_location = match_location
            
            # If returning to hotel after match, add that segment
            hotel_location = day["hotel_location"]
            if hotel_location != current_location:
                # Format travel time properly
                travel_minutes = train_times.get((current_location, hotel_location), 0)
                hours = travel_minutes // 60
                mins = travel_minutes % 60
                travel_time = f"{hours}h {mins}m"
                
                # Clean location names
                from_clean = current_location.replace(' hbf', '')
                to_clean = hotel_location.replace(' hbf', '')
                
                # Generate segment text with "After Game" context
                context_text = f" ({day_str}, After Game)"
                segment_key = (from_clean, to_clean, context_text)
                if segment_key not in seen_segments:
                    seen_segments.add(segment_key)
                    travel_segments.append(f"{from_clean} → {to_clean}{context_text} - {travel_time}")
                
                current_location = hotel_location
    
    return travel_segments

def print_formatted_trip_schedule(response):
    """
    Print the trip schedule in a formatted way, grouping days and showing travel options.
    """
    def clean_location(loc):
        """Remove hbf suffix from location names"""
        return loc.replace(" hbf", "") if loc else ""

    output = []

    # Print header information
    output.append(f"📍 Start Location: {clean_location(response.start_location)}")
    output.append(f"📅 Start Date: {response.start_date}")
    output.append(f"⏳ Max Travel Time: {response.max_travel_time}")
    output.append(f"🗓️ Trip Duration: {response.trip_duration}")
    output.append(f"🏆 Preferred Leagues: {', '.join(response.preferred_leagues) if isinstance(response.preferred_leagues, list) else response.preferred_leagues}")
    
    if hasattr(response, 'must_teams') and response.must_teams:
        must_teams_display = ', '.join(response.must_teams) if isinstance(response.must_teams, list) else response.must_teams
        output.append(f"⭐ Must Include Teams: {must_teams_display}")
    
    output.append("=" * 50 + "\n")

    if response.no_trips_available:
        output.append("No trips with matches found for this period.")
        output.append("")
        
    else:
        # Process trip groups
        for group_index, group in enumerate(response.trip_groups or [], start=1):
            output.append("-" * 100)
            output.append(f"Trip {group_index}:")
            output.append("-" * 100)

            # Add common metadata summary
            if group.variation_details and group.variation_details[0]:
                variant = group.variation_details[0]
                
                # Display actual start location if original was "Any"
                if response.start_location.lower() == "any":
                    output.append(f"📍 Starting City: {variant.start_location}")
                
                output.append(f"🏙️  Cities: {', '.join(variant.cities)}")
                output.append(f"⚽ Teams: {', '.join(variant.teams)}")
                output.append(f"🏟️  Number of Games: {variant.num_games}")
                
                # Show airports near start location
                if variant.airport_distances and "start" in variant.airport_distances:
                    airport_text = ", ".join(
                        f"{a['airport']} ({a['travel_time']})"
                        for a in variant.airport_distances["start"][:3]
                    )
                    
                    display_location = variant.start_location if response.start_location.lower() == "any" else clean_location(response.start_location)
                    output.append(f"✈️  Airports near start location ({display_location}): {airport_text}")

                output.append("")

            # Process itinerary days
            base_trip = group.base_trip
            day_map = {}
            day_order = []

            # Group items by day while preserving order
            for day_item in base_trip["Itinerary"]:
                day_name = day_item.get("day", "Unknown")
                
                if day_name not in day_map:
                    day_map[day_name] = {"matches": [], "locations": []}
                    day_order.append(day_name)
                
                day_map[day_name]["matches"].extend(day_item.get("matches", []))

                # For rest days, store location
                if not day_item.get("matches") and "location" in day_item:
                    day_map[day_name]["locations"].append(day_item["location"])

            # Print days in order
            for day_name in day_order:
                day_info = day_map[day_name]
                output.append(f"📅 {day_name}")

                if day_info["matches"]:
                    # Display matches
                    match_header = "   ⚽ Match:" if len(day_info["matches"]) == 1 else "   ⚽ Matches:"
                    output.append(match_header)
                    
                    for match in day_info["matches"]:
                        match_prefix = "🌟 " if match.get("contains_must_team", False) else ""
                        output.append(f"      {match_prefix}🏟️  {match['match']}")
                        output.append(f"      📍 {clean_location(match['location'])}")
                else:
                    output.append("   💤 Rest Day")

                output.append("")

            # Process travel options
            if len(group.variations) > 1:
                output.append("   🔄 Travel Options:")
                for var_idx, variant_detail in enumerate(group.variation_details):
                    # Format travel option header
                    output.append(
                        f"      🚆 Option {var_idx+1}: "
                        f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
                        f"ending in {variant_detail.end_location}:"
                    )
                    
                    # Add hotel summary
                    hotel_summary = _get_hotel_summary(group.variations[var_idx])
                    if hotel_summary:
                        output.append(f"      🏨 Hotel Changes: {hotel_summary['total_hotel_changes']}")
                        output.append(f"      🏨 Unique Hotels: {hotel_summary['unique_hotels']}")
                        if "hotel_cities" in hotel_summary and hotel_summary["hotel_cities"]:
                            output.append(f"      🏨 Hotel Locations: {', '.join(hotel_summary['hotel_cities'])}")

                    # Add nearest airports
                    _add_airport_info(output, variant_detail, "      ")
                    
                    # Add hotel details
                    _add_hotel_details(output, group.variations[var_idx], "      ")
                    
                    # Add travel segments
                    travel_segments = _get_travel_segments(group.variations[var_idx])
                    if travel_segments:
                        output.append("      " + "\n      ".join(travel_segments))

                    if var_idx < len(group.variation_details) - 1:
                        output.append("")
            else:
                # Single option
                variant_detail = group.variation_details[0] if group.variation_details else None
                if variant_detail:
                    output.append(
                        f"   ℹ️  Only one travel option: "
                        f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
                        f"ending in {variant_detail.end_location}"
                    )

                    # Add hotel summary
                    hotel_summary = _get_hotel_summary(group.base_trip)
                    if hotel_summary:
                        output.append(f"   🏨 Hotel Changes: {hotel_summary['total_hotel_changes']}")
                        output.append(f"   🏨 Unique Hotels: {hotel_summary['unique_hotels']}")
                        if "hotel_cities" in hotel_summary and hotel_summary["hotel_cities"]:
                            output.append(f"   🏨 Hotel Locations: {', '.join(hotel_summary['hotel_cities'])}")

                    # Add nearest airports
                    _add_airport_info(output, variant_detail, "   ")
                    
                    # Add hotel details
                    _add_hotel_details(output, group.base_trip, "   ")
                    
                    # Add travel segments
                    travel_segments = []
                    for seg in variant_detail.travel_segments:
                        from_clean = clean_location(seg.from_location)
                        to_clean = clean_location(seg.to_location)
                        
                        # Format context text
                        context_text = ""
                        if seg.day:
                            context_text = f" ({seg.day}" + (f", {seg.context})" if seg.context else ")")
                        elif seg.context:
                            context_text = f" ({seg.context})"
                        
                        segment_text = f"{from_clean} → {to_clean}{context_text} - {seg.travel_time}"
                        if segment_text not in travel_segments:
                            travel_segments.append(segment_text)

                    if travel_segments:
                        output.append("      " + "\n      ".join(travel_segments))

            output.append("")  # Blank line after each trip group

    # TBD games
    if response.tbd_games:
        output.append("\n📝 Upcoming Unscheduled Games:")
        output.append("These games don't have confirmed times yet but might be included in your trip once scheduled:")

        for game in sorted(response.tbd_games, key=lambda g: g["date"]):
            match_prefix = "🌟 " if game.get("has_must_team", False) else ""
            output.append(
                f"   • {match_prefix}{game['date']} - {game['match']} @ {clean_location(game['location'])} ({game['league']})"
            )
        output.append("\nCheck back later for updated schedules!")

    formatted_output = "\n".join(output)
    print(formatted_output)  # Actually print to console
    return formatted_output

#======================================================
# API ROUTES - HOME
#======================================================

@app.get("/")
def home():
    return {"message": "Welcome to the Multi-Game Trip Planner API"}

#======================================================
# API ROUTES - TRIP PLANNING
#======================================================

@app.post("/plan-trip", summary="Plan a multi-game trip",
          description="Creates an optimized itinerary to watch multiple games based on preferences",
          response_model=FormattedResponse)
def get_trip(request: TripRequest):
    """
    Plan a multi-day trip to watch games with optimized travel and hotel options.
    """
    try:
        # Input validation
        if request.trip_duration <= 0:
            return JSONResponse(content={"error": "Trip duration must be positive"}, status_code=400)
            
        if request.max_travel_time <= 0:
            return JSONResponse(content={"error": "Maximum travel time must be positive"}, status_code=400)

        # Load and filter games
        regular_games, tbd_games = load_games(GAMES_FILE)
        
        # Filter by leagues if specified
        if request.preferred_leagues:
            preferred_lower = {league.lower() for league in request.preferred_leagues}
            regular_games = [g for g in regular_games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            tbd_games = [g for g in tbd_games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            
            if not regular_games and not tbd_games:
                return JSONResponse(
                    content={"error": f"No games found for the selected leagues: {', '.join(request.preferred_leagues)}"},
                    status_code=404
                )
        
        # Validate must_teams existence
        if request.must_teams:
            must_teams_lower = {team.lower() for team in request.must_teams}
            team_found = any(
                (hasattr(g, 'home_team') and g.home_team.lower() in must_teams_lower) or
                (hasattr(g, 'away_team') and g.away_team.lower() in must_teams_lower)
                for g in regular_games + tbd_games
            )
            
            if not team_found:
                return JSONResponse(
                    content={"error": f"No games found for the requested teams: {', '.join(request.must_teams)}"},
                    status_code=404
                )
        
        # Plan the trip
        trip_result = plan_trip(
            start_location=request.start_location,
            trip_duration=request.trip_duration,
            max_travel_time=request.max_travel_time,
            games=regular_games,
            train_times=train_times,
            tbd_games=tbd_games,
            preferred_leagues=request.preferred_leagues,
            start_date=request.start_date,
            must_teams=request.must_teams
        )
        
        # Extract common result data
        display_start_date = request.start_date or "Earliest Available"
        if isinstance(trip_result, dict) and "actual_start_date" in trip_result:
            display_start_date = trip_result["actual_start_date"]
        
        tbd_games_in_period = None
        if isinstance(trip_result, dict):
            tbd_games_in_period = trip_result.get("TBD_Games") or trip_result.get("tbd_games")
        
        # Create base response object
        base_response = {
            "start_location": request.start_location,
            "start_date": display_start_date,
            "max_travel_time": f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
            "trip_duration": f"{request.trip_duration} days",
            "preferred_leagues": request.preferred_leagues or "All Leagues",
            "must_teams": request.must_teams,
            "tbd_games": tbd_games_in_period
        }
        
        # Handle error cases
        if isinstance(trip_result, dict) and "error" in trip_result:
            return JSONResponse(content=trip_result, status_code=400)
            
        # Handle no trips available
        if isinstance(trip_result, dict) and "no_trips_available" in trip_result:
            response = FormattedResponse(
                **base_response,
                no_trips_available=True,
                message="No scheduled games found during this period."
            )
            print_formatted_trip_schedule(response)
            return JSONResponse(content=response.model_dump(), status_code=200)
        
        # Extract trip schedule
        trip_schedule = trip_result.get("trips", trip_result) if isinstance(trip_result, dict) else trip_result
        
        # Validate trip schedule
        if not trip_schedule or not isinstance(trip_schedule, list):
            response = FormattedResponse(
                **base_response,
                no_trips_available=True,
                message="No trip found. No available games during this period."
            )
            print_formatted_trip_schedule(response)
            return JSONResponse(content=response.model_dump(), status_code=200)
            
        # Check for matches in the schedule
        has_matches = any(
            isinstance(day, dict) and day.get("matches")
            for trip in trip_schedule if isinstance(trip, list)
            for day in trip
        )
        
        if not has_matches:
            response = FormattedResponse(
                **base_response,
                no_trips_available=True,
                message="No scheduled games found during this period."
            )
            print_formatted_trip_schedule(response)
            return JSONResponse(content=response.model_dump(), status_code=200)
        
        # Format trips
        formatted_trips = [{"Trip Number": i, "Itinerary": trip}
                           for i, trip in enumerate(trip_schedule, start=1)
                           if isinstance(trip, list)]
        
        # Sort trips by number of matches (descending) and then by total travel time
        sorted_trips = sorted(
            formatted_trips,
            key=lambda t: (-sum(len(day.get("matches", [])) for day in t["Itinerary"]), 
                         calculate_total_travel_time(t))
        )
        
        # Process trip groups
        trip_groups = identify_similar_trips(sorted_trips)
        
        # Process each group to add metadata
        structured_groups = process_trip_groups(trip_groups, request.start_location, train_times)
        
        # Create final response
        response = FormattedResponse(
            **base_response,
            no_trips_available=False,
            trip_groups=structured_groups
        )
        
        print_formatted_trip_schedule(response)
        return JSONResponse(content=response.model_dump(), status_code=200)
        
    except Exception as e:
        print(f"Unexpected error in get_trip: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=500
        )

#======================================================
# API ROUTES - REFERENCE DATA
#======================================================

@app.get("/available-leagues", 
         summary="Get all available leagues",
         description="Returns a list of all leagues available in the system",
         tags=["Reference Data"])
def get_leagues():
    try:
        leagues = set()
        for game in games:  
            if hasattr(game, 'league'):
                leagues.add(game.league)
        
        # Sort leagues by priority or alphabetically
        sorted_leagues = sorted(list(leagues), 
                               key=lambda x: league_priority.get(x, 999))
        
        return {"leagues": sorted_leagues}
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to retrieve leagues: {str(e)}"},
            status_code=500
        )

@app.get("/available-teams",
         summary="Get all available teams",
         description="Returns a list of all teams in the system, optionally filtered by league",
         tags=["Reference Data"])
def get_teams(league: Optional[str] = Query(None, description="Filter teams by league")):
    """Get all available teams, optionally filtered by league."""
    teams = set()
    
    for game in games:  # games contains regular games
        if league and hasattr(game, 'league') and game.league != league:
            continue
            
        if hasattr(game, 'home_team'):
            teams.add(game.home_team)
        if hasattr(game, 'away_team'):
            teams.add(game.away_team)
    
    # Sort teams alphabetically 
    sorted_teams = sorted(list(teams))
    
    return {"teams": sorted_teams}

@app.get("/available-cities",
         summary="Get all available cities",
         description="Returns a list of all cities (train stations) in the system",
         tags=["Reference Data"])
def get_cities():
    """Get all available cities for the start location selection."""
    # Extract unique cities from train_times keys
    cities = set()
    
    for key_pair in train_times.keys():
        cities.add(key_pair[0])
        cities.add(key_pair[1])
    
    # Add "Any" as first option
    cities_list = ["Any"] + sorted([city for city in cities if city != "Any"])
    
    # Clean city names for display (removing 'hbf' suffix)
    display_cities = [(city, city.replace(" hbf", "")) for city in cities_list]
    
    return {
        "cities": [
            {"id": city[0], "name": city[1]} for city in display_cities
        ]
    }

@app.get("/available-dates",
         summary="Get dates with available matches",
         description="Returns a list of dates that have scheduled matches, optionally filtered by league",
         tags=["Reference Data"])
def get_available_dates(
    league: Optional[str] = Query(None, description="Filter dates by league"),
    team: Optional[str] = Query(None, description="Filter dates by team"),
    days: int = Query(60, description="Number of days to look ahead")
):
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days)
    
    date_matches = {}
    
    # Process regular games
    for game in games:
        if not hasattr(game, 'date'):
            continue
            
        game_date = game.date.date()
        if game_date < start_date or game_date > end_date:
            continue
            
        # Apply league filter if specified
        if league and hasattr(game, 'league') and game.league != league:
            continue
            
        # Apply team filter if specified
        if team:
            team_lower = team.lower()
            if not ((hasattr(game, 'home_team') and game.home_team.lower() == team_lower) or
                   (hasattr(game, 'away_team') and game.away_team.lower() == team_lower)):
                continue
        
        # Format date as string
        date_str = game_date.strftime("%Y-%m-%d")
        
        if date_str not in date_matches:
            date_matches[date_str] = {
                "date": game_date.strftime("%d %B"),
                "count": 0,
                "leagues": set()
            }
            
        date_matches[date_str]["count"] += 1
        if hasattr(game, 'league'):
            date_matches[date_str]["leagues"].add(game.league)
    
    # Convert sets to lists for JSON serialization
    for date_str in date_matches:
        date_matches[date_str]["leagues"] = list(date_matches[date_str]["leagues"])
    
    # Return dates sorted chronologically
    return {
        "dates": [
            {
                "date": date_str,
                "display": date_matches[date_str]["date"],
                "matches": date_matches[date_str]["count"],
                "leagues": date_matches[date_str]["leagues"]
            }
            for date_str in sorted(date_matches.keys())
        ]
    }

#======================================================
# API ROUTES - TRAVEL DATA
#======================================================

@app.get("/city-connections/{city}",
         summary="Get cities reachable from a specific city",
         description="Returns a list of cities that are reachable within a given time from the specified city",
         tags=["Travel Data"])
def get_city_connections(
    city: str = Path(..., description="The city name to check connections from"),
    max_time: int = Query(240, description="Maximum travel time in minutes")
):
    """Get cities reachable within specified time from a given city."""
    if city.lower() == "any":
        return JSONResponse(
            content={"error": "Cannot get connections for 'Any'. Please specify a city."},
            status_code=400
        )
            
    # Find exact match for city (case insensitive)
    city_match = None
    for city_key in set(c for pair in train_times.keys() for c in pair):
        if city_key.lower() == city.lower():
            city_match = city_key
            break
    
    if not city_match:
        return JSONResponse(
            content={"error": f"City '{city}' not found in the database."},
            status_code=404
        )
    
    connections = []
    
    # Find all reachable cities
    for city_pair, travel_time in train_times.items():
        if city_pair[0] == city_match and travel_time <= max_time:
            dest_city = city_pair[1]
            connections.append({
                "city": dest_city,
                "display_name": dest_city.replace(" hbf", ""),
                "travel_time": travel_time,
                "travel_time_formatted": f"{travel_time // 60}h {travel_time % 60}m"
            })
    
    # Sort by travel time
    connections.sort(key=lambda x: x["travel_time"])
    
    return {
        "source_city": city_match,
        "display_name": city_match.replace(" hbf", ""),
        "connections": connections,
        "count": len(connections)
    }

#======================================================
# API ROUTES - TEAM DATA
#======================================================

@app.get("/team-schedule/{team}",
         summary="Get a team's schedule",
         description="Returns the schedule for a specific team",
         tags=["Team Data"])
def get_team_schedule(
    team: str = Path(..., description="The team name"),
    days: int = Query(60, description="Number of days to look ahead")
):
    """Get upcoming schedule for a specific team."""
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days)
    team_lower = team.lower()
    
    # Find matching team with correct capitalization
    team_name = None
    all_teams = set()
    for game in games:
        if hasattr(game, 'home_team'):
            all_teams.add(game.home_team)
        if hasattr(game, 'away_team'):
            all_teams.add(game.away_team)
    
    for t in all_teams:
        if t.lower() == team_lower:
            team_name = t
            break
    
    if not team_name:
        return JSONResponse(
            content={"error": f"Team '{team}' not found in the database."},
            status_code=404
        )
    
    # Find all matches for this team
    upcoming_matches = []
    for game in games:
        if not (hasattr(game, 'date') and hasattr(game, 'home_team') and hasattr(game, 'away_team')):
            continue
            
        game_date = game.date.date()
        if game_date < start_date or game_date > end_date:
            continue
            
        is_home = hasattr(game, 'home_team') and game.home_team.lower() == team_lower
        is_away = hasattr(game, 'away_team') and game.away_team.lower() == team_lower
        
        if not (is_home or is_away):
            continue
            
        upcoming_matches.append({
            "date": game_date.strftime("%d %B %Y"),
            "time": game.time,
            "opponent": game.away_team if is_home else game.home_team,
            "is_home": is_home,
            "league": game.league if hasattr(game, 'league') else "Unknown",
            "location": game.hbf_location if hasattr(game, 'hbf_location') else "Unknown",
            "display_location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown"
        })
    
    # Also add TBD games
    tbd_matches = []
    for game in tbd_games:
        if not (hasattr(game, 'date') and hasattr(game, 'home_team') and hasattr(game, 'away_team')):
            continue
            
        game_date = game.date.date()
        if game_date < start_date or game_date > end_date:
            continue
            
        is_home = hasattr(game, 'home_team') and game.home_team.lower() == team_lower
        is_away = hasattr(game, 'away_team') and game.away_team.lower() == team_lower
        
        if not (is_home or is_away):
            continue
            
        tbd_matches.append({
            "date": game_date.strftime("%d %B %Y"),
            "opponent": game.away_team if is_home else game.home_team,
            "is_home": is_home,
            "league": game.league if hasattr(game, 'league') else "Unknown",
            "location": game.hbf_location if hasattr(game, 'hbf_location') else "Unknown",
            "display_location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown"
        })
    
    return {
        "team": team_name,
        "matches": sorted(upcoming_matches, key=lambda x: x["date"]),
        "tbd_matches": sorted(tbd_matches, key=lambda x: x["date"]),
        "total_matches": len(upcoming_matches) + len(tbd_matches)
    }

#======================================================
# API ROUTES - SEARCH & UTILITY
#======================================================

@app.get("/search",
         summary="Search for teams, cities, or leagues",
         description="Searches across teams, cities, and leagues for the given query",
         tags=["Search"])
def search(
    q: str = Query(..., description="Search query (min 2 characters)"),
    types: List[str] = Query(["teams", "cities", "leagues"], description="Types of entities to search")
):
    """Search across teams, cities, and leagues."""
    if len(q) < 2:
        return JSONResponse(
            content={"error": "Search query must be at least 2 characters"},
            status_code=400
        )
            
    q_lower = q.lower()
    results = {
        "teams": [],
        "cities": [],
        "leagues": []
    }
    
    # Search teams
    if "teams" in types:
        all_teams = set()
        for game in games:
            if hasattr(game, 'home_team'):
                all_teams.add(game.home_team)
            if hasattr(game, 'away_team'):
                all_teams.add(game.away_team)
        
        matching_teams = [team for team in all_teams if q_lower in team.lower()]
        results["teams"] = sorted(matching_teams)
    
    # Search cities
    if "cities" in types:
        all_cities = set()
        for city_pair in train_times.keys():
            all_cities.add(city_pair[0].replace(" hbf", ""))
            all_cities.add(city_pair[1].replace(" hbf", ""))
        
        matching_cities = [city for city in all_cities if q_lower in city.lower()]
        results["cities"] = sorted(matching_cities)
    
    # Search leagues
    if "leagues" in types:
        all_leagues = set()
        for game in games:
            if hasattr(game, 'league'):
                all_leagues.add(game.league)
        
        matching_leagues = [league for league in all_leagues if q_lower in league.lower()]
        results["leagues"] = sorted(matching_leagues, key=lambda x: league_priority.get(x, 999))
    
    return {
        "query": q,
        "results": results,
        "total_results": sum(len(results[t]) for t in results)
    }

@app.get("/health", 
         summary="Health check",
         description="Simple endpoint to verify API is operational",
         tags=["System"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "games_loaded": len(games),
        "tbd_games_loaded": len(tbd_games)
    }