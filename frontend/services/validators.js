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