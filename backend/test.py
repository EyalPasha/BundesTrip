import copy
import os
import sys
import pytest
import pandas as pd  # Add this import for loading train times

# Add the current directory to path so imports work correctly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from unittest import mock
from datetime import datetime, timedelta
from typing import Dict, List

# Now import with proper relative paths
from models import TripRequest, FormattedResponse, TripVariation, TripGroup

# Import the function to test using relative import
from app import (
    app, has_special_suffix, get_date_sortkey, sort_date_string, format_travel_time,
    get_minutes, process_travel_segments, process_hotel_information, process_trip_variant,
    print_formatted_trip_schedule
)
# Import utility functions and models
from utils import (
    load_games, load_train_times, plan_trip, calculate_total_travel_time,
    identify_similar_trips, get_travel_minutes_utils, enhance_trip_planning_for_any_start,
    convert_to_minutes, get_travel_minutes_utils, map_team_to_hbf, is_must_team_match,
    process_tbd_games, optimize_trip_variations, filter_best_variations_by_hotel_changes,
    determine_best_start_location, identify_potential_start_cities
)

# Create test client
client = TestClient(app)

# Unit tests for has_special_suffix
def test_has_special_suffix_with_mitte():
    assert has_special_suffix("Berlin mitte") is True
    assert has_special_suffix("BERLIN MITTE") is True
    assert has_special_suffix("berlin Mitte") is True

def test_has_special_suffix_with_bahnhof():
    assert has_special_suffix("Frankfurt bahnhof") is True
    assert has_special_suffix("FRANKFURT BAHNHOF") is True
    assert has_special_suffix("München Bahnhof") is True

def test_has_special_suffix_with_regular_city():
    assert has_special_suffix("Berlin") is False
    assert has_special_suffix("München") is False
    assert has_special_suffix("Frankfurt") is False

def test_has_special_suffix_with_empty_string():
    assert has_special_suffix("") is False

# Unit tests for date sorting functions
def test_get_date_sortkey_valid_date():
    day_item = {"day": "28 March"}
    assert get_date_sortkey(day_item) == "2025-03-28"

def test_get_date_sortkey_unknown_date():
    day_item = {"day": "Unknown"}
    assert get_date_sortkey(day_item) == "9999-99-99"

def test_get_date_sortkey_invalid_date():
    day_item = {"day": "Not a date"}
    assert get_date_sortkey(day_item) == "Not a date"

def test_get_date_sortkey_missing_day():
    day_item = {"other_field": "value"}
    assert get_date_sortkey(day_item) == "9999-99-99"

def test_sort_date_string_valid_date():
    assert sort_date_string("28 March") == "2025-03-28"

def test_sort_date_string_unknown_date():
    assert sort_date_string("Unknown") == "9999-99-99"

def test_sort_date_string_invalid_date():
    assert sort_date_string("Not a date") == "Not a date"

# Unit tests for time formatting functions
def test_format_travel_time_with_hours_and_minutes():
    assert format_travel_time(125) == "2h 5m"

def test_format_travel_time_with_zero_hours():
    assert format_travel_time(45) == "0h 45m"

def test_format_travel_time_with_zero_minutes():
    assert format_travel_time(120) == "2h 0m"

def test_format_travel_time_with_none():
    assert format_travel_time(None) == "Unknown"

def test_get_minutes_with_hours_and_minutes():
    assert get_minutes("2h 30m") == 150

def test_get_minutes_with_zero_hours():
    assert get_minutes("0h 45m") == 45

def test_get_minutes_with_zero_time():
    assert get_minutes("0h 0m") == 0

def test_get_minutes_with_unknown():
    assert get_minutes("Unknown") == float('inf')

