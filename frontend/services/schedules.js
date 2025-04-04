import { applyTeamLogoStyles, preloadLogos, formatTeamOptionWithLogo, formatLeagueOptionWithLogo, getTeamLogoUrl, getLeagueLogoUrl } from './team-logos.js';
import { fetchAllTeams, fetchLeagues } from './schedule-service.js';
import { GERMAN_TEAMS } from './data-loader.js';
import { showErrorToast } from './notifications.js';

// DOM Elements
const DOM = {
    // Filter elements
    leagueFilter: document.getElementById('leagueFilter'),
    teamFilter: document.getElementById('teamFilter'),
    dateFilter: document.getElementById('dateFilter'),
    
    // Container elements
    scheduleLoading: document.getElementById('scheduleLoading'),
    scheduleResults: document.getElementById('scheduleResults'),
    scheduleContent: document.getElementById('scheduleContent'),
    noSchedule: document.getElementById('noSchedule'),
    
    // Filter display
    activeFilters: document.getElementById('activeFilters'),
    filterBadges: document.getElementById('filterBadges'),
    clearFilters: document.getElementById('clearFilters')
};

// Global state
const state = {
    leagues: [],
    teams: [],
    games: [],
    filters: {
        league: 'all',
        team: 'all',
        date: null
    },
};

function initializeFlatpickr() {
    // Initialize the date picker with custom styling
    flatpickr(DOM.dateFilter, {
        dateFormat: "F j, Y",
        altInput: true,
        altFormat: "F j, Y",
        minDate: "today",
        maxDate: new Date().fp_incr(120), // 120 days from now
        onChange: function(selectedDates) {
            if (selectedDates.length > 0) {
                jumpToDate(selectedDates[0]);
            }
        },
        disableMobile: "true",
        locale: {
            firstDayOfWeek: 1 // Start with Monday
        },
        // Add these options for styling
        onReady: function() {
            // Add classes for styling
            document.querySelector('.flatpickr-calendar').classList.add('custom-calendar');
            DOM.dateFilter.classList.add('flatpickr-ready');
            
            // Set CSS variable for primary color
            document.documentElement.style.setProperty('--primary-color', '#043d7c');
            document.documentElement.style.setProperty('--accent-color', '#ff6b00');
        },
        // Customize the date appearance to show game counts
        onDayCreate: function(dObj, dStr, fp, dayElem) {

        }
    });
    
    // Add a class to body after initialization
    setTimeout(() => {
        document.body.classList.add('flatpickr-ready');
    }, 300);
}

// Initialize the page when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // Initialize logos
    applyTeamLogoStyles();
    preloadLogos();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load data first
    await Promise.all([
        loadTeams(),
        loadLeagues()
    ]);
    
    // Remove this line:
    // initializeSelect2();
    
    initializeFlatpickr();
    
    // Load initial games
    loadAllGames();
});

// Load teams into the filter dropdown
async function loadTeams() {
    try {
        // First try to get teams from global state if loaded by main page
        let teams = [];
        if (window.globalTeamsData && window.globalTeamsData.teams) {
            teams = window.globalTeamsData.teams;
        } else {
            teams = await fetchAllTeams();
        }
        
        // Filter to only German teams
        const germanTeams = teams.filter(team => GERMAN_TEAMS.includes(team));
        state.teams = germanTeams;
        
        // Clear and populate the select
        DOM.teamFilter.innerHTML = '<option value="all">All Teams</option>';
        
        // Add team options sorted alphabetically
        germanTeams.sort().forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            DOM.teamFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load teams:', error);
    }
}

