import { 
    loadCities,
    loadLeagues, 
    loadTeams,
    loadAvailableDates
} from './data-loader.js';

import { applyTeamLogoStyles, preloadLogos, formatTeamOptionWithLogo, formatTeamSelectionWithLogo, formatLeagueOptionWithLogo, formatLeagueSelectionWithLogo } from './team-logos.js';

import { 
    showComponentLoading, 
    hideComponentLoading,
    showListView,
    clearFilters 
} from './ui-helpers.js';

import { handleSearch, initFormHandlers, updateMinGamesOptions } from './trip-service.js';
import { renderResults } from '../components/results-display.js';
import { checkHealth } from './api.js';
import { initFilterDrawer } from './filters.js'; // Add this import

import { initPreferredLeaguesSelect } from './select2-init.js';

// Import cancellation function
import { cancelTripRequest } from './api.js';

// Add this import at the top with your other imports
import { initializeMatchesExpander } from '../components/trip-card.js';

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
        resultsSection: 'results',
        resultsCount: 'resultsCount',
        tripResults: 'tripResults',
        loadingIndicator: 'loading',
        noResultsMessage: 'noResultsMessage',
        teamFiltersContainer: 'teamFilters',
        cityFiltersContainer: 'cityFilters',
        sortResults: 'sortResults',
        minGamesInput: 'minGames',
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
                //console.warn(`DOM element not found: ${id}`);
            }
            window.DOM[key] = null; // Set to null to allow safe checks
        }
    }
}

// Modify the initialization code to prevent double-initialization

// CONSOLIDATED APP INITIALIZATION
document.addEventListener('DOMContentLoaded', function() {
    // Don't call initializeMobileLayout here anymore
    // It will only be called once during the app initialization
    
    // Continue with the rest of the app initialization
    initializeApp()
        .catch(error => {
            console.error("App initialization error:", error);
            showErrorToast("Failed to initialize application. Please refresh the page.");
        });
    initializeMatchesExpander();
});

// Main application initialization flow
async function initializeApp() {
    // console.log("Starting application initialization...");
    
    // Step 1: Initialize DOM references first
    // console.log("Step 1: Initializing DOM references");
    initDOMReferences();
    
    // Step 2: Apply visual styles and preload resources
    // console.log("Step 2: Applying visual styles");
    document.body.classList.add('loading-select2');
    applyTeamLogoStyles();
    preloadLogos();
    
    // Step 3: Initialize form handlers and basic event listeners
    // console.log("Step 3: Setting up form handlers");
    initFormHandlers();
    updateMinGamesOptions();
    
    // Step 4: Load required data from API
    // console.log("Step 4: Loading data from API");
    try {
        const [cities, leagues, teams, availableDates] = await Promise.all([
            loadCities(),
            loadLeagues(),
            loadTeams(),
            loadAvailableDates(),
            checkApiHealth() // Also check API health in parallel
        ]);
        // console.log("Data loading complete");
    } catch (error) {
        console.error("Error loading initial data:", error);
        // Continue with initialization even if some data fails to load
    }
    
    // Step 5: Initialize UI components
    // console.log("Step 5: Initializing UI components");
    await initializeUIComponents();
    
    // Step 6: Apply mobile-specific layout adjustments
    // console.log("Step 6: Applying mobile layout adjustments");
    initializeMobileLayout();
    
    // Step 7: Set up remaining event listeners
    // console.log("Step 7: Setting up remaining event listeners");
    setupEventListeners();
    
    // Step 8: Set up session management
    // console.log("Step 8: Setting up session management");
    setupSessionManagement();
    
    // Step 9: Try to restore page state
    // console.log("Step 9: Attempting page restoration");
    await attemptPageRestore();
    
    // Step 10: Final UI adjustments and show the form
    // console.log("Step 10: Final UI preparation");
    document.body.classList.add('select2-ready');
    document.body.classList.remove('loading-select2');
    
    // console.log("Application initialization complete");
}

