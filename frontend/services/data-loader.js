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

const TEAM_TICKET_LINKS = {
  // Bundesliga
  "Bayern Munich": "https://tickets.fcbayern.com",
  "Borussia Dortmund": "https://www.ticket-onlineshop.com/ols/bvb/de/home/",
  "Bayer Leverkusen": "https://www.bayer04.de/en-us/shop/tickets",
  "RB Leipzig": "https://rbleipzig.com/en/tickets/",
  "VfB Stuttgart": "https://tickets.vfb.de/shop/103",
  "Eintracht Frankfurt": "https://stores.eintracht.de/tickets/",
  "SC Freiburg": "https://www.scfreiburg.com/tickets/",
  "1. FC Union Berlin": "https://tickets.union-zeughaus.de",
  "TSG Hoffenheim": "https://tickets.tsg-hoffenheim.de",
  "1. FSV Mainz 05": "https://www.ticket-onlineshop.com/ols/mainz05/en/dauerkarte",
  "VfL Wolfsburg": "https://www.vfl-wolfsburg.de/onlineshop-geschlossen",
  "Borussia Mönchengladbach": "https://www.ticket-onlineshop.com/ols/borussia-tickets/",
  "Werder Bremen": "https://www.werder.de/tickets/heimspiele/",
  "FC Augsburg": "https://www.fcaugsburg.de/en/page/tickets-15",
  "1. FC Heidenheim": "https://www.fc-heidenheim.de/tickets-overview",
  "FC St. Pauli": "https://www.ticket-onlineshop.com/ols/fcstpauli/de",
  "1. FC Köln": "https://fc.de/en/fc-tickets/",
  "Hamburger SV": "https://www.ticket-onlineshop.com/ols/hsv/",

  // 2. Bundesliga
  "Arminia Bielefeld": "https://shop.arminia.de/arminia-bielefeld/eintrittskarten.htm",
  "VfL Bochum": "https://www.ticket-onlineshop.com/ols/vflbochum1848/",
  "Holstein Kiel": "https://www.ticket-onlineshop.com/ols/holstein-kiel/",
  "SV Darmstadt 98": "https://tickets.sv98.de/",
  "Fortuna Düsseldorf": "https://tickets.f95.de",
  "Karlsruher SC": "https://tickets.ksc.de",
  "Hannover 96": "https://www.ticket-onlineshop.com/ols/h96/",
  "SC Paderborn 07": "https://www.ticket-onlineshop.com/ols/scp07/",
  "SpVgg Greuther Fürth": "https://shop.sgf1903.de/sgf1903/SynwayWarengruppen/data/shop/cf9dd53c-5f1c-4f63-915b-992c5d4c2e32",
  "Hertha BSC": "https://www.herthabsc.com/en/tickets/matchday-tickets",
  "FC Schalke 04": "https://tickets.schalke04.de",
  "SV Elversberg": "https://www.ticket-onlineshop.com/ols/sv07elversberg/de",
  "1. FC Nürnberg": "https://www.fcn.de/tickets/",
  "1. FC Kaiserslautern": "https://shop.fck.de/tickets/",
  "1. FC Magdeburg": "https://1fcm.de/tickets/",
  "Eintracht Braunschweig": "https://www.ticket-onlineshop.com/ols/eintracht-braunschweig/",
  "Preußen Münster": "https://www.ticket-onlineshop.com/ols/scpreussen/",
  "Dynamo Dresden": "https://www.dynamo-dresden.de/fans/ticketinfos/tickets/",

  // 3. Liga
  "SSV Ulm 1846": "https://www.ssv-ticketshop.de/",
  "SSV Jahn Regensburg": "https://www.ssv-jahnshop.de/ssv-jahn/tageskarten_2.htm",
  "Alemannia Aachen": "https://www.alemannia-aachen.de/tivoli/tickets/",
  "Energie Cottbus": "https://tickets.egocentric.systems/tickets.asp?o=9026&page=subscription",
  "Erzgebirge Aue": "https://tickets.fc-erzgebirge.de",
  "Hansa Rostock": "https://tickets.fc-hansa.de",
  "FC Ingolstadt 04": "https://tickets.fcingolstadt.de/shop?wes=102ab5e4110&shopid=110&nextstate=2&lpShortcutId=27",
  "TSV 1860 Munich": "https://www.tsv1860-ticketing.de/tsv1860/",
  "VfL Osnabrück": "https://www.ticket-onlineshop.com/ols/vflosnabrueck/",
  "Rot-Weiss Essen": "https://www.rot-weiss-essen.de/fans/eintrittskarten/tickets-termine-news/",
  "FC Saarbrücken": "https://fc-saarbruecken.reservix.de/",
  "VfB Stuttgart II": "https://tickets.vfb.de/shop/103",
  "SC Verl": "https://www.ticket-onlineshop.com/ols/sportclub-verl/de",
  "Viktoria Köln": "https://www.viktoria1904.de/tickets",
  "Waldhof Mannheim": "https://tickets.svw07.de",
  "SV Wehen Wiesbaden": "https://svww.de/tickets",
  "TSG Hoffenheim II": "https://tickets.tsg-hoffenheim.de",
  "MSV Duisburg": "https://www.msv-duisburg.de/aktuelles/tickets/",
  "TSV Havelse": "https://shop.snapticket.de/seller/tsv-havelse-acfe",
  "1. FC Schweinfurt 05": "https://tickets-fcschweinfurt1905.reservix.de/",

  // Other
  "Borussia Dortmund II": "https://www.ticket-onlineshop.com/ols/bvb/de/home/",
  "Hannover 96 II": "https://www.ticket-onlineshop.com/ols/h96/",
  "SV Sandhausen": "https://tickets.svs1916.de",
  "SpVgg Unterhaching": "https://tickets.snec.de/shops/176"
};


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

