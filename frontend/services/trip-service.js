import { validateForm } from './validators.js';
import { planTrip, cancelTripRequest, API_BASE_URL } from './api.js';
import { renderResults } from '../components/results-display.js';
import { renderTripCard } from '../components/trip-card.js';

// Make renderTripCard globally available for API service
window.renderTripCard = renderTripCard;

// Store the current request ID globally
window.currentRequestId = null;

// Wait for both auth service and user to be ready
async function waitForAuthentication() {
    return new Promise((resolve, reject) => {
        const checkAuth = async () => {
            try {
                if (window.authService && window.authService.initialized) {
                    const user = await window.authService.getCurrentUser();
                    if (user && window.authService.getAuthToken()) {
                        // console.log('✅ Authentication ready for API calls');
                        resolve(user);
                    } else {
                        // console.log('⏳ Waiting for user authentication...');
                        setTimeout(checkAuth, 200);
                    }
                } else {
                    // console.log('⏳ Waiting for auth service...');
                    setTimeout(checkAuth, 200);
                }
            } catch (error) {
                console.error('Auth check error:', error);
                reject(error);
            }
        };
        
        checkAuth();
        
        // Timeout after 10 seconds
        setTimeout(() => {
            reject(new Error('Authentication timeout - please refresh and try again'));
        }, 10000);
    });
}

