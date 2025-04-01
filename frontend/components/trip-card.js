function renderTripCard(group, index, tripContext = {}) {
    const baseTrip = group.base_trip;
    const tripResults = document.getElementById('tripResults');
    
    if (!tripResults) return; // Safety check
    
    // Use provided trip context or fallback to DOM
    const tripDuration = tripContext.tripDuration || 
        (window.DOM?.tripDurationInput ? window.DOM.tripDurationInput.value : "3");
    
    // Reference the first variation for quick access to common details
    const defaultVariant = group.variation_details[0] || {};
    
    const tripCard = document.createElement('div');
    tripCard.className = 'card trip-card fade-in mb-4 shadow-sm';
    tripCard.dataset.teams = defaultVariant.teams?.join(',') || '';
    tripCard.dataset.cities = defaultVariant.cities?.join(',') || '';
    
    // Trip header - enhanced with more information
    const header = document.createElement('div');
    header.className = 'trip-header position-relative';

    // Get first and last cities
    const firstCity = defaultVariant.start_location?.replace(' hbf', '') || 
                     (defaultVariant.cities?.length > 0 ? defaultVariant.cities[0] : 'Unknown');
    const finalCity = defaultVariant.end_location?.replace(' hbf', '') || 
                     (defaultVariant.cities?.length > 0 ? defaultVariant.cities[defaultVariant.cities.length - 1] : 'Unknown');

    // Process leagues data from matches - FIXED LOGIC
    const leaguesMap = {};
    let hasLeagueInfo = false;

    // Go through all days in the itinerary to find matches
    baseTrip.Itinerary.forEach(day => {
        if (day.matches) {
            day.matches.forEach(match => {
                // Try to extract league information
                let leagueName = null;
                
                // Check if match has explicit league property
                if (match.league) {
                    leagueName = match.league;
                } 
                // Skip extraction from match titles - this was causing the issue
                
                if (leagueName) {
                    hasLeagueInfo = true;
                    leaguesMap[leagueName] = (leaguesMap[leagueName] || 0) + 1;
                }
            });
        }
    });

    // Format leagues as cleaner badges without the count numbers
    let leaguesBadges = '';
    if (hasLeagueInfo) {
        Object.entries(leaguesMap).forEach(([league, count]) => {
            leaguesBadges += `
                <span class="badge bg-secondary rounded-pill me-1 mb-1">
                    ${league}
                </span>
            `;
        });
    }

    // Get match information for preview
    const allMatches = [];
    baseTrip.Itinerary.forEach(day => {
        if (day.matches && day.matches.length > 0) {
            day.matches.forEach(match => {
                allMatches.push({
                    match: match.match,
                    date: day.day,
                    location: match.location.replace(' hbf', ''),
                    contains_must_team: match.contains_must_team || false
                });
            });
        }
    });

    header.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h3 class="mb-0">Trip ${index}</h3>
            <span class="badge bg-primary rounded-pill px-3 py-2">${defaultVariant.num_games || 0} matches</span>
        </div>
        
        <div class="d-flex flex-wrap align-items-center mb-3">
            <div class="me-3 d-flex align-items-center">
                <i class="fas fa-calendar-alt text-primary me-1"></i>
                <span>${tripDuration}</span>
            </div>
            <div class="me-3 d-flex align-items-center">
                <i class="fas fa-sliders-h text-secondary me-1"></i>
                <span>${group.variation_details.length} travel options</span>
            </div>
        </div>
        
        ${allMatches.length > 0 ? `
        <div class="match-preview">
            ${allMatches.slice(0, Math.min(3, allMatches.length)).map(match => `
                <div class="match-preview-item ${match.contains_must_team ? 'must-match' : ''}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="match-teams-preview">
                            <i class="fas fa-futbol text-secondary me-2"></i>
                            <strong>${match.match}</strong>
                            ${match.contains_must_team ? '<span class="badge bg-warning text-dark ms-1">Must-See</span>' : ''}
                        </div>
                        <div class="match-location-preview">
                            <i class="fas fa-map-marker-alt text-danger me-1"></i>
                            ${match.location}
                        </div>
                    </div>
                    <div class="small text-muted mt-1">${match.date}</div>
                </div>
            `).join('')}
            ${allMatches.length > 3 ? `
                <div class="text-center text-muted small mt-2">
                    +${allMatches.length - 3} more matches
                </div>
            ` : ''}
        </div>
        ` : ''}
        
        <button class="btn btn-sm btn-outline-secondary mt-3 toggle-details">
            <i class="fas fa-chevron-down"></i> Show Details
        </button>
    `;
    
    // Trip details - initially collapsed
    const details = document.createElement('div');
    details.className = 'trip-details collapse';
    
    // *** MOVE TRAVEL OPTIONS TO TOP OF DETAILS ***
    // Create travel options section first (before itinerary)
    const travelOptionsSection = document.createElement('div');
    travelOptionsSection.className = 'travel-options-section mt-3 mb-4';
    
    const travelOptionsHeader = document.createElement('h5');
    travelOptionsHeader.className = 'mb-3 d-flex align-items-center';
    travelOptionsHeader.innerHTML = '<i class="fas fa-exchange-alt text-primary me-2"></i> Travel Options';
    travelOptionsSection.appendChild(travelOptionsHeader);
    
    // Create tabs for travel options
    const optionsTabs = document.createElement('div');
    optionsTabs.className = 'nav nav-tabs mb-3';
    optionsTabs.id = `trip-${index}-tabs`;
    
    // Create content container for travel options
    const optionsContent = document.createElement('div');
    optionsContent.className = 'tab-content';
    optionsContent.id = `trip-${index}-content`;
    
    // Create container for the dynamic itinerary
    const dynamicItineraryContainer = document.createElement('div');
    dynamicItineraryContainer.className = 'dynamic-itinerary-container mt-4';
    
    // Only add travel options if multiple variations exist
    if (group.variations && group.variations.length > 0) {
        // Create each option tab
        group.variation_details.forEach((variant, varIdx) => {
            const isActive = varIdx === 0;
            const optionId = `trip-${index}-option-${varIdx}`;
            
            // Create tab
            const tab = document.createElement('button');
            tab.className = `nav-link ${isActive ? 'active' : ''}`;
            tab.id = `${optionId}-tab`;
            tab.setAttribute('data-bs-toggle', 'tab');
            tab.setAttribute('data-bs-target', `#${optionId}`);
            tab.setAttribute('type', 'button');
            tab.setAttribute('role', 'tab');
            tab.setAttribute('aria-controls', optionId);
            tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
            tab.innerHTML = `
                <i class="fas fa-${varIdx === 0 ? 'star' : 'route'} me-1"></i> 
                Option ${varIdx + 1}
            `;
            optionsTabs.appendChild(tab);
            
            // Create content pane
            const contentPane = document.createElement('div');
            contentPane.className = `tab-pane fade ${isActive ? 'show active' : ''}`;
            contentPane.id = optionId;
            contentPane.setAttribute('role', 'tabpanel');
            contentPane.setAttribute('aria-labelledby', `${optionId}-tab`);

            // Extract route path
            const firstCity = variant.start_location?.replace(' hbf', '') || 
                             (variant.cities?.length > 0 ? variant.cities[0] : 'Unknown');
            const finalCity = variant.end_location?.replace(' hbf', '') || 
                             (variant.cities?.length > 0 ? variant.cities[variant.cities.length - 1] : 'Unknown');

            // Add complete travel option info with modern styling
            contentPane.innerHTML = `
                <div class="variant-summary mb-3 border-bottom pb-3">
                    <div class="d-flex flex-wrap justify-content-between align-items-center">
                        <div class="option-stats d-flex align-items-center">
                            <div class="stat-item me-4">
                                <div class="d-flex align-items-center">
                                    <div class="stat-icon">
                                        <i class="fas fa-map-marker-alt text-danger"></i>
                                    </div>
                                    <div class="stat-content ms-2">
                                        <div class="stat-label text-muted small">Cities</div>
                                        <div class="stat-value fw-bold">${variant.cities?.length || 0}</div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="stat-item me-4">
                                <div class="d-flex align-items-center">
                                    <div class="stat-icon">
                                        <i class="fas fa-clock text-success"></i>
                                    </div>
                                    <div class="stat-content ms-2">
                                        <div class="stat-label text-muted small">Total Travel</div>
                                        <div class="stat-value fw-bold">${variant.travel_hours || 0}h ${variant.travel_minutes || 0}m</div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="stat-item">
                                <div class="d-flex align-items-center">
                                    <div class="stat-icon">
                                        <i class="fas fa-hotel text-primary"></i>
                                    </div>
                                    <div class="stat-content ms-2">
                                        <div class="stat-label text-muted small">Hotel Changes</div>
                                        <div class="stat-value fw-bold">${variant.hotel_changes || 0}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="route-preview mt-2 mt-md-0">
                            <div class="small text-muted mb-1">Route</div>
                            <div class="d-flex align-items-center">
                                <span class="fw-medium">${firstCity}</span>
                                <i class="fas fa-long-arrow-alt-right mx-2 text-muted"></i>
                                <span class="fw-medium">${finalCity}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            optionsContent.appendChild(contentPane);
            
            // Add click handler to update itinerary when tab is clicked
            tab.addEventListener('click', function() {
                renderItineraryForVariant(dynamicItineraryContainer, group, varIdx);
            });
        });
        
        travelOptionsSection.appendChild(optionsTabs);
        travelOptionsSection.appendChild(optionsContent);
        details.appendChild(travelOptionsSection);
    }
    
    // Add the dynamic itinerary container
    details.appendChild(dynamicItineraryContainer);
    
    // Render the initial itinerary (option 0)
    renderItineraryForVariant(dynamicItineraryContainer, group, 0);
    
    // Add content to card
    tripCard.appendChild(header);
    tripCard.appendChild(details);
    
    // Add card to results container
    tripResults.appendChild(tripCard);
    
    // Add toggle functionality
    const toggleButton = tripCard.querySelector('.toggle-details');
    const detailsSection = tripCard.querySelector('.trip-details');
    
    toggleButton.addEventListener('click', function() {
        const isCollapsed = detailsSection.classList.contains('collapse');
        
        if (isCollapsed) {
            detailsSection.classList.remove('collapse');
            this.innerHTML = '<i class="fas fa-chevron-up"></i> Hide Details';
        } else {
            detailsSection.classList.add('collapse');
            this.innerHTML = '<i class="fas fa-chevron-down"></i> Show Details';
        }
    });
}

/**
 * Extracts hotel summary information from a variant
 * @param {object} variant - The trip variation object
 * @returns {object|null} Hotel summary info or null if not available
 */
function extractHotelSummary(variant) {
    if (!variant) return null;
    
    // First try to get from variant's direct properties
    if (variant.hotel_changes !== undefined && variant.unique_hotels !== undefined) {
        return {
            hotelChanges: variant.hotel_changes,
            uniqueHotels: variant.unique_hotels,
            hotelLocations: variant.hotel_locations || []
        };
    }
    
    // If not available directly, try to extract from day_itinerary
    if (variant.day_itinerary && variant.day_itinerary.length > 0) {
        const hotels = new Set();
        const hotelLocations = [];
        let hotelChanges = 0;
        let prevHotel = null;
        
        for (const day of variant.day_itinerary) {
            if (day && day.hotel) {
                const hotel = day.hotel;
                hotels.add(hotel);
                
                if (!hotelLocations.includes(hotel)) {
                    hotelLocations.push(hotel);
                }
                
                if (prevHotel && prevHotel !== hotel) {
                    hotelChanges++;
                }
                
                prevHotel = hotel;
            }
        }
        
        if (hotels.size > 0) {
            return {
                hotelChanges: hotelChanges,
                uniqueHotels: hotels.size,
                hotelLocations: hotelLocations
            };
        }
    }
    
    // Legacy fallback
    // Look for hotel summary object in the itinerary
    if (variant.Itinerary) {
        for (const day of variant.Itinerary) {
            if (day && !day.matches && !day.day && day.hotel_changes !== undefined) {
                return {
                    hotelChanges: day.hotel_changes,
                    uniqueHotels: day.unique_hotels,
                    hotelLocations: day.hotel_locations ? day.hotel_locations : []
                };
            }
        }
        
        // Try to extract from individual days
        const hotels = new Set();
        const hotelLocations = [];
        let hotelChanges = 0;
        let prevHotel = null;
        
        for (const day of variant.Itinerary) {
            if (day && day.hotel) {
                const hotel = day.hotel;
                hotels.add(hotel);
                
                if (!hotelLocations.includes(hotel)) {
                    hotelLocations.push(hotel);
                }
                
                if (prevHotel && prevHotel !== hotel) {
                    hotelChanges++;
                }
                
                prevHotel = hotel;
            }
        }
        
        if (hotels.size > 0) {
            return {
                hotelChanges: hotelChanges,
                uniqueHotels: hotels.size,
                hotelLocations: hotelLocations
            };
        }
    }
    
    return null;
}

function renderTravelSegments(variant) {
    const segmentsContainer = document.createElement('div');
    segmentsContainer.className = 'travel-segments mt-3';
    
    // Check if travel_segments exists in the variant
    if (!variant.travel_segments || variant.travel_segments.length === 0) {
        const noSegments = document.createElement('div');
        noSegments.className = 'alert alert-info';
        noSegments.textContent = 'No travel segments available for this option.';
        segmentsContainer.appendChild(noSegments);
        return segmentsContainer;
    }
    
    const segmentsList = document.createElement('div');
    segmentsList.className = 'list-group';
    
    variant.travel_segments.forEach((segment, idx) => {
        const segmentItem = document.createElement('div');
        segmentItem.className = 'list-group-item travel-segment';
        
        // Clean up location names (remove "hbf" suffix)
        const fromLocation = typeof segment.from_location === 'string' ? 
            segment.from_location.replace(' hbf', '') : 'Unknown';
        const toLocation = typeof segment.to_location === 'string' ? 
            segment.to_location.replace(' hbf', '') : 'Unknown';
        
        // Get context (day or purpose)
        let context = '';
        if (segment.context) {
            context = segment.context;
        } else if (segment.day) {
            context = segment.day;
        }
        
        segmentItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <span class="segment-number me-2">${idx + 1}</span>
                    <div>
                        ${fromLocation} → ${toLocation} 
                        ${context ? `<span class="text-muted">(${context})</span>` : ''}
                    </div>
                </div>
                <div class="travel-time badge bg-info text-white">${segment.travel_time || 'Unknown'}</div>
            </div>
        `;
        
        segmentsList.appendChild(segmentItem);
    });
    
    segmentsContainer.appendChild(segmentsList);
    return segmentsContainer;
}

