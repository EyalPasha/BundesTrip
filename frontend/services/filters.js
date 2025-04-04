import { clearFilters } from './ui-helpers.js';
import { renderNextBatch } from '../components/results-display.js';

// Global state to track active filters
const activeFilters = {
  team: null,
  city: null,
  minGames: 1,
  maxHotelChanges: 7
};

// Make filter state globally available for newly loaded trips
window.activeFilters = activeFilters;

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
    
    // Apply all active filters
    applyAllFilters();
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
    
    // Apply all active filters
    applyAllFilters();
}

// New function to filter by number of games
function filterByGames(minGames) {
    activeFilters.minGames = minGames;
    applyAllFilters();
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
            
            // Extract travel time 
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
    const tripGroupData = JSON.parse(tripCard.dataset.tripGroup || '{}');
    let selectedVariantIndex = 0; // Default to first variant

    // Sort options according to the specified logic:
    // 1. If max hotel changes is set to max, sort by travel time
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
        selectedVariantIndex = firstValidOption.index;
        
        import('../components/trip-card.js').then(module => {
            if (typeof module.renderItineraryForVariant === 'function' && tripGroupData) {
                module.renderItineraryForVariant(dynamicItineraryContainer, tripGroupData, selectedVariantIndex);
            }
        });
    }
}

// New function to filter by hotel changes
function filterByHotelChanges(maxChanges) {
    // Update the active filter state
    activeFilters.maxHotelChanges = maxChanges;
    
    // Apply all filters to trip cards to hide any that have no valid options
    applyAllFilters();
    
    // Process each visible trip card to reorder options
    document.querySelectorAll('.trip-card:not([style*="display: none"])').forEach(card => {
        filterTripOptions(card);
    });
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
                if (!teams.includes(activeFilters.team)) {
                    return false;
                }
            }
            
            // Check city filter
            if (activeFilters.city) {
                const cities = defaultVariant.cities || [];
                if (!cities.includes(activeFilters.city)) {
                    return false;
                }
            }
            
            // Check number of games filter
            if (activeFilters.minGames > 1) {
                if ((defaultVariant.num_games || 0) < activeFilters.minGames) {
                    return false;
                }
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
        const tbdSection = container ? container.querySelector('.card.mt-4.fade-in.shadow-sm.mb-4') : null;
        
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
        
        // Re-render with the filtered data
        if (typeof renderNextBatch === 'function') {
            renderNextBatch();
        }
    } else {
        // Legacy mode for non-paginated display
        const tripCards = document.querySelectorAll('.trip-card');
        
        tripCards.forEach(card => {
            // Start assuming the card passes all filters
            let showCard = true;
            
            // Apply team filter
            if (activeFilters.team) {
                const cardTeams = card.dataset.teams.split(',');
                if (!cardTeams.includes(activeFilters.team)) {
                    showCard = false;
                }
            }
            
            // Apply city filter
            if (showCard && activeFilters.city) {
                const cardCities = card.dataset.cities.split(',');
                if (!cardCities.includes(activeFilters.city)) {
                    showCard = false;
                }
            }
            
            // Number of games filter
            if (showCard && activeFilters.minGames > 1) {
                const matchCountEl = card.querySelector('.match-count-badge');
                if (matchCountEl) {
                    const numGames = parseInt(matchCountEl.textContent);
                    if (numGames < activeFilters.minGames) {
                        showCard = false;
                    }
                }
            }
            
            // Apply visibility based on filters
            card.style.display = showCard ? 'block' : 'none';
            
            // Filter travel options based on hotel changes
            if (showCard && activeFilters.maxHotelChanges < 7) {
                filterTripOptions(card);
            }
        });
    }
}

