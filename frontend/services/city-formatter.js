/**
 * Formats city names for display by taking only the first word
 * @param {string} cityName - The full city name from backend
 * @returns {string} - The formatted city name for display
 */
function formatCityForDisplay(cityName) {
    if (!cityName || typeof cityName !== 'string') return '';
    
    // Take only the first word, removing prefixes like "hbf", "bahnhof", "westf", etc.
    return cityName.split(' ')[0];
}

/**
 * Keep the original city name for backend communication
 * @param {string} cityName - The city name as received from backend
 * @returns {string} - The original city name for backend requests
 */
function formatCityForBackend(cityName) {
    // Return exactly as received from backend
    return cityName;
}

// Make functions globally available
window.formatCityForDisplay = formatCityForDisplay;
window.formatCityForBackend = formatCityForBackend;

export { formatCityForDisplay, formatCityForBackend };