import { getCities, getLeagues, getTeams, getAvailableDates } from './api.js';
import { showErrorToast } from './notifications.js';
import { showComponentLoading, hideComponentLoading } from './ui-helpers.js';

// German teams list - this should match the teams in your backend database
const GERMAN_TEAMS = [
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig", 
    "VfB Stuttgart", "Eintracht Frankfurt", "SC Freiburg", "1. FC Union Berlin", 
    "TSG Hoffenheim", "1. FSV Mainz 05", "VfL Wolfsburg", "Borussia Mönchengladbach", 
    "Werder Bremen", "FC Augsburg", "VfL Bochum", "1. FC Heidenheim", "FC St. Pauli",
    "Holstein Kiel", "1. FC Köln", "SV Darmstadt 98", "Fortuna Düsseldorf", "Hamburger SV",
    "Karlsruher SC", "Hannover 96", "SC Paderborn 07", "SpVgg Greuther Fürth",
    "Hertha BSC", "FC Schalke 04", "SV Elversberg", "1. FC Nürnberg", "1. FC Kaiserslautern",
    "1. FC Magdeburg", "Eintracht Braunschweig", "SSV Ulm 1846", "Preußen Münster",
    "SSV Jahn Regensburg", "Alemannia Aachen", "Arminia Bielefeld", "Borussia Dortmund II",
    "Dynamo Dresden", "Energie Cottbus", "Erzgebirge Aue", "Hannover 96 II", 
    "Hansa Rostock", "FC Ingolstadt 04", "TSV 1860 Munich", "VfL Osnabrück", 
    "Rot-Weiss Essen", "FC Saarbrücken", "SV Sandhausen", "SpVgg Unterhaching", 
    "VfB Stuttgart II", "SC Verl", "Viktoria Köln", "Waldhof Mannheim", "SV Wehen Wiesbaden"
];

// This should match the priority in your backend's league_priority
const LEAGUE_PRIORITY = {
    "bundesliga": 1,
    "2bundesliga": 2,
    "Champions League": 3,
    "DFB-Pokal": 4,
    "3-liga": 5,
    "Europa League": 6,
    "Conference League": 7
};

const LEAGUE_DISPLAY_NAMES = {
    "bundesliga": "Bundesliga",
    "2bundesliga": "2. Bundesliga",
    "Champions League": "UEFA Champions League",
    "DFB-Pokal": "DFB-Pokal (German Cup)",
    "3-liga": "3. Liga",
    "Europa League": "UEFA Europa League",
    "Conference League": "UEFA Conference League"
};

// Update this function in data-loader.js
async function loadCities() {
    try {
        showComponentLoading(window.DOM.startLocationSelect.parentElement);
        const data = await getCities();
        
        // Save the placeholder option
        const placeholderOption = document.createElement('option');
        placeholderOption.value = "";
        placeholderOption.textContent = "Select a city";
        placeholderOption.selected = true;
        placeholderOption.disabled = true;
        
        // Clear existing options
        window.DOM.startLocationSelect.innerHTML = '';
        
        // Add the placeholder option back first
        window.DOM.startLocationSelect.appendChild(placeholderOption);
        
        // Add cities from the backend response
        data.cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.id;
            option.textContent = city.name;
            window.DOM.startLocationSelect.appendChild(option);
        });
        
        // Ensure the placeholder is selected
        window.DOM.startLocationSelect.value = "";
        
    } catch (error) {
        showErrorToast(`Failed to load cities: ${error.message}`);
    } finally {
        hideComponentLoading(window.DOM.startLocationSelect.parentElement);
    }
}

async function loadLeagues() {
    try {
        showComponentLoading(window.DOM.preferredLeaguesSelect.parentElement);
        const data = await getLeagues();
        
        // Clear all existing options
        window.DOM.preferredLeaguesSelect.innerHTML = '';
        
        // Sort leagues by priority before adding to dropdown
        const sortedLeagues = [...data.leagues].sort((a, b) => {
            const priorityA = LEAGUE_PRIORITY[a] || 999; // Default high priority for unknown leagues
            const priorityB = LEAGUE_PRIORITY[b] || 999;
            return priorityA - priorityB; // Sort ascending by priority (1 is highest)
        });
        
        sortedLeagues.forEach(league => {
            const option = document.createElement('option');
            option.value = league; // Keep original value for API interactions
            
            // Use the display name if available, otherwise use the original
            option.textContent = LEAGUE_DISPLAY_NAMES[league] || league;
            
            window.DOM.preferredLeaguesSelect.appendChild(option);
        });
        
        // Initialize Select2 with enhanced styling and templates
        $(window.DOM.preferredLeaguesSelect).select2({
            placeholder: 'Select Leagues',
            width: '100%',
            closeOnSelect: false,
            allowClear: true,
            templateResult: formatLeagueOption,
            templateSelection: formatLeagueSelection,
            dropdownParent: $(window.DOM.preferredLeaguesSelect).parent()
        });
        
        // Force the placeholder to appear
        $(window.DOM.preferredLeaguesSelect).val(null).trigger('change');
        
        // Set up event listener for league changes
        $(window.DOM.preferredLeaguesSelect).on('change', function() {
            updateTeamsByLeague();
        });
        
    } catch (error) {
        showErrorToast(`Failed to load leagues: ${error.message}`);
    } finally {
        hideComponentLoading(window.DOM.preferredLeaguesSelect.parentElement);
    }
}