# Mock tests for calculate_total_travel_time
@mock.patch("utils.train_times")  # Updated to correct path
def test_calculate_total_travel_time(mock_train_times):
    # Setup mock train times
    mock_train_times.get.return_value = 60  # 60 minutes for each train journey
    
    # Create a test trip with travel between locations
    test_trip = {
        "Itinerary": [
            {"location": "Berlin hbf", "note": "Start"},  # Added hbf
            {"day": "1 April", "location": "München hbf", "matches": [  # Added hbf
                {"match": "Bayern vs Dortmund", "location": "München hbf"}  # Added hbf
            ]},
            {"day": "2 April", "location": "Frankfurt hbf", "matches": [  # Added hbf
                {"match": "Frankfurt vs Leverkusen", "location": "Frankfurt hbf"}  # Added hbf
            ]}
        ]
    }
    
    # Test with trip starting at Berlin hbf
    total_time = calculate_total_travel_time(test_trip, mock_train_times, "Berlin hbf")  # Added hbf
    # Should account for Berlin->München and München->Frankfurt
    assert total_time == 120

# Tests for process_travel_segments
def test_process_travel_segments():
    # Mock train_times for the test
    train_times_data = {
        ("Berlin hbf", "München hbf"): 240,
        ("München hbf", "Berlin hbf"): 240,
        ("München hbf", "Frankfurt hbf"): 180,
        ("Frankfurt hbf", "München hbf"): 180
    }
    
    sorted_days = [
        {"day": "1 April", "hotel": "Berlin hbf"},
        {"day": "2 April", "hotel": "München hbf", "matches": [
            {"location": "München hbf", "match": "Bayern vs Dortmund"}
        ]},
        {"day": "3 April", "hotel": "Frankfurt hbf"}
    ]
    
    variant_detail = TripVariation(
        total_travel_time=420,
        travel_hours=7,
        travel_minutes=0,
        travel_segments=[],
        cities=["Berlin hbf", "München hbf", "Frankfurt hbf"],  # Added hbf
        teams=["Bayern", "Dortmund"],
        num_games=1,
        start_location="Berlin hbf",  # Added hbf
        end_location="Frankfurt hbf",  # Added hbf
        airport_distances={}
    )
    
    match_by_day = {"2 April": "München hbf"}
    hotel_by_day = {"1 April": "Berlin hbf", "2 April": "München hbf", "3 April": "Frankfurt hbf"}
    
    with mock.patch("app.train_times", train_times_data):
        segments = process_travel_segments(
            sorted_days, variant_detail, "Berlin hbf", match_by_day, hotel_by_day
        )
    
        # Check that we have the expected segments
        assert len(segments) >= 2
        assert any("Berlin hbf → München hbf" in s for s in segments)
        assert any("München hbf → Frankfurt hbf" in s for s in segments)

# Tests for process_hotel_information
def test_process_hotel_information():
    sorted_days = [
        {"day": "1 April", "hotel": "Berlin hbf"},
        {"day": "2 April", "hotel": "Berlin hbf"},  # Same hotel
        {"day": "3 April", "hotel": "München hbf"},  # Change hotel
        {"day": "4 April", "hotel": "Frankfurt hbf"}  # Change hotel again
    ]
    
    hotel_info = process_hotel_information(sorted_days)
    
    # Check that we have the expected hotel changes
    assert len(hotel_info) == 4
    assert "1 April: Stay in hotel in Berlin hbf" in hotel_info
    assert "2 April: Stay in hotel in Berlin hbf" in hotel_info
    assert "3 April: Change hotel to München hbf" in hotel_info
    assert "4 April: Change hotel to Frankfurt hbf" in hotel_info

# Tests for process_trip_variant
@mock.patch("app.train_times")
def test_process_trip_variant(mock_train_times):
    # Setup mock train times
    mock_train_times.get.return_value = 120
    
    # Create a test variant
    test_variant = {
        "Itinerary": [
            {"location": "Berlin hbf", "note": "Start"},
            {"day": "1 April", "location": "Berlin hbf", "hotel": "Berlin hbf"},
            {"day": "2 April", "location": "München hbf", "hotel": "München hbf", "matches": [
                {"match": "Bayern vs Dortmund (19:30)", "location": "München hbf"}
            ]},
            {"day": "3 April", "location": "Frankfurt hbf", "hotel": "Frankfurt hbf", "matches": [
                {"match": "Frankfurt vs Leverkusen (15:00)", "location": "Frankfurt hbf"}
            ]}
        ]
    }
    
    # Process the variant
    result = process_trip_variant(test_variant, "Berlin hbf")
    
    # Validate results
    assert result.start_location == "Berlin hbf"
    assert result.end_location == "Frankfurt hbf"
    assert result.num_games == 2
    assert len(result.cities) == 3
    assert "Berlin hbf" in result.cities
    assert "München hbf" in result.cities
    assert "Frankfurt hbf" in result.cities
    assert len(result.teams) == 4
    assert "Bayern" in result.teams
    assert "Dortmund" in result.teams
    assert "Frankfurt" in result.teams
    assert "Leverkusen" in result.teams

