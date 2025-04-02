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
        console.time(`API call to ${endpoint}`); // Add timing
        
        // Reduce timeout to 60 seconds
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000); 
        
        // Add keep-alive connection for better performance
        const cacheOptions = {
            cache: endpoint.includes('plan-trip') ? 'no-cache' : 'default',
            keepalive: true,
            ...options,
        };
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...cacheOptions,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                'X-Client-Source': 'web-interface', // Help server identify source
                'Connection': 'keep-alive',
                'Accept': 'application/json',
                ...options.headers
            }
        });
        
        clearTimeout(timeoutId);
        console.timeEnd(`API call to ${endpoint}`); // Log timing
        
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
    const loadingIndicator = document.getElementById('loadingIndicator');
    const loadingText = document.getElementById('loadingText');
    
    // Only update loading text if the element exists
    if (loadingIndicator) loadingIndicator.classList.remove('d-none');
    
    try {
        // Start a timer to update the loading message
        let secondsElapsed = 0;
        const loadingTimer = setInterval(() => {
            secondsElapsed++;
            // Only update loading text if the element exists
            if (loadingText) {
                if (secondsElapsed < 5) {
                    loadingText.textContent = 'Connecting to server...';
                } else if (secondsElapsed < 20) {
                    loadingText.textContent = `Planning trip routes (${secondsElapsed}s)...`;
                } else if (secondsElapsed < 40) {
                    loadingText.textContent = `Finding matches (${secondsElapsed}s)...`;
                } else {
                    loadingText.textContent = `Processing results (${secondsElapsed}s)...`; 
                }
            }
        }, 1000);
        
        // Make the request
        const response = await fetchApi('/plan-trip', {
            method: 'POST',
            body: JSON.stringify(tripData)
        });
        
        // Provide better error for no trips meeting min games criteria - but check if element exists first
        if (response.no_trips_available && loadingText) {
            if (response.min_games > 1) {
                loadingText.textContent = 
                    `No trips found with ${response.min_games} or more games. Try reducing the minimum games requirement.`;
            } else {
                loadingText.textContent = 
                    `No trips found. Try adjusting your search parameters.`;
            }
        }
        
        // Clear the timer
        clearInterval(loadingTimer);
        
        return response;
    } catch (error) {
        console.error("Trip planning error:", error);
        console.error("Request payload was:", JSON.stringify(tripData, null, 2));
        throw error;
    } finally {
        if (loadingIndicator) loadingIndicator.classList.add('d-none');
    }
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

/**
 * Get game details for a specific date and league
 * @param {string} league - League name
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<object>} Game details
 */
async function getGameDetails(league, date) {
    return fetchApi(`/game-details/${encodeURIComponent(league)}/${date}`);
}

/**
 * Get a league's schedule
 * @param {string} league - League name
 * @param {number} days - Number of days to look ahead
 * @returns {Promise<object>} League schedule
 */
async function getLeagueSchedule(league, days = 60) {
    return fetchApi(`/league-schedule/${encodeURIComponent(league)}?days=${days}`);
}

/**
 * Get airport information and connections
 * @param {string|null} city - Filter for connections to a specific city
 * @returns {Promise<object>} Airport information
 */
async function getAirportInformation(city = null) {
    const endpoint = city ? `/airport-information?city=${encodeURIComponent(city)}` : '/airport-information';
    return fetchApi(endpoint);
}

/**
 * Get travel statistics
 * @returns {Promise<object>} Travel statistics
 */
async function getTravelStats() {
    return fetchApi('/travel-stats');
}

/**
 * Get all games on a specific date
 * @param {string} date - Date in YYYY-MM-DD format
 * @param {string|null} league - Filter by league
 * @returns {Promise<object>} Games on date
 */
async function getGamesByDate(date, league = null) {
    const endpoint = league 
        ? `/games-by-date/${date}?league=${encodeURIComponent(league)}`
        : `/games-by-date/${date}`;
    return fetchApi(endpoint);
}

/**
 * Check API health
 * @returns {Promise<object>} Health status
 */
async function checkHealth() {
    return fetchApi('/health');
}

/**
 * Search for teams, cities, or leagues
 * @param {string} query - Search query (min 2 characters)
 * @param {Array<string>} types - Types to search ["teams", "cities", "leagues"]
 * @returns {Promise<object>} Search results
 */
async function search(query, types = ["teams", "cities", "leagues"]) {
    const queryParams = new URLSearchParams();
    queryParams.append('q', query);
    
    // Add each type as a separate query parameter
    types.forEach(type => queryParams.append('types', type));
    
    return fetchApi(`/search?${queryParams.toString()}`);
}

/**
 * Refresh game and travel data (admin only)
 * @param {string} apiKey - Admin API key
 * @returns {Promise<object>} Refresh status
 */
async function refreshData(apiKey) {
    return fetchApi(`/admin/refresh-data?api_key=${apiKey}`, {
        method: 'POST'
    });
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
    getTeamSchedule,
    getGameDetails,
    getLeagueSchedule,
    getAirportInformation,
    getTravelStats,
    getGamesByDate,
    checkHealth,
    search,
    refreshData
};