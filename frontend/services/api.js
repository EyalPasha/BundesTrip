// API Base URL - adjust as needed for production
const API_BASE_URL = 'http://10.0.0.28:8000';

/**
 * Get auth token for API requests
 */
function getAuthHeaders() {
    const token = window.authService?.getAuthToken()
    return token ? {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    } : {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
}

/**
 * Make an API request with built-in error handling and retry logic
 * @param {string} endpoint - API endpoint to call
 * @param {object} options - Fetch API options
 * @param {number} retries - Number of retry attempts for server errors
 * @returns {Promise<object|null>} Response data or null on error
 */
async function fetchApi(endpoint, options = {}, retries = 2) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000); 
        
        const cacheOptions = {
            cache: endpoint.includes('plan-trip') ? 'no-cache' : 'default',
            keepalive: true,
            ...options,
        };
        
        console.log(`Fetching ${API_BASE_URL}${endpoint}...`);
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...cacheOptions,
            signal: controller.signal,
            headers: {
                ...getAuthHeaders(), // Use auth headers instead of API key
                'X-Client-Source': 'web-interface',
                'Connection': 'keep-alive',
                'Ngrok-Skip-Browser-Warning': 'true',
                ...options.headers
            },
            mode: 'cors'
        });
        
        clearTimeout(timeoutId);        
        
        // Check if we're getting HTML instead of JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/html')) {
            console.error(`Received HTML response instead of JSON for ${endpoint}`);
            throw new Error('Server returned HTML instead of JSON. This may indicate a CORS or server configuration issue.');
        }
        
        // Enhanced error handling with user-friendly messages
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            let errorMessage;
            
            switch (response.status) {
                case 400:
                    errorMessage = errorData.error || 'Invalid request. Please check your search criteria.';
                    break;
                case 401:
                    errorMessage = 'Please log in to continue.';
                    // Redirect to login if not authenticated
                    if (window.location.pathname !== '/login.html') {
                        window.location.href = '/login.html';
                    }
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
        
        // Make the request with a header reader to extract request ID early
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);
        
        const response = await fetch(`${API_BASE_URL}/plan-trip`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Ngrok-Skip-Browser-Warning': 'true'
            },
            body: JSON.stringify(tripData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // Handle non-OK responses
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Server error (${response.status})`);
        }
        
        // Get response data
        const data = await response.json();
        
        // Extract and store request ID as early as possible
        if (data.request_id) {
            window.currentRequestId = data.request_id;
            console.log("Request ID received:", data.request_id);
        }
        
        // Provide better error for no trips
        if (data.no_trips_available && loadingText) {
            if (data.min_games > 1) {
                loadingText.textContent = 
                    `No trips found with ${data.min_games} or more games. Try reducing the minimum games requirement.`;
            } else {
                loadingText.textContent = 
                    `No trips found. Try adjusting your search parameters.`;
            }
        }
        
        // Clear the timer
        clearInterval(loadingTimer);
        
        return data;
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
 * @returns {Promise<Array>} List of dates with match counts
 */
async function getAvailableDates(params = {}) {
    const queryParams = new URLSearchParams();
    
    if (params.league) queryParams.append('league', params.league);
    if (params.team) queryParams.append('team', params.team);
    // Remove days parameter - no longer supported by backend
    
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
 * @returns {Promise<object>} Team schedule information
 */
async function getTeamSchedule(team) {
    // No longer using the days parameter
    return fetchApi(`/team-schedule/${encodeURIComponent(team)}`);
}

/**
 * Get a league's schedule
 * @param {string} league - League name
 * @returns {Promise<object>} League schedule
 */
async function getLeagueSchedule(league) {
    // No longer using the days parameter
    return fetchApi(`/league-schedule/${encodeURIComponent(league)}`);
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
 * @param {boolean} includePast - Whether to include past games
 * @returns {Promise<object>} Games on date
 */
async function getGamesByDate(date, league = null, includePast = false) {
    const queryParams = new URLSearchParams();
    
    if (league) queryParams.append('league', league);
    if (includePast) queryParams.append('include_past', 'true');
    
    const endpoint = `/games-by-date/${date}${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return fetchApi(endpoint);
}

/**
 * Get game details for a specific date
 * @param {string} league - League name
 * @param {string} date - Date in YYYY-MM-DD format
 * @param {boolean} includePast - Whether to include past games
 * @returns {Promise<object>} Game details
 */
async function getGameDetails(league, date, includePast = false) {
    const queryParams = new URLSearchParams();
    
    if (includePast) queryParams.append('include_past', 'true');
    
    const endpoint = `/game-details/${encodeURIComponent(league)}/${date}${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
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

/**
 * Cancel an ongoing trip planning request
 * @param {string} requestId - The ID of the request to cancel
 * @returns {Promise<object>} Response from the cancellation request
 */
async function cancelTripRequest(requestId) {
    if (!requestId) {
        console.warn("No request ID to cancel");
        return { success: false, message: "No request ID provided" };
    }
    
    console.log(`Attempting to cancel request: ${requestId}`);
    
    try {
        // Use direct fetch with API_BASE_URL
        const url = `${API_BASE_URL}/cancel-trip/${requestId}`;
        console.log(`Sending cancellation request to: ${url}`);
        
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'Ngrok-Skip-Browser-Warning': 'true'
            }
        });
        
        console.log(`Cancellation response status: ${response.status} ${response.statusText}`);
        
        if (!response.ok) {
            let errorText = await response.text();
            console.error(`Server error during cancellation: ${errorText}`);
            return { success: false, message: `Failed to cancel: ${response.statusText}` };
        }
        
        const result = await response.json();
        console.log(`Successfully cancelled request ${requestId}:`, result);
        return { success: true, ...result };
    } catch (error) {
        console.error(`Error cancelling trip request ${requestId}:`, error);
        return { success: false, message: error.message };
    }
}

// Update your API service to include authentication

class ApiService {
    constructor() {
        this.baseURL = this.detectApiUrl();
        console.log(`🌐 API Service initialized with base URL: ${this.baseURL}`);
    }

    detectApiUrl() {
        const hostname = window.location.hostname;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000';
        } else if (hostname.startsWith('192.168.') || hostname.startsWith('10.0.')) {
            return `http://${hostname}:8000`;
        } else {
            return 'http://10.0.0.28:8000';
        }
    }

    // Get authentication headers
    async getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };

        // Add auth token if user is signed in
        if (window.authService && window.authService.initialized) {
            // Get current session to ensure fresh token
            try {
                const { data: { session } } = await supabase.auth.getSession();
                
                if (session?.access_token) {
                    // Update auth service with fresh token
                    window.authService.authToken = session.access_token;
                    window.authService.currentUser = session.user;
                    
                    headers['Authorization'] = `Bearer ${session.access_token}`;
                    console.log('🔐 Including fresh auth token in request');
                    
                    // Log token expiry for debugging
                    try {
                        const payload = JSON.parse(atob(session.access_token.split('.')[1]));
                        const expiryTime = new Date(payload.exp * 1000);
                        console.log('🕐 Token expires at:', expiryTime.toLocaleString());
                    } catch (e) {
                        console.log('🔍 Could not parse token expiry');
                    }
                } else {
                    console.warn('⚠️ No session found - user may need to log in again');
                }
            } catch (error) {
                console.error('❌ Error getting fresh session:', error);
            }
        } else {
            console.warn('⚠️ Auth service not ready');
        }

        return headers;
    }

    async makeRequest(url, options = {}) {
        try {
            const headers = await this.getAuthHeaders();
            
            console.log('📡 Making request to:', url);
            console.log('🔧 Request headers:', headers);
            
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...headers,
                    ...options.headers
                },
                credentials: 'include'  // Add this for CORS
            });

            console.log('📨 Response status:', response.status);

            if (!response.ok) {
                if (response.status === 401) {
                    console.error('🔒 Authentication failed - token may be invalid');
                    
                    // Try to get response body for more details
                    try {
                        const errorBody = await response.text();
                        console.error('🔍 Error response body:', errorBody);
                    } catch (e) {
                        console.error('Could not read error response body');
                    }
                    
                    // Try to refresh token and retry once
                    if (window.authService && !options._isRetry) {
                        console.log('🔄 Attempting token refresh and retry...');
                        const newToken = await window.authService.refreshToken();
                        
                        if (newToken) {
                            // Retry the request once with new token
                            const newHeaders = await this.getAuthHeaders();
                            return this.makeRequest(url, {
                                ...options,
                                headers: {
                                    ...newHeaders,
                                    ...options.headers
                                },
                                _isRetry: true // Prevent infinite retry loop
                            });
                        }
                    }
                    
                    throw new Error('Authentication failed. Please log in again.');
                } else if (response.status === 403) {
                    throw new Error('Access forbidden. Insufficient permissions.');
                } else if (response.status === 500) {
                    // Try to get more specific error message
                    try {
                        const errorBody = await response.text();
                        console.error('🔍 Server error details:', errorBody);
                        throw new Error(`Server error: ${errorBody || 'Internal server error'}`);
                    } catch (e) {
                        throw new Error(`Server error (${response.status})`);
                    }
                } else {
                    throw new Error(`Server error (${response.status})`);
                }
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                console.error('🌐 Network error - this could be a CORS issue or server is down');
                throw new Error('Network error: Unable to connect to server. Please check if the server is running.');
            }
            console.error(`API request failed:`, error);
            throw error;
        }
    }

    // Plan a trip with authentication
    async planTrip(tripData) {
        console.log('🚀 Planning trip with data:', tripData);
        
        try {
            const result = await this.makeRequest(`${this.baseURL}/plan-trip`, {
                method: 'POST',
                body: JSON.stringify(tripData)
            });

            console.log('✅ Trip planning successful');
            return result;
        } catch (error) {
            console.error('❌ Trip planning error:', error);
            console.error('Request payload was:', tripData);
            throw error;
        }
    }

    // Get request ID with authentication
    async getRequestId() {
        try {
            const result = await this.makeRequest(`${this.baseURL}/register-request`);
            return result.request_id;
        } catch (error) {
            console.error('Failed to get request ID:', error);
            return null;
        }
    }

    // Cancel trip request
    async cancelTrip(requestId) {
        try {
            const result = await this.makeRequest(`${this.baseURL}/cancel-trip/${requestId}`, {
                method: 'DELETE'
            });
            return result;
        } catch (error) {
            console.error('Failed to cancel trip:', error);
            throw error;
        }
    }

    // Get request status
    async getRequestStatus(requestId) {
        try {
            const result = await this.makeRequest(`${this.baseURL}/request-status/${requestId}`);
            return result;
        } catch (error) {
            console.error('Failed to get request status:', error);
            return null;
        }
    }

    // Public endpoints (no auth required)
    async getAvailableLeagues() {
        try {
            const response = await fetch(`${this.baseURL}/available-leagues`);
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch leagues:', error);
            return { leagues: [] };
        }
    }

    async getAvailableTeams(league = null) {
        try {
            const url = league ? 
                `${this.baseURL}/available-teams?league=${encodeURIComponent(league)}` : 
                `${this.baseURL}/available-teams`;
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch teams:', error);
            return { teams: [] };
        }
    }

    async getAvailableCities() {
        try {
            const response = await fetch(`${this.baseURL}/available-cities`);
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch cities:', error);
            return { cities: [] };
        }
    }
        
    async saveTrip(tripData, originalRequest, isFavorite = false) {
        try {
            console.log('🔄 Saving trip data:', {
                tripData: tripData,
                originalRequest: originalRequest,
                isFavorite: isFavorite
            });
            
            const requestBody = {
                trip_data: tripData,
                original_request: originalRequest,
                is_favorite: isFavorite
                // No trip_name - backend will auto-generate with numbering
            };
            
            // Use the makeRequest method like other API calls
            const result = await this.makeRequest(`${this.baseURL}/api/save-trip`, {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });
    
            console.log('✅ Trip saved successfully:', result);
            return result;
            
        } catch (error) {
            console.error('❌ Failed to save trip:', error);
            throw error;
        }
    }

    async getSavedTrips(limit = 20, favoritesOnly = false) {
        try {
            const headers = await this.getAuthHeaders();
            
            const url = `${this.baseURL}/api/saved-trips?limit=${limit}&favorites_only=${favoritesOnly}`;
            const response = await fetch(url, {
                method: 'GET',
                headers
            });

            if (!response.ok) {
                throw new Error(`Failed to get saved trips: ${response.status}`);
            }

            const result = await response.json();
            console.log('📚 Loaded saved trips:', result);
            return result;
            
        } catch (error) {
            console.error('❌ Failed to get saved trips:', error);
            throw error;
        }
    }

    async deleteSavedTrip(tripId) {
        try {
            const headers = await this.getAuthHeaders();
            
            const response = await fetch(`${this.baseURL}/api/saved-trips/${tripId}`, {
                method: 'DELETE',
                headers
            });

            if (!response.ok) {
                throw new Error(`Failed to delete trip: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ Failed to delete trip:', error);
            throw error;
        }
    }

    async toggleTripFavorite(tripId) {
        try {
            const headers = await this.getAuthHeaders();
            
            const response = await fetch(`${this.baseURL}/api/saved-trips/${tripId}/favorite`, {
                method: 'POST',
                headers
            });

            if (!response.ok) {
                throw new Error(`Failed to toggle favorite: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ Failed to toggle favorite:', error);
            throw error;
        }
    }
    
    async unsaveTrip(tripId) {
        try {
            console.log('🗑️ Attempting to unsave trip:', tripId);
            
            const response = await fetchApi('/trips/unsave', {  // Note: /trips/unsave not /api/trips/unsave
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    trip_id: tripId
                })
            });
    
            if (response.success) {
                console.log('✅ Trip unsaved successfully:', response);
                
                // Log user activity
                await this.logUserActivity('trip_unsaved', {
                    trip_id: tripId,
                    trip_name: response.trip_name || 'Unknown Trip',
                    action_details: 'Trip removed from saved collection'
                });
                
                return response;
            } else {
                throw new Error(response.message || 'Failed to unsave trip');
            }
            
        } catch (error) {
            console.error('❌ Failed to unsave trip:', error);
            throw error;
        }
    }

    // Log user activity
    async logUserActivity(activityType, details = {}) {
        try {
            const user = window.authService?.getCurrentUser();
            if (!user) return; // Don't log if user not authenticated
            
            const activityData = {
                user_id: user.id,
                activity_type: activityType,
                activity_details: details,
                timestamp: new Date().toISOString(),
                user_agent: navigator.userAgent,
                ip_address: 'client-side' // Will be replaced by server
            };
            
            await fetchApi('/user/activity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(activityData)
            });
            
            console.log(`📊 User activity logged: ${activityType}`, details);
            
        } catch (error) {
            console.warn('⚠️ Failed to log user activity:', error);
            // Don't throw - activity logging shouldn't break main functionality
        }
    }

    // Get trip request history
    async getTripRequestHistory(limit = 20) {
        try {
            console.log('📋 Fetching trip request history...');
            
            const response = await fetchApi(`/api/trip-request-history?limit=${limit}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            console.log(`✅ Retrieved ${response.requests?.length || 0} trip requests`);
            return response;
            
        } catch (error) {
            console.error('❌ Failed to get trip request history:', error);
            throw error;
        }
    }
}

// Create global instance
window.apiService = new ApiService();

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
    refreshData,
    cancelTripRequest,
    API_BASE_URL,
    ApiService,
};

// Also export as default for easier importing
export default ApiService;

// Add this to the global assignments at the end of api.js:

window.unsaveTrip = function(tripId) {
    return window.apiService.unsaveTrip(tripId);
};

window.logUserActivity = function(activityType, details) {
    return window.apiService.logUserActivity(activityType, details);
};