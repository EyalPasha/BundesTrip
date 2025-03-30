import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fastapi import FastAPI, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from utils import load_games, load_train_times, plan_trip, calculate_total_travel_time, identify_similar_trips, get_travel_minutes_utils, enhance_trip_planning_for_any_start
from models import TripRequest, FormattedResponse, TripVariation, TripGroup, TravelSegment
from scrapers.synonyms import AIRPORT_CITIES, league_priority
from config import GAMES_FILE, TRAIN_TIMES_FILE, CORS_ORIGINS

# Initialize FastAPI with metadata
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

@app.get("/")
def home():
    return {"message": "Welcome to the Multi-Game Trip Planner API"}

# ────────────────────────────────
# 🛠️ Helper Functions
# ────────────────────────────────

def has_special_suffix(location_name: str) -> bool:
    """Check if location has a special suffix that shouldn't have hbf appended"""
    special_suffixes = ["mitte", "bahnhof"]
    location_lower = location_name.lower()
    return any(suffix in location_lower for suffix in special_suffixes)


def get_date_sortkey(day_item: Dict) -> str:
    """Generate a sortable key for dates in format 'DD Month'"""
    day_str = day_item.get("day", "Unknown")
    if day_str == "Unknown":
        return "9999-99-99"  # Sort Unknown to the end
    
    try:
        # Parse date like "28 March"
        parts = day_str.split()
        if len(parts) >= 2:
            month_names = ["January", "February", "March", "April", "May", "June", 
                         "July", "August", "September", "October", "November", "December"]
            day = int(parts[0])
            month = month_names.index(parts[1]) + 1
            return f"2025-{month:02d}-{day:02d}"  # Use fixed year for sorting
    except:
        pass
    
    return day_str  # Fallback to string sorting


def sort_date_string(day_str: str) -> str:
    """Sort dates in string format 'DD Month'"""
    if day_str == "Unknown":
        return "9999-99-99"  # Sort unknown to end
    
    try:
        parts = day_str.split()
        if len(parts) >= 2:
            month_names = ["January", "February", "March", "April", "May", "June", 
                        "July", "August", "September", "October", "November", "December"]
            day = int(parts[0])
            month = month_names.index(parts[1]) + 1
            return f"2025-{month:02d}-{day:02d}"
    except:
        pass
    
    return day_str


def format_travel_time(minutes: Optional[int]) -> str:
    """Format travel time in minutes to 'Xh Ym' format"""
    if minutes is None:
        return "Unknown"
    
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def get_minutes(time_str: str) -> int:
    """Convert time string to minutes for sorting"""
    if time_str == "0h 0m":
        return 0
    if time_str == "Unknown":
        return float('inf')
    
    parts = time_str.split('h ')
    hours = int(parts[0])
    minutes = int(parts[1].replace('m', ''))
    return hours * 60 + minutes


def process_travel_segments(
    sorted_days: List[Dict],
    variant_detail: TripVariation,
    start_location: str,
    match_by_day: Dict[str, str],
    hotel_by_day: Dict[str, str]
) -> List[str]:
    """
    Process and generate travel segments for an itinerary, correctly handling hotel changes
    on match days.
    """
    travel_segments_text = []
    seen_segments = set()  # Track unique segments
    
    # Sort days chronologically
    sorted_dates = sorted([day.get("day") for day in sorted_days if isinstance(day, dict) and day.get("day")],
                         key=lambda d: datetime.strptime(d + " 2025", "%d %B %Y"))
    
    prev_hotel_location = variant_detail.start_location
    
    # Process day by day
    for i, date_str in enumerate(sorted_dates):
        # Get hotel for this day
        current_hotel = hotel_by_day.get(date_str)
        if not current_hotel:
            continue
            
        # Get match location for this day
        match_location = match_by_day.get(date_str)
        
        # Clean up location names
        from_loc_clean = prev_hotel_location.replace(" hbf", "")
        to_loc_clean = current_hotel.replace(" hbf", "")
        match_loc_clean = match_location.replace(" hbf", "") if match_location else None
        
        # First day special handling (travel from start location to first hotel)
        if i == 0 and from_loc_clean.lower() != to_loc_clean.lower():
            travel_minutes = get_travel_minutes_utils(train_times, from_loc_clean, to_loc_clean)
            if travel_minutes and travel_minutes > 0:
                travel_time = format_travel_time(travel_minutes)
                segment_key = (from_loc_clean, to_loc_clean, date_str)
                
                if segment_key not in seen_segments:
                    seen_segments.add(segment_key)
                    travel_segments_text.append(
                        f"{from_loc_clean} → {to_loc_clean} ({date_str}) - {travel_time}"
                    )
        
        # Match day handling
        if match_location:
            # Case 1: Match at same location as current hotel
            if match_loc_clean and match_loc_clean.lower() == to_loc_clean.lower():
                # Just add zero-time segment for after game
                segment_key = (match_loc_clean, to_loc_clean, f"{date_str}, After Game")
                if segment_key not in seen_segments:
                    seen_segments.add(segment_key)
                    travel_segments_text.append(
                        f"{match_loc_clean} → {to_loc_clean} ({date_str}, After Game) - 0h 0m"
                    )
            
            # Case 2: Match at different location than hotel
            elif match_loc_clean:
                # Travel to match
                travel_minutes = get_travel_minutes_utils(train_times, to_loc_clean, match_loc_clean)
                if travel_minutes and travel_minutes > 0:
                    travel_time = format_travel_time(travel_minutes)
                    segment_key = (to_loc_clean, match_loc_clean, date_str)
                    
                    if segment_key not in seen_segments:
                        seen_segments.add(segment_key)
                        travel_segments_text.append(
                            f"{to_loc_clean} → {match_loc_clean} ({date_str}) - {travel_time}"
                        )
                
                # Return from match
                travel_minutes = get_travel_minutes_utils(train_times, match_loc_clean, to_loc_clean)
                if travel_minutes and travel_minutes > 0:
                    travel_time = format_travel_time(travel_minutes)
                    segment_key = (match_loc_clean, to_loc_clean, f"{date_str}, After Game")
                    
                    if segment_key not in seen_segments:
                        seen_segments.add(segment_key)
                        travel_segments_text.append(
                            f"{match_loc_clean} → {to_loc_clean} ({date_str}, After Game) - {travel_time}"
                        )
        
        # Handle hotel change to next day (but only if there's a next day)
        if i < len(sorted_dates) - 1:
            next_date = sorted_dates[i + 1]
            next_hotel = hotel_by_day.get(next_date)
            
            if next_hotel and next_hotel.lower() != current_hotel.lower():
                next_hotel_clean = next_hotel.replace(" hbf", "")
                
                travel_minutes = get_travel_minutes_utils(train_times, to_loc_clean, next_hotel_clean)
                if travel_minutes and travel_minutes > 0:
                    travel_time = format_travel_time(travel_minutes)
                    segment_key = (to_loc_clean, next_hotel_clean, next_date)
                    
                    if segment_key not in seen_segments:
                        seen_segments.add(segment_key)
                        travel_segments_text.append(
                            f"{to_loc_clean} → {next_hotel_clean} ({next_date}) - {travel_time}"
                        )
        
        # Update for next iteration
        prev_hotel_location = current_hotel
    
    return travel_segments_text