// Replace the initPreferredLeaguesSelect() call with this:
async function initializeUIComponents() {
    // Initialize basic Select2 dropdowns
    $('#startLocation, #tripDuration, #maxTravelTime, #minGames').select2({
        width: '100%',
        minimumResultsForSearch: Infinity,
        selectionCssClass: 'select2-selection--clean',
        dropdownCssClass: 'select2-dropdown--clean'
    });
    
    // Initialize flatpickr date picker once with improved mobile positioning
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
            onOpen: function(selectedDates, dateStr, instance) {
                // Fix mobile positioning on calendar open
                if (window.innerWidth < 768) {
                    const calendarElement = instance.calendarContainer;
                    
                    // Force correct day grid layout
                    setTimeout(() => {
                        // Position the calendar in the center of the screen first
                        calendarElement.style.position = 'fixed';
                        calendarElement.style.top = '50%';
                        calendarElement.style.left = '50%';
                        calendarElement.style.transform = 'translate(-50%, -50%)';
                        
                        // Apply proper positioning class after a brief delay
                        setTimeout(() => {
                            calendarElement.classList.add('proper-position');
                        }, 50);
                    }, 0);
                }
            },
            onClose: function(selectedDates, dateStr, instance) {
                // Remove positioning classes when calendar closes
                const calendarElement = instance.calendarContainer;
                calendarElement.classList.remove('proper-position');
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
    
    // Initialize Visual League Selector (REPLACE the old initPreferredLeaguesSelect)
    initVisualLeagueSelector();
    
    // Initialize Individual Team Select2 dropdowns
    await initIndividualTeamSelects();
    
    // Update selection classes after a short delay to ensure Select2 is ready
    setTimeout(function() {
        // Remove the old leagues update since we're using visual selector now
        // Remove the old mustTeams update since we're using individual selects now
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

// NEW: Visual League Selector initialization
function initVisualLeagueSelector() {
    const leagueBoxes = document.querySelectorAll('.league-box');
    const hiddenSelect = document.getElementById('preferredLeagues');
    const warningElement = document.getElementById('leaguesLimitWarning');
    let selectedLeagues = [];
    
    leagueBoxes.forEach(box => {
        box.addEventListener('click', function() {
            // Remove the disabled check since there's no limit now
            
            const leagueValue = this.dataset.league;
            const combinedLeagues = this.dataset.combined ? this.dataset.combined.split(',') : [leagueValue];
            
            if (this.classList.contains('selected')) {
                // Deselect
                this.classList.remove('selected');
                
                // Remove from selected leagues
                combinedLeagues.forEach(league => {
                    const index = selectedLeagues.indexOf(league);
                    if (index > -1) {
                        selectedLeagues.splice(index, 1);
                    }
                });
                
                // Update hidden select
                combinedLeagues.forEach(league => {
                    const option = hiddenSelect.querySelector(`option[value="${league}"]`);
                    if (option) option.selected = false;
                });
                
            } else {
                // Select (no limit check needed)
                this.classList.add('selected', 'just-selected');
                
                // Add animation class temporarily
                setTimeout(() => {
                    this.classList.remove('just-selected');
                }, 300);
                
                // Add to selected leagues
                combinedLeagues.forEach(league => {
                    if (!selectedLeagues.includes(league)) {
                        selectedLeagues.push(league);
                    }
                });
                
                // Update hidden select
                combinedLeagues.forEach(league => {
                    const option = hiddenSelect.querySelector(`option[value="${league}"]`);
                    if (option) option.selected = true;
                });
            }
            
            // Trigger change event on hidden select
            $(hiddenSelect).trigger('change');
            
            // Update container state
            updateLeagueContainerState();
        });
    });
}

function updateLeagueContainerState() {
    const container = document.getElementById('preferredLeaguesContainer');
    const selectedBoxes = container.querySelectorAll('.league-box.selected');
    
    if (selectedBoxes.length > 0) {
        container.classList.add('has-selections');
    } else {
        container.classList.remove('has-selections');
    }
}

// Update the getSelectedLeagues function to work with the new system
function getSelectedLeagues() {
    const hiddenSelect = document.getElementById('preferredLeagues');
    const selectedOptions = Array.from(hiddenSelect.selectedOptions);
    return selectedOptions.map(option => option.value);
}

// Make it globally available
window.getSelectedLeagues = getSelectedLeagues;

// New function to initialize individual team selects
async function initIndividualTeamSelects() {
    try {
        const teams = await loadTeams(); // This now returns an array of team objects
        
        // Initialize each team select
        for (let i = 1; i <= 4; i++) {
            const selectId = `#mustTeam${i}`;
            const $select = $(selectId);
            
            if ($select.length) {
                // Clear existing options
                $select.empty();
                
                // Add empty option first
                $select.append(new Option(`Select Team ${i}`, '', true, true));
                
                // Populate with team options
                teams.forEach(team => {
                    const option = new Option(team.name, team.id, false, false);
                    $select.append(option);
                });
                
                // Initialize Select2
                $select.select2({
                    placeholder: `Select Team ${i}`,
                    width: '100%',
                    allowClear: true,
                    minimumResultsForSearch: Infinity,
                    selectionCssClass: 'select2-selection--clean',
                    dropdownCssClass: 'select2-dropdown--clean',
                    templateResult: formatTeamOptionWithLogo,
                    templateSelection: formatTeamSelectionWithLogo,
                    dropdownParent: $('body')
                });
                
                // Add change handler
                $select.on('select2:select select2:unselect', function(e) {
                    updateTeamSelectState($(this));
                    preventDuplicateTeamSelection();
                });
            }
        }
    } catch (error) {
        console.error('Error initializing individual team selects:', error);
        showErrorToast('Failed to load teams for selection');
    }
}

// Function to update the visual state of team selects
function updateTeamSelectState($select) {
    const hasSelection = $select.val() && $select.val() !== '';
    const container = $select.next('.select2-container');
    
    if (hasSelection) {
        container.find('.select2-selection--single').addClass('has-team');
    } else {
        container.find('.select2-selection--single').removeClass('has-team');
    }
}

// Function to prevent selecting the same team multiple times
function preventDuplicateTeamSelection() {
    const selectedTeams = [];
    
    // Collect all selected teams
    for (let i = 1; i <= 4; i++) {
        const value = $(`#mustTeam${i}`).val();
        if (value) {
            selectedTeams.push(value);
        }
    }
    
    // Update each dropdown to disable already selected teams
    for (let i = 1; i <= 4; i++) {
        const $select = $(`#mustTeam${i}`);
        const currentValue = $select.val();
        
        // Re-enable all options first
        $select.find('option').prop('disabled', false);
        
        // Disable options that are selected in other dropdowns
        selectedTeams.forEach(teamId => {
            if (teamId !== currentValue) {
                $select.find(`option[value="${teamId}"]`).prop('disabled', true);
            }
        });
        
        // Trigger change to update the dropdown
        $select.trigger('change.select2');
    }
}

// Update the form data collection function
function getSelectedTeams() {
    const teams = [];
    for (let i = 1; i <= 4; i++) {
        const value = $(`#mustTeam${i}`).val();
        if (value) {
            teams.push(value);
        }
    }
    return teams;
}

// Make it globally available
window.getSelectedTeams = getSelectedTeams;

// Check API health and show toast if there's an issue
async function checkApiHealth() {
    try {
        const health = await checkHealth();
        // console.log("API Health:", health);
        if (health.status !== 'ok') {
            //console.warn("API not fully operational - some features may be limited");
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

// Make renderResults globally available for session restore
window.renderResults = renderResults;

// Add all remaining event listeners
function setupEventListeners() {
    // Form submission with auth check
    if(window.DOM.tripSearchForm) {
        window.DOM.tripSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Check authentication FIRST - if fails, stop everything
            if (!checkAuthenticationForTripPlanning()) {
                // console.log("Authentication required - blocking form submission");
                return; // Stop here - don't call handleSearch
            }
            
            // Only proceed with search if authenticated
            handleSearch(e);
        });
    }
    
    // Rest of your existing event listeners...
    $('#tripDuration').on('change', function() {
        updateMinGamesOptions();
    });
    
    
    $('#preferredLeagues').on('select2:select select2:unselect', function(e) {
        updateSelectionClasses($(this), $('#preferredLeaguesContainer'));
    });
    
    $('select').on('select2:open', function() {
        document.body.classList.add('select2-open');
        
        setTimeout(function() {
            const dropdown = document.querySelector('.select2-dropdown');
            if (dropdown) {
                dropdown.style.zIndex = "9999";
            }
        }, 10);
    });
    
    $('select').on('select2:close', function() {
        document.body.classList.remove('select2-open');
    });
    
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
    
    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        const resultObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class' && 
                    !resultsSection.classList.contains('d-none')) {
                    const filterCard = document.getElementById('filterResultsCard');
                    if (filterCard) {
                        filterCard.style.display = 'none';
                    }
                }
            });
        });
        
        resultObserver.observe(resultsSection, { attributes: true });
    }
}