// Load leagues into the filter dropdown
async function loadLeagues() {
    try {
        // First try to get leagues from global state if loaded by main page
        let leagues = [];
        if (window.globalLeaguesData && window.globalLeaguesData.leagues) {
            leagues = window.globalLeaguesData.leagues;
        } else {
            leagues = await fetchLeagues();
        }
        
        state.leagues = leagues;
        
        // Clear and populate the select
        DOM.leagueFilter.innerHTML = '<option value="all">All Leagues</option>';
        
        // Add league options
        leagues.forEach(league => {
            const option = document.createElement('option');
            option.value = league;
            option.textContent = getLeagueDisplayName(league);
            DOM.leagueFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load leagues:', error);
    }
}

// Helper function for league display names
function getLeagueDisplayName(league) {
    const displayNames = {
        "bundesliga": "Bundesliga",
        "2bundesliga": "2. Bundesliga",
        "3-liga": "3. Liga",
        "Champions League": "UEFA Champions League",
        "Europa League": "UEFA Europa League",
        "Conference League": "UEFA Conference League",
        "DFB-Pokal": "DFB-Pokal"
    };
    
    return displayNames[league] || league;
}

window.applyScheduleFilters = function(type, value) {
    if (type === 'league') {
        state.filters.league = value;
    } else if (type === 'team') {
        state.filters.team = value; 
    }
    applyFilters();
};

// Set up event listeners
function setupEventListeners() {
    // Clear filters
    DOM.clearFilters.addEventListener('click', clearFilters);
    
    // Remove the view toggle buttons code completely
    
    // Make filters sticky
    const filterBar = document.querySelector('.filter-bar');
    if (filterBar) {
        // Add sticky class to the filter bar
        filterBar.classList.add('sticky-filters');
        
        // Add active filters to sticky zone if present
        const activeFilters = document.getElementById('activeFilters');
        if (activeFilters) {
            activeFilters.classList.add('sticky-active-filters');
        }
        
        console.log('Filters set to sticky mode');
    }
    
    // Add CSS for sticky behavior
    addStickyStyles();
}

// Add sticky styles to the document
// Add sticky styles to the document
function addStickyStyles() {
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        .sticky-filters {
            position: sticky;
            top: 0;
            z-index: 1000;
            background-color: #fff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-top: 0;
            padding-top: 15px;
            padding-bottom: 15px;
            transition: box-shadow 0.3s ease;
        }
        
        .sticky-active-filters {
            position: sticky;
            top: 80px;
            z-index: 999;
            background-color: #fff;
            padding-top: 10px;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        
        /* Center the filter row with equal margins */
        .filter-bar .row {
            justify-content: center;
        }
        
        /* Add equal spacing between filter elements */
        .filter-bar .col-md-4,
        .filter-bar .col-md-3 {
            padding: 0 15px;
        }
        
        @media (max-width: 768px) {
            .sticky-filters {
                padding-top: 10px;
                padding-bottom: 10px;
            }
            
            .sticky-active-filters {
                top: 120px;
            }
            
            /* Adjust spacing for mobile */
            .filter-bar .col-md-4,
            .filter-bar .col-md-3 {
                padding: 0 10px;
                margin-bottom: 10px;
            }
        }
        
        /* Highlight animation for the date jumping */
        .highlight-section {
            animation: highlight-fade 2s ease;
        }
        
        @keyframes highlight-fade {
            0%, 30% { background-color: rgba(13, 110, 253, 0.15); }
            100% { background-color: transparent; }
        }
        
        /* Ensure the schedule content has enough padding to avoid initial overlap */
        #scheduleContent {
            padding-top: 10px;
        }

        /* Highlight animation for the date jumping */
        .highlight-section {
            animation: highlight-fade 2s ease;
        }
        
        @keyframes highlight-fade {
            0%, 30% { background-color: rgba(13, 110, 253, 0.15); }
            100% { background-color: transparent; }
        }
        
        /* Ensure the schedule content has enough padding to avoid initial overlap */
        #scheduleContent {
            padding-top: 10px;
        }
        
        /* Fix the active filters overlap issue */
        .sticky-active-filters {
            top: 100px !important;
            margin-top: 20px;
            padding-top: 15px;
        }
            
    `;
    document.head.appendChild(styleElement);
    
    // Add scroll event listener to close dropdowns when scrolling
    window.addEventListener('scroll', function() {
        // Close flatpickr calendar if open
        const calendar = document.querySelector('.flatpickr-calendar');
        if (calendar && calendar.classList.contains('open')) {
            DOM.dateFilter._flatpickr.close();
        }
        
        // Close league filter dropdown if open
        if (DOM.leagueFilter && DOM.leagueFilter.classList.contains('select2-hidden-accessible')) {
            const leagueDropdown = document.querySelector('.select2-container--open');
            if (leagueDropdown) {
                $(DOM.leagueFilter).select2('close');
            }
        }
        
        // Close team filter dropdown if open
        if (DOM.teamFilter && DOM.teamFilter.classList.contains('select2-hidden-accessible')) {
            const teamDropdown = document.querySelector('.select2-container--open');
            if (teamDropdown) {
                $(DOM.teamFilter).select2('close');
            }
        }
    }, { passive: true });
}

// Load all upcoming games
async function loadAllGames() {
    // Show loading
    DOM.scheduleLoading.classList.remove('d-none');
    DOM.scheduleResults.classList.add('d-none');
    DOM.noSchedule.classList.add('d-none');
    
    try {
        // Remove this line:
        // state.pagination.currentPage = 1;
        
        // Fetch all upcoming games without day limitation
        const response = await fetch(`http://localhost:8000/available-dates`);
        if (!response.ok) {
            throw new Error('Failed to load game schedule');
        }
        
        const data = await response.json();
        
        if (!data.dates || data.dates.length === 0) {
            showNoGames();
            return;
        }
        
        // Store all dates with games
        state.games = data.dates;
        
        // Apply any active filters
        const filteredGames = filterGames(state.games);
        
        // Render games
        renderGames(filteredGames);
        
        // Show results
        DOM.scheduleLoading.classList.add('d-none');
        DOM.scheduleResults.classList.remove('d-none');
        
    } catch (error) {
        console.error('Error loading games:', error);
        showErrorToast(`Error loading game schedule: ${error.message}`);
        showNoGames();
    }
}

// Filter games based on current filter state
function filterGames(games) {
    const { league, team, date } = state.filters;
    
    // Start with all games
    let filteredGames = [...games];
    
    // Apply league filter
    if (league !== 'all') {
        filteredGames = filteredGames.filter(game => 
            game.leagues && game.leagues.includes(league)
        );
    }
    
    // Apply team filter (will require additional API calls)
    if (team !== 'all') {
        // This needs to be implemented with the team schedule API
        // For now, we'll just return games and handle team filtering during rendering
    }
    
    // Apply date filter if set
    if (date) {
        // Format the target date as YYYY-MM-DD for comparison
        const targetDateStr = date.toISOString().split('T')[0];
        filteredGames = filteredGames.filter(game => game.date === targetDateStr);
    }
    
    return filteredGames;
}