// Updated handleSearch function with authentication
async function handleSearch(e) {
    e.preventDefault();
    if (!validateForm()) {
        return;
    }
    
    // console.log('🔍 Starting trip search...');
    
    try {
        // STEP 1: Check authentication first
        // console.log('🔐 Checking authentication...');
        await waitForAuthentication();
        // console.log('✅ User authenticated, proceeding with search');
        
        // Reset loading UI to visible state
        resetLoadingUI(true);
        
        // Clean up any previous search state
        document.body.classList.remove('has-filter-drawer');
        
        // IMPORTANT: Reset loading animation elements
        const loadingAnimation = document.getElementById('loadingAnimation');
        const loadingMessages = document.getElementById('loadingMessages');
        const cancelSearchButton = document.getElementById('cancelSearch');
        const noResultsMessage = document.getElementById('noResultsMessage');
        
        if (loadingAnimation) loadingAnimation.classList.remove('d-none');
        if (loadingMessages) loadingMessages.classList.remove('d-none'); 
        if (cancelSearchButton) cancelSearchButton.classList.remove('d-none');
        if (noResultsMessage) noResultsMessage.classList.add('d-none');
        
        // Reset filter button visibility
        const filterButton = document.querySelector('.filter-button');
        if (filterButton) {
            filterButton.style.display = 'none';
        }
        
        // Declare variables at the top level so they're accessible in all blocks
        let searchCancelled = false;
        let response = null;
        let error = null;
        let noResultsShown = false;
        
        // STEP 2: GET A REQUEST ID FIRST - with authentication
        let requestId = null;
        try {
            // console.log('🎫 Getting authenticated request ID...');
            requestId = await window.apiService.getRequestId();
            window.currentRequestId = requestId;
            // console.log("Got request ID:", requestId);
            
            if (!requestId) {
                throw new Error('Failed to get request ID - please try again');
            }
        } catch (error) {
            console.error("Failed to get request ID:", error);
            
            // Handle authentication errors specifically
            if (error.message.includes('Authentication failed')) {
                setTimeout(() => {
                    window.location.href = './login.html';
                }, 2000);
            }
            return;
        }
        
        // STEP 3: SET UP CANCEL BUTTON WITH THE ID
        const cancelButton = document.getElementById('cancelSearch');
        if (cancelButton) {
            // Reset existing event listeners
            const newCancelButton = cancelButton.cloneNode(true);
            cancelButton.parentNode.replaceChild(newCancelButton, cancelButton);
            
            newCancelButton.addEventListener('click', async function() {
                // Set button to canceling state
                this.disabled = true;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Canceling...';
                
                searchCancelled = true;
                
                try {
                    // Cancel request using authenticated API service
                    await window.apiService.cancelTrip(requestId);
                    // console.log(`Search cancelled for request ${requestId}`);
                } catch (err) {
                    console.error("Error cancelling search:", err);
                } finally {
                    // Reset search state and return to form
                    resetLoadingUI(false);
                    window.returnToSearch();
                }
            });
        }
        
        // STEP 4: SHOW UI, HIDE PREVIOUS RESULTS
        // Hide results container while searching
        const resultsContainer = document.getElementById('resultsContainer');
        if (resultsContainer) {
            resultsContainer.classList.add('d-none');
        }
        
        // Clear previous results
        const tripResults = document.getElementById('tripResults');
        if (tripResults) {
            tripResults.innerHTML = '';
        }

        // Hide filters container AND filter card during search
        const filtersContainer = document.getElementById('filtersContainer');
        if (filtersContainer) {
            filtersContainer.classList.add('d-none');
        }
        
        // Hide the entire filter results card
        const filterResultsCard = document.getElementById('filterResultsCard');
        if (filterResultsCard) {
            filterResultsCard.classList.add('d-none');
        }
        
        // Remove any existing filter drawer
        const existingFilterBtn = document.querySelector('.filter-btn');
        const existingFilterDrawer = document.querySelector('.filter-drawer');
        const existingOverlay = document.querySelector('.drawer-overlay');
        
        if (existingFilterBtn) existingFilterBtn.remove();
        if (existingFilterDrawer) existingFilterDrawer.remove();
        if (existingOverlay) existingOverlay.remove();
        
        // Reset the module-level references to filter elements
        try {
            const filtersModule = await import('../services/filters.js');
            if (filtersModule && typeof filtersModule.resetFilterDrawerReferences === 'function') {
                filtersModule.resetFilterDrawerReferences();
            }
        } catch (err) {
            console.warn('Could not reset filter drawer references:', err);
        }
        
        // IMPORTANT: Reset the active filters GLOBALLY to prevent persistence between searches
        if (window.activeFilters) {
            window.activeFilters.team = null;
            window.activeFilters.city = null;
            window.activeFilters.minGames = 1;
            window.activeFilters.maxHotelChanges = 7;
        } else {
            // Create activeFilters if it doesn't exist
            window.activeFilters = {
                team: null,
                city: null,
                minGames: 1,
                maxHotelChanges: 7
            };
        }
        
        // Also reset the original filter state in the filters.js module
        try {
            const filtersModule = await import('../services/filters.js');
            if (filtersModule && typeof filtersModule.resetFilters === 'function') {
                filtersModule.resetFilters();
            }
        } catch (err) {
            console.warn('Could not reset filters module state:', err);
        }

        // Hide trip options header
        const tripOptionsHeader = document.getElementById('tripOptionsHeader');
        if (tripOptionsHeader) {
            tripOptionsHeader.classList.add('d-none');
        }
        
        // Hide results count container
        const resultsCountContainer = document.getElementById('resultsCountContainer');
        if (resultsCountContainer) {
            resultsCountContainer.classList.add('d-none');
        }

        // Show loading state and prevent page scrolling
        window.DOM.loadingIndicator = document.getElementById('loading');
        window.DOM.loadingIndicator.classList.remove('d-none');
        document.body.classList.add('no-scroll'); // Prevent scrolling
        window.DOM.resultsSection.classList.remove('d-none');

        // Fix the null reference error by adding a null check
        if (window.DOM.noResultsMessage) {
            window.DOM.noResultsMessage.classList.add('d-none');
        }
        
        // STEP 5: BUILD PAYLOAD WITH THE REQUEST ID
        try {
            // Use Select2's API to get selected values
            const selectedLeagues = $(window.DOM.preferredLeaguesSelect).val() || [];
            
            // NEW: Get teams from individual selects instead of multi-select
            const selectedTeams = getSelectedTeams(); // Use the new function from script.js
            
            const payload = {
                start_location: window.DOM.startLocationSelect.value,
                start_date: window.DOM.startDateInput.value || null,
                trip_duration: parseInt(window.DOM.tripDurationInput.value),
                max_travel_time: parseInt(window.DOM.maxTravelTimeInput.value),
                preferred_leagues: selectedLeagues.length > 0 ? selectedLeagues : null,
                must_teams: selectedTeams.length > 0 ? selectedTeams : [], // Updated to use new function
                min_games: parseInt(window.DOM.minGamesInput.value || "2"),
                request_id: requestId
            };
            
            // Ensure the date has a year
            if (payload.start_date && !payload.start_date.includes("2025") && !payload.start_date.includes("2026")) {
                // Add current year if missing
                const currentYear = new Date().getFullYear();
                payload.start_date = `${payload.start_date} ${currentYear}`;
            }
            
            // console.log('📝 Trip payload prepared:', payload);
            
            // STORE SEARCH REQUEST FOR TRIP SAVING
            if (window.tripSaver) {
                window.tripSaver.storeSearchRequest(payload);
                // console.log('🔄 Stored search request for saving:', payload);
            }

            // STEP 6: MAKE THE AUTHENTICATED REQUEST
            // console.log(`🚀 Planning trip with authenticated request ID: ${requestId}`);
            response = await window.apiService.planTrip(payload);
            
            // STEP 7: PROCESS RESPONSE
            // Show results container if we got results
            if (resultsContainer && response && response.trip_groups && response.trip_groups.length > 0) {
                resultsContainer.classList.remove('d-none');
            }
            
            // Show filter card only if we have results
            if (response && response.trip_groups && response.trip_groups.length > 0) {
                if (filterResultsCard) {
                    filterResultsCard.classList.remove('d-none');
                }
                
                // Show trip options header
                if (tripOptionsHeader) {
                    tripOptionsHeader.classList.remove('d-none');
                }
                
                // Show results count container
                if (resultsCountContainer) {
                    resultsCountContainer.classList.remove('d-none');
                }
                
                // Update results count
                const resultsCount = document.getElementById('resultsCount');
                if (resultsCount) {
                    resultsCount.textContent = response.trip_groups.length;
                }
            } else {
                // Show the no results message within the loading container
                const loadingAnimation = document.getElementById('loadingAnimation');
                const loadingMessages = document.getElementById('loadingMessages');
                const cancelButton = document.getElementById('cancelSearch');
                const noResultsMessage = document.getElementById('noResultsMessage');
                
                if (loadingAnimation) loadingAnimation.classList.add('d-none');
                if (loadingMessages) loadingMessages.classList.add('d-none');
                if (cancelButton) cancelButton.classList.add('d-none');
                if (noResultsMessage) noResultsMessage.classList.remove('d-none');
                
                // Keep the loading overlay visible to show the no results message
                // Skip hiding the loading indicator in the finally block
                noResultsShown = true;
            }
            
            // Render the results
            renderResults(response, false);
            
        } catch (err) {
            // Store the caught error in our variable
            error = err;
            
            if (!searchCancelled) {
                console.error("Error in handleSearch:", error);
                
                // Handle authentication errors specifically
                if (error.message.includes('Authentication failed')) {
                    setTimeout(() => {
                        window.location.href = './login.html';
                    }, 2000);
                    return;
                }
                
                // Display no results message
                if (window.DOM.noResultsMessage) {
                    window.DOM.noResultsMessage.classList.remove('d-none');
                    
                    // Scroll to no results message with delay to ensure it's rendered
                    setTimeout(() => {
                        // Calculate the centered position considering the viewport height
                        const viewHeight = window.innerHeight;
                        const noResultsHeight = window.DOM.noResultsMessage.offsetHeight;
                        const topOffset = Math.max(50, (viewHeight - noResultsHeight) / 2);
                        
                        window.scrollTo({
                            top: window.DOM.noResultsMessage.offsetTop - topOffset,
                            behavior: 'smooth'
                        });
                    }, 200);
                }
            }
        } finally {
            // Now these variables are all in scope
            const shouldHideLoading = searchCancelled || 
                (response && response.trip_groups && response.trip_groups.length > 0) ||
                (error && error.message !== "No trips found matching your criteria");
            
            if (shouldHideLoading) {
                // Hide loading and restore scrolling
                window.DOM.loadingIndicator.classList.add('d-none');
                document.body.classList.remove('no-scroll');
            }
            // Only clear the request ID if we're done or had an error
            const shouldClearRequest = !window.DOM.loadingIndicator.classList.contains('d-none') || error;
            if (shouldClearRequest) {
                window.currentRequestId = null;
            }
            // Otherwise, keep the loading indicator visible with the "No Results" message
        }
        
    } catch (authError) {
        console.error('Authentication error:', authError);
        
        // Handle authentication timeout or failure
        let errorMessage = 'Authentication required to plan trips.';
        
        if (authError.message.includes('timeout')) {
            errorMessage = 'Authentication timeout. Please refresh the page and try again.';
        } else if (authError.message.includes('Authentication failed')) {
            errorMessage = 'Please log in again to plan your trip.';
        }
        
        // Redirect to login after a delay
        setTimeout(() => {
            window.location.href = './login.html';
        }, 2000);
        
        // Reset UI state
        resetLoadingUI(false);
        document.body.classList.remove('no-scroll');
    }
}

