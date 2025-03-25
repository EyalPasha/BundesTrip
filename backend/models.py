from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class Game(BaseModel):
    league: str
    date: datetime
    time: Optional[str]
    home_team: str
    away_team: str
    hbf_location: str

class TravelRoute(BaseModel):
    from_hbf: str
    to_hbf: str
    travel_time: int

class TravelSegment(BaseModel):
    from_location: str
    to_location: str
    day: Optional[str] = None
    context: Optional[str] = None
    travel_time: str

class TripVariation(BaseModel):
    total_travel_time: int
    travel_hours: int
    travel_minutes: int
    travel_segments: List[TravelSegment]
    cities: List[str] = []        
    teams: List[str] = []         
    num_games: int = 0
    start_location: str = ""  # Add this field for the actual starting city
    end_location: str = ""  # Final city of the trip
    airport_distances: Dict[str, List[Dict[str, str]]] = {}  # Distances to/from airports                  

class TripGroup(BaseModel):
    base_trip: Dict[str, Any]
    variations: List[Dict[str, Any]]
    variation_details: List[TripVariation] = []

class FormattedResponse(BaseModel):
    start_location: str
    start_date: str
    max_travel_time: str
    trip_duration: str
    preferred_leagues: Any
    must_teams: Optional[List[str]] = None  
    no_trips_available: bool = False
    trip_groups: Optional[List[TripGroup]] = None
    tbd_games: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None

class TripPlan(BaseModel):
    start_location: Optional[str]
    max_travel_time: int
    trip_duration: int
    preferred_leagues: Optional[List[str]]
    game_schedule: list

class TripRequest(BaseModel):
    start_location: Optional[str] = "Any"
    max_travel_time: int = 300
    trip_duration: int = 5
    preferred_leagues: Optional[List[str]] = None
    start_date: Optional[str] = None
    must_teams: Optional[List[str]] = None