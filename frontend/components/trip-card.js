function renderTripCard(group, index) {
    const baseTrip = group.base_trip;
    const tripResults = document.getElementById('tripResults');
    
    if (!tripResults) return; // Safety check
    
    // Get trip duration from DOM or use default
    const tripDurationInput = window.DOM?.tripDurationInput;
    const tripDuration = tripDurationInput ? tripDurationInput.value : "3";
    
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
                <i class="fas fa-map-marker-alt text-danger me-1"></i> 
                <span>${defaultVariant.cities?.length || 0} cities</span>
            </div>
            <div class="me-3 d-flex align-items-center">
                <i class="fas fa-clock text-success me-1"></i>
                <span>${defaultVariant.travel_hours || 0}h ${defaultVariant.travel_minutes || 0}m travel</span>
            </div>
            <div class="me-3 d-flex align-items-center">
                <i class="fas fa-calendar-alt text-primary me-1"></i>
                <span>${tripDuration} days</span>
            </div>
            <div class="me-3 d-flex align-items-center">
                <i class="fas fa-route text-info me-1"></i>
                <span>${firstCity} → ${finalCity}</span>
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
    
    // Itinerary with timeline styling
    const itinerary = document.createElement('div');
    itinerary.className = 'itinerary timeline mt-3';
    
    // Group items by day, but preserve order
    const dayMap = {};
    const dayOrder = [];
    
    baseTrip.Itinerary.forEach(dayItem => {
        const dayName = dayItem.day || 'Unknown';
        if (!dayMap[dayName]) {
            dayMap[dayName] = { matches: [], location: null };
            dayOrder.push(dayName);
        }
        
        if (dayItem.matches) {
            dayMap[dayName].matches.push(...dayItem.matches);
        }
        
        // Always store the location if it exists, not just for rest days
        if (dayItem.location) {
            dayMap[dayName].location = dayItem.location;
        }
    });
    
    // Create timeline for each day
    dayOrder.forEach((dayName, dayIndex) => {
        const dayInfo = dayMap[dayName];
        const isLastDay = dayIndex === dayOrder.length - 1; // Check if this is the last day
        
        // Day header with improved visual
        const dayHeader = document.createElement('div');
        dayHeader.className = 'day-header mb-3 position-relative';
        dayHeader.innerHTML = `
            <div class="day-badge">${dayIndex + 1}</div>
            <h5 class="mb-0 ms-4 ps-2">Day ${dayIndex + 1}: ${dayName}</h5>
            <div class="day-line"></div>
        `;
        itinerary.appendChild(dayHeader);
        
        if (dayInfo.matches && dayInfo.matches.length > 0) {
            // Render matches with enhanced styling
            const matchesContainer = document.createElement('div');
            matchesContainer.className = 'matches-container ms-4 ps-2 mb-4';
            
            dayInfo.matches.forEach(match => {
                const matchItem = document.createElement('div');
                matchItem.className = match.contains_must_team 
                    ? 'match-item must-team mb-3 p-3 rounded' 
                    : 'match-item mb-3 p-3 rounded';
                
                const matchLocation = match.location.replace(' hbf', '');
                const fromLocation = match.travel_from ? match.travel_from.replace(' hbf', '') : '';
                
                // Enhanced match item with team logos, time
                matchItem.innerHTML = `
                    <div class="match-details">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong class="match-teams">${match.match}</strong>
                            ${match.contains_must_team ? '<span class="badge bg-warning text-dark">Must-See</span>' : ''}
                        </div>
                        <div class="match-meta d-flex flex-wrap">
                            <div class="me-3 d-flex align-items-center">
                                <i class="fas fa-map-marker-alt text-danger me-1"></i> 
                                <span>${matchLocation}</span>
                            </div>
                            ${match.travel_from ? `
                            <div class="d-flex align-items-center">
                                <i class="fas fa-train text-primary me-1"></i>
                                <span>From ${fromLocation} - ${match.travel_time}</span>
                            </div>` : ''}
                        </div>
                    </div>
                `;
                
                matchesContainer.appendChild(matchItem);
            });
            
            itinerary.appendChild(matchesContainer);
        } else {
            // Enhanced rest day display
            const restDay = document.createElement('div');
            restDay.className = 'rest-day ms-4 ps-2 mb-4 p-3 bg-light rounded';
            
            let location = dayInfo.location ? dayInfo.location.replace(' hbf', '') : '---';
            
            // Find the next city if this is not the last day
            let nextCity = '---';
            if (!isLastDay && dayIndex + 1 < dayOrder.length) {
                const nextDayName = dayOrder[dayIndex + 1];
                const nextDayInfo = dayMap[nextDayName];
                
                if (nextDayInfo.location) {
                    nextCity = nextDayInfo.location.replace(' hbf', '');
                } else if (nextDayInfo.matches && nextDayInfo.matches.length > 0) {
                    // If no direct location for the day, try to get it from the first match
                    nextCity = nextDayInfo.matches[0].location.replace(' hbf', '');
                }
            }
            
            // Different message based on whether it's the last day
            const restDayMessage = isLastDay 
                ? `Your trip has come to an end. You can return home from ${location} or explore nearby cities. Check airport information below for travel options.`
                : `Take time to explore ${location}, visit local attractions, or travel early to ${nextCity !== '---' ? nextCity : 'your next destination'}. A rest day gives you flexibility to enjoy the cities at your own pace.`;
            
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
    
    // NEW: Travel Options Section - with multiple options
    if (group.variations && group.variations.length > 0) {
        const travelOptionsSection = document.createElement('div');
        travelOptionsSection.className = 'travel-options-section mt-4 mb-3';
        
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
        
        // Create each option tab and content
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
                Option ${varIdx + 1} <span class="option-time ms-1">(${variant.travel_hours || 0}h ${variant.travel_minutes || 0}m)</span>
            `;
            optionsTabs.appendChild(tab);
            
            // Create content pane
            const contentPane = document.createElement('div');
            contentPane.className = `tab-pane fade ${isActive ? 'show active' : ''}`;
            contentPane.id = optionId;
            contentPane.setAttribute('role', 'tabpanel');
            contentPane.setAttribute('aria-labelledby', `${optionId}-tab`);
            
            // Travel segments list
            const segmentsList = renderTravelSegments(variant);
            
            // Airport Information if available
            if (variant.airports && variant.airports.length > 0) {
                const airportInfo = document.createElement('div');
                airportInfo.className = 'airport-info bg-light rounded p-3 mt-3';
                
                let finalCity = variant.final_city || 
                    (variant.travel_segments && variant.travel_segments.length > 0 ? 
                        variant.travel_segments[variant.travel_segments.length - 1].to_location : '');
                
                if (finalCity) {
                    finalCity = finalCity.replace(' hbf', '');
                    
                    airportInfo.innerHTML = `
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas fa-plane text-info me-2"></i>
                            <strong>Nearest airports to ${finalCity}:</strong>
                        </div>
                        <ul class="list-unstyled ms-4 mb-0">
                            ${variant.airports.map(airport => 
                                `<li class="mb-1">
                                    <i class="fas fa-plane-departure text-info me-1"></i> 
                                    ${airport.name} (${airport.travel_time})
                                </li>`
                            ).join('')}
                        </ul>
                    `;
                    
                    contentPane.appendChild(airportInfo);
                }
            }
            
            // Return trip info if available
            if (variant.return_trip) {
                const returnInfo = document.createElement('div');
                returnInfo.className = 'return-info bg-light rounded p-3 mt-3';
                
                const startLocation = variant.return_trip.start_location || '';
                const endLocation = variant.return_trip.end_location || '';
                const travelTime = variant.return_trip.travel_time || '';
                
                returnInfo.innerHTML = `
                    <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-undo text-warning me-2"></i>
                        <strong>Return to start location:</strong>
                    </div>
                    <div class="ms-4">
                        <i class="fas fa-long-arrow-alt-right me-1"></i>
                        ${startLocation.replace(' hbf', '')} → ${endLocation.replace(' hbf', '')} - ${travelTime}
                    </div>
                `;
                
                contentPane.appendChild(returnInfo);
            }
            
            // Add segments list (always last)
            contentPane.appendChild(segmentsList);
            
            // Add to main content container
            optionsContent.appendChild(contentPane);
        });
        
        // Add tabs and content to travel options section
        travelOptionsSection.appendChild(optionsTabs);
        travelOptionsSection.appendChild(optionsContent);
        
        // Add travel options to itinerary
        itinerary.appendChild(travelOptionsSection);
    }
    
    // INSERT HERE - Add airport distances section if available
    if (defaultVariant.airport_distances) {
        // Add city context to airport distances
        const airportDistancesWithCities = {
            ...defaultVariant.airport_distances,
            start_city: defaultVariant.start_location?.replace(' hbf', '') || 'starting point',
            end_city: defaultVariant.end_location?.replace(' hbf', '') || 'destination'
        };
        
        const airportSection = renderAirportDistances(airportDistancesWithCities);
        if (airportSection) {
            itinerary.appendChild(airportSection);
        }
    }
    
    details.appendChild(itinerary);
    
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

function renderTravelSegments(variant) {
    const segmentsContainer = document.createElement('div');
    segmentsContainer.className = 'travel-segments mt-3';
    
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
        
        const fromLocation = segment.from_location.replace(' hbf', '');
        const toLocation = segment.to_location.replace(' hbf', '');
        const context = segment.context || segment.day || '';
        
        segmentItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <span class="segment-number me-2">${idx + 1}</span>
                    <div>
                        ${fromLocation} → ${toLocation} 
                        ${context ? `<span class="text-muted">(${context})</span>` : ''}
                    </div>
                </div>
                <div class="travel-time badge bg-info text-white">${segment.travel_time}</div>
            </div>
        `;
        
        segmentsList.appendChild(segmentItem);
    });
    
    segmentsContainer.appendChild(segmentsList);
    return segmentsContainer;
}

function renderTbdGames(tbdGames) {
    if (!tbdGames || tbdGames.length === 0) return;
    
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
    
    // Use insertBefore instead of appendChild to put at the beginning
    if (tripResults.firstChild) {
        tripResults.insertBefore(tbdSection, tripResults.firstChild);
    } else {
        tripResults.appendChild(tbdSection);
    }
}

function renderAirportDistances(airportDistances) {
    if (!airportDistances) return null;
    
    const container = document.createElement('div');
    container.className = 'airport-distances mt-4';
    
    // Create header
    const header = document.createElement('h5');
    header.className = 'mb-3';
    header.innerHTML = '<i class="fas fa-plane me-2"></i> Airport Information';
    container.appendChild(header);
    
    // Get city names for context
    const startCity = airportDistances.start_city || 'starting point';
    const endCity = airportDistances.end_city || 'final destination';
    
    // Create tab navigation for start/end airports
    const nav = document.createElement('div');
    nav.className = 'nav nav-tabs mb-3';
    nav.innerHTML = `
        <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#start-airports">
            <i class="fas fa-plane-arrival me-1"></i> Airports Near ${startCity}
        </button>
        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#end-airports">
            <i class="fas fa-plane-departure me-1"></i> Airports Near ${endCity}
        </button>
    `;

    container.appendChild(nav);
    
    // Create tab content
    const tabContent = document.createElement('div');
    tabContent.className = 'tab-content';
    
    // Start airports tab
    const startAirportsTab = document.createElement('div');
    startAirportsTab.className = 'tab-pane fade show active';
    startAirportsTab.id = 'start-airports';
    
    if (airportDistances.start && airportDistances.start.length > 0) {
        const startList = document.createElement('div');
        startList.className = 'list-group';
        
        airportDistances.start.forEach(airport => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            item.innerHTML = `
                <div>
                    <i class="fas fa-plane-arrival text-primary me-2"></i>
                    <strong>${airport.airport}</strong> Airport
                </div>
                <span class="badge bg-info text-white" title="Travel time to ${startCity}">
                    ${airport.travel_time} to ${startCity}
                </span>
            `;
            startList.appendChild(item);
        });
        
        startAirportsTab.appendChild(startList);
    } else {
        startAirportsTab.innerHTML = '<div class="alert alert-info">No airport information available</div>';
    }
    
    // End airports tab
    const endAirportsTab = document.createElement('div');
    endAirportsTab.className = 'tab-pane fade';
    endAirportsTab.id = 'end-airports';
    
    if (airportDistances.end && airportDistances.end.length > 0) {
        const endList = document.createElement('div');
        endList.className = 'list-group';
        
        airportDistances.end.forEach(airport => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            item.innerHTML = `
                <div>
                    <i class="fas fa-plane-departure text-success me-2"></i>
                    <strong>${airport.airport}</strong> Airport
                </div>
                <span class="badge bg-info text-white" title="Travel time from ${endCity}">
                    ${airport.travel_time} from ${endCity}
                </span>
            `;
            endList.appendChild(item);
        });
        
        endAirportsTab.appendChild(endList);
    } else {
        endAirportsTab.innerHTML = '<div class="alert alert-info">No airport information available</div>';
    }
    
    tabContent.appendChild(startAirportsTab);
    tabContent.appendChild(endAirportsTab);
    container.appendChild(tabContent);
    
    return container;
}

export { renderTripCard, renderTbdGames, renderAirportDistances };