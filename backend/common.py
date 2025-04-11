import uuid
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger("trip-planner")

# Storage for active request tracking
active_requests = {}

# Check if a request has been cancelled
def is_request_cancelled(request_id: str) -> bool:
    """Check if a request has been cancelled."""
    if request_id in active_requests:
        # Log the check only if it's cancelled (to reduce log noise)
        is_cancelled = active_requests[request_id]["status"] == "cancelled"
        if is_cancelled:
            logger.info(f"Cancellation check for request {request_id}: CANCELLED")
        return is_cancelled
    logger.warning(f"Cancellation check for non-existent request ID: {request_id}")
    return False

# Register a new request
def register_request() -> str:
    """Register a new trip planning request and return its ID."""
    request_id = str(uuid.uuid4())
    active_requests[request_id] = {
        "status": "processing",
        "created_at": datetime.now()
    }
    logger.info(f"New request registered: {request_id}")
    return request_id

# Clean up completed requests
def cleanup_request(request_id: str):
    """Remove a request from tracking after it's complete."""
    if request_id in active_requests:
        status = active_requests[request_id]["status"]
        active_requests.pop(request_id)
        logger.info(f"Request {request_id} cleaned up (status was: {status})")
    else:
        logger.warning(f"Attempted to clean up non-existent request: {request_id}")

# Periodically clean up old requests
def cleanup_old_requests():
    """Clean up requests older than 2 hours."""
    now = datetime.now()
    to_remove = []
    for req_id, req_data in active_requests.items():
        if now - req_data["created_at"] > timedelta(hours=2):
            to_remove.append(req_id)
    
    for req_id in to_remove:
        prev_status = active_requests[req_id]["status"]
        active_requests.pop(req_id)
        logger.info(f"Auto-cleaned expired request {req_id} (was {prev_status})")

# Process the start date string
def get_processed_start_date(start_date=None):
    """Process and validate the start date."""
    if start_date:
        try:
            # Parse date with year included
            parsed_date = datetime.strptime(start_date, "%d %B %Y")
            # Return without year for display
            return parsed_date, f"{parsed_date.day} {parsed_date.strftime('%B')}"
        except ValueError:
            raise ValueError("Invalid start date format. Use '28 March 2025' format.")
    else:
        today = datetime.now()
        next_year = today.year + 1  # Use next year for default dates
        start_with_year = today.replace(year=next_year)
        return start_with_year, today.strftime("%d %B")