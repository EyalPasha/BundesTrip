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

function renderFilters(teams, cities) {
    // Get DOM elements
    const teamFiltersContainer = window.DOM.teamFiltersContainer;
    const cityFiltersContainer = window.DOM.cityFiltersContainer;
    
    // Clear existing filters
    teamFiltersContainer.innerHTML = '';
    cityFiltersContainer.innerHTML = '';
    
    // Team filters
    teams.forEach(team => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-light text-dark border';
        badge.textContent = team;
        badge.dataset.team = team;
        badge.onclick = () => filterByTeam(team);
        teamFiltersContainer.appendChild(badge);
    });
    
    // City filters
    cities.forEach(city => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-light text-dark border';
        badge.textContent = city.replace(' hbf', '');
        badge.dataset.city = city;
        badge.onclick = () => filterByCity(city);
        cityFiltersContainer.appendChild(badge);
    });
    
    // Add clear filters option
    const clearTeamFilters = document.createElement('span');
    clearTeamFilters.className = 'badge bg-secondary text-white ms-2';
    clearTeamFilters.innerHTML = '<i class="fas fa-times"></i> Clear';
    clearTeamFilters.onclick = clearFilters;
    teamFiltersContainer.appendChild(clearTeamFilters);
    
    const clearCityFilters = document.createElement('span');
    clearCityFilters.className = 'badge bg-secondary text-white ms-2';
    clearCityFilters.innerHTML = '<i class="fas fa-times"></i> Clear';
    clearCityFilters.onclick = clearFilters;
    cityFiltersContainer.appendChild(clearCityFilters);
}

export {
    filterByTeam,
    filterByCity,
    renderFilters
};