/**
 * Add loading spinner to a component
 * @param {HTMLElement} element - The element to show loading on
 */
function showComponentLoading(element) {
    if (!element) return;
    
    // Remove any existing spinners first
    hideComponentLoading(element);
    
    // Instead of adding a spinner, just apply a subtle loading state
    element.classList.add('is-loading');
    
    // Optional: Add a subtle visual indicator without using a spinner
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'component-loading-state position-absolute end-0 top-50 translate-middle-y me-2';
    loadingIndicator.style.opacity = '0.6';
    
    element.style.position = 'relative';  // Ensure parent is positioned for absolute positioning
    element.appendChild(loadingIndicator);
}

/**
 * Remove loading spinner from a component
 * @param {HTMLElement} element - The element to remove loading from
 */
function hideComponentLoading(element) {
    if (!element) return;
    
    // Remove the loading class
    element.classList.remove('is-loading');
    
    // Remove all loading indicators from the component
    const loadingIndicators = element.querySelectorAll('.component-loading-state');
    loadingIndicators.forEach(indicator => indicator.remove());
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