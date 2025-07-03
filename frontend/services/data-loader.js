import { getCities, getLeagues, getTeams, getAvailableDates } from './api.js';
import { showErrorToast } from './notifications.js';
import { showComponentLoading, hideComponentLoading } from './ui-helpers.js';
import { 
    formatTeamOptionWithLogo, 
    formatTeamSelectionWithLogo, 
    getTeamLogoUrl,
    getLeagueLogoUrl
} from './team-logos.js';
import { formatCityForDisplay, formatCityForBackend } from './city-formatter.js';
import { initMustTeamsSelect, initPreferredLeaguesSelect } from './select2-init.js';

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
    "VfB Stuttgart II", "SC Verl", "Viktoria Köln", "Waldhof Mannheim", "SV Wehen Wiesbaden", 
    "TSG Hoffenheim II", "MSV Duisburg", "TSV Havelse", "1. FC Schweinfurt 05"
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
    "Champions League": "Champions League",
    "DFB-Pokal": "DFB-Pokal",
    "3-liga": "3. Liga",
    "Europa League": "Europa League",
    "Conference League": "Conference League"
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
            option.value = city.id; // Keep original ID for backend
            option.textContent = formatCityForDisplay(city.name); // Display only first word
            option.dataset.originalName = city.name; // Store original name for backend
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
            const priorityA = LEAGUE_PRIORITY[a] || 999;
            const priorityB = LEAGUE_PRIORITY[b] || 999;
            return priorityA - priorityB;
        });
        
        sortedLeagues.forEach(league => {
            const option = document.createElement('option');
            option.value = league;
            option.textContent = LEAGUE_DISPLAY_NAMES[league] || league;
            option.dataset.league = league;
            window.DOM.preferredLeaguesSelect.appendChild(option);
        });
        
        // Force the placeholder to appear
        $(window.DOM.preferredLeaguesSelect).val(null).trigger('change');
        
        // Set up event listener for league changes - but only if team selects exist
        $(window.DOM.preferredLeaguesSelect).on('change', function() {
            // Check if any individual team selects exist before calling updateTeamsByLeague
            const teamSelectsExist = ['mustTeam1', 'mustTeam2', 'mustTeam3', 'mustTeam4']
                .some(id => document.getElementById(id));
                
            if (teamSelectsExist) {
                updateTeamsByLeague();
            }
        });
        
    } catch (error) {
        showErrorToast(`Failed to load leagues: ${error.message}`);
    } finally {
        hideComponentLoading(window.DOM.preferredLeaguesSelect.parentElement);
    }
}

async function loadTeams() {
    try {
        const data = await getTeams();
        
        // IMPORTANT: Filter to only include German teams
        const germanTeams = data.teams.filter(team => GERMAN_TEAMS.includes(team));
        
        // Return the teams data for use by individual team selects
        return germanTeams.map(team => ({
            id: team,
            name: team
        }));
        
    } catch (error) {
        showErrorToast(`Failed to load teams: ${error.message}`);
        return []; // Return empty array on error
    }
}

async function updateTeamsByLeague() {
    const selectedLeagues = $(window.DOM.preferredLeaguesSelect).val();
    
    // If no leagues selected, load all (German) teams
    if (!selectedLeagues || selectedLeagues.length === 0) {
        await loadAllTeams();
        return;
    }
    
    // Get all individual team selects
    const teamSelects = ['mustTeam1', 'mustTeam2', 'mustTeam3', 'mustTeam4'];
    const currentSelections = {};
    
    // Remember currently selected teams
    teamSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            currentSelections[selectId] = select.value;
        }
    });
    
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
        
        // Update all individual team dropdowns
        teamSelects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                // Clear existing options except placeholder
                const placeholder = select.querySelector('option[value=""]');
                select.innerHTML = '';
                
                // Re-add placeholder if it existed
                if (placeholder) {
                    select.appendChild(placeholder);
                }
                
                // Add teams
                germanTeams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team;
                    option.textContent = team;
                    option.dataset.team = team;
                    select.appendChild(option);
                });
                
                // Restore previous selection if still valid
                if (currentSelections[selectId] && germanTeams.includes(currentSelections[selectId])) {
                    select.value = currentSelections[selectId];
                }
                
                // Trigger Select2 update if initialized
                if ($(select).hasClass('select2-hidden-accessible')) {
                    $(select).trigger('change');
                }
            }
        });
        
    } catch (error) {
        showErrorToast(`Failed to update teams: ${error.message}`);
    }
}

// Update the loadAllTeams function
async function loadAllTeams() {
    // Get all individual team selects
    const teamSelects = ['mustTeam1', 'mustTeam2', 'mustTeam3', 'mustTeam4'];
    const currentSelections = {};
    
    // Remember currently selected teams
    teamSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            currentSelections[selectId] = select.value;
        }
    });
    
    try {
        // Get all teams
        const result = await getTeams();
        
        if (!result || !result.teams) return;
        
        // FILTER: Only keep German teams
        const germanTeams = result.teams.filter(team => GERMAN_TEAMS.includes(team));
        
        // Update all individual team dropdowns
        teamSelects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                // Clear existing options except placeholder
                const placeholder = select.querySelector('option[value=""]');
                select.innerHTML = '';
                
                // Re-add placeholder if it existed
                if (placeholder) {
                    select.appendChild(placeholder);
                }
                
                // Add teams
                germanTeams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team;
                    option.textContent = team;
                    option.dataset.team = team;
                    select.appendChild(option);
                });
                
                // Restore previous selection if still valid
                if (currentSelections[selectId] && germanTeams.includes(currentSelections[selectId])) {
                    select.value = currentSelections[selectId];
                }
                
                // Trigger Select2 update if initialized
                if ($(select).hasClass('select2-hidden-accessible')) {
                    $(select).trigger('change');
                }
            }
        });
        
    } catch (error) {
        showErrorToast(`Failed to load teams: ${error.message}`);
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
        // No longer passing "days" parameter
        const data = await getAvailableDates({
            league: params.league,
            team: params.team
        });
        return data.dates || [];
    } catch (error) {
        console.error('Failed to load available dates:', error);
        return [];
    }
}

export {
    loadCities,
    loadLeagues,
    loadTeams,
    updateTeamsByLeague,
    loadAvailableDates,
    GERMAN_TEAMS
};