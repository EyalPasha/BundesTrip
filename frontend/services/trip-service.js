import { validateForm } from './validators.js';
import { planTrip } from './api.js';
import { showErrorToast, showSuccessToast } from './notifications.js';
import { renderResults } from '../components/results-display.js';
import { renderTripCard } from '../components/trip-card.js';

// Make renderTripCard globally available for API service
window.renderTripCard = renderTripCard;

// Update the handleSearch function in trip-service.js to fix the error
async function handleSearch(e) {
    e.preventDefault();
    if (!validateForm()) {
        return;
    }
    
    // Add a flag to track if we're showing the no results message
    let noResultsShown = false;
    
    // Declare these variables at the top level so they're available in the finally block
    let response = null;
    let error = null;
    
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
    
    // Setup cancel button handler
    let searchCancelled = false;
    const cancelButton = document.getElementById('cancelSearch');
    
    if (cancelButton) {
        // Reset existing event listeners
        const newCancelButton = cancelButton.cloneNode(true);
        cancelButton.parentNode.replaceChild(newCancelButton, cancelButton);
        
        newCancelButton.addEventListener('click', function() {
            searchCancelled = true;
            
            // Hide loading and restore scrolling
            window.DOM.loadingIndicator.classList.add('d-none');
            document.body.classList.remove('no-scroll');
            
            // Clear any previous results
            const tripResults = document.getElementById('tripResults');
            if (tripResults) {
                tripResults.innerHTML = '';
            }
            
            // Hide no results message if it's showing
            if (window.DOM.noResultsMessage) {
                window.DOM.noResultsMessage.classList.add('d-none');
            }
            
            // Show toast notification
            showErrorToast("Search cancelled");
            
            // Reset the search form focus
            if (window.DOM.startLocationSelect) {
                window.DOM.startLocationSelect.focus();
            }
        });
    }
    
    try {
        // Use Select2's API to get selected values
        const selectedLeagues = $(window.DOM.preferredLeaguesSelect).val() || [];
        const selectedTeams = $(window.DOM.mustTeamsSelect).val() || [];
        
        const payload = {
            start_location: window.DOM.startLocationSelect.value,
            start_date: window.DOM.startDateInput.value || null,
            trip_duration: parseInt(window.DOM.tripDurationInput.value),
            max_travel_time: parseInt(window.DOM.maxTravelTimeInput.value),
            preferred_leagues: selectedLeagues.length > 0 ? selectedLeagues : null,
            must_teams: selectedTeams.length > 0 ? selectedTeams : [],
            min_games: parseInt(window.DOM.minGamesInput.value || "2") // Default to 2 if not present
        };
        
        // Ensure the date has a year
        if (payload.start_date && !payload.start_date.includes("2025") && !payload.start_date.includes("2026")) {
            // Add current year if missing
            const currentYear = new Date().getFullYear();
            payload.start_date = `${payload.start_date} ${currentYear}`;
        }
        
        // Check if search was cancelled during API call
        if (searchCancelled) return;
        
        // Call API
        response = await planTrip(payload);
        
        // Check if search was cancelled while waiting for response
        if (searchCancelled) return;
        
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
            noResultsShown = true; // Add this flag to track state
        }
        
        // Render the results
        renderResults(response, false); // Add a parameter to indicate we want to keep the loading overlay if no results

        // Show success message with the count of trip options
        const tripCount = response.trip_groups?.length || 0;
        if (tripCount > 0) {
            showSuccessToast(`Found ${tripCount} trip option${tripCount !== 1 ? 's' : ''}!`);
            
            // Hide loading and show results
            window.DOM.loadingIndicator.classList.add('d-none');
            document.body.classList.remove('no-scroll');
            
            // Scroll directly to results section 
            setTimeout(() => {
                window.DOM.resultsSection.scrollIntoView({ 
                    behavior: "smooth", 
                    block: "start" 
                });
            }, 100);
        }
        
    } catch (err) {
        // Store the caught error in our variable
        error = err;
        
        if (!searchCancelled) {
            console.error("Error in handleSearch:", error);
            
            // Only show error toast for actual errors, not "no results" scenarios
            if (error.message !== "No trips found matching your criteria") {
                showErrorToast(error.message || "Error planning trip");
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
        // Only hide the loading indicator if:
        // 1. The search was cancelled, OR
        // 2. We have results, OR 
        // 3. There was an error (not "no results")
        
        const shouldHideLoading = searchCancelled || 
            (response && response.trip_groups && response.trip_groups.length > 0) ||
            (error && error.message !== "No trips found matching your criteria");
        
        if (shouldHideLoading) {
            // Hide loading and restore scrolling
            window.DOM.loadingIndicator.classList.add('d-none');
            document.body.classList.remove('no-scroll');
        }
        // Otherwise, keep the loading indicator visible with the "No Results" message
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

// Export all functions
export { handleSearch, initFormHandlers, updateMinGamesOptions };