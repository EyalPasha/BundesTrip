from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
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

class HotelStay(BaseModel):
    location: str
    check_in_date: str
    check_out_date: Optional[str] = None
    nights: int = 1

class TripVariation(BaseModel):
    total_travel_time: int
    travel_hours: int
    travel_minutes: int
    travel_segments: List[TravelSegment]
    cities: List[str] = []        
    teams: List[str] = []         
    num_games: int = 0
    start_location: str = "" 
    end_location: str = ""  
    airport_distances: Dict[str, List[Dict[str, str]]] = {} 
    hotel_changes: int = 0  
    unique_hotels: int = 0  
    hotel_locations: List[str] = []  
    hotel_stays: List[Dict[str, Any]] = [] 
    hotel_details: List[str] = []
    day_itinerary: List[Dict[str, Any]] = []

class TripGroup(BaseModel):
    base_trip: Dict[str, Any]
    variations: List[Dict[str, Any]]
    variation_details: List[TripVariation] = []

class FormattedResponse(BaseModel):
    request_id: str
    start_location: str
    start_date: str
    max_travel_time: str
    trip_duration: str
    preferred_leagues: Any
    must_teams: Optional[List[str]] = None
    min_games: int = 2
    no_trips_available: bool = False
    trip_groups: Optional[List[TripGroup]] = None
    tbd_games: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    cancelled: bool = False

class TripPlan(BaseModel):
    start_location: Optional[str]
    max_travel_time: int
    trip_duration: int
    preferred_leagues: Optional[List[str]]
    game_schedule: list

class TripRequest(BaseModel):
    start_location: Optional[str] = "Any"
    max_travel_time: int
    trip_duration: int
    preferred_leagues: Optional[List[str]] = None
    start_date: Optional[str] = None
    must_teams: Optional[List[str]] = None
    min_games: Optional[int] = 2
    request_id: Optional[str] = None
    
class SaveTripRequest(BaseModel):
    trip_data: Dict[Any, Any] = Field(..., description="Complete trip data from search results")
    original_request: Dict[Any, Any] = Field(..., description="Original search parameters")
    is_favorite: bool = Field(False, description="Whether to mark as favorite")