// Listen for Enter key on form inputs to submit the form
function setupFormSubmitOnEnter() {
    const formInputs = document.querySelectorAll('.search-form input, .search-form select');
    formInputs.forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.querySelector('#searchButton').click();
            }
        });
    });
}

// Initialize form event handlers
function initFormHandlers() {
    // Add event listener to clear validation errors when fields change
    window.DOM.startLocationSelect.addEventListener('change', function() {
        this.classList.remove('is-invalid');
    });
    
    // Add event listener to update minGames options when tripDuration changes
    window.DOM.tripDurationInput.addEventListener('change', function() {
        updateMinGamesOptions();
    });
    
    // Setup other form interactions
    setupFormSubmitOnEnter();

    // Bind the trip duration change event
    document.getElementById('tripDuration')?.addEventListener('change', updateMinGamesOptions);
    
    // Call once to initialize
    updateMinGamesOptions();
}

// Update the updateMinGamesOptions function in trip-service.js
function updateMinGamesOptions() {
    const tripDurationSelect = document.getElementById('tripDuration');
    const minGamesSelect = document.getElementById('minGames');
    
    if (!tripDurationSelect || !minGamesSelect) {
        console.warn('Trip duration or min games select not found');
        return;
    }
    
    // Get the current trip duration value
    const duration = parseInt(tripDurationSelect.value);
    
    // Store current selection if it exists
    const currentSelection = minGamesSelect.value;
    
    // Temporarily destroy Select2 if it exists
    if ($(minGamesSelect).data('select2')) {
        $(minGamesSelect).select2('destroy');
    }
    
    // Clear existing options
    minGamesSelect.innerHTML = '';
    
    // Special case: If duration is exactly 2 days
    if (duration === 2) {
        // Only allow exactly 2 games (not a range)
        const option = document.createElement('option');
        option.value = 2;
        option.textContent = '2 Games';
        minGamesSelect.appendChild(option);
        
        // Automatically set to 2
        minGamesSelect.value = '2';
    } else {
        // Normal case: Calculate max games (duration - 1)
        const maxGames = duration - 1;
        
        // Add options from 2 to maxGames
        for (let i = 2; i <= maxGames; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = `${i} ${i === 1 ? 'Game' : 'Games'}`;
            minGamesSelect.appendChild(option);
        }
        
        // Try to restore previous selection if valid
        if (currentSelection && parseInt(currentSelection) <= maxGames && parseInt(currentSelection) >= 2) {
            minGamesSelect.value = currentSelection;
        } else {
            // Default to the first option (2 games)
            minGamesSelect.value = '2';
        }
    }
    
    // Re-initialize Select2
    $(minGamesSelect).select2({
        width: '100%',
        minimumResultsForSearch: Infinity,
        selectionCssClass: 'select2-selection--clean',
        dropdownCssClass: 'select2-dropdown--clean'
    });
    
}