# Mock tests for plan_trip
@mock.patch("utils.plan_trip")
def test_plan_trip_function_is_called_correctly(mock_plan_trip):
    # Setup mock return value for plan_trip
    mock_plan_trip.return_value = {"trips": [
        [{"day": "1 April", "matches": [{"match": "Team A vs Team B", "location": "Berlin"}]}]
    ]}
    
    # Call the function
    result = plan_trip(
        start_location="Berlin",
        trip_duration=5,
        max_travel_time=240,
        games=[],  # Empty for this test
        train_times={},  # Empty for this test
        tbd_games=[],
        preferred_leagues=["Bundesliga"],
        start_date="2023-04-01",
        must_teams=["Team A"]
    )
    
    # Verify plan_trip was called with correct parameters
    mock_plan_trip.assert_called_once_with(
        start_location="Berlin",
        trip_duration=5,
        max_travel_time=240,
        games=[],
        train_times={},
        tbd_games=[],
        preferred_leagues=["Bundesliga"],
        start_date="2023-04-01",
        must_teams=["Team A"]
    )
    
    # Verify the result is as expected
    assert "trips" in result
    assert len(result["trips"]) == 1

# Mock tests for enhance_trip_planning_for_any_start
@mock.patch("utils.enhance_trip_planning_for_any_start")
def test_enhance_trip_planning_for_any_start_function(mock_enhance):
    # Setup mock return value
    mock_enhance.return_value = {"trips": [
        [{"day": "1 April", "matches": [{"match": "Team A vs Team B", "location": "Berlin"}]}]
    ]}
    
    # Call the function
    result = enhance_trip_planning_for_any_start(
        start_location="Any",
        trip_duration=5,
        max_travel_time=240,
        games=[],  # Empty for this test
        train_times={},  # Empty for this test
        tbd_games=[],
        preferred_leagues=["Bundesliga"],
        start_date="2023-04-01",
        must_teams=["Team A"]
    )
    
    # Verify the function was called with correct parameters
    mock_enhance.assert_called_once_with(
        start_location="Any",
        trip_duration=5,
        max_travel_time=240,
        games=[],
        train_times={},
        tbd_games=[],
        preferred_leagues=["Bundesliga"],
        start_date="2023-04-01",
        must_teams=["Team A"]
    )
    
    # Verify the result is as expected
    assert "trips" in result
    assert len(result["trips"]) == 1

