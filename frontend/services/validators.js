import { showErrorToast } from './notifications.js';

function validateForm() {
    let isValid = true;
    const errors = [];
    
    // Start location validation
    if (!window.DOM.startLocationSelect.value) {
        isValid = false;
        errors.push("Please select a start location");
        window.DOM.startLocationSelect.classList.add('is-invalid');
    } else {
        window.DOM.startLocationSelect.classList.remove('is-invalid');
    }
    
    // For Select2 fields, we need special handling
    if (!$('#startLocation').val()) {
        $('#startLocation').next('.select2-container').addClass('is-invalid-select2');
        isValid = false;
    } else {
        $('#startLocation').next('.select2-container').removeClass('is-invalid-select2');
    }
    
    // Start date validation (new required field)
    if (!window.DOM.startDateInput.value) {
        isValid = false;
        errors.push("Please select a start date");
        window.DOM.startDateInput.classList.add('is-invalid');
    } else {
        window.DOM.startDateInput.classList.remove('is-invalid');
    }
    
    // Trip duration validation
    const duration = parseInt(window.DOM.tripDurationInput.value);
    if (isNaN(duration) || duration < 1 || duration > 10) {
        isValid = false;
        errors.push("Trip duration must be between 1 and 10 days");
        window.DOM.tripDurationInput.classList.add('is-invalid');
    } else {
        window.DOM.tripDurationInput.classList.remove('is-invalid');
    }
    
    // Max travel time validation
    const maxTravel = parseInt(window.DOM.maxTravelTimeInput.value);
    if (isNaN(maxTravel) || maxTravel < 30 || maxTravel > 420) {
        isValid = false;
        errors.push("Maximum travel time must be between 30 and 420 minutes");
        window.DOM.maxTravelTimeInput.classList.add('is-invalid');
    } else {
        window.DOM.maxTravelTimeInput.classList.remove('is-invalid');
    }
    
    // Validate min games
    const minGames = parseInt(window.DOM.minGamesInput.value);
    const tripDuration = parseInt(window.DOM.tripDurationInput.value);
    
    if (isNaN(minGames) || minGames < 1) {
        isValid = false;
        errors.push("Minimum games must be at least 1");
        window.DOM.minGamesInput.classList.add('is-invalid');
    } else if (minGames > tripDuration) {
        isValid = false;
        errors.push("Minimum games cannot exceed trip duration");
        window.DOM.minGamesInput.classList.add('is-invalid');
    } else {
        window.DOM.minGamesInput.classList.remove('is-invalid');
    }
        
    // Show validation errors if any
    if (!isValid) {
        showValidationErrors(errors);
    }
    
    return isValid;
}

function showValidationErrors(errors) {
    let errorHtml = '<ul class="mb-0 ps-3">';
    errors.forEach(error => {
        errorHtml += `<li>${error}</li>`;
    });
    errorHtml += '</ul>';
    
    showErrorToast(`Please correct the following issues: ${errorHtml}`);
}

export { validateForm, showValidationErrors };