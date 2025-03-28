import { handleSearch } from '../services/trip-service.js';
import { loadCities, loadLeagues, loadTeams } from '../services/data-loader.js'; // ADD THIS LINE

// Initialize search form
function initSearchForm() {
    console.log("Initializing search form...");
    // Load data for dropdowns immediately
    Promise.all([
        loadCities(),
        loadLeagues(),
        loadTeams()
    ]);
    
    // Add event listener once DOM is definitely available
    const waitForDOM = setInterval(() => {
        if (window.DOM && window.DOM.tripSearchForm) {
            clearInterval(waitForDOM);
            console.log("Adding submit event listener to search form");
            window.DOM.tripSearchForm.addEventListener('submit', handleSearch);
        }
    }, 100);
}

export { initSearchForm };