# API integration tests
def test_get_trip_endpoint_with_specific_location():
    # Test data
    request_data = {
        "start_location": "Berlin hbf",  # Added hbf
        "trip_duration": 5,
        "max_travel_time": 240,
        "preferred_leagues": ["Bundesliga"],
        "start_date": "2023-04-01",
        "must_teams": ["Bayern"]
    }
    
    with mock.patch("app.plan_trip") as mock_plan:
        # Setup mock to return a valid trip
        mock_plan.return_value = {"trips": [
            [{"day": "1 April", "matches": [{"match": "Bayern vs Dortmund", "location": "München hbf"}]}]  # Added hbf
        ]}
        
        # Make the API request
        response = client.post("/plan-trip", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Parse response content
        content = response.json()
        assert content["start_location"] == "Berlin hbf"  # Added hbf
        assert content["no_trips_available"] is False
        assert len(content["trip_groups"]) > 0

def test_get_trip_endpoint_with_any_location():
    # Test data
    request_data = {
        "start_location": "Any",
        "trip_duration": 5,
        "max_travel_time": 240,
        "preferred_leagues": ["Bundesliga"],
        "start_date": "2023-04-01"
    }
    
    with mock.patch("app.enhance_trip_planning_for_any_start") as mock_enhance:
        # Setup mock to return a valid trip
        mock_enhance.return_value = {"trips": [
            [{"day": "1 April", "matches": [{"match": "Bayern vs Dortmund", "location": "München"}]}]
        ]}
        
        # Make the API request
        response = client.post("/plan-trip", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Parse response content
        content = response.json()
        assert content["start_location"] == "Any"
        assert content["no_trips_available"] is False

def test_get_trip_endpoint_no_trips_available():
    # Test data
    request_data = {
        "start_location": "Berlin",
        "trip_duration": 5,
        "max_travel_time": 240,
        "preferred_leagues": ["Bundesliga"],
        "start_date": "2023-04-01"
    }
    
    with mock.patch("app.plan_trip") as mock_plan:
        # Setup mock to return no trips
        mock_plan.return_value = {"no_trips_available": True, "tbd_games": []}
        
        # Make the API request
        response = client.post("/plan-trip", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Parse response content
        content = response.json()
        assert content["no_trips_available"] is True

def test_get_trip_endpoint_with_error():
    # Test data
    request_data = {
        "start_location": "Berlin",
        "trip_duration": 0,  # Invalid value
        "max_travel_time": 240,
        "preferred_leagues": ["Bundesliga"],
        "start_date": "2023-04-01"
    }
    
    # Make the API request
    response = client.post("/plan-trip", json=request_data)
    
    # Verify response
    assert response.status_code == 400
    
    # Parse response content
    content = response.json()
    assert "error" in content

def test_get_trip_endpoint_leagues_not_found():
    # Test data
    request_data = {
        "start_location": "Berlin",
        "trip_duration": 5,
        "max_travel_time": 240,
        "preferred_leagues": ["NonExistentLeague"],
        "start_date": "2023-04-01"
    }
    
    with mock.patch("app.games", return_value=[]):
        with mock.patch("app.tbd_games", return_value=[]):
            # Make the API request
            response = client.post("/plan-trip", json=request_data)
            
            # Since we're mocking empty game lists, it should return 404
            # or a structured response indicating no games found
            assert response.status_code in [404, 200]
            content = response.json()
            if response.status_code == 404:
                assert "error" in content
            else:
                assert content.get("no_trips_available", False) is True

# Comprehensive test for calculate_total_travel_time
def test_calculate_total_travel_time_comprehensive():
    # Create mock train_times
    mock_train_times = {
        ("Berlin hbf", "München hbf"): 240,
        ("München hbf", "Berlin hbf"): 240,
        ("München hbf", "Frankfurt hbf"): 180,
        ("Frankfurt hbf", "München hbf"): 180,
        ("Berlin hbf", "Frankfurt hbf"): 300,
        ("Frankfurt hbf", "Berlin hbf"): 300
    }
    
    # Test case 1: Simple trip with one journey
    trip1 = {
        "Itinerary": [
            {"location": "Berlin hbf", "note": "Start"},
            {"day": "1 April", "matches": [
                {"match": "Hertha vs Union", "location": "Berlin hbf", "travel_from": "Berlin hbf"}
            ]}
        ]
    }
    
    total_time1 = calculate_total_travel_time(trip1, mock_train_times, "Berlin hbf")
    assert total_time1 == 0  # No travel needed
    
    # Test case 2: Trip with multiple journeys
    trip2 = {
        "Itinerary": [
            {"location": "Berlin hbf", "note": "Start"},
            {"day": "1 April", "matches": [
                {"match": "Bayern vs Dortmund", "location": "München hbf", "travel_from": "Berlin hbf"}
            ]},
            {"day": "2 April", "matches": [
                {"match": "Frankfurt vs Leverkusen", "location": "Frankfurt hbf", "travel_from": "München hbf"}
            ]}
        ]
    }
    
    total_time2 = calculate_total_travel_time(trip2, mock_train_times, "Berlin hbf")
    assert total_time2 == 420  # Berlin->München (240) + München->Frankfurt (180)
    
    # Test case 3: Trip with missing travel_from (should use previous location)
    trip3 = {
        "Itinerary": [
            {"location": "Berlin hbf", "note": "Start"},
            {"day": "1 April", "matches": [
                {"match": "Bayern vs Dortmund", "location": "München hbf", "travel_from": "Berlin hbf"}
            ]},
            {"day": "2 April", "matches": [
                {"match": "Frankfurt vs Leverkusen", "location": "Frankfurt hbf"}  # No travel_from
            ]}
        ]
    }
    
    total_time3 = calculate_total_travel_time(trip3, mock_train_times, "Berlin hbf")
    assert total_time3 == 420  # Should still calculate Berlin->München + München->Frankfurt
    
    # Test case 4: Missing travel times in train_times
    trip4 = {
        "Itinerary": [
            {"location": "Berlin hbf", "note": "Start"},
            {"day": "1 April", "matches": [
                {"match": "Team X vs Team Y", "location": "Unknown City", "travel_from": "Berlin hbf"}
            ]}
        ]
    }
    
    total_time4 = calculate_total_travel_time(trip4, mock_train_times, "Berlin hbf")
    assert total_time4 == 0  # Should handle missing train times gracefully

# Test for missing trips in API response
def test_no_missing_trips_in_response():
    # Create test data with multiple trips
    test_trips = [
        [{"day": "1 April", "matches": [{"match": "Team A vs Team B", "location": "Berlin"}]}],
        [{"day": "2 April", "matches": [{"match": "Team C vs Team D", "location": "München"}]}],
        [{"day": "3 April", "matches": [{"match": "Team E vs Team F", "location": "Frankfurt"}]}]
    ]
    
    # Test request data
    request_data = {
        "start_location": "Berlin",
        "trip_duration": 5,
        "max_travel_time": 240,
        "preferred_leagues": ["Bundesliga"]
    }
    
    with mock.patch("app.plan_trip") as mock_plan:
        # Return the test trips
        mock_plan.return_value = {"trips": test_trips}
        
        # Make the API request
        response = client.post("/plan-trip", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Check all trips are included
        content = response.json()
        assert content["no_trips_available"] is False
        # Each test trip should create a trip group
        assert len(content["trip_groups"]) == len(test_trips)

# Test utils.py functions
def test_get_travel_minutes_utils():
    # Mock train_times dictionary
    train_times = {
        ("Berlin hbf", "München hbf"): 240,  # Added hbf
        ("Frankfurt hbf", "Hamburg hbf"): 180,  # Added hbf
        ("Berlin hbf", "Frankfurt hbf"): 300  # Added hbf
    }
    
    # Test direct lookup
    assert get_travel_minutes_utils(train_times, "Berlin hbf", "München hbf") == 240  # Added hbf
    
    # Test reverse lookup
    assert get_travel_minutes_utils(train_times, "München hbf", "Berlin hbf") == 240  # Added hbf
    
    # Test same location (case insensitive)
    assert get_travel_minutes_utils(train_times, "Berlin hbf", "berlin hbf") == 0  # Added hbf
    
    # Test with hbf variant
    assert get_travel_minutes_utils(train_times, "Berlin hbf", "Frankfurt hbf") == 300  # Added hbf
    
    # Test missing route
    assert get_travel_minutes_utils(train_times, "Berlin hbf", "Paris hbf") is None  # Added hbf

def test_convert_to_minutes():
    assert convert_to_minutes("2h 30m") == 150
    assert convert_to_minutes("1h") == 60
    assert convert_to_minutes("45m") == 45
    assert convert_to_minutes("120") == 120
    
    # Test invalid input
    with pytest.raises(ValueError):
        convert_to_minutes("")
    
    with pytest.raises(ValueError):
        convert_to_minutes("invalid")

def test_is_must_team_match():
    must_teams = {"bayern", "dortmund", "union berlin"}
    
    # Test basic matches
    assert is_must_team_match("Bayern München", must_teams) is True
    assert is_must_team_match("Borussia Dortmund", must_teams) is True
    assert is_must_team_match("1. FC Union Berlin", must_teams) is True
    
    # Test non-matches
    assert is_must_team_match("RB Leipzig", must_teams) is False
    assert is_must_team_match("Hertha BSC", must_teams) is False
    
    # Test with reserve teams
    assert is_must_team_match("Bayern München II", must_teams) is False  # Should not match with reserve team
    assert is_must_team_match("Dortmund U23", must_teams) is False

    # Test empty set
    assert is_must_team_match("Bayern München", set()) is False

# Test identify_similar_trips
def test_identify_similar_trips():
    # Create sample trips
    trip1 = {
        "Itinerary": [
            {"day": "1 April", "matches": [{"match": "Bayern vs Dortmund"}]},
            {"day": "2 April", "matches": [{"match": "Leipzig vs Union"}]}
        ]
    }
    
    # Same matches but different travel route
    trip2 = {
        "Itinerary": [
            {"day": "1 April", "matches": [{"match": "Bayern vs Dortmund"}]},
            {"day": "2 April", "matches": [{"match": "Leipzig vs Union"}]}
        ]
    }
    
    # Different matches
    trip3 = {
        "Itinerary": [
            {"day": "1 April", "matches": [{"match": "Hertha vs Schalke"}]},
            {"day": "3 April", "matches": [{"match": "Köln vs Mainz"}]}
        ]
    }
    
    # Group the trips
    trip_groups = identify_similar_trips([trip1, trip2, trip3])
    
    # Should have 2 groups - one for trip1+trip2, one for trip3
    assert len(trip_groups) == 2
    
    # Check that trip1 and trip2 are in the same group
    for group in trip_groups:
        if group["Base"] == trip1:
            assert len(group["Variations"]) == 2
            assert trip1 in group["Variations"]
            assert trip2 in group["Variations"]
        elif group["Base"] == trip3:
            assert len(group["Variations"]) == 1
            assert trip3 in group["Variations"]

# Test optimize_trip_variations
@mock.patch("utils.create_hotel_variation")
def test_optimize_trip_variations(mock_create_variation):
    # Mock train times
    train_times = {
        ("Berlin", "München"): 240,
        ("München", "Berlin"): 240,
        ("Berlin", "Frankfurt"): 300,
        ("Frankfurt", "Berlin"): 300,
        ("München", "Frankfurt"): 180,
        ("Frankfurt", "München"): 180
    }
    
    # Create base trip
    base_trip = [
        {"day": "1 April", "location": "Berlin", "hotel": "Berlin"},
        {"day": "2 April", "location": "München", "matches": [{"match": "Bayern vs Dortmund"}]},
        {"day": "3 April", "location": "Frankfurt", "matches": [{"match": "Frankfurt vs Mainz"}]}
    ]
    
    # Create two variations - one with same hotels, one with different
    variation1 = copy.deepcopy(base_trip)
    variation2 = copy.deepcopy(base_trip)
    
    # Mocking variation creation
    mock_create_variation.side_effect = [variation1, variation2]
    
    # Call the function
    result = optimize_trip_variations(base_trip, train_times, 240, "Berlin")
    
    # Should include the original trip plus variations
    assert len(result) >= 1
    assert result[0] == base_trip  # First result should be original trip

# Test determine_best_start_location
def test_determine_best_start_location():
    from collections import namedtuple
    Game = namedtuple('Game', ['hbf_location', 'date'])
    
    # Create test data
    today = datetime.now()
    games = [
        Game(hbf_location="Berlin", date=today),
        Game(hbf_location="München", date=today),
        Game(hbf_location="Frankfurt", date=today),
        Game(hbf_location="München", date=today + timedelta(days=1))
    ]
    
    # Mock train times where München has most connections
    train_times = {
        ("Berlin", "München"): 240,
        ("München", "Berlin"): 240,
        ("Berlin", "Frankfurt"): 300,
        ("Frankfurt", "Berlin"): 300,
        ("München", "Frankfurt"): 180,
        ("Frankfurt", "München"): 180,
        ("München", "Hamburg"): 240,
        ("Hamburg", "München"): 240
    }
    
    # Test with 'Any' start location
    result = determine_best_start_location("Any", games, today, train_times, 240)
    # Should return the location with most reachable games
    assert result == "München"
    
    # Test with specific start location
    result = determine_best_start_location("Berlin", games, today, train_times, 240)
    assert result == "Berlin"

# Test identify_potential_start_cities
def test_identify_potential_start_cities():
    from collections import namedtuple
    Game = namedtuple('Game', ['hbf_location', 'date'])
    
    # Create test data
    today = datetime.now()
    games = [
        Game(hbf_location="Berlin", date=today),
        Game(hbf_location="München", date=today + timedelta(days=1)),
        Game(hbf_location="Frankfurt", date=today + timedelta(days=2))
    ]
    
    # Mock train times
    train_times = {
        ("Berlin", "München"): 240,
        ("München", "Berlin"): 240,
        ("Berlin", "Frankfurt"): 300,
        ("Frankfurt", "Berlin"): 300,
        ("München", "Frankfurt"): 180,
        ("Frankfurt", "München"): 180,
        ("Hamburg", "Berlin"): 120,
        ("Berlin", "Hamburg"): 120
    }
    
    # Test the function
    start_cities = identify_potential_start_cities(
        games, train_times, 3, 240, start_date=today
    )
    
    # Should include game locations and major cities
    assert "Berlin" in start_cities
    assert "München" in start_cities
    assert "Frankfurt" in start_cities
    
    # Should include well-connected cities
    assert len(start_cities) <= 15  # Should limit the number of cities

# Test process_tbd_games
def test_process_tbd_games():
    from collections import namedtuple
    Game = namedtuple('Game', ['league', 'date', 'home_team', 'away_team', 'hbf_location'])
    
    # Create test data
    today = datetime.now()
    tbd_games = [
        Game(league="Bundesliga", date=today, home_team="Bayern", away_team="Dortmund", hbf_location="München"),
        Game(league="2. Bundesliga", date=today + timedelta(days=1), home_team="Hamburg", away_team="Köln", hbf_location="Hamburg"),
        Game(league="Bundesliga", date=today + timedelta(days=5), home_team="Frankfurt", away_team="Leipzig", hbf_location="Frankfurt")
    ]
    
    # Mock train times
    train_times = {
        ("Berlin", "München"): 240,
        ("Berlin", "Hamburg"): 120,
        ("Berlin", "Frankfurt"): 300
    }
    
    # Call the function
    result = process_tbd_games(
        tbd_games, today, 3, ["Bundesliga"], {"Berlin"}, {"bayern"}, train_times, 240
    )
    
    # Should only include games within trip period and preferred leagues
    assert len(result) == 1
    assert result[0]["match"] == "Bayern vs Dortmund"
    assert result[0]["has_must_team"] is True

# Test health endpoint
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

# Test available dates endpoint
def test_available_dates_endpoint():
    with mock.patch("app.games") as mock_games:
        from collections import namedtuple
        Game = namedtuple('Game', ['date', 'league', 'home_team', 'away_team'])
        
        # Create mock games
        mock_games.__iter__.return_value = [
            Game(date=datetime.now(), league="Bundesliga", home_team="Bayern", away_team="Dortmund"),
            Game(date=datetime.now() + timedelta(days=1), league="2. Bundesliga", home_team="Hamburg", away_team="Köln")
        ]
        
        response = client.get("/available-dates")
        assert response.status_code == 200
        assert "dates" in response.json()
        assert len(response.json()["dates"]) > 0

# Test city connections endpoint
def test_city_connections_endpoint():
    with mock.patch("app.train_times") as mock_train_times:
        # Mock train times
        mock_train_times.keys.return_value = [
            ("Berlin", "München"),
            ("München", "Berlin"),
            ("Berlin", "Frankfurt"),
            ("Frankfurt", "Berlin")
        ]
        mock_train_times.get.return_value = 240
        
        response = client.get("/city-connections/Berlin?max_time=300")
        assert response.status_code == 200
        assert "connections" in response.json()
        
        # Test invalid city
        response = client.get("/city-connections/InvalidCity")
        assert response.status_code == 404

# Test real train_times file loading
def test_load_train_times_file():
    # Test loading the actual train_times file
    train_times_file = os.path.join(os.path.dirname(__file__), "data", "fastest_train_times.csv")
    if os.path.exists(train_times_file):
        df = pd.read_csv(train_times_file)
        assert len(df) > 0
        assert "From" in df.columns
        assert "To" in df.columns
        assert "Fastest Train Time" in df.columns

if __name__ == "__main__":
    pytest.main(["-xvs", "test.py"])