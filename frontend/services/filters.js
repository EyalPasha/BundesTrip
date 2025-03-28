import { clearFilters } from './ui-helpers.js';

function filterByTeam(team) {
    const tripCards = document.querySelectorAll('.trip-card');
    
    tripCards.forEach(card => {
        const cardTeams = card.dataset.teams.split(',');
        if (cardTeams.includes(team)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
    
    // Update active filter
    document.querySelectorAll('#teamFilters .badge').forEach(badge => {
        if (badge.dataset.team === team) {
            badge.classList.remove('bg-light');
            badge.classList.remove('text-dark');
            badge.classList.add('bg-primary');
            badge.classList.add('text-white');
        } else if (badge.dataset.team) {
            badge.classList.add('bg-light');
            badge.classList.add('text-dark');
            badge.classList.remove('bg-primary');
            badge.classList.remove('text-white');
        }
    });
}

function filterByCity(city) {
    const tripCards = document.querySelectorAll('.trip-card');
    
    tripCards.forEach(card => {
        const cardCities = card.dataset.cities.split(',');
        if (cardCities.includes(city)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
    
    // Update active filter
    document.querySelectorAll('#cityFilters .badge').forEach(badge => {
        if (badge.dataset.city === city) {
            badge.classList.remove('bg-light');
            badge.classList.remove('text-dark');
            badge.classList.add('bg-primary');
            badge.classList.add('text-white');
        } else if (badge.dataset.city) {
            badge.classList.add('bg-light');
            badge.classList.add('text-dark');
            badge.classList.remove('bg-primary');
            badge.classList.remove('text-white');
        }
    });
}

// Updated renderFilters function to work with trip_groups
function renderFilters(tripGroups) {
    // Extract unique teams and cities from trip groups
    const uniqueTeams = new Set();
    const uniqueCities = new Set();
    
    tripGroups.forEach(group => {
        if (group.variation_details && group.variation_details.length > 0) {
            group.variation_details.forEach(variation => {
                // Extract teams
                if (variation.teams && Array.isArray(variation.teams)) {
                    variation.teams.forEach(team => uniqueTeams.add(team));
                }
                
                // Extract cities
                if (variation.cities && Array.isArray(variation.cities)) {
                    variation.cities.forEach(city => uniqueCities.add(city));
                }
            });
        }
    });
    
    // Sort teams and cities alphabetically
    const teams = [...uniqueTeams].sort();
    const cities = [...uniqueCities].sort();
    
    // Get DOM elements
    const teamFiltersContainer = window.DOM.teamFiltersContainer;
    const cityFiltersContainer = window.DOM.cityFiltersContainer;
    
    // Clear existing filters
    teamFiltersContainer.innerHTML = '';
    cityFiltersContainer.innerHTML = '';
    
    // Team filters
    teams.forEach(team => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-light text-dark border m-1';
        badge.textContent = team;
        badge.dataset.team = team;
        badge.onclick = () => filterByTeam(team);
        badge.style.cursor = 'pointer';
        teamFiltersContainer.appendChild(badge);
    });
    
    // City filters
    cities.forEach(city => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-light text-dark border m-1';
        badge.textContent = city.replace(' hbf', '');
        badge.dataset.city = city;
        badge.onclick = () => filterByCity(city);
        badge.style.cursor = 'pointer';
        cityFiltersContainer.appendChild(badge);
    });
    
    // Add clear filters option
    if (teams.length > 0) {
        const clearTeamFilters = document.createElement('span');
        clearTeamFilters.className = 'badge bg-secondary text-white ms-2';
        clearTeamFilters.innerHTML = '<i class="fas fa-times"></i> Clear';
        clearTeamFilters.onclick = clearFilters;
        clearTeamFilters.style.cursor = 'pointer';
        teamFiltersContainer.appendChild(clearTeamFilters);
    }
    
    if (cities.length > 0) {
        const clearCityFilters = document.createElement('span');
        clearCityFilters.className = 'badge bg-secondary text-white ms-2';
        clearCityFilters.innerHTML = '<i class="fas fa-times"></i> Clear';
        clearCityFilters.onclick = clearFilters;
        clearCityFilters.style.cursor = 'pointer';
        cityFiltersContainer.appendChild(clearCityFilters);
    }
}

export {
    filterByTeam,
    filterByCity,
    renderFilters
};