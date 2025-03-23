/**
 * Add loading spinner to a component
 * @param {HTMLElement} element - The element to show loading on
 */
function showComponentLoading(element) {
    if (!element) return;
    
    // Remove any existing spinners first
    hideComponentLoading(element);
    
    // Add a loading spinner to the component
    const spinner = document.createElement('div');
    spinner.className = 'component-spinner position-absolute end-0 top-50 translate-middle-y me-2';
    spinner.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    
    element.style.position = 'relative';  // Ensure parent is positioned for absolute positioning
    element.appendChild(spinner);
}

/**
 * Remove loading spinner from a component
 * @param {HTMLElement} element - The element to remove loading from
 */
function hideComponentLoading(element) {
    if (!element) return;
    
    // Remove all loading spinners from the component
    const spinners = element.querySelectorAll('.component-spinner');
    spinners.forEach(spinner => spinner.remove());
}

/**
 * Show list view of trip results
 */
function showListView() {
    window.DOM.tripResults.classList.remove('d-none');
}

/**
 * Clear all applied filters
 */
function clearFilters() {
    // Reset all filters
    const tripCards = document.querySelectorAll('.trip-card');
    tripCards.forEach(card => {
        card.style.display = 'block';
    });
    
    // Reset team filter badges
    document.querySelectorAll('#teamFilters .badge').forEach(badge => {
        if (badge.dataset.team) {
            badge.classList.add('bg-light');
            badge.classList.add('text-dark');
            badge.classList.remove('bg-primary');
            badge.classList.remove('text-white');
        }
    });
    
    // Reset city filter badges
    document.querySelectorAll('#cityFilters .badge').forEach(badge => {
        if (badge.dataset.city) {
            badge.classList.add('bg-light');
            badge.classList.add('text-dark');
            badge.classList.remove('bg-primary');
            badge.classList.remove('text-white');
        }
    });
}

export {
    showComponentLoading,
    hideComponentLoading,
    showListView,
    clearFilters
};