def process_hotel_information(sorted_days: List[Dict]) -> List[str]:
    """Process hotel changes and stays for an itinerary"""
    hotel_info = []
    prev_hotel = None
    processed_days = set()  # Track which days we've already processed
    
    for day in sorted_days:
        day_str = day.get("day")
        hotel = day.get("hotel")
        
        # Skip if we've already processed this day or it's unknown
        if not day_str or not hotel or day_str == "Unknown" or day_str in processed_days:
            continue
            
        processed_days.add(day_str)  # Mark this day as processed
        
        # Check if this is a hotel change
        is_change = prev_hotel is not None and hotel != prev_hotel
        hotel_clean = hotel.replace(" hbf", "")
        
        if is_change:
            hotel_info.append(f"{day_str}: Change hotel to {hotel_clean}")
        else:
            hotel_info.append(f"{day_str}: Stay in hotel in {hotel_clean}")
        
        prev_hotel = hotel
        
    return hotel_info

def process_trip_variant(variant: Dict, actual_start_location: str) -> TripVariation:
    """Process a trip variant and extract its details"""
    total_travel_time = calculate_total_travel_time(variant, train_times, actual_start_location)

    # Extract cities, teams, and count games
    cities = set()
    teams = set()
    num_games = 0
    end_location = actual_start_location  # Default in case we find no locations
    
    # Extract from itinerary and determine the end location
    for day in variant["Itinerary"]:
        # Process location
        if "location" in day and day["location"] != "Unknown" and not day["location"].startswith("Any"):
            # Update end_location with the most recent location
            end_location = day["location"]
            # Clean city name for display
            clean_city = day["location"].replace(" hbf", "")
            cities.add(clean_city)
        
        # Process matches for teams and increment game count
        for match in day.get("matches", []):
            num_games += 1
            
            # Extract team names from match string (format: "Team1 vs Team2 (time)")
            if "match" in match:
                match_parts = match["match"].split(" vs ")
                if len(match_parts) == 2:
                    home_team = match_parts[0].strip()
                    away_team = match_parts[1].split(" (")[0].strip()
                    teams.add(home_team)
                    teams.add(away_team)
    
    # Clean start and end locations for display
    clean_start_location = actual_start_location.replace(" hbf", "")
    
    # Determine the true ending location - where person will actually end up
    true_end_location = None
    # First, get the location of the last night's hotel stay
    last_hotel_location = None
    for day in reversed(variant["Itinerary"]):
        if "hotel" in day:
            last_hotel_location = day["hotel"]
            break
    
    # Then check if there's a return travel on the last day with matches
    last_day_with_matches = None
    for day in reversed(variant["Itinerary"]):
        if day.get("matches"):
            last_day_with_matches = day
            break
    
    true_end_location = last_hotel_location or end_location
    clean_end_location = true_end_location.replace(" hbf", "") if true_end_location else clean_start_location
    
    # Calculate airport distances
    airport_distances = {
        "start": [],
        "end": []
    }
    
    # Get distances from actual start location to all airports
    for airport in AIRPORT_CITIES:
        # Skip if it's the same location
        if airport.lower() == actual_start_location.lower():
            airport_distances["start"].append({
                "airport": airport.replace(" hbf", ""),
                "travel_time": "0h 0m"
            })
            continue
        
        # Get travel time from train_times dictionary
        travel_minutes = train_times.get((actual_start_location, airport), None)
        travel_time = format_travel_time(travel_minutes)
            
        airport_distances["start"].append({
            "airport": airport.replace(" hbf", ""),
            "travel_time": travel_time
        })
    
    # Get distances from end location to all airports
    for airport in AIRPORT_CITIES:
        # Skip if it's the same location
        if airport.lower() == true_end_location.lower():
            airport_distances["end"].append({
                "airport": airport.replace(" hbf", ""),
                "travel_time": "0h 0m"
            })
            continue
        
        # Get travel time from train_times dictionary
        travel_minutes = train_times.get((true_end_location, airport), None)
        travel_time = format_travel_time(travel_minutes)
            
        airport_distances["end"].append({
            "airport": airport.replace(" hbf", ""),
            "travel_time": travel_time
        })
    
    # Sort airport distances by travel time
    airport_distances["start"].sort(key=lambda x: get_minutes(x["travel_time"]))
    airport_distances["end"].sort(key=lambda x: get_minutes(x["travel_time"]))
    
    # Convert sets to sorted lists for consistent output
    cities_list = sorted(list(cities))
    teams_list = sorted(list(teams))
    
    # Extract hotel information
    hotel_stats = None
    for day in variant["Itinerary"]:
        if isinstance(day, dict) and not day.get("matches") and not day.get("day") and "hotel_changes" in day:
            hotel_stats = day
            break
    
    hotel_changes = hotel_stats.get("hotel_changes", 0) if hotel_stats else 0
    unique_hotels = hotel_stats.get("unique_hotels", 0) if hotel_stats else 0
    hotel_locations = hotel_stats.get("hotel_locations", []) if hotel_stats else []
    hotel_stays = hotel_stats.get("hotel_stays", []) if hotel_stats else []
    
    # Process hotel details and travel segments
    sorted_days = []
    for day in variant["Itinerary"]:
        if isinstance(day, dict) and "day" in day and "hotel" in day:
            sorted_days.append(day)
    
    sorted_days = sorted(sorted_days, key=get_date_sortkey)
    
    # Create dicts to track location data for travel segments
    hotel_by_day = {}
    match_by_day = {}
    
    # Map days to hotels and match locations
    for day in sorted_days:
        if "day" in day and "hotel" in day:
            day_name = day["day"]
            hotel_by_day[day_name] = day["hotel"]
        
        if "day" in day and "matches" in day and day["matches"]:
            day_name = day["day"]
            match_location = day["matches"][0]["location"]
            match_by_day[day_name] = match_location
    
    # Process travel segments
    travel_segments_text = process_travel_segments(
        sorted_days, 
        TripVariation(
            total_travel_time=total_travel_time,
            travel_hours=total_travel_time // 60,
            travel_minutes=total_travel_time % 60,
            travel_segments=[],
            cities=cities_list,
            teams=teams_list,
            num_games=num_games,
            start_location=clean_start_location,
            end_location=clean_end_location,
            airport_distances=airport_distances,
            hotel_changes=hotel_changes,
            unique_hotels=unique_hotels,
            hotel_locations=[loc.replace(" hbf", "") for loc in hotel_locations],
            hotel_stays=hotel_stays
        ),
        actual_start_location, 
        match_by_day, 
        hotel_by_day
    )
    
    # Convert text segments to TravelSegment objects
    travel_segments = []
    for segment_text in travel_segments_text:
        # Parse segment text like "Berlin → Frankfurt (29 March) - 3h 59m"
        try:
            parts = segment_text.split(" → ")
            from_location = parts[0]
            
            # Extract to_location and the rest
            rest_parts = parts[1].split(" (")
            to_location = rest_parts[0]
            
            # Extract day and context
            day_context = rest_parts[1].split(")")[0]
            day = day_context
            context = None
            if "," in day_context:
                day_parts = day_context.split(", ")
                day = day_parts[0]
                context = day_parts[1]
            
            # Extract travel time
            travel_time = segment_text.split(" - ")[1]
            
            travel_segments.append(TravelSegment(
                from_location=from_location,
                to_location=to_location,
                day=day,
                context=context,
                travel_time=travel_time
            ))
        except Exception as e:
            # If parsing fails, add a simple version
            travel_segments.append(TravelSegment(
                from_location="Unknown",
                to_location="Unknown",
                travel_time=segment_text
            ))
    
    # Get hotel details
    hotel_details = []
    if sorted_days:
        hotel_details = process_hotel_information(sorted_days)
    
    # Create day-by-day itinerary
    day_itinerary = []
    day_map = {}
    day_order = []
    
    # Process the itinerary
    for day_item in variant["Itinerary"]:
        day_name = day_item.get("day", "Unknown")
        
        # Skip days with "Unknown" date
        if day_name == "Unknown":
            continue
        
        if day_name not in day_map:
            day_map[day_name] = {"matches": [], "locations": [], "hotel": None}
            day_order.append(day_name)  # preserve order
            
        # Add matches
        if day_item.get("matches"):
            day_map[day_name]["matches"].extend([{
                "match": m["match"],
                "location": m["location"].replace(" hbf", ""),
                "travel_from": m.get("travel_from", "").replace(" hbf", ""),
                "travel_time": m.get("travel_time", ""),
                "contains_must_team": m.get("contains_must_team", False)
            } for m in day_item["matches"]])
            
        # Add hotel
        if "hotel" in day_item:
            day_map[day_name]["hotel"] = day_item["hotel"].replace(" hbf", "")
            
        # If no matches, treat as rest-day item -> store location
        if not day_item.get("matches") and "location" in day_item:
            day_map[day_name]["locations"].append(day_item["location"].replace(" hbf", ""))
    
    # Convert day map to ordered list
    for day_name in day_order:
        day_info = day_map[day_name]
        day_itinerary.append({
            "day": day_name,
            "matches": day_info["matches"],
            "locations": day_info["locations"],
            "hotel": day_info["hotel"],
            "is_rest_day": len(day_info["matches"]) == 0
        })
    
    # Add variation details with actual start location
    return TripVariation(
        total_travel_time=total_travel_time,
        travel_hours=total_travel_time // 60,
        travel_minutes=total_travel_time % 60,
        travel_segments=travel_segments,
        cities=cities_list,
        teams=teams_list,
        num_games=num_games,
        start_location=clean_start_location,
        end_location=clean_end_location,
        airport_distances=airport_distances,
        hotel_changes=hotel_changes,
        unique_hotels=unique_hotels,
        hotel_locations=[loc.replace(" hbf", "") for loc in hotel_locations],
        hotel_stays=hotel_stays,
        # Add these fields to the object - they'll be included in the JSON serialization
        hotel_details=hotel_details,
        day_itinerary=day_itinerary
    )


