import { renderTripCard, renderTbdGames } from './trip-card.js';
import { renderFilters } from '../services/filters.js'; 
import { showListView } from '../services/ui-helpers.js';

// Enhanced rendering function to process airport data and travel options
function renderResults(response) {
    const tripResults = document.getElementById('tripResults');
    
    // Clear previous results
    if (tripResults) {
        tripResults.innerHTML = '';
    }
    
    // Show TBD games FIRST if available
    if (response.tbd_games && response.tbd_games.length > 0) {
        renderTbdGames(response.tbd_games);
    }
    
    // Process trip groups (if any)
    if (response.trip_groups && response.trip_groups.length > 0) {
        response.trip_groups.forEach((group, index) => {
            renderTripCard(group, index + 1);
        });
    }
    
    // Only show no results message if BOTH trips AND TBD games are missing
    if ((!response.trip_groups || response.trip_groups.length === 0) && 
        (!response.tbd_games || response.tbd_games.length === 0)) {
        window.DOM.noResultsMessage.classList.remove('d-none');
    } else {
        window.DOM.noResultsMessage.classList.add('d-none');
    }
}

export { renderResults };