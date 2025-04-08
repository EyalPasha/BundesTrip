import { clearFilters } from './ui-helpers.js';
import { renderNextBatch } from '../components/results-display.js';
import { getTeamLogoUrl } from './team-logos.js';

// Global state to track active filters
const activeFilters = {
  team: null,
  city: null,
  minGames: 1,
  maxHotelChanges: 7
};

// Temporary filter state for the drawer - only applied when Apply button is clicked
const pendingFilters = {
  team: null,
  city: null,
  minGames: 1,
  maxHotelChanges: 7
};

// Make filter state globally available for newly loaded trips
window.activeFilters = activeFilters;

// DOM elements for the filter drawer
let filterButton;
let filterCount;
let drawerOverlay;
let filterDrawer;

// Initialize the filter drawer UI
function initFilterDrawer() {
    // Remove any existing filter elements from the DOM first
    const existingFilterBtn = document.querySelector('.filter-btn');
    const existingFilterDrawer = document.querySelector('.filter-drawer');
    const existingOverlay = document.querySelector('.drawer-overlay');
    
    if (existingFilterBtn) existingFilterBtn.remove();
    if (existingFilterDrawer) existingFilterDrawer.remove();
    if (existingOverlay) existingOverlay.remove();
    
    // Create filter button
    filterButton = document.createElement('button');
    filterButton.className = 'filter-btn';
    filterButton.innerHTML = '<i class="fas fa-filter"></i>';
    filterButton.setAttribute('aria-label', 'Filter trips');
    
    // Add filter count badge
    filterCount = document.createElement('span');
    filterCount.className = 'filter-count';
    filterCount.textContent = '0';
    filterButton.appendChild(filterCount);
    
    // Create overlay
    drawerOverlay = document.createElement('div');
    drawerOverlay.className = 'drawer-overlay';
    
    // Create drawer
    filterDrawer = document.createElement('div');
    filterDrawer.className = 'filter-drawer';
    filterDrawer.innerHTML = `
        <div class="drawer-header">
            <h3 class="drawer-title">Filter Trips</h3>
            <button class="drawer-close" aria-label="Close filter menu">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="drawer-content">
            <div class="drawer-active-filters"></div>
            
            <div class="drawer-filter-group">
                <label class="drawer-filter-label">
                    <i class="fas fa-futbol me-2"></i> Team Filters
                </label>
                <div id="drawerTeamFilters" class="mb-3"></div>
            </div>
            
            <div class="drawer-filter-group">
                <label class="drawer-filter-label">
                    <i class="fas fa-map-marker-alt me-2"></i> City Filters
                </label>
                <div id="drawerCityFilters" class="mb-3"></div>
            </div>
            
            <div class="drawer-filter-group filter-slider-group">
                <div class="filter-slider-header">
                    <label class="filter-slider-label" for="drawerGamesSlider">
                        <i class="fas fa-futbol me-1"></i> Minimum Games
                    </label>
                    <span class="filter-slider-value" id="drawerGamesSliderValue">Any</span>
                </div>
                <input type="range" class="form-range" min="1" max="6" value="1" id="drawerGamesSlider">
            </div>
            
            <div class="drawer-filter-group filter-slider-group">
                <div class="filter-slider-header">
                    <label class="filter-slider-label" for="drawerHotelChangesSlider">
                        <i class="fas fa-hotel me-1"></i> Max Hotel Changes
                    </label>
                    <span class="filter-slider-value" id="drawerHotelChangesValue">Any</span>
                </div>
                <input type="range" class="form-range" min="0" max="7" value="7" id="drawerHotelChangesSlider">
            </div>
        </div>
        <div class="drawer-actions">
            <button class="btn btn-outline-secondary" id="clearDrawerFilters">
                <i class="fas fa-times me-2"></i> Clear All
            </button>
            <button class="btn btn-primary" id="applyDrawerFilters">
                <i class="fas fa-check me-2"></i> Apply Filters
            </button>
        </div>
    `;
    
    // Add elements to the document
    document.body.appendChild(filterButton);
    document.body.appendChild(drawerOverlay);
    document.body.appendChild(filterDrawer);
    
    // Add has-filter-drawer class to body
    document.body.classList.add('has-filter-drawer');
    
    // Add event listeners
    filterButton.addEventListener('click', openFilterDrawer);
    drawerOverlay.addEventListener('click', closeFilterDrawer);
    filterDrawer.querySelector('.drawer-close').addEventListener('click', closeFilterDrawer);
    document.getElementById('clearDrawerFilters').addEventListener('click', clearDrawerFilters);
    document.getElementById('applyDrawerFilters').addEventListener('click', applyAndCloseDrawer);
    
    // Set up slider event listeners to update pending filters, not active ones
    const drawerGamesSlider = document.getElementById('drawerGamesSlider');
    const drawerGamesSliderValue = document.getElementById('drawerGamesSliderValue');
    
    drawerGamesSlider.addEventListener('input', function() {
        const value = parseInt(this.value);
        if (value === 1) {
            drawerGamesSliderValue.textContent = 'Any';
        } else {
            drawerGamesSliderValue.textContent = `${value}+`;
        }
        
        if (value === parseInt(drawerGamesSlider.max)) {
            drawerGamesSliderValue.textContent = value;
        }
        
        // Update pending filter state
        pendingFilters.minGames = value;
        
        // Update drawer active filters display
        updateDrawerActiveFilters();
    });
    
    const drawerHotelChangesSlider = document.getElementById('drawerHotelChangesSlider');
    const drawerHotelChangesValue = document.getElementById('drawerHotelChangesValue');
    
    drawerHotelChangesSlider.addEventListener('input', function() {
        const value = parseInt(this.value);
        if (value === parseInt(drawerHotelChangesSlider.max)) {
            drawerHotelChangesValue.textContent = 'Any';
        } else {
            drawerHotelChangesValue.textContent = value;
        }
        
        // Update pending filter state
        pendingFilters.maxHotelChanges = value;
        
        // Update drawer active filters display
        updateDrawerActiveFilters();
    });
    
    // Update filter count based on active filters (not pending)
    updateFilterCount();
}

// Open the filter drawer
function openFilterDrawer() {
    // Initialize pending filters with current active values
    pendingFilters.team = activeFilters.team;
    pendingFilters.city = activeFilters.city;
    pendingFilters.minGames = activeFilters.minGames;
    pendingFilters.maxHotelChanges = activeFilters.maxHotelChanges;
    
    // Sync drawer filters with active filters
    syncFiltersToDrawer();
    
    // Show drawer and overlay
    filterDrawer.classList.add('open');
    drawerOverlay.classList.add('open');
    document.body.style.overflow = 'hidden'; // Prevent scrolling
}

// Close the filter drawer
function closeFilterDrawer() {
    filterDrawer.classList.remove('open');
    drawerOverlay.classList.remove('open');
    document.body.style.overflow = '';
}

