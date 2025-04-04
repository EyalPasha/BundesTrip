import { GERMAN_TEAMS } from './data-loader.js';

// Map team names to their logo filenames
const TEAM_LOGO_MAPPING = {
    "Bayern Munich": "München.png", //
    "Borussia Dortmund": "Dortmund.webp", //
    "Bayer Leverkusen": "Leverkusen.png",//
    "RB Leipzig": "Leipzig.png",//
    "VfB Stuttgart": "Stuttgart.png", //
    "Eintracht Frankfurt": "Frankfurt.png",//
    "SC Freiburg": "Freiburg.png",//
    "1. FC Union Berlin": "UnionBerlin.png", //
    "TSG Hoffenheim": "Hoffenheim.png",//
    "1. FSV Mainz 05": "Mainz.png",//
    "VfL Wolfsburg": "Wolfsburg.png", //
    "Borussia Mönchengladbach": "Mönchengladbach.png",//
    "Werder Bremen": "Bremen.webp",//
    "FC Augsburg": "Augsburg.png",//
    "VfL Bochum": "Bochum.png",//
    "1. FC Heidenheim": "Heidenheim.png",//
    "FC St. Pauli": "Pauli.png", //
    "Holstein Kiel": "Kiel.png",//
    "1. FC Köln": "Koln.png",//
    "SV Darmstadt 98": "Darmstadt.png",//
    "Fortuna Düsseldorf": "Düsseldorf.png",//
    "Hamburger SV": "Hamburger.png",//
    "Karlsruher SC": "Karlsruher.png",//
    "Hannover 96": "Hannover.png",//
    "SC Paderborn 07": "Paderborn.png", //
    "SpVgg Greuther Fürth": "Fürth.png",//
    "Hertha BSC": "Hertha.png",//
    "FC Schalke 04": "Schalke.webp", // 
    "SV Elversberg": "Elversberg.png",//
    "1. FC Nürnberg": "Nürnberg.png",//
    "1. FC Kaiserslautern": "Kaiserslautern.png",//
    "1. FC Magdeburg": "Magdeburg.png",//
    "Eintracht Braunschweig": "Braunschweig.png",//
    "SSV Ulm 1846": "Ulm.png", // 
    "Preußen Münster": "Münster.png",//
    "SSV Jahn Regensburg": "Regensburg.png", //
    "Alemannia Aachen": "Aachen.png",//
    "Arminia Bielefeld": "Bielefeld.png",//
    "Borussia Dortmund II": "Dortmund.webp", //
    "Dynamo Dresden": "Dresden.png",//
    "Energie Cottbus": "Cottbus.png",//
    "Erzgebirge Aue": "Aue.png",//
    "Hannover 96 II": "Hannover.png", //
    "Hansa Rostock": "Rostock.png", // 
    "FC Ingolstadt 04": "Ingolstadt.png",//
    "TSV 1860 Munich": "1860_München.png",//
    "VfL Osnabrück": "Osnabrueck.png",//
    "Rot-Weiss Essen": "Essen.png",//
    "FC Saarbrücken": "Saarbrucken.png", //
    "SV Sandhausen": "Sandhausen.png", //
    "SpVgg Unterhaching": "Unterhaching.png", //
    "VfB Stuttgart II": "Stuttgart.png", //
    "SC Verl": "Verl.png", //
    "Viktoria Köln": "Viktoria_Köln.png", //
    "Waldhof Mannheim": "Mannheim.png",//
    "SV Wehen Wiesbaden": "Wiesbaden.png" //
};

// League logo mapping
const LEAGUE_LOGO_MAPPING = {
    "3-liga": "3liga.webp",
    "2bundesliga": "b2.png",
    "bundesliga": "b1.png", // Note: using same logo as 2bundesliga per instructions
    "Champions League": "cl.png",
    "Conference League": "col.png",
    "Europa League": "el.png",
    "DFB-Pokal": "dfb.png"
};

// Base path for logo files
const LOGO_BASE_PATH = '../logos/';
const DEFAULT_LOGO = 'soccer-1.png'; // Fallback logo

/**
 * Get logo URL for a team
 * @param {string} teamName The full team name
 * @returns {string} URL to the team's logo
 */
function getTeamLogoUrl(teamName) {
    const logoFile = TEAM_LOGO_MAPPING[teamName];
    if (!logoFile) {
        console.warn(`No logo found for team: ${teamName}`);
        return `${LOGO_BASE_PATH}${DEFAULT_LOGO}`;
    }
    return `${LOGO_BASE_PATH}${logoFile}`;
}

/**
 * Get logo URL for a league
 * @param {string} leagueName The league name
 * @returns {string} URL to the league's logo
 */