// Call once on page load to set initial options
document.addEventListener('DOMContentLoaded', function() {
    if (window.DOM && window.DOM.tripDurationInput) {
        updateMinGamesOptions();
    }
});

// Add this function at the end of your file
function resetLoadingUI(show = false) {
    const loadingContainer = document.getElementById('loading');
    const loadingAnimation = document.getElementById('loadingAnimation');
    const loadingMessages = document.getElementById('loadingMessages');
    const cancelSearchButton = document.getElementById('cancelSearch');
    const noResultsMessage = document.getElementById('noResultsMessage');
    
    if (show) {
        // Show loading UI
        if (loadingContainer) loadingContainer.classList.remove('d-none');
        if (loadingAnimation) loadingAnimation.classList.remove('d-none');
        if (loadingMessages) loadingMessages.classList.remove('d-none');
        
        // Reset and show cancel button
        if (cancelSearchButton) {
            cancelSearchButton.classList.remove('d-none');
            cancelSearchButton.disabled = false;
            cancelSearchButton.innerHTML = '<i class="fas fa-times-circle"></i> Cancel Search';
        }
        
        if (noResultsMessage) noResultsMessage.classList.add('d-none');
    } else {
        // Hide loading UI
        if (loadingContainer) loadingContainer.classList.add('d-none');
        // Don't hide the child elements, just the container
    }
}

// Export the new function
export { handleSearch, initFormHandlers, updateMinGamesOptions, resetLoadingUI };