// Add a flag to track if mobile layout has been initialized
let mobileLayoutInitialized = false;

function initializeMobileLayout() {
    // Check if we're on mobile
    const isMobile = window.innerWidth < 768;
    
    // Exit if not mobile or already initialized
    if(!isMobile || mobileLayoutInitialized) {
        return;
    }
    
    // console.log("Mobile layout detected - initializing mobile UI");
    
    // Mark as initialized to prevent duplicate initialization
    mobileLayoutInitialized = true;
    
    // Add mobile-ready class to the body ASAP
    document.body.classList.add('mobile-ready');
    
    // Make form sections collapsible on mobile with custom titles
    const formSections = document.querySelectorAll('.form-section');
    
    // Set custom titles for sections
    const sectionTitles = [
        "Starting Location", // First section remains visible
        "Times and Duration",
        "Additional Filters"
    ];
    
    // First step: Get the start date container
    const startDateContainer = document.querySelector('#startDate')?.closest('.mb-3');
    
    // Second step: Remove the start date container from its original location
    if (startDateContainer) {
        startDateContainer.parentNode.removeChild(startDateContainer);
    }

    // Third step: Create collapsible sections
    formSections.forEach((section, index) => {
        // Skip the first section - keep it visible
        if(index > 0) {
            // Check if this section already has a header (prevent duplication)
            if (section.querySelector('.form-section-header')) {
                return; // Skip this section if it already has a header
            }
            
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
            
            // Create content container
            const content = document.createElement('div');
            content.className = 'form-section-content';
            
            // Move all content except header into this container
            while(section.childNodes.length > 1) {
                content.appendChild(section.childNodes[1]);
            }
            section.appendChild(content);
            
            // Toggle section on click with smooth animation
            header.addEventListener('click', function() {
                const isOpen = content.classList.contains('show');
                
                // Update icon first for snappy feedback
                header.querySelector('i').className = isOpen ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
                
                // Toggle content visibility with animation
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
            }
        }
    });
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

// Update the returnToSearch function to use the cancellation API
function returnToSearch() {
    cleanupLoadingAnimation();
    
    // Cancel the current request if exists
    if (window.currentRequestId) {
        cancelTripRequest(window.currentRequestId)
            .then(result => {
                if (result.success) {
                    // console.log("Trip request cancelled successfully");
                    // Remove any notification code here
                } else {
                    //console.warn("Failed to cancel trip request:", result.message);
                }
            })
            .catch(err => {
                //console.warn("Error during cancellation:", err);
            })
            .finally(() => {
                // Clear the request ID regardless of outcome
                window.currentRequestId = null;
            });
    }
    
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
    
    // Reset cancel button state
    if (cancelButton) {
        cancelButton.classList.remove('d-none');
        cancelButton.disabled = false;
        cancelButton.innerHTML = '<i class="fas fa-times-circle"></i> Cancel Search';
    }
    
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
import('../components/trip-card.js').then(module => {
    window.renderItineraryForVariant = module.renderItineraryForVariant;
});

// Export helper functions to avoid circular dependencies
export const helpers = {
    showComponentLoading,
    hideComponentLoading,
    showListView,
    clearFilters
};

// Add this function to handle authentication checks

function checkAuthenticationForTripPlanning() {
    // Use synchronous check - don't call async getCurrentUser()
    const user = window.authService?.currentUser;
    
    if (!user) {
        // Show login modal and prevent any further action
        showLoginPrompt();
        return false;
    }
    return true;
}

function showLoginPrompt() {
    const modalHTML = `
        <div class="modal fade" id="loginPromptModal" tabindex="-1" aria-labelledby="loginPromptModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content modern-modal">
                    <button type="button" class="btn-close-custom" data-bs-dismiss="modal" aria-label="Close">
                        <i class="fas fa-times"></i>
                    </button>
                    <div class="modal-body px-4 py-4">
                        <div class="text-center mb-4">
                            <div class="auth-icon-container mb-3">
                                <i class="fas fa-user-shield fa-1x"></i>
                                <div class="icon-bg"></div>
                            </div>
                            <h4 class="fw-semibold text-dark mb-2">Please log in to plan your trip</h4>
                            <p class="text-muted mb-0">You need an account to save and manage your personalized trip plans. Join thousands of football fans who trust BundesTrip!</p>
                        </div>
                        <div class="auth-actions">
                            <div class="row g-3">
                                <div class="col-12 col-sm-6">
                                    <a href="./login.html" class="btn btn-primary btn-lg w-100 auth-btn">
                                        <i class="fas fa-sign-in-alt me-2"></i>
                                        <span>Login</span>
                                    </a>
                                </div>
                                <div class="col-12 col-sm-6">
                                    <a href="./register.html" class="btn btn-outline-primary btn-lg w-100 auth-btn">
                                        <i class="fas fa-user-plus me-2"></i>
                                        <span>Create Account</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        /* Modal Container */
        .modern-modal {
            border: none;
            border-radius: 1.25rem;
            box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25), 0 0 0 1px rgb(255 255 255 / 0.05);
            overflow: hidden;
            position: relative;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        }
        
        /* Custom Close Button */
        .btn-close-custom {
            position: absolute;
            top: 1.25rem;
            right: 1.25rem;
            background: none;
            border: none;
            color: #64748b;
            font-size: 1.125rem;
            cursor: pointer;
            z-index: 10;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            background: rgba(100, 116, 139, 0.1);
        }
        
        .btn-close-custom:hover {
            background: rgba(220, 38, 38, 0.1);
            color: #dc2626;
            transform: scale(1.05);
        }
        
        .btn-close-custom:active {
            transform: scale(0.95);
        }
        
        /* Auth Icon Container */
        .auth-icon-container {
            position: relative;
            display: inline-block;
            margin-bottom: 1rem;
        }
        
        .auth-icon-container i {
            color: #043d7c !important;
            position: relative;
            z-index: 2;
        }
        
        .auth-icon-container .icon-bg {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, rgba(4, 61, 124, 0.1), rgba(4, 61, 124, 0.05));
            border-radius: 50%;
            transform: translate(-50%, -50%);
            z-index: 1;
            animation: pulse 3s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { 
                transform: translate(-50%, -50%) scale(1); 
                opacity: 0.8; 
            }
            50% { 
                transform: translate(-50%, -50%) scale(1.1); 
                opacity: 0.4; 
            }
        }
        
        /* Modal Typography */
        .modern-modal h4 {
            color: #1e293b;
            font-weight: 600;
            line-height: 1.3;
        }
        
        .modern-modal p {
            color: #64748b;
            line-height: 1.6;
        }
        
        /* Benefits Grid */
        .auth-benefits {
            background: linear-gradient(135deg, rgba(4, 61, 124, 0.03), rgba(4, 61, 124, 0.01));
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid rgba(4, 61, 124, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        .auth-benefits::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #043d7c, transparent);
            opacity: 0.3;
        }
        
        .benefit-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 0.75rem 0.5rem;
            transition: transform 0.2s ease;
        }
        
        .benefit-item:hover {
            transform: translateY(-2px);
        }
        
        .benefit-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #043d7c, #032c59);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.5rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        
        .benefit-icon i {
            color: white !important;
            font-size: 0.875rem;
        }
        
        .benefit-item small {
            font-weight: 500;
            color: #374151;
            font-size: 0.8rem;
        }
        
        /* Auth Buttons */
        .auth-btn {
            position: relative;
            font-weight: 600;
            border-radius: 0.875rem;
            padding: 1rem 1.5rem;
            transition: all 0.3s ease;
            overflow: hidden;
            border: 2px solid transparent;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            min-height: 56px; /* Add this line */
            box-sizing: border-box; /* Add this line */
        }
        
        .auth-btn span {
            white-space: nowrap; /* Add this rule */
        }
        
        .auth-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s ease;
        }
        
        .auth-btn:hover::before {
            left: 100%;
        }
        
        .btn-primary.auth-btn {
            background: linear-gradient(135deg, #043d7c 0%, #032c59 100%);
            border-color: #043d7c;
            color: white;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        
        .btn-primary.auth-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
            background: linear-gradient(135deg, #032c59 0%, #043d7c 100%);
            color: white;
        }
        
        .btn-outline-primary.auth-btn {
            border: 2px solid #043d7c;
            color: #043d7c;
            background: transparent;
        }
        
        .btn-outline-primary.auth-btn:hover {
            background: #043d7c;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        }
        
        .auth-btn i {
            color: inherit !important;
        }
        
        /* Mobile Responsive */
        @media (max-width: 576px) {
            .modal-dialog {
                max-width: calc(100vw - 2rem);
                margin: 1rem;
            }
            
            .modern-modal .modal-body {
                padding: 2rem 1.5rem;
            }
            
            .btn-close-custom {
                top: 1rem;
                right: 1rem;
                width: 32px;
                height: 32px;
                font-size: 1rem;
            }
            
            .auth-icon-container i {
                font-size: 1.5rem !important;
            }
            
            .auth-icon-container .icon-bg {
                width: 55px;
                height: 55px;
            }
            
            .auth-benefits {
                padding: 1rem;
            }
            
            .benefit-icon {
                width: 36px;
                height: 36px;
            }
            
            .benefit-icon i {
                font-size: 0.75rem !important;
            }
            
            .benefit-item small {
                font-size: 0.75rem;
            }
            
            .auth-btn {
                padding: 0.875rem 1.25rem;
                font-size: 0.9rem;
                min-height: 50px; /* Add this line for mobile */
            }
            
            h4 {
                font-size: 1.25rem !important;
            }
            
            .auth-benefits .row {
                gap: 0.5rem !important;
            }
        }
        
        /* Tablet */
        @media (min-width: 577px) and (max-width: 768px) {
            .modal-dialog {
                max-width: 85vw;
            }
        }
        
        /* Large screens */
        @media (min-width: 769px) {
            .modal-dialog {
                max-width: 520px;
            }
        }
        
        /* Accessibility */
        @media (prefers-reduced-motion: reduce) {
            .auth-btn::before,
            .auth-icon-container .icon-bg,
            .benefit-item {
                animation: none !important;
                transition: none !important;
            }
        }
        
        /* High contrast mode */
        @media (prefers-contrast: high) {
            .modern-modal {
                border: 2px solid #1e293b;
            }
            
            .auth-benefits {
                border: 2px solid #043d7c;
            }
            
            .btn-close-custom {
                border: 1px solid #64748b;
            }
        }
        
        /* Focus States */
        .btn-close-custom:focus-visible {
            outline: 2px solid #043d7c;
            outline-offset: 2px;
        }
        
        .auth-btn:focus-visible {
            outline: 2px solid #043d7c;
            outline-offset: 2px;
        }
        </style>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('loginPromptModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal with backdrop: 'static' to prevent dismissal by clicking outside
    const modal = new bootstrap.Modal(document.getElementById('loginPromptModal'), {
        backdrop: 'static', // Prevents closing by clicking outside
        keyboard: false     // Prevents closing with Escape key
    });
    modal.show();
}

// New function to set up session management
function setupSessionManagement() {
    if (window.sessionManager) {
        // Set up navigation detection
        window.sessionManager.setupNavigationDetection();
        
        // Set up scroll position tracking
        let scrollTimer;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimer);
            scrollTimer = setTimeout(() => {
                const scrollPosition = window.pageYOffset || document.documentElement.scrollTop || 0;
                if (window.sessionManager && scrollPosition > 0) {
                    window.sessionManager.updateScrollPosition(scrollPosition);
                }
            }, 250); // Throttle scroll updates
        });
        
        // Listen for page visibility changes to save current state
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'hidden') {
                // Page is being hidden (user switching tabs/apps)
                const scrollPosition = window.pageYOffset || document.documentElement.scrollTop || 0;
                if (window.sessionManager && scrollPosition > 0) {
                    window.sessionManager.updateScrollPosition(scrollPosition);
                }
            }
        });
    }
}

// New function to attempt page restoration
async function attemptPageRestore() {
    if (window.sessionRestore) {
        try {
            const restored = await window.sessionRestore.restorePage();
            if (restored) {
                //console.log('✅ Page state restored from session');
            }
        } catch (error) {
            //console.warn('⚠️ Page restoration failed:', error);
        }
    }
}