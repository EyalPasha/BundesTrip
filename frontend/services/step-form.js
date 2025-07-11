// Multi-step form logic
let currentStep = 1;
const totalSteps = 3;

// Initialize step form
function initStepForm() {
    // Set initial step class immediately
    const stepNavigation = document.querySelector('.step-navigation');
    if (stepNavigation) {
        stepNavigation.className = `step-navigation step-${currentStep}`;
    }
    
    updateStepVisibility();
    setupStepNavigation();
    setupMinGamesLogic();
}

function setupStepNavigation() {
    const nextBtn = document.getElementById('nextStep');
    const prevBtn = document.getElementById('prevStep');
    const submitBtn = document.getElementById('submitForm');

    nextBtn?.addEventListener('click', nextStep);
    prevBtn?.addEventListener('click', prevStep);

    // Fix: Remove error when a city is selected (works for both native and Select2)
    const startLocation = document.getElementById('startLocation');
    if (startLocation) {
        // For native select
        startLocation.addEventListener('change', function() {
            if (this.value) {
                this.classList.remove('is-invalid');
                const errorMsg = this.parentNode.querySelector('.invalid-feedback');
                if (errorMsg) errorMsg.remove();
            }
        });
        // For Select2 (if used)
        $(startLocation).on('select2:select', function() {
            if (this.value) {
                this.classList.remove('is-invalid');
                const errorMsg = this.parentNode.querySelector('.invalid-feedback');
                if (errorMsg) errorMsg.remove();
            }
        });
    }

    document.getElementById('startDate')?.addEventListener('change', function() {
        this.classList.remove('is-invalid');
        const errorMsg = this.parentNode.querySelector('.invalid-feedback');
        if (errorMsg) errorMsg.remove();
    });

    document.getElementById('maxTravelTime')?.addEventListener('change', function() {
        this.classList.remove('is-invalid');
        const errorMsg = this.parentNode.querySelector('.invalid-feedback');
        if (errorMsg) errorMsg.remove();
    });
}
function nextStep() {
    if (currentStep < totalSteps && validateCurrentStep()) {
        currentStep++;
        updateStepVisibility();
        updateStepProgress();
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateStepVisibility();
        updateStepProgress();
    }
}

function updateStepVisibility() {
    // Hide all panels
    document.querySelectorAll('.step-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Show current panel
    const currentPanel = document.querySelector(`.step-panel[data-step="${currentStep}"]`);
    if (currentPanel) {
        currentPanel.classList.add('active');
    }
    
    // Update navigation container class
    const stepNavigation = document.querySelector('.step-navigation');
    stepNavigation.className = `step-navigation step-${currentStep}`;
    
    // Update navigation buttons
    const nextBtn = document.getElementById('nextStep');
    const prevBtn = document.getElementById('prevStep');
    const submitBtn = document.getElementById('submitForm');
    
    // Previous button - hide completely on step 1
    if (currentStep === 1) {
        prevBtn.classList.add('hidden-step-button');
    } else {
        prevBtn.classList.remove('hidden-step-button');
    }
    
    // Next/Submit button - swap between them but maintain same position
    if (currentStep === totalSteps) {
        // Hide next button
        nextBtn.style.display = 'none';
        nextBtn.classList.add('d-none');
        // Show submit button in same position
        submitBtn.style.display = 'flex';
        submitBtn.classList.remove('d-none');
    } else {
        // Show next button
        nextBtn.style.display = 'flex';
        nextBtn.classList.remove('d-none');
        // Hide submit button
        submitBtn.style.display = 'none';
        submitBtn.classList.add('d-none');
    }
}

function updateStepProgress() {
    document.querySelectorAll('.step-indicator').forEach((indicator, index) => {
        const stepNum = index + 1;
        
        indicator.classList.remove('active', 'completed');
        
        if (stepNum < currentStep) {
            indicator.classList.add('completed');
        } else if (stepNum === currentStep) {
            indicator.classList.add('active');
        }
    });
    
    // Update connectors
    document.querySelectorAll('.step-connector').forEach((connector, index) => {
        const stepNum = index + 1;
        
        if (stepNum < currentStep) {
            connector.classList.add('completed');
        } else {
            connector.classList.remove('completed');
        }
    });
}

function validateCurrentStep() {
    if (currentStep === 1) {
        const startLocation = document.getElementById('startLocation').value;
        const startDate = document.getElementById('startDate').value;
        const tripDuration = document.getElementById('tripDuration').value;
        
        // Clear ALL previous validation states and error messages first
        document.getElementById('startLocation').classList.remove('is-invalid');
        document.getElementById('startDate').classList.remove('is-invalid');
        
        // Remove any existing error messages
        const existingErrors = document.querySelectorAll('.invalid-feedback');
        existingErrors.forEach(error => error.remove());
        
        let isValid = true;
        
        // Check each field individually and mark only invalid ones
        if (!startLocation) {
            document.getElementById('startLocation').classList.add('is-invalid');
            showFieldError('startLocation', 'Please select a starting city');
            isValid = false;
        }
        
        if (!startDate) {
            document.getElementById('startDate').classList.add('is-invalid');
            showFieldError('startDate', 'Please select a start date');
            isValid = false;
        }
        
        if (!isValid) {
            // Add shake animation to the form
            const currentPanel = document.querySelector(`.step-panel[data-step="${currentStep}"]`);
            if (currentPanel) {
                currentPanel.classList.add('shake-animation');
                setTimeout(() => {
                    currentPanel.classList.remove('shake-animation');
                }, 500);
            }
        }
        
        return isValid;
    }
    
    if (currentStep === 2) {
        const maxTravelTime = document.getElementById('maxTravelTime').value;
        
        // Clear previous validation state and error messages
        document.getElementById('maxTravelTime').classList.remove('is-invalid');
        const existingErrors = document.querySelectorAll('.invalid-feedback');
        existingErrors.forEach(error => error.remove());
        
        if (!maxTravelTime) {
            document.getElementById('maxTravelTime').classList.add('is-invalid');
            showFieldError('maxTravelTime', 'Please select maximum travel time');
            return false;
        }
    }
    
    return true;
}

function showFieldError(fieldId, message) {
    // Remove existing error message
    const existingError = document.querySelector(`#${fieldId} + .invalid-feedback`);
    if (existingError) {
        existingError.remove();
    }
    
    // Create error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    // Insert after the field
    const field = document.getElementById(fieldId);
    if (field) {
        // For Select2 elements, insert after the container
        const select2Container = field.nextElementSibling;
        if (select2Container && select2Container.classList.contains('select2-container')) {
            select2Container.parentNode.insertBefore(errorDiv, select2Container.nextSibling);
        } else {
            field.parentNode.insertBefore(errorDiv, field.nextSibling);
        }
    }
}

function setupMinGamesLogic() {
    const tripDurationSelect = document.getElementById('tripDuration');
    const minGamesSelect = document.getElementById('minGames');
    
    function updateMinGames() {
        const duration = parseInt(tripDurationSelect.value);
        let minGames = Math.max(2, duration - 1);
        
        // Special case: 2 days = 2 games minimum
        if (duration === 2) {
            minGames = 2;
        }
        
        // Clear existing options
        minGamesSelect.innerHTML = '';
        
        // Add options from minimum to duration
        for (let i = minGames; i <= Math.min(duration, 5); i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = `${i} Games`;
            if (i === minGames) option.selected = true;
            minGamesSelect.appendChild(option);
        }
        
        // Trigger Select2 update if initialized
        if ($(minGamesSelect).hasClass('select2-hidden-accessible')) {
            $(minGamesSelect).trigger('change');
        }
    }
    
    tripDurationSelect?.addEventListener('change', updateMinGames);
    
    // Initialize on load
    updateMinGames();
}

// Call this after your existing initialization
document.addEventListener('DOMContentLoaded', async function() {
    // Initialize immediately, don't wait
    initStepForm();

    // Set step subtitles based on login status
    let loggedIn = false;
    if (window.authService && typeof window.authService.getCurrentUser === 'function') {
        try {
            const user = await window.authService.getCurrentUser();
            loggedIn = !!user;
        } catch (e) {
            loggedIn = false;
        }
    }

    const subtitles = [
        { id: 'stepSubtitle1', loggedIn: 'Start your journey', loggedOut: 'You must <a href="login.html" class="text-primary" style="text-decoration:underline;cursor:pointer;">log in</a> or <a href="register.html" class="text-primary" style="text-decoration:underline;cursor:pointer;">sign up</a> to search trips!' },
        { id: 'stepSubtitle2', loggedIn: 'How many games and travel time', loggedOut: 'You must <a href="login.html" class="text-primary" style="text-decoration:underline;cursor:pointer;">log in</a> or <a href="register.html" class="text-primary" style="text-decoration:underline;cursor:pointer;">sign up</a> to search trips!' },
        { id: 'stepSubtitle3', loggedIn: 'Leagues and teams (optional)', loggedOut: 'You must <a href="login.html" class="text-primary" style="text-decoration:underline;cursor:pointer;">log in</a> or <a href="register.html" class="text-primary" style="text-decoration:underline;cursor:pointer;">sign up</a> to search trips!' }
    ];

    subtitles.forEach(sub => {
        const el = document.getElementById(sub.id);
        if (el) {
            if (loggedIn) {
                el.textContent = sub.loggedIn;
            } else {
                el.innerHTML = sub.loggedOut;
            }
        }
    });
});