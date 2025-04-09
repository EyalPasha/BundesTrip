import { getTeamLogoUrl } from '../services/team-logos.js';

/**
 * Date formatting helper functions
 */

// Parse various date formats into Date objects
function parseDate(dateString) {
  if (!dateString) return null;
  
  // Try to handle various date formats
  const monthNames = {
    'january': 0, 'jan': 0, 'february': 1, 'feb': 1, 'march': 2, 'mar': 2, 
    'april': 3, 'apr': 3, 'may': 4, 'june': 5, 'jun': 5, 'july': 6, 'jul': 6, 
    'august': 7, 'aug': 7, 'september': 8, 'sep': 8, 'sept': 8, 
    'october': 9, 'oct': 9, 'november': 10, 'nov': 10, 'december': 11, 'dec': 11
  };
  
  // Remove any day of week prefix if present (e.g., "Monday, ")
  const cleanedDateString = dateString.replace(/^[a-zA-Z]+,\s*/, '');
  
  // Try standard format: "10 April 2025"
  const regex = /(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})/;
  const match = cleanedDateString.match(regex);
  
  if (match) {
    const day = parseInt(match[1], 10);
    const monthStr = match[2].toLowerCase();
    const year = parseInt(match[3], 10);
    
    const monthIndex = monthNames[monthStr];
    if (monthIndex !== undefined) {
      return new Date(year, monthIndex, day);
    }
  }
  
  // If the above didn't work, try parsing directly
  const fallbackDate = new Date(cleanedDateString);
  if (!isNaN(fallbackDate.getTime())) {
    return fallbackDate;
  }
  
  return null;
}

// Get the day name for a date
function getDayName(date) {
  if (!date || !(date instanceof Date)) return '';
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return days[date.getDay()];
}

// Format date as "day Month" (e.g., "10 April") without leading zeros
function formatShortDate(date) {
  if (!date || !(date instanceof Date)) return '';
  
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  
  return `${date.getDate()} ${months[date.getMonth()]}`;
}

