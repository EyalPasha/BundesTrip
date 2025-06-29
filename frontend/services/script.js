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
                console.warn(`DOM element not found: ${id}`);
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
    
    // Initialize Preferred Leagues Select2
    initPreferredLeaguesSelect();
    
    // Initialize Individual Team Select2 dropdowns
    await initIndividualTeamSelects();
    
    // Update selection classes after a short delay to ensure Select2 is ready
    setTimeout(function() {
        updateSelectionClasses($('#preferredLeagues'), $('#preferredLeaguesContainer'));
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
    
    // Setup selection limits
    setupSelectionLimits();
    
    // Handle preferred leagues selection changes
    $('#preferredLeagues').on('select2:select select2:unselect', function(e) {
        updateSelectionClasses($(this), $('#preferredLeaguesContainer'));
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
    
    // Initialize filter drawer when results are first shown
    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        const resultObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class' && 
                    !resultsSection.classList.contains('d-none')) {
                    // Hide the old filter card with CSS
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
    
    console.log("Mobile layout detected - initializing mobile UI");
    
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
                    console.log("Trip request cancelled successfully");
                    // Remove any notification code here
                } else {
                    console.warn("Failed to cancel trip request:", result.message);
                }
            })
            .catch(err => {
                console.warn("Error during cancellation:", err);
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
    const user = window.authService?.currentUser;
    
    if (!user) {
        // Show login modal instead of error
        showLoginPrompt();
        return false;
    }
    return true;
}

function showLoginPrompt() {
    const modalHTML = `
        <div class="modal fade" id="loginPromptModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-sign-in-alt me-2"></i>Login Required
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <i class="fas fa-user-circle fa-3x text-primary mb-3"></i>
                            <h6>Please log in to plan your trip</h6>
                            <p class="text-muted">You need an account to save and manage your trip plans.</p>
                        </div>
                        <div class="d-grid gap-2">
                            <a href="./login.html" class="btn btn-primary">
                                <i class="fas fa-sign-in-alt me-2"></i>Login
                            </a>
                            <a href="./register.html" class="btn btn-outline-primary">
                                <i class="fas fa-user-plus me-2"></i>Create Account
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('loginPromptModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('loginPromptModal'));
    modal.show();
}

// Update your existing form submission handler
document.getElementById('tripSearchForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Check authentication first
    if (!checkAuthenticationForTripPlanning()) {
        return;
    }
});

// Add selection limit handlers
function setupSelectionLimits() {
    // Preferred Leagues - Max 3
    $('#preferredLeagues').on('select2:select', function(e) {
        const selectedCount = $(this).val()?.length || 0;
        const warningElement = document.getElementById('leaguesLimitWarning');

        if (selectedCount >= 3) {
            // Disable remaining options
            $(this).find('option:not(:selected)').each(function() {
                $(this).prop('disabled', true);
            });
            $(this).select2('destroy').select2({
                placeholder: 'Maximum 3 leagues selected',
                width: '100%',
                closeOnSelect: false,
                allowClear: true,
                minimumResultsForSearch: Infinity,
                selectionCssClass: 'select2-selection--clean',
                dropdownCssClass: 'select2-dropdown--clean',
                templateResult: formatLeagueOptionWithLogo,
                templateSelection: formatLeagueSelectionWithLogo,
                dropdownParent: $('body')
            });

            // --- FIX: Re-apply .has-selections class ---
            const $container = $(this).next('.select2-container').find('.select2-selection--multiple');
            if ($(this).val() && $(this).val().length > 0) {
                $container.addClass('has-selections');
                $('#preferredLeaguesContainer').addClass('has-selections');
            }

            warningElement.classList.add('show');
        }

        updateSelectionClasses($(this), $('#preferredLeaguesContainer'));
    });

    $('#preferredLeagues').on('select2:unselect', function(e) {
        const selectedCount = $(this).val()?.length || 0;
        const warningElement = document.getElementById('leaguesLimitWarning');

        if (selectedCount < 3) {
            // Re-enable all options
            $(this).find('option').prop('disabled', false);
            $(this).select2('destroy').select2({
                placeholder: 'Select Leagues',
                width: '100%',
                closeOnSelect: false,
                allowClear: true,
                minimumResultsForSearch: Infinity,
                selectionCssClass: 'select2-selection--clean',
                dropdownCssClass: 'select2-dropdown--clean',
                templateResult: formatLeagueOptionWithLogo,
                templateSelection: formatLeagueSelectionWithLogo,
                dropdownParent: $('body')
            });

            // --- FIX: Re-apply .has-selections class ---
            const $container = $(this).next('.select2-container').find('.select2-selection--multiple');
            if ($(this).val() && $(this).val().length > 0) {
                $container.addClass('has-selections');
                $('#preferredLeaguesContainer').addClass('has-selections');
            } else {
                $container.removeClass('has-selections');
                $('#preferredLeaguesContainer').removeClass('has-selections');
            }

            warningElement.classList.remove('show');
        }

        updateSelectionClasses($(this), $('#preferredLeaguesContainer'));
    });

    // Remove the old mustTeams selection limit code since we now have individual selects
    // The individual selects automatically limit to 4 teams (one per dropdown)
}