import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import unittest
from unittest import mock
import random
from datetime import datetime, timedelta
import json
from fastapi.testclient import TestClient
from app import get_trip
from models import TripRequest
from utils import load_games, load_train_times, calculate_total_travel_time
from config import GAMES_FILE, TRAIN_TIMES_FILE
from types import SimpleNamespace

# Use relative import to get the function from parent directory

class TestGetTrip(unittest.TestCase):
    """Test cases for get_trip function in app.py"""
    
    def setUp(self):
        """Set up test data before each test."""
        # Load the actual data files
        self.train_times = load_train_times(TRAIN_TIMES_FILE)
        self.games, self.tbd_games = load_games(GAMES_FILE)
        
        # Sample test cities
        self.test_cities = ["Berlin hbf", "Munich hbf", "Frankfurt hbf", "Hamburg hbf", 
                           "Cologne hbf", "Stuttgart hbf", "Dortmund hbf", "Any"]
        
        # Sample leagues for testing
        self.test_leagues = ["Bundesliga", "2. Bundesliga", "3. Liga", "DFB-Pokal"]
        
        # Get teams from the loaded games data
        self.test_teams = set()
        for game in self.games:
            if hasattr(game, 'home_team'):
                self.test_teams.add(game.home_team)
            if hasattr(game, 'away_team'):
                self.test_teams.add(game.away_team)
        self.test_teams = list(self.test_teams)
        
    def generate_trip_request(self, seed=None):
        """Generate a deterministic trip request based on seed."""
        if seed is not None:
            random.seed(seed)
            
        start_location = random.choice(self.test_cities)
        trip_duration = random.randint(3, 10)
        max_travel_time = random.randint(120, 360)
        
        # Decide whether to include optional parameters
        include_start_date = random.random() > 0.3
        include_leagues = random.random() > 0.4
        include_must_teams = random.random() > 0.6
        
        # Today's date plus a small offset
        today = datetime.now().date()
        start_date = (today + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d") if include_start_date else None
        
        # Randomly select leagues and teams
        preferred_leagues = random.sample(self.test_leagues, 
                                         random.randint(1, len(self.test_leagues))) if include_leagues else None
        
        must_teams = None
        if include_must_teams and self.test_teams:
            # Try to select teams that actually have games
            must_teams = random.sample(self.test_teams, min(2, len(self.test_teams)))
        
        # Create the TripRequest
        return TripRequest(
            start_location=start_location,
            trip_duration=trip_duration,
            max_travel_time=max_travel_time,
            start_date=start_date,
            preferred_leagues=preferred_leagues,
            must_teams=must_teams
        )
    
    def validate_trip_results(self, request, response):
        """Validate that trip results match the request criteria."""
        # Skip validation if no trips were available
        if response.no_trips_available:
            return True
        
        # For each trip group
        for group in response.trip_groups:
            # Check each variation
            for i, variation in enumerate(group.variations):
                # Get the corresponding variation details
                detail = group.variation_details[i] if i < len(group.variation_details) else None
                if not detail:
                    continue
                
                # Validate each travel segment is within max_travel_time
                for segment in detail.travel_segments:
                    # Get travel time between cities from train_times
                    segment_time = self.train_times.get((segment.from_location, segment.to_location))
                    if segment_time is not None and segment_time > request.max_travel_time:
                        return False, f"Travel segment exceeds max: {segment.from_location} to {segment.to_location} takes {segment_time} minutes > {request.max_travel_time}"
                
                # Validate start location
                if request.start_location.lower() != "any" and detail.start_location.lower() not in request.start_location.lower():
                    return False, f"Start location mismatch: {detail.start_location} != {request.start_location}"
                
                # Validate must_teams inclusion
                if request.must_teams:
                    # Check if at least one must_team is included
                    must_team_found = False
                    for team in request.must_teams:
                        if team in detail.teams:
                            must_team_found = True
                            break
                    if not must_team_found:
                        return False, f"Must team not found in trip: {request.must_teams}"
                
                # Verify travel segments match reported total
                travel_time_total = 0
                for segment in detail.travel_segments:
                    # Get travel time between cities from train_times
                    expected_time = self.train_times.get((segment.from_location, segment.to_location))
                    if expected_time is not None:
                        travel_time_total += expected_time
                
                # Allow small difference for rounding etc.
                if abs(travel_time_total - detail.total_travel_time) > 5:
                    return False, f"Travel time calculation mismatch: {travel_time_total} != {detail.total_travel_time}"
                
        return True, "All validations passed"
    
    def test_random_trips(self):
        """Test get_trip with 10 random trip configurations."""
        for i in range(10):
            # Generate a trip request with a fixed seed for reproducibility
            request = self.generate_trip_request(seed=i)
            
            # Make the request
            with mock.patch('app.train_times', self.train_times):
                with mock.patch('app.games', self.games):
                    with mock.patch('app.tbd_games', self.tbd_games):
                        result = get_trip(request)
            
            # Parse the result
            if hasattr(result, 'body'):
                # It's a JSONResponse
                content = json.loads(result.body.decode('utf-8'))
                
                # Check basic structure
                self.assertIn('start_location', content, f"Trip {i+1}: Missing start_location in response")
                self.assertIn('max_travel_time', content, f"Trip {i+1}: Missing max_travel_time in response")
                
                # Convert to object for validation
                result_obj = json.loads(json.dumps(content), object_hook=lambda d: SimpleNamespace(**d))
                
                # Validate trip
                is_valid, message = self.validate_trip_results(request, result_obj)
                self.assertTrue(is_valid, f"Trip {i+1}: {message}")
                
                print(f"Test {i+1}: Request - {request}")
                print(f"Test {i+1}: Response - {'No trips available' if getattr(result_obj, 'no_trips_available', False) else 'Trips found'}")
                print("-" * 80)
    
    def test_specific_scenarios(self):
        """Test specific scenarios that exercise different logic paths."""
        # Test 1: Invalid trip duration
        request = TripRequest(
            start_location="Berlin hbf",
            trip_duration=-1,
            max_travel_time=240
        )
        result = get_trip(request)
        self.assertEqual(result.status_code, 400)
        
        # Test 2: Invalid max travel time
        request = TripRequest(
            start_location="Berlin hbf",
            trip_duration=5,
            max_travel_time=-1
        )
        result = get_trip(request)
        self.assertEqual(result.status_code, 400)
        
        # Test 3: Non-existent league
        request = TripRequest(
            start_location="Berlin hbf",
            trip_duration=5,
            max_travel_time=240,
            preferred_leagues=["Non-existent League"]
        )
        with mock.patch('app.train_times', self.train_times):
            with mock.patch('app.games', self.games):
                with mock.patch('app.tbd_games', self.tbd_games):
                    result = get_trip(request)
                    
        self.assertEqual(result.status_code, 404)
        
        # Test 4: Non-existent team
        request = TripRequest(
            start_location="Berlin hbf",
            trip_duration=5,
            max_travel_time=240,
            must_teams=["Non-existent Team"]
        )
        with mock.patch('app.train_times', self.train_times):
            with mock.patch('app.games', self.games):
                with mock.patch('app.tbd_games', self.tbd_games):
                    result = get_trip(request)
                    
        self.assertEqual(result.status_code, 404)

if __name__ == "__main__":
    unittest.main()