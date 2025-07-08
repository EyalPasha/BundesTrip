import { applyTeamLogoStyles, preloadLogos, formatTeamOptionWithLogo, formatLeagueOptionWithLogo, getTeamLogoUrl, getLeagueLogoUrl } from './team-logos.js';
import { fetchAllTeams, fetchLeagues, fetchAvailableDates, fetchGamesByDate, fetchTeamSchedule } from './schedule-service.js';
import { GERMAN_TEAMS } from './data-loader.js';
import { formatCityForDisplay, formatCityForBackend } from './city-formatter.js';
import { TEAM_TICKET_LINKS } from './data-loader.js';

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

// Restore the desktop date filter functionality
function initializeFlatpickr() {
    // Skip if we're on mobile
    if (window.innerWidth < 768 || !DOM.dateFilter) {
        return;
    }

    flatpickr(DOM.dateFilter, {
        dateFormat: "F j, Y",
        altInput: true,
        altFormat: "F j, Y",
        minDate: "today",
        maxDate: new Date().fp_incr(120),
        onChange: function(selectedDates) {
            if (selectedDates.length > 0) {
                jumpToDate(selectedDates[0]);
            }
        },
        disableMobile: "true",
        locale: { firstDayOfWeek: 1 },
        onClose: function(selectedDates, dateStr, instance) {
            setTimeout(() => { instance.clear(); }, 100);
        },
        // --- ADD THIS BLOCK ---
        onDayCreate: function(dObj, dStr, fp, dayElem) {
            const y = dayElem.dateObj.getFullYear();
            const m = String(dayElem.dateObj.getMonth() + 1).padStart(2, '0');
            const d = String(dayElem.dateObj.getDate()).padStart(2, '0');
            const dateStr = `${y}-${m}-${d}`;
        
            if (state.games && state.games.length > 0) {
                const matchDate = state.games.find(g => g.date === dateStr);
                if (matchDate && matchDate.matches) {
                    dayElem.classList.add('has-matches');
                    const dot = document.createElement('span');
                    dot.className = 'date-dot';
                    dayElem.appendChild(dot);
                }
            }
        }
        // --- END BLOCK ---
    });
}

// Initialize the page when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // console.log('Schedule page initialized');
    
    // Pre-hide filters with inline styles to prevent flash
    document.head.insertAdjacentHTML('beforeend', `
        <style id="initial-hide-filters">
            .filter-bar { 
                opacity: 0 !important; 
                pointer-events: none !important; 
                visibility: hidden !important;
            }
            .filter-btn, .calendar-btn {
                opacity: 0 !important;
                pointer-events: none !important;
                visibility: hidden !important;
            }
        </style>
    `);
    
    // Initialize logos
    applyTeamLogoStyles();
    preloadLogos();
    
    // Setup event listeners (but don't show filters yet)
    setupEventListeners();
    
    try {
        // Show enhanced loading immediately
        DOM.scheduleLoading.innerHTML = `
            <div class="enhanced-loading">
                <div class="loading-ball"></div>
                <div class="loading-shadow"></div>
                <div class="loading-text">Loading Schedule</div>
            </div>
        `;
        
        // Load data first with proper timing
        //console.log('Loading teams and leagues...');
        const [teams, leagues] = await Promise.all([
            loadTeams(),
            loadLeagues()
        ]);
        
        //console.log(`Successfully loaded ${teams.length} teams and ${leagues.length} leagues`);
        
        await loadAllGames();
        
        initializeFlatpickr();
        createCalendarButton(); // <-- add this here
        
        showAllFilters();
        
    } catch (error) {
        console.error('Error during initialization:', error);
        // Even on error, show filters so users can interact
        showAllFilters();
    }
});

// Function to show all filters after loading
function showAllFilters() {
    // console.log('Showing filters after loading');
    
    // Remove the initial hiding style
    const initialStyle = document.getElementById('initial-hide-filters');
    if (initialStyle) {
        initialStyle.remove();
    }
    
    // Show desktop filters with a smooth transition
    const filterBar = document.querySelector('.filter-bar');
    if (filterBar) {
        filterBar.style.transition = 'opacity 0.5s ease';
        filterBar.style.opacity = '1';
        filterBar.style.visibility = 'visible';
        filterBar.style.pointerEvents = 'auto';
    }
    
    // Show mobile buttons with animations
    setTimeout(() => {
        const buttons = document.querySelectorAll('.filter-btn, .calendar-btn');
        buttons.forEach((btn, index) => {
            btn.style.transition = 'opacity 0.5s ease, transform 0.3s ease';
            btn.style.opacity = '1';
            btn.style.visibility = 'visible';
            btn.style.pointerEvents = 'auto';
            
            // Add entrance animation
            if (btn.classList.contains('filter-btn')) {
                btn.style.animation = 'slideInRight 0.5s ease forwards';
            } else if (btn.classList.contains('calendar-btn')) {
                btn.style.animation = 'slideInLeft 0.5s ease forwards';
            }
        });
        
        // Add animation keyframes
        document.head.insertAdjacentHTML('beforeend', `
            <style>
                @keyframes slideInRight {
                    from { transform: translateX(50px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                @keyframes slideInLeft {
                    from { transform: translateX(-50px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            </style>
        `);
    }, 100);
}