// Filter travel options within a trip card
function filterTripOptions(tripCard) {
    const tabButtons = tripCard.querySelectorAll('[data-bs-toggle="tab"]');
    const tabPanes = tripCard.querySelectorAll('.tab-pane');
    
    let validOptionFound = false;
    const optionsInfo = [];
    
    // First pass: collect info about each option without hiding any yet
    tabButtons.forEach((button, idx) => {
        const optionPane = tabPanes[idx];
        const hotelChanges = extractHotelChanges(optionPane);
        
        // Track if this option is valid under current filter
        const isValid = hotelChanges <= activeFilters.maxHotelChanges;
        if (isValid) validOptionFound = true;
        
        // Store information about each option
        optionsInfo.push({
            button: button,
            pane: optionPane,
            hotelChanges: hotelChanges,
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
    
    // First try to find explicit hotel changes display using proper DOM traversal
    const statLabels = optionPane.querySelectorAll('.stat-label');
    
    // Search through all stat labels to find hotel changes
    for (let i = 0; i < statLabels.length; i++) {
        if (statLabels[i].textContent.includes('Hotel Changes')) {
            const valueEl = statLabels[i].nextElementSibling;
            if (valueEl && valueEl.classList.contains('stat-value')) {
                return parseInt(valueEl.textContent) || 0;
            }
        }
    }
    
    // Second, try to count hotel stay items
    const hotelStayItems = optionPane.querySelectorAll('.hotel-stay-item');
    if (hotelStayItems.length > 0) {
        return Math.max(0, hotelStayItems.length - 1);  // Changes = stays - 1
    }
    
    return 0; // Default if we can't find the information
}

// Enhanced clear filters function - update this in filters.js
function clearFiltersEnhanced() {
    // Reset active filters state
    activeFilters.team = null;
    activeFilters.city = null;
    activeFilters.minGames = 1;
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
    
    // Reset sliders
    const gamesSlider = document.getElementById('gamesSlider');
    if (gamesSlider) {
        gamesSlider.value = 1;
        const gamesSliderValue = document.getElementById('gamesSliderValue');
        if (gamesSliderValue) {
            gamesSliderValue.textContent = 'Any';
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
    
    // If using pagination, restore original data and re-render
    if (window.tripResults && window.tripResults.originalTrips) {
        window.tripResults.allTrips = [...window.tripResults.originalTrips];
        window.tripResults.renderedCount = 0;
        window.tripResults.hasMoreTrips = window.tripResults.allTrips.length > 0;
        
        // Get the results container
        const container = document.getElementById('tripResults');
        
        // IMPORTANT: Save the TBD games section before clearing the container
        const tbdSection = container ? container.querySelector('.card.mt-4.fade-in.shadow-sm.mb-4') : null;
        
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
        
        // Re-render with original data
        renderNextBatch();
    } else {
        // Legacy mode: show all cards and reset option tabs
        document.querySelectorAll('.trip-card').forEach(card => {
            card.style.display = 'block';
            
            // Show all option tabs
            card.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
                tab.style.display = 'block';
            });
        });
    }
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
                const rangeText = sliderLabel.querySelector('span:first-child');
                if (rangeText) {
                    rangeText.textContent = 'Number of Games:';
                }
            }
            
            // Visually indicate this is fixed
            gamesSlider.style.opacity = '0.7';
            
            // Set fixed filter value
            activeFilters.minGames = 2;
            
            // Remove any existing event listeners and add a no-op one
            gamesSlider.replaceWith(gamesSlider.cloneNode(true));
            document.getElementById('gamesSlider').addEventListener('input', function() {
                // No-op - slider is fixed at 2
            });
        } 
        // Normal case: Multiple game count options
        else if (maxGames > 2) {
            // Enable the slider and set range from 2 to maxGames
            gamesSlider.disabled = false;
            gamesSlider.style.opacity = '1';
            gamesSlider.min = 2;
            gamesSlider.max = maxGames;
            gamesSlider.value = 2; // Default to minimum
            gamesSliderValue.textContent = 'Any';
            
            // Show the actual range in the label
            const sliderLabel = gamesSlider.previousElementSibling;
            if (sliderLabel) {
                const rangeText = sliderLabel.querySelector('span:first-child');
                if (rangeText) {
                    rangeText.textContent = `Number of Games (2-${maxGames}):`;
                }
            }
            
            // Add the event listener for sliding functionality
            gamesSlider.addEventListener('input', function() {
                const value = parseInt(this.value);
                if (value === 2) { // Since 2 is our minimum
                    gamesSliderValue.textContent = 'Any';
                    filterByGames(2);
                } else {
                    gamesSliderValue.textContent = `${value}+`;
                    filterByGames(value);
                }
                
                // When at max, show exact number instead of "+"
                if (value === maxGames) {
                    gamesSliderValue.textContent = value;
                }
            });
        }
        // Edge case: Less than 2 games (shouldn't happen with your min=2 requirement)
        else {
            // Hide or disable the slider since it's not applicable
            gamesSlider.disabled = true;
            gamesSlider.style.opacity = '0.5';
            gamesSliderValue.textContent = 'N/A';
            
            // Update label
            const sliderLabel = gamesSlider.previousElementSibling;
            if (sliderLabel) {
                const rangeText = sliderLabel.querySelector('span:first-child');
                if (rangeText) {
                    rangeText.textContent = 'Number of Games:';
                }
            }
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
                filterByHotelChanges(value);
            } else {
                hotelChangesValue.textContent = value;
                filterByHotelChanges(value);
            }
        });
    }
}

export {
    filterByTeam,
    filterByCity,
    renderFilters,
    clearFiltersEnhanced as clearFilters,
    filterByGames,
    filterByHotelChanges,
    filterTripOptions // Add this export
};