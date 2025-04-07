import { 
    loadCities,
    loadLeagues, 
    loadTeams,
    loadAvailableDates
} from './services/data-loader.js';

import { applyTeamLogoStyles, preloadLogos, formatTeamOptionWithLogo, formatTeamSelectionWithLogo, formatLeagueOptionWithLogo, formatLeagueSelectionWithLogo } from './services/team-logos.js';

import { 
    showComponentLoading, 
    hideComponentLoading,
    showListView,
    clearFilters 
} from './services/ui-helpers.js';

import { handleSearch, initFormHandlers, updateMinGamesOptions } from './services/trip-service.js';
import { renderResults } from './components/results-display.js';
import { checkHealth } from './services/api.js';

import { initPreferredLeaguesSelect } from './services/select2-init.js';

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

// CONSOLIDATED APP INITIALIZATION
document.addEventListener('DOMContentLoaded', function() {
    // Use a structured promise chain for proper sequencing
    initializeApp()
        .catch(error => {
            console.error("App initialization error:", error);
            showErrorToast("Failed to initialize application. Please refresh the page.");
        });
});

// Main application initialization flow
async function initializeApp() {
    console.log("Starting application initialization...");
    
    // Step 1: Initialize DOM references first
    console.log("Step 1: Initializing DOM references");
    initDOMReferences();
    
    // Step 2: Apply visual styles and preload resources
    console.log("Step 2: Applying visual styles");
    document.body.classList.add('loading-select2');
    applyTeamLogoStyles();
    preloadLogos();
    
    // Step 3: Initialize form handlers and basic event listeners
    console.log("Step 3: Setting up form handlers");
    initFormHandlers();
    updateMinGamesOptions();
    
    // Step 4: Load required data from API
    console.log("Step 4: Loading data from API");
    try {
        const [cities, leagues, teams, availableDates] = await Promise.all([
            loadCities(),
            loadLeagues(),
            loadTeams(),
            loadAvailableDates(),
            checkApiHealth() // Also check API health in parallel
        ]);
        console.log("Data loading complete");
    } catch (error) {
        console.error("Error loading initial data:", error);
        // Continue with initialization even if some data fails to load
    }
    
    // Step 5: Initialize UI components
    console.log("Step 5: Initializing UI components");
    await initializeUIComponents();
    
    // Step 6: Apply mobile-specific layout adjustments
    console.log("Step 6: Applying mobile layout adjustments");
    initializeMobileLayout();
    
    // Step 7: Set up remaining event listeners
    console.log("Step 7: Setting up remaining event listeners");
    setupEventListeners();
    
    // Step 8: Final UI adjustments and show the form
    console.log("Step 8: Final UI preparation");
    document.body.classList.add('select2-ready');
    document.body.classList.remove('loading-select2');
    
    console.log("Application initialization complete");
}

// Initialize all UI components (Select2, flatpickr, etc.)
async function initializeUIComponents() {
    // Initialize basic Select2 dropdowns
    $('#startLocation, #tripDuration, #maxTravelTime, #minGames').select2({
        width: '100%',
        minimumResultsForSearch: Infinity,
        selectionCssClass: 'select2-selection--clean',
        dropdownCssClass: 'select2-dropdown--clean'
    });
    
    // Initialize flatpickr date picker once
    const availableDates = await loadAvailableDates();
    if(window.DOM.startDateInput) {
        flatpickr(window.DOM.startDateInput, {
            dateFormat: "d F Y",
            minDate: "today",
            disableMobile: true,
            allowInput: false,
            onChange: function(selectedDates, dateStr) {
                if (dateStr) {
                    window.DOM.startDateInput.classList.remove('is-invalid');
                }
            },
            onDayCreate: function(dObj, dStr, fp, dayElem) {
                if (availableDates && availableDates.length > 0) {
                    const dateStr = dayElem.dateObj.toISOString().split('T')[0];
                    const matchDate = availableDates.find(d => d.date === dateStr);
                    
                    if (matchDate && matchDate.count) {
                        dayElem.classList.add('has-matches');
                        
                        const badge = document.createElement('span');
                        badge.className = 'date-badge';
                        badge.textContent = matchDate.count;
                        dayElem.appendChild(badge);
                    }
                }
            },
            onReady: function() {
                setTimeout(function() {
                    if(document.querySelector('#startDate')) {
                        document.querySelector('#startDate').classList.add('flatpickr-ready');
                    }
                }, 100);
            }
        });
    }
    
    // Initialize Preferred Leagues Select2
    initPreferredLeaguesSelect();
    
    // Initialize Must Teams Select2
    if(window.DOM.mustTeamsSelect) {
        $(window.DOM.mustTeamsSelect).select2({
            placeholder: 'Select Teams',
            width: '100%',
            closeOnSelect: false,
            allowClear: true,
            minimumResultsForSearch: Infinity,
            selectionCssClass: 'select2-selection--clean',
            dropdownCssClass: 'select2-dropdown--clean',
            templateResult: formatTeamOptionWithLogo,
            templateSelection: formatTeamSelectionWithLogo,
            dropdownParent: $('body')
        });
    }
    
    // Update selection classes after a short delay to ensure Select2 is ready
    setTimeout(function() {
        updateSelectionClasses($('#preferredLeagues'), $('#preferredLeaguesContainer'));
        updateSelectionClasses($('#mustTeams'), $('#mustTeamsContainer'));
    }, 300);
    
    // Return a promise that resolves when everything is initialized
    return new Promise(resolve => {
        // Hide preloaders with a slight delay to ensure components are ready
        setTimeout(() => {
            hidePreloaders();
            resolve();
        }, 300);
    });
}