// Apply current filters
async function applyFilters() {
    // Update filter state
    state.filters.league = DOM.leagueFilter.value;
    state.filters.team = DOM.teamFilter.value;
    
    // Show active filters if any
    updateActiveFiltersDisplay();
    
    // Remove this line:
    // state.pagination.currentPage = 1;
    
    // Show loading
    DOM.scheduleLoading.classList.remove('d-none');
    DOM.scheduleResults.classList.add('d-none');
    DOM.noSchedule.classList.add('d-none');
    
    try {
        // If team filter is active, use the dedicated team-schedule API
        if (state.filters.team !== 'all') {
            const teamName = state.filters.team;
            console.log(`Fetching schedule for team: ${teamName}`);
            
            // Use dedicated API endpoint for team schedules
            const response = await fetch(`http://localhost:8000/team-schedule/${encodeURIComponent(teamName)}`);
            if (!response.ok) {
                throw new Error(`Failed to load team schedule: ${response.status}`);
            }
            
            const teamData = await response.json();
            console.log('Team schedule data structure:', JSON.stringify(teamData, null, 2));
            
            // Check if we have matches
            if (!teamData.matches || teamData.matches.length === 0) {
                if (!teamData.tbd_matches || teamData.tbd_matches.length === 0) {
                    showNoGames();
                    return;
                }
            }
            
            // Store team data for use in fetchGamesForDate
            window.currentTeamData = teamData;
            
            // Directly display team games instead of relying on dates
            displayTeamGames(teamData);
            
            // Show results
            DOM.scheduleLoading.classList.add('d-none');
            DOM.scheduleResults.classList.remove('d-none');
            
        } else {
            // Clear any stored team data
            window.currentTeamData = null;
            
            // If only league filter is active or no filters active
            // Just apply standard filtering
            let filteredGames = filterGames(state.games);
            
            if (filteredGames.length === 0) {
                showNoGames();
                return;
            }
            
            // Render filtered games
            renderGames(filteredGames);
            
            // Show results
            DOM.scheduleLoading.classList.add('d-none');
            DOM.scheduleResults.classList.remove('d-none');
        }
        
    } catch (error) {
        console.error('Error applying filters:', error);
        showErrorToast(`Error filtering games: ${error.message}`);
        showNoGames();
    }
}

// Update active filters display
function updateActiveFiltersDisplay() {
    const { league, team } = state.filters;
    
    // Clear current badges
    DOM.filterBadges.innerHTML = '';
    
    let hasActiveFilters = false;
    
    // Add league filter badge if active
    if (league !== 'all') {
        const leagueName = getLeagueDisplayName(league);
        addFilterBadge('league', leagueName, league);
        hasActiveFilters = true;
    }
    
    // Add team filter badge if active
    if (team !== 'all') {
        addFilterBadge('team', team, team);
        hasActiveFilters = true;
    }
    
    // Show or hide active filters section
    if (hasActiveFilters) {
        DOM.activeFilters.classList.remove('d-none');
    } else {
        DOM.activeFilters.classList.add('d-none');
    }
}

// Add a filter badge
function addFilterBadge(type, text, value) {
    const badge = document.createElement('span');
    badge.className = 'badge rounded-pill bg-primary d-flex align-items-center';
    badge.innerHTML = `
        ${type === 'league' ? 
            `<img src="${getLeagueLogoUrl(value)}" class="me-1" width="16" height="16" alt="${text}">` : 
            (type === 'team' ? 
                `<img src="${getTeamLogoUrl(value)}" class="me-1" width="16" height="16" alt="${text}">` : 
                '')}
        ${text}
        <button class="btn-close btn-close-white ms-2" data-filter-type="${type}" aria-label="Remove ${type} filter"></button>
    `;
    
    // Add click handler to remove filter
    badge.querySelector('.btn-close').addEventListener('click', () => {
        removeFilter(type);
    });
    
    DOM.filterBadges.appendChild(badge);
}

// Remove a specific filter
function removeFilter(type) {
    if (type === 'league') {
        DOM.leagueFilter.value = 'all';
        $(DOM.leagueFilter).trigger('change');
    } else if (type === 'team') {
        DOM.teamFilter.value = 'all';
        $(DOM.teamFilter).trigger('change');
    }
    
    applyFilters();
}

// Clear all filters
function clearFilters() {
    DOM.leagueFilter.value = 'all';
    DOM.teamFilter.value = 'all';
    $(DOM.leagueFilter).trigger('change');
    $(DOM.teamFilter).trigger('change');
    
    state.filters = {
        league: 'all',
        team: 'all',
        date: null
    };
    
    DOM.activeFilters.classList.add('d-none');
    
    loadAllGames();
}