// Load teams into the filter dropdown
async function loadTeams() {
    try {
        // First try to get teams from global state if loaded by main page
        let teams = [];
        if (window.globalTeamsData && window.globalTeamsData.teams) {
            //console.log('Using teams from global state:', window.globalTeamsData.teams.length);
            teams = window.globalTeamsData.teams;
        } else {
            //console.log('Fetching teams from API');
            teams = await fetchAllTeams();
            //console.log('Fetched teams from API:', teams.length);
        }
        
        // Filter to only German teams
        const germanTeams = teams.filter(team => GERMAN_TEAMS.includes(team));
        state.teams = germanTeams;
        
        if (germanTeams.length === 0) {
            //console.warn('No German teams found in the data');
        }
        
        // Clear and populate the select
        DOM.teamFilter.innerHTML = '<option value="all">All Teams</option>';
        
        // Add team options sorted alphabetically
        germanTeams.sort().forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            DOM.teamFilter.appendChild(option);
        });
        
        //console.log(`Team filter populated with ${germanTeams.length} teams`);
        
        // Trigger an event that mobile filters can listen for
        document.dispatchEvent(new CustomEvent('teamsLoaded', {
            detail: { teams: germanTeams }
        }));
        
        return germanTeams;
    } catch (error) {
        console.error('Failed to load teams:', error);
        return [];
    }
}

// Load leagues into the filter dropdown
async function loadLeagues() {
    try {
        // First try to get leagues from global state if loaded by main page
        let leagues = [];
        if (window.globalLeaguesData && window.globalLeaguesData.leagues) {
            //console.log('Using leagues from global state:', window.globalLeaguesData.leagues);
            leagues = window.globalLeaguesData.leagues;
        } else {
            //console.log('Fetching leagues from API');
            leagues = await fetchLeagues();
            //console.log('Fetched leagues from API:', leagues);
        }
        
        state.leagues = leagues;
        
        if (leagues.length === 0) {
            //console.warn('No leagues found in the data');
        }
        
        // Clear and populate the select
        DOM.leagueFilter.innerHTML = '<option value="all">All Leagues</option>';
        
        // Add league options
        leagues.forEach(league => {
            const option = document.createElement('option');
            option.value = league;
            option.textContent = getLeagueDisplayName(league);
            DOM.leagueFilter.appendChild(option);
        });
        
        //console.log(`League filter populated with ${leagues.length} leagues`);
        
        // Trigger an event that mobile filters can listen for
        document.dispatchEvent(new CustomEvent('leaguesLoaded', {
            detail: { leagues: leagues }
        }));
        
        return leagues;
    } catch (error) {
        console.error('Failed to load leagues:', error);
        return [];
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
// Modify the existing function to no longer include date picker
function setupEventListeners() {
    // Clear filters
    DOM.clearFilters.addEventListener('click', clearFilters);
    
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
        
        // console.log('Filters set to sticky mode');
    }
    
    // Add CSS for sticky behavior
    addStickyStyles();
}

// Update the CSS styles to hide calendar button on desktop
function addStickyStyles() {
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        /* Desktop filters - keep sticky behavior */
        @media (min-width: 768px) {
            .sticky-filters {
                position: sticky;
                top: 56px; /* Add navbar height here (56px is standard Bootstrap navbar height) */
                z-index: 999; /* Lower than navbar's z-index */
                background-color: #fff;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                margin-top: 0;
                padding-top: 15px;
                padding-bottom: 15px;
                transition: box-shadow 0.3s ease;
            }
            
            .sticky-active-filters {
                position: sticky;
                top: 162px; /* Navbar (56px) + filter bar height (~80px) */
                z-index: 998; /* Lower than filters z-index */
                background-color: #fff;
                padding-top: 10px;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }
            
            /* Ensure navbar has highest z-index */
            .navbar.sticky-top {
                z-index: 1000;
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
            
            /* Highlight animation for the date jumping */
            .highlight-section {
                animation: highlight-fade 2s ease;
            }
            
            @keyframes highlight-fade {
                0%, 30% { background-color: rgba(13, 110, 253, 0.15); }
                100% { background-color: transparent; }
            }
            
            /* Hide calendar button on desktop */
            .calendar-btn {
                display: none;
            }
        }
        
        /* Mobile filter button and drawer */
        @media (max-width: 767.98px) {
            /* Hide the original filter bar */
            .filter-bar {
                display: none !important;
            }
            
            /* Hide the active filters display (will show in a different way) */
            .sticky-active-filters {
                display: none !important;
            }
            
            /* Filter toggle button */
            .filter-btn {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background-color: #043d7c;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                z-index: 1000;
                border: none;
                font-size: 1.2rem;
                transition: transform 0.2s;
            }
            
            .filter-btn:active {
                transform: scale(0.95);
            }
            
            /* Calendar button (mobile) */
            .calendar-btn {
                position: fixed;
                bottom: 20px;
                left: 20px;
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background-color: #043d7c;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                z-index: 1000;
                border: none;
                font-size: 1.2rem;
                transition: transform 0.2s;
            }
            
            .calendar-btn:active {
                transform: scale(0.95);
            }
            
            /* Filter count badge */
            .filter-count {
                position: absolute;
                top: -5px;
                right: -5px;
                background-color: #ff6b00;
                color: white;
                border-radius: 50%;
                width: 22px;
                height: 22px;
                font-size: 0.7rem;
                font-weight: bold;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 2px solid white;
                opacity: 0;
                transition: opacity 0.3s;
            }
            
            .filter-count.has-filters {
                opacity: 1;
            }
            
            /* Drawer overlay */
            .drawer-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0,0,0,0.5);
                z-index: 1001;
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.3s;
            }
            
            .drawer-overlay.open {
                opacity: 1;
                visibility: visible;
            }
            
            /* Filter drawer */
            .filter-drawer {
                position: fixed;
                top: 0;
                right: -85%;
                width: 85%;
                height: 100%;
                background-color: white;
                z-index: 1002;
                box-shadow: -2px 0 10px rgba(0,0,0,0.2);
                transition: right 0.3s;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }
            
            .filter-drawer.open {
                right: 0;
            }
            
            /* Drawer header */
            .drawer-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            
            .drawer-title {
                font-size: 1.2rem;
                font-weight: 500;
                margin: 0;
                color: #043d7c;
            }
            
            .drawer-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                line-height: 1;
                color: #666;
                padding: 0;
            }
            
            /* Drawer content */
            .drawer-content {
                padding: 15px;
                flex-grow: 1;
                overflow-y: auto;
            }
            
            /* Filter group */
            .drawer-filter-group {
                margin-bottom: 20px;
            }
            
            .drawer-filter-label {
                font-weight: 600;
                font-size: 0.9rem;
                margin-bottom: 8px;
                color: #333;
            }
            
            /* Active filters */
            .mobile-active-filters {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin: 10px 0 20px;
            }
            
            .mobile-filter-badge {
                background-color: #f0f4f8;
                color: #043d7c;
                border-radius: 20px;
                padding: 5px 12px;
                font-size: 0.8rem;
                display: flex;
                align-items: center;
                gap: 8px;
                border: 1px solid #d0e0f0;
            }
            
            .badge-remove {
                background: none;
                border: none;
                color: #999;
                padding: 0;
                font-size: 0.9rem;
            }
            
            /* Action buttons */
            .drawer-actions {
                padding: 15px;
                border-top: 1px solid #eee;
                display: flex;
                gap: 10px;
            }
            
            .drawer-actions button {
                flex: 1;
                padding: 10px;
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
        /* Mobile team header fixes */
        @media (max-width: 767.98px) {
            .team-header {
                padding: 0.75rem !important;
            }
            
            .team-header h2.h3 {
                font-size: 1.1rem !important;
                margin-right: 0.5rem;
            }
            
            .team-header .badge {
                font-size: 0.65rem !important;
                padding: 0.15rem 0.4rem !important;
            }
            
            .fs-7 {
                font-size: 0.7rem !important;
            }
            
            /* Ensure badges don't wrap awkwardly */
            .team-header .d-flex.flex-wrap {
                margin-left: 0 !important;
            }
        }
    `;
    document.head.appendChild(styleElement);
    
    // Create the calendar button (now only for mobile)
    createCalendarButton();
    
    // Only create mobile filter button on mobile screens
    if (window.innerWidth < 768) {
        createMobileFilterButton();
    }
    
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

// Create floating calendar button - mobile only
function createCalendarButton() {
    // Only create for mobile devices
    if (window.innerWidth >= 768) {
        return; // Skip creation on desktop
    }

    const calendarButton = document.createElement('button');
    calendarButton.className = 'calendar-btn';
    calendarButton.innerHTML = '<i class="fas fa-calendar-alt"></i>';
    calendarButton.setAttribute('aria-label', 'Jump to date');

    // Append to document
    document.body.appendChild(calendarButton);

    // Setup calendar functionality with reset on close
    flatpickr(calendarButton, {
        dateFormat: "F j, Y",
        inline: false,
        minDate: "today",
        maxDate: new Date().fp_incr(120),
        onChange: function(selectedDates) {
            if (selectedDates.length > 0) {
                jumpToDate(selectedDates[0]);
            }
        },
        disableMobile: "true",
        locale: { firstDayOfWeek: 1 },
        onReady: function(dateObj, dateStr, instance) {
            instance.calendarContainer.classList.add('floating-calendar');
        },
        onClose: function(selectedDates, dateStr, instance) {
            setTimeout(() => { instance.clear(); }, 100);
        },
        // --- ADD THIS BLOCK ---
        onDayCreate: function(dObj, dStr, fp, dayElem) {
            const y = dayElem.dateObj.getFullYear();
            const m = String(dayElem.dateObj.getMonth() + 1).padStart(2, '0');
            const d = String(dayElem.dateObj.getDate()).padStart(2, '0');
            const dateStr = `${y}-${m}-${d}`;

            if (state.games && state.games.length > 0) {
                const matchDate = state.games.find(g => g.date === dateStr);
                if (matchDate && matchDate.matches) {
                    dayElem.classList.add('has-matches');
                    const dot = document.createElement('span');
                    dot.className = 'date-dot';
                    dayElem.appendChild(dot);
                }
            }
        }
        // --- END BLOCK ---
    });
}

// Create mobile filter button and drawer
function createMobileFilterButton() {
    // Create filter button
    const filterButton = document.createElement('button');
    filterButton.className = 'filter-btn';
    filterButton.innerHTML = '<i class="fas fa-filter"></i>';
    filterButton.setAttribute('aria-label', 'Filter games');
    
    // Add filter count badge
    const filterCount = document.createElement('span');
    filterCount.className = 'filter-count';
    filterCount.textContent = '0';
    filterButton.appendChild(filterCount);
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'drawer-overlay';
    
    // Create drawer
    const drawer = document.createElement('div');
    drawer.className = 'filter-drawer';
    drawer.innerHTML = `
        <div class="drawer-header">
            <h3 class="drawer-title">Filter Games</h3>
            <button class="drawer-close" aria-label="Close filter menu">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="drawer-content">
            <div class="mobile-active-filters"></div>
            
            <div class="drawer-filter-group">
                <label class="drawer-filter-label" for="mobileLeagueFilter">
                    <i class="fas fa-trophy me-2"></i> League
                </label>
                <select class="form-select" id="mobileLeagueFilter">
                    <option value="all">All Leagues</option>
                </select>
            </div>
            
            <div class="drawer-filter-group">
                <label class="drawer-filter-label" for="mobileTeamFilter">
                    <i class="fas fa-futbol me-2"></i> Team
                </label>
                <select class="form-select" id="mobileTeamFilter">
                    <option value="all">All Teams</option>
                </select>
            </div>
        </div>
        <div class="drawer-actions">
            <button class="btn btn-outline-secondary" id="clearMobileFilters">
                <i class="fas fa-times me-2"></i> Clear All
            </button>
            <button class="btn btn-primary" id="applyMobileFilters">
                <i class="fas fa-check me-2"></i> Apply Filters
            </button>
        </div>
    `;
    
    // In the createMobileFilterButton() function, after creating the drawer, add Select2 initialization:
    
    // After the drawer is added to the document body, initialize Select2 on mobile filters
    document.body.appendChild(filterButton);
    document.body.appendChild(overlay);
    document.body.appendChild(drawer);
    
    // Initialize Select2 on mobile filters after drawer is added to DOM
    setTimeout(() => {
        const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
        const mobileTeamFilter = document.getElementById('mobileTeamFilter');
        
        if (mobileLeagueFilter && window.$) {
            $(mobileLeagueFilter).select2({
                dropdownParent: drawer,
                width: '100%',
                templateResult: function(option) {
                    if (!option.id || option.id === 'all') {
                        return option.text;
                    }
                    return formatLeagueOptionWithLogo(option);
                },
                templateSelection: function(option) {
                    if (!option.id || option.id === 'all') {
                        return option.text;
                    }
                    return formatLeagueOptionWithLogo(option);
                },
                escapeMarkup: function(markup) {
                    return markup;
                }
            });
        }
        
        if (mobileTeamFilter && window.$) {
            $(mobileTeamFilter).select2({
                dropdownParent: drawer,
                width: '100%',
                templateResult: function(option) {
                    if (!option.id || option.id === 'all') {
                        return option.text;
                    }
                    return formatTeamOptionWithLogo(option);
                },
                templateSelection: function(option) {
                    if (!option.id || option.id === 'all') {
                        return option.text;
                    }
                    return formatTeamOptionWithLogo(option);
                },
                escapeMarkup: function(markup) {
                    return markup;
                }
            });
        }
    }, 100);
    // Initialize flatpickr for mobile date filter
    const mobileDateFilter = document.getElementById('mobileDateFilter');
    if (mobileDateFilter) {
        flatpickr(mobileDateFilter, {
            dateFormat: "F j, Y",
            minDate: "today",
            maxDate: new Date().fp_incr(120),
            disableMobile: "true"
        });
    }
    
    // Update filter count
    function updateFilterCount() {
        let count = 0;
        if (state.filters.league !== 'all') count++;
        if (state.filters.team !== 'all') count++;
        
        filterCount.textContent = count;
        if (count > 0) {
            filterCount.classList.add('has-filters');
        } else {
            filterCount.classList.remove('has-filters');
        }
        
        // Update mobile active filters
        updateMobileActiveFilters();
    }
    
    // Update mobile active filters display
    function updateMobileActiveFilters() {
        const mobileFiltersContainer = document.querySelector('.mobile-active-filters');
        if (!mobileFiltersContainer) return;
        
        mobileFiltersContainer.innerHTML = '';
        
        if (state.filters.league !== 'all') {
            const leagueName = getLeagueDisplayName(state.filters.league);
            const badge = createMobileFilterBadge('league', leagueName);
            mobileFiltersContainer.appendChild(badge);
        }
        
        if (state.filters.team !== 'all') {
            const badge = createMobileFilterBadge('team', state.filters.team);
            mobileFiltersContainer.appendChild(badge);
        }
    }
    
    // Create mobile filter badge
    function createMobileFilterBadge(type, text) {
        const badge = document.createElement('div');
        badge.className = 'mobile-filter-badge';
        badge.innerHTML = `
            <span>${text}</span>
            <button class="badge-remove" data-filter-type="${type}" aria-label="Remove ${type} filter">
                <i class="fas fa-times-circle"></i>
            </button>
        `;
        
        // Add click handler to remove filter
        badge.querySelector('.badge-remove').addEventListener('click', (e) => {
            e.stopPropagation();
            removeFilter(type);
            
            // Update select values in mobile drawer
            const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
            const mobileTeamFilter = document.getElementById('mobileTeamFilter');
            
            if (type === 'league' && mobileLeagueFilter) {
                mobileLeagueFilter.value = 'all';
            } else if (type === 'team' && mobileTeamFilter) {
                mobileTeamFilter.value = 'all';
            }
            
            updateFilterCount();
        });
        
        return badge;
    }
    
    // Update the filter button click handler:
    filterButton.addEventListener('click', () => {
        drawer.classList.add('open');
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden'; 
        
        // Set current values using Select2 if available
        const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
        const mobileTeamFilter = document.getElementById('mobileTeamFilter');
        
        if (mobileLeagueFilter) {
            if ($(mobileLeagueFilter).hasClass('select2-hidden-accessible')) {
                $(mobileLeagueFilter).val(state.filters.league).trigger('change');
            } else {
                mobileLeagueFilter.value = state.filters.league;
            }
        }
        
        if (mobileTeamFilter) {
            if ($(mobileTeamFilter).hasClass('select2-hidden-accessible')) {
                $(mobileTeamFilter).val(state.filters.team).trigger('change');
            } else {
                mobileTeamFilter.value = state.filters.team;
            }
        }
        
        // Update mobile active filters
        updateMobileActiveFilters();
    });
    
    document.querySelector('.drawer-close').addEventListener('click', () => {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    });
    
    overlay.addEventListener('click', () => {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    });
        
document.getElementById('applyMobileFilters').addEventListener('click', () => {
    // Update state with mobile filter values using Select2
    const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
    const mobileTeamFilter = document.getElementById('mobileTeamFilter');

    // Always use .val() if Select2 is initialized
    if (mobileLeagueFilter && $(mobileLeagueFilter).hasClass('select2-hidden-accessible')) {
        state.filters.league = $(mobileLeagueFilter).val();
    } else if (mobileLeagueFilter) {
        state.filters.league = mobileLeagueFilter.value;
    }

    if (mobileTeamFilter && $(mobileTeamFilter).hasClass('select2-hidden-accessible')) {
        state.filters.team = $(mobileTeamFilter).val();
    } else if (mobileTeamFilter) {
        state.filters.team = mobileTeamFilter.value;
    }

    // Sync with main filters
    if (DOM.leagueFilter) {
        DOM.leagueFilter.value = state.filters.league;
        if ($(DOM.leagueFilter).hasClass('select2-hidden-accessible')) {
            $(DOM.leagueFilter).trigger('change');
        }
    }
    if (DOM.teamFilter) {
        DOM.teamFilter.value = state.filters.team;
        if ($(DOM.teamFilter).hasClass('select2-hidden-accessible')) {
            $(DOM.teamFilter).trigger('change');
        }
    }

    // Apply filters
    applyFilters();

    // Close drawer
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    document.body.style.overflow = '';

    // Update filter count
    updateFilterCount();
});
    
    // Clear filters button - update to work with Select2
    document.getElementById('clearMobileFilters').addEventListener('click', () => {
        // Reset mobile filters using Select2 if available
        const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
        const mobileTeamFilter = document.getElementById('mobileTeamFilter');
        
        if (mobileLeagueFilter) {
            if ($(mobileLeagueFilter).hasClass('select2-hidden-accessible')) {
                $(mobileLeagueFilter).val('all').trigger('change');
            } else {
                mobileLeagueFilter.value = 'all';
            }
        }
        
        if (mobileTeamFilter) {
            if ($(mobileTeamFilter).hasClass('select2-hidden-accessible')) {
                $(mobileTeamFilter).val('all').trigger('change');
            } else {
                mobileTeamFilter.value = 'all';
            }
        }
        
        // Reset state
        state.filters.league = 'all';
        state.filters.team = 'all';
        state.filters.date = null;
        
        // Sync with main filters
        if (DOM.leagueFilter) {
            DOM.leagueFilter.value = 'all';
            if ($(DOM.leagueFilter).hasClass('select2-hidden-accessible')) {
                $(DOM.leagueFilter).trigger('change');
            }
        }
        if (DOM.teamFilter) {
            DOM.teamFilter.value = 'all';
            if ($(DOM.teamFilter).hasClass('select2-hidden-accessible')) {
                $(DOM.teamFilter).trigger('change');
            }
        }
        
        // Update UI
        updateMobileActiveFilters();
        updateFilterCount();
        
        // Load all games
        loadAllGames();
        
        // Close drawer
        drawer.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    });
    
    // Clear filters button
    document.getElementById('clearMobileFilters').addEventListener('click', () => {
        // Reset mobile filters
        const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
        const mobileTeamFilter = document.getElementById('mobileTeamFilter');
        
        if (mobileLeagueFilter) mobileLeagueFilter.value = 'all';
        if (mobileTeamFilter) mobileTeamFilter.value = 'all';
        
        // Reset state
        state.filters.league = 'all';
        state.filters.team = 'all';
        state.filters.date = null;
        
        // Sync with main filters
        if (DOM.leagueFilter) DOM.leagueFilter.value = 'all';
        if (DOM.teamFilter) DOM.teamFilter.value = 'all';
        
        // Update UI
        updateMobileActiveFilters();
        updateFilterCount();
        
        // Load all games
        loadAllGames();
        
        // Close drawer
        drawer.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    });
    
    // Jump to date when selected in mobile drawer
    if (mobileDateFilter && mobileDateFilter._flatpickr) {
        mobileDateFilter._flatpickr.config.onChange.push(function(selectedDates) {
            if (selectedDates.length > 0) {
                jumpToDate(selectedDates[0]);
                
                // Close drawer
                drawer.classList.remove('open');
                overlay.classList.remove('open');
                document.body.style.overflow = '';
            }
        });
    }
    
    // Initialize filter count
    updateFilterCount();
    
    // Update filter count when filters change
    updateClearButton = (function(original) {
        return function() {
            original.call(this);
            if (typeof updateFilterCount === 'function') {
                updateFilterCount();
            }
        };
    })(updateClearButton);

    // More reliable method to populate filters after Select2 initialization
    function populateMobileFilters() {
        //console.log('Populating mobile filters');
        
        // Get references to the mobile filter elements
        const mobileLeagueFilter = document.getElementById('mobileLeagueFilter');
        const mobileTeamFilter = document.getElementById('mobileTeamFilter');
        
        if (!mobileLeagueFilter || !mobileTeamFilter) {
            console.error('Mobile filters not found in the DOM');
            return;
        }
        
        // Clear existing options
        mobileLeagueFilter.innerHTML = '<option value="all">All Leagues</option>';
        mobileTeamFilter.innerHTML = '<option value="all">All Teams</option>';
        
        // Use state data instead of cloning from DOM
        if (state.leagues && state.leagues.length > 0) {
            //console.log(`Populating ${state.leagues.length} leagues in mobile filter`);
            state.leagues.forEach(league => {
                const option = document.createElement('option');
                option.value = league;
                option.textContent = getLeagueDisplayName(league);
                mobileLeagueFilter.appendChild(option);
            });
        } else {
            //console.warn('No leagues in state to populate mobile filter');
        }
        
        if (state.teams && state.teams.length > 0) {
            //console.log(`Populating ${state.teams.length} teams in mobile filter`);
            state.teams.sort().forEach(team => {
                const option = document.createElement('option');
                option.value = team;
                option.textContent = team;
                mobileTeamFilter.appendChild(option);
            });
        } else {
            //console.warn('No teams in state to populate mobile filter');
        }
        
        //console.log(`Mobile filters populated. League options: ${mobileLeagueFilter.options.length}, Team options: ${mobileTeamFilter.options.length}`);
    }
    
    // Listen for teams and leagues loading events
    document.addEventListener('teamsLoaded', function(event) {
        //console.log('Teams loaded event received, updating mobile filters');
        // Update state with the loaded teams
        if (event.detail && event.detail.teams) {
            state.teams = event.detail.teams;
        }
        populateMobileFilters();
    });
    
    document.addEventListener('leaguesLoaded', function(event) {
        //console.log('Leagues loaded event received, updating mobile filters');
        // Update state with the loaded leagues
        if (event.detail && event.detail.leagues) {
            state.leagues = event.detail.leagues;
        }
        populateMobileFilters();
    });
    
    // Listen for Select2 initialization to repopulate
    document.addEventListener('select2Initialized', function() {
        // console.log('Select2 initialized event received, updating mobile filters');
        populateMobileFilters();
    });
    
    // Initial attempt at population
    setTimeout(() => {
        populateMobileFilters();
    }, 500);
}

// Load all upcoming games
async function loadAllGames() {
    // Show enhanced loading
    DOM.scheduleLoading.classList.remove('d-none');
    DOM.scheduleLoading.innerHTML = `
        <div class="enhanced-loading">
            <div class="loading-ball"></div>
            <div class="loading-shadow"></div>
            <div class="loading-text">Loading Schedule</div>
        </div>
    `;
    DOM.scheduleResults.classList.add('d-none');
    DOM.noSchedule.classList.add('d-none');
    
    try {
        // Use the imported service function instead of direct fetch
        const data = await fetchAvailableDates();
        
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
        
        return data; // Return data to allow for proper async await chain
        
    } catch (error) {
        console.error('Error loading games:', error);
        showNoGames();
        throw error; // Rethrow to allow for proper error handling
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
    if (window.innerWidth >= 768) {
        state.filters.league = DOM.leagueFilter.value;
        state.filters.team = DOM.teamFilter.value;
    }
    
    // Show active filters if any
    updateClearButton();
    
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
            // console.log(`Fetching schedule for team: ${teamName}`);
            
            // Use dedicated API endpoint for team schedules
            const teamData = await fetchTeamSchedule(teamName);
            // console.log('Team schedule data structure:', JSON.stringify(teamData, null, 2));
            
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
        showNoGames();
    }
}

// Update clear button visibility and active filters display
function updateClearButton() {
    const clearButton = document.getElementById('clearFilters');
    const { league, team } = state.filters;
    
    // Check if any filters are active
    const hasActiveFilters = (league !== 'all') || (team !== 'all');
    
    if (clearButton) {
        if (hasActiveFilters) {
            clearButton.classList.remove('d-none');
        } else {
            clearButton.classList.add('d-none');
        }
    }
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
    // Reset filter dropdowns
    DOM.leagueFilter.value = 'all';
    DOM.teamFilter.value = 'all';
    
    // Trigger change events if using Select2
    if (window.$ && $(DOM.leagueFilter).hasClass('select2-hidden-accessible')) {
        $(DOM.leagueFilter).trigger('change');
    }
    if (window.$ && $(DOM.teamFilter).hasClass('select2-hidden-accessible')) {
        $(DOM.teamFilter).trigger('change');
    }
    
    // Reset state
    state.filters = {
        league: 'all',
        team: 'all',
        date: null
    };
    
    // Hide clear button
    updateClearButton();
    
    // Reload all games
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
    
    // console.log(`Jumping to date: ${apiDateStr} - Year: ${year}, Month: ${month}, Day: ${day}`);
    
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
        // console.log(`Found exact match for date: ${apiDateStr}`);
        // We found the exact date - scroll to it
        dateElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        return;
    }
    
    // console.log(`No exact match found for ${apiDateStr}, looking for closest date`);
    
    // If we don't have the exact date, find the closest date
    const allDateSections = document.querySelectorAll('.date-section[id^="date-"]');
    if (allDateSections.length === 0) {
        // No dates available, show a message
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
    
    // console.log(`Looking for closest date to ${apiDateStr} among ${dates.length} available dates`);
    
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
        return;
    }
    
    // console.log(`Closest date found: ${closest.dateStr} (${closest.dateParts.year}-${closest.dateParts.month}-${closest.dateParts.day})`);
    
    // Scroll to the closest date
    closest.element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    

    // Show a message if it's not the exact date
    if (closest.dateStr !== apiDateStr) {
        const closestFormatted = closest.date.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long', 
            day: 'numeric'
        });
        
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
    // Add enhanced loading indicator
    container.innerHTML = `
        <div class="date-loading">
            <div class="loading-pulse">
                <div class="loading-card"></div>
                <div class="loading-line"></div>
                <div class="loading-line short"></div>
            </div>
        </div>
    `;
    
    // Check if we have a team filter active and we have currentTeamData cached
    const { team } = state.filters;
    if (team !== 'all' && window.currentTeamData) {
        // console.log('Using cached team data for date:', dateStr);
        
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
        
        // console.log('Looking for matches on date:', searchDateStr);
        
        // Look for matches on this date in the cached team data
        const matchesForDate = window.currentTeamData.matches.filter(match => {
            return match.date === searchDateStr;
        });
        
        const tbdMatchesForDate = window.currentTeamData.tbd_matches.filter(match => {
            return match.date === searchDateStr;
        });
        
        // Log what we found for debugging
        // console.log(`Found ${matchesForDate.length} regular matches and ${tbdMatchesForDate.length} TBD matches for ${searchDateStr}`);
        
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
                leagueSection.appendChild(gameCard);
            });
            
            container.appendChild(leagueSection);
        }
    } else {
        // Fetch games for this date normally if no team filter or no cached data
        fetchGamesByDate(dateStr)
            .then(data => { // Remove the response.json() step - data is already parsed
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

    // Ensure game time is never undefined or null in display
    let displayTime = 'TBD';
    if (game.time && game.time !== 'null' && game.time.trim() !== '') {
        displayTime = game.time;
    }

    if (displayTime === 'TBD') {
        card.classList.add('tbd-game');
    }

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body py-3';

    // --- FLEX ROW LAYOUT ---
    const row = document.createElement('div');
    row.className = 'game-row d-flex align-items-center';

    // Time box (left, desktop only)
    const timeBox = document.createElement('div');
    timeBox.className = `match-time-box${displayTime === 'TBD' ? ' text-muted fst-italic' : ''} desktop-time-display`;
    timeBox.textContent = displayTime;

    // Teams (center)
    const teams = document.createElement('div');
    teams.className = 'match-teams flex-grow-1 d-flex align-items-center justify-content-center';
    teams.innerHTML = `
        <div class="home-team d-flex align-items-center">
            <span class="team-name me-1">${homeTeam}</span>
            <img src="${getTeamLogoUrl(homeTeam)}" alt="${homeTeam}" class="team-badge ms-1">
        </div>
        <div class="vs-container px-2">
            <span class="vs">vs</span>
        </div>
        <div class="away-team d-flex align-items-center">
            <img src="${getTeamLogoUrl(awayTeam)}" alt="${awayTeam}" class="team-badge me-1">
            <span class="team-name ms-1">${awayTeam}</span>
        </div>
    `;

    // Ticket link for home team
    const homeTeamTicketUrl = TEAM_TICKET_LINKS?.[homeTeam] || null;
    const ticketBtnHTML = homeTeamTicketUrl ? `
        <a href="${homeTeamTicketUrl}" target="_blank" rel="noopener" class="ticket-link-btn ms-2 d-inline-flex align-items-center"
            title="Buy tickets for ${homeTeam}" style="gap:4px;text-decoration:none;color:inherit;">
            <i class="fas fa-ticket-alt"></i>
            <span>Tickets</span>
            <i class="fas fa-arrow-up-right-from-square" style="font-size:0.95em;margin-left:2px;"></i>
        </a>
    ` : '';

    // Location (right, desktop only)
    const locationBox = document.createElement('div');
    locationBox.className = 'match-location-box text-end desktop-location-display';
    locationBox.innerHTML = `
        <i class="fas fa-map-marker-alt me-1"></i>
        <span>${formatCityForDisplay(game.display_location || game.location)}</span>
    `;

    // Chevron for mobile expand/collapse
    const chevron = document.createElement('div');
    chevron.className = 'mobile-chevron d-md-none ms-2';
    chevron.innerHTML = `<i class="fas fa-chevron-down"></i>`;

    // Ticket link for home team (desktop only)
    const ticketBtnDesktop = document.createElement('div');
    ticketBtnDesktop.className = 'ticket-link-desktop d-none d-md-flex align-items-center ms-2';
    if (homeTeamTicketUrl) {
        ticketBtnDesktop.innerHTML = `
            <a href="${homeTeamTicketUrl}" target="_blank" rel="noopener" class="ticket-link-btn d-inline-flex align-items-center"
                title="Buy tickets for ${homeTeam}" style="gap:4px;text-decoration:none;color:inherit;">
                <i class="fas fa-ticket-alt"></i>
                <span>Tickets</span>
                <i class="fas fa-arrow-up-right-from-square" style="font-size:0.95em;margin-left:2px;"></i>
            </a>
        `;
    }
    
    // Assemble row: time, ticket, teams, location, chevron
    row.appendChild(timeBox);
    if (homeTeamTicketUrl) row.appendChild(ticketBtnDesktop);
    row.appendChild(teams);
    row.appendChild(locationBox);
    row.appendChild(chevron);
    // Details dropdown (mobile only)
    const details = document.createElement('div');
    details.className = 'match-details-section';
    details.innerHTML = `
        <div class="match-details-content">
            <div class="match-time-detail">
                <i class="fas fa-clock me-2"></i>
                <span>${displayTime}</span>
            </div>
            <div class="match-location-detail">
                <i class="fas fa-map-marker-alt me-2"></i>
                <span>${formatCityForDisplay(game.display_location || game.location)}</span>
            </div>
            ${homeTeamTicketUrl ? `
            <div class="match-ticket-detail mt-2">
                <a href="${homeTeamTicketUrl}" target="_blank" rel="noopener" class="ticket-link-btn d-inline-flex align-items-center"
                    title="Buy tickets for ${homeTeam}" style="gap:4px;text-decoration:none;color:inherit;">
                    <i class="fas fa-ticket-alt"></i>
                    <span>Tickets</span>
                    <i class="fas fa-arrow-up-right-from-square" style="font-size:0.95em;margin-left:2px;"></i>
                </a>
            </div>
            ` : ''}
        </div>
    `;

    // Hide details by default on mobile
    details.style.display = 'none';

    // Toggle dropdown on row click (mobile only)
    row.addEventListener('click', function (e) {
        // Only trigger on mobile
        if (window.innerWidth < 768) {
            e.stopPropagation();
            const isOpen = details.style.display === 'block';
            details.style.display = isOpen ? 'none' : 'block';
            chevron.querySelector('i').classList.toggle('fa-chevron-down', isOpen);
            chevron.querySelector('i').classList.toggle('fa-chevron-up', !isOpen);
        }
    });

    cardBody.appendChild(row);
    cardBody.appendChild(details);
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
                
                // console.log(`DateView: Comparing [${homeTeam}] or [${awayTeam}] with filter [${team}]`);
                return homeTeam === team || awayTeam === team;
            });
            
            // Skip this league if no games match the team filter
            if (filteredGames.length === 0) {
                // console.log(`DateView: No games in ${league} match team filter: ${team}`);
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
    
    // Create header with improved mobile layout
    const teamHeader = document.createElement('div');
    teamHeader.className = 'team-header mb-4 pb-2 border-bottom';
    teamHeader.innerHTML = `
        <div class="d-flex flex-column flex-md-row">
            <div class="d-flex align-items-center mb-2 mb-md-0">
                <img src="${getTeamLogoUrl(teamName)}" class="me-3" width="48" height="48" alt="${teamName}" 
                    style="width: 48px; height: 48px; object-fit: contain;">
                <h2 class="h3 mb-0">${teamName}</h2>
            </div>
            <div class="d-flex flex-wrap gap-2 ms-md-auto mt-2 mt-md-0 align-items-md-center">
                <span class="badge bg-primary rounded-pill fs-7">${teamData.total_matches} Total</span>
                <span class="badge bg-success rounded-pill fs-7">${teamData.matches.length} Scheduled</span>
                <span class="badge bg-warning text-dark rounded-pill fs-7">${teamData.tbd_matches.length} TBD</span>
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
                    // Use the standard game card function instead of custom HTML
                    const game = {
                        match: match.is_home ? 
                            `${teamName} vs ${match.opponent}` : 
                            `${match.opponent} vs ${teamName}`,
                        time: match.time || 'TBD',
                        location: match.location,
                        display_location: match.display_location || match.location,
                        league: match.league
                    };
                    
                    const gameCard = createGameCard(game);
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