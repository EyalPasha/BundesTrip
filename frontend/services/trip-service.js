import { validateForm } from './validators.js';
import { planTrip } from './api.js';
import { showErrorToast, showSuccessToast } from './notifications.js';
import { renderResults } from '../components/results-display.js';

async function handleSearch(e) {
    console.log("Form submitted!", e);
    e.preventDefault();
    
    // Validate form before submission
    console.log("Validating form...");
    if (!validateForm()) {
        return;
    }
    
    // Show loading state
    window.DOM.loadingIndicator.classList.remove('d-none');
    window.DOM.resultsSection.classList.remove('d-none');
    window.DOM.tripResults.innerHTML = '';
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
        
        console.log("Sending payload:", payload);
        
        // Call API
        const response = await planTrip(payload);
        console.log("API response received:", response);
        
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