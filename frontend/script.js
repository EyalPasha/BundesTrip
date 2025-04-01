import { 
    loadCities,
    loadLeagues, 
    loadTeams,
    loadAvailableDates
} from './services/data-loader.js';

import { 
    showComponentLoading, 
    hideComponentLoading,
    showListView,
    clearFilters 
} from './services/ui-helpers.js';

import { handleSearch, initFormHandlers, updateMinGamesOptions } from './services/trip-service.js';
import { renderResults } from './components/results-display.js';
import { checkHealth } from './services/api.js';

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
        sortResults: document.getElementById('sortResults'),
        minGamesInput: document.getElementById('minGames'),
        // Add references to any new UI elements here
    };

    // Initialize form handlers
    initFormHandlers();
    
    // Initial update of minGames options based on trip duration
    updateMinGamesOptions();
    
    // Check API health before initializing UI
    try {
        const health = await checkHealth();
        console.log("API Health:", health);
        if (health.status !== 'ok') {
            console.warn("API not fully operational - some features may be limited");
        }
    } catch (error) {
        console.error("API health check failed:", error);
        
        // Create and show toast
        const toastContainer = document.getElementById('toastContainer') || document.createElement('div');
        if (!toastContainer.id) {
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        const toastId = `toast-${Date.now()}`;
        const toast = document.createElement('div');
        toast.className = 'toast show';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.id = toastId;
        
        toast.innerHTML = `
            <div class="toast-header bg-danger text-white">
                <strong class="me-auto">Connection Error</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                Unable to connect to the server. Some features may be limited.
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const toastEl = document.getElementById(toastId);
            if (toastEl) {
                const bsToast = new bootstrap.Toast(toastEl);
                bsToast.hide();
            }
        }, 5000);
    }

    // Initialize date picker with all dates available
    const availableDates = await loadAvailableDates();
    flatpickr(window.DOM.startDateInput, {
        dateFormat: "d F Y",  // Include year in date format
        minDate: "today",
        disableMobile: true,
        allowInput: false,  // Prevent manual text entry to ensure valid dates
        // Add onChange handler to clear validation error if present
        onChange: function(selectedDates, dateStr) {
            if (dateStr) {
                window.DOM.startDateInput.classList.remove('is-invalid');
            }
        },
        // Remove the 'enable' property to allow all dates
        // Instead, highlight dates with games using the onDayCreate callback
        onDayCreate: function(dObj, dStr, fp, dayElem) {
            if (availableDates && availableDates.length > 0) {
                const dateStr = dayElem.dateObj.toISOString().split('T')[0];
                const matchDate = availableDates.find(d => d.date === dateStr);
                
                if (matchDate && matchDate.count) {
                    // Add a visual indicator for dates with games
                    dayElem.classList.add('has-matches');
                    
                    // Create badge with proper positioning
                    const badge = document.createElement('span');
                    badge.className = 'date-badge';
                    badge.textContent = matchDate.count;
                    dayElem.appendChild(badge);
                }
            }
        }
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

    // Replace the current Select2 configuration with this:
    $(document).ready(function() {
        // Configure Preferred Leagues dropdown
        $('#preferredLeagues').select2({
            placeholder: 'Select leagues...',
            width: '100%',
            dropdownParent: $('#preferredLeaguesContainer'),
            minimumResultsForSearch: Infinity,
            selectionCssClass: 'select2-selection--clean',
            dropdownCssClass: 'select2-dropdown--clean'
        });
        
        // Configure Must Include Teams dropdown
        $('#mustTeams').select2({
            placeholder: 'Select teams...',
            width: '100%',
            dropdownParent: $('#mustTeamsContainer'),
            minimumResultsForSearch: Infinity,
            selectionCssClass: 'select2-selection--clean',
            dropdownCssClass: 'select2-dropdown--clean'
        });
    });
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