async function loadTeams() {
    try {
        showComponentLoading(window.DOM.mustTeamsSelect.parentElement);
        const data = await getTeams();
        
        // Clear all existing options
        window.DOM.mustTeamsSelect.innerHTML = '';
        
        // IMPORTANT: Filter to only include German teams
        const germanTeams = data.teams.filter(team => GERMAN_TEAMS.includes(team));
        
        germanTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            window.DOM.mustTeamsSelect.appendChild(option);
        });
        
        // Initialize Select2 with enhanced styling and templates
        $(window.DOM.mustTeamsSelect).select2({
            placeholder: 'Select Teams',
            width: '100%',
            closeOnSelect: false,
            allowClear: true,
            templateResult: formatTeamOption,
            templateSelection: formatTeamSelection,
            dropdownParent: $(window.DOM.mustTeamsSelect).parent()
        });
        
    } catch (error) {
        showErrorToast(`Failed to load teams: ${error.message}`);
    } finally {
        hideComponentLoading(window.DOM.mustTeamsSelect.parentElement);
    }
}

async function updateTeamsByLeague() {
    const selectedLeagues = $(window.DOM.preferredLeaguesSelect).val();
    
    // If no leagues selected, load all (German) teams
    if (!selectedLeagues || selectedLeagues.length === 0) {
        await loadAllTeams();
        return;
    }
    
    // Remember currently selected teams
    const selectedTeams = $(window.DOM.mustTeamsSelect).val() || [];
    
    // Show loading indicator
    showComponentLoading(window.DOM.mustTeamsSelect.parentElement);
    
    try {
        // Call API to get teams for selected leagues
        const results = await Promise.all(selectedLeagues.map(league => getTeams(league)));
        
        // Combine teams from all selected leagues
        const teams = [];
        results.forEach(result => {
            if (result && result.teams) {
                teams.push(...result.teams);
            }
        });
        
        // Deduplicate teams
        const uniqueTeams = [...new Set(teams)];
        
        // FILTER: Only keep German teams
        const germanTeams = uniqueTeams.filter(team => GERMAN_TEAMS.includes(team));
        
        // Update teams dropdown
        window.DOM.mustTeamsSelect.innerHTML = '';
        
        germanTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            window.DOM.mustTeamsSelect.appendChild(option);
        });
        
        // Restore previously selected teams (if they're still valid)
        $(window.DOM.mustTeamsSelect).val(selectedTeams.filter(team => germanTeams.includes(team)));
        $(window.DOM.mustTeamsSelect).trigger('change');
    } catch (error) {
        showErrorToast(`Failed to update teams: ${error.message}`);
    } finally {
        hideComponentLoading(window.DOM.mustTeamsSelect.parentElement);
    }
}

async function loadAllTeams() {
    // Remember currently selected teams
    const selectedTeams = $(window.DOM.mustTeamsSelect).val() || [];
    
    // Show loading indicator
    showComponentLoading(window.DOM.mustTeamsSelect.parentElement);
    
    try {
        // Get all teams
        const result = await getTeams();
        
        if (!result || !result.teams) return;
        
        // FILTER: Only keep German teams - this is the key fix
        const germanTeams = result.teams.filter(team => GERMAN_TEAMS.includes(team));
        
        // Update teams dropdown
        window.DOM.mustTeamsSelect.innerHTML = '';
        
        germanTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            window.DOM.mustTeamsSelect.appendChild(option);
        });
        
        // Restore previously selected teams (if they're still valid)
        $(window.DOM.mustTeamsSelect).val(selectedTeams.filter(team => germanTeams.includes(team)));
        $(window.DOM.mustTeamsSelect).trigger('change');
    } catch (error) {
        showErrorToast(`Failed to load teams: ${error.message}`);
    } finally {
        hideComponentLoading(window.DOM.mustTeamsSelect.parentElement);
    }
}

/**
 * Load available dates with matches for the datepicker
 * @param {Object} params Filter parameters
 * @param {string} [params.league] League filter
 * @param {string} [params.team] Team filter 
 * @returns {Promise<Array>} Array of dates with match info
 */
async function loadAvailableDates(params = {}) {
    try {
        const data = await getAvailableDates(params);
        return data.dates || [];
    } catch (error) {
        console.error('Failed to load available dates:', error);
        return [];
    }
}

// Format options for Select2 dropdowns - clean modern design
function formatLeagueOption(league) {
    if (!league.id) return league.text;
    // Simple clean design with proper text alignment
    return $(`<div class="select-option">${league.text}</div>`);
}

function formatLeagueSelection(league) {
    if (!league.id) return league.text;
    return $(`<span class="selected-item">${league.text}</span>`);
}

function formatTeamOption(team) {
    if (!team.id) return team.text;
    // Simple clean design with proper text alignment
    return $(`<div class="select-option">${team.text}</div>`);
}

function formatTeamSelection(team) {
    if (!team.id) return team.text;
    return $(`<span class="selected-item">${team.text}</span>`);
}

export {
    loadCities,
    loadLeagues,
    loadTeams,
    updateTeamsByLeague,
    loadAvailableDates,
    GERMAN_TEAMS
};