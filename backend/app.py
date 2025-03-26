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


def get_travel_minutes(train_times, from_loc, to_loc):
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







def print_formatted_trip_schedule(response):
    """
    Print the trip schedule in a formatted way, grouping any duplicate days
    so that you don't get multiple lines for the same day. Preserves the original
    order of the itinerary as it appears in JSON.
    """
    output = []
    debug = []  # Debug output list

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
        # Define the special suffixes check function once, at the top level
        def has_special_suffix(location_name):
            special_suffixes = ["mitte", "süd", "nord", "ost", "west", "hbf", "bahnhof"]
            location_lower = location_name.lower()
            return any(suffix in location_lower for suffix in special_suffixes)
            
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
                
                # Remove hotel statistics from trip summary - it will be per travel option

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

            # Group items by day, but preserve the JSON order
            base_trip = group.base_trip
            day_map = {}
            day_order = []

            for day_item in base_trip["Itinerary"]:
                day_name = day_item.get("day", "Unknown")
                
                # Skip days with "Unknown" date
                if day_name == "Unknown":
                    continue
                
                if day_name not in day_map:
                    day_map[day_name] = {"matches": [], "locations": []}
                    day_order.append(day_name)  # preserve order

                day_map[day_name]["matches"].extend(day_item.get("matches", []))

                # If no matches, treat as rest-day item -> store location
                if not day_item.get("matches") and "location" in day_item:
                    day_map[day_name]["locations"].append(day_item["location"])

            # Now print the days in the order they appeared in the JSON
            for day_name in day_order:
                day_info = day_map[day_name]
                output.append(f"📅 {day_name}")

                if day_info["matches"]:
                    # Single or multiple matches?
                    if len(day_info["matches"]) == 1:
                        output.append("   ⚽ Match:")
                    else:
                        output.append("   ⚽ Matches:")
                    for match in day_info["matches"]:
                        clean_location = match['location'].replace(' hbf', '')
                        from_loc = match.get('travel_from', '').replace(' hbf', '')

                        # Handle "Any" in from_loc (should never happen with our fix, but just in case)
                        if from_loc.lower() == "any":
                            from_loc = group.variation_details[0].start_location if group.variation_details else clean_location

                        # Highlight matches with must_teams
                        match_prefix = "🌟 " if match.get("contains_must_team", False) else ""
                        output.append(f"      {match_prefix}🏟️  {match['match']}")
                        output.append(f"      📍 {clean_location}")

                else:
                    output.append(f"   💤 Rest Day")

                output.append("")

            # Travel options - add hotel info per option here
            if len(group.variations) > 1:
                output.append("   🔄 Travel Options:")
                for var_idx, variant_detail in enumerate(group.variation_details):
                    # Travel option header
                    output.append(
                        f"      🚆 Option {var_idx+1}: "
                        f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
                        f"ending in {variant_detail.end_location}:"
                    )
                    
                    # Add hotel information for this specific travel option
                    hotel_summary = None
                    for day in group.variations[var_idx]["Itinerary"]:
                        if isinstance(day, dict) and not day.get("matches") and not day.get("day") and "hotel_changes" in day:
                            hotel_summary = day
                            break
                    
                    if hotel_summary:
                        output.append(f"      🏨 Hotel Changes: {hotel_summary.get('hotel_changes', 0)}")
                        output.append(f"      🏨 Unique Hotels: {hotel_summary.get('unique_hotels', 0)}")
                        if "hotel_locations" in hotel_summary and hotel_summary["hotel_locations"]:
                            # Clean up hotel location names
                            clean_locations = [loc.replace(" hbf", "") for loc in hotel_summary["hotel_locations"]]
                            output.append(f"      🏨 Hotel Locations: {', '.join(clean_locations)}")

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
                    
                    # Now add day-by-day hotel information for this travel option
                    output.append(f"      🏨 Hotel Details:")
                    
                    # Create a chronological list of days for hotel details
                    prev_hotel = None
                    processed_days = set()  # Track which days we've already processed
                    
                    # Sort the itinerary days chronologically
                    sorted_days = []
                    for day in group.variations[var_idx]["Itinerary"]:
                        if isinstance(day, dict) and "day" in day and "hotel" in day:
                            sorted_days.append(day)
                    
                    # Sort by date
                    def get_date_sortkey(day_item):
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
                    
                    sorted_days = sorted(sorted_days, key=get_date_sortkey)
                    
                    # Process each day's hotel information
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
                            output.append(f"        {day_str}: Change hotel to {hotel_clean}")
                        else:
                            output.append(f"        {day_str}: Stay in hotel in {hotel_clean}")
                        
                        prev_hotel = hotel
                    
                    # Travel segments display with enhanced debugging
                    travel_segments_text = []
                    seen_segments = set()  # Track unique segments

                    # Create dicts to track location data
                    hotel_by_day = {}
                    match_by_day = {}
                    debug.append(f"DEBUG Trip {group_index} Option {var_idx+1} - Processing travel segments")
                    
                    # Map days to hotels and match locations
                    for day in sorted_days:
                        if "day" in day and "hotel" in day:
                            day_name = day["day"]
                            hotel_by_day[day_name] = day["hotel"]
                            debug.append(f"  Hotel for {day_name}: {day['hotel']}")
                        
                        if "day" in day and "matches" in day and day["matches"]:
                            day_name = day["day"]
                            match_location = day["matches"][0]["location"]
                            match_by_day[day_name] = match_location
                            debug.append(f"  Match for {day_name}: {match_location}")
                    
                    # Sort days chronologically
                    def sort_date_string(day_str):
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
                    
                    sorted_match_days = sorted(match_by_day.keys(), key=sort_date_string)
                    debug.append(f"  Sorted match days: {sorted_match_days}")
                    
                    # Start from actual start location
                    current_location = variant_detail.start_location
                    debug.append(f"  Starting location: {current_location}")
                    
                    # CRITICAL FIX 1: Always show first journey to match location
                    if sorted_match_days:
                        first_day = sorted_match_days[0]
                        first_match_location = match_by_day[first_day]
                        debug.append(f"  First match day: {first_day} at {first_match_location}")
                        
                        # Direct journey from start location to first match
                        if current_location != first_match_location:
                            from_loc_clean = current_location.replace(" hbf", "")
                            to_loc_clean = first_match_location.replace(" hbf", "")
                            
                            # Only append hbf if the location doesn't have a special suffix
                            from_with_hbf = from_loc_clean + " hbf" if not has_special_suffix(from_loc_clean) else from_loc_clean
                            to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                            
                            debug.append(f"  Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                            travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                            debug.append(f"  Travel minutes: {travel_minutes}")
                            
                            if travel_minutes and travel_minutes > 0:
                                travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                segment_key = (from_loc_clean, to_loc_clean, first_day)
                                debug.append(f"  Adding journey: {from_loc_clean} → {to_loc_clean} ({first_day}) - {travel_time}")
                                
                                if segment_key not in seen_segments:
                                    seen_segments.add(segment_key)
                                    travel_segments_text.append(
                                        f"{from_loc_clean} → {to_loc_clean} ({first_day}) - {travel_time}"
                                    )
                                    
                            # Update current location to first match location
                            current_location = first_match_location
                    
                    # CRITICAL FIX 2: Handle consecutive match days
                    for i in range(1, len(sorted_match_days)):
                        prev_day = sorted_match_days[i-1]
                        curr_day = sorted_match_days[i]
                        
                        prev_match_location = match_by_day[prev_day]
                        curr_match_location = match_by_day[curr_day]
                        
                        debug.append(f"  Processing consecutive days: {prev_day} → {curr_day}")
                        debug.append(f"  Locations: {prev_match_location} → {curr_match_location}")
                        
                        # If match locations differ, add a journey between them
                        if prev_match_location != curr_match_location:
                            from_loc_clean = prev_match_location.replace(" hbf", "")
                            to_loc_clean = curr_match_location.replace(" hbf", "")
                            
                            from_with_hbf = from_loc_clean + " hbf" if not has_special_suffix(from_loc_clean) else from_loc_clean
                            to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                            
                            debug.append(f"  Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                            travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                            debug.append(f"  Travel minutes: {travel_minutes}")
                            
                            if travel_minutes and travel_minutes > 0:
                                travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                segment_key = (from_loc_clean, to_loc_clean, curr_day)
                                debug.append(f"  Adding journey: {from_loc_clean} → {to_loc_clean} ({curr_day}) - {travel_time}")
                                
                                if segment_key not in seen_segments:
                                    seen_segments.add(segment_key)
                                    travel_segments_text.append(
                                        f"{from_loc_clean} → {to_loc_clean} ({curr_day}) - {travel_time}"
                                    )
                            
                            current_location = curr_match_location
                    
                    # Process hotel returns and other day-by-day movements
                    for i, day in enumerate(sorted_days):
                        day_str = day.get("day")
                        
                        # Skip days without a defined date
                        if not day_str or day_str == "Unknown":
                            continue
                        
                        # Process hotel changes between days
                        if i > 0 and day.get("hotel") != sorted_days[i-1].get("hotel"):
                            prev_hotel = sorted_days[i-1].get("hotel")
                            curr_hotel = day.get("hotel")
                            
                            if prev_hotel and curr_hotel and prev_hotel != curr_hotel:
                                from_loc_clean = prev_hotel.replace(" hbf", "")
                                to_loc_clean = curr_hotel.replace(" hbf", "")
                                
                                # Only add the journey if we're not already there
                                if from_loc_clean != to_loc_clean and current_location.replace(" hbf", "") != to_loc_clean:
                                    from_with_hbf = from_loc_clean + " hbf" if not has_special_suffix(from_loc_clean) else from_loc_clean
                                    to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                                    
                                    debug.append(f"  Hotel change: Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                                    travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                                    debug.append(f"  Travel minutes: {travel_minutes}")
                                    
                                    if travel_minutes and travel_minutes > 0:
                                        travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                        segment_key = (from_loc_clean, to_loc_clean, day_str)
                                        debug.append(f"  Adding journey: {from_loc_clean} → {to_loc_clean} ({day_str}) - {travel_time}")
                                        
                                        if segment_key not in seen_segments:
                                            seen_segments.add(segment_key)
                                            travel_segments_text.append(
                                                f"{from_loc_clean} → {to_loc_clean} ({day_str}) - {travel_time}"
                                            )
                                    
                                    current_location = curr_hotel
                        
                        # Process match travel (but only if we haven't handled it with consecutive match logic)
                        if day.get("matches"):
                            match = day["matches"][0]
                            match_location = match["location"]
                            to_loc_clean = match_location.replace(" hbf", "")
                            current_loc_clean = current_location.replace(" hbf", "")
                            
                            # Don't add redundant journey if we already processed it via consecutive match logic
                            if to_loc_clean != current_loc_clean:
                                # FIXED: Use has_special_suffix for current location too
                                from_with_hbf = current_loc_clean + " hbf" if not has_special_suffix(current_loc_clean) else current_loc_clean
                                to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                                
                                debug.append(f"  Match travel: Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                                travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                                debug.append(f"  Travel minutes: {travel_minutes}")
                                
                                if travel_minutes and travel_minutes > 0:
                                    travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                    segment_key = (current_loc_clean, to_loc_clean, day_str)
                                    debug.append(f"  Adding journey: {current_loc_clean} → {to_loc_clean} ({day_str}) - {travel_time}")
                                    
                                    if segment_key not in seen_segments:
                                        seen_segments.add(segment_key)
                                        travel_segments_text.append(
                                            f"{current_loc_clean} → {to_loc_clean} ({day_str}) - {travel_time}"
                                        )
                                
                                current_location = match_location
                            
                            # Check if we need to return to hotel after match
                            if day_str in hotel_by_day:
                                hotel_loc = hotel_by_day[day_str]
                                hotel_loc_clean = hotel_loc.replace(" hbf", "")
                                
                                # Skip return journey on the last day if we're ending at match location
                                is_last_match_day = not any(other_day.get("matches") for other_day in sorted_days[i+1:])
                                ends_at_match_location = variant_detail.end_location == to_loc_clean
                                
                                if is_last_match_day and ends_at_match_location:
                                    debug.append(f"  Skipping return journey on last day: {to_loc_clean} is end location")
                                    continue
                                
                                # Add travel to hotel if match location != hotel location
                                if hotel_loc_clean != to_loc_clean:
                                    # FIXED: Use has_special_suffix here as well
                                    from_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                                    to_with_hbf = hotel_loc_clean + " hbf" if not has_special_suffix(hotel_loc_clean) else hotel_loc_clean
                                    
                                    debug.append(f"  Return to hotel: Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                                    travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                                    debug.append(f"  Travel minutes: {travel_minutes}")
                                    
                                    if travel_minutes and travel_minutes > 0:
                                        travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                        segment_key = (to_loc_clean, hotel_loc_clean, f"{day_str}, After Game")
                                        debug.append(f"  Adding journey: {to_loc_clean} → {hotel_loc_clean} ({day_str}, After Game) - {travel_time}")
                                        
                                        if segment_key not in seen_segments:
                                            seen_segments.add(segment_key)
                                            travel_segments_text.append(
                                                f"{to_loc_clean} → {hotel_loc_clean} ({day_str}, After Game) - {travel_time}"
                                            )
                                    
                                    current_location = hotel_loc
                    
                    output.append("      " + "\n      ".join(travel_segments_text))

                    if var_idx < len(group.variation_details) - 1:
                        output.append("")
            else:
                # Single travel option - use the same enhanced travel segment logic
                variant_detail = group.variation_details[0] if group.variation_details else None
                if variant_detail:
                    output.append(
                        f"   ℹ️  Only one travel option: "
                        f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
                        f"ending in {variant_detail.end_location}"
                    )

                    # Add hotel information for this option
                    hotel_summary = None
                    # Check both places where hotel summary might be stored
                    for day in group.variations[0]["Itinerary"]:
                        if isinstance(day, dict) and not day.get("matches") and not day.get("day") and "hotel_changes" in day:
                            hotel_summary = day
                            break
                    
                    if not hotel_summary:
                        for day in group.base_trip["Itinerary"]:
                            if isinstance(day, dict) and not day.get("matches") and not day.get("day") and "hotel_changes" in day:
                                hotel_summary = day
                                break
                    
                    if hotel_summary:
                        output.append(f"   🏨 Hotel Changes: {hotel_summary.get('hotel_changes', 0)}")
                        output.append(f"   🏨 Unique Hotels: {hotel_summary.get('unique_hotels', 0)}")
                        if "hotel_locations" in hotel_summary and hotel_summary["hotel_locations"]:
                            # Clean up hotel location names
                            clean_locations = [loc.replace(" hbf", "") for loc in hotel_summary["hotel_locations"]]
                            output.append(f"   🏨 Hotel Locations: {', '.join(clean_locations)}")
                    
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

                    # Now add day-by-day hotel information for this travel option
                    output.append(f"   🏨 Hotel Details:")
                    
                    # Sort the itinerary days chronologically
                    sorted_days = []
                    for day in group.variations[0]["Itinerary"]:
                        if isinstance(day, dict) and "day" in day and "hotel" in day:
                            sorted_days.append(day)
                    
                    # Sort by date
                    def get_date_sortkey(day_item):
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
                    
                    sorted_days = sorted(sorted_days, key=get_date_sortkey)
                    
                    # Process each day's hotel information
                    prev_hotel = None
                    processed_days = set()  # Track which days we've already processed
    
                    # Process each day's hotel information
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
                            output.append(f"        {day_str}: Change hotel to {hotel_clean}")
                        else:
                            output.append(f"        {day_str}: Stay in hotel in {hotel_clean}")
                        
                        prev_hotel = hotel
                    
                    # Use the same enhanced travel segment logic for single options
                    travel_segments_text = []
                    seen_segments = set()  # Track unique segments
                    
                    debug.append(f"DEBUG Trip {group_index} Single Option - Processing travel segments")
                    
                    # Create dicts to track location data
                    hotel_by_day = {}
                    match_by_day = {}
                    
                    # Map days to hotels and match locations
                    for day in sorted_days:
                        if "day" in day and "hotel" in day:
                            day_name = day["day"]
                            hotel_by_day[day_name] = day["hotel"]
                            debug.append(f"  Hotel for {day_name}: {day['hotel']}")
                        
                        if "day" in day and "matches" in day and day["matches"]:
                            day_name = day["day"]
                            match_location = day["matches"][0]["location"]
                            match_by_day[day_name] = match_location
                            debug.append(f"  Match for {day_name}: {match_location}")
                    
                    # Sort days chronologically
                    def sort_date_string(day_str):
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
                    
                    sorted_match_days = sorted(match_by_day.keys(), key=sort_date_string)
                    debug.append(f"  Sorted match days: {sorted_match_days}")
                    
                    # Start from actual start location
                    current_location = variant_detail.start_location
                    debug.append(f"  Starting location: {current_location}")
                    
                    # CRITICAL FIX 1: Always show first journey to match location
                    if sorted_match_days:
                        first_day = sorted_match_days[0]
                        first_match_location = match_by_day[first_day]
                        debug.append(f"  First match day: {first_day} at {first_match_location}")
                        
                        # Direct journey from start location to first match
                        if current_location != first_match_location:
                            from_loc_clean = current_location.replace(" hbf", "")
                            to_loc_clean = first_match_location.replace(" hbf", "")
                            
                            # Only append hbf if the location doesn't have a special suffix
                            from_with_hbf = from_loc_clean + " hbf" if not has_special_suffix(from_loc_clean) else from_loc_clean
                            to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                            
                            debug.append(f"  Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                            travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                            debug.append(f"  Travel minutes: {travel_minutes}")
                            
                            if travel_minutes and travel_minutes > 0:
                                travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                segment_key = (from_loc_clean, to_loc_clean, first_day)
                                debug.append(f"  Adding journey: {from_loc_clean} → {to_loc_clean} ({first_day}) - {travel_time}")
                                
                                if segment_key not in seen_segments:
                                    seen_segments.add(segment_key)
                                    travel_segments_text.append(
                                        f"{from_loc_clean} → {to_loc_clean} ({first_day}) - {travel_time}"
                                    )
                            
                            # Update current location to first match location
                            current_location = first_match_location
                    
                    # CRITICAL FIX 2: Handle consecutive match days
                    for i in range(1, len(sorted_match_days)):
                        prev_day = sorted_match_days[i-1]
                        curr_day = sorted_match_days[i]
                        
                        prev_match_location = match_by_day[prev_day]
                        curr_match_location = match_by_day[curr_day]
                        
                        debug.append(f"  Processing consecutive days: {prev_day} → {curr_day}")
                        debug.append(f"  Locations: {prev_match_location} → {curr_match_location}")
                        
                        # If match locations differ, add a journey between them
                        if prev_match_location != curr_match_location:
                            from_loc_clean = prev_match_location.replace(" hbf", "")
                            to_loc_clean = curr_match_location.replace(" hbf", "")
                            
                            from_with_hbf = from_loc_clean + " hbf" if not has_special_suffix(from_loc_clean) else from_loc_clean
                            to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                            
                            debug.append(f"  Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                            travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                            debug.append(f"  Travel minutes: {travel_minutes}")
                            
                            if travel_minutes and travel_minutes > 0:
                                travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                segment_key = (from_loc_clean, to_loc_clean, curr_day)
                                debug.append(f"  Adding journey: {from_loc_clean} → {to_loc_clean} ({curr_day}) - {travel_time}")
                                
                                if segment_key not in seen_segments:
                                    seen_segments.add(segment_key)
                                    travel_segments_text.append(
                                        f"{from_loc_clean} → {to_loc_clean} ({curr_day}) - {travel_time}"
                                    )
                            
                            current_location = curr_match_location
                    
                    # Process hotel returns - similar to multi-option logic
                    for i, day in enumerate(sorted_days):
                        day_str = day.get("day")
                        
                        # Skip days without a defined date
                        if not day_str or day_str == "Unknown":
                            continue
                        
                        # Process match travel (only if we haven't handled it already)
                        if day.get("matches"):
                            match = day["matches"][0]
                            match_location = match["location"]
                            to_loc_clean = match_location.replace(" hbf", "")
                            current_loc_clean = current_location.replace(" hbf", "")
                            
                            # Don't add redundant journey if we already processed it via consecutive match logic
                            if to_loc_clean != current_loc_clean:
                                # FIXED: Use has_special_suffix for current location too
                                from_with_hbf = current_loc_clean + " hbf" if not has_special_suffix(current_loc_clean) else current_loc_clean
                                to_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                                
                                debug.append(f"  Match travel: Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                                travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                                debug.append(f"  Travel minutes: {travel_minutes}")
                                
                                if travel_minutes and travel_minutes > 0:
                                    travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                    segment_key = (current_loc_clean, to_loc_clean, day_str)
                                    debug.append(f"  Adding journey: {current_loc_clean} → {to_loc_clean} ({day_str}) - {travel_time}")
                                    
                                    if segment_key not in seen_segments:
                                        seen_segments.add(segment_key)
                                        travel_segments_text.append(
                                            f"{current_loc_clean} → {to_loc_clean} ({day_str}) - {travel_time}"
                                        )
                                
                                current_location = match_location
                            
                            # Check if we need to return to hotel after match
                            if day_str in hotel_by_day:
                                hotel_loc = hotel_by_day[day_str]
                                hotel_loc_clean = hotel_loc.replace(" hbf", "")
                                
                                # Skip return journey on the last day if we're ending at match location
                                is_last_match_day = not any(other_day.get("matches") for other_day in sorted_days[i+1:])
                                ends_at_match_location = variant_detail.end_location == to_loc_clean
                                
                                if is_last_match_day and ends_at_match_location:
                                    debug.append(f"  Skipping return journey on last day: {to_loc_clean} is end location")
                                    continue
                                
                                # Add travel to hotel if match location != hotel location
                                if hotel_loc_clean != to_loc_clean:
                                    # FIXED: Use has_special_suffix here as well
                                    from_with_hbf = to_loc_clean + " hbf" if not has_special_suffix(to_loc_clean) else to_loc_clean
                                    to_with_hbf = hotel_loc_clean + " hbf" if not has_special_suffix(hotel_loc_clean) else hotel_loc_clean
                                    
                                    debug.append(f"  Return to hotel: Looking up travel time: {from_with_hbf} → {to_with_hbf}")
                                    travel_minutes = get_travel_minutes(train_times, from_with_hbf, to_with_hbf)
                                    debug.append(f"  Travel minutes: {travel_minutes}")
                                    
                                    if travel_minutes and travel_minutes > 0:
                                        travel_time = f"{travel_minutes//60}h {travel_minutes%60}m"
                                        segment_key = (to_loc_clean, hotel_loc_clean, f"{day_str}, After Game")
                                        debug.append(f"  Adding journey: {to_loc_clean} → {hotel_loc_clean} ({day_str}, After Game) - {travel_time}")
                                        
                                        if segment_key not in seen_segments:
                                            seen_segments.add(segment_key)
                                            travel_segments_text.append(
                                                f"{to_loc_clean} → {hotel_loc_clean} ({day_str}, After Game) - {travel_time}"
                                            )
                                    
                                    current_location = hotel_loc
                    
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

    # Add debug info if needed
    #print("\n=== DEBUG INFO ===")
    #print("\n".join(debug))
    #print("=== END DEBUG ===\n")

    print("\n".join(output))
    return "\n".join(output)





@app.post("/plan-trip", summary="Plan a multi-game trip",
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
        
                # Use pre-loaded games and apply filters
        # Load games directly on each request
        regular_games, tbd_games = load_games(GAMES_FILE)
        # More efficient filtering with sets and list comprehensions
        if request.preferred_leagues:
            # Convert to set for O(1) lookup instead of O(n)
            preferred_lower = {league.lower() for league in request.preferred_leagues}
            
            # Use list comprehensions for more efficient filtering
            regular_games_filtered = [g for g in regular_games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            tbd_games_filtered = [g for g in tbd_games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            
            # Check if no games match the preferred leagues
            if not regular_games_filtered and not tbd_games_filtered:
                return JSONResponse(
                    content={
                        "error": f"No games found for the selected leagues: {', '.join(request.preferred_leagues)}"
                    },
                    status_code=404
                )
                
            regular_games = regular_games_filtered
            tbd_games = tbd_games_filtered
        
        # Check if must_teams exist in the dataset
        if request.must_teams:
            must_teams_lower = {team.lower() for team in request.must_teams}
            team_found = False
            
            for game in regular_games:
                if (hasattr(game, 'home_team') and game.home_team.lower() in must_teams_lower) or \
                   (hasattr(game, 'away_team') and game.away_team.lower() in must_teams_lower):
                    team_found = True
                    break
                    
            if not team_found:
                for game in tbd_games:
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
        # Extract TBD games more efficiently
        result_tbd_games = None
        is_error_with_tbd = False
        
        # Get the actual start date used (from the earliest game if no date was specified)
        display_start_date = request.start_date or "Earliest Available"
        if isinstance(trip_result, dict) and "actual_start_date" in trip_result:
            display_start_date = trip_result["actual_start_date"]
        
        if isinstance(trip_result, dict):
            # Direct dictionary lookup is more efficient
            result_tbd_games = trip_result.get("TBD_Games") or trip_result.get("tbd_games")
            is_error_with_tbd = "error" in trip_result and result_tbd_games
            
            if is_error_with_tbd:
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
            
            # Extract trip schedule more efficiently
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

        # Check for rest days more efficiently
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

        # More efficient trip formatting
        formatted_trips = [
            {"Trip Number": i, "Itinerary": trip}
            for i, trip in enumerate(trip_schedule, start=1)
            if isinstance(trip, list)
        ]

        # More efficient trip sorting
        sorted_trips = sorted(
            formatted_trips,
            key=lambda t: (
                -sum(len(day.get("matches", [])) for day in t["Itinerary"]), 
                calculate_total_travel_time(t)
            )
        )
        
        # Process trip groups
        trip_groups = identify_similar_trips(sorted_trips)
        
        # Helper function to format travel time
        def format_travel_time(minutes):
            if minutes is None:
                return "Unknown"
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
        
        
        # Add this before creating structured_groups
        for group in trip_groups:
            # Fix the base trip data when start_location is "Any"
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

        # Then continue with creating structured_groups
        structured_groups = []

        # Pre-initialize location tracking dictionaries
        for group in trip_groups:
            variation_details = []
            
            # Process each variation with fewer temporary variables
            for variant in group["Variations"]:
                total_travel_time = calculate_total_travel_time(variant)
                
                # Determine actual start location - either from request or first match's location
                actual_start_location = request.start_location
                if actual_start_location.lower() == "any":
                    # Find the first day with matches and get the location (where the game is played)
                    for day in variant["Itinerary"]:
                        if day.get("matches"):
                            # Use the match location (home team's city) instead of travel_from
                            actual_start_location = day["matches"][0]["location"]
                            break
                
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
                # Clean start location for display
                clean_start_location = actual_start_location.replace(" hbf", "")

                # Determine the true ending location - where person will actually end up
                true_end_location = None
                # First, get the location of the last night's hotel stay
                last_hotel_location = None
                for day in reversed(variant["Itinerary"]):
                    if "hotel_location" in day:
                        last_hotel_location = day["hotel_location"]
                        break

                # Then check if there's a return travel on the last day with matches
                last_day_with_matches = None
                for day in reversed(variant["Itinerary"]):
                    if day.get("matches"):
                        last_day_with_matches = day
                        break

                # If there's a return journey on the last day with matches, that's where they'll end up
                if last_day_with_matches and "return_travel" in last_day_with_matches:
                    true_end_location = last_day_with_matches["return_travel"]["to"]
                else:
                    # Otherwise, they'll end up at the last hotel or the last match location
                    true_end_location = last_hotel_location or end_location

                # Clean end location for display
                clean_end_location = true_end_location.replace(" hbf", "")
                
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
                    if travel_minutes is not None:
                        travel_time = format_travel_time(travel_minutes)
                    else:
                        travel_time = "Unknown"
                        
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
                    if travel_minutes is not None:
                        travel_time = format_travel_time(travel_minutes)
                    else:
                        travel_time = "Unknown"
                        
                    airport_distances["end"].append({
                        "airport": airport.replace(" hbf", ""),
                        "travel_time": travel_time
                    })
                
                # Sort airport distances by travel time
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
                
                # Use actual start location for travel segments
                travel_segments = []
                
                # Special handling for first segment to show journey to first match location
                first_match_found = False
                
                # Pre-compute lookup tables for travel segments
                location_to_day = {}
                location_to_travel_time = {}
                
                for day in variant["Itinerary"]:
                    if day.get("matches"):
                        for match in day["matches"]:
                            location_to_day[match["location"]] = day["day"]
                            location_to_travel_time[match["location"]] = match.get("travel_time", "Unknown")
                
                # Use actual start location
                current_location = actual_start_location
                
                # Calculate all travel segments in a single pass
                for day in variant["Itinerary"]:
                    if not day.get("matches"):
                        continue
                        
                    for match in day["matches"]:
                        # Special handling for first match when using "Any" as start location
                        if not first_match_found:
                            first_match_found = True
                            
                            # When start_location is "Any", we assume the trip starts at the first game's location
                            # So we don't need to travel there - just set current_location and skip this segment
                            if request.start_location.lower() == "any":
                                current_location = match["location"]
                                continue
                            # For explicit start locations, keep existing logic
                            elif match["location"] == actual_start_location:
                                current_location = match["location"]
                                continue
                        
                        # Regular travel segment handling (unchanged)
                        from_loc = match.get("travel_from", current_location)
                        to_loc = match["location"]
                        travel_time = match.get("travel_time", "Unknown")
                        
                        # Don't include "Any" in travel segments
                        if from_loc.lower() == "any":
                            from_loc = actual_start_location
                        
                        # Extract day format just once
                        day_parts = day["day"].split()
                        day_formatted = f"{day_parts[0]} {day_parts[1]}" if len(day_parts) >= 2 else day["day"]
                        
                        # Add implicit journey if needed
                        if from_loc != current_location:
                            # More efficient context generation
                            prev_day = ""
                            prev_time = travel_time
                            
                            if current_location in location_to_day:
                                day_full = location_to_day[current_location]
                                prev_day = " ".join(day_full.split()[:2]) if " " in day_full else day_full
                                prev_time = location_to_travel_time.get(current_location, travel_time)
                            
                            travel_segments.append(TravelSegment(
                                from_location=current_location,
                                to_location=from_loc,
                                context=f"{prev_day}, After Game" if prev_day else None,
                                travel_time=prev_time
                            ))
                        
                        # Add explicit journey
                        travel_segments.append(TravelSegment(
                            from_location=from_loc,
                            to_location=to_loc,
                            day=day_formatted,
                            travel_time=travel_time
                        ))
                        
                        current_location = to_loc
                
                # Convert sets to sorted lists for consistent output
                cities_list = sorted(list(cities))
                teams_list = sorted(list(teams))
                
                # Add variation details with actual start location
                variation_details.append(TripVariation(
                    total_travel_time=total_travel_time,
                    travel_hours=total_travel_time // 60,
                    travel_minutes=total_travel_time % 60,
                    travel_segments=travel_segments,
                    cities=cities_list,
                    teams=teams_list,
                    num_games=num_games,
                    start_location=clean_start_location,  # Add actual start location
                    end_location=clean_end_location,
                    airport_distances=airport_distances
                ))
            
            # Add complete group
            structured_groups.append(TripGroup(
                base_trip=group["Base"],
                variations=group["Variations"],
                variation_details=variation_details
            ))
        
        # Create final response in one step
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