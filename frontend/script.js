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

// Function to safely initialize DOM references
function initDOMReferences() {
    const elements = {
        tripSearchForm: 'tripSearchForm',
        startLocationSelect: 'startLocation',
        startDateInput: 'startDate',
        tripDurationInput: 'tripDuration',
        maxTravelTimeInput: 'maxTravelTime',
        preferredLeaguesSelect: 'preferredLeagues',
        mustTeamsSelect: 'mustTeams',
        resultsSection: 'results',
        resultsCount: 'resultsCount',
        tripResults: 'tripResults',
        loadingIndicator: 'loading',
        noResultsMessage: 'noResultsMessage',
        viewListBtn: 'viewList',
        teamFiltersContainer: 'teamFilters',
        cityFiltersContainer: 'cityFilters',
        sortResults: 'sortResults',
        minGamesInput: 'minGames',
        tripOptionsHeader: 'tripOptionsHeader',
        resultsCountContainer: 'resultsCountContainer',
    };
    
    // Safely get elements with logging for any missing ones
    for (const [key, id] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            window.DOM[key] = element;
        } else {
            console.warn(`DOM element not found: ${id}`);
            window.DOM[key] = null; // Set to null to allow safe checks
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // Initialize DOM references
    initDOMReferences();
    
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

    // Initialize loading animation
    initLoadingAnimation();
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

function initLoadingAnimation() {
  // Rotate through loading messages
  const messages = document.querySelectorAll('.loading-message');
  let currentIndex = 0;
  
  if (messages.length > 0) {
    setInterval(() => {
      // Remove active class from current message
      messages[currentIndex].classList.remove('active');
      
      // Move to next message
      currentIndex = (currentIndex + 1) % messages.length;
      
      // Add active class to new message
      messages[currentIndex].classList.add('active');
    }, 2500);
  }
}

function returnToSearch() {
    // Hide the loading container
    if (window.DOM.loadingIndicator) {
        window.DOM.loadingIndicator.classList.add('d-none');
    }
    
    // Reset the content inside loading for next time
    const loadingAnimation = document.getElementById('loadingAnimation');
    const loadingMessages = document.getElementById('loadingMessages');
    const cancelButton = document.getElementById('cancelSearch');
    const noResultsMessage = document.getElementById('noResultsMessage');
    
    if (loadingAnimation) loadingAnimation.classList.remove('d-none');
    if (loadingMessages) loadingMessages.classList.remove('d-none');
    if (cancelButton) cancelButton.classList.remove('d-none');
    if (noResultsMessage) noResultsMessage.classList.add('d-none');
    
    // Enable scrolling
    document.body.classList.remove('no-scroll');
    
    // Scroll back to top
    window.scrollTo({top: 0, behavior: 'smooth'});
}

// Make returnToSearch globally available so onclick can find it
window.returnToSearch = returnToSearch;

// Export helper functions to avoid circular dependencies
export const helpers = {
    showComponentLoading,
    hideComponentLoading,
    showListView,
    clearFilters
};