const LEAGUE_NAME_MAP = {
    "Bundesliga": "bundesliga",
    "2. Bundesliga": "2bundesliga",
    "3. Liga": "3-liga",
    "DFB-Pokal": "dfb-pokal",
    "Champions League": "champions league",
    "Europa League": "europa league",
    "Conference League": "conference league",
    "European Cups": "european cups" // If you use this in your backend
};

const AIRPORT_CITIES = [
    "München",
    "Berlin", 
    "Frankfurt",
    "Düsseldorf",
    "Stuttgart",
    "Karlsruhe"
];

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

        // Find which airport cities are present in the fetched data
        const fetchedCityNames = data.cities.map(city => city.name);
        const allAirportsPresent = AIRPORT_CITIES.every(ac => fetchedCityNames.includes(ac));

        let airportCities = [];
        let otherCities = [];

        if (allAirportsPresent) {
            // Ensure order matches AIRPORT_CITIES
            airportCities = AIRPORT_CITIES.map(ac => data.cities.find(city => city.name === ac));
            otherCities = data.cities.filter(city => !AIRPORT_CITIES.includes(city.name));
        } else {
            // If not all airports present, just show all cities as usual
            otherCities = data.cities;
        }

        // Add airport cities group if all present
        if (airportCities.length > 0 && airportCities.every(Boolean)) {
            const airportGroup = document.createElement('optgroup');
            airportGroup.label = "International Airports";
            airportCities.forEach(city => {
                const option = document.createElement('option');
                option.value = city.id;
                // Show "Karlsruhe (Baden-Baden)" as placeholder, but keep original name for backend
                if (city.name === "Karlsruhe") {
                    option.textContent = "Karlsruhe (Baden-Baden)";
                } else {
                    option.textContent = formatCityForDisplay(city.name);
                }
                option.dataset.originalName = city.name;
                airportGroup.appendChild(option);
            });
            window.DOM.startLocationSelect.appendChild(airportGroup);
        }

        // Add the rest of the cities
        if (otherCities.length > 0) {
            const otherGroup = document.createElement('optgroup');
            otherGroup.label = "Other Cities";
            otherCities.forEach(city => {
                const option = document.createElement('option');
                option.value = city.id;
                if (city.name === "Any") {
                    option.textContent = "Any Start Location";
                } else {
                    option.textContent = formatCityForDisplay(city.name);
                }
                option.dataset.originalName = city.name;
                otherGroup.appendChild(option);
            });
            window.DOM.startLocationSelect.appendChild(otherGroup);
        }

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
        
        // Set up event listener for league changes - now always load all teams
        $(window.DOM.preferredLeaguesSelect).on('change', function() {
            loadAllTeams();
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

// Remove the updateTeamsByLeague logic and just call loadAllTeams
async function updateTeamsByLeague() {
    await loadAllTeams();
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
    GERMAN_TEAMS,
    TEAM_TICKET_LINKS,
    LEAGUE_NAME_MAP
};