// Jump to a specific date
// Jump to a specific date in the existing schedule view
function jumpToDate(date) {
    // Create consistent date string format for ID lookup and comparison
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const apiDateStr = `${year}-${month}-${day}`;
    
    console.log(`Jumping to date: ${apiDateStr} - Year: ${year}, Month: ${month}, Day: ${day}`);
    
    // Format date for display
    const formattedDate = date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    // First check if we have this exact date in our schedule
    const dateElement = document.getElementById(`date-${apiDateStr}`);
    
    if (dateElement) {
        console.log(`Found exact match for date: ${apiDateStr}`);
        // We found the exact date - scroll to it
        dateElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Highlight the section temporarily
        dateElement.classList.add('highlight-section');
        setTimeout(() => {
            dateElement.classList.remove('highlight-section');
        }, 2000);
        
        return;
    }
    
    console.log(`No exact match found for ${apiDateStr}, looking for closest date`);
    
    // If we don't have the exact date, find the closest date
    const allDateSections = document.querySelectorAll('.date-section[id^="date-"]');
    if (allDateSections.length === 0) {
        // No dates available, show a message
        showErrorToast(`No scheduled games found near ${formattedDate}`);
        return;
    }
    
    // Get all date sections with their date values
    const dates = [];
    allDateSections.forEach(section => {
        const dateStr = section.id.replace('date-', '');
        
        // Create date parts to avoid timezone issues
        const [dateYear, dateMonth, dateDay] = dateStr.split('-').map(Number);
        
        dates.push({
            element: section,
            date: new Date(dateYear, dateMonth - 1, dateDay),
            dateStr: dateStr,
            // For easier debugging
            dateParts: {
                year: dateYear,
                month: dateMonth,
                day: dateDay
            }
        });
    });
    
    console.log(`Looking for closest date to ${apiDateStr} among ${dates.length} available dates`);
    
    // Find the closest date to our target
    // First try to find dates before or equal to target
    let closest = null;
    let minDiff = Infinity;
    const targetTime = new Date(year, parseInt(month) - 1, parseInt(day)).getTime();
    
    // First priority: find dates before or equal to target
    for (const d of dates) {
        const dTime = d.date.getTime();
        if (dTime <= targetTime) {
            const diff = Math.abs(targetTime - dTime);
            if (diff < minDiff) {
                minDiff = diff;
                closest = d;
            }
        }
    }
    
    // If we couldn't find a previous date, look for the closest future date
    if (!closest) {
        for (const d of dates) {
            const diff = Math.abs(targetTime - d.date.getTime());
            if (diff < minDiff) {
                minDiff = diff;
                closest = d;
            }
        }
    }
    
    if (!closest) {
        showErrorToast(`No scheduled games found near ${formattedDate}`);
        return;
    }
    
    console.log(`Closest date found: ${closest.dateStr} (${closest.dateParts.year}-${closest.dateParts.month}-${closest.dateParts.day})`);
    
    // Scroll to the closest date
    closest.element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Highlight the section
    closest.element.classList.add('highlight-section');
    setTimeout(() => {
        closest.element.classList.remove('highlight-section');
    }, 2000);
    
    // Show a message if it's not the exact date
    if (closest.dateStr !== apiDateStr) {
        const closestFormatted = closest.date.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long', 
            day: 'numeric'
        });
        
        showErrorToast(`No games on ${formattedDate}. Showing closest available date: ${closestFormatted}`);
    }
}

// Render games in the selected view
function renderGames(games) {
    // Always use list view, no condition needed
    renderListView(games);
}

// Render games in list view grouped by date
function renderListView(games) {
    // Clear the container
    DOM.scheduleContent.innerHTML = '';
    
    // Sort games by date
    const sortedGames = [...games].sort((a, b) => {
        return a.date.localeCompare(b.date);
    });
    
    // Group games by month for better organization
    const gamesByMonth = groupGamesByMonth(sortedGames);
    
    // Create container for all months
    const container = document.createElement('div');
    container.className = 'schedule-feed';
    
    // Process each month
    for (const [month, monthGames] of Object.entries(gamesByMonth)) {
        // Create month section
        const monthSection = document.createElement('div');
        monthSection.className = 'month-section mb-4';
        
        // Add month header
        const monthHeader = document.createElement('h2');
        monthHeader.className = 'h4 mb-3 pb-2 border-bottom';
        monthHeader.textContent = month;
        monthSection.appendChild(monthHeader);
        
        // Process each date in this month
        for (const gameDate of monthGames) {
            // Create date section
            const dateSection = document.createElement('div');
            dateSection.className = 'date-section mb-4';
            dateSection.id = `date-${gameDate.date}`; // For jump-to functionality
            
            // Add date header
            const dateHeader = document.createElement('h3');
            dateHeader.className = 'h5 mb-3 d-flex align-items-center';
            
            // Format date for display
            const dateParts = gameDate.date.split('-');
            const dateObj = new Date(parseInt(dateParts[0]), parseInt(dateParts[1]) - 1, parseInt(dateParts[2]));
            const formattedDate = dateObj.toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric'
            });
            
            dateHeader.innerHTML = `
                <i class="fas fa-calendar-day me-2"></i>
                ${formattedDate}
                <span class="badge bg-primary rounded-pill ms-2">${gameDate.matches} Games</span>
            `;
            dateSection.appendChild(dateHeader);
            
            // Create games container
            const gamesContainer = document.createElement('div');
            gamesContainer.className = 'games-container';
            
            // Now fetch and display actual games for this date
            fetchGamesForDate(gameDate.date, gamesContainer);
            
            dateSection.appendChild(gamesContainer);
            monthSection.appendChild(dateSection);
        }
        
        container.appendChild(monthSection);
    }
    
    DOM.scheduleContent.appendChild(container);
}