def print_formatted_trip_schedule(response: FormattedResponse) -> str:
    """Format trip schedule for display using pre-calculated data from TripVariation objects"""
    output = []

    output.append(f"📍 Start Location: {response.start_location.replace(' hbf', '')}")
    output.append(f"📅 Start Date: {response.start_date}")
    output.append(f"⏳ Max Travel Time: {response.max_travel_time}")
    output.append(f"🗓️ Trip Duration: {response.trip_duration}")
    output.append(
        f"🏆 Preferred Leagues: "
        f"{', '.join(response.preferred_leagues) if isinstance(response.preferred_leagues, list) else response.preferred_leagues}"
    )
    
    # Add must_teams display
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

            # Add common metadata summary if available
            if group.variation_details and group.variation_details[0]:
                variant = group.variation_details[0]
                
                # Display actual start location if original was "Any"
                if response.start_location.lower() == "any":
                    output.append(f"📍 Starting City: {variant.start_location}")
                
                output.append(f"🏙️  Cities: {', '.join(variant.cities)}")
                output.append(f"⚽ Teams: {', '.join(variant.teams)}")
                output.append(f"🏟️  Number of Games: {variant.num_games}")

                if variant.airport_distances and "start" in variant.airport_distances:
                    airport_text = ", ".join(
                        [f"{a['airport']} ({a['travel_time']})"
                         for a in variant.airport_distances["start"][:3]]
                    )
                    
                    # Use variant.start_location if start_location is "Any"
                    display_location = variant.start_location if response.start_location.lower() == "any" else response.start_location.replace(' hbf', '')
                    output.append(
                        f"✈️  Airports near start location "
                        f"({display_location}): "
                        f"{airport_text}"
                    )

                output.append("")

            # Use the pre-calculated day-by-day itinerary from the base variant
            base_variant = group.variation_details[0] if group.variation_details else None
            
            if base_variant and base_variant.day_itinerary:
                # Print each day in chronological order
                for day_info in base_variant.day_itinerary:
                    day_name = day_info.get("day", "Unknown")
                    output.append(f"📅 {day_name}")

                    if day_info.get("matches"):
                        # Single or multiple matches?
                        if len(day_info["matches"]) == 1:
                            output.append("   ⚽ Match:")
                        else:
                            output.append("   ⚽ Matches:")
                        for match in day_info["matches"]:
                            # Highlight matches with must_teams
                            match_prefix = "🌟 " if match.get("contains_must_team", False) else ""
                            output.append(f"      {match_prefix}🏟️  {match['match']}")
                            output.append(f"      📍 {match['location']}")
                    else:
                        output.append(f"   💤 Rest Day")

                    output.append("")

            # Travel options - use pre-calculated variation details
            if len(group.variations) > 1:
                output.append("   🔄 Travel Options:")
                for var_idx, variant_detail in enumerate(group.variation_details):
                    # Use pre-calculated total travel time
                    output.append(
                        f"      🚆 Option {var_idx+1}: "
                        f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
                        f"ending in {variant_detail.end_location}:"
                    )
                    
                    # Add hotel information for this specific travel option
                    output.append(f"      🏨 Hotel Changes: {variant_detail.hotel_changes}")
                    output.append(f"      🏨 Unique Hotels: {variant_detail.unique_hotels}")
                    if variant_detail.hotel_locations:
                        output.append(f"      🏨 Hotel Locations: {', '.join(variant_detail.hotel_locations)}")

                    # End airports
                    if variant_detail.airport_distances and "end" in variant_detail.airport_distances:
                        top_airports = variant_detail.airport_distances["end"][:3]
                        if top_airports:
                            airport_text = ", ".join(
                                [f"{a['airport']} ({a['travel_time']})"
                                 for a in top_airports]
                            )
                            output.append(
                                f"      ✈️  Nearest airports to {variant_detail.end_location}: {airport_text}"
                            )
                    
                    # Use pre-calculated hotel details
                    output.append(f"      🏨 Hotel Details:")
                    for detail in variant_detail.hotel_details:
                        output.append(f"        {detail}")
                    
                    # Use pre-calculated travel segments
                    travel_segments_text = [
                        f"{segment.from_location} → {segment.to_location} "
                        f"({segment.day}{', ' + segment.context if segment.context else ''}) - "
                        f"{segment.travel_time}"
                        for segment in variant_detail.travel_segments
                    ]
                    
                    output.append("      " + "\n      ".join(travel_segments_text))

                    if var_idx < len(group.variation_details) - 1:
                        output.append("")
            else:
                # Single travel option - use the pre-processed data
                variant_detail = group.variation_details[0] if group.variation_details else None
                if variant_detail:
                    output.append(
                        f"   ℹ️  Only one travel option: "
                        f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
                        f"ending in {variant_detail.end_location}"
                    )

                    # Add hotel information from the variant detail
                    output.append(f"   🏨 Hotel Changes: {variant_detail.hotel_changes}")
                    output.append(f"   🏨 Unique Hotels: {variant_detail.unique_hotels}")
                    if variant_detail.hotel_locations:
                        output.append(f"   🏨 Hotel Locations: {', '.join(variant_detail.hotel_locations)}")
                    
                    # End airports
                    if variant_detail.airport_distances and "end" in variant_detail.airport_distances:
                        top_airports = variant_detail.airport_distances["end"][:3]
                        if top_airports:
                            airport_text = ", ".join(
                                [f"{a['airport']} ({a['travel_time']})"
                                for a in top_airports]
                            )
                            output.append(
                                f"   ✈️  Nearest airports to {variant_detail.end_location}: {airport_text}"
                            )

                    # Use pre-calculated hotel details 
                    output.append(f"   🏨 Hotel Details:")
                    for detail in variant_detail.hotel_details:
                        output.append(f"        {detail}")
                    
                    # Use pre-calculated travel segments
                    travel_segments_text = [
                        f"{segment.from_location} → {segment.to_location} "
                        f"({segment.day}{', ' + segment.context if segment.context else ''}) - "
                        f"{segment.travel_time}"
                        for segment in variant_detail.travel_segments
                    ]
                    
                    output.append("      " + "\n      ".join(travel_segments_text))

            output.append("")  # Blank line after each trip group

    # TBD games
    if response.tbd_games:
        output.append("\n📝 Upcoming Unscheduled Games:")
        output.append("These games don't have confirmed times yet but might be included in your trip once scheduled:")

        for game in sorted(response.tbd_games, key=lambda g: g["date"]):
            clean_location = game['location'].replace(' hbf', '')
            date_display = game['date']
            
            # Highlight TBD games with must_teams
            match_prefix = "🌟 " if game.get("has_must_team", False) else ""
            output.append(
                f"   • {match_prefix}{date_display} - {game['match']} @ {clean_location} ({game['league']})"
            )

        output.append("\nCheck back later for updated schedules!")

    print("\n".join(output))
    return "\n".join(output)

