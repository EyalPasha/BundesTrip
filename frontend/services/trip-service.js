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
    
    // Validate form before submission
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
            max_travel_time: parseInt(window.DOM.maxTravelTimeInput.value), // Fix: was DOMlets
            preferred_leagues: selectedLeagues.length > 0 ? selectedLeagues : null,
            must_teams: selectedTeams.length > 0 ? selectedTeams : []
        };

        // Ensure the date has a year (note: this is a fallback in case the flatpickr change doesn't work)
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
        showSuccessToast(`Found ${tripCount} trip option${tripCount !== 1 ? 's' : ''}!`);
        
    } catch (error) {
        console.error("Error in handleSearch:", error);
        showErrorToast(`Error planning trip: ${error.message}`);
        window.DOM.noResultsMessage.classList.remove('d-none');
    } finally {
        // Hide loading
        window.DOM.loadingIndicator.classList.add('d-none');
    }
}

export { handleSearch };