// Fetch and render games for a specific date
function fetchGamesForDate(dateStr, container) {
    // Add loading indicator
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    // Check if we have a team filter active and we have currentTeamData cached
    const { team } = state.filters;
    if (team !== 'all' && window.currentTeamData) {
        console.log('Using cached team data for date:', dateStr);
        
        // Extract the date part to match with our stored data
        const dateParts = dateStr.split('-');
        const year = parseInt(dateParts[0]);
        const month = parseInt(dateParts[1]) - 1;
        const day = parseInt(dateParts[2]);
        
        // Format the date to match the format in team data ("DD Month YYYY")
        const dateObj = new Date(year, month, day);
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];
        const searchDateStr = `${day} ${monthNames[month]} ${year}`;
        
        console.log('Looking for matches on date:', searchDateStr);
        
        // Look for matches on this date in the cached team data
        const matchesForDate = window.currentTeamData.matches.filter(match => {
            return match.date === searchDateStr;
        });
        
        const tbdMatchesForDate = window.currentTeamData.tbd_matches.filter(match => {
            return match.date === searchDateStr;
        });
        
        // Log what we found for debugging
        console.log(`Found ${matchesForDate.length} regular matches and ${tbdMatchesForDate.length} TBD matches for ${searchDateStr}`);
        
        // Clear loading indicator
        container.innerHTML = '';
        
        // If no matches found for this date
        if (matchesForDate.length === 0 && tbdMatchesForDate.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No games found for ${team} on this date.
                </div>
            `;
            return;
        }
        
        // Group by league
        const gamesByLeague = {};
        
        // Process scheduled matches
        matchesForDate.forEach(match => {
            if (!gamesByLeague[match.league]) {
                gamesByLeague[match.league] = [];
            }
            
            // Format match data for the game card
            gamesByLeague[match.league].push({
                match: match.is_home ? 
                    `${team} vs ${match.opponent}` : 
                    `${match.opponent} vs ${team}`,
                time: match.time || 'TBD',
                location: match.location,
                display_location: match.display_location || match.location,
                league: match.league
            });
        });
        
        // Process TBD matches
        tbdMatchesForDate.forEach(match => {
            if (!gamesByLeague[match.league]) {
                gamesByLeague[match.league] = [];
            }
            
            // Format match data for the game card
            gamesByLeague[match.league].push({
                match: match.is_home ? 
                    `${team} vs ${match.opponent}` : 
                    `${match.opponent} vs ${team}`,
                time: 'TBD',
                location: match.location,
                display_location: match.display_location || match.location,
                league: match.league
            });
        });
        
        // Sort leagues by priority
        const sortedLeagues = Object.keys(gamesByLeague).sort((a, b) => {
            const leaguePriority = {
                'bundesliga': 1,
                '2bundesliga': 2,
                '3-liga': 3,
                'Champions League': 4,
                'Europa League': 5,
                'Conference League': 6,
                'DFB-Pokal': 7
            };
            return (leaguePriority[a] || 999) - (leaguePriority[b] || 999);
        });
        
        // Render games by league
        for (const league of sortedLeagues) {
            // Apply league filter if active
            if (state.filters.league !== 'all' && league !== state.filters.league) {
                continue;
            }
            
            const leagueGames = gamesByLeague[league];
            
            // Create league section
            const leagueSection = document.createElement('div');
            leagueSection.className = 'league-section mb-3';
            
            // Add league header
            const leagueHeader = document.createElement('div');
            leagueHeader.className = `league-header p-2 ${getLeagueClass(league)}`;
            leagueHeader.innerHTML = `
                <div class="d-flex align-items-center">
                    <img src="${getLeagueLogoUrl(league)}" alt="${league}" class="me-2" width="24" height="24">
                    <h4 class="h6 mb-0">${getLeagueDisplayName(league)}</h4>
                </div>
            `;
            leagueSection.appendChild(leagueHeader);
            
            // Add games
            leagueGames.forEach(game => {
                const gameCard = createGameCard(game);
                gameCard.classList.add('highlighted-game'); // Highlight all games since we're filtering by team
                leagueSection.appendChild(gameCard);
            });
            
            container.appendChild(leagueSection);
        }
    } else {
        // Fetch games for this date normally if no team filter or no cached data
        fetch(`http://localhost:8000/games-by-date/${dateStr}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load games for this date');
                }
                return response.json();
            })
            .then(data => {
                // Clear loading indicator
                container.innerHTML = '';
                
                // Check if we have games and if league filter is applied
                const { league, team } = state.filters;
                let gamesByLeague = data.games_by_league || {};
                
                // Apply league filter if active
                if (league !== 'all') {
                    gamesByLeague = {};
                    if (data.games_by_league && data.games_by_league[league]) {
                        gamesByLeague[league] = data.games_by_league[league];
                    }
                }
                
                // Check if we have any games after filtering
                if (Object.keys(gamesByLeague).length === 0) {
                    container.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            No games found for this date matching your filters.
                        </div>
                    `;
                    return;
                }
                
                // Sort leagues by priority
                const sortedLeagues = Object.keys(gamesByLeague).sort((a, b) => {
                    const leaguePriority = {
                        'bundesliga': 1,
                        '2bundesliga': 2,
                        '3-liga': 3,
                        'Champions League': 4,
                        'Europa League': 5,
                        'Conference League': 6,
                        'DFB-Pokal': 7
                    };
                    return (leaguePriority[a] || 999) - (leaguePriority[b] || 999);
                });
                
                // Render games by league
                for (const league of sortedLeagues) {
                    const leagueGames = gamesByLeague[league];
                    
                    let filteredGames = leagueGames;

                    // Apply team filter if active
                    if (team !== 'all') {
                        filteredGames = filteredGames.filter(game => {
                            if (!game.match) return false;
                            
                            // Split the match string into home and away teams
                            const matchParts = game.match.split(' vs ');
                            if (matchParts.length !== 2) return false;
                            
                            // Check if either team matches the filter exactly
                            const homeTeam = matchParts[0].trim();
                            const awayTeam = matchParts[1].split(" (")[0].trim();
                            
                            return homeTeam === team || awayTeam === team;
                        });
                        
                        // Skip this league if no games match the team filter
                        if (filteredGames.length === 0) {
                            continue;
                        }
                    }
                    
                    // Create league section
                    const leagueSection = document.createElement('div');
                    leagueSection.className = 'league-section mb-3';
                    
                    // Add league header
                    const leagueHeader = document.createElement('div');
                    leagueHeader.className = `league-header p-2 ${getLeagueClass(league)}`;
                    leagueHeader.innerHTML = `
                        <div class="d-flex align-items-center">
                            <img src="${getLeagueLogoUrl(league)}" alt="${league}" class="me-2" width="24" height="24">
                            <h4 class="h6 mb-0">${getLeagueDisplayName(league)}</h4>
                        </div>
                    `;
                    leagueSection.appendChild(leagueHeader);
                    
                    // Add games
                    filteredGames.forEach(game => {
                        // Standard game card will handle TBD times properly
                        const gameCard = createGameCard(game);
                        leagueSection.appendChild(gameCard);
                    });
                    
                    container.appendChild(leagueSection);
                }
            })
            .catch(error => {
                console.error('Error fetching games for date:', error);
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error loading games: ${error.message}
                    </div>
                `;
            });
    }
}

