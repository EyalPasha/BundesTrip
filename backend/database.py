from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Initialize Supabase admin client (service role for backend operations)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

class DatabaseService:
    def __init__(self):
        self.client = supabase_admin

    # ──────────────────────────────────
    # 👤 User Management
    # ──────────────────────────────────

    async def get_user_role(self, user_id: str) -> str:
        """Get user role from database"""
        try:
            result = self.client.table('user_roles').select('role').eq('user_id', user_id).single().execute()
            return result.data.get('role', 'user') if result.data else 'user'
        except Exception as e:
            logger.warning(f"Could not fetch user role for {user_id}: {e}")
            return 'user'  # Default role

    async def create_user_role(self, user_id: str, role: str = 'user') -> Optional[Dict]:
        """Create user role in database"""
        try:
            result = self.client.table('user_roles').insert({
                'user_id': user_id,
                'role': role
            }).execute()
            logger.info(f"Created role '{role}' for user {user_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create user role: {e}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> Optional[Dict]:
        """Update user profile"""
        try:
            # Add updated_at timestamp
            profile_data['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table('user_profiles').update(profile_data).eq('id', user_id).execute()
            logger.info(f"Updated profile for user {user_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            return None

    # ──────────────────────────────────
    # 💾 Saved Trips
    # ──────────────────────────────────
    
    async def save_trip(self, user_id: str, trip_name: str, trip_data: Dict, original_request: Dict, is_favorite: bool = False) -> Optional[Dict]:
        """Save a trip for user with proper numbering"""
        try:
            # Validate that we have valid JSON-serializable data
            if not isinstance(trip_data, dict):
                raise ValueError("trip_data must be a dictionary")
            
            if not isinstance(original_request, dict):
                original_request = {}
            
            # Extract trip details for duplicate checking and storage
            start_location = trip_data.get('start_location') or original_request.get('start_location', 'Unknown')
            start_date = trip_data.get('start_date') or original_request.get('start_date')
            trip_duration = trip_data.get('trip_duration') or original_request.get('trip_duration', 3)
            
            # Normalize trip duration to integer
            if isinstance(trip_duration, str):
                import re
                match = re.search(r'(\d+)', trip_duration)
                trip_duration = int(match.group(1)) if match else 3
            
            # If no custom trip name provided, generate one with user-specific numbering
            if not trip_name or trip_name.strip() == '':
                next_number = await self.get_next_trip_number(user_id)
                trip_name = f"Trip #{next_number}"
            
            trip_record = {
                'user_id': user_id,
                'trip_name': trip_name,
                'trip_data': trip_data,
                'original_request': original_request,
                'is_favorite': is_favorite,
                'start_location': start_location,
                'start_date': start_date,
                'trip_duration': trip_duration
            }
            
            result = self.client.table('saved_trips').insert(trip_record).execute()
            logger.info(f"Saved trip '{trip_name}' for user {user_id}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to save trip: {e}")
            return None

    async def get_user_saved_trips(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's saved trips (account-bound)"""
        try:
            result = self.client.table('saved_trips').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get saved trips for user {user_id}: {e}")
            return []
        
    async def get_trip_by_id(self, user_id: str, trip_id: str) -> Optional[Dict]:
        """Get specific trip by ID (account-bound)"""
        try:
            result = self.client.table('saved_trips').select('*').eq('user_id', user_id).eq('id', trip_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get trip {trip_id} for user {user_id}: {e}")
            return None

    async def delete_saved_trip(self, user_id: str, trip_id: str) -> bool:
        """Delete a saved trip (account-bound)"""
        try:
            # Ensure the trip belongs to this user before deletion
            trip = await self.get_trip_by_id(user_id, trip_id)
            if not trip:
                logger.warning(f"Trip {trip_id} not found for user {user_id} or access denied")
                return False
            
            result = self.client.table('saved_trips').delete().eq('user_id', user_id).eq('id', trip_id).execute()
            logger.info(f"Deleted trip {trip_id} ({trip.get('trip_name')}) for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete trip {trip_id} for user {user_id}: {e}")
            return False

    async def toggle_trip_favorite(self, user_id: str, trip_id: str) -> Optional[Dict]:
        """Toggle favorite status of a saved trip (account-bound)"""
        try:
            # Get current status (ensure user owns this trip)
            current = self.client.table('saved_trips').select('is_favorite').eq('user_id', user_id).eq('id', trip_id).single().execute()
            
            if not current.data:
                logger.warning(f"Trip {trip_id} not found for user {user_id}")
                return None
                
            new_status = not current.data['is_favorite']
            
            result = self.client.table('saved_trips').update({
                'is_favorite': new_status,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('id', trip_id).execute()
            
            logger.info(f"Toggled favorite status for trip {trip_id} to {new_status} for user {user_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to toggle favorite for user {user_id}: {e}")
            return None
        
    async def get_next_trip_number(self, user_id: str) -> int:
        """Get the next trip number for a specific user (account-bound)"""
        try:
            # Get all trips for THIS USER ONLY, ordered by creation date
            result = self.client.table('saved_trips').select('trip_name').eq('user_id', user_id).order('created_at').execute()
            
            if not result.data:
                return 1
            
            # Find highest number used in format "Trip #X" for this user
            max_number = 0
            for trip in result.data:
                trip_name = trip['trip_name']
                # Look for pattern "Trip #X"
                if trip_name.startswith('Trip #'):
                    try:
                        number_str = trip_name.replace('Trip #', '').strip()
                        number = int(number_str)
                        max_number = max(max_number, number)
                    except ValueError:
                        continue
            
            return max_number + 1
            
        except Exception as e:
            logger.error(f"Error getting next trip number for user {user_id}: {e}")
            # If there's an error, just count the user's trips + 1
            try:
                result = self.client.table('saved_trips').select('id', count='exact').eq('user_id', user_id).execute()
                return (result.count or 0) + 1
            except:
                return 1
            
    async def renumber_user_trips(self, user_id: str) -> bool:
        """Renumber user trips after deletion to maintain sequential numbering"""
        try:
            # Get all trips for this user that have auto-generated names (Trip #X)
            result = self.client.table('saved_trips').select('id', 'trip_name').eq('user_id', user_id).order('created_at').execute()
            
            if not result.data:
                return True
            
            updates = []
            trip_number = 1
            
            for trip in result.data:
                trip_name = trip['trip_name']
                # Only renumber auto-generated trip names
                if trip_name.startswith('Trip #'):
                    new_name = f"Trip #{trip_number}"
                    if new_name != trip_name:
                        updates.append({
                            'id': trip['id'],
                            'trip_name': new_name,
                            'updated_at': datetime.utcnow().isoformat()
                        })
                    trip_number += 1
            
            # Perform batch update if needed
            if updates:
                for update in updates:
                    self.client.table('saved_trips').update({
                        'trip_name': update['trip_name'],
                        'updated_at': update['updated_at']
                    }).eq('id', update['id']).execute()
                
                logger.info(f"Renumbered {len(updates)} trips for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to renumber trips for user {user_id}: {e}")
            return False
        
    async def check_trip_duplicate(self, user_id: str, trip_data: Dict) -> Optional[Dict]:
        """Check if user already has this trip saved (account-bound)"""
        try:
            # Get user's saved trips
            user_trips = await self.get_user_saved_trips(user_id, 100)
            
            # Extract comparison data from new trip
            current_start_location = self.normalize_location(trip_data.get('start_location', ''))
            current_start_date = self.normalize_date(trip_data.get('start_date', ''))
            current_duration = self.normalize_duration(trip_data.get('trip_duration', 3))
            current_games = self.extract_games_from_trip(trip_data)
            
            # Compare with each saved trip
            for saved_trip in user_trips:
                saved_start_location = self.normalize_location(saved_trip.get('start_location', ''))
                saved_start_date = self.normalize_date(saved_trip.get('start_date', ''))
                saved_duration = self.normalize_duration(saved_trip.get('trip_duration', 3))
                saved_games = self.extract_games_from_trip(saved_trip.get('trip_data', {}))
                
                # Check if all key parameters match
                if (current_start_location == saved_start_location and 
                    current_start_date == saved_start_date and 
                    current_duration == saved_duration and 
                    self.do_games_match(current_games, saved_games)):
                    
                    return saved_trip
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking duplicates for user {user_id}: {e}")
            return None
        
    # Helper methods for duplicate checking
    def normalize_location(self, location: str) -> str:
        """Normalize location for comparison"""
        if not location:
            return ''
        return location.lower().replace('hbf', '').replace('hauptbahnhof', '').strip()

    def normalize_date(self, date_str: str) -> str:
        """Normalize date for comparison"""
        try:
            if isinstance(date_str, str):
                from datetime import datetime
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
        except:
            pass
        return str(date_str).strip()

    def normalize_duration(self, duration) -> int:
        """Normalize duration for comparison"""
        if isinstance(duration, int):
            return duration
        if isinstance(duration, str):
            import re
            match = re.search(r'(\d+)', duration)
            return int(match.group(1)) if match else 3
        return 3

    def extract_games_from_trip(self, trip_data: Dict) -> List[str]:
        """Extract game identifiers from trip data for comparison"""
        games = []
        try:
            if 'trip_groups' in trip_data:
                for group in trip_data['trip_groups']:
                    if 'base_trip' in group and 'Itinerary' in group['base_trip']:
                        for day in group['base_trip']['Itinerary']:
                            if 'matches' in day:
                                for match in day['matches']:
                                    if isinstance(match, dict) and 'match' in match:
                                        games.append(match['match'].lower().strip())
                                    elif isinstance(match, str):
                                        games.append(match.lower().strip())
        except Exception as e:
            logger.warning(f"Error extracting games: {e}")
        return sorted(games)

    def do_games_match(self, games1: List[str], games2: List[str]) -> bool:
        """Check if two game lists match"""
        return set(games1) == set(games2)
    # ──────────────────────────────────
    # 📊 Trip Requests Logging
    # ──────────────────────────────────

    async def log_trip_request(self, user_id: str, request_data: Dict, results: Dict = None, status: str = 'pending', processing_time_ms: int = None, error_message: str = None) -> Optional[str]:
        """Log a trip request to the database"""
        try:
            # Extract key fields from request_data
            start_location = request_data.get('start_location', 'Unknown')
            start_date = request_data.get('start_date')
            trip_duration = request_data.get('trip_duration', 0)
            max_travel_time = request_data.get('max_travel_time', 0)
            preferred_leagues = request_data.get('preferred_leagues', [])
            must_teams = request_data.get('must_teams', [])
            min_games = request_data.get('min_games', 2)
            
            # Convert start_date to proper format if needed
            if start_date and start_date != "Earliest Available":
                try:
                    # Try to parse various date formats
                    if isinstance(start_date, str):
                        from datetime import datetime
                        if " " in start_date and len(start_date.split()) >= 2:
                            # Format like "28 March" or "28 March 2025"
                            parts = start_date.split()
                            if len(parts) == 2:
                                # Add current year
                                current_year = datetime.now().year
                                start_date = f"{parts[0]} {parts[1]} {current_year}"
                        
                        start_date_obj = datetime.strptime(start_date, "%d %B %Y")
                        start_date = start_date_obj.strftime("%Y-%m-%d")
                except:
                    # If parsing fails, use current date
                    start_date = datetime.now().strftime("%Y-%m-%d")
            else:
                # Default to current date for "Earliest Available"
                start_date = datetime.now().strftime("%Y-%m-%d")
            
            # Prepare the record
            trip_request_record = {
                'user_id': user_id,
                'start_location': start_location,
                'start_date': start_date,
                'trip_duration': trip_duration,
                'max_travel_time': max_travel_time,
                'preferred_leagues': preferred_leagues,
                'must_teams': must_teams,
                'min_games': min_games,
                'request_data': request_data,
                'results': results,
                'status': status,
                'processing_time_ms': processing_time_ms,
                'error_message': error_message
            }
            
            # Add completed_at if status is completed, failed, or cancelled
            if status in ['completed', 'failed', 'cancelled']:
                trip_request_record['completed_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table('trip_requests').insert(trip_request_record).execute()
            
            if result.data:
                request_id = result.data[0]['id']
                logger.info(f"✅ Trip request logged: {request_id} for user {user_id}")
                return request_id
            else:
                logger.error(f"❌ Failed to log trip request for user {user_id}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error logging trip request for user {user_id}: {e}")
            return None

    async def update_trip_request(self, request_id: str, status: str = None, results: Dict = None, processing_time_ms: int = None, error_message: str = None) -> bool:
        """Update an existing trip request"""
        try:
            update_data = {}
            
            if status:
                update_data['status'] = status
            if results:
                update_data['results'] = results
            if processing_time_ms is not None:
                update_data['processing_time_ms'] = processing_time_ms
            if error_message:
                update_data['error_message'] = error_message
            
            # Add completed_at if status is final
            if status and status in ['completed', 'failed', 'cancelled']:
                update_data['completed_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table('trip_requests').update(update_data).eq('id', request_id).execute()
            
            if result.data:
                logger.info(f"✅ Trip request updated: {request_id}")
                return True
            else:
                logger.warning(f"⚠️ No trip request found to update: {request_id}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error updating trip request {request_id}: {e}")
            return False

    async def get_user_trip_requests(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's trip request history"""
        try:
            result = self.client.table('trip_requests').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get trip requests for user {user_id}: {e}")
            return []

    # ──────────────────────────────────
    # 📈 User Activity Tracking
    # ──────────────────────────────────

    async def log_user_activity(self, user_id: Optional[str], activity_type: str, activity_data: Optional[Dict] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Log user activity for analytics"""
        try:
            activity_record = {
                'user_id': user_id,
                'activity_type': activity_type,
                'activity_data': activity_data or {},
                'ip_address': ip_address,
                'user_agent': user_agent
            }
            
            self.client.table('user_activity').insert(activity_record).execute()
        except Exception as e:
            logger.error(f"Failed to log user activity: {e}")
            # Don't raise exception - activity logging shouldn't break main functionality

    # ──────────────────────────────────
    # 🏛️ Admin Functions
    # ──────────────────────────────────

    async def get_user_stats(self) -> Dict:
        """Get user statistics for admin dashboard"""
        try:
            # Get total users
            users_result = self.client.table('user_profiles').select('id', count='exact').execute()
            total_users = users_result.count or 0
            
            # Get total trip requests
            requests_result = self.client.table('trip_requests').select('id', count='exact').execute()
            total_requests = requests_result.count or 0
            
            # Get recent activity
            activity_result = self.client.table('user_activity').select('activity_type', count='exact').gte('created_at', (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()).execute()
            daily_activity = activity_result.count or 0
            
            return {
                'total_users': total_users,
                'total_trip_requests': total_requests,
                'daily_activity': daily_activity
            }
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {'total_users': 0, 'total_trip_requests': 0, 'daily_activity': 0}

    async def log_admin_action(self, admin_id: str, action: str, details: Dict = None) -> bool:
        """Log an admin action"""
        try:
            admin_log_record = {
                'admin_id': admin_id,
                'action': action,
                'details': details or {}
            }
            
            result = self.client.table('admin_logs').insert(admin_log_record).execute()
            
            if result.data:
                logger.info(f"🔧 Admin action logged: {action} by {admin_id}")
                return True
            else:
                logger.error(f"❌ Failed to log admin action: {action}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error logging admin action {action}: {e}")
            return False

    async def get_admin_logs(self, limit: int = 100, admin_id: str = None) -> List[Dict]:
        """Get admin action logs"""
        try:
            query = self.client.table('admin_logs').select('*')
            
            if admin_id:
                query = query.eq('admin_id', admin_id)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get admin logs: {e}")
            return []

# Global database service instance
db_service = DatabaseService()

# Export commonly used functions for backward compatibility
get_user_role = db_service.get_user_role
create_user_role = db_service.create_user_role
save_trip = db_service.save_trip
get_user_saved_trips = db_service.get_user_saved_trips
log_trip_request = db_service.log_trip_request
log_user_activity = db_service.log_user_activity