# ────────────────────────────────
# 🛠️ Get Trip
# ────────────────────────────────


@app.post("/plan-trip", 
          summary="Plan a multi-game trip",
          description="Creates an optimized itinerary to watch multiple games based on preferences",
          response_model=FormattedResponse)
def get_trip(request: TripRequest):
    try:
        # Input validation
        if request.trip_duration <= 0:
            return JSONResponse(
                content={"error": "Trip duration must be positive"},
                status_code=400
            )
            
        if request.max_travel_time <= 0:
            return JSONResponse(
                content={"error": "Maximum travel time must be positive"},
                status_code=400
            )
        
        # Filter games by preferred leagues
        if request.preferred_leagues:
            # Convert to set for O(1) lookup instead of O(n)
            preferred_lower = {league.lower() for league in request.preferred_leagues}
            
            # Use list comprehensions for more efficient filtering
            regular_games_filtered = [g for g in games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            tbd_games_filtered = [g for g in tbd_games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            
            # Check if no games match the preferred leagues
            if not regular_games_filtered and not tbd_games_filtered:
                return JSONResponse(
                    content={
                        "error": f"No games found for the selected leagues: {', '.join(request.preferred_leagues)}"
                    },
                    status_code=404
                )
                
            filtered_games = regular_games_filtered
            filtered_tbd_games = tbd_games_filtered
        else:
            filtered_games = games
            filtered_tbd_games = tbd_games
        
        # Check if must_teams exist in the dataset
        if request.must_teams:
            must_teams_lower = {team.lower() for team in request.must_teams}
            team_found = False
            
            for game in filtered_games:
                if (hasattr(game, 'home_team') and game.home_team.lower() in must_teams_lower) or \
                   (hasattr(game, 'away_team') and game.away_team.lower() in must_teams_lower):
                    team_found = True
                    break
                    
            if not team_found:
                for game in filtered_tbd_games:
                    if (hasattr(game, 'home_team') and game.home_team.lower() in must_teams_lower) or \
                       (hasattr(game, 'away_team') and game.away_team.lower() in must_teams_lower):
                        team_found = True
                        break
            
            if not team_found:
                return JSONResponse(
                    content={
                        "error": f"No games found for the requested teams: {', '.join(request.must_teams)}"
                    },
                    status_code=404
                )
        
        # Plan trip with optimized parameters
        # NEW: Use enhance_trip_planning_for_any_start for "Any" start location
        if request.start_location.lower() == "any":
            trip_result = enhance_trip_planning_for_any_start(
                start_location=request.start_location,
                trip_duration=request.trip_duration,
                max_travel_time=request.max_travel_time,
                games=filtered_games,
                train_times=train_times,
                tbd_games=filtered_tbd_games,
                preferred_leagues=request.preferred_leagues,
                start_date=request.start_date,
                must_teams=request.must_teams
            )
        else:
            trip_result = plan_trip(
                start_location=request.start_location,
                trip_duration=request.trip_duration,
                max_travel_time=request.max_travel_time,
                games=filtered_games,
                train_times=train_times,
                tbd_games=filtered_tbd_games,
                preferred_leagues=request.preferred_leagues,
                start_date=request.start_date,
                must_teams=request.must_teams
            )
        
        # Extract TBD games
        result_tbd_games = None
        
        # Get the actual start date used
        display_start_date = request.start_date or "Earliest Available"
        if isinstance(trip_result, dict) and "actual_start_date" in trip_result:
            display_start_date = trip_result["actual_start_date"]
        
        if isinstance(trip_result, dict):
            # Direct dictionary lookup is more efficient
            result_tbd_games = trip_result.get("TBD_Games") or trip_result.get("tbd_games")
            
            if "error" in trip_result and result_tbd_games:
                # Create structured response for TBD-only case
                structured_response = FormattedResponse(
                    start_location=request.start_location,
                    start_date=display_start_date,
                    max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                    trip_duration=f"{request.trip_duration} days",
                    preferred_leagues=request.preferred_leagues or "All Leagues",
                    must_teams=request.must_teams,
                    no_trips_available=True,
                    message="No scheduled games found, but there are TBD games during this period.",
                    tbd_games=result_tbd_games
                )
                print_formatted_trip_schedule(structured_response)
                return JSONResponse(content=structured_response.model_dump(), status_code=200)
            elif "error" in trip_result and not result_tbd_games:
                return JSONResponse(content=trip_result, status_code=400)
            
            # Extract trip schedule
            trip_schedule = trip_result.get("trips", trip_result)
            if "no_trips_available" in trip_result:
                structured_response = FormattedResponse(
                    start_location=request.start_location,
                    start_date=display_start_date,
                    max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                    trip_duration=f"{request.trip_duration} days",
                    preferred_leagues=request.preferred_leagues or "All Leagues",
                    must_teams=request.must_teams,
                    no_trips_available=True,
                    message="No scheduled games found during this period.",
                    tbd_games=result_tbd_games
                )
                print_formatted_trip_schedule(structured_response)
                return JSONResponse(content=structured_response.model_dump(), status_code=200)
        else:
            trip_schedule = trip_result

        # Early termination for invalid or empty trip schedules
        if not trip_schedule or not isinstance(trip_schedule, list):
            structured_response = FormattedResponse(
                start_location=request.start_location,
                start_date=display_start_date,
                max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                trip_duration=f"{request.trip_duration} days",
                preferred_leagues=request.preferred_leagues or "All Leagues",
                must_teams=request.must_teams,
                no_trips_available=True,
                message="No trip found. No available games during this period.",
                tbd_games=result_tbd_games
            )
            print_formatted_trip_schedule(structured_response)
            return JSONResponse(content=structured_response.model_dump(), status_code=200)

        # Check for matches
        has_matches = any(
            isinstance(day, dict) and day.get("matches")
            for trip in trip_schedule if isinstance(trip, list)
            for day in trip
        )
        
        if not has_matches:
            structured_response = FormattedResponse(
                start_location=request.start_location,
                start_date=display_start_date,
                max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                trip_duration=f"{request.trip_duration} days",
                preferred_leagues=request.preferred_leagues or "All Leagues",
                must_teams=request.must_teams,
                no_trips_available=True,
                message="No scheduled games found during this period.",
                tbd_games=result_tbd_games
            )
            print_formatted_trip_schedule(structured_response)
            return JSONResponse(content=structured_response.model_dump(), status_code=200)

        # Format trips
        formatted_trips = [
            {"Trip Number": i, "Itinerary": trip}
            for i, trip in enumerate(trip_schedule, start=1)
            if isinstance(trip, list)
        ]

        # Sort trips
        sorted_trips = sorted(
            formatted_trips,
            key=lambda t: (
                -sum(len(day.get("matches", [])) for day in t["Itinerary"]), 
                calculate_total_travel_time(t)
            )
        )
        
        # Process trip groups
        trip_groups = identify_similar_trips(sorted_trips)
        
        # Fix base trip data when start_location is "Any"
        for group in trip_groups:
            if request.start_location.lower() == "any" and group["Base"]["Itinerary"]:
                # Find the first match location
                first_match_location = None
                for day in group["Base"]["Itinerary"]:
                    if day.get("matches"):
                        first_match_location = day["matches"][0]["location"]
                        break
                        
                # If we found a first match location, update the starting location
                if first_match_location:
                    # Update the first day in the itinerary that has note="Start"
                    for day in group["Base"]["Itinerary"]:
                        if day.get("note") == "Start":
                            day["location"] = first_match_location
                            break
                            
                    # Also fix any travel_from fields in the first match
                    for day in group["Base"]["Itinerary"]:
                        if day.get("matches"):
                            for match in day["matches"]:
                                if match.get("location") == first_match_location:
                                    match["travel_from"] = first_match_location
                                    match["travel_time"] = "0h 0m"
                            break

        # Process trip groups
        structured_groups = []

        for group in trip_groups:
            variation_details = []
            
            # Process each variation
            for variant in group["Variations"]:
                # Determine actual start location
                actual_start_location = request.start_location
                if actual_start_location.lower() == "any":
                    # Find the first day with matches
                    for day in variant["Itinerary"]:
                        if day.get("matches"):
                            actual_start_location = day["matches"][0]["location"]
                            break
                            
                # Process variant details
                variation_details.append(process_trip_variant(variant, actual_start_location))
            
            # Add complete group
            structured_groups.append(TripGroup(
                base_trip=group["Base"],
                variations=group["Variations"],
                variation_details=variation_details
            ))
        
        # Create final response
        structured_response = FormattedResponse(
            start_location=request.start_location,
            start_date=display_start_date,
            max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
            trip_duration=f"{request.trip_duration} days",
            preferred_leagues=request.preferred_leagues or "All Leagues",
            must_teams=request.must_teams,
            no_trips_available=False,
            trip_groups=structured_groups,
            tbd_games=result_tbd_games
        )
        
        print_formatted_trip_schedule(structured_response)
        return JSONResponse(content=structured_response.model_dump(), status_code=200)
        
    except Exception as e:
        print(f"Unexpected error in get_trip: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=500
        )



# ────────────────────────────────
# 🛠️ API's
# ────────────────────────────────


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
    
    for game in games:
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
    """Get dates with available matches for the date picker."""
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

@app.get("/game-details/{league}/{date}",
         summary="Get game details for a specific date",
         description="Returns detailed information about games on a specific date for a league",
         tags=["Game Data"])
def get_game_details(
    league: str = Path(..., description="The league name"),
    date: str = Path(..., description="The date in YYYY-MM-DD format"),
):
    """Get detailed game information for a specific date and league."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return JSONResponse(
            content={"error": "Invalid date format. Please use YYYY-MM-DD."},
            status_code=400
        )
    
    # Filter games by league and date
    day_games = []
    
    for game in games:
        if not (hasattr(game, 'date') and hasattr(game, 'league')):
            continue
            
        game_date = game.date.date()
        if game_date == target_date and game.league == league:
            day_games.append({
                "match": f"{game.home_team} vs {game.away_team}",
                "time": game.time if hasattr(game, 'time') else "TBD",
                "location": game.hbf_location if hasattr(game, 'hbf_location') else "Unknown",
                "display_location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown",
                "league": game.league
            })
    
    return {
        "league": league,
        "date": date,
        "display_date": target_date.strftime("%d %B %Y"),
        "games": day_games,
        "count": len(day_games)
    }


@app.get("/league-schedule/{league}",
         summary="Get a league's schedule",
         description="Returns the schedule for a specific league",
         tags=["League Data"])
def get_league_schedule(
    league: str = Path(..., description="The league name"),
    days: int = Query(60, description="Number of days to look ahead")
):
    """Get upcoming schedule for a specific league."""
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days)
    
    # Find matching league with correct capitalization
    league_name = None
    all_leagues = set()
    for game in games:
        if hasattr(game, 'league'):
            all_leagues.add(game.league)
    
    for l in all_leagues:
        if l.lower() == league.lower():
            league_name = l
            break
    
    if not league_name:
        return JSONResponse(
            content={"error": f"League '{league}' not found in the database."},
            status_code=404
        )
    
    # Group games by date
    dates_with_games = {}
    for game in games:
        if not (hasattr(game, 'date') and hasattr(game, 'league') and game.league == league_name):
            continue
            
        game_date = game.date.date()
        if game_date < start_date or game_date > end_date:
            continue
            
        date_str = game_date.strftime("%Y-%m-%d")
        if date_str not in dates_with_games:
            dates_with_games[date_str] = {
                "date": game_date.strftime("%d %B %Y"),
                "games": []
            }
        
        dates_with_games[date_str]["games"].append({
            "match": f"{game.home_team} vs {game.away_team}",
            "time": game.time if hasattr(game, 'time') else "TBD",
            "location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown"
        })
    
    # Sort dates and games
    sorted_dates = sorted(dates_with_games.keys())
    schedule = []
    for date_str in sorted_dates:
        day_info = dates_with_games[date_str]
        schedule.append({
            "date": date_str,
            "display_date": day_info["date"],
            "games": day_info["games"],
            "game_count": len(day_info["games"])
        })
    
    return {
        "league": league_name,
        "schedule": schedule,
        "total_matchdays": len(schedule),
        "total_games": sum(day["game_count"] for day in schedule)
    }


@app.get("/airport-information",
         summary="Get airport information",
         description="Returns information about airports and their connections to cities",
         tags=["Travel Data"])
def get_airport_information(city: Optional[str] = Query(None, description="Filter for connections to a specific city")):
    """Get airport information and their connections to cities."""
    from scrapers.synonyms import AIRPORT_CITIES
    
    airports = []
    for airport in AIRPORT_CITIES:
        airport_clean = airport.replace(" hbf", "")
        
        # If city filter is provided, check connections
        if city:
            # Find exact match for city
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
            
            # Check if there's a direct connection
            travel_minutes = train_times.get((city_match, airport), None)
            if travel_minutes is None:
                continue
                
            travel_time = format_travel_time(travel_minutes)
            
            airports.append({
                "airport": airport_clean,
                "connections": [{
                    "city": city_match,
                    "display_name": city_match.replace(" hbf", ""),
                    "travel_time": travel_minutes,
                    "travel_time_formatted": travel_time
                }]
            })
        else:
            # Get all connections for this airport
            connections = []
            for city_pair, travel_time in train_times.items():
                if city_pair[0] == airport:
                    dest_city = city_pair[1]
                    connections.append({
                        "city": dest_city,
                        "display_name": dest_city.replace(" hbf", ""),
                        "travel_time": travel_time,
                        "travel_time_formatted": format_travel_time(travel_time)
                    })
            
            # Sort connections by travel time
            connections.sort(key=lambda x: x["travel_time"])
            
            airports.append({
                "airport": airport_clean,
                "connections": connections[:20]  # Limit to top 20 connections to avoid huge response
            })
    
    return {
        "airports": airports,
        "count": len(airports)
    }


@app.get("/travel-stats",
         summary="Get travel statistics",
         description="Returns statistics about travel times between cities",
         tags=["Travel Data"])
def get_travel_stats():
    """Get statistics about travel times between cities."""
    if not train_times:
        return JSONResponse(
            content={"error": "No travel data available"},
            status_code=500
        )
    
    # Calculate statistics
    travel_times = list(train_times.values())
    avg_travel_time = sum(travel_times) / len(travel_times) if travel_times else 0
    max_travel_time = max(travel_times) if travel_times else 0
    min_travel_time = min(travel_times) if travel_times else 0
    
    # Get most connected cities
    city_connections = {}
    for city_pair in train_times.keys():
        city1, city2 = city_pair
        
        if city1 not in city_connections:
            city_connections[city1] = 0
        city_connections[city1] += 1
        
        if city2 not in city_connections:
            city_connections[city2] = 0
        city_connections[city2] += 1
    
    # Sort cities by number of connections
    most_connected = sorted(
        [(city, count) for city, count in city_connections.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]  # Top 10
    
    # Get fastest and slowest connections
    fastest = sorted(
        [(pair, time) for pair, time in train_times.items()],
        key=lambda x: x[1]
    )[:5]  # Top 5 fastest
    
    slowest = sorted(
        [(pair, time) for pair, time in train_times.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]  # Top 5 slowest
    
    return {
        "total_connections": len(train_times),
        "average_travel_time": {
            "minutes": round(avg_travel_time),
            "formatted": format_travel_time(round(avg_travel_time))
        },
        "max_travel_time": {
            "minutes": max_travel_time,
            "formatted": format_travel_time(max_travel_time)
        },
        "min_travel_time": {
            "minutes": min_travel_time,
            "formatted": format_travel_time(min_travel_time)
        },
        "most_connected_cities": [
            {
                "city": city.replace(" hbf", ""),
                "connections": count
            }
            for city, count in most_connected
        ],
        "fastest_connections": [
            {
                "from": pair[0].replace(" hbf", ""),
                "to": pair[1].replace(" hbf", ""),
                "travel_time": {
                    "minutes": time,
                    "formatted": format_travel_time(time)
                }
            }
            for pair, time in fastest
        ],
        "slowest_connections": [
            {
                "from": pair[0].replace(" hbf", ""),
                "to": pair[1].replace(" hbf", ""),
                "travel_time": {
                    "minutes": time,
                    "formatted": format_travel_time(time)
                }
            }
            for pair, time in slowest
        ]
    }


@app.get("/games-by-date/{date}",
         summary="Get all games on a specific date",
         description="Returns all games scheduled for a specific date across all leagues",
         tags=["Game Data"])
def get_games_by_date(
    date: str = Path(..., description="The date in YYYY-MM-DD format"),
    league: Optional[str] = Query(None, description="Filter by league")
):
    """Get all games scheduled for a specific date."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return JSONResponse(
            content={"error": "Invalid date format. Please use YYYY-MM-DD."},
            status_code=400
        )
    
    # Filter games by date
    day_games = []
    
    for game in games:
        if not hasattr(game, 'date'):
            continue
            
        game_date = game.date.date()
        if game_date == target_date:
            # Apply league filter if specified
            if league and hasattr(game, 'league') and game.league != league:
                continue
                
            day_games.append({
                "match": f"{game.home_team} vs {game.away_team}",
                "time": game.time if hasattr(game, 'time') else "TBD",
                "location": game.hbf_location if hasattr(game, 'hbf_location') else "Unknown",
                "display_location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown",
                "league": game.league if hasattr(game, 'league') else "Unknown"
            })
    
    # Group by league
    by_league = {}
    for game in day_games:
        league_name = game["league"]
        if league_name not in by_league:
            by_league[league_name] = []
        by_league[league_name].append(game)
    
    return {
        "date": date,
        "display_date": target_date.strftime("%d %B %Y"),
        "total_games": len(day_games),
        "games_by_league": by_league,
        "leagues": list(by_league.keys())
    }

@app.post("/admin/refresh-data",
         summary="Refresh game and travel data",
         description="Reloads game schedules and train times from data files without restarting the server",
         tags=["Administration"])
def refresh_data(api_key: str = Query(..., description="API key for admin operations")):
    """Refresh all data from source files."""
    # Simple API key check (in production, use proper authentication)
    from config import ADMIN_API_KEY
    if api_key != ADMIN_API_KEY:
        return JSONResponse(
            content={"error": "Invalid API key"},
            status_code=401
        )
    
    try:
        global train_times, games, tbd_games
        
        # Reload data
        new_train_times = load_train_times(TRAIN_TIMES_FILE)
        new_games, new_tbd_games = load_games(GAMES_FILE)
        
        # Update global variables
        train_times = new_train_times
        games = new_games
        tbd_games = new_tbd_games
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "games_loaded": len(games),
            "tbd_games_loaded": len(tbd_games),
            "train_connections_loaded": len(train_times)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"error": f"Failed to refresh data: {str(e)}"},
            status_code=500
        )