// Check API health and show toast if there's an issue
async function checkApiHealth() {
    try {
        const health = await checkHealth();
        console.log("API Health:", health);
        if (health.status !== 'ok') {
            console.warn("API not fully operational - some features may be limited");
        }
        return health;
    } catch (error) {
        console.error("API health check failed:", error);
        showErrorToast("Unable to connect to the server. Some features may be limited.");
        return { status: 'error', error };
    }
}

// Show error toast message
function showErrorToast(message) {
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
            <strong class="me-auto">Error</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const toastEl = document.getElementById(toastId);
        if (toastEl) {
            if (typeof bootstrap !== 'undefined') {
                const bsToast = new bootstrap.Toast(toastEl);
                bsToast.hide();
            } else {
                toastEl.remove();
            }
        }
    }, 5000);
}

// Add all remaining event listeners
function setupEventListeners() {
    // Form submission
    if(window.DOM.tripSearchForm) {
        window.DOM.tripSearchForm.addEventListener('submit', handleSearch);
    }
    
    // Trip duration change
    $('#tripDuration').on('change', function() {
        updateMinGamesOptions();
    });
    
    // Handle preferred leagues selection changes
    $('#preferredLeagues').on('select2:select select2:unselect', function(e) {
        updateSelectionClasses($(this), $('#preferredLeaguesContainer'));
    });
    
    // Handle must teams selection changes
    $('#mustTeams').on('select2:select select2:unselect', function(e) {
        updateSelectionClasses($(this), $('#mustTeamsContainer'));
    });
    
    // Fix dropdown position when opened
    $('select').on('select2:open', function() {
        document.body.classList.add('select2-open');
        
        // Ensure dropdown is properly positioned
        setTimeout(function() {
            const dropdown = document.querySelector('.select2-dropdown');
            if (dropdown) {
                dropdown.style.zIndex = "9999";
            }
        }, 10);
    });
    
    // Clean up when dropdown closes
    $('select').on('select2:close', function() {
        document.body.classList.remove('select2-open');
    });
    
    // Initialize loading animation observer
    const loadingIndicator = document.getElementById('loading');
    if (loadingIndicator) {
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
}

// Initialize mobile-specific layouts
function initializeMobileLayout() {
    // Check if we're on mobile
    const isMobile = window.innerWidth < 768;
    
    if(isMobile) {
        console.log("Mobile layout detected - initializing mobile UI");
        
        // Make form sections collapsible on mobile with custom titles
        const formSections = document.querySelectorAll('.form-section');
        
        // Set custom titles for sections
        const sectionTitles = [
            "Starting Location", // First section remains visible
            "Times and Duration",
            "Additional Filters"
        ];
        
        // First step: Get the start date container BEFORE changing the DOM structure
        // This avoids potential issues where the selector cannot find the element later
        const startDateContainer = document.querySelector('#startDate').closest('.mb-3');
        
        // Second step: Remove the start date container from its original location
        if (startDateContainer) {
            startDateContainer.parentNode.removeChild(startDateContainer);
            console.log("✅ Start date removed from original location");
        } else {
            console.error("❌ Could not find start date container");
            // If we can't find it, return early to avoid breaking the layout
            return;
        }

        // Third step: Create collapsible sections
        formSections.forEach((section, index) => {
            // Skip the first section - keep it visible
            if(index > 0) {
                // Create collapsible header with custom title
                const header = document.createElement('div');
                header.className = 'form-section-header';
                header.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center py-1">
                        <span class="section-title">${sectionTitles[index]}</span>
                        <i class="fas fa-chevron-down"></i>
                    </div>
                `;
                
                // Insert header before section content
                section.prepend(header);
                
                // Hide section content initially
                const content = document.createElement('div');
                content.className = 'form-section-content collapse';
                
                // Move all content except header into this container
                while(section.childNodes.length > 1) {
                    content.appendChild(section.childNodes[1]);
                }
                section.appendChild(content);
                
                // Toggle section on click
                header.addEventListener('click', function() {
                    const isOpen = content.classList.contains('show');
                    header.querySelector('i').className = isOpen ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
                    
                    if(isOpen) {
                        content.classList.remove('show');
                    } else {
                        content.classList.add('show');
                    }
                });
                
                // Fourth step: If this is the "Times and Duration" section, insert the start date
                if (index === 1 && startDateContainer) {
                    // Insert at the beginning of the content container
                    content.insertBefore(startDateContainer, content.firstChild);
                    console.log("✅ Start date successfully moved to Times and Duration section");
                }
            }
        });
    }
}

// Update selection classes function
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

// Hide preloaders function
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
            if(el) {
                el.style.opacity = '1';
                el.style.position = 'relative';
                el.style.zIndex = '1';
            }
        });
    }, 50);
}

// Enhanced loading animation function
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

// Cleanup function for loading animation
function cleanupLoadingAnimation() {
  if (window.loadingMessageInterval) {
    clearInterval(window.loadingMessageInterval);
  }
}

// Return to search function
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
    
    // Hide the entire results section to prevent white space
    if (window.DOM.resultsSection) {
        window.DOM.resultsSection.classList.add('d-none');
    }
    
    // Enable scrolling
    document.body.classList.remove('no-scroll');
    
    // Scroll back to top
    window.scrollTo({top: 0, behavior: 'smooth'});
}

// Make returnToSearch globally available
window.returnToSearch = returnToSearch;

// Make key functions available globally
window.renderItineraryForVariant = null;

// Import and expose trip-card.js functions globally
import('./components/trip-card.js').then(module => {
    window.renderItineraryForVariant = module.renderItineraryForVariant;
});

// Export helper functions to avoid circular dependencies
export const helpers = {
    showComponentLoading,
    hideComponentLoading,
    showListView,
    clearFilters
};