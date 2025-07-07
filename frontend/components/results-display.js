import { renderTripCard, renderTbdGames } from './trip-card.js';
import { renderFilters, initFilterDrawer } from '../services/filters.js'; 
import { showListView } from '../services/ui-helpers.js';
import { formatCityForDisplay, formatCityForBackend } from '../services/city-formatter.js';
/**
 * Renders trip search results with enhanced handling of backend data
 * @param {Object} response - The API response from the trip planning endpoint
 * @param {boolean} isRestore - Whether this is a session restore
 */
function renderResults(response, isRestore = false) {
    // Check for cancelled flag in response
    if (response.cancelled) {
        return;
    }

    // --- Move this up! ---
    const tbdGames = response.tbd_games || response.TBD_Games || [];
    // ---------------------

    const tripResults = document.getElementById('tripResults');
    
    // Clear previous results
    if (tripResults) {
        tripResults.innerHTML = '';
    }
    
    // Ensure body has the filter drawer class when we have results
    if (response.trip_groups && response.trip_groups.length > 0) {
        document.body.classList.add('has-filter-drawer');
    }
    
    // *** CRITICAL: Show results section immediately for restore ***
    if (isRestore) {
        const resultsSection = document.getElementById('results');
        if (resultsSection) {
            resultsSection.classList.remove('d-none');
        }
        
        // Hide loading container during restore
        const loadingContainer = document.getElementById('loading');
        if (loadingContainer) {
            loadingContainer.classList.add('d-none');
        }
        
        // Enable scrolling
        document.body.classList.remove('no-scroll');
    }
    
    // Initialize the window.tripResults pagination state
    if (response.trip_groups && response.trip_groups.length > 0) {
        window.tripResults = {
            currentIndex: 0,
            batchSize: 5,
            allTrips: response.trip_groups,
            displayedTrips: [],
            filterStates: {},
            context: response,
            renderedCount: 0,
            hasMoreTrips: response.trip_groups.length > 0,
            originalTrips: [...response.trip_groups]
        };
        
        // Store trip context for rendering
        window.tripContext = {
            tripDuration: response.trip_duration,
            startLocation: response.start_location,
            startDate: response.start_date,
            tbdGames: tbdGames, // now safe!
            mustTeams: response.must_teams || [] // <-- add this
        };
    } else {
        window.tripResults = null;
        window.tripContext = null;
    }
    
    // Check if we have both no trips AND TBD games
    const noTrips = !response.trip_groups || response.trip_groups.length === 0;
    const hasTbdGames = tbdGames && tbdGames.length > 0;

    // Show TBD games if available
    if (hasTbdGames) {
        renderTbdGames(tbdGames, response.must_teams || []);
    }
    
    // Handle no trips with TBD games
    if (noTrips && hasTbdGames) {
        const loadingAnimation = document.getElementById('loadingAnimation');
        const loadingMessages = document.getElementById('loadingMessages');
        const cancelButton = document.getElementById('cancelSearch');
        const noResultsMessage = document.getElementById('noResultsMessage');
        
        if (loadingAnimation) loadingAnimation.classList.add('d-none');
        if (loadingMessages) loadingMessages.classList.add('d-none');
        if (cancelButton) cancelButton.classList.add('d-none');
        
        if (noResultsMessage) {
            noResultsMessage.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">No scheduled games found for your trip dates</h4>
                    <p>However, we found ${response.tbd_games.length} unscheduled games that might be available during your trip once times are confirmed:</p>
                    <ul class="list-unstyled tbd-games-list">
                        ${response.tbd_games.map(game => `
                            <li class="mb-2">
                                <div class="d-flex align-items-center">
                                    <span class="badge bg-warning text-dark me-2">TBD</span>
                                    <div>
                                        <strong>${game.match}</strong><br>
                                        <small>${game.date} at ${formatCityForDisplay(game.location)}</small>
                                    </div>
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                    <p class="mb-0">Check back later for updated schedules.</p>
                </div>
            `;
            noResultsMessage.classList.remove('d-none');
        }
    }
    
    // Process trip groups (if any)
    if (!noTrips) {
        // *** ENSURE ALL UI ELEMENTS ARE VISIBLE FOR RESTORATION ***
        const resultsSection = document.getElementById('results');
        const resultsCountContainer = document.getElementById('resultsCountContainer');
        const filterResultsCard = document.getElementById('filterResultsCard');
        
        // Show results section
        if (resultsSection) {
            resultsSection.classList.remove('d-none');
        }
        
        // Show and update results count container
        if (resultsCountContainer) {
            resultsCountContainer.classList.remove('d-none');
            const tripCount = response.trip_groups.length;
            
            resultsCountContainer.className = 'results-header mb-4';
            resultsCountContainer.innerHTML = `
                <div class="results-header-content">
                    <div class="results-icon">
                        <i class="fas fa-map-marked-alt"></i>
                    </div>
                    <div class="results-info">
                        <h2>Your Trip Options</h2>
                        <div class="results-meta">
                            <div class="results-count">
                                <span id="resultsCount" class="count-badge">${tripCount}</span> trips found
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Generate filters based on match data
        renderFilters(response.trip_groups);
        
        // Hide the old filter card since we're using the drawer
        if (filterResultsCard) {
            filterResultsCard.style.display = 'none';
        }
        
        // Initialize filter drawer with appropriate delay
        setTimeout(() => {
            import('../services/filters.js').then(module => {
                if (typeof module.initFilterDrawer === 'function') {
                    module.initFilterDrawer();
                    
                    const filterButton = document.querySelector('.filter-button');
                    if (filterButton) {
                        filterButton.classList.remove('d-none');
                        filterButton.style.display = 'flex';
                        
                        const filterCount = document.querySelector('.filter-count');
                        if (filterCount) {
                            const activeFilterCount = Object.values(window.activeFilters || {})
                                .filter(value => value !== null && value !== undefined).length;
                            
                            if (activeFilterCount > 0) {
                                filterCount.textContent = activeFilterCount;
                                filterCount.classList.remove('d-none');
                            } else {
                                filterCount.classList.add('d-none');
                            }
                        }
                    }
                }
            });
        }, isRestore ? 0 : 100);
        
        // Enable sorting and list-view controls
        const sortingControl = document.getElementById('sortResults');
        if (sortingControl) {
            sortingControl.classList.remove('d-none');
        }
        
        const viewListBtn = document.getElementById('viewList');
        if (viewListBtn) {
            viewListBtn.classList.remove('d-none');
            viewListBtn.onclick = () => showListView(response.trip_groups);
        }

        // Render first batch of trips
        renderNextBatch();
    } else {
        // Handle no results message for non-restore cases
        if (!isRestore && !hasTbdGames) {
            const loadingAnimation = document.getElementById('loadingAnimation');
            const loadingMessages = document.getElementById('loadingMessages');
            const cancelButton = document.getElementById('cancelSearch');
            const noResultsMessage = document.getElementById('noResultsMessage'); 
            
            if (loadingAnimation) loadingAnimation.classList.add('d-none');
            if (loadingMessages) loadingMessages.classList.add('d-none');
            if (cancelButton) cancelButton.classList.add('d-none');
            if (noResultsMessage) noResultsMessage.classList.remove('d-none');
        }
    }

    // Initialize tooltips on newly rendered elements
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
    }
}

/**
 * Extracts unique cities from trip groups for filtering
 * @param {Array} tripGroups - Array of trip groups from API response
 * @returns {Array} - Unique cities across all trips
 */
function extractCities(tripGroups) {
    const cities = new Set();
    
    tripGroups.forEach(group => {
        if (group.variation_details && group.variation_details.length > 0) {
            group.variation_details.forEach(variation => {
                if (variation.cities && Array.isArray(variation.cities)) {
                    // Keep original city names for filtering logic
                    variation.cities.forEach(city => cities.add(city));
                }
            });
        }
    });
    
    return [...cities].sort();
}

/**
 * Extracts unique teams from trip groups for filtering
 * @param {Array} tripGroups - Array of trip groups from API response
 * @returns {Array} - Unique teams across all trips
 */
function extractTeams(tripGroups) {
    const teams = new Set();
    
    tripGroups.forEach(group => {
        if (group.variation_details && group.variation_details.length > 0) {
            group.variation_details.forEach(variation => {
                if (variation.teams && Array.isArray(variation.teams)) {
                    variation.teams.forEach(team => teams.add(team));
                }
            });
        }
    });
    
    return [...teams].sort();
}

// Update the renderNextBatch function to save progress
function renderNextBatch() {
    const state = window.tripResults;
    if (!state || !state.allTrips) return;

    const resultsContainer = document.getElementById('tripResults');
    if (!resultsContainer) {
        console.error("Trip results container not found");
        return;
    }
    
    // Ensure renderedCount is initialized
    if (state.renderedCount === undefined) {
        state.renderedCount = 0;
    }
    
    // Calculate the end index for this batch
    const start = state.renderedCount;
    const end = Math.min(start + state.batchSize, state.allTrips.length);
    
    //console.log(`Rendering trips ${start + 1} to ${end} of ${state.allTrips.length}`);
    
    // Track the newly rendered cards to filter them
    const newlyRenderedCards = [];
    
    // Render this batch of trips
    for (let i = start; i < end; i++) {
        const trip = state.allTrips[i];
        renderTripCard(trip, i + 1, window.tripContext);
        
        // Get the card we just rendered (last child)
        const lastCard = resultsContainer.lastElementChild;
        if (lastCard && lastCard.classList.contains('trip-card')) {
            // Mark it for filtering and add to our tracking array
            lastCard.classList.add('newly-rendered');
            newlyRenderedCards.push(lastCard);
        }
    }
    
    // Update the rendered count
    state.renderedCount = end;
    state.hasMoreTrips = state.renderedCount < state.allTrips.length;
    
    // *** SAVE PROGRESS TO SESSION STORAGE ***
    if (window.sessionManager) {
        window.sessionManager.updateRenderedCount(state.renderedCount);
    }
    
    // Apply filters to newly rendered cards with a reliable approach
    setTimeout(() => {
        import('../services/filters.js').then(module => {
            // Get the newly rendered cards using our marker class
            const newCards = document.querySelectorAll('.trip-card.newly-rendered');
            
            //console.log(`Applying filters to ${newCards.length} newly rendered cards`);
            
            // Apply hotel changes filter if it's active
            if (window.activeFilters && window.activeFilters.maxHotelChanges < 7) {
                newCards.forEach(card => {
                    try {
                        if (typeof module.filterTripOptions === 'function') {
                            module.filterTripOptions(card);
                        }
                        // Remove the marker class after filtering
                        card.classList.remove('newly-rendered');
                    } catch (error) {
                        console.error('Error applying hotel filter to new card:', error);
                    }
                });
            } else {
                // Remove marker class even if filter wasn't applied
                newCards.forEach(card => card.classList.remove('newly-rendered'));
            }
        });
    }, 50);

    // Remove any existing load more button
    const existingButton = document.getElementById('loadMoreTrips');
    if (existingButton) {
        existingButton.remove();
    }
    
    // Add load more button if there are more trips
    if (state.hasMoreTrips) {
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.id = 'loadMoreTrips';
        loadMoreBtn.className = 'text-center my-4';
        loadMoreBtn.innerHTML = `
        <button class="btn btn-outline-primary load-more-btn">
            <i class="fas fa-chevron-down me-2"></i>
            Load More Trips
            <span class="ms-2 badge">
                ${state.renderedCount}/${state.allTrips.length}
            </span>
        </button>
    `;
        loadMoreBtn.addEventListener('click', renderNextBatch);
        resultsContainer.appendChild(loadMoreBtn);
    } else if (state.renderedCount > 0) {
        // Add a "no more trips" indicator when all trips are loaded
        const noMoreTrips = document.createElement('div');
        noMoreTrips.className = 'text-center text-muted my-4';
        noMoreTrips.innerHTML = `
            <p><i class="fas fa-check-circle me-2"></i>All ${state.allTrips.length} trips loaded</p>
        `;
        resultsContainer.appendChild(noMoreTrips);
    }
}

// Add function to render multiple batches for restoration
function renderMultipleBatches(targetCount) {
    const state = window.tripResults;
    if (!state || !state.allTrips) return;

    const resultsContainer = document.getElementById('tripResults');
    if (!resultsContainer) return;

    // Reset current state
    state.renderedCount = 0;
    resultsContainer.innerHTML = '';

    // --- FIX: Re-render TBD games if present and no trips ---
    if (
        window.tripContext &&
        window.tripContext.tbdGames &&
        window.tripContext.tbdGames.length > 0 &&
        state.allTrips.length === 0
    ) {
        // Call renderTbdGames directly (already imported at top)
        renderTbdGames(window.tripContext.tbdGames, window.tripContext.mustTeams || [], true);
    }

    // Render trips up to the target count
    const totalToRender = Math.min(targetCount, state.allTrips.length);

    for (let i = 0; i < totalToRender; i++) {
        const trip = state.allTrips[i];
        renderTripCard(trip, i + 1, window.tripContext);
    }
    
    // Update state
    state.renderedCount = totalToRender;
    state.hasMoreTrips = state.renderedCount < state.allTrips.length;
    
    // Add load more button if needed
    if (state.hasMoreTrips) {
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.id = 'loadMoreTrips';
        loadMoreBtn.className = 'text-center my-4';
        loadMoreBtn.innerHTML = `
        <button class="btn btn-outline-primary load-more-btn">
            <i class="fas fa-chevron-down me-2"></i>
            Load More Trips
            <span class="ms-2 badge">
                ${state.renderedCount}/${state.allTrips.length}
            </span>
        </button>
    `;
        loadMoreBtn.addEventListener('click', renderNextBatch);
        resultsContainer.appendChild(loadMoreBtn);
    } else {
        // All trips are loaded
        const noMoreTrips = document.createElement('div');
        noMoreTrips.className = 'text-center text-muted my-4';
        noMoreTrips.innerHTML = `
            <p><i class="fas fa-check-circle me-2"></i>All ${state.allTrips.length} trips loaded</p>
        `;
        resultsContainer.appendChild(noMoreTrips);
    }
}

function resetFilterDrawerReferences() {
    filterButton = null;
    filterCount = null; 
    drawerOverlay = null;
    filterDrawer = null;
}

export { renderResults, extractCities, extractTeams, resetFilterDrawerReferences, renderNextBatch, renderMultipleBatches };