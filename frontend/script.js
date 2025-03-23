import { 
    loadCities,
    loadLeagues, 
    loadTeams,
    updateTeamsByLeague
} from './services/data-loader.js';

import { 
    showComponentLoading, 
    hideComponentLoading,
    showListView,
    clearFilters 
} from './services/ui-helpers.js';

import { handleSearch } from './services/trip-service.js';
import { renderResults } from './components/results-display.js';

// Create a global DOM object to share references between modules
window.DOM = {};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // Store DOM references globally for access from other modules
    window.DOM = {
        tripSearchForm: document.getElementById('tripSearchForm'),
        startLocationSelect: document.getElementById('startLocation'),
        startDateInput: document.getElementById('startDate'),
        tripDurationInput: document.getElementById('tripDuration'),
        maxTravelTimeInput: document.getElementById('maxTravelTime'),
        preferredLeaguesSelect: document.getElementById('preferredLeagues'),
        mustTeamsSelect: document.getElementById('mustTeams'),
        resultsSection: document.getElementById('results'),
        resultsCount: document.getElementById('resultsCount'),
        tripResults: document.getElementById('tripResults'),
        loadingIndicator: document.getElementById('loading'),
        noResultsMessage: document.getElementById('noResults'),
        viewListBtn: document.getElementById('viewList'),
        teamFiltersContainer: document.getElementById('teamFilters'),
        cityFiltersContainer: document.getElementById('cityFilters'),
        sortResults: document.getElementById('sortResults')
    };

    // Initialize date picker
    flatpickr(window.DOM.startDateInput, {
        dateFormat: "d F",
        minDate: "today",
        disableMobile: true
    });
    
    // Initialize selects
    await Promise.all([
        loadCities(),
        loadLeagues(),
        loadTeams()
    ]);
    
    // Initialize event listeners
    window.DOM.tripSearchForm.addEventListener('submit', handleSearch);
    
    // Make these globally available for other modules that might need them
    window.appHelpers = {
        showComponentLoading,
        hideComponentLoading,
        showListView,
        clearFilters
    };
    
    // Add sorting functionality
    if (window.DOM.sortResults) {
        window.DOM.sortResults.addEventListener('change', handleSortResults);
    }

});

// Sort results by selected criteria
function handleSortResults() {
    const sortBy = this.value;
    const tripCards = [...document.querySelectorAll('.trip-card')];
    
    tripCards.sort((a, b) => {
        if (sortBy === 'matches') {
            // Sort by number of matches (descending)
            const matchesA = a.querySelector('.badge.bg-primary')?.textContent.trim().split(' ')[0] || "0";
            const matchesB = b.querySelector('.badge.bg-primary')?.textContent.trim().split(' ')[0] || "0";
            return parseInt(matchesB) - parseInt(matchesA);
        } else if (sortBy === 'travel') {
            // Sort by travel time (ascending)
            const travelTimeA = a.querySelector('.text-success')?.nextElementSibling?.textContent || "";
            const travelTimeB = b.querySelector('.text-success')?.nextElementSibling?.textContent || "";
            
            const hoursA = parseInt(travelTimeA.match(/(\d+)h/)?.[1] || "0");
            const hoursB = parseInt(travelTimeB.match(/(\d+)h/)?.[1] || "0");
            
            const minutesA = parseInt(travelTimeA.match(/(\d+)m/)?.[1] || "0");
            const minutesB = parseInt(travelTimeB.match(/(\d+)m/)?.[1] || "0");
            
            return (hoursA * 60 + minutesA) - (hoursB * 60 + minutesB);
        }
        return 0;
    });
    
    // Reorder the DOM elements
    const container = document.getElementById('tripResults');
    tripCards.forEach(card => {
        container.appendChild(card);
    });
}

// Export helper functions to avoid circular dependencies
export const helpers = {
    showComponentLoading,
    hideComponentLoading,
    showListView,
    clearFilters
};