/**
 * Renders airport distances section for trip details with consistent styling
 */
function renderAirportDistances(airportData) {
    // Early return if no data available
    if (!airportData) return null;
    
    // Check for different possible data structures
    const startAirports = airportData.start || [];
    const endAirports = airportData.end || airportData.nearest_airports || [];
    const majorAirports = airportData.major || airportData.closest_major_airports || [];
    
    // If no airports in any category, return nothing
    if (startAirports.length === 0 && endAirports.length === 0 && majorAirports.length === 0) {
        return null;
    }

    const airportSection = document.createElement('div');
    airportSection.className = 'travel-segments-section mt-4 mb-3';
    
    // Airports near start location
    if (startAirports && startAirports.length > 0) {
        const startAirportsDiv = document.createElement('div');
        startAirportsDiv.className = 'mb-3';
        
        const startTitle = document.createElement('h5');
        startTitle.className = 'mb-3 d-flex align-items-center';
        startTitle.innerHTML = `
            <i class="fas fa-plane-departure text-primary me-2"></i>
            Airports near ${airportData.start_city || 'starting point'}
        `;
        startAirportsDiv.appendChild(startTitle);
        
        const startList = document.createElement('div');
        startList.className = 'list-group';
        
        startAirports.slice(0, 3).forEach((airport, idx) => {
            const airportName = airport.airport || airport.name || airport.code || 'Unknown Airport';
            const airportCode = airport.code ? `(${airport.code})` : '';
            const travelTime = airport.travel_time || 'N/A';
            
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item travel-segment';
            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <span class="segment-number me-2">${idx + 1}</span>
                        <div>
                            ${airportName} ${airportCode}
                        </div>
                    </div>
                    <div class="travel-time badge bg-info text-white">${travelTime}</div>
                </div>
            `;
            startList.appendChild(listItem);
        });
        
        startAirportsDiv.appendChild(startList);
        airportSection.appendChild(startAirportsDiv);
    }

    // Airports near end location
    if (endAirports && endAirports.length > 0) {
        const endAirportsDiv = document.createElement('div');
        endAirportsDiv.className = 'mb-3';
        
        const endTitle = document.createElement('h5');
        endTitle.className = 'mb-3 d-flex align-items-center';
        endTitle.innerHTML = `
            <i class="fas fa-plane-departure text-primary me-2"></i>
            Airports near ${airportData.end_city || 'destination'}
        `;
        endAirportsDiv.appendChild(endTitle);
        
        const endList = document.createElement('div');
        endList.className = 'list-group';
        
        endAirports.slice(0, 3).forEach((airport, idx) => {
            const airportName = airport.airport || airport.name || airport.code || 'Unknown Airport';
            const airportCode = airport.code ? `(${airport.code})` : '';
            const travelTime = airport.travel_time || 'N/A';
            
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item travel-segment';
            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <span class="segment-number me-2">${idx + 1}</span>
                        <div>
                            ${airportName} ${airportCode}
                        </div>
                    </div>
                    <div class="travel-time badge bg-info text-white">${travelTime}</div>
                </div>
            `;
            endList.appendChild(listItem);
        });
        
        endAirportsDiv.appendChild(endList);
        airportSection.appendChild(endAirportsDiv);
    }
    
    // Major airports
    if (majorAirports && majorAirports.length > 0) {
        const majorAirportsDiv = document.createElement('div');
        majorAirportsDiv.className = 'mb-3';
        
        const majorTitle = document.createElement('h5');
        majorTitle.className = 'mb-3 d-flex align-items-center';
        majorTitle.innerHTML = `
            <i class="fas fa-plane-departure text-primary me-2"></i>
            Major International Airports
        `;
        majorAirportsDiv.appendChild(majorTitle);
        
        const majorList = document.createElement('div');
        majorList.className = 'list-group';
        
        majorAirports.slice(0, 3).forEach((airport, idx) => {
            const airportName = airport.airport || airport.name || airport.code || 'Unknown Airport';
            const airportCode = airport.code ? `(${airport.code})` : '';
            const travelTime = airport.travel_time || 'N/A';
            
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item travel-segment';
            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <span class="segment-number me-2">${idx + 1}</span>
                        <div>
                            ${airportName} ${airportCode}
                        </div>
                    </div>
                    <div class="travel-time badge bg-info text-white">${travelTime}</div>
                </div>
            `;
            majorList.appendChild(listItem);
        });
        
        majorAirportsDiv.appendChild(majorList);
        airportSection.appendChild(majorAirportsDiv);
    }
    
    return airportSection;
}

function renderTbdGames(tbdGames, mustTeams = []) {
    if (!tbdGames || tbdGames.length === 0) return;
    
    // Convert mustTeams to lowercase for case-insensitive comparison
    const mustTeamsLower = mustTeams.map(team => team.toLowerCase());
    
    const tripResults = document.getElementById('tripResults');
    if (!tripResults) return; // Safety check
    
    const tbdSection = document.createElement('div');
    tbdSection.className = 'card mt-4 fade-in shadow-sm mb-4'; // Added mb-4 for spacing
    
    // TBD header with better styling
    const tbdHeader = document.createElement('div');
    tbdHeader.className = 'card-header bg-light d-flex justify-content-between align-items-center';
    tbdHeader.innerHTML = `
        <h4 class="mb-0">
            <i class="fas fa-calendar-alt text-warning me-2"></i> 
            Upcoming Unscheduled Games
        </h4>
        <span class="badge bg-warning text-dark">${tbdGames.length} games</span>
    `;
    
    // TBD content with enhanced styling
    const tbdContent = document.createElement('div');
    tbdContent.className = 'card-body';
    
    // Group TBD games by date
    const groupedGames = {};
    tbdGames.forEach(game => {
        // Check if game contains must-see team
        if (!game.has_must_team && mustTeamsLower.length > 0) {
            // Parse teams from match string
            const matchParts = game.match.split(' vs ');
            if (matchParts.length === 2) {
                const homeTeam = matchParts[0].toLowerCase();
                const awayTeam = matchParts[1].toLowerCase();
                game.has_must_team = mustTeamsLower.includes(homeTeam) || mustTeamsLower.includes(awayTeam);
            }
        }

        if (!groupedGames[game.date]) {
            groupedGames[game.date] = [];
        }
        groupedGames[game.date].push(game);
    });
    
    // Intro text
    const introText = document.createElement('p');
    introText.className = 'lead';
    introText.innerHTML = `These games don't have confirmed times yet but might be included in your trip once scheduled:`;
    tbdContent.appendChild(introText);
    
    // Create accordion for grouped games
    const accordion = document.createElement('div');
    accordion.className = 'accordion mt-3';
    accordion.id = 'tbd-accordion';
    
    let dateCounter = 0;
    for (const date in groupedGames) {
        dateCounter++;
        const dateId = `tbd-date-${dateCounter}`;
        
        // Create accordion item
        const accordionItem = document.createElement('div');
        accordionItem.className = 'accordion-item';
        
        // Header
        const accordionHeader = document.createElement('h2');
        accordionHeader.className = 'accordion-header';
        accordionHeader.innerHTML = `
            <button class="accordion-button ${dateCounter > 1 ? 'collapsed' : ''}" type="button" 
                    data-bs-toggle="collapse" data-bs-target="#${dateId}">
                <strong>${date}</strong> 
                <span class="badge bg-secondary ms-2">${groupedGames[date].length} games</span>
            </button>
        `;
        
        // Body
        const accordionBody = document.createElement('div');
        accordionBody.id = dateId;
        accordionBody.className = `accordion-collapse collapse ${dateCounter === 1 ? 'show' : ''}`;
        
        const bodyContent = document.createElement('div');
        bodyContent.className = 'accordion-body p-0';
        
        // Games list
        const gamesList = document.createElement('ul');
        gamesList.className = 'list-group list-group-flush';
        
        groupedGames[date].forEach(game => {
            const gameItem = document.createElement('li');
            gameItem.className = `list-group-item ${game.has_must_team ? 'list-group-item-warning' : ''}`;
            
            const location = game.location.replace(' hbf', '');
            
            gameItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        ${game.has_must_team ? '<i class="fas fa-star text-warning me-2"></i>' : ''}
                        <strong>${game.match}</strong> 
                        <span class="text-muted">@ ${location}</span>
                    </div>
                    <span class="badge bg-secondary">${game.league}</span>
                </div>
            `;
            
            gamesList.appendChild(gameItem);
        });
        
        bodyContent.appendChild(gamesList);
        accordionBody.appendChild(bodyContent);
        
        accordionItem.appendChild(accordionHeader);
        accordionItem.appendChild(accordionBody);
        accordion.appendChild(accordionItem);
    }
    
    tbdContent.appendChild(accordion);
    
    // Add footer with tip
    const tbdFooter = document.createElement('div');
    tbdFooter.className = 'card-footer text-center text-muted';
    tbdFooter.innerHTML = `
        <i class="fas fa-info-circle me-1"></i>
        Check back later for updated schedules. These games may become options for your trip once times are confirmed.
    `;
    
    tbdSection.appendChild(tbdHeader);
    tbdSection.appendChild(tbdContent);
    tbdSection.appendChild(tbdFooter);
    
    tripResults.insertBefore(tbdSection, tripResults.firstChild);
}

/**
 * Renders the itinerary for a specific trip variant
 * @param {HTMLElement} container - The container to render the itinerary into
 * @param {Object} group - The trip group data
 * @param {number} variantIndex - The index of the selected variant
 */
function renderItineraryForVariant(container, group, variantIndex) {
    // Clear the container
    container.innerHTML = '';
    
    // Safety checks - keep existing error handling
    if (!group || !group.variation_details) {
        const errorMsg = document.createElement('div');
        errorMsg.className = 'alert alert-warning';
        errorMsg.textContent = 'Unable to display trip details: Missing data';
        container.appendChild(errorMsg);
        return;
    }
    
    // Get the selected variant
    const variant = group.variation_details[variantIndex];
    const variantFull = group.variations ? group.variations[variantIndex] : null;
    
    if (!variant) {
        const errorMsg = document.createElement('div');
        errorMsg.className = 'alert alert-warning';
        errorMsg.textContent = 'Unable to display trip variant: Missing data';
        container.appendChild(errorMsg);
        return;
    }
    
    // Create itinerary with timeline styling
    const itinerary = document.createElement('div');
    itinerary.className = 'itinerary timeline mt-3';
    
    // Create day-by-day itinerary from variant's day_itinerary
    if (variant.day_itinerary && variant.day_itinerary.length > 0) {
        // First, organize travel segments by day for easy lookup
        const travelSegmentsByDay = {};
        if (variant.travel_segments && variant.travel_segments.length > 0) {
            variant.travel_segments.forEach(segment => {
                const day = segment.day || '';
                if (!travelSegmentsByDay[day]) {
                    travelSegmentsByDay[day] = [];
                }
                travelSegmentsByDay[day].push(segment);
            });
        }
        
        // Track previous day's hotel for detecting hotel changes
        let previousHotel = null;
        
        variant.day_itinerary.forEach((dayInfo, dayIndex) => {
            const dayName = dayInfo.day || `Day ${dayIndex + 1}`;
            const isLastDay = dayIndex === variant.day_itinerary.length - 1;
            
            // Day header with improved visual
            const dayHeader = document.createElement('div');
            dayHeader.className = 'day-header mb-3 position-relative';
            dayHeader.innerHTML = `
                <div class="day-badge">${dayIndex + 1}</div>
                <h5 class="mb-0 ms-4 ps-2">Day ${dayIndex + 1}: ${dayName}</h5>
                <div class="day-line"></div>
            `;
            itinerary.appendChild(dayHeader);
            
            // Check for hotel change
            if (dayInfo.hotel) {
                const hotelInfo = document.createElement('div');
                hotelInfo.className = 'hotel-info ms-4 ps-2 mb-3';
                
                // If hotel changed from previous day
                if (previousHotel && previousHotel !== dayInfo.hotel) {
                    hotelInfo.innerHTML = `
                        <div class="d-flex align-items-center text-primary">
                            <i class="fas fa-exchange-alt me-2"></i>
                            <strong>Hotel change: ${previousHotel} → ${dayInfo.hotel}</strong>
                        </div>
                    `;
                } else {
                    hotelInfo.innerHTML = `
                        <div class="d-flex align-items-center text-primary">
                            <i class="fas fa-hotel me-2"></i>
                            <strong>Hotel: ${dayInfo.hotel}</strong>
                        </div>
                    `;
                }
                
                itinerary.appendChild(hotelInfo);
                previousHotel = dayInfo.hotel;
            }
            
            // Add travel segments for this day
            const dayTravelSegments = travelSegmentsByDay[dayName] || [];
            if (dayTravelSegments.length > 0) {
                // Filter out "after game" segments that have 0 travel time
                const filteredSegments = dayTravelSegments.filter(segment => {
                    const context = segment.context || '';
                    const travelTime = segment.travel_time || '';
                    // Keep the segment if it's not an "after game" with zero time
                    return !(
                        context.toLowerCase().includes('after game') && 
                        (travelTime === '0h 0m' || travelTime === '0m' || travelTime === '0')
                    );
                });
                
                // Only create container if we have segments after filtering
                if (filteredSegments.length > 0) {
                    const travelContainer = document.createElement('div');
                    travelContainer.className = 'travel-container ms-4 ps-2 mb-3';
                    
                    filteredSegments.forEach((segment, idx) => {
                        // Clean up location names
                        const fromLocation = typeof segment.from_location === 'string' ? 
                            segment.from_location.replace(' hbf', '') : 'Unknown';
                        const toLocation = typeof segment.to_location === 'string' ? 
                            segment.to_location.replace(' hbf', '') : 'Unknown';
                        
                        // Get context (purpose)
                        const context = segment.context || '';
                        
                        const travelItem = document.createElement('div');
                        travelItem.className = 'travel-item mb-2 p-2 bg-light rounded';
                        travelItem.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-train text-primary me-2"></i>
                                    <div>
                                        Travel: ${fromLocation} → ${toLocation}
                                        ${context ? `<span class="text-muted">(${context})</span>` : ''}
                                    </div>
                                </div>
                                <div class="travel-time badge bg-info text-white">${segment.travel_time || 'Unknown'}</div>
                            </div>
                        `;
                        
                        travelContainer.appendChild(travelItem);
                    });
                    
                    itinerary.appendChild(travelContainer);
                }
            }
            
            // Render matches or rest day
            if (dayInfo.matches && dayInfo.matches.length > 0) {
                // Matches container
                const matchesContainer = document.createElement('div');
                matchesContainer.className = 'matches-container ms-4 ps-2 mb-4';
                
                dayInfo.matches.forEach(match => {
                    const matchItem = document.createElement('div');
                    matchItem.className = match.contains_must_team 
                        ? 'match-item must-team mb-3 p-3 rounded' 
                        : 'match-item mb-3 p-3 rounded';
                    
                    matchItem.innerHTML = `
                        <div class="match-details">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <strong class="match-teams">${match.match}</strong>
                                ${match.contains_must_team ? '<span class="badge bg-warning text-dark">Must-See</span>' : ''}
                            </div>
                            <div class="match-meta d-flex flex-wrap">
                                <div class="me-3 d-flex align-items-center">
                                    <i class="fas fa-map-marker-alt text-danger me-1"></i> 
                                    <span>${match.location}</span>
                                </div>
                                ${match.travel_from ? `
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-train text-primary me-1"></i>
                                    <span>From ${match.travel_from} - ${match.travel_time}</span>
                                </div>` : ''}
                            </div>
                        </div>
                    `;
                    
                    matchesContainer.appendChild(matchItem);
                });
                
                itinerary.appendChild(matchesContainer);
            } else {
                // Rest day
                const restDay = document.createElement('div');
                restDay.className = 'rest-day ms-4 ps-2 mb-4 p-3 bg-light rounded';
                
                const location = dayInfo.locations && dayInfo.locations.length > 0 
                    ? dayInfo.locations[0] 
                    : dayInfo.hotel || '---';
                
                // Find the next location if this is not the last day
                let nextLocation = '---';
                if (!isLastDay && dayIndex + 1 < variant.day_itinerary.length) {
                    const nextDayInfo = variant.day_itinerary[dayIndex + 1];
                    if (nextDayInfo.locations && nextDayInfo.locations.length > 0) {
                        nextLocation = nextDayInfo.locations[0];
                    } else if (nextDayInfo.matches && nextDayInfo.matches.length > 0) {
                        nextLocation = nextDayInfo.matches[0].location;
                    } else if (nextDayInfo.hotel) {
                        nextLocation = nextDayInfo.hotel;
                    }
                }
                
                const restDayMessage = isLastDay 
                    ? `Your trip has come to an end. You can return home from ${location} or explore nearby cities.`
                    : `Take time to explore ${location}, visit local attractions, or travel early to ${nextLocation !== '---' ? nextLocation : 'your next destination'}.`;
                
                const iconClass = isLastDay ? 'fa-flag-checkered' : 'fa-bed';
                
                restDay.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="fas ${iconClass} ${isLastDay ? 'text-success' : 'text-secondary'} me-2"></i>
                        <span>${isLastDay ? 'Final day' : 'Rest day'} in ${location}</span>
                    </div>
                    <div class="text-muted small mt-1">
                        ${restDayMessage}
                    </div>
                `;
                
                itinerary.appendChild(restDay);
            }
        });
    }
    
    // Airport information (keep this section)
    if (variant.airport_distances) {
        const airportData = {
            nearest_airports: variant.airport_distances.end || [],
            closest_major_airports: variant.airport_distances.major || [],
            start_city: variant.start_location?.replace(' hbf', '') || 'starting point',
            end_city: variant.end_location?.replace(' hbf', '') || 'destination'
        };
        
        const airportSection = renderAirportDistances(airportData);
        
        if (airportSection) {
            itinerary.appendChild(airportSection);
        }
    } else if (variant.nearest_airports || variant.closest_major_airports) {
        // Fallback for older data format
        const airportSection = renderAirportDistances({
            nearest_airports: variant.nearest_airports || [],
            closest_major_airports: variant.closest_major_airports || [],
            start_city: variant.start_location?.replace(' hbf', '') || 'starting point', 
            end_city: variant.end_location?.replace(' hbf', '') || 'destination'
        });
        
        if (airportSection) {
            itinerary.appendChild(airportSection);
        }
    }
    
    // Add the itinerary to the container
    container.appendChild(itinerary);
}

// Export the functions so they can be used by other modules
export { renderTripCard, renderTbdGames, extractHotelSummary, renderTravelSegments, renderAirportDistances, renderItineraryForVariant };