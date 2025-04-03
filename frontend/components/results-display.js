import { renderTripCard, renderTbdGames } from './trip-card.js';
import { renderFilters } from '../services/filters.js'; 
import { showListView } from '../services/ui-helpers.js';

/**
 * Renders trip search results with enhanced handling of backend data
 * Properly processes trip groups, variations, hotel information and airport data
 * 
 * @param {Object} response - The API response from the trip planning endpoint
 * @param {boolean} hideLoadingOnNoResults - Indicates whether to keep the loading container visible
 */
// Updated renderResults function with pagination support
function renderResults(response, hideLoadingOnNoResults = true) {
    const tripResults = document.getElementById('tripResults');
    
    // Clear previous results
    if (tripResults) {
        tripResults.innerHTML = '';
    }

    // Initialize the window.tripResults pagination state
    if (response.trip_groups && response.trip_groups.length > 0) {
        // Store all trips for pagination
        window.tripResults = {
            allTrips: response.trip_groups || [],
            renderedCount: 0,
            batchSize: 3, // Display 3 trips per batch
            hasMoreTrips: true
        };
    } else {
        window.tripResults = null;
    }
    
    // Update the results count if it exists
    const resultsCount = document.getElementById('resultsCount');
    if (resultsCount) {
        // Count both trip groups and TBD games if available
        const tripCount = response.trip_groups ? response.trip_groups.length : 0;
        const tbdCount = response.tbd_games ? response.tbd_games.length : 0;
        
        if (tripCount > 0) {
            resultsCount.textContent = `${tripCount} trip${tripCount !== 1 ? 's' : ''} found`;
        } else if (tbdCount > 0) {
            resultsCount.textContent = `${tbdCount} upcoming unscheduled game${tbdCount !== 1 ? 's' : ''}`;
        } else {
            resultsCount.textContent = 'No results found';
        }
    }
    
    // Show TBD games FIRST if available
    if (response.tbd_games && response.tbd_games.length > 0) {
        renderTbdGames(response.tbd_games, response.must_teams || []);
    }
    
    // Process trip groups (if any)
    if (response.trip_groups && response.trip_groups.length > 0) {
        // Show filter card
        const filterResultsCard = document.getElementById('filterResultsCard');
        if (filterResultsCard) {
            filterResultsCard.classList.remove('d-none');
        }
        
        // Add min games info to results header if present
        const resultsHeader = document.querySelector('#resultsContainer h2');
        if (resultsHeader && response.min_games) {
            resultsHeader.innerHTML = `Trip Results <span class="badge bg-primary" id="tripCount">${response.trip_groups.length}</span>
                <small class="ms-2 text-muted">(min. ${response.min_games} games/trip)</small>`;
        }
        
        // Generate filters based on match data
        renderFilters(response.trip_groups);
        
        // Store trip context for all rendered trips
        window.tripContext = {
            startLocation: response.start_location,
            startDate: response.start_date,
            maxTravelTime: response.max_travel_time,
            tripDuration: response.trip_duration,
            preferredLeagues: response.preferred_leagues,
            mustTeams: response.must_teams
        };
        
        // Render first batch of trips instead of all at once
        renderNextBatch();
        
        // Enable sorting and list-view controls once results are displayed
        const sortingControl = document.getElementById('sortResults');
        if (sortingControl) {
            sortingControl.classList.remove('d-none');
        }
        
        const viewListBtn = document.getElementById('viewList');
        if (viewListBtn) {
            viewListBtn.classList.remove('d-none');
            viewListBtn.onclick = () => showListView(response.trip_groups);
        }
    } else {
        // Hide filter card if no results
        const filterResultsCard = document.getElementById('filterResultsCard');
        if (filterResultsCard) {
            filterResultsCard.classList.add('d-none');
        }
    }
    
    // Rest of your existing code for handling messages, loading state, etc.
    // Handle error messages or no results
    if (response.message) {
        const messageContainer = document.getElementById('messageContainer') || 
            document.createElement('div');
        
        if (!messageContainer.id) {
            messageContainer.id = 'messageContainer';
            messageContainer.className = 'alert alert-info mb-4';
            if (tripResults.firstChild) {
                tripResults.insertBefore(messageContainer, tripResults.firstChild);
            } else {
                tripResults.appendChild(messageContainer);
            }
        }
        
        messageContainer.textContent = response.message;
    }
    
    // Only process loading state if we have results OR if we're explicitly told to hide loading
    const hasResults = (response.trip_groups && response.trip_groups.length > 0) || 
                       (response.tbd_games && response.tbd_games.length > 0);
                       
    if (hasResults || hideLoadingOnNoResults) {
        // Only hide loading if we have results or are explicitly told to
        if (window.DOM && window.DOM.loadingIndicator) {
            window.DOM.loadingIndicator.classList.add('d-none');
        }
        
        // Enable scrolling
        document.body.classList.remove('no-scroll');
    }
    
    // Remove any "no scheduled games" messages that would be redundant
    const messageContainer = document.getElementById('messageContainer');
    if (messageContainer) {
        if (messageContainer.textContent.includes("No scheduled games found")) {
            messageContainer.remove();
        }
    }
    
    // Initialize tooltips on newly rendered elements
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
    }
}

/**
 * Extracts unique cities from trip groups for filtering
 * @param {Array} tripGroups - Array of trip groups from API response
 * @returns {Array} - Unique cities across all trips
 */
function extractCities(tripGroups) {
    const cities = new Set();
    
    tripGroups.forEach(group => {
        if (group.variation_details && group.variation_details.length > 0) {
            group.variation_details.forEach(variation => {
                if (variation.cities && Array.isArray(variation.cities)) {
                    variation.cities.forEach(city => cities.add(city));
                }
            });
        }
    });
    
    return [...cities].sort();
}

/**
 * Extracts unique teams from trip groups for filtering
 * @param {Array} tripGroups - Array of trip groups from API response
 * @returns {Array} - Unique teams across all trips
 */
function extractTeams(tripGroups) {
    const teams = new Set();
    
    tripGroups.forEach(group => {
        if (group.variation_details && group.variation_details.length > 0) {
            group.variation_details.forEach(variation => {
                if (variation.teams && Array.isArray(variation.teams)) {
                    variation.teams.forEach(team => teams.add(team));
                }
            });
        }
    });
    
    return [...teams].sort();
}

// Update the renderNextBatch function
function renderNextBatch() {
    const state = window.tripResults;
    if (!state || !state.allTrips) return;

    const resultsContainer = document.getElementById('tripResults');
    
    // Calculate the end index for this batch
    const start = state.renderedCount;
    const end = Math.min(start + state.batchSize, state.allTrips.length);
    
    // Render this batch of trips
    for (let i = start; i < end; i++) {
        const trip = state.allTrips[i];
        renderTripCard(trip, i + 1, window.tripContext);
    }
    
    // Update the rendered count
    state.renderedCount = end;
    state.hasMoreTrips = state.renderedCount < state.allTrips.length;
    
    // Remove any existing load more button
    const existingButton = document.getElementById('loadMoreTrips');
    if (existingButton) {
        existingButton.remove();
    }
    
    // Add load more button if there are more trips
    if (state.hasMoreTrips) {
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.id = 'loadMoreTrips';
        loadMoreBtn.className = 'text-center my-4';
        loadMoreBtn.innerHTML = `
        <button class="btn btn-outline-primary load-more-btn">
            <i class="fas fa-chevron-down me-2"></i>
            Load More Trips
            <span class="ms-2 badge">
                ${state.renderedCount}/${state.allTrips.length}
            </span>
        </button>
    `;
        loadMoreBtn.addEventListener('click', renderNextBatch);
        resultsContainer.appendChild(loadMoreBtn);
    } else if (state.renderedCount > 0) {
        // Add a "no more trips" indicator when all trips are loaded
        const noMoreTrips = document.createElement('div');
        noMoreTrips.className = 'text-center text-muted my-4';
        noMoreTrips.innerHTML = `
            <p><i class="fas fa-check-circle me-2"></i>All ${state.allTrips.length} trips loaded</p>
        `;
        resultsContainer.appendChild(noMoreTrips);
    }
}
export { renderResults, extractCities, extractTeams, renderNextBatch };