function getLeagueLogoUrl(leagueName) {
    // If leagueName is actually an object with an id property (from Select2)
    if (leagueName && typeof leagueName === 'object' && leagueName.id) {
        leagueName = leagueName.id;
    }
    
    const logoFile = LEAGUE_LOGO_MAPPING[leagueName];
    if (!logoFile) {
        console.warn(`No logo found for league: ${leagueName}`);
        return `${LOGO_BASE_PATH}${DEFAULT_LOGO}`;
    }
    return `${LOGO_BASE_PATH}${logoFile}`;
}
/**
 * Create an image element for a team logo with standardized sizing
 * @param {string} teamName The full team name
 * @param {Object} options Optional configuration
 * @param {number} options.width Width in pixels (default: 32)
 * @param {number} options.height Height in pixels (default: 32)
 * @param {string} options.className Additional CSS classes
 * @returns {HTMLImageElement} Image element
 */
function createTeamLogoElement(teamName, options = {}) {
    const url = getTeamLogoUrl(teamName);
    
    const img = document.createElement('img');
    img.src = url;
    img.alt = `${teamName} logo`;
    img.width = options.width || 32;
    img.height = options.height || 32;
    
    if (options.className) {
        img.className = options.className;
    }
    
    img.classList.add('team-logo');
    return img;
}

/**
 * Format function for Select2 to display team logos in dropdowns
 * @param {Object} team Select2 option object
 * @returns {jQuery|string} Formatted option with logo
 */
function formatTeamOptionWithLogo(team) {
    if (!team.id) return team.text; // Skip placeholder
    
    const logoUrl = getTeamLogoUrl(team.id);
    
    return $(
        `<div class="select-option team-option">
            <img src="${logoUrl}" class="team-logo" alt="${team.text} logo" />
            <span>${team.text}</span>
        </div>`
    );
}

/**
 * Format function for Select2 to display league logos in dropdowns
 * @param {Object} league Select2 option object
 * @returns {jQuery|string} Formatted option with logo
 */
function formatLeagueOptionWithLogo(league) {
    if (!league.id) return league.text; // Skip placeholder
    
    const logoUrl = getLeagueLogoUrl(league.id);
    
    // Fix this check to use the correct default logo
    if (logoUrl.includes(DEFAULT_LOGO)) {
        console.warn(`No logo found for league: ${league.id}`);
    }
    
    return $(
        `<div class="select-option league-option">
            <img src="${logoUrl}" class="league-logo" alt="${league.text} logo" />
            <span>${league.text}</span>
        </div>`
    );
}

/**
 * Format function for Select2 to display team logos in selected items
 * @param {Object} team Select2 option object
 * @returns {jQuery|string} Formatted selection with logo
 */
function formatTeamSelectionWithLogo(team) {
    if (!team.id) return team.text; // Skip placeholder
    
    const logoUrl = getTeamLogoUrl(team.id);
    
    return $(
        `<span class="selected-item team-selection">
            <img src="${logoUrl}" class="team-logo-small" alt="${team.text} logo" />
            <span>${team.text}</span>
        </span>`
    );
}

/**
 * Format function for Select2 to display league logos in selected items
 * @param {Object} league Select2 option object
 * @returns {jQuery|string} Formatted selection with logo
 */
function formatLeagueSelectionWithLogo(league) {
    if (!league.id) return league.text; // Skip placeholder
    
    const logoUrl = getLeagueLogoUrl(league.id);
    
    return $(
        `<span class="selected-item league-selection">
            <img src="${logoUrl}" class="league-logo-small" alt="${league.text} logo" />
            <span>${league.text}</span>
        </span>`
    );
}

/**
 * Apply team logo CSS styles to the document
 */
function applyTeamLogoStyles() {
    if (document.getElementById('team-logo-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'team-logo-styles';
    styleEl.textContent = `
        .team-logo, .league-logo {
            width: 32px;
            height: 32px;
            object-fit: contain;
            background-color: transparent;
            vertical-align: middle;
            margin-right: 8px;
        }
        
        .team-logo-small, .league-logo-small {
            width: 20px;
            height: 20px;
            object-fit: contain;
            background-color: transparent;
            vertical-align: middle;
            margin-right: 5px;
        }
        
        .team-option, .league-option {
            display: flex;
            align-items: center;
        }
        
        .team-selection, .league-selection {
            display: inline-flex;
            align-items: center;
        }
    `;
    
    document.head.appendChild(styleEl);
}

// Cache logo images to ensure they're loaded before displayed
function preloadLogos() {
    // Preload team logos
    Object.values(TEAM_LOGO_MAPPING).forEach(logoFile => {
        const img = new Image();
        img.src = `${LOGO_BASE_PATH}${logoFile}`;
    });
    
    // Preload league logos
    Object.values(LEAGUE_LOGO_MAPPING).forEach(logoFile => {
        const img = new Image();
        img.src = `${LOGO_BASE_PATH}${logoFile}`;
    });
}

export {
    getTeamLogoUrl,
    createTeamLogoElement,
    formatTeamOptionWithLogo,
    formatTeamSelectionWithLogo,
    getLeagueLogoUrl, 
    formatLeagueOptionWithLogo,
    formatLeagueSelectionWithLogo,
    applyTeamLogoStyles,
    preloadLogos, // Renamed from preloadTeamLogos
    TEAM_LOGO_MAPPING,
    LEAGUE_LOGO_MAPPING
};