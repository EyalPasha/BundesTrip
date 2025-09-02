import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fastapi import FastAPI, Query, Path, BackgroundTasks, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from models import TripRequest, FormattedResponse, TripGroup, TravelSegment, TripVariation, SaveTripRequest
from data.synonyms import AIRPORT_CITIES, league_priority
from config import (GAMES_FILE, TRAIN_TIMES_FILE, CORS_ORIGINS, 
                    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY,
                    JWT_SECRET, validate_config)
import functools
import traceback
import asyncio
import logging
from concurrent.futures import TimeoutError
import jwt
from database import db_service, get_user_role, log_trip_request, log_user_activity
from fastapi import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("trip-planner")

# Import from utils and common
from utils import (load_games, load_train_times, calculate_total_travel_time, 
                  identify_similar_trips, get_travel_minutes_utils, 
                  parse_date_string, plan_trip_with_cancellation, enhance_trip_planning_for_any_start)
from common import (is_request_cancelled, register_request, cleanup_request, cleanup_old_requests, active_requests)

# Initialize Supabase client for admin operations
from supabase import create_client
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Store the background task reference
cleanup_task_ref = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    global cleanup_task_ref
    
    # Startup
    try:
        validate_config()
        logger.info("✅ Production configuration validated successfully")
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise
    
    async def cleanup_task():
        while True:
            await asyncio.sleep(60 * 60)  # Run every hour
            cleanup_old_requests()
            
            # Clear date-sensitive cache entries once per day at midnight to prevent stale dates
            # This saves costs while ensuring data freshness
            global _query_cache
            current_time = time()
            # Clear cache once every 24 hours (86400 seconds)
            if current_time % (24 * 60 * 60) < 60:  # Once per day
                _query_cache.clear()
                logger.info("🔄 Daily cache clear: Cleared query cache to prevent stale date entries")
            
    logger.info("🚀 BundesTrip API starting in production mode")
    logger.info(f"📊 Loaded {len(games)} games and {len(tbd_games)} TBD games")
    logger.info(f"🚆 Loaded {len(train_times)} train connections")
    logger.info("🔐 Supabase authentication enabled")
    
    cleanup_task_ref = asyncio.create_task(cleanup_task())
    
    yield  # This is where the app runs
    
    # Shutdown
    if cleanup_task_ref and not cleanup_task_ref.done():
        logger.info("Cancelling periodic cleanup task")
        cleanup_task_ref.cancel()
        try:
            await cleanup_task_ref
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled successfully")

# Initialize FastAPI with metadata
app = FastAPI(
    title="Multi-Game Trip Planner API",
    description="API for planning trips to multiple soccer/football games",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add these imports at the top with your other imports:
import time
import json
from starlette.middleware.base import BaseHTTPMiddleware

# Add this middleware class after your imports but before your endpoints:
class TripRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only log trip planning requests
        if request.url.path == "/plan-trip" and request.method == "POST":
            start_time = time.time()
            
            # Get user info from authorization header
            user_info = None
            try:
                auth_header = request.headers.get("authorization")
                if auth_header:
                    # Use the existing verification function
                    user_info = verify_supabase_token(auth_header)
            except Exception as e:
                logger.warning(f"Failed to get user info for trip request logging: {e}")
                pass
            
            # Read request body for logging
            request_body = None
            try:
                body = await request.body()
                if body:
                    request_body = json.loads(body.decode())
                    
                    # Create new request with same body (since body can only be read once)
                    async def receive():
                        return {"type": "http.request", "body": body}
                    
                    request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to read request body for logging: {e}")
                pass
            
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the request if we have the necessary data
            if request_body and user_info:
                try:
                    # Determine status based on response
                    status = "completed" if response.status_code == 200 else "failed"
                    error_message = None
                    
                    if response.status_code != 200:
                        error_message = f"HTTP {response.status_code}"
                    
                    # Log to database
                    await db_service.log_trip_request(
                        user_id=user_info['user_id'],
                        request_data={
                            'start_location': request_body.get('start_location', 'Unknown'),
                            'start_date': request_body.get('start_date', 'Unknown'),
                            'trip_duration': request_body.get('trip_duration', 0),
                            'max_travel_time': request_body.get('max_travel_time', 0),
                            'preferred_leagues': request_body.get('preferred_leagues', []),
                            'must_teams': request_body.get('must_teams', []),
                            'min_games': request_body.get('min_games', 2),
                            'request_id': request_body.get('request_id'),
                            'endpoint': '/plan-trip',
                            'method': 'POST'
                        },
                        status=status,
                        processing_time_ms=processing_time_ms,
                        error_message=error_message
                    )
                    
                    logger.info(f"🔄 Trip request logged via middleware: {user_info.get('email', 'unknown')} - {status} ({processing_time_ms}ms)")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to log trip request via middleware: {e}")
            else:
                logger.warning(f"⚠️ Skipping trip request logging - missing data: body={request_body is not None}, user={user_info is not None}")
            
            return response
        
        # For all other requests, just pass through
        return await call_next(request)

# Add the middleware to your FastAPI app (add this line AFTER the CORS middleware):
app.add_middleware(TripRequestLoggingMiddleware)

# Load data using config paths
train_times = load_train_times(TRAIN_TIMES_FILE)
games, tbd_games = load_games(GAMES_FILE)

# Pre-compute static data for faster API responses
def precompute_static_data():
    """Pre-compute static data that doesn't change between requests"""
    global _cached_cities, _cached_leagues, _cached_teams, _cached_dates_index
    
    # Pre-compute cities from train_times
    cities = set()
    for key_pair in train_times.keys():
        cities.add(key_pair[0])
        cities.add(key_pair[1])
    cities_list = ["Any"] + sorted([city for city in cities if city != "Any"])
    display_cities = [(city, city.replace(" hbf", "")) for city in cities_list]
    _cached_cities = [{"id": city[0], "name": city[1]} for city in display_cities]
    
    # Pre-compute leagues and teams
    leagues = set()
    teams = set()
    for game in games + tbd_games:
        if hasattr(game, 'league'):
            leagues.add(game.league)
        if hasattr(game, 'home_team'):
            teams.add(game.home_team)
        if hasattr(game, 'away_team'):
            teams.add(game.away_team)
    
    _cached_leagues = sorted(list(leagues))
    _cached_teams = sorted(list(teams))
    
    # Pre-compute date index for faster date filtering
    _cached_dates_index = {}
    # NOTE: We don't filter by "today" here - we'll do that dynamically
    # to avoid stale dates when server runs for multiple days
    
    for game in games + tbd_games:
        if hasattr(game, 'date'):
            game_date = game.date.date()
            date_str = game_date.strftime("%Y-%m-%d")
            if date_str not in _cached_dates_index:
                _cached_dates_index[date_str] = {
                    "date": game_date.strftime("%d %B"),
                    "count": 0,
                    "leagues": set(),
                    "games": [],
                    "game_date": game_date  # Store actual date for filtering
                }
            _cached_dates_index[date_str]["count"] += 1
            if hasattr(game, 'league'):
                _cached_dates_index[date_str]["leagues"].add(game.league)
            _cached_dates_index[date_str]["games"].append(game)
    
    # Convert sets to lists for JSON serialization
    for date_str in _cached_dates_index:
        _cached_dates_index[date_str]["leagues"] = list(_cached_dates_index[date_str]["leagues"])

# Initialize cached data
_cached_cities = []
_cached_leagues = []
_cached_teams = []
_cached_dates_index = {}

# Pre-compute all static data at startup
precompute_static_data()

# Cache for dynamic queries (with TTL)
from time import time
_query_cache = {}
_cache_ttl = 300  # 5 minutes

def get_cached_result(cache_key):
    """Get cached result if still valid"""
    if cache_key in _query_cache:
        cached_data, timestamp = _query_cache[cache_key]
        if time() - timestamp < _cache_ttl:
            return cached_data
        else:
            del _query_cache[cache_key]
    return None

def set_cached_result(cache_key, data):
    """Cache result with timestamp"""
    _query_cache[cache_key] = (data, time())

# ────────────────────────────────
# 🔐 Authentication Functions
# ────────────────────────────────

def get_supabase_jwt_secret():
    """Get JWT secret for token verification"""
    # Use the JWT_SECRET from environment variables
    # This is the proper JWT secret from your Supabase project
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET not configured in environment variables")
    
    return JWT_SECRET


def verify_supabase_token(authorization: str = Header(None)):
    """Verify Supabase JWT token with proper signature validation"""
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required. Please log in."
        )
    
    if not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization format. Use 'Bearer <token>'"
        )
    
    token = authorization.split(' ')[1]
    
    try:
        # Get Supabase JWT secret
        jwt_secret = get_supabase_jwt_secret()
        
        # Verify JWT token with proper signature validation
        payload = jwt.decode(
            token, 
            jwt_secret, 
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Validate required claims
        if not payload.get('sub'):
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        if payload.get('aud') != 'authenticated':
            raise HTTPException(status_code=401, detail="Invalid token: wrong audience")
        
        # Check token expiration
        exp = payload.get('exp')
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token has expired")
        
        # Get user role from database
        user_role = get_user_role(payload.get('sub'))
        
        return {
            'user_id': payload.get('sub'),
            'email': payload.get('email'),
            'role': user_role,
            'aud': payload.get('aud'),
            'iss': payload.get('iss')
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token audience")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid token signature")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token format")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")