// Format date range as "day Month-day Month year" (e.g., "10 April-14 April 2025")
function formatDateRange(startDate, endDate) {
  if (!startDate || !endDate) return '';
  
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  
  // Use the same year only if the years match
  if (startDate.getFullYear() === endDate.getFullYear()) {
    return `${startDate.getDate()} ${months[startDate.getMonth()]}-${endDate.getDate()} ${months[endDate.getMonth()]} ${endDate.getFullYear()}`;
  } else {
    return `${startDate.getDate()} ${months[startDate.getMonth()]} ${startDate.getFullYear()}-${endDate.getDate()} ${months[endDate.getMonth()]} ${endDate.getFullYear()}`;
  }
}

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
    tripCard.className = 'card trip-card fade-in shadow-sm'; // Remove mb-4 class
    tripCard.dataset.teams = defaultVariant.teams?.join(',') || '';
    tripCard.dataset.cities = defaultVariant.cities?.join(',') || '';
    tripCard.dataset.tripGroup = JSON.stringify(group);
    
    // Trip header - enhanced with more information
    const header = document.createElement('div');
    header.className = 'trip-header position-relative';

    // Get first and last cities
    const firstCity = defaultVariant.start_location?.replace(' hbf', '') || 
                     (defaultVariant.cities?.length > 0 ? defaultVariant.cities[0] : 'Unknown');
    const finalCity = defaultVariant.end_location?.replace(' hbf', '') || 
                     (defaultVariant.cities?.length > 0 ? defaultVariant.cities[defaultVariant.cities.length - 1] : 'Unknown');

    // Extract start and end dates for the trip
    let tripStartDate = '';
    let tripEndDate = '';

    if (defaultVariant.day_itinerary && defaultVariant.day_itinerary.length > 0) {
        // Get the first day
        const firstDay = defaultVariant.day_itinerary[0];
        if (firstDay.day) {
            // Try a few different date extraction patterns
            let dateMatch = firstDay.day.match(/,\s*(.+)$/);
            if (dateMatch && dateMatch[1]) {
                tripStartDate = dateMatch[1].trim();
            } else if (firstDay.day.includes(' - ')) {
                // Try extracting from "Day X - Date" format
                dateMatch = firstDay.day.match(/\s*-\s*(.+)$/);
                if (dateMatch && dateMatch[1]) {
                    tripStartDate = dateMatch[1].trim();
                }
            } else {
                // If it looks like a date directly, use it
                if (/\d{1,2}\s+[A-Za-z]+\s+\d{4}/.test(firstDay.day)) {
                    tripStartDate = firstDay.day;
                }
            }
        }
        
        // Get the last day
        const lastDay = defaultVariant.day_itinerary[defaultVariant.day_itinerary.length - 1];
        if (lastDay.day) {
            // Try a few different date extraction patterns (same as above)
            let dateMatch = lastDay.day.match(/,\s*(.+)$/);
            if (dateMatch && dateMatch[1]) {
                tripEndDate = dateMatch[1].trim();
            } else if (lastDay.day.includes(' - ')) {
                // Try extracting from "Day X - Date" format
                dateMatch = lastDay.day.match(/\s*-\s*(.+)$/);
                if (dateMatch && dateMatch[1]) {
                    tripEndDate = dateMatch[1].trim();
                }
            } else {
                // If it looks like a date directly, use it
                if (/\d{1,2}\s+[A-Za-z]+\s+\d{4}/.test(lastDay.day)) {
                    tripEndDate = lastDay.day;
                }
            }
        }
        
    }

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
                const { time, cleanMatch } = extractTimeFromMatch(match.match);
                allMatches.push({
                    match: cleanMatch,
                    matchTime: time,
                    date: day.day,
                    location: match.location.replace(' hbf', ''),
                    contains_must_team: match.contains_must_team || false
                });
            });
        }
    });

    // Extract hotel info with dates for preview
    const hotelSummary = [];
    if (defaultVariant.day_itinerary && defaultVariant.day_itinerary.length > 0) {
        let currentHotel = null;
        let startDate = null;
        let endDate = null;
        
        defaultVariant.day_itinerary.forEach((dayInfo, index) => {
            if (!dayInfo.hotel) return;
            
            // Extract date in a readable format
            let dateDisplay = '';
            if (dayInfo.day) {
                // Extract only the date part after the comma
                const dateMatch = dayInfo.day.match(/,\s*(.+)$/);
                if (dateMatch && dateMatch[1]) {
                    dateDisplay = dateMatch[1].trim();
                } else {
                    // If no comma found, just use the whole day string
                    dateDisplay = dayInfo.day;
                }
            }
            
            if (currentHotel !== dayInfo.hotel) {
                // If we have a previous hotel, add it to the summary
                if (currentHotel) {
                    hotelSummary.push({
                        hotel: currentHotel,
                        startDate: startDate,
                        endDate: endDate || startDate
                    });
                }
                // Start new hotel stay
                currentHotel = dayInfo.hotel;
                startDate = dateDisplay || `Day ${index + 1}`;
                endDate = dateDisplay || `Day ${index + 1}`;
            } else {
                // Continue current hotel stay
                endDate = dateDisplay || `Day ${index + 1}`;
            }
        });
        
        // Add the last hotel
        if (currentHotel) {
            hotelSummary.push({
                hotel: currentHotel,
                startDate: startDate,
                endDate: endDate
            });
        }
    }
    // Get the end city for airport preview
    let endCityForAirports = '';
    if (defaultVariant.end_location) {
        endCityForAirports = defaultVariant.end_location.replace(' hbf', '');
    } else if (defaultVariant.cities && defaultVariant.cities.length > 0) {
        endCityForAirports = defaultVariant.cities[defaultVariant.cities.length - 1];
    }
    
    header.innerHTML = `
    <div class="trip-header-main">
        <h3>Trip ${index}</h3>
        <span class="match-count-badge">${defaultVariant.num_games || 0} matches</span>
    </div>
    
    <div class="trip-header-meta">
        <div class="trip-meta-item">
            <i class="fas fa-calendar-alt"></i>
            <span>
                ${tripStartDate && tripEndDate ? 
                  `<span class="date-range">${tripStartDate} - ${tripEndDate}</span>` : 
                  ''}
            </span>
        </div>
        <div class="trip-meta-item">
            <i class="fas fa-sliders-h"></i>
            <span>${group.variation_details.length} travel options</span>
        </div>
    </div>
    
    ${allMatches.length > 0 ? `
        <div class="match-preview">
            <div class="preview-section-title">
                <i class="fas fa-futbol"></i> Matches
            </div>
            <div class="match-list">
                ${allMatches.slice(0, Math.min(3, allMatches.length)).map(match => {
                    // Extract teams from match text
                    const teams = match.match.split(' vs ');
                    const homeTeam = teams[0] || '';
                    const awayTeam = teams[1] || '';
                    
                    // First extract just the date part (remove day name)
                    const matchDate = match.date.replace(/^.+,\s*/, '');

                    return `
                        <div class="match-preview-item ${match.contains_must_team ? 'must-match' : ''}">
                            <div class="match-content-grid">
                                <!-- Location on left -->
                                <div class="match-location-side">
                                    <i class="fas fa-map-marker-alt"></i> ${match.location}
                                </div>
                                
                                <!-- Teams in center -->
                                <div class="match-teams-preview">
                                    <strong>${homeTeam}</strong>
                                    <img src="${getTeamLogoUrl(homeTeam)}" class="team-logo-small" alt="${homeTeam} logo">
                                    <span class="vs-text">vs</span>
                                    <img src="${getTeamLogoUrl(awayTeam)}" class="team-logo-small" alt="${awayTeam} logo">
                                    <strong>${awayTeam}</strong>
                                </div>
                                
                                <!-- Date and time on right -->
                                <div class="match-datetime-side">
                                    <span class="match-date-inline">
                                        <i class="fas fa-calendar-day"></i> ${matchDate}
                                    </span>
                                    ${match.matchTime ? `
                                    <span class="match-time-data">
                                        <i class="fas fa-clock"></i> ${match.matchTime}
                                    </span>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
                ${allMatches.length > 3 ? `
                    <div class="more-matches-indicator">
                        +${allMatches.length - 3} more matches
                    </div>
                ` : ''}
            </div>
        </div>
    ` : ''}
    
    <button class="toggle-details-button" type="button">
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
    optionsTabs.setAttribute('role', 'tablist'); // Add this for accessibility
    optionsTabs.setAttribute('aria-label', `Trip ${index} travel options`); // Add this for better accessibility

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

            // First, extract hotel summary for this variant
            const hotelSummary = [];
            if (variant.day_itinerary && variant.day_itinerary.length > 0) {
                let currentHotel = null;
                let startDate = null;
                let endDate = null;
                
                variant.day_itinerary.forEach((dayInfo, idx) => {
                    if (!dayInfo.hotel) return;
                    
                    // Extract date in a readable format
                    let dateDisplay = '';
                    if (dayInfo.day) {
                        const dateMatch = dayInfo.day.match(/,\s*(.+)$/);
                        if (dateMatch && dateMatch[1]) {
                            dateDisplay = dateMatch[1].trim();
                        } else {
                            dateDisplay = dayInfo.day;
                        }
                    }
                    
                    if (currentHotel !== dayInfo.hotel) {
                        // If we have a previous hotel, add it to the summary
                        if (currentHotel) {
                            hotelSummary.push({
                                hotel: currentHotel,
                                startDate: startDate,
                                endDate: endDate || startDate
                            });
                        }
                        // Start new hotel stay
                        currentHotel = dayInfo.hotel;
                        startDate = dateDisplay || `Day ${idx + 1}`;
                        endDate = dateDisplay || `Day ${idx + 1}`;
                    } else {
                        // Continue current hotel stay
                        endDate = dateDisplay || `Day ${idx + 1}`;
                    }
                });
                
                // Add the last hotel
                if (currentHotel) {
                    hotelSummary.push({
                        hotel: currentHotel,
                        startDate: startDate,
                        endDate: endDate
                    });
                }
            }

            // Add complete travel option info with modern styling
            
            contentPane.innerHTML = `
                <div class="variant-summary">
                    <!-- Main Summary Header - Combined Stats -->
                    <div class="trip-summary-header">
                        <div class="trip-summary-icon">
                            <i class="fas ${varIdx === 0 ? 'fa-star' : 'fa-route'}"></i>
                        </div>
                        <div class="trip-summary-details">
                            <div class="trip-time-info">
                                <i class="fas fa-clock"></i> ${variant.travel_hours || 0}h ${variant.travel_minutes || 0}m total travel
                            </div>
                            <div class="trip-meta-info">
                                <span><i class="fas fa-map-marker-alt"></i> ${variant.cities?.length || 0} cities</span>
                                <span><i class="fas fa-hotel"></i> ${variant.hotel_changes || 0} hotel changes</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Organized Content Grid -->
                    <div class="summary-content-grid">
                        <!-- Hotels Section -->
                        ${hotelSummary.length > 0 ? `
                            <div class="hotels-section">
                                <div class="section-heading">
                                    <i class="fas fa-hotel"></i> Accommodations
                                </div>
                                <div class="hotel-stays-list">
                                    ${hotelSummary.map(stay => renderHotelStayItem(stay)).join('')}
                                </div>
                            </div>
                        ` : ''}
                        
                        <!-- Airport Section -->
                        ${variant.airport_distances ? `
                            <div class="airports-section">
                                <div class="section-heading">
                                    <i class="fas fa-plane-departure"></i> Airports near ${finalCity}
                                </div>
                                <div class="airport-list">
                                    ${(variant.airport_distances.end || []).slice(0, 2).map(airport => {
                                        const airportName = airport.airport || airport.name || airport.code || 'Airport';
                                        const airportCode = airport.code ? `(${airport.code})` : '';
                                        return `
                                            <div class="airport-item">
                                                <span class="airport-name">${airportName}</span>
                                                <span class="travel-time">${airport.travel_time}</span>
                                            </div>
                                        `;
                                    }).join('')}
                                    ${(variant.airport_distances.major || []).slice(0, 1).map(airport => {
                                        const airportName = airport.airport || airport.name || airport.code || 'Airport';
                                        return `
                                            <div class="airport-item">
                                                <span class="airport-name">${airportName}</span>
                                                <span class="travel-time">${airport.travel_time}</span>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        ` : ''}
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
    
    // Add section headers before timeline
    const timelineHeader = document.createElement('div');
    timelineHeader.innerHTML = `
      <h5 class="mb-3 d-flex align-items-center">
        <i class="fas fa-calendar-alt text-primary me-2"></i> Day-by-Day Itinerary
      </h5>
    `;
    details.appendChild(timelineHeader);
    
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
    const toggleButton = tripCard.querySelector('.toggle-details-button');
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

function renderTbdGames(tbdGames, mustTeams = [], noTripsFound = false) {
    if (!tbdGames || tbdGames.length === 0) return;
    
    // If no trips found, don't render the TBD games
    if (noTripsFound) {
        // Just return without rendering anything
        // The no trips animation will be handled by the results-display.js file
        return;
    }
    
    // Convert mustTeams to lowercase for case-insensitive comparison
    const mustTeamsLower = mustTeams.map(team => team.toLowerCase());
    
    const tripResults = document.getElementById('tripResults');
    if (!tripResults) return; // Safety check
    
    const tbdSection = document.createElement('div');
    tbdSection.className = 'card trip-card fade-in shadow-sm mb-4'; 
    tbdSection.id = 'tbdGamesSection';
    
    // More compact TBD header
    const tbdHeader = document.createElement('div');
    tbdHeader.className = 'trip-header position-relative';
    tbdHeader.innerHTML = `
        <div class="trip-header-main">
            <h3><i class="fas fa-calendar-alt text-secondary me-2"></i>Upcoming Games</h3>
            <span class="match-count-badge">${tbdGames.length}</span>
        </div>
        <div class="trip-header-meta">
            <div class="trip-meta-item">
                <i class="fas fa-info-circle"></i>
                <span>Games with unconfirmed times that may be included once scheduled</span>
            </div>
        </div>
    `;
    
    // TBD content with improved styling matching trip cards
    const tbdContent = document.createElement('div');
    tbdContent.className = 'p-2';
    
    // Group TBD games by date
    const groupedGames = {};
    tbdGames.forEach(game => {
        // Check if game contains must-see team
        if (!game.has_must_team && mustTeamsLower.length > 0) {
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
    
    // Create accordion for grouped games
    const accordion = document.createElement('div');
    accordion.className = 'accordion';
    accordion.id = 'tbd-accordion';
    
    let dateCounter = 0;
    for (const date in groupedGames) {
        dateCounter++;
        const dateId = `tbd-date-${dateCounter}`;
        
        // Create accordion item with more compact styling
        const accordionItem = document.createElement('div');
        accordionItem.className = 'accordion-item border-0 mb-2';
        
        // Header styling - all collapsed by default
        const accordionHeader = document.createElement('h2');
        accordionHeader.className = 'accordion-header';
        accordionHeader.innerHTML = `
            <button class="accordion-button collapsed shadow-sm" 
                    type="button" data-bs-toggle="collapse" data-bs-target="#${dateId}">
                <div class="d-flex align-items-center justify-content-between w-100">
                    <div>
                        <i class="fas fa-calendar-day me-1"></i>
                        <span>${date}</span>
                    </div> 
                    <span class="badge bg-primary">${groupedGames[date].length}</span>
                </div>
            </button>
        `;
        
        // Body with consistent styling - all collapsed by default
        const accordionBody = document.createElement('div');
        accordionBody.id = dateId;
        accordionBody.className = 'accordion-collapse collapse'; 
        
        const bodyContent = document.createElement('div');
        bodyContent.className = 'accordion-body p-2';
        
        // Games list styled like match preview items
        const gamesList = document.createElement('div');
        gamesList.className = 'match-preview';
        
        groupedGames[date].forEach(game => {
            const location = game.location.replace(' hbf', '');
            
            // Extract teams - assuming game.match contains "Team A vs Team B" format
            const teams = game.match.split(' vs ');
            const homeTeam = teams[0] || '';
            const awayTeam = teams[1] || '';
            
            const gameItem = document.createElement('div');
            gameItem.className = 'match-preview-item' + 
                (game.has_must_team ? ' must-match' : '');
                        
            // New grid-based layout with proper team-logo-vs-logo-team order
            gameItem.innerHTML = `
                <div class="tbd-match-teams-grid">
                    <div class="tbd-home-team">${homeTeam}</div>
                    <img src="${getTeamLogoUrl(homeTeam)}" class="tbd-home-logo" alt="${homeTeam} logo">
                    <div class="tbd-vs-container">vs</div>
                    <img src="${getTeamLogoUrl(awayTeam)}" class="tbd-away-logo" alt="${awayTeam} logo">
                    <div class="tbd-away-team">${awayTeam}</div>
                    <span class="tbd-location">
                        <i class="fas fa-map-marker-alt"></i> ${game.location || 'TBD'}
                    </span>
                    ${game.has_must_team ? '<span class="tbd-must-see-badge">Must-See</span>' : ''}
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
    
    tbdSection.appendChild(tbdHeader);
    tbdSection.appendChild(tbdContent);
    
    // Insert at the beginning of the results
    tripResults.insertBefore(tbdSection, tripResults.firstChild);
    
    // Add "No trips found" message if specified
    if (noTripsFound) {
        const noTripsMessage = document.createElement('div');
        noTripsMessage.className = 'no-trips-message fade-in';
        noTripsMessage.innerHTML = `
            <div class="alert-content">
                <i class="fas fa-info-circle"></i>
                <div class="message-text">
                    <h4>No Trips Available</h4>
                    <p>We couldn't find any trips matching your criteria, but we've displayed some upcoming games above that may interest you.</p>
                </div>
            </div>
            <div class="suggestion-text">Try adjusting your search filters for better results.</div>
        `;
        
        // Insert the message after the TBD games section
        tripResults.insertBefore(noTripsMessage, tbdSection.nextSibling);
        
        // Scroll to TBD games section with slight delay to allow rendering
        setTimeout(() => {
            tbdSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);
    }
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
        // First, create travel segments from match data if not present
        if (!variant.travel_segments || variant.travel_segments.length === 0) {
            variant.travel_segments = [];
            
            // Extract travel segments from match data in day_itinerary
            variant.day_itinerary.forEach((dayInfo, idx) => {
                if (dayInfo.matches && dayInfo.matches.length > 0) {
                    dayInfo.matches.forEach(match => {
                        if (match.travel_from && match.travel_time) {
                            variant.travel_segments.push({
                                day: dayInfo.day,
                                from_location: match.travel_from,
                                to_location: match.location,
                                travel_time: match.travel_time,
                            });
                        }
                    });
                }
            });
            
        }
        
        // Organize travel segments by day for easy lookup
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
            const hotel = dayInfo.hotel || '';
            
            // Extract date display for day header
            let dateDisplay = '';
            if (dayInfo.day) {
                // Extract date in a readable format
                const dateMatch = dayInfo.day.match(/,\s*(.+)$/);
                if (dateMatch && dateMatch[1]) {
                    dateDisplay = dateMatch[1].trim();
                } else {
                    dateDisplay = dayInfo.day;
                }
            }

            // Day header with hotel name and date on same line
            const dayHeader = document.createElement('div');
            dayHeader.className = `day-header ${isLastDay ? 'final-day' : ''}`;
            dayHeader.innerHTML = formatDayHeader(dayInfo, dayIndex);
            itinerary.appendChild(dayHeader);
            
            // Get travel segments for this day
            let dayTravelSegments = travelSegmentsByDay[dayName] || [];
            
            // For the last day, also check travel segments from matches
            if (isLastDay && dayTravelSegments.length === 0 && dayInfo.matches) {
                dayInfo.matches.forEach(match => {
                    if (match.travel_from && match.travel_time) {
                        // Create a travel segment directly from the match data
                        dayTravelSegments.push({
                            from_location: match.travel_from,
                            to_location: match.location,
                            travel_time: match.travel_time,
                        });
                    }
                });
            }
            
            // Split segments as before...
            const beforeGameSegments = [];
            const afterGameSegments = [];
            
            dayTravelSegments.forEach(segment => {
                // Filter out zero-time segments in all cases
                const travelTime = segment.travel_time || '';
                if (travelTime === '0h 0m' || travelTime === '0m' || travelTime === '0') {
                    return; // Skip this segment entirely
                }
                
                const context = segment.context || '';
                if (context.toLowerCase().includes('after game')) {
                    afterGameSegments.push(segment);
                } else {
                    beforeGameSegments.push(segment);
                }
            });

            // Render before-game segments
            if (beforeGameSegments.length > 0) {
                const travelContainer = document.createElement('div');
                travelContainer.className = 'travel-container ms-4 ps-2 mb-3';
                
                beforeGameSegments.forEach(segment => renderTravelSegmentItem(segment, travelContainer));
                itinerary.appendChild(travelContainer);
            }
            
            // Render matches or rest day
            if (dayInfo.matches && dayInfo.matches.length > 0) {
                // Matches container
                const matchesContainer = document.createElement('div');
                matchesContainer.className = 'matches-container ms-4 ps-2 mb-4';
                
                dayInfo.matches.forEach(match => {
                    // Extract the time from the match title FIRST
                    const { time, cleanMatch } = extractTimeFromMatch(match.match);
                    
                    // THEN split the clean match text (without time)
                    const teams = cleanMatch.split(' vs ');
                    const homeTeam = (teams[0] || '').trim();
                    const awayTeam = (teams[1] || '').trim();
                    
                    const matchItem = document.createElement('div');
                    matchItem.className = match.contains_must_team 
                        ? 'match-item must-team' 
                        : 'match-item';
                    
                    matchItem.innerHTML = `
                        <div class="match-header">
                            <div class="match-teams">
                                <img src="${getTeamLogoUrl(homeTeam)}" class="team-logo" alt="${homeTeam} logo">
                                ${homeTeam}
                                <span class="vs-text">vs</span>
                                <img src="${getTeamLogoUrl(awayTeam)}" class="team-logo" alt="${awayTeam} logo">
                                ${awayTeam}
                            </div>
                            ${match.contains_must_team ? '<span class="must-see-tag">Must-See Match</span>' : ''}
                        </div>
                        <div class="match-meta">
                            <div class="match-location-container">
                                <i class="fas fa-map-marker-alt"></i> 
                                <span>${match.location}</span>
                                ${time ? `
                                <span class="match-time-data">
                                    <i class="fas fa-clock"></i>
                                    ${time}
                                </span>` : ''}
                            </div>
                        </div>
                    `;
                    
                    matchesContainer.appendChild(matchItem);
                });
                
                itinerary.appendChild(matchesContainer);
            } else {
                // Rest day
                const restDay = document.createElement('div');
                restDay.className = 'rest-day';
                
                // Use the hotel directly as the location since that's what we show in the day header
                const location = dayInfo.hotel || '---';
                
                // Find the next location if this is not the last day
                let nextLocation = '---';
                if (!isLastDay && dayIndex + 1 < variant.day_itinerary.length) {
                    const nextDayInfo = variant.day_itinerary[dayIndex + 1];
                    if (nextDayInfo.hotel) {
                        nextLocation = nextDayInfo.hotel;
                    }
                }
                
                const restDayMessage = isLastDay 
                    ? `Your trip has come to an end. You can return home from ${location} or explore nearby cities.`
                    : `Take time to explore ${location}, visit local attractions, go shopping or enjoy the local cuisine.`;
                
                const iconClass = isLastDay ? 'fa-flag-checkered' : 'fa-bed';
                
                restDay.innerHTML = `
                    <div class="rest-day-header">
                        <i class="fas ${iconClass} ${isLastDay ? 'final-day-icon' : 'rest-day-icon'}"></i>
                        <span>${isLastDay ? 'Final day' : 'Rest day'} in ${location}</span>
                    </div>
                    <div class="rest-day-message">
                        ${restDayMessage}
                    </div>
                `;
                
                itinerary.appendChild(restDay);
            }

            // After rendering matches, add the after-game segments
            if (afterGameSegments.length > 0) {
                const afterGameContainer = document.createElement('div');
                afterGameContainer.className = 'travel-container ms-4 ps-2 mb-3';
                
                afterGameSegments.forEach(segment => renderTravelSegmentItem(segment, afterGameContainer));
                itinerary.appendChild(afterGameContainer);
            }
        });
    }

    // Add closing element to the timeline after all days are rendered
    const timelineEnd = document.createElement('div');
    timelineEnd.className = 'timeline-end';

    const endMarker = document.createElement('div');
    endMarker.className = 'timeline-end-marker';
    endMarker.innerHTML = '<i class="fas fa-flag-checkered"></i>';

    const endText = document.createElement('div');
    endText.className = 'timeline-end-text';
    endText.innerHTML = `
        <h5 class="mb-3">Trip Complete!</h5>
        <p>Your ${variant.day_itinerary.length}-day journey through Germany is all set. Enjoy the matches, stunning cities, and vibrant atmosphere of German football!</p>
        <div class="mt-3">
            <span class="badge bg-light text-dark me-2 mb-2">${variant.num_games || 0} matches</span>
            <span class="badge bg-light text-dark me-2 mb-2">${variant.cities?.length || 0} cities</span>
            <span class="badge bg-light text-dark me-2 mb-2">${variant.travel_hours || 0}h ${variant.travel_minutes || 0}m travel</span>
        </div>
    `;

    timelineEnd.appendChild(endMarker);
    timelineEnd.appendChild(endText);
    itinerary.appendChild(timelineEnd);
    
    // Add the itinerary to the container
    container.appendChild(itinerary);
}

// Add this helper function to render travel segments
function renderTravelSegmentItem(segment, container) {
    // Clean up location names
    const fromLocation = typeof segment.from_location === 'string' ? 
        segment.from_location.replace(' hbf', '') : 'Unknown';
    const toLocation = typeof segment.to_location === 'string' ? 
        segment.to_location.replace(' hbf', '') : 'Unknown';
    
    // Get context (purpose)
    const context = segment.context || '';
    
    const travelItem = document.createElement('div');
    travelItem.className = 'travel-item';
    travelItem.innerHTML = `
        <div class="travel-item-content">
            <div class="travel-item-route">
                <i class="fas fa-train"></i>
                <div>
                    Travel: ${fromLocation} → ${toLocation}
                    ${context ? `<span class="travel-context">(${context})</span>` : ''}
                </div>
            </div>
            <div class="travel-time">${segment.travel_time || 'Unknown'}</div>
        </div>
    `;
    
    container.appendChild(travelItem);
}

function extractTimeFromMatch(matchText) {
    // Extract time in format (HH:MM) if present
    const timeMatch = matchText.match(/\((\d{1,2}:\d{2})\)$/);
    if (timeMatch && timeMatch[1]) {
        // Return the extracted time and the cleaned match name
        return {
            time: timeMatch[1],
            cleanMatch: matchText.replace(/\s*\(\d{1,2}:\d{2}\)$/, '')
        };
    }
    return {
        time: null,
        cleanMatch: matchText
    };
}

// Update the hotel stay rendering in the accommodations section
function renderHotelStayItem(stay) {
  // Parse dates
  const startDate = parseDate(stay.startDate);
  const endDate = parseDate(stay.endDate);
  
  // Get day names
  const startDay = startDate ? getDayName(startDate) : '';
  const endDay = endDate ? getDayName(endDate) : '';
  
  // Format dates with day names
  let dateDisplay = '';
  if (startDate && endDate) {
    if (startDay === endDay) {
      // Same day
      dateDisplay = `${startDay}, ${formatShortDate(startDate)}`;
    } else {
      // Date range with day names
      dateDisplay = `${startDay}-${endDay}, ${formatDateRange(startDate, endDate)}`;
    }
  }
  
  return `
    <div class="hotel-stay-item">
      <div class="hotel-stay-left">${stay.hotel}</div>
      <div class="hotel-stay-dates">${dateDisplay}</div>
    </div>
  `;
}

// Update the day header in renderItineraryForVariant function to include day name
function formatDayHeader(dayInfo, dayIndex) {
  const hotel = dayInfo.hotel || '';
  let dateDisplay = '';
  let dayName = '';
  
  if (dayInfo.day) {
    // Extract date in a readable format
    const dateMatch = dayInfo.day.match(/,\s*(.+)$/);
    const dateStr = dateMatch && dateMatch[1] ? dateMatch[1].trim() : dayInfo.day;
    
    // Parse the date
    const date = parseDate(dateStr);
    
    if (date) {
      dayName = getDayName(date);
      
      // Format as "day Month year" without leading zeros
      const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
      ];
      dateDisplay = `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
    } else {
      dateDisplay = dateStr;
    }
  }
  
  return `
    <div class="day-badge">${dayIndex + 1}</div>
    <div class="day-header-content">
      <h5>Day ${dayIndex + 1}: ${hotel} ${dayName ? `<span class="day-date-inline">${dayName}, ${dateDisplay}</span>` : ''}</h5>
    </div>
    <div class="day-line"></div>
  `;
}

// Add to your trip-card.js click handler
document.querySelectorAll('.toggle-details-button').forEach(button => {
  button.addEventListener('click', function() {
    const card = this.closest('.trip-card');
    const details = card.querySelector('.trip-details');
    
    if (details.classList.contains('show')) {
      // Collapse
      details.classList.remove('show');
      card.classList.remove('expanded');
      this.innerHTML = '<i class="fas fa-chevron-down"></i> Show Details';
      
      // Smooth scroll to card top
      setTimeout(() => {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } else {
      // Expand
      details.classList.add('show');
      card.classList.add('expanded');
      this.innerHTML = '<i class="fas fa-chevron-up"></i> Hide Details';
    }
  });
});

// Export the functions so they can be used by other modules
export { renderTripCard, renderTbdGames, extractHotelSummary, renderTravelSegments, renderAirportDistances, renderItineraryForVariant };