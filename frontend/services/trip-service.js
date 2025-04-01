import { validateForm } from './validators.js';
import { planTrip } from './api.js';
import { showErrorToast, showSuccessToast } from './notifications.js';
import { renderResults } from '../components/results-display.js';
import { renderTripCard } from '../components/trip-card.js';

// Make renderTripCard globally available for API service
window.renderTripCard = renderTripCard;

async function handleSearch(e) {
    console.log("Form submitted!", e);
    e.preventDefault();
    
    // Check mandatory fields first (faster than full validation)
    if (!window.DOM.startLocationSelect.value) {
        showErrorToast("Starting location is required");
        window.DOM.startLocationSelect.classList.add('is-invalid');
        return;
    }
    
    if (!window.DOM.startDateInput.value) {
        showErrorToast("Start date is required");
        window.DOM.startDateInput.classList.add('is-invalid');
        return;
    }
    
    // Full form validation
    console.log("Validating form...");
    if (!validateForm()) {
        return;
    }
    
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
    
    // Show loading state
    window.DOM.loadingIndicator.classList.remove('d-none');
    window.DOM.resultsSection.classList.remove('d-none');
    window.DOM.noResultsMessage.classList.add('d-none');
    
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
        
        console.log("Sending payload:", payload);
        
        // Call API
        const response = await planTrip(payload);
        console.log("API response received:", response);
        
        // Show results container if we got results
        if (resultsContainer && response && response.trip_groups && response.trip_groups.length > 0) {
            resultsContainer.classList.remove('d-none');
        }
        
        // Render the results
        renderResults(response);
        
        // Show success message with the count of trip options
        const tripCount = response.trip_groups?.length || 0;
        if (tripCount > 0) {
            showSuccessToast(`Found ${tripCount} trip option${tripCount !== 1 ? 's' : ''}!`);
        } else {
            showErrorToast("No trips found matching your criteria");
            window.DOM.noResultsMessage.classList.remove('d-none');
        }
        
    } catch (error) {
        console.error("Error in handleSearch:", error);
        showErrorToast(`Error planning trip: ${error.message}`);
        window.DOM.noResultsMessage.classList.remove('d-none');
    } finally {
        // Hide loading
        window.DOM.loadingIndicator.classList.add('d-none');
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
}

// Function to update minGames dropdown options based on tripDuration
function updateMinGamesOptions() {
    const tripDuration = parseInt(window.DOM.tripDurationInput.value);
    const minGamesSelect = window.DOM.minGamesInput;
    const currentValue = parseInt(minGamesSelect.value);
    
    // Clear existing options
    minGamesSelect.innerHTML = '';
    
    // Add new options based on trip duration
    for (let i = 1; i <= Math.min(tripDuration, 10); i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = i === 1 ? '1 Game' : `${i} Games`; // Capitalize "Games"
        minGamesSelect.appendChild(option);
    }
    
    // Restore previous value if possible, otherwise set to 2 or max available
    if (currentValue <= tripDuration) {
        minGamesSelect.value = currentValue;
    } else {
        minGamesSelect.value = Math.min(2, tripDuration);
    }
}

// Call once on page load to set initial options
document.addEventListener('DOMContentLoaded', function() {
    if (window.DOM && window.DOM.tripDurationInput) {
        updateMinGamesOptions();
    }
});

// Export all functions
export { handleSearch, initFormHandlers, updateMinGamesOptions };