def verify_admin_user(authorization: str = Header(None)):
    """Verify admin user - requires both valid token and admin role"""
    user = verify_supabase_token(authorization)
    
    if user['role'] != 'admin':
        logger.warning(f"Admin access denied for user {user.get('email', 'unknown')} with role {user.get('role', 'none')}")
        raise HTTPException(
            status_code=403, 
            detail="Admin access required. You must be an admin to access this endpoint."
        )
    
    logger.info(f"Admin access granted to {user.get('email', 'unknown')}")
    return user


def get_user_role(user_id: str) -> str:
    """Get user role from database"""
    import asyncio
    try:
        # Create a new event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(db_service.get_user_role(user_id))
    except Exception as e:
        logger.warning(f"Could not fetch user role for {user_id}: {e}")
        return 'user'

def optional_auth(authorization: str = Header(None)):
    """Optional authentication for endpoints that work with or without auth"""
    if not authorization:
        return None
    
    try:
        return verify_supabase_token(authorization)
    except HTTPException:
        return None


# ────────────────────────────────
# 🔐 Save Functions
# ────────────────────────────────

@app.post("/api/save-trip", tags=["Trip Management"])
async def save_user_trip(
    request: SaveTripRequest,
    user = Depends(verify_supabase_token)
):
    """Save a trip for the user with auto-generated numbering"""
    try:
        # Validate that we have the essential trip data structure
        if not isinstance(request.trip_data, dict):
            raise HTTPException(status_code=400, detail="Invalid trip data format")
        
        # Validate required fields in trip data
        required_fields = ['request_id', 'start_location', 'trip_duration']
        missing_fields = [field for field in required_fields if field not in request.trip_data]
        
        if missing_fields:
            logger.warning(f"Trip data missing fields: {missing_fields}")
            # Don't fail, just log the warning - some older trip data might not have all fields
        
        # Auto-generate trip name with numbering
        next_number = await db_service.get_next_trip_number(user['user_id'])
        trip_name = f"Trip #{next_number}"
        
        # Enhance trip data with save metadata for better frontend handling
        enhanced_trip_data = {
            **request.trip_data,
            "save_metadata": {
                "saved_at": datetime.now().isoformat(),
                "saved_by": user['email'],
                "version": "1.0"
            }
        }
        
        # Validate original_request structure
        if not isinstance(request.original_request, dict):
            logger.warning("Original request is not a dict, using empty dict")
            request.original_request = {}
        
        # Save to database
        result = await db_service.save_trip(
            user['user_id'], 
            trip_name, 
            enhanced_trip_data,
            request.original_request,
            request.is_favorite
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to save trip to database")
        
        # Log the save action
        await db_service.log_user_activity(
            user['user_id'],
            'trip_saved',
            {
                'trip_name': trip_name, 
                'is_favorite': request.is_favorite,
                'has_trip_groups': 'trip_groups' in request.trip_data,
                'request_id': request.trip_data.get('request_id', 'unknown')
            }
        )
        
        logger.info(f"Trip '{trip_name}' saved successfully for user {user['email']}")
        
        return {
            "success": True, 
            "trip": result,
            "trip_name": trip_name,
            "message": f"Trip saved as '{trip_name}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save trip: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save trip: {str(e)}")

@app.get("/api/saved-trips", tags=["Trip Management"])
async def get_saved_trips(
    limit: int = Query(20, description="Number of trips to return"),
    favorites_only: bool = Query(False, description="Return only favorite trips"),
    user = Depends(verify_supabase_token)
):
    """Get user's saved trips formatted for frontend display"""
    try:
        # Get trips from database
        all_trips = await db_service.get_user_saved_trips(user['user_id'], limit=1000)
        
        # Filter favorites if requested
        if favorites_only:
            all_trips = [trip for trip in all_trips if trip.get('is_favorite', False)]
        
        # Sort by created date (newest first) and apply limit
        sorted_trips = sorted(all_trips, key=lambda x: x['created_at'], reverse=True)[:limit]
        
        # Format trips for frontend display (same structure as search results)
        formatted_trips = []
        for trip in sorted_trips:
            try:
                # Get the core trip data
                trip_data = trip['trip_data']
                
                # Format the trip for display - preserve the EXACT same structure as search results
                formatted_trip = {
                    "id": trip['id'],
                    "trip_name": trip['trip_name'],
                    "created_at": trip['created_at'],
                    "updated_at": trip['updated_at'],
                    "is_favorite": trip['is_favorite'],
                    
                    # PRESERVE EXACT SEARCH RESULT STRUCTURE
                    "request_id": trip_data.get('request_id', ''),
                    "start_location": trip_data.get('start_location', 'Unknown'),
                    "start_date": trip_data.get('start_date', 'Unknown'),
                    "max_travel_time": trip_data.get('max_travel_time', 'Unknown'),
                    "trip_duration": trip_data.get('trip_duration', 'Unknown'),
                    "preferred_leagues": trip_data.get('preferred_leagues', []),
                    "must_teams": trip_data.get('must_teams', []),
                    "min_games": trip_data.get('min_games', 2),
                    "no_trips_available": trip_data.get('no_trips_available', False),
                    "trip_groups": trip_data.get('trip_groups', []),
                    "tbd_games": trip_data.get('tbd_games', []),
                    "message": trip_data.get('message'),
                    "cancelled": trip_data.get('cancelled', False),
                    
                    # Add metadata for management
                    "save_info": {
                        "original_request": trip['original_request'],
                        "saved_at": trip['created_at'],
                        "is_favorite": trip['is_favorite']
                    }
                }
                
                formatted_trips.append(formatted_trip)
                
            except Exception as e:
                logger.error(f"Error formatting trip {trip['id']}: {e}")
                # Add basic info even if formatting fails
                formatted_trips.append({
                    "id": trip['id'],
                    "trip_name": trip['trip_name'],
                    "created_at": trip['created_at'],
                    "is_favorite": trip['is_favorite'],
                    "error": "Failed to load trip details",
                    "no_trips_available": True
                })
        
        return {
            "trips": formatted_trips,
            "total_count": len(all_trips),
            "displayed_count": len(formatted_trips),
            "has_more": len(all_trips) > limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get saved trips: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get saved trips: {str(e)}")

@app.delete("/api/saved-trips/{trip_id}", tags=["Trip Management"])
async def delete_saved_trip(
    trip_id: str,
    user = Depends(verify_supabase_token)
):
    """Delete a saved trip"""
    try:
        success = await db_service.delete_saved_trip(user['user_id'], trip_id)
        
        if success:
            # Log the delete action
            await db_service.log_user_activity(
                user['user_id'],
                'trip_deleted',
                {'trip_id': trip_id}
            )
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Trip not found")
    except Exception as e:
        logger.error(f"Failed to delete trip: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/saved-trips/{trip_id}/favorite", tags=["Trip Management"])
async def toggle_trip_favorite(
    trip_id: str,
    user = Depends(verify_supabase_token)
):
    """Toggle favorite status of a saved trip"""
    try:
        result = await db_service.toggle_trip_favorite(user['user_id'], trip_id)
        
        if result:
            # Log the action
            await db_service.log_user_activity(
                user['user_id'],
                'trip_favorited',
                {'trip_id': trip_id, 'is_favorite': result['is_favorite']}
            )
            return {"success": True, "trip": result}
        else:
            raise HTTPException(status_code=404, detail="Trip not found")
    except Exception as e:
        logger.error(f"Failed to toggle favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trip-history", tags=["Trip Management"])
async def get_trip_history(
    limit: int = Query(20, description="Number of requests to return"),
    user = Depends(verify_supabase_token)
):
    """Get user's trip request history"""
    try:
        history = await db_service.get_user_trip_history(user['user_id'], limit)
        return {"history": history}
    except Exception as e:
        logger.error(f"Failed to get trip history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/trips/unsave", tags=["Trip Management"])
async def unsave_trip(
    request: Request,
    user = Depends(verify_supabase_token)
):
    """Delete a saved trip with proper account-bound security"""
    try:
        # Get request data
        body = await request.json()
        trip_id = body.get('trip_id')
        
        if not trip_id:
            raise HTTPException(status_code=400, detail="trip_id is required")
        
        logger.info(f"🗑️ Unsaving trip {trip_id} for user {user['user_id']}")
        
        # Get trip details before deletion (for logging and response)
        trip_details = await db_service.get_trip_by_id(user['user_id'], trip_id)
        if not trip_details:
            raise HTTPException(status_code=404, detail="Trip not found or access denied")
        
        # Delete the trip (account-bound)
        success = await db_service.delete_saved_trip(user['user_id'], trip_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete trip")
        
        # Renumber remaining trips for this user
        await db_service.renumber_user_trips(user['user_id'])
        
        # Log user activity
        await db_service.log_user_activity(
            user_id=user['user_id'],
            activity_type='trip_deleted',
            activity_data={
                'trip_id': trip_id,
                'trip_name': trip_details.get('trip_name'),
                'deletion_method': 'user_initiated',
                'start_location': trip_details.get('start_location'),
                'trip_duration': trip_details.get('trip_duration')
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        logger.info(f"✅ Successfully deleted trip '{trip_details.get('trip_name')}' for user {user['email']}")
        
        return {
            "success": True,
            "message": f"Trip '{trip_details.get('trip_name')}' has been deleted",
            "trip_name": trip_details.get('trip_name')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error unsaving trip: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/user/activity", tags=["User Activity"])
async def log_user_activity_endpoint(
    request: Request,
    user = Depends(verify_supabase_token)
):
    """Log user activity"""
    try:
        # Get request data
        body = await request.json()
        
        activity_type = body.get('activity_type')
        activity_details = body.get('activity_details', {})
        
        if not activity_type:
            raise HTTPException(status_code=400, detail="activity_type is required")
        
        logger.info(f"📊 Logging user activity: {activity_type} for user {user['email']}")
        
        # Log the activity
        await db_service.log_user_activity(
            user_id=user['user_id'],
            activity_type=activity_type,
            activity_data=activity_details,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        logger.info(f"✅ User activity logged successfully: {activity_type}")
        
        return {
            "success": True,
            "message": "Activity logged successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error logging user activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to log user activity")
# ────────────────────────────────
# 🛠️ Logging Functions
# ────────────────────────────────

def log_user_request(user_info: dict, endpoint: str, params: dict = None, request: Request = None):
    """Log user requests for analytics"""
    try:
        # Get IP and user agent from request
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
        
        # Log to database asynchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(db_service.log_user_activity(
            user_id=user_info.get('user_id') if user_info else None,
            activity_type=f"api_request:{endpoint.replace('/', '_')}",
            activity_data={
                'endpoint': endpoint,
                'params': params or {},
                'user_email': user_info.get('email') if user_info else None
            },
            ip_address=ip_address,
            user_agent=user_agent
        ))
        
        logger.info(f"Request logged: {endpoint} by {user_info.get('email', 'anonymous')}")
    except Exception as e:
        logger.error(f"Failed to log user request: {e}")
# ────────────────────────────────
# 🏠 Basic Endpoints
# ────────────────────────────────

@app.get("/")
def home():
    return {
        "message": "Welcome to the Multi-Game Trip Planner API",
        "version": "1.0.0",
        "authentication": "Supabase JWT required for most endpoints",
        "docs": "/docs"
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
        "tbd_games_loaded": len(tbd_games),
        "authentication": "Supabase",
        "environment": "production"
    }

# ────────────────────────────────
# 🛠️ Cancellation Endpoints
# ────────────────────────────────

@app.delete("/cancel-trip/{request_id}", 
           summary="Cancel an ongoing trip planning request",
           description="Cancels a trip planning request by ID to free up server resources")
def cancel_trip(request_id: str, user = Depends(verify_supabase_token)):
    """Cancel a trip planning request by ID."""
    # Verify user owns this request or is admin
    if request_id in active_requests:
        request_owner = active_requests[request_id].get('user_id')
        if request_owner != user['user_id'] and user['role'] != 'admin':
            raise HTTPException(status_code=403, detail="Can only cancel your own requests")
        
        active_requests[request_id]["status"] = "cancelled"
        logger.info(f"Request {request_id} cancelled by user {user['email']}")
        return {"message": f"Request {request_id} cancelled successfully"}
    
    logger.warning(f"Cancellation attempt for non-existent request ID: {request_id}")
    return JSONResponse(
        content={"error": f"Request {request_id} not found or already completed"},
        status_code=404
    )

@app.get("/request-status/{request_id}",
          summary="Check the status of a trip planning request",
          description="Returns the current status of a trip planning request")
def request_status(request_id: str, user = Depends(verify_supabase_token)):
    """Get the status of a trip planning request."""
    if request_id in active_requests:
        request_owner = active_requests[request_id].get('user_id')
        if request_owner != user['user_id'] and user['role'] != 'admin':
            raise HTTPException(status_code=403, detail="Can only check status of your own requests")
            
        status = active_requests[request_id]["status"]
        return {
            "request_id": request_id,
            "status": status,
            "created_at": active_requests[request_id]["created_at"].isoformat()
        }
    return JSONResponse(
        content={"error": f"Request {request_id} not found"},
        status_code=404
    )
    
@app.get("/register-request", 
         summary="Get a request ID before submitting a search",
         description="Returns an ID to use for trip planning and cancellation")
def register_new_request(user = Depends(verify_supabase_token)):
    """Get a request ID before starting a search."""
    try:
        request_id = register_request(user['user_id'])
        logger.info(f"New request ID pre-registered: {request_id} for user {user['email']}")
        return {"request_id": request_id}
    except Exception as e:
        logger.error(f"Failed to register request for user {user.get('email', 'unknown')}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate request ID")

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
            year = 2025  # Hardcoded year
            
            # Check if year is included in the date string
            if len(parts) >= 3 and parts[2].isdigit() and len(parts[2]) == 4:
                year = int(parts[2])
                
            return f"{year}-{month:02d}-{day:02d}"
    except:
        pass
    
    return day_str

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
            year = 2025  # Default year
            
            # Check if year is included in date string
            if len(parts) >= 3 and parts[2].isdigit() and len(parts[2]) == 4:
                year = int(parts[2])
                
            return f"{year}-{month:02d}-{day:02d}"
    except:
        pass
    
    return day_str

@functools.lru_cache(maxsize=2048)
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
                     key=lambda d: parse_date_string(d))
    
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

@functools.lru_cache(maxsize=2048)
def get_airport_distances(location, is_start=True):
    """Cache airport distances calculation"""
    distances = []
    for airport in AIRPORT_CITIES:
        if airport.lower() == location.lower():
            distances.append({
                "airport": airport.replace(" hbf", ""),
                "travel_time": "0h 0m"
            })
            continue
        
        city_pair = (location, airport) if is_start else (airport, location)
        travel_minutes = train_times.get(city_pair, None)
        travel_time = format_travel_time(travel_minutes)
            
        distances.append({
            "airport": airport.replace(" hbf", ""),
            "travel_time": travel_time
        })
    
    # Sort by travel time
    distances.sort(key=lambda x: get_minutes(x["travel_time"]))
    return distances

def process_trip_variant(variant: Dict, actual_start_location: str) -> TripVariation:
    """Optimized process_trip_variant function"""
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
        "start": get_airport_distances(actual_start_location, is_start=True),
        "end": get_airport_distances(true_end_location, is_start=False)
    }
    
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


# def print_formatted_trip_schedule(response: FormattedResponse) -> str:
#     """Format trip schedule for display using pre-calculated data from TripVariation objects"""
#     output = []

#     output.append(f"📍 Start Location: {response.start_location.replace(' hbf', '')}")
#     output.append(f"📅 Start Date: {response.start_date}")
#     output.append(f"⏳ Max Travel Time: {response.max_travel_time}")
#     output.append(f"🗓️ Trip Duration: {response.trip_duration}")
#     output.append(
#         f"🏆 Preferred Leagues: "
#         f"{', '.join(response.preferred_leagues) if isinstance(response.preferred_leagues, list) else response.preferred_leagues}"
#     )
    
#     # Add must_teams display
#     if hasattr(response, 'must_teams') and response.must_teams:
#         must_teams_display = ', '.join(response.must_teams) if isinstance(response.must_teams, list) else response.must_teams
#         output.append(f"⭐ Must Include Teams: {must_teams_display}")
    
#     output.append("=" * 50 + "\n")

#     if response.no_trips_available:
#         output.append("No trips with matches found for this period.")
#         output.append("")
#     else:
#         # Process trip groups
#         for group_index, group in enumerate(response.trip_groups or [], start=1):
#             output.append("-" * 100)
#             output.append(f"Trip {group_index}:")
#             output.append("-" * 100)

#             # Add common metadata summary if available
#             if group.variation_details and group.variation_details[0]:
#                 variant = group.variation_details[0]
                
#                 # Display actual start location if original was "Any"
#                 if response.start_location.lower() == "any":
#                     output.append(f"📍 Starting City: {variant.start_location}")
                
#                 output.append(f"🏙️  Cities: {', '.join(variant.cities)}")
#                 output.append(f"⚽ Teams: {', '.join(variant.teams)}")
#                 output.append(f"🏟️  Number of Games: {variant.num_games}")

#                 if variant.airport_distances and "start" in variant.airport_distances:
#                     airport_text = ", ".join(
#                         [f"{a['airport']} ({a['travel_time']})"
#                          for a in variant.airport_distances["start"][:3]]
#                     )
                    
#                     # Use variant.start_location if start_location is "Any"
#                     display_location = variant.start_location if response.start_location.lower() == "any" else response.start_location.replace(' hbf', '')
#                     output.append(
#                         f"✈️  Airports near start location "
#                         f"({display_location}): "
#                         f"{airport_text}"
#                     )

#                 output.append("")

#             # Use the pre-calculated day-by-day itinerary from the base variant
#             base_variant = group.variation_details[0] if group.variation_details else None
            
#             if base_variant and base_variant.day_itinerary:
#                 # Print each day in chronological order
#                 for day_info in base_variant.day_itinerary:
#                     day_name = day_info.get("day", "Unknown")
#                     output.append(f"📅 {day_name}")

#                     if day_info.get("matches"):
#                         # Single or multiple matches?
#                         if len(day_info["matches"]) == 1:
#                             output.append("   ⚽ Match:")
#                         else:
#                             output.append("   ⚽ Matches:")
#                         for match in day_info["matches"]:
#                             # Highlight matches with must_teams
#                             match_prefix = "🌟 " if match.get("contains_must_team", False) else ""
#                             output.append(f"      {match_prefix}🏟️  {match['match']}")
#                             output.append(f"      📍 {match['location']}")
#                     else:
#                         output.append(f"   💤 Rest Day")

#                     output.append("")

#             # Travel options - use pre-calculated variation details
#             if len(group.variations) > 1:
#                 output.append("   🔄 Travel Options:")
#                 for var_idx, variant_detail in enumerate(group.variation_details):
#                     # Use pre-calculated total travel time
#                     output.append(
#                         f"      🚆 Option {var_idx+1}: "
#                         f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
#                         f"ending in {variant_detail.end_location}:"
#                     )
                    
#                     # Add hotel information for this specific travel option
#                     output.append(f"      🏨 Hotel Changes: {variant_detail.hotel_changes}")
#                     output.append(f"      🏨 Unique Hotels: {variant_detail.unique_hotels}")
#                     if variant_detail.hotel_locations:
#                         output.append(f"      🏨 Hotel Locations: {', '.join(variant_detail.hotel_locations)}")

#                     # End airports
#                     if variant_detail.airport_distances and "end" in variant_detail.airport_distances:
#                         top_airports = variant_detail.airport_distances["end"][:3]
#                         if top_airports:
#                             airport_text = ", ".join(
#                                 [f"{a['airport']} ({a['travel_time']})"
#                                  for a in top_airports]
#                             )
#                             output.append(
#                                 f"      ✈️  Nearest airports to {variant_detail.end_location}: {airport_text}"
#                             )
                    
#                     # Use pre-calculated hotel details
#                     output.append(f"      🏨 Hotel Details:")
#                     for detail in variant_detail.hotel_details:
#                         output.append(f"        {detail}")
                    
#                     # Use pre-calculated travel segments
#                     travel_segments_text = [
#                         f"{segment.from_location} → {segment.to_location} "
#                         f"({segment.day}{', ' + segment.context if segment.context else ''}) - "
#                         f"{segment.travel_time}"
#                         for segment in variant_detail.travel_segments
#                     ]
                    
#                     output.append("      " + "\n      ".join(travel_segments_text))

#                     if var_idx < len(group.variation_details) - 1:
#                         output.append("")
#             else:
#                 # Single travel option - use the pre-processed data
#                 variant_detail = group.variation_details[0] if group.variation_details else None
#                 if variant_detail:
#                     output.append(
#                         f"   ℹ️  Only one travel option: "
#                         f"{variant_detail.travel_hours}h {variant_detail.travel_minutes}m total travel, "
#                         f"ending in {variant_detail.end_location}"
#                     )

#                     # Add hotel information from the variant detail
#                     output.append(f"   🏨 Hotel Changes: {variant_detail.hotel_changes}")
#                     output.append(f"   🏨 Unique Hotels: {variant_detail.unique_hotels}")
#                     if variant_detail.hotel_locations:
#                         output.append(f"   🏨 Hotel Locations: {', '.join(variant_detail.hotel_locations)}")
                    
#                     # End airports
#                     if variant_detail.airport_distances and "end" in variant_detail.airport_distances:
#                         top_airports = variant_detail.airport_distances["end"][:3]
#                         if top_airports:
#                             airport_text = ", ".join(
#                                 [f"{a['airport']} ({a['travel_time']})"
#                                 for a in top_airports]
#                             )
#                             output.append(
#                                 f"   ✈️  Nearest airports to {variant_detail.end_location}: {airport_text}"
#                             )

#                     # Use pre-calculated hotel details 
#                     output.append(f"   🏨 Hotel Details:")
#                     for detail in variant_detail.hotel_details:
#                         output.append(f"        {detail}")
                    
#                     # Use pre-calculated travel segments
#                     travel_segments_text = [
#                         f"{segment.from_location} → {segment.to_location} "
#                         f"({segment.day}{', ' + segment.context if segment.context else ''}) - "
#                         f"{segment.travel_time}"
#                         for segment in variant_detail.travel_segments
#                     ]
                    
#                     output.append("      " + "\n      ".join(travel_segments_text))

#             output.append("")  # Blank line after each trip group

#     # TBD games
#     if response.tbd_games:
#         output.append("\n📝 Upcoming Unscheduled Games:")
#         output.append("These games don't have confirmed times yet but might be included in your trip once scheduled:")

#         for game in sorted(response.tbd_games, key=lambda g: g["date"]):
#             clean_location = game['location'].replace(' hbf', '')
#             date_display = game['date']
            
#             # Highlight TBD games with must_teams
#             match_prefix = "🌟 " if game.get("has_must_team", False) else ""
#             output.append(
#                 f"   • {match_prefix}{date_display} - {game['match']} @ {clean_location} ({game['league']})"
#             )

#         output.append("\nCheck back later for updated schedules!")
        
#     output_text="\n".join(output)    
#     # Save to file
#     try:
#         # Create 'logs' directory if it doesn't exist
#         log_dir = os.path.join(os.path.dirname(__file__), 'logs')
#         os.makedirs(log_dir, exist_ok=True)
        
#         # Generate filename with timestamp
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename = f"trip_schedule_{timestamp}.txt"
#         filepath = os.path.join(log_dir, filename)
        
#         # Write to file
#         with open(filepath, 'w', encoding='utf-8') as f:
#             f.write(output_text)
            
#         print(f"Trip schedule saved to {filepath}")
#     except Exception as e:
#         print(f"Error saving trip schedule to file: {e}")
    
#     print(output_text)
#     return output_text

# ────────────────────────────────
# 🛠️ Get Trip
# ────────────────────────────────


@app.post("/plan-trip", 
          summary="Plan a multi-game trip",
          description="Creates an optimized itinerary to watch multiple games based on preferences",
          response_model=FormattedResponse)
async def get_trip(request: TripRequest, 
                   background_tasks: BackgroundTasks,
                   user = Depends(verify_supabase_token)):
    """Plan a trip with authentication required."""
    
    # Log the request
    log_user_request(user, "/plan-trip", {
        "start_location": request.start_location,
        "trip_duration": request.trip_duration,
        "max_travel_time": request.max_travel_time,
        "preferred_leagues": request.preferred_leagues,
        "must_teams": request.must_teams
    })
    
    try:
        # Use existing ID if provided, otherwise generate new one
        request_id = request.request_id if hasattr(request, 'request_id') and request.request_id else register_request(user['user_id'])
        
        if not hasattr(request, 'request_id') or not request.request_id:
            logger.info(f"New trip planning request started: {request_id} by {user['email']}")
        else:
            logger.info(f"Trip planning request continued with ID: {request_id} by {user['email']}")
        
        # Store user info with request
        if request_id in active_requests:
            active_requests[request_id]['user_id'] = user['user_id']
            active_requests[request_id]['user_email'] = user['email']
        
        # Input validation
        if request.trip_duration <= 0:
            cleanup_request(request_id)
            logger.warning(f"Request {request_id} rejected: Invalid trip duration")
            return JSONResponse(
                content={"error": "Trip duration must be positive"},
                status_code=400
            )
            
        if request.max_travel_time <= 0:
            cleanup_request(request_id)
            logger.warning(f"Request {request_id} rejected: Invalid max travel time")
            return JSONResponse(
                content={"error": "Maximum travel time must be positive"},
                status_code=400
            )
        
        # Log request parameters
        logger.info(f"Request {request_id} parameters: start={request.start_location}, "
                   f"duration={request.trip_duration}, max_travel={request.max_travel_time}, "
                   f"user={user['email']}. one_city_only={request.one_city_only}")
        
        # Filter games by preferred leagues
        if request.preferred_leagues:
            # Convert to set for O(1) lookup instead of O(n)
            preferred_lower = {league.lower() for league in request.preferred_leagues}
            
            # Use list comprehensions for more efficient filtering
            regular_games_filtered = [g for g in games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            tbd_games_filtered = [g for g in tbd_games if hasattr(g, 'league') and g.league.lower() in preferred_lower]
            
            # Check if no games match the preferred leagues
            if not regular_games_filtered and not tbd_games_filtered:
                cleanup_request(request_id)
                logger.warning(f"Request {request_id} failed: No games found for selected leagues")
                return JSONResponse(
                    content={
                        "error": f"No games found for the selected leagues: {', '.join(request.preferred_leagues)}"
                    },
                    status_code=404
                )
                
            filtered_games = regular_games_filtered
            filtered_tbd_games = tbd_games_filtered
            logger.info(f"Request {request_id} filtered to {len(filtered_games)} games in leagues: {request.preferred_leagues}")
        else:
            filtered_games = games
            filtered_tbd_games = tbd_games
            logger.info(f"Request {request_id} using all {len(filtered_games)} games")
        
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
                cleanup_request(request_id)
                logger.warning(f"Request {request_id} failed: No games found for must_teams")
                return JSONResponse(
                    content={
                        "error": f"No games found for the requested teams: {', '.join(request.must_teams)}"
                    },
                    status_code=404
                )
            
            logger.info(f"Request {request_id} includes must_teams: {request.must_teams}")
        
        # Get min_games from request with default value of 2
        min_games = request.min_games if hasattr(request, 'min_games') else 2
        
        # Plan trip with optimized parameters including min_games
        if request.start_location.lower() == "any":
            logger.info(f"Request {request_id} using 'Any' start location optimization")
            trip_result = await enhance_trip_planning_for_any_start(
                request_id=request_id,
                start_location=request.start_location,
                trip_duration=request.trip_duration,
                max_travel_time=request.max_travel_time,
                games=filtered_games,
                train_times=train_times,
                tbd_games=None,  # Set to None to ignore TBD games in trip planning
                preferred_leagues=request.preferred_leagues,
                start_date=request.start_date,
                must_teams=request.must_teams,
                min_games=min_games,
                one_city_only=request.one_city_only

            )
        else:
            logger.info(f"Request {request_id} using specific start location: {request.start_location}")
            trip_result = await plan_trip_with_cancellation(
                request_id=request_id,
                start_location=request.start_location,
                trip_duration=request.trip_duration,
                max_travel_time=request.max_travel_time,
                games=filtered_games,
                train_times=train_times,
                tbd_games=None,  # Set to None to ignore TBD games in trip planning
                preferred_leagues=request.preferred_leagues,
                start_date=request.start_date,
                must_teams=request.must_teams,
                min_games=min_games,
                one_city_only=request.one_city_only

            )
        
        # Check if the request was cancelled
        if is_request_cancelled(request_id) or (isinstance(trip_result, dict) and trip_result.get("cancelled")):
            logger.info(f"Request {request_id} was cancelled - returning cancelled response")
            return FormattedResponse(
                request_id=request_id,
                start_location=request.start_location,
                start_date=request.start_date or "Not specified",
                max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                trip_duration=f"{request.trip_duration} days",
                preferred_leagues=request.preferred_leagues or "All Leagues",
                must_teams=request.must_teams,
                min_games=min_games,
                no_trips_available=True,
                message="Trip planning cancelled by user",
                cancelled=True
            )
        
        # Get the actual start date used
        display_start_date = request.start_date or "Earliest Available"
        if isinstance(trip_result, dict) and "actual_start_date" in trip_result:
            display_start_date = trip_result["actual_start_date"]
        
        if isinstance(trip_result, dict):
            # Check for error
            if "error" in trip_result:
                # Create structured response for error case
                structured_response = FormattedResponse(
                    request_id=request_id,
                    start_location=request.start_location,
                    start_date=display_start_date,
                    max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                    trip_duration=f"{request.trip_duration} days",
                    preferred_leagues=request.preferred_leagues or "All Leagues",
                    must_teams=request.must_teams,
                    min_games=min_games,
                    no_trips_available=True,
                    message="No scheduled games found during this period.",
                    tbd_games=[]  # Empty for now, will be populated below
                )
                background_tasks.add_task(cleanup_request, request_id)
                return JSONResponse(content=structured_response.model_dump(), status_code=200)
            
            # Extract trip schedule
            trip_schedule = trip_result.get("trips", trip_result)
            if "no_trips_available" in trip_result:
                structured_response = FormattedResponse(
                    request_id=request_id,
                    start_location=request.start_location,
                    start_date=display_start_date,
                    max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                    trip_duration=f"{request.trip_duration} days",
                    preferred_leagues=request.preferred_leagues or "All Leagues",
                    must_teams=request.must_teams,
                    min_games=min_games,
                    no_trips_available=True,
                    message="No scheduled games found during this period.",
                    tbd_games=[]  # Empty for now, will be populated below
                )
                background_tasks.add_task(cleanup_request, request_id)
                return JSONResponse(content=structured_response.model_dump(), status_code=200)
        else:
            trip_schedule = trip_result

        # Early termination for invalid or empty trip schedules
        if not trip_schedule or not isinstance(trip_schedule, list):
            structured_response = FormattedResponse(
                request_id=request_id,
                start_location=request.start_location,
                start_date=display_start_date,
                max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                trip_duration=f"{request.trip_duration} days",
                preferred_leagues=request.preferred_leagues or "All Leagues",
                must_teams=request.must_teams,
                min_games=min_games,
                no_trips_available=True,
                message="No trip found. No available games during this period.",
                tbd_games=[]  # Empty for now, will be populated below
            )
            background_tasks.add_task(cleanup_request, request_id)
            return JSONResponse(content=structured_response.model_dump(), status_code=200)

        # Check for matches
        has_matches = any(
            isinstance(day, dict) and day.get("matches")
            for trip in trip_schedule if isinstance(trip, list)
            for day in trip
        )
        
        if not has_matches:
            structured_response = FormattedResponse(
                request_id=request_id,
                start_location=request.start_location,
                start_date=display_start_date,
                max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
                trip_duration=f"{request.trip_duration} days",
                preferred_leagues=request.preferred_leagues or "All Leagues",
                must_teams=request.must_teams,
                min_games=min_games,
                no_trips_available=True,
                message="No scheduled games found during this period.",
                tbd_games=[]  # Empty for now, will be populated below
            )
            background_tasks.add_task(cleanup_request, request_id)
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
        
        # NEW: Process TBD games in the trip date range
        tbd_games_in_period = []
        
        try:
            # Parse the start date
            if display_start_date == "Earliest Available":
                start_date_obj = datetime.now()
            else:
                # Try with and without year
                try:
                    if " " in display_start_date and len(display_start_date.split()) == 2:
                        # Add current year if missing
                        current_year = datetime.now().year
                        start_date_obj = datetime.strptime(f"{display_start_date} {current_year}", "%d %B %Y")
                    else:
                        start_date_obj = datetime.strptime(display_start_date, "%d %B %Y")
                except:
                    start_date_obj = datetime.now()
            
            # Calculate end date
            end_date_obj = start_date_obj + timedelta(days=request.trip_duration)
            
            # Convert must_teams to lowercase set for efficient lookups
            must_teams_lower = {team.lower() for team in request.must_teams} if request.must_teams else None
            
            # Process TBD games
            for tbd_game in filtered_tbd_games:
                if not all(hasattr(tbd_game, attr) for attr in ('date', 'hbf_location')):
                    continue
                
                game_date = tbd_game.date.date()
                
                # Check if game is within trip period
                if start_date_obj.date() <= game_date < end_date_obj.date():
                    # Check if a must_team is present
                    has_must_team = False
                    if must_teams_lower and hasattr(tbd_game, 'home_team') and hasattr(tbd_game, 'away_team'):
                        home_team_lower = tbd_game.home_team.lower()
                        away_team_lower = tbd_game.away_team.lower()
                        for must_team in must_teams_lower:
                            if must_team in home_team_lower or must_team in away_team_lower:
                                has_must_team = True
                                break
                    
                    tbd_games_in_period.append({
                        "match": f"{tbd_game.home_team} vs {tbd_game.away_team}",
                        "date": tbd_game.date.strftime("%d %B %Y"),
                        "location": tbd_game.hbf_location,
                        "league": tbd_game.league if hasattr(tbd_game, 'league') else "Unknown",
                        "has_must_team": has_must_team
                    })
            
            # Sort TBD games by date
            tbd_games_in_period.sort(key=lambda g: datetime.strptime(g["date"], "%d %B %Y"))
            
            logger.info(f"Request {request_id} - Found {len(tbd_games_in_period)} TBD games in trip period")
        except Exception as e:
            logger.error(f"Request {request_id} - Error processing TBD games: {str(e)}")
            # Don't let TBD game processing failure affect the rest of the response
        
        # Create final response
        structured_response = FormattedResponse(
            request_id=request_id,
            start_location=request.start_location,
            start_date=display_start_date,
            max_travel_time=f"{request.max_travel_time // 60}h {request.max_travel_time % 60}m",
            trip_duration=f"{request.trip_duration} days",
            preferred_leagues=request.preferred_leagues or "All Leagues",
            must_teams=request.must_teams,
            min_games=min_games,
            no_trips_available=False,
            trip_groups=structured_groups,
            tbd_games=tbd_games_in_period
        )

        logger.info(f"Request {request_id} completed successfully - found {len(structured_groups)} trip groups")
        
        # Clean up the request when done
        background_tasks.add_task(cleanup_request, request_id)
        background_tasks.add_task(lambda: logger.info(f"Request {request_id} resources cleaned up"))
        
        return JSONResponse(content=structured_response.model_dump(), status_code=200)
        
    except Exception as e:
        if 'request_id' in locals():
            logger.error(f"Request {request_id} failed with error: {str(e)}")
            background_tasks.add_task(cleanup_request, request_id)
        else:
            logger.error(f"Trip planning request failed before ID assignment: {str(e)}")
        
        traceback.print_exc()
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=500
        )

# ────────────────────────────────
# 🛠️ Public API Endpoints (No Auth Required)
# ────────────────────────────────

@app.get("/available-leagues", 
         summary="Get all available leagues",
         description="Returns a list of all leagues available in the system",
         tags=["Reference Data"])
def get_leagues():
    """Get available leagues - no authentication required."""
    try:
        # Return pre-computed and sorted leagues with cache headers
        sorted_leagues = sorted(_cached_leagues, key=lambda x: league_priority.get(x, 999))
        result = {"leagues": sorted_leagues}
        
        response = JSONResponse(content=result)
        response.headers["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
        response.headers["ETag"] = f'"{hash(str(result))}"'
        return response
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
    
    # For unfiltered requests, return pre-computed teams
    if not league:
        result = {"teams": _cached_teams}
        response = JSONResponse(content=result)
        response.headers["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
        response.headers["ETag"] = f'"{hash(str(result))}"'
        return response
    
    # For filtered requests, check cache first
    cache_key = f"teams_{league}"
    cached_result = get_cached_result(cache_key)
    if cached_result:
        response = JSONResponse(content=cached_result)
        response.headers["Cache-Control"] = "public, max-age=600"  # 10 minutes for filtered
        return response
    
    # Filter teams by league efficiently using pre-computed data
    teams = set()
    for game in games:
        if hasattr(game, 'league') and game.league == league:
            if hasattr(game, 'home_team'):
                teams.add(game.home_team)
            if hasattr(game, 'away_team'):
                teams.add(game.away_team)
    
    result = {"teams": sorted(list(teams))}
    
    # Cache the filtered result
    set_cached_result(cache_key, result)
    
    response = JSONResponse(content=result)
    response.headers["Cache-Control"] = "public, max-age=600"  # 10 minutes for filtered results
    return response


@app.get("/test-fast")
def test_fast():
    """Minimal test endpoint to check performance"""
    return {"message": "Hello World", "timestamp": "2025-09-02"}

@app.get("/available-cities",
         summary="Get all available cities",
         description="Returns a list of all cities (train stations) in the system",
         tags=["Reference Data"])
def get_cities():
    """Get all available cities for the start location selection."""
    # Return pre-computed cities with cache headers
    response = JSONResponse(content={"cities": _cached_cities})
    response.headers["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
    response.headers["ETag"] = f'"{hash(str(_cached_cities))}"'
    return response


@app.get("/available-dates",
         summary="Get all dates with available matches",
         description="Returns a list of all future dates that have scheduled matches, optionally filtered by league or team",
         tags=["Reference Data"])
def get_available_dates(
    league: Optional[str] = Query(None, description="Filter dates by league"),
    team: Optional[str] = Query(None, description="Filter dates by team")
):
    """Get all future dates with available matches for the date picker."""
    
    # Create cache key for filtered queries
    cache_key = f"dates_{league or 'all'}_{team or 'all'}"
    
    # Check cache first for filtered results
    if league or team:
        cached_result = get_cached_result(cache_key)
        if cached_result:
            response = JSONResponse(content=cached_result)
            response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes for filtered
            return response
    
    # For unfiltered requests, use pre-computed data but filter by current date
    if not league and not team:
        today = datetime.now().date()  # Get current date each time
        result = {
            "dates": [
                {
                    "date": date_str,
                    "display": _cached_dates_index[date_str]["date"],
                    "matches": _cached_dates_index[date_str]["count"],
                    "leagues": _cached_dates_index[date_str]["leagues"]
                }
                for date_str in sorted(_cached_dates_index.keys())
                if _cached_dates_index[date_str]["game_date"] >= today  # Filter by current date
            ]
        }
        response = JSONResponse(content=result)
        response.headers["Cache-Control"] = "public, max-age=1800"  # Reduced to 30 minutes for date-sensitive data
        response.headers["ETag"] = f'"{hash(str(result))}"'
        return response
    
    # For filtered requests, use the pre-computed index for efficiency
    filtered_dates = {}
    today = datetime.now().date()  # Get current date for filtering
    
    for date_str, date_data in _cached_dates_index.items():
        # Skip past dates
        if date_data["game_date"] < today:
            continue
            
        matching_games = []
        
        for game in date_data["games"]:
            # Apply league filter
            if league and hasattr(game, 'league') and game.league != league:
                continue
                
            # Apply team filter
            if team:
                team_lower = team.lower()
                if not ((hasattr(game, 'home_team') and game.home_team.lower() == team_lower) or
                       (hasattr(game, 'away_team') and game.away_team.lower() == team_lower)):
                    continue
            
            matching_games.append(game)
        
        if matching_games:
            leagues_for_date = set()
            for game in matching_games:
                if hasattr(game, 'league'):
                    leagues_for_date.add(game.league)
            
            filtered_dates[date_str] = {
                "date": date_data["date"],
                "count": len(matching_games),
                "leagues": list(leagues_for_date)
            }
    
    result = {
        "dates": [
            {
                "date": date_str,
                "display": filtered_dates[date_str]["date"],
                "matches": filtered_dates[date_str]["count"],
                "leagues": filtered_dates[date_str]["leagues"]
            }
            for date_str in sorted(filtered_dates.keys())
        ]
    }
    
    # Cache filtered results
    set_cached_result(cache_key, result)
    
    response = JSONResponse(content=result)
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes for filtered results
    return response


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
         summary="Get a team's complete schedule",
         description="Returns the future schedule for a specific team",
         tags=["Team Data"])
def get_team_schedule(
    team: str = Path(..., description="The team name")
):
    """Get future games schedule for a specific team."""
    team_lower = team.lower()
    today = datetime.now().date()
    
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
    
    # Find all future matches for this team
    upcoming_matches = []
    for game in games:
        if not (hasattr(game, 'date') and hasattr(game, 'home_team') and hasattr(game, 'away_team')):
            continue
            
        game_date = game.date.date()
        
        # Skip dates that have passed
        if game_date < today:
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
    
    # Also add future TBD games
    tbd_matches = []
    for game in tbd_games:
        if not (hasattr(game, 'date') and hasattr(game, 'home_team') and hasattr(game, 'away_team')):
            continue
            
        game_date = game.date.date()
        
        # Skip dates that have passed
        if game_date < today:
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
    include_past: bool = Query(False, description="Include games from past dates")
):
    """Get detailed game information for a specific date and league."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        # Check if the date is in the past and if past dates should be excluded
        if target_date < today and not include_past:
            return {
                "league": league,
                "date": date,
                "display_date": target_date.strftime("%d %B %Y"),
                "games": [],
                "count": 0,
                "is_past_date": True,
                "message": "This date has passed. Set include_past=true to see historical games."
            }
            
        # Filter games by league and date
        day_games = []
        
        # Process regular games
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
        
        # Process TBD games
        for game in tbd_games:
            if not (hasattr(game, 'date') and hasattr(game, 'league')):
                continue
                
            game_date = game.date.date()
            if game_date == target_date and game.league == league:
                day_games.append({
                    "match": f"{game.home_team} vs {game.away_team}",
                    "time": "TBD",
                    "location": game.hbf_location if hasattr(game, 'hbf_location') else "Unknown",
                    "display_location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown",
                    "league": game.league
                })
        
        return {
            "league": league,
            "date": date,
            "display_date": target_date.strftime("%d %B %Y"),
            "games": day_games,
            "count": len(day_games),
            "is_past_date": target_date < today
        }
    except ValueError:
        return JSONResponse(
            content={"error": "Invalid date format. Please use YYYY-MM-DD."},
            status_code=400
        )

@app.get("/league-schedule/{league}",
         summary="Get a league's complete schedule",
         description="Returns the future schedule for a specific league",
         tags=["League Data"])
def get_league_schedule(
    league: str = Path(..., description="The league name")
):
    """Get future games schedule for a specific league."""
    today = datetime.now().date()
    
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
    
    # Process regular games
    for game in games:
        if not (hasattr(game, 'date') and hasattr(game, 'league') and game.league == league_name):
            continue
            
        game_date = game.date.date()
        
        # Skip dates that have passed
        if game_date < today:
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
    
    # Process TBD games
    for game in tbd_games:
        if not (hasattr(game, 'date') and hasattr(game, 'league') and game.league == league_name):
            continue
            
        game_date = game.date.date()
        
        # Skip dates that have passed
        if game_date < today:
            continue
            
        date_str = game_date.strftime("%Y-%m-%d")
        if date_str not in dates_with_games:
            dates_with_games[date_str] = {
                "date": game_date.strftime("%d %B %Y"),
                "games": []
            }
        
        dates_with_games[date_str]["games"].append({
            "match": f"{game.home_team} vs {game.away_team}",
            "time": "TBD",
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
    league: Optional[str] = Query(None, description="Filter by league"),
    include_past: bool = Query(False, description="Include games from past dates")
):
    """Get all games scheduled for a specific date."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        # Check if the date is in the past and if past dates should be excluded
        if target_date < today and not include_past:
            return {
                "date": date,
                "display_date": target_date.strftime("%d %B %Y"),
                "total_games": 0,
                "games_by_league": {},
                "leagues": [],
                "is_past_date": True,
                "message": "This date has passed. Set include_past=true to see historical games."
            }
            
        # Filter games by date
        day_games = []
        
        # Process regular games
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
        
        # Process TBD games
        for game in tbd_games:
            if not hasattr(game, 'date'):
                continue
                
            game_date = game.date.date()
            if game_date == target_date:
                # Apply league filter if specified
                if league and hasattr(game, 'league') and game.league != league:
                    continue
                    
                day_games.append({
                    "match": f"{game.home_team} vs {game.away_team}",
                    "time": "TBD",
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
            "leagues": list(by_league.keys()),
            "is_past_date": target_date < today
        }
    except ValueError:
        return JSONResponse(
            content={"error": "Invalid date format. Please use YYYY-MM-DD."},
            status_code=400
        )  
    
@app.post("/admin/refresh-data",
         summary="Refresh game and travel data",
         description="Reloads game schedules and train times from data files",
         tags=["Administration"])
async def refresh_data(admin_user = Depends(verify_admin_user)):
    """Refresh all data from source files - admin only."""
    
    log_user_request(admin_user, "/admin/refresh-data")
    
    try:
        global train_times, games, tbd_games
        
        # Log admin action start
        await db_service.log_admin_action(
            admin_id=admin_user['user_id'],
            action='data_refresh_started',
            details={
                'admin_email': admin_user['email'],
                'endpoint': '/admin/refresh-data',
                'previous_counts': {
                    'games': len(games),
                    'tbd_games': len(tbd_games),
                    'train_connections': len(train_times)
                }
            }
        )
        
        # Reload data
        new_train_times = load_train_times(TRAIN_TIMES_FILE)
        new_games, new_tbd_games = load_games(GAMES_FILE)
        
        # Update global variables
        old_counts = {
            'games': len(games),
            'tbd_games': len(tbd_games),
            'train_connections': len(train_times)
        }
        
        train_times = new_train_times
        games = new_games
        tbd_games = new_tbd_games
        
        # Clear cache and recompute static data
        global _query_cache
        _query_cache.clear()
        precompute_static_data()
        
        new_counts = {
            'games': len(games),
            'tbd_games': len(tbd_games),
            'train_connections': len(train_times)
        }
        
        # Log successful admin action
        await db_service.log_admin_action(
            admin_id=admin_user['user_id'],
            action='data_refresh_completed',
            details={
                'admin_email': admin_user['email'],
                'old_counts': old_counts,
                'new_counts': new_counts,
                'changes': {
                    'games_change': new_counts['games'] - old_counts['games'],
                    'tbd_games_change': new_counts['tbd_games'] - old_counts['tbd_games'],
                    'train_connections_change': new_counts['train_connections'] - old_counts['train_connections']
                }
            }
        )
        
        logger.info(f"Data refreshed by admin user {admin_user['email']}")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "games_loaded": len(games),
            "tbd_games_loaded": len(tbd_games),
            "train_connections_loaded": len(train_times),
            "refreshed_by": admin_user['email'],
            "changes": {
                "games_change": new_counts['games'] - old_counts['games'],
                "tbd_games_change": new_counts['tbd_games'] - old_counts['tbd_games'],
                "train_connections_change": new_counts['train_connections'] - old_counts['train_connections']
            }
        }
    except Exception as e:
        # Log failed admin action
        await db_service.log_admin_action(
            admin_id=admin_user['user_id'],
            action='data_refresh_failed',
            details={
                'admin_email': admin_user['email'],
                'error': str(e)
            }
        )
        
        logger.error(f"Failed to refresh data: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": f"Failed to refresh data: {str(e)}"},
            status_code=500
        )   

@app.get("/admin/logs", tags=["Administration"])
async def get_admin_logs(
    limit: int = Query(100, description="Number of logs to return"),
    admin_id: Optional[str] = Query(None, description="Filter by specific admin ID"),
    admin_user = Depends(verify_admin_user)
):
    """Get admin action logs - admin only"""
    try:
        logs = await db_service.get_admin_logs(limit, admin_id)
        
        # Log this admin action
        await db_service.log_admin_action(
            admin_id=admin_user['user_id'],
            action='admin_logs_viewed',
            details={
                'admin_email': admin_user['email'],
                'requested_limit': limit,
                'filter_admin_id': admin_id,
                'logs_returned': len(logs)
            }
        )
        
        return {
            "success": True,
            "logs": logs,
            "total": len(logs),
            "viewed_by": admin_user['email']
        }
        
    except Exception as e:
        logger.error(f"Failed to get admin logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def log_trip_request_from_response(request_data: dict, user_info: dict, processing_time_ms: int, status_code: int):
    """Log trip request from response data"""
    try:
        status = "completed" if status_code == 200 else "failed"
        error_message = None
        
        if status_code != 200:
            error_message = f"HTTP {status_code}"
        
        await db_service.log_trip_request(
            user_id=user_info['user_id'],
            request_data={
                'start_location': request_data.get('start_location', 'Unknown'),
                'start_date': request_data.get('start_date', 'Unknown'),
                'trip_duration': request_data.get('trip_duration', 0),
                'max_travel_time': request_data.get('max_travel_time', 0),
                'preferred_leagues': request_data.get('preferred_leagues', []),
                'must_teams': request_data.get('must_teams', []),
                'min_games': request_data.get('min_games', 2),
                'request_id': request_data.get('request_id'),
                'endpoint': '/plan-trip',
                'method': 'POST'
            },
            status=status,
            processing_time_ms=processing_time_ms,
            error_message=error_message
        )
        
        logger.info(f"🔄 Trip request logged: {user_info['email']} - {status} ({processing_time_ms}ms)")
        
    except Exception as e:
        logger.error(f"❌ Failed to log trip request: {e}")
        
        
@app.get("/api/trip-request-history", tags=["Trip Management"])
async def get_trip_request_history(
    limit: int = Query(20, description="Number of requests to return"),
    user = Depends(verify_supabase_token)
):
    """Get user's trip request history with detailed information"""
    try:
        requests = await db_service.get_user_trip_requests(user['user_id'], limit)
        
        # Format the requests for frontend display
        formatted_requests = []
        for req in requests:
            formatted_req = {
                'id': req['id'],
                'start_location': req['start_location'],
                'start_date': req['start_date'],
                'trip_duration': req['trip_duration'],
                'max_travel_time': req['max_travel_time'],
                'preferred_leagues': req['preferred_leagues'],
                'must_teams': req['must_teams'],
                'min_games': req['min_games'],
                'status': req['status'],
                'created_at': req['created_at'],
                'completed_at': req['completed_at'],
                'processing_time_ms': req['processing_time_ms'],
                'error_message': req['error_message'],
                'has_results': req['results'] is not None,
                'results_summary': {
                    'trip_groups_count': len(req['results'].get('trip_groups', [])) if req['results'] else 0,
                    'tbd_games_count': len(req['results'].get('tbd_games', [])) if req['results'] else 0,
                    'no_trips_available': req['results'].get('no_trips_available', True) if req['results'] else True
                } if req['results'] else None
            }
            formatted_requests.append(formatted_req)
        
        return {
            "success": True,
            "requests": formatted_requests,
            "total": len(formatted_requests)
        }
        
    except Exception as e:
        logger.error(f"Failed to get trip request history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
       
@app.get("/tbd-games",
         summary="Get all future TBD games",
         description="Returns all future games without confirmed times, optionally filtered by league and team",
         tags=["Game Data"])
def get_tbd_games(
    league: Optional[str] = Query(None, description="Filter by league"),
    team: Optional[str] = Query(None, description="Filter by team")
):
    """Get all future games without confirmed times."""
    try:
        filtered_games = []
        today = datetime.now().date()
        
        for game in tbd_games:
            if not hasattr(game, 'date'):
                continue
                
            game_date = game.date.date()
            
            # Skip dates that have passed
            if game_date < today:
                continue
                
            # Apply league filter if specified
            if league and hasattr(game, 'league') and game.league.lower() != league.lower():
                continue
                
            # Apply team filter if specified
            if team and not ((hasattr(game, 'home_team') and game.home_team.lower() == team.lower()) or 
                           (hasattr(game, 'away_team') and game.away_team.lower() == team.lower())):
                continue
                
            # Format the game for response
            game_info = {
                "match": f"{game.home_team} vs {game.away_team}",
                "date": game_date.strftime("%d %B %Y"),
                "league": game.league if hasattr(game, 'league') else "Unknown",
                "location": game.hbf_location if hasattr(game, 'hbf_location') else "Unknown",
                "display_location": game.hbf_location.replace(" hbf", "") if hasattr(game, 'hbf_location') else "Unknown"
            }
            
            filtered_games.append(game_info)
            
        # Sort by date
        sorted_games = sorted(filtered_games, key=lambda x: x["date"])
        
        # Group by league
        by_league = {}
        for game in sorted_games:
            league_name = game["league"]
            if league_name not in by_league:
                by_league[league_name] = []
            by_league[league_name].append(game)
        
        return {
            "total": len(sorted_games),
            "games": sorted_games,
            "games_by_league": by_league,
            "leagues": list(by_league.keys())
        }
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to retrieve TBD games: {str(e)}"},
            status_code=500
        )