// Apply filters and close the drawer
function applyAndCloseDrawer() {
    // Copy pending filter state to active filters
    activeFilters.team = pendingFilters.team;
    activeFilters.city = pendingFilters.city;
    activeFilters.minGames = pendingFilters.minGames;
    activeFilters.maxHotelChanges = pendingFilters.maxHotelChanges;
    
    // Update UI to reflect changes
    // 1. Update slider values in the main UI if they exist
    const mainGamesSlider = document.getElementById('gamesSlider');
    const mainGamesSliderValue = document.getElementById('gamesSliderValue');
    
    if (mainGamesSlider && mainGamesSliderValue) {
        mainGamesSlider.value = activeFilters.minGames;
        if (activeFilters.minGames === 2) {
            mainGamesSliderValue.textContent = 'Any (2+)';
        } else if (activeFilters.minGames === parseInt(mainGamesSlider.max)) {
            mainGamesSliderValue.textContent = activeFilters.minGames;
        } else {
            mainGamesSliderValue.textContent = `${activeFilters.minGames}+`;
        }
    }
    
    const mainHotelChangesSlider = document.getElementById('hotelChangesSlider');
    const mainHotelChangesValue = document.getElementById('hotelChangesValue');
    
    if (mainHotelChangesSlider && mainHotelChangesValue) {
        mainHotelChangesSlider.value = activeFilters.maxHotelChanges;
        if (activeFilters.maxHotelChanges === parseInt(mainHotelChangesSlider.max)) {
            mainHotelChangesValue.textContent = 'Any';
        } else {
            mainHotelChangesValue.textContent = activeFilters.maxHotelChanges;
        }
    }
    
    // Update team and city filter UI in the main view
    updateTeamFilterUI();
    updateCityFilterUI();
    
    // Apply filters to the data
    applyAllFilters();
    
    // Close drawer
    closeFilterDrawer();
    
    // Update filter count badge
    updateFilterCount();
    
    // Dispatch event
    dispatchFilterChangeEvent();
}

// Sync main filters to drawer
function syncFiltersToDrawer() {
    // Set pending filters to match active filters
    pendingFilters.team = activeFilters.team;
    pendingFilters.city = activeFilters.city;
    pendingFilters.minGames = activeFilters.minGames;
    pendingFilters.maxHotelChanges = activeFilters.maxHotelChanges;
    
    // Update drawer UI
    updateDrawerTeamFilters();
    updateDrawerCityFilters();
    
    // Update sliders
    const drawerGamesSlider = document.getElementById('drawerGamesSlider');
    const drawerGamesSliderValue = document.getElementById('drawerGamesSliderValue');
    
    if (drawerGamesSlider && drawerGamesSliderValue) {
        drawerGamesSlider.value = pendingFilters.minGames;
        if (pendingFilters.minGames === 1) {
            drawerGamesSliderValue.textContent = 'Any';
        } else {
            drawerGamesSliderValue.textContent = `${pendingFilters.minGames}+`;
        }
        
        if (pendingFilters.minGames === parseInt(drawerGamesSlider.max)) {
            drawerGamesSliderValue.textContent = pendingFilters.minGames;
        }
    }
    
    const drawerHotelChangesSlider = document.getElementById('drawerHotelChangesSlider');
    const drawerHotelChangesValue = document.getElementById('drawerHotelChangesValue');
    
    if (drawerHotelChangesSlider && drawerHotelChangesValue) {
        drawerHotelChangesSlider.value = pendingFilters.maxHotelChanges;
        if (pendingFilters.maxHotelChanges === parseInt(drawerHotelChangesSlider.max)) {
            drawerHotelChangesValue.textContent = 'Any';
        } else {
            drawerHotelChangesValue.textContent = pendingFilters.maxHotelChanges;
        }
    }
    
    // Update active filters display in drawer
    updateDrawerActiveFilters();
}

// Update active filters display in drawer
function updateDrawerActiveFilters() {
    const activeFiltersContainer = document.querySelector('.drawer-active-filters');
    if (!activeFiltersContainer) return;
    
    activeFiltersContainer.innerHTML = '';
    
    let hasActiveFilters = false;
    
    // Add team filter badge
    if (pendingFilters.team) {
        const badge = createDrawerFilterBadge('team', pendingFilters.team);
        activeFiltersContainer.appendChild(badge);
        hasActiveFilters = true;
    }
    
    // Add city filter badge
    if (pendingFilters.city) {
        const badge = createDrawerFilterBadge('city', pendingFilters.city);
        activeFiltersContainer.appendChild(badge);
        hasActiveFilters = true;
    }
    
    // Add min games filter badge - only show if above the min of 2
    if (pendingFilters.minGames > 2) {
        const badge = createDrawerFilterBadge('minGames', `${pendingFilters.minGames}+ games`);
        activeFiltersContainer.appendChild(badge);
        hasActiveFilters = true;
    }
    
    // Add hotel changes filter badge
    if (pendingFilters.maxHotelChanges < 7) {
        const badge = createDrawerFilterBadge('maxHotelChanges', `Max ${pendingFilters.maxHotelChanges} hotel changes`);
        activeFiltersContainer.appendChild(badge);
        hasActiveFilters = true;
    }
    
    // Show or hide the active filters section
    if (hasActiveFilters) {
        activeFiltersContainer.style.display = 'flex';
    } else {
        activeFiltersContainer.style.display = 'none';
    }
}

// Create filter badge for drawer
function createDrawerFilterBadge(type, text) {
    const badge = document.createElement('div');
    badge.className = 'drawer-filter-badge';
    badge.innerHTML = `
        <span>${text}</span>
        <button class="badge-remove" data-filter-type="${type}" aria-label="Remove ${type} filter">
            <i class="fas fa-times-circle"></i>
        </button>
    `;
    
    // Add click handler to remove filter in pending state only
    badge.querySelector('.badge-remove').addEventListener('click', (e) => {
        e.stopPropagation();
        
        if (type === 'team') {
            pendingFilters.team = null;
        } else if (type === 'city') {
            pendingFilters.city = null;
        } else if (type === 'minGames') {
            pendingFilters.minGames = 1;
            document.getElementById('drawerGamesSlider').value = 1;
            document.getElementById('drawerGamesSliderValue').textContent = 'Any';
        } else if (type === 'maxHotelChanges') {
            pendingFilters.maxHotelChanges = 7;
            document.getElementById('drawerHotelChangesSlider').value = 7;
            document.getElementById('drawerHotelChangesValue').textContent = 'Any';
        }
        
        // Update drawer UI only
        updateDrawerActiveFilters();
        updateDrawerTeamFilterUI();
        updateDrawerCityFilterUI();
    });
    
    return badge;
}

// Update team filters in the drawer
function updateDrawerTeamFilters() {
    const drawerTeamFilters = document.getElementById('drawerTeamFilters');
    if (!drawerTeamFilters) return;
    
    // Clear existing filters
    drawerTeamFilters.innerHTML = '';
    
    // Clone team filters from the main filters panel
    const teamFilters = document.getElementById('teamFilters');
    if (teamFilters) {
        const badges = teamFilters.querySelectorAll('.badge');
        badges.forEach(badge => {
            const clonedBadge = badge.cloneNode(true);
            
            // Update classes for active state if needed
            if (badge.dataset.team === pendingFilters.team) {
                clonedBadge.classList.remove('bg-light');
                clonedBadge.classList.remove('text-dark');
                clonedBadge.classList.add('bg-primary');
                clonedBadge.classList.add('text-white');
            }
            
            // Add click event for drawer (not immediate application)
            if (clonedBadge.dataset.team) {
                clonedBadge.addEventListener('click', () => drawerFilterByTeam(clonedBadge.dataset.team));
            } else {
                // Clear button inside drawer
                clonedBadge.addEventListener('click', clearDrawerFilters);
            }
            
            drawerTeamFilters.appendChild(clonedBadge);
        });
    }
}

// Update city filters in the drawer
function updateDrawerCityFilters() {
    const drawerCityFilters = document.getElementById('drawerCityFilters');
    if (!drawerCityFilters) return;
    
    // Clear existing filters
    drawerCityFilters.innerHTML = '';
    
    // Clone city filters from the main filters panel
    const cityFilters = document.getElementById('cityFilters');
    if (cityFilters) {
        const badges = cityFilters.querySelectorAll('.badge');
        badges.forEach(badge => {
            const clonedBadge = badge.cloneNode(true);
            
            // Update classes for active state if needed
            if (badge.dataset.city === pendingFilters.city) {
                clonedBadge.classList.remove('bg-light');
                clonedBadge.classList.remove('text-dark');
                clonedBadge.classList.add('bg-primary');
                clonedBadge.classList.add('text-white');
            }
            
            // Add click event for drawer (not immediate application)
            if (clonedBadge.dataset.city) {
                clonedBadge.addEventListener('click', () => drawerFilterByCity(clonedBadge.dataset.city));
            } else {
                // Clear button inside drawer
                clonedBadge.addEventListener('click', clearDrawerFilters);
            }
            
            drawerCityFilters.appendChild(clonedBadge);
        });
    }
}

// Update filter count badge on the filter button
function updateFilterCount() {
    if (!filterCount) return;
    
    let count = 0;
    
    if (activeFilters.team) count++;
    if (activeFilters.city) count++;
    if (activeFilters.minGames > 2) count++;  // Only count if above default min of 2
    if (activeFilters.maxHotelChanges < 7) count++;
    
    filterCount.textContent = count;
    
    if (count > 0) {
        filterCount.classList.add('has-filters');
    } else {
        filterCount.classList.remove('has-filters');
    }
}

function filterByTeam(team) {
    const tripCards = document.querySelectorAll('.trip-card');
    
    // Update active filter state
    if (activeFilters.team === team) {
        // Clicking active filter clears it
        activeFilters.team = null;
    } else {
        activeFilters.team = team;
    }
    
    // Update UI for team filters
    updateTeamFilterUI();
    updateDrawerTeamFilters();
    
    // Update filter count badge
    updateFilterCount();
    
    // Update active filters display in drawer
    updateDrawerActiveFilters();
    
    // Apply all active filters
    applyAllFilters();
    
    // Dispatch event
    dispatchFilterChangeEvent();
}

function filterByCity(city) {
    const tripCards = document.querySelectorAll('.trip-card');
    
    // Update active filter state
    if (activeFilters.city === city) {
        // Clicking active filter clears it
        activeFilters.city = null;
    } else {
        activeFilters.city = city;
    }
    
    // Update UI for city filters
    updateCityFilterUI();
    updateDrawerCityFilters();
    
    // Update filter count badge
    updateFilterCount();
    
    // Update active filters display in drawer
    updateDrawerActiveFilters();
    
    // Apply all active filters
    applyAllFilters();
    
    // Dispatch event
    dispatchFilterChangeEvent();
}

// New function to filter by number of games
function filterByGames(minGames) {
    activeFilters.minGames = minGames;
    updateFilterCount();
    updateDrawerActiveFilters();
    applyAllFilters();
    
    // Dispatch event
    dispatchFilterChangeEvent();
}

// Add a new function to reorder trip options based on hotel changes
function reorderTripOptions(tripCard, maxHotelChanges, optionsInfo = null) {
    const tabButtons = tripCard.querySelectorAll('[data-bs-toggle="tab"]');
    const tabPanes = tripCard.querySelectorAll('.tab-pane');
    
    // Exit early if we don't have multiple options
    if (tabButtons.length <= 1) return;
    
    // Get reference to the itinerary container for this trip
    const dynamicItineraryContainer = tripCard.querySelector('.dynamic-itinerary-container');
    if (!dynamicItineraryContainer) return;
    
    // If optionsInfo wasn't provided, gather it now
    const options = optionsInfo || [];
    if (!optionsInfo) {
        tabButtons.forEach((button, idx) => {
            const optionPane = tabPanes[idx];
            const hotelChanges = extractHotelChanges(optionPane);
            
            // Extract travel time - this part looks correct
            let travelMinutes = 0;
            const statLabels = optionPane.querySelectorAll('.stat-label');
            
            for (let i = 0; i < statLabels.length; i++) {
                if (statLabels[i].textContent.includes('Total Travel')) {
                    const valueEl = statLabels[i].nextElementSibling;
                    if (valueEl && valueEl.classList.contains('stat-value')) {
                        const timeText = valueEl.textContent;
                        const hoursMatch = timeText.match(/(\d+)h/);
                        const minsMatch = timeText.match(/(\d+)m/);
                        
                        if (hoursMatch) travelMinutes += parseInt(hoursMatch[1]) * 60;
                        if (minsMatch) travelMinutes += parseInt(minsMatch[1]);
                    }
                }
            }
            
            options.push({
                button: button,
                pane: optionPane,
                hotelChanges: hotelChanges,
                travelMinutes: travelMinutes,
                isValid: hotelChanges <= maxHotelChanges,
                index: idx
            });
        });
    }
    
    // Get the trip group data stored as a data attribute 
    let tripGroupData;
    try {
        tripGroupData = JSON.parse(tripCard.dataset.tripGroup || '{}');
        if (!tripGroupData || Object.keys(tripGroupData).length === 0) {
            console.error('Missing trip group data in card');
            return;
        }
    } catch (err) {
        console.error('Failed to parse trip group data:', err);
        return;
    }
    
    // Sort options according to the specified logic
    const maxPossibleChanges = Math.max(...options.map(o => o.hotelChanges));
    if (maxHotelChanges >= maxPossibleChanges) {
        // Sort by travel time (fastest first)
        options.sort((a, b) => a.travelMinutes - b.travelMinutes);
    } else {
        // First show options that meet criteria, sorted by hotelChanges ascending
        // Then show options that exceed criteria, sorted by original position
        options.sort((a, b) => {
            // First separate valid from invalid options
            if (a.isValid && !b.isValid) return -1;
            if (!a.isValid && b.isValid) return 1;
            
            // For valid options, sort by hotel changes
            if (a.isValid && b.isValid) {
                return a.hotelChanges - b.hotelChanges;
            }
            
            // For invalid options, preserve original order
            return a.index - b.index;
        });
    }

    // Reorder the DOM elements
    const nav = tabButtons[0].parentNode;
    const content = tabPanes[0].parentNode;
    
    // Clear active state from all tabs
    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabPanes.forEach(pane => {
        pane.classList.remove('active');
        pane.classList.remove('show');
    });
    
    // Reattach in the new order
    options.forEach(option => {
        nav.appendChild(option.button);
        content.appendChild(option.pane);
    });
    
    // Activate the first valid option
    const firstValidOption = options.find(o => o.isValid);
    if (firstValidOption) {
        firstValidOption.button.classList.add('active');
        firstValidOption.pane.classList.add('active');
        firstValidOption.pane.classList.add('show');
        
        // Update the itinerary for the newly selected option
        const selectedVariantIndex = firstValidOption.index;
        
        // Ensure dynamic import completes and itinerary is updated
        import('../components/trip-card.js').then(module => {
            if (typeof module.renderItineraryForVariant === 'function') {
                // Important: Add a small delay to ensure the tab activation is complete
                setTimeout(() => {
                    try {
                        module.renderItineraryForVariant(dynamicItineraryContainer, tripGroupData, selectedVariantIndex);
                    } catch (error) {
                        console.error('Failed to render itinerary variant:', error);
                    }
                }, 50);
            }
        }).catch(err => {
            console.error('Failed to import trip-card module:', err);
        });
    }
    
    console.log('Trip options reordered:', {
        card: tripCard,
        options: options.map(o => ({
            index: o.index,
            hotelChanges: o.hotelChanges,
            isValid: o.isValid
        }))
    });
}

function filterByHotelChanges(maxChanges) {
    // Update the active filter state
    activeFilters.maxHotelChanges = maxChanges;
    
    // Update filter count badge
    updateFilterCount();
    
    // Update active filters display in drawer
    updateDrawerActiveFilters();
    
    // Create a counter to track how many cards we've processed
    let processedCards = 0;
    let totalVisibleCards = 0;
    
    console.log(`Applying hotel changes filter: max ${maxChanges} changes`);
    
    // IMPORTANT: Process each card first BEFORE applying all filters
    // This prevents timing issues with cards disappearing during processing
    document.querySelectorAll('.trip-card').forEach(card => {
        try {
            // Skip TBD games section which has a different structure
            if (card.id === 'tbdGamesSection') return;
            
            // Store the original display state
            const wasVisible = card.style.display !== 'none';
            if (wasVisible) totalVisibleCards++;
            
            // Process each card's options regardless of current visibility
            // This ensures all cards have their options properly ordered
            filterTripOptions(card);
            processedCards++;
        } catch (error) {
            console.error('Error processing trip card:', error, card);
        }
    });
    
    console.log(`Processed ${processedCards} out of ${totalVisibleCards} visible cards`);
    
    // NOW apply all filters after we've processed all cards
    // This will hide cards that don't meet other filter criteria
    applyAllFilters();
    
    // Add tab change listeners after filtering
    setTimeout(addTabChangeListeners, 100);
    
    // Dispatch event
    dispatchFilterChangeEvent();
}

// Update team filter UI
function updateTeamFilterUI() {
    document.querySelectorAll('#teamFilters .badge').forEach(badge => {
        if (badge.dataset.team === activeFilters.team) {
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
    
    // Also update drawer filter UI
    updateDrawerTeamFilters();
    updateFilterCount();
}

// Update city filter UI
function updateCityFilterUI() {
    document.querySelectorAll('#cityFilters .badge').forEach(badge => {
        if (badge.dataset.city === activeFilters.city) {
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
    
    // Also update drawer filter UI
    updateDrawerCityFilters();
    updateFilterCount();
}

// Update the applyAllFilters function in filters.js to preserve TBD games
function applyAllFilters() {
    // If we're using pagination, filter the original data
    if (window.tripResults && window.tripResults.allTrips) {
        // Filter the original data
        const allTrips = window.tripResults.originalTrips || window.tripResults.allTrips;
        
        // Store original trips if not already done
        if (!window.tripResults.originalTrips) {
            window.tripResults.originalTrips = [...allTrips];
        }
        
        // Apply filters to the data
        const filteredTrips = allTrips.filter(trip => {
            // Extract first variation for basic filtering
            const defaultVariant = trip.variation_details && trip.variation_details[0];
            
            if (!defaultVariant) return false;
            
            // Check team filter
            if (activeFilters.team) {
                const teams = defaultVariant.teams || [];
                if (!teams.includes(activeFilters.team)) return false;
            }
            
            // Check city filter
            if (activeFilters.city) {
                const cities = defaultVariant.cities || [];
                if (!cities.includes(activeFilters.city)) return false;
            }
            
            // Check number of games filter
            if (activeFilters.minGames > 1) {
                if ((defaultVariant.num_games || 0) < activeFilters.minGames) return false;
            }
            
            // For trips that pass the basic filters, we'll filter their variations later
            return true;
        });
        
        // Update the filtered trips array
        window.tripResults.allTrips = filteredTrips;
        window.tripResults.renderedCount = 0;
        window.tripResults.hasMoreTrips = filteredTrips.length > 0;
        
        // Get the results container
        const container = document.getElementById('tripResults');
        
        // IMPORTANT: Save the TBD games section before clearing the container
        const tbdSection = container ? container.querySelector('#tbdGamesSection') : null;
        
        // Clear the results container
        if (container) {
            container.innerHTML = '';
            
            // Re-add the TBD games section if it was found
            if (tbdSection) {
                container.appendChild(tbdSection);
            }
        }
        
        // Update count display
        const resultsCount = document.getElementById('resultsCount');
        if (resultsCount) {
            resultsCount.textContent = filteredTrips.length;
        }
        
        // Show a message when no trips match filters (but we have TBD games)
        if (filteredTrips.length === 0) {
            showNoFilterMatchesMessage(container, tbdSection !== null);
        } else {
            // Hide the no matches message if it exists
            hideNoFilterMatchesMessage();
        }
        
        // Re-render with the filtered data
        if (typeof renderNextBatch === 'function' && filteredTrips.length > 0) {
            renderNextBatch();
        }
    } else {
        // Legacy mode for non-paginated display
        const tripCards = document.querySelectorAll('.trip-card');
        let visibleCount = 0;
        
        tripCards.forEach(card => {
            // Skip the TBD games card which has a different structure
            if (card.id === 'tbdGamesSection') return;
            
            // Start assuming the card passes all filters
            let showCard = true;
            
            // Apply team filter
            if (activeFilters.team) {
                const cardTeams = card.dataset.teams.split(',');
                if (!cardTeams.includes(activeFilters.team)) showCard = false;
            }
            
            // Apply city filter
            if (showCard && activeFilters.city) {
                const cardCities = card.dataset.cities.split(',');
                if (!cardCities.includes(activeFilters.city)) showCard = false;
            }
            
            // Number of games filter
            if (showCard && activeFilters.minGames > 1) {
                const matchCountEl = card.querySelector('.match-count-badge');
                if (matchCountEl) {
                    const matchCount = parseInt(matchCountEl.textContent);
                    if (matchCount < activeFilters.minGames) showCard = false;
                }
            }
            
            // Apply visibility based on filters
            card.style.display = showCard ? 'block' : 'none';
            
            // Count visible trip cards
            if (showCard) visibleCount++;
            
            // Filter travel options based on hotel changes
            if (showCard && activeFilters.maxHotelChanges < 7) {
                filterTripOptions(card);
            }
        });
        
        // Show message if no trip cards are visible except possibly the TBD section
        const container = document.getElementById('tripResults');
        const tbdSection = container ? container.querySelector('#tbdGamesSection') : null;
        
        if (visibleCount === 0) {
            showNoFilterMatchesMessage(container, tbdSection !== null);
        } else {
            hideNoFilterMatchesMessage();
        }
    }
}

// New function to display a message when no trips match the filters
function showNoFilterMatchesMessage(container, hasTbdGames) {
    // Remove any existing no-matches message
    hideNoFilterMatchesMessage();
    
    // Don't add a message if we don't have a container
    if (!container) return;
    
    // Create the message element
    const noMatchesMessage = document.createElement('div');
    noMatchesMessage.id = 'noFilterMatchesMessage';
    noMatchesMessage.className = 'alert alert-info mt-4 text-center fade-in';
    
    // Different message depending on whether we have TBD games
    if (hasTbdGames) {
        noMatchesMessage.innerHTML = `
            <i class="fas fa-filter me-2"></i>
            <strong>No trips match your current filters</strong>
            <p class="mb-2 mt-2">Try adjusting your filters or check out the upcoming matches listed above.</p>
            <button class="btn btn-outline-primary btn-sm" id="resetFiltersBtn">
                <i class="fas fa-times me-1"></i> Reset Filters
            </button>
        `;
    } else {
        noMatchesMessage.innerHTML = `
            <i class="fas fa-filter me-2"></i>
            <strong>No trips match your current filters</strong>
            <p class="mb-2 mt-2">Please adjust your filter criteria and try again.</p>
            <button class="btn btn-outline-primary btn-sm" id="resetFiltersBtn">
                <i class="fas fa-times me-1"></i> Reset Filters
            </button>
        `;
    }
    
    // Add to the container after the TBD section (if it exists)
    const tbdSection = container.querySelector('#tbdGamesSection');
    if (tbdSection) {
        tbdSection.after(noMatchesMessage);
    } else {
        container.appendChild(noMatchesMessage);
    }
    
    // Add event listener to the reset button
    document.getElementById('resetFiltersBtn').addEventListener('click', clearFiltersEnhanced);
}

// Function to hide the no matches message
function hideNoFilterMatchesMessage() {
    const existingMessage = document.getElementById('noFilterMatchesMessage');
    if (existingMessage) {
        existingMessage.remove();
    }
}

// Filter travel options within a trip card
function filterTripOptions(tripCard) {
    const tabButtons = tripCard.querySelectorAll('[data-bs-toggle="tab"]');
    const tabPanes = tripCard.querySelectorAll('.tab-pane');
    
    // If there are no tab buttons or panes, this isn't a trip card with options
    if (!tabButtons.length || !tabPanes.length) return;
    
    let validOptionFound = false;
    const optionsInfo = [];
    
    // First pass: collect info about each option without hiding any yet
    tabButtons.forEach((button, idx) => {
        const optionPane = tabPanes[idx];
        const hotelChanges = extractHotelChanges(optionPane);
        
        // Store the hotel changes directly on the tab button for faster future access
        button.dataset.hotelChanges = hotelChanges;
        
        // Extract travel time information
        let travelMinutes = 0;
        try {
            const statLabels = optionPane.querySelectorAll('.stat-label');
            
            for (let i = 0; i < statLabels.length; i++) {
                if (statLabels[i].textContent.includes('Total Travel')) {
                    const valueEl = statLabels[i].nextElementSibling;
                    if (valueEl && valueEl.classList.contains('stat-value')) {
                        const timeText = valueEl.textContent;
                        const hoursMatch = timeText.match(/(\d+)h/);
                        const minsMatch = timeText.match(/(\d+)m/);
                        
                        if (hoursMatch) travelMinutes += parseInt(hoursMatch[1]) * 60;
                        if (minsMatch) travelMinutes += parseInt(minsMatch[1]);
                    }
                }
            }
        } catch (error) {
            console.warn('Error extracting travel time:', error);
        }
        
        // Track if this option is valid under current filter
        const isValid = hotelChanges <= activeFilters.maxHotelChanges;
        if (isValid) validOptionFound = true;
        
        // Store information about each option
        optionsInfo.push({
            button: button,
            pane: optionPane,
            hotelChanges: hotelChanges,
            travelMinutes: travelMinutes,
            index: idx,
            isValid: isValid
        });
    });
    
    // If no valid options found for this trip card, hide the entire card
    if (!validOptionFound) {
        tripCard.style.display = 'none';
        return;
    }
    
    // If we're here, show the card
    tripCard.style.display = 'block';
    
    // Now handle reordering the options according to specified rules
    reorderTripOptions(tripCard, activeFilters.maxHotelChanges, optionsInfo);
}

// Helper function to extract hotel changes from option pane - Fix the selector issue
function extractHotelChanges(optionPane) {
    if (!optionPane) return 0;
    
    // Method 1: Try to find explicit hotel changes in stat label
    const statLabels = optionPane.querySelectorAll('.stat-label');
    
    for (let i = 0; i < statLabels.length; i++) {
        if (statLabels[i].textContent.includes('Hotel Changes')) {
            const valueEl = statLabels[i].nextElementSibling;
            if (valueEl && valueEl.classList.contains('stat-value')) {
                const value = parseInt(valueEl.textContent) || 0;
                return value;
            }
        }
    }
    
    // Method 2: Try to count hotel stay items
    const hotelStayItems = optionPane.querySelectorAll('.hotel-stay-item');
    if (hotelStayItems.length > 0) {
        return Math.max(0, hotelStayItems.length - 1);  // Changes = stays - 1
    }
    
    // Method 3: Try to extract from the hotel-stays-section text
    const hotelSectionText = optionPane.textContent || '';
    const hotelChangesMatch = hotelSectionText.match(/Hotel Changes[:\s]*(\d+)/i);
    if (hotelChangesMatch && hotelChangesMatch[1]) {
        return parseInt(hotelChangesMatch[1]) || 0;
    }
    
    // Method 4: Check if there's a data attribute directly on the tab
    const tabId = optionPane.id;
    const tabButton = document.querySelector(`[data-bs-target="#${tabId}"]`);
    if (tabButton && tabButton.dataset.hotelChanges) {
        return parseInt(tabButton.dataset.hotelChanges) || 0;
    }
    
    // Method 5: Last resort - check the trip data directly
    try {
        const tripCard = optionPane.closest('.trip-card');
        if (tripCard && tripCard.dataset.tripGroup) {
            const tripData = JSON.parse(tripCard.dataset.tripGroup);
            const optionIndex = Array.from(tripCard.querySelectorAll('.tab-pane')).indexOf(optionPane);
            
            if (tripData && tripData.variation_details && tripData.variation_details[optionIndex]) {
                return tripData.variation_details[optionIndex].hotel_changes || 0;
            }
        }
    } catch (e) {
        console.warn('Error extracting hotel changes from trip data', e);
    }
    
    return 0; // Default if we can't find the information
}

// Add proper event listening for tab changes to update the itinerary
function addTabChangeListeners() {
    // Find all trip cards (not just filtered ones)
    document.querySelectorAll('.trip-card').forEach(card => {
        // Skip TBD games section
        if (card.id === 'tbdGamesSection') return;
        
        const tabButtons = card.querySelectorAll('[data-bs-toggle="tab"]');
        
        tabButtons.forEach(button => {
            // Store the hotel changes data attribute for faster access
            const targetId = button.getAttribute('data-bs-target');
            if (!targetId) return;
            
            const targetPane = document.querySelector(targetId);
            if (!targetPane) return;
            
            const hotelChanges = extractHotelChanges(targetPane);
            button.dataset.hotelChanges = hotelChanges;
            
            // Remove any existing listeners
            const newButton = button.cloneNode(true);
            if (button.parentNode) {
                button.parentNode.replaceChild(newButton, button);
            
                // Add new listener
                newButton.addEventListener('shown.bs.tab', function(event) {
                    const tabIndex = Array.from(tabButtons).indexOf(newButton);
                    const dynamicItineraryContainer = card.querySelector('.dynamic-itinerary-container');
                    
                    if (dynamicItineraryContainer && card.dataset.tripGroup && tabIndex >= 0) {
                        try {
                            const tripGroupData = JSON.parse(card.dataset.tripGroup);
                            
                            import('../components/trip-card.js').then(module => {
                                if (typeof module.renderItineraryForVariant === 'function') {
                                    module.renderItineraryForVariant(dynamicItineraryContainer, tripGroupData, tabIndex);
                                }
                            });
                        } catch (err) {
                            console.error('Failed to update itinerary on tab change:', err);
                        }
                    }
                });
            }
        });
    });
}

function clearFiltersEnhanced() {
    // Reset active filters state
    activeFilters.team = null;
    activeFilters.city = null;
    activeFilters.minGames = 2;  // Default to 2 games minimum
    activeFilters.maxHotelChanges = 7;
    
    // Reset UI elements
    document.querySelectorAll('#teamFilters .badge, #cityFilters .badge').forEach(badge => {
        if (badge.dataset.team || badge.dataset.city) {
            badge.classList.add('bg-light');
            badge.classList.add('text-dark');
            badge.classList.remove('bg-primary');
            badge.classList.remove('text-white');
        }
    });
    
    // Reset sliders in main UI with checks
    const gamesSlider = document.getElementById('gamesSlider');
    if (gamesSlider) {
        gamesSlider.value = 2; // Default to 2 games
        const gamesSliderValue = document.getElementById('gamesSliderValue');
        if (gamesSliderValue) {
            gamesSliderValue.textContent = 'Any (2+)';
        }
    }
    
    const hotelChangesSlider = document.getElementById('hotelChangesSlider');
    if (hotelChangesSlider) {
        hotelChangesSlider.value = 7;
        const hotelChangesValue = document.getElementById('hotelChangesValue');
        if (hotelChangesValue) {
            hotelChangesValue.textContent = 'Any';
        }
    }
    
    // Reset drawer sliders with checks
    const drawerGamesSlider = document.getElementById('drawerGamesSlider');
    if (drawerGamesSlider) {
        drawerGamesSlider.value = 2;  // Default to 2 games
        const drawerGamesSliderValue = document.getElementById('drawerGamesSliderValue');
        if (drawerGamesSliderValue) {
            drawerGamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
        }
    }
    
    const drawerHotelChangesSlider = document.getElementById('drawerHotelChangesSlider');
    if (drawerHotelChangesSlider) {
        drawerHotelChangesSlider.value = 7;
        const drawerHotelChangesValue = document.getElementById('drawerHotelChangesValue');
        if (drawerHotelChangesValue) {
            drawerHotelChangesValue.textContent = 'Any';
        }
    }
    
    // Reset pending filters too
    pendingFilters.team = null;
    pendingFilters.city = null;
    pendingFilters.minGames = 2;
    pendingFilters.maxHotelChanges = 7;
    
    // Update drawer UI
    updateDrawerTeamFilters();
    updateDrawerCityFilters();
    updateDrawerActiveFilters();
    
    // Update filter count badge
    updateFilterCount();
    
    // If using pagination, restore original data and re-render
    if (window.tripResults && window.tripResults.originalTrips) {
        window.tripResults.allTrips = [...window.tripResults.originalTrips];
        window.tripResults.renderedCount = 0;
        window.tripResults.hasMoreTrips = window.tripResults.allTrips.length > 0;
        
        // Get the results container
        const container = document.getElementById('tripResults');
        
        // IMPORTANT: Save the TBD games section before clearing the container
        const tbdSection = container ? container.querySelector('#tbdGamesSection') : null;
        
        // Clear the results container
        if (container) {
            container.innerHTML = '';
            
            // Re-add the TBD games section if it was found
            if (tbdSection) {
                container.appendChild(tbdSection);
            }
        }
        
        // Update count display
        const resultsCount = document.getElementById('resultsCount');
        if (resultsCount) {
            resultsCount.textContent = window.tripResults.allTrips.length;
        }
        
        // Hide any no matches message
        hideNoFilterMatchesMessage();
        
        // Re-render with original data
        if (typeof renderNextBatch === 'function') {
            renderNextBatch();
        } else {
            console.warn('renderNextBatch function not found');
        }
    } else {
        // Legacy mode: show all cards and reset option tabs
        document.querySelectorAll('.trip-card').forEach(card => {
            // Don't reset the TBD section
            if (card.id === 'tbdGamesSection') return;
            
            card.style.display = 'block';
            
            // Show all option tabs
            card.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
                tab.style.display = 'block';
            });
        });
        
        // Hide any no matches message
        hideNoFilterMatchesMessage();
    }
    
    // Dispatch event
    dispatchFilterChangeEvent();
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
        
        // Add team logo to badge
        const logo = document.createElement('img');
        logo.src = getTeamLogoUrl(team);
        logo.alt = `${team} logo`;
        logo.className = 'team-filter-logo';
        logo.width = 16;
        logo.height = 16;
        
        badge.appendChild(logo);
        badge.appendChild(document.createTextNode(' ' + team));
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
        clearTeamFilters.onclick = clearFiltersEnhanced;
        clearTeamFilters.style.cursor = 'pointer';
        teamFiltersContainer.appendChild(clearTeamFilters);
    }
    
    if (cities.length > 0) {
        const clearCityFilters = document.createElement('span');
        clearCityFilters.className = 'badge bg-secondary text-white ms-2';
        clearCityFilters.innerHTML = '<i class="fas fa-times"></i> Clear';
        clearCityFilters.onclick = clearFiltersEnhanced;
        clearCityFilters.style.cursor = 'pointer';
        cityFiltersContainer.appendChild(clearCityFilters);
    }
    
    // Find max number of games across all trips to set slider range
    let maxGamesFound = 1;
    let maxHotelChangesFound = 0;
    
    tripGroups.forEach(group => {
        if (group.variation_details && group.variation_details.length > 0) {
            group.variation_details.forEach(variation => {
                // Track max games
                if (variation.num_games) {
                    maxGamesFound = Math.max(maxGamesFound, variation.num_games);
                }
                
                // Track max hotel changes
                if (variation.hotel_changes !== undefined) {
                    maxHotelChangesFound = Math.max(maxHotelChangesFound, variation.hotel_changes);
                }
            });
        }
    });
    
    // Initialize sliders based on data
    initializeSliders(maxGamesFound, maxHotelChangesFound);
    
    // Initialize drawer sliders with the same values
    initializeDrawerSliders(maxGamesFound, maxHotelChangesFound);
    
    // Initialize the filter drawer if it doesn't exist yet
    if (!filterButton) {
        initFilterDrawer();
    } else {
        // Otherwise, update filters in the drawer
        updateDrawerTeamFilters();
        updateDrawerCityFilters();
        updateDrawerActiveFilters();
        updateFilterCount();
    }
    
    // Hide the old filter card
    const filterResultsCard = document.getElementById('filterResultsCard');
    if (filterResultsCard) {
        filterResultsCard.style.display = 'none';
    }
}

// Update the initializeSliders function for both fixes
function initializeSliders(maxGames, maxHotelChanges) {
    // Set up games slider
    const gamesSlider = document.getElementById('gamesSlider');
    const gamesSliderValue = document.getElementById('gamesSliderValue');
    const sliderContainer = gamesSlider?.parentElement;
    
    if (gamesSlider && gamesSliderValue) {
        // Special case: When all trips have exactly 2 games
        if (maxGames === 2) {
            // Position slider at far right to indicate "2"
            gamesSlider.min = 2;
            gamesSlider.max = 2;
            gamesSlider.value = 2;
            gamesSliderValue.textContent = '2';
            
            // Get the label and update it
            const sliderLabel = gamesSlider.previousElementSibling;
            if (sliderLabel) {
                const spanElement = sliderLabel.querySelector('span');
                if (spanElement) spanElement.textContent = 'Games:';
            }
            
            // Visually indicate this is fixed
            gamesSlider.style.opacity = '0.7';
            
            // Set fixed filter value
            activeFilters.minGames = 2;
            pendingFilters.minGames = 2;
            
            // Remove any existing event listeners and add a no-op one
            gamesSlider.replaceWith(gamesSlider.cloneNode(true));
            document.getElementById('gamesSlider').addEventListener('input', function() {
                // No-op - slider is fixed at 2
            });
        } 
        // Normal case: Multiple game count options
        else if (maxGames > 2) {
            // Important: Set min to 2 instead of 1
            gamesSlider.min = 2;
            gamesSlider.max = maxGames;
            
            // Default to minimum (2 games)
            gamesSlider.value = 2;
            gamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
            
            // Set initial filter value
            activeFilters.minGames = 2;
            pendingFilters.minGames = 2;
            
            // Add the event listener for sliding functionality
            gamesSlider.addEventListener('input', function() {
                const value = parseInt(this.value);
                
                // Always show the min as "Any (2+)" 
                if (value === 2) {
                    gamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
                    activeFilters.minGames = 2;
                } else {
                    gamesSliderValue.textContent = `${value}+`;
                    activeFilters.minGames = value;
                    
                    if (value === maxGames) {
                        gamesSliderValue.textContent = value;
                    }
                }
                
                filterByGames(value);
            });
        }
        else {
            // Fallback case (should not happen)
            gamesSlider.min = 2;
            gamesSlider.max = 5;
            gamesSlider.value = 2;
            gamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
            activeFilters.minGames = 2;
            pendingFilters.minGames = 2;
        }
    }
    
    // Set up hotel changes slider (unchanged)
    const hotelChangesSlider = document.getElementById('hotelChangesSlider');
    const hotelChangesValue = document.getElementById('hotelChangesValue');
    
    if (hotelChangesSlider && hotelChangesValue) {
        // Update max value based on data
        hotelChangesSlider.max = Math.max(7, maxHotelChanges);
        hotelChangesSlider.value = hotelChangesSlider.max; // Default to maximum (Any)
        hotelChangesValue.textContent = 'Any';
        
        hotelChangesSlider.addEventListener('input', function() {
            const value = parseInt(this.value);
            if (value === parseInt(hotelChangesSlider.max)) {
                hotelChangesValue.textContent = 'Any';
            } else {
                hotelChangesValue.textContent = value;
            }
            
            filterByHotelChanges(value);
        });
    }
}

function initializeDrawerSliders(maxGames, maxHotelChanges) {
    // Set up games slider in drawer
    const drawerGamesSlider = document.getElementById('drawerGamesSlider');
    const drawerGamesSliderValue = document.getElementById('drawerGamesSliderValue');
    
    if (drawerGamesSlider && drawerGamesSliderValue) {
        // Special case: When all trips have exactly 2 games
        if (maxGames === 2) {
            drawerGamesSlider.min = 2;
            drawerGamesSlider.max = 2;
            drawerGamesSlider.value = 2;
            drawerGamesSliderValue.textContent = '2';
            drawerGamesSlider.style.opacity = '0.7';
            pendingFilters.minGames = 2;
            
            // Remove any existing event listeners and add a no-op one
            drawerGamesSlider.replaceWith(drawerGamesSlider.cloneNode(true));
            document.getElementById('drawerGamesSlider').addEventListener('input', function() {
                // No-op - slider is fixed at 2
            });
        } 
        // Normal case: Multiple game count options
        else if (maxGames > 2) {
            drawerGamesSlider.disabled = false;
            drawerGamesSlider.style.opacity = '1';
            // Important: Set min to 2 instead of 1
            drawerGamesSlider.min = 2;
            drawerGamesSlider.max = maxGames;
            drawerGamesSlider.value = pendingFilters.minGames;
            
            // Use "Any (2+)" for minimum
            if (pendingFilters.minGames === 2) {
                drawerGamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
            } else {
                drawerGamesSliderValue.textContent = pendingFilters.minGames + '+';
                if (pendingFilters.minGames === maxGames) {
                    drawerGamesSliderValue.textContent = pendingFilters.minGames;
                }
            }
            
            // Add the event listener for sliding functionality
            const existingSlider = document.getElementById('drawerGamesSlider');
            const newSlider = existingSlider.cloneNode(true);
            existingSlider.parentNode.replaceChild(newSlider, existingSlider);
            
            newSlider.addEventListener('input', function() {
                const value = parseInt(this.value);
                if (value === 2) {
                    drawerGamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
                    pendingFilters.minGames = 2;
                } else {
                    drawerGamesSliderValue.textContent = `${value}+`;
                    pendingFilters.minGames = value;
                    if (value === maxGames) {
                        drawerGamesSliderValue.textContent = value;
                    }
                }
                
                // Update active filters display
                updateDrawerActiveFilters();
            });
        }
    }
    
    // Set up hotel changes slider in drawer
    const drawerHotelChangesSlider = document.getElementById('drawerHotelChangesSlider');
    const drawerHotelChangesValue = document.getElementById('drawerHotelChangesValue');
    
    if (drawerHotelChangesSlider && drawerHotelChangesValue) {
        // Update max value based on data
        drawerHotelChangesSlider.max = Math.max(7, maxHotelChanges);
        drawerHotelChangesSlider.value = activeFilters.maxHotelChanges;
        
        if (activeFilters.maxHotelChanges === parseInt(drawerHotelChangesSlider.max)) {
            drawerHotelChangesValue.textContent = 'Any';
        } else {
            drawerHotelChangesValue.textContent = activeFilters.maxHotelChanges;
        }
        
        // Add the event listener for sliding functionality
        const existingSlider = document.getElementById('drawerHotelChangesSlider');
        const newSlider = existingSlider.cloneNode(true);
        existingSlider.parentNode.replaceChild(newSlider, existingSlider);
        
        newSlider.addEventListener('input', function() {
            const value = parseInt(this.value);
            if (value === parseInt(drawerHotelChangesSlider.max)) {
                drawerHotelChangesValue.textContent = 'Any';
                activeFilters.maxHotelChanges = value;
            } else {
                drawerHotelChangesValue.textContent = value;
                activeFilters.maxHotelChanges = value;
            }
            
            // Update active filters display
            updateDrawerActiveFilters();
            updateFilterCount();
        });
    }
}

// Dispatch a custom event when filters change
function dispatchFilterChangeEvent() {
    const event = new CustomEvent('filtersChanged', {
        detail: {
            activeFilters: { ...activeFilters }
        }
    });
    document.dispatchEvent(event);
}

// Add this new function to reset filter state
function resetFilters() {
    // Reset active filters state
    activeFilters.team = null;
    activeFilters.city = null;
    activeFilters.minGames = 2;  // Default to 2 games minimum
    activeFilters.maxHotelChanges = 7;
    
    // Update UI if elements exist
    updateFilterCount();
    
    // Update drawer UI if it exists
    if (filterDrawer) {
        updateDrawerTeamFilters();
        updateDrawerCityFilters();
        updateDrawerActiveFilters();
    }
}

// Add new drawer-specific filter functions that don't immediately apply filters
function drawerFilterByTeam(team) {
    // Toggle team selection
    if (pendingFilters.team === team) {
        pendingFilters.team = null;
    } else {
        pendingFilters.team = team;
    }
    
    // Update UI only
    updateDrawerTeamFilterUI();
    updateDrawerActiveFilters();
}

function drawerFilterByCity(city) {
    // Toggle city selection
    if (pendingFilters.city === city) {
        pendingFilters.city = null;
    } else {
        pendingFilters.city = city;
    }
    
    // Update UI only
    updateDrawerCityFilterUI();
    updateDrawerActiveFilters();
}

// Update drawer filter UI based on pending filters
function updateDrawerTeamFilterUI() {
    const drawerTeamFilters = document.getElementById('drawerTeamFilters');
    if (!drawerTeamFilters) return;
    
    drawerTeamFilters.querySelectorAll('.badge').forEach(badge => {
        if (badge.dataset.team === pendingFilters.team) {
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

function updateDrawerCityFilterUI() {
    const drawerCityFilters = document.getElementById('drawerCityFilters');
    if (!drawerCityFilters) return;
    
    drawerCityFilters.querySelectorAll('.badge').forEach(badge => {
        if (badge.dataset.city === pendingFilters.city) {
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

// Add a function to clear drawer filters (not applied until Apply button)
function clearDrawerFilters() {
    // Reset pending filters state
    pendingFilters.team = null;
    pendingFilters.city = null;
    pendingFilters.minGames = 2;  // Default to 2 games minimum
    pendingFilters.maxHotelChanges = 7;
    
    // Reset drawer UI
    updateDrawerTeamFilterUI();
    updateDrawerCityFilterUI();
    updateDrawerActiveFilters();
    
    // Reset sliders in drawer
    const drawerGamesSlider = document.getElementById('drawerGamesSlider');
    if (drawerGamesSlider) {
        drawerGamesSlider.value = 2;  // Default to 2 games
        const drawerGamesSliderValue = document.getElementById('drawerGamesSliderValue');
        if (drawerGamesSliderValue) {
            drawerGamesSliderValue.textContent = 'Any (2+)'; // Changed from '2+' to 'Any (2+)'
        }
    }
    
    const drawerHotelChangesSlider = document.getElementById('drawerHotelChangesSlider');
    if (drawerHotelChangesSlider) {
        drawerHotelChangesSlider.value = 7;
        const drawerHotelChangesValue = document.getElementById('drawerHotelChangesValue');
        if (drawerHotelChangesValue) {
            drawerHotelChangesValue.textContent = 'Any';
        }
    }
}

export {
    filterByTeam,
    filterByCity,
    renderFilters,
    clearFiltersEnhanced as clearFilters,
    filterByGames,
    filterByHotelChanges,
    filterTripOptions,
    initFilterDrawer,
    resetFilters  // Add this new export
};