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
        teamFiltersContainer: 'teamFilters',
        cityFiltersContainer: 'cityFilters',
        sortResults: 'sortResults',
        minGamesInput: 'minGames',
        tripOptionsHeader: 'tripOptionsHeader',
        resultsCountContainer: 'resultsCountContainer',
        gamesSlider: 'gamesSlider',
        gamesSliderValue: 'gamesSliderValue',
        hotelChangesSlider: 'hotelChangesSlider',
        hotelChangesValue: 'hotelChangesValue',
    };
    
    // Safely get elements with logging for any missing ones
    for (const [key, id] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            window.DOM[key] = element;
        } else {
            // Only log warnings for required elements
            if (!['viewListBtn', 'teamFiltersContainer', 'cityFiltersContainer', 'sortResults'].includes(id)) {
                console.warn(`DOM element not found: ${id}`);
            }
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

    // Replace your current Select2 initialization code
    $(document).ready(function() {
        // Add loading class to body
        document.body.classList.add('loading-select2');
        
        // Hide preloaders once real components are ready
function hidePreloaders() {
    // First synchronize styling
    document.querySelectorAll('.select2-preloader, .select2-preloader-multi').forEach(el => {
        el.style.position = 'absolute';
        el.style.zIndex = '0';
        el.style.opacity = '0';
        el.style.transition = 'opacity 0.2s ease-out';
    });
    
    // Short delay to start the opacity transition
    setTimeout(() => {
        // Now fade in the real elements
        document.querySelectorAll('#startLocation, #tripDuration, #maxTravelTime, #minGames, #preferredLeaguesContainer, #mustTeamsContainer').forEach(el => {
            el.style.opacity = '1';
            el.style.position = 'relative';
            el.style.zIndex = '1';
        });
        
        // Mark the body as ready
        document.body.classList.add('select2-ready');
        document.body.classList.remove('loading-select2');
    }, 50);
}

        // Initialize all Select2 dropdowns at once
        $('#startLocation, #tripDuration, #maxTravelTime, #minGames').select2({
            width: '100%',
            minimumResultsForSearch: Infinity,
            selectionCssClass: 'select2-selection--clean',
            dropdownCssClass: 'select2-dropdown--clean'
        });
        
        // Initialize the multi-select dropdowns
        $('#preferredLeagues, #mustTeams').select2({
            placeholder: 'Select...',
            width: '100%',
            dropdownParent: $('body'),
            minimumResultsForSearch: Infinity,
            selectionCssClass: 'select2-selection--clean',
            dropdownCssClass: 'select2-dropdown--clean'
        });
        
        // Allow a slightly longer timeout to ensure everything is ready
        setTimeout(hidePreloaders, 300);
    });

    // Add this to your script.js file to handle selection changes
    $(document).ready(function() {
        // Handle preferred leagues selection changes
        $('#preferredLeagues').on('select2:select select2:unselect', function(e) {
            updateSelectionClasses($(this), $('#preferredLeaguesContainer'));
        });
        
        // Handle must teams selection changes
        $('#mustTeams').on('select2:select select2:unselect', function(e) {
            updateSelectionClasses($(this), $('#mustTeamsContainer'));
        });
        
        // Update classes based on selection state
        function updateSelectionClasses(selectElement, containerElement) {
            // Check if there are any selections
            const hasSelections = selectElement.val() && selectElement.val().length > 0;
            
            // Add or remove classes based on selection state
            if (hasSelections) {
                selectElement.next('.select2-container').find('.select2-selection--multiple')
                    .addClass('has-selections');
                containerElement.addClass('has-selections');
            } else {
                selectElement.next('.select2-container').find('.select2-selection--multiple')
                    .removeClass('has-selections');
                containerElement.removeClass('has-selections');
            }
        }
        
        // Run once initially to set the correct state on page load
        setTimeout(function() {
            updateSelectionClasses($('#preferredLeagues'), $('#preferredLeaguesContainer'));
            updateSelectionClasses($('#mustTeams'), $('#mustTeamsContainer'));
        }, 300);
    });

    // Initialize loading animation
    const loadingIndicator = document.getElementById('loading');
    if (loadingIndicator) {
        // Initialize animation when loading becomes visible
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class' && 
                    !loadingIndicator.classList.contains('d-none')) {
                    initLoadingAnimation();
                }
            });
        });
        
        observer.observe(loadingIndicator, { attributes: true });
    }
});

// Enhanced loading animation function - add to script.js
function initLoadingAnimation() {
  const messages = document.querySelectorAll('.loading-message');
  let currentIndex = 0;
  
  // Clear any existing animation
  if (window.loadingMessageInterval) {
    clearInterval(window.loadingMessageInterval);
  }
  
  // Reset all messages
  messages.forEach(msg => {
    msg.classList.remove('active');
    msg.style.opacity = '0';
    msg.style.transform = 'translateY(20px)';
  });
  
  // Activate first message immediately
  if (messages.length > 0) {
    messages[0].classList.add('active');
    messages[0].style.opacity = '1';
    messages[0].style.transform = 'translateY(0)';
    
    // Set up message rotation with better timing
    window.loadingMessageInterval = setInterval(() => {
      // Hide current message
      messages[currentIndex].classList.remove('active');
      messages[currentIndex].style.opacity = '0';
      messages[currentIndex].style.transform = 'translateY(-20px)';
      
      // Move to next message
      currentIndex = (currentIndex + 1) % messages.length;
      
      // Show next message
      setTimeout(() => {
        messages[currentIndex].classList.add('active');
        messages[currentIndex].style.opacity = '1';
        messages[currentIndex].style.transform = 'translateY(0)';
      }, 300);
      
    }, 3000); // Show each message for 3 seconds
  }
}

// Add a cleanup function to clear intervals when loading is hidden
function cleanupLoadingAnimation() {
  if (window.messageInterval) {
    clearInterval(window.messageInterval);
  }
}

// Update returnToSearch function to reset pagination state
function returnToSearch() {
    cleanupLoadingAnimation();
    
    // Reset trip results pagination state
    window.tripResults = null;
    window.tripContext = null;
    
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
    
    // IMPORTANT: Hide the entire results section to prevent white space
    if (window.DOM.resultsSection) {
        window.DOM.resultsSection.classList.add('d-none');
    }
    
    // Enable scrolling
    document.body.classList.remove('no-scroll');
    
    // Scroll back to top
    window.scrollTo({top: 0, behavior: 'smooth'});
}

// Make returnToSearch globally available so onclick can find it
window.returnToSearch = returnToSearch;

// Add this to your document.ready function in script.js
$(document).ready(function() {
    // Initialize flatpickr with consistent styling and timing
    const datePicker = flatpickr("#startDate", {
        dateFormat: "Y-m-d",
        minDate: "today",
        disableMobile: true,
        // Don't show it immediately to maintain consistent transition
        onReady: function() {
            // Delay showing until select2 is also ready
            setTimeout(function() {
                document.querySelector('#startDate').classList.add('flatpickr-ready');
            }, 100);
        },
    });
    
    // This should be at the end of your ready handler, after all Select2 and flatpickr initializations
    setTimeout(function() {
        document.body.classList.add('select2-ready');
        document.body.classList.remove('loading-select2');
    }, 100);
});

// Add to script.js, after your DOM initialization

// Make key functions available globally to avoid import issues
window.renderItineraryForVariant = null;

// Import and expose trip-card.js functions globally for easier access
import('./components/trip-card.js').then(module => {
    window.renderItineraryForVariant = module.renderItineraryForVariant;
});

// Add this to the document ready function in script.js
$(document).ready(function() {
    // Add event listener for trip duration change
    $('#tripDuration').on('change', function() {
        // Import and call the updateMinGamesOptions function
        import('./services/trip-service.js').then(module => {
            if (typeof module.updateMinGamesOptions === 'function') {
                module.updateMinGamesOptions();
            }
        });
    });
    
    // Rest of your existing document.ready code
});


// Export helper functions to avoid circular dependencies
export const helpers = {
    showComponentLoading,
    hideComponentLoading,
    showListView,
    clearFilters
};