// Update the createGameCard function to ensure TBD times are properly displayed
function createGameCard(game) {
    const card = document.createElement('div');
    card.className = 'card game-card mb-2';
    
    // Extract team names
    let homeTeam = '';
    let awayTeam = '';
    
    if (game.match) {
        const matchParts = game.match.split(' vs ');
        if (matchParts.length === 2) {
            homeTeam = matchParts[0].trim();
            awayTeam = matchParts[1].trim();
        }
    }
    
    // Check if this game includes the filtered team
    const isHighlighted = state.filters.team !== 'all' && 
                         (homeTeam === state.filters.team || awayTeam === state.filters.team);
    
    if (isHighlighted) {
        card.classList.add('highlighted-game');
    }
    
    // Absolutely ensure game time is never undefined or null in display
    let displayTime = 'TBD';
    if (game.time && game.time !== 'null' && game.time.trim() !== '') {
        displayTime = game.time;
    }
    
    // Add specific class for TBD games
    if (displayTime === 'TBD') {
        card.classList.add('tbd-game');
    }
    
    const cardBody = document.createElement('div');
    cardBody.className = 'card-body py-3';
    
    // Fixed VS position layout
    cardBody.innerHTML = `
        <div class="row align-items-center">
            <div class="col-md-2 col-3">
                <div class="match-time text-center ${displayTime === 'TBD' ? 'text-muted fst-italic' : ''}">
                    ${displayTime}
                </div>
            </div>
            
            <div class="col-md-8 col-6">
                <div class="match-teams">
                    <div class="home-team">
                        <span class="team-name">${homeTeam}</span>
                        <img src="${getTeamLogoUrl(homeTeam)}" alt="${homeTeam}" class="team-badge">
                    </div>
                    
                    <div class="vs-container">
                        <span class="vs">vs</span>
                    </div>
                    
                    <div class="away-team">
                        <img src="${getTeamLogoUrl(awayTeam)}" alt="${awayTeam}" class="team-badge">
                        <span class="team-name">${awayTeam}</span>
                    </div>
                </div>
            </div>
            
            <div class="col-md-2 col-3 text-end">
                <div class="match-location">
                    <i class="fas fa-map-marker-alt me-1"></i>
                    <span>${game.display_location || game.location}</span>
                </div>
            </div>
        </div>
    `;
    
    card.appendChild(cardBody);
    return card;
}

// Helper function to get league CSS class
function getLeagueClass(league) {
    if (!league) return '';
    
    const leagueLower = league.toLowerCase();
    
    if (leagueLower.includes('bundesliga') && !leagueLower.includes('2')) {
        return 'bundesliga';
    } else if (leagueLower.includes('2bundesliga') || leagueLower.includes('2. bundesliga')) {
        return 'liga2';
    } else if (leagueLower.includes('3-liga') || leagueLower.includes('3. liga')) {
        return 'liga3';
    } else if (leagueLower.includes('champions')) {
        return 'champions-league';
    } else if (leagueLower.includes('europa')) {
        return 'europa-league';
    } else if (leagueLower.includes('pokal')) {
        return 'dfb-pokal';
    }
    
    return '';
}

// Group games by month
function groupGamesByMonth(games) {
    const gamesByMonth = {};
    
    games.forEach(game => {
        // Extract month and year from date
        const dateParts = game.date.split('-');
        const dateObj = new Date(parseInt(dateParts[0]), parseInt(dateParts[1]) - 1, 1);
        const monthYear = dateObj.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        
        if (!gamesByMonth[monthYear]) {
            gamesByMonth[monthYear] = [];
        }
        
        gamesByMonth[monthYear].push(game);
    });
    
    // Sort games within each month
    for (const month in gamesByMonth) {
        gamesByMonth[month].sort((a, b) => {
            return a.date.localeCompare(b.date);
        });
    }
    
    return gamesByMonth;
}

// Render view for a specific date
function renderDateView(data) {
    // Clear the container
    DOM.scheduleContent.innerHTML = '';
    
    // Create date header
    const dateHeader = document.createElement('div');
    dateHeader.className = 'date-header mb-4';
    dateHeader.innerHTML = `
        <div class="d-flex align-items-center mb-2">
            <i class="fas fa-calendar-day me-3 display-5"></i>
            <h2 class="mb-0">${data.display_date}</h2>
        </div>
        <div class="date-stats">
            <span class="badge bg-secondary">${data.total_games} Games</span>
            <span class="badge bg-secondary ms-2">${Object.keys(data.games_by_league).length} Leagues</span>
        </div>
    `;
    DOM.scheduleContent.appendChild(dateHeader);
    
    // Create games container
    const gamesContainer = document.createElement('div');
    gamesContainer.className = 'games-container';
    
    // Check if we have games and if league filter is applied
    const { league, team } = state.filters;
    let gamesByLeague = data.games_by_league;
    
    // Apply league filter if active
    if (league !== 'all') {
        gamesByLeague = {};
        if (data.games_by_league[league]) {
            gamesByLeague[league] = data.games_by_league[league];
        }
    }
    
    // Check if we have any games after filtering
    if (Object.keys(gamesByLeague).length === 0) {
        gamesContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No games found for this date matching your filters.
            </div>
        `;
        DOM.scheduleContent.appendChild(gamesContainer);
        return;
    }
    
    // Sort leagues by priority
    const sortedLeagues = Object.keys(gamesByLeague).sort((a, b) => {
        const leaguePriority = {
            'bundesliga': 1,
            '2bundesliga': 2,
            '3-liga': 3,
            'Champions League': 4,
            'Europa League': 5,
            'Conference League': 6,
            'DFB-Pokal': 7
        };
        return (leaguePriority[a] || 999) - (leaguePriority[b] || 999);
    });
    
    // Render games by league
    for (const league of sortedLeagues) {
        const leagueGames = gamesByLeague[league];
        
        let filteredGames = leagueGames;

        // Apply team filter if active
        if (team !== 'all') {
            filteredGames = filteredGames.filter(game => {
                if (!game.match) return false;
                
                // Split the match string into home and away teams
                const matchParts = game.match.split(' vs ');
                if (matchParts.length !== 2) return false;
                
                // Check if either team matches the filter exactly
                const homeTeam = matchParts[0].trim();
                const awayTeam = matchParts[1].trim();
                
                console.log(`DateView: Comparing [${homeTeam}] or [${awayTeam}] with filter [${team}]`);
                return homeTeam === team || awayTeam === team;
            });
            
            // Skip this league if no games match the team filter
            if (filteredGames.length === 0) {
                console.log(`DateView: No games in ${league} match team filter: ${team}`);
                continue;
            }
        }
        
        // Create league section
        const leagueSection = document.createElement('div');
        leagueSection.className = 'league-section mb-4';
        
        // Add league header
        const leagueHeader = document.createElement('div');
        leagueHeader.className = `league-header p-3 ${getLeagueClass(league)}`;
        leagueHeader.innerHTML = `
            <div class="d-flex align-items-center">
                <img src="${getLeagueLogoUrl(league)}" alt="${league}" class="me-3" width="32" height="32">
                <h3 class="h5 mb-0">${getLeagueDisplayName(league)}</h3>
            </div>
        `;
        leagueSection.appendChild(leagueHeader);
        
        // Add games
        filteredGames.forEach(game => {
            const gameCard = createGameCard(game);
            leagueSection.appendChild(gameCard);
        });
        
        gamesContainer.appendChild(leagueSection);
    }
    
    DOM.scheduleContent.appendChild(gamesContainer);
}


// Show no games message
function showNoGames() {
    DOM.scheduleLoading.classList.add('d-none');
    DOM.scheduleResults.classList.add('d-none');
    DOM.noSchedule.classList.remove('d-none');
}

// Display all games for a team directly from the team data
function displayTeamGames(teamData) {
    // Clear the container
    DOM.scheduleContent.innerHTML = '';
    
    const teamName = teamData.team;
    
    // Create header
    const teamHeader = document.createElement('div');
    teamHeader.className = 'team-header mb-4 pb-2 border-bottom';
    teamHeader.innerHTML = `
        <div class="d-flex align-items-center mb-3">
            <img src="${getTeamLogoUrl(teamName)}" class="me-3" width="60" height="60" alt="${teamName}">
            <div>
                <h2 class="h3 mb-1">${teamName}</h2>
                <div class="d-flex gap-2">
                    <span class="badge bg-primary rounded-pill">${teamData.total_matches} Total Matches</span>
                    <span class="badge bg-success rounded-pill">${teamData.matches.length} Scheduled</span>
                    <span class="badge bg-warning text-dark rounded-pill">${teamData.tbd_matches.length} TBD</span>
                </div>
            </div>
        </div>
    `;
    DOM.scheduleContent.appendChild(teamHeader);
    
    // Create container for all matches
    const matchesContainer = document.createElement('div');
    matchesContainer.className = 'team-matches schedule-feed';
    
    // Group matches by month
    const matchesByMonth = {};
    
    // Process both confirmed and TBD matches
    const allMatches = [...teamData.matches, ...teamData.tbd_matches];
    
    // Apply league filter if active
    let filteredMatches = allMatches;
    if (state.filters.league !== 'all') {
        filteredMatches = allMatches.filter(match => match.league === state.filters.league);
    }
    
    // Sort matches by date
    filteredMatches.sort((a, b) => {
        // Parse dates for comparison
        const dateA = parseDate(a.date);
        const dateB = parseDate(b.date);
        return dateA - dateB;
    });
    
    if (filteredMatches.length === 0) {
        const noMatchesMsg = document.createElement('div');
        noMatchesMsg.className = 'alert alert-info';
        noMatchesMsg.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>
            No matches found for ${teamName}${state.filters.league !== 'all' ? ` in ${getLeagueDisplayName(state.filters.league)}` : ''}.
        `;
        matchesContainer.appendChild(noMatchesMsg);
        DOM.scheduleContent.appendChild(matchesContainer);
        return;
    }
    
    // Group by month
    filteredMatches.forEach(match => {
        // Extract date parts
        const dateParts = match.date.split(' ');
        const monthYear = `${dateParts[1]} ${dateParts[2]}`;
        
        if (!matchesByMonth[monthYear]) {
            matchesByMonth[monthYear] = [];
        }
        
        matchesByMonth[monthYear].push(match);
    });
    
    // Create month sections
    Object.keys(matchesByMonth).forEach(monthYear => {
        const monthMatches = matchesByMonth[monthYear];
        
        // Create month section
        const monthSection = document.createElement('div');
        monthSection.className = 'month-section mb-4';
        
        // Add month header
        const monthHeader = document.createElement('h3');
        monthHeader.className = 'h4 mb-3 pb-2 border-bottom';
        monthHeader.textContent = monthYear;
        monthSection.appendChild(monthHeader);
        
        // Group by day
        const dayGroups = {};
        monthMatches.forEach(match => {
            const dayKey = match.date;
            if (!dayGroups[dayKey]) {
                dayGroups[dayKey] = [];
            }
            dayGroups[dayKey].push(match);
        });
        
        // Process each day
        Object.keys(dayGroups).sort((a, b) => {
            // Sort days chronologically
            const dateA = parseDate(a);
            const dateB = parseDate(b);
            return dateA - dateB;
        }).forEach(day => {
            const dayMatches = dayGroups[day];
            
            // Create day section
            const daySection = document.createElement('div');
            daySection.className = 'date-section mb-4';
            
            // Parse date parts
            const dateParts = day.split(' ');
            const dayNum = parseInt(dateParts[0]);
            const monthName = dateParts[1];
            const year = parseInt(dateParts[2]);
            
            // Create Date object for formatting
            const date = new Date(year, ['January', 'February', 'March', 'April', 'May', 'June', 
                                      'July', 'August', 'September', 'October', 'November', 'December']
                                     .indexOf(monthName), dayNum);
            
            // Format date and create date ID for jump-to functionality
            const dateId = `${year}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
            daySection.id = `date-${dateId}`;
            
            // Format date
            const formattedDate = date.toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric'
            });
            
            // Add day header
            const dayHeader = document.createElement('h4');
            dayHeader.className = 'h5 mb-3 d-flex align-items-center';
            dayHeader.innerHTML = `
                <i class="fas fa-calendar-day me-2"></i>
                ${formattedDate}
                <span class="badge bg-primary rounded-pill ms-2">${dayMatches.length} Games</span>
            `;
            daySection.appendChild(dayHeader);
            
            // Group by league
            const leagueGroups = {};
            dayMatches.forEach(match => {
                if (!leagueGroups[match.league]) {
                    leagueGroups[match.league] = [];
                }
                leagueGroups[match.league].push(match);
            });
            
            // Sort leagues by priority
            const sortedLeagues = Object.keys(leagueGroups).sort((a, b) => {
                const leaguePriority = {
                    'bundesliga': 1,
                    '2bundesliga': 2,
                    '3-liga': 3,
                    'Champions League': 4,
                    'Europa League': 5,
                    'Conference League': 6,
                    'DFB-Pokal': 7
                };
                return (leaguePriority[a] || 999) - (leaguePriority[b] || 999);
            });
            
            // Process each league
            sortedLeagues.forEach(leagueName => {
                const leagueMatches = leagueGroups[leagueName];
                
                // Create league section
                const leagueSection = document.createElement('div');
                leagueSection.className = 'league-section mb-3';
                
                // Add league header
                const leagueHeader = document.createElement('div');
                leagueHeader.className = `league-header p-2 ${getLeagueClass(leagueName)}`;
                leagueHeader.innerHTML = `
                    <div class="d-flex align-items-center">
                        <img src="${getLeagueLogoUrl(leagueName)}" alt="${leagueName}" class="me-2" width="24" height="24">
                        <h5 class="h6 mb-0">${getLeagueDisplayName(leagueName)}</h5>
                    </div>
                `;
                leagueSection.appendChild(leagueHeader);
                
                // Add matches
                leagueMatches.forEach(match => {
                    // Create game card
                    const gameCard = document.createElement('div');
                    gameCard.className = 'card game-card highlighted-game mb-2';
                    
                    const matchTime = match.time || 'TBD';
                    const timeClass = matchTime === 'TBD' ? 'text-muted fst-italic' : '';
                    
                    const cardBody = document.createElement('div');
                    cardBody.className = 'card-body py-3';
                    
                    cardBody.innerHTML = `
                        <div class="row align-items-center">
                            <div class="col-md-2 col-3">
                                <div class="match-time text-center ${timeClass}">
                                    ${matchTime}
                                </div>
                            </div>
                            
                            <div class="col-md-8 col-6">
                                <div class="match-teams">
                                    <div class="home-team">
                                        <span class="team-name">${match.is_home ? teamName : match.opponent}</span>
                                        <img src="${getTeamLogoUrl(match.is_home ? teamName : match.opponent)}" 
                                             alt="${match.is_home ? teamName : match.opponent}" class="team-badge">
                                    </div>
                                    
                                    <div class="vs-container">
                                        <span class="vs">vs</span>
                                    </div>
                                    
                                    <div class="away-team">
                                        <img src="${getTeamLogoUrl(match.is_home ? match.opponent : teamName)}" 
                                             alt="${match.is_home ? match.opponent : teamName}" class="team-badge">
                                        <span class="team-name">${match.is_home ? match.opponent : teamName}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-2 col-3 text-end">
                                <div class="match-location">
                                    <i class="fas fa-map-marker-alt me-1"></i>
                                    <span>${match.display_location || match.location}</span>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    gameCard.appendChild(cardBody);
                    leagueSection.appendChild(gameCard);
                });
                
                daySection.appendChild(leagueSection);
            });
            
            monthSection.appendChild(daySection);
        });
        
        matchesContainer.appendChild(monthSection);
    });
    
    DOM.scheduleContent.appendChild(matchesContainer);
}

// Helper function to parse date string into Date object
function parseDate(dateStr) {
    // Example: "28 March 2025"
    const parts = dateStr.split(' ');
    const day = parseInt(parts[0]);
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December'];
    const month = monthNames.indexOf(parts[1]);
    const year = parseInt(parts[2]);
    
    return new Date(year, month, day);
}