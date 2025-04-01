import { renderTripCard, renderTbdGames } from './trip-card.js';
import { renderFilters } from '../services/filters.js'; 
import { showListView } from '../services/ui-helpers.js';

/**
 * Renders trip search results with enhanced handling of backend data
 * Properly processes trip groups, variations, hotel information and airport data
 * 
 * @param {Object} response - The API response from the trip planning endpoint
 */
function renderResults(response) {
    const tripResults = document.getElementById('tripResults');
    
    // Clear previous results
    if (tripResults) {
        tripResults.innerHTML = '';
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
        // Add min games info to results header if present
        const resultsHeader = document.querySelector('#resultsContainer h2');
        if (resultsHeader && response.min_games) {
            resultsHeader.innerHTML = `Trip Results <span class="badge bg-primary" id="tripCount">${response.trip_groups.length}</span>
                <small class="ms-2 text-muted">(min. ${response.min_games} games/trip)</small>`;
        }
        
        // Generate filters based on match data
        renderFilters(response.trip_groups);
        
        // Render each trip group
        response.trip_groups.forEach((group, index) => {
            renderTripCard(group, index + 1, {
                startLocation: response.start_location,
                startDate: response.start_date,
                maxTravelTime: response.max_travel_time,
                tripDuration: response.trip_duration,
                preferredLeagues: response.preferred_leagues,
                mustTeams: response.must_teams
            });
        });
        
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
    }
    
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
    
    // Only show no results message if BOTH trips AND TBD games are missing
    if ((!response.trip_groups || response.trip_groups.length === 0) && 
        (!response.tbd_games || response.tbd_games.length === 0)) {
        
        if (window.DOM && window.DOM.noResultsMessage) {
            window.DOM.noResultsMessage.classList.remove('d-none');
        }
        
        // Hide sorting and list-view controls when no results
        const sortingControl = document.getElementById('sortResults');
        if (sortingControl) {
            sortingControl.classList.add('d-none');
        }
        
        const viewListBtn = document.getElementById('viewList');
        if (viewListBtn) {
            viewListBtn.classList.add('d-none');
        }
    } else {
        if (window.DOM && window.DOM.noResultsMessage) {
            window.DOM.noResultsMessage.classList.add('d-none');
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

export { renderResults, extractCities, extractTeams };