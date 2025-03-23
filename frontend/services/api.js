// API Base URL - adjust as needed for production
const API_BASE_URL = 'http://localhost:8000';

/**
 * Make an API request with built-in error handling and retry logic
 * @param {string} endpoint - API endpoint to call
 * @param {object} options - Fetch API options
 * @param {number} retries - Number of retry attempts for server errors
 * @returns {Promise<object|null>} Response data or null on error
 */
async function fetchApi(endpoint, options = {}, retries = 2) {
    try {
        // Create a promise that will resolve with either the fetch result or a timeout error
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        clearTimeout(timeoutId);
        
        // Enhanced error handling with user-friendly messages
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            let errorMessage;
            
            switch (response.status) {
                case 400:
                    errorMessage = errorData.error || 'Invalid request. Please check your search criteria.';
                    break;
                case 401:
                    errorMessage = 'Authentication required. Please log in again.';
                    break;
                case 403:
                    errorMessage = 'You don\'t have permission to access this resource.';
                    break;
                case 404:
                    errorMessage = 'The requested resource was not found.';
                    break;
                case 429:
                    errorMessage = 'Too many requests. Please try again later.';
                    break;
                case 500:
                case 502:
                case 503:
                case 504:
                    errorMessage = 'Server error. Our team has been notified.';
                    break;
                default:
                    errorMessage = errorData.error || `Error (${response.status})`;
            }
            
            // Log the actual error details for debugging
            console.error(`API Error: ${response.status} ${response.statusText}`, errorData);
            
            // Retry logic for server errors (5xx)
            if (response.status >= 500 && retries > 0) {
                console.warn(`Retrying request to ${endpoint} (${retries} retries left)`);
                return fetchApi(endpoint, options, retries - 1);
            }
            
            throw new Error(errorMessage);
        }
        
        return await response.json();
    } catch (error) {
        // Handle network errors and timeouts
        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please check your connection and try again.');
        } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            throw new Error('Network error. Please check your internet connection.');
        }
        
        // Re-throw the error with the message we've already set
        throw error;
    }
}

/**
 * Get all available cities for starting points
 * @returns {Promise<Array>} List of cities
 */
async function getCities() {
    return fetchApi('/available-cities');
}

/**
 * Get all available leagues
 * @returns {Promise<Array>} List of leagues
 */
async function getLeagues() {
    return fetchApi('/available-leagues');
}

/**
 * Get all available teams, optionally filtered by league
 * @param {string|null} league - League to filter by
 * @returns {Promise<Array>} List of teams
 */
async function getTeams(league = null) {
    const endpoint = league ? `/available-teams?league=${encodeURIComponent(league)}` : '/available-teams';
    return fetchApi(endpoint);
}

/**
 * Plan a trip with the given parameters
 * @param {object} tripData - Trip planning parameters
 * @returns {Promise<object>} Trip planning results
 */
async function planTrip(tripData) {
    return fetchApi('/plan-trip', {
        method: 'POST',
        body: JSON.stringify(tripData)
    });
}

/**
 * Get available dates with matches
 * @param {object} params - Filter parameters
 * @param {string|null} params.league - League to filter by
 * @param {string|null} params.team - Team to filter by
 * @param {number} params.days - Number of days to look ahead
 * @returns {Promise<Array>} List of dates with match counts
 */
async function getAvailableDates(params = {}) {
    const queryParams = new URLSearchParams();
    
    if (params.league) queryParams.append('league', params.league);
    if (params.team) queryParams.append('team', params.team);
    if (params.days) queryParams.append('days', params.days);
    
    const endpoint = `/available-dates${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return fetchApi(endpoint);
}

/**
 * Get cities reachable from a specific city
 * @param {string} city - Source city name
 * @param {number} maxTime - Maximum travel time in minutes
 * @returns {Promise<object>} List of reachable cities with travel times
 */
async function getCityConnections(city, maxTime = 240) {
    return fetchApi(`/city-connections/${encodeURIComponent(city)}?max_time=${maxTime}`);
}

/**
 * Get a team's schedule
 * @param {string} team - Team name
 * @param {number} days - Number of days to look ahead
 * @returns {Promise<object>} Team schedule information
 */
async function getTeamSchedule(team, days = 60) {
    return fetchApi(`/team-schedule/${encodeURIComponent(team)}?days=${days}`);
}

// Export all API functions
export {
    fetchApi,
    getCities,
    getLeagues,
    getTeams,
    planTrip,
    getAvailableDates,
    getCityConnections,
    getTeamSchedule
};