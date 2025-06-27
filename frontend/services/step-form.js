// Multi-step form logic
let currentStep = 1;
const totalSteps = 3;

// Initialize step form
function initStepForm() {
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
    
    // Update navigation buttons
    const nextBtn = document.getElementById('nextStep');
    const prevBtn = document.getElementById('prevStep');
    const submitBtn = document.getElementById('submitForm');
    
    // Previous button
    if (currentStep === 1) {
        prevBtn.classList.add('hidden-step-button');
        prevBtn.style.visibility = 'hidden';
    } else {
        prevBtn.classList.remove('hidden-step-button');
        prevBtn.style.visibility = 'visible';
    }
    
    // Next/Submit button
    if (currentStep === totalSteps) {
        nextBtn.style.display = 'none';
        nextBtn.classList.add('d-none');
        submitBtn.style.display = 'flex';
        submitBtn.classList.remove('d-none');
    } else {
        nextBtn.style.display = 'flex';
        nextBtn.classList.remove('d-none');
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
        
        if (!startLocation || !startDate || !tripDuration) {
            // Add shake animation or highlight missing fields
            return false;
        }
    }
    
    if (currentStep === 2) {
        const maxTravelTime = document.getElementById('maxTravelTime').value;
        if (!maxTravelTime) {
            return false;
        }
    }
    
    return true;
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
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        initStepForm();
    }, 500); // Allow other initialization to complete first
});