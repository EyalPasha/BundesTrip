class TripSaver {
    constructor() {
        // Store original request globally for easy access
        this.lastSearchRequest = null;
    }

    // Call this function whenever a search is performed to store the request
    storeSearchRequest(searchRequest) {
        this.lastSearchRequest = searchRequest;
        // console.log('🔄 Stored search request for saving:', searchRequest);
    }

    async showSaveDialog(tripData) {
        // Check if user is logged in
        if (!window.authService || !window.authService.getCurrentUser()) {
            this.showLoginPrompt();
            return;
        }

        // Check if we have the original request
        if (!this.lastSearchRequest) {
            console.warn('⚠️ No search request found - using basic data');
            this.lastSearchRequest = {
                start_location: tripData.start_location || 'Unknown',
                trip_duration: tripData.trip_duration || 3,
                start_date: tripData.start_date || new Date().toISOString().split('T')[0]
            };
        }

        // Check if trip is already saved
        // console.log('🔍 Checking if trip is already saved...');
        const duplicateCheck = await this.checkIfTripAlreadySaved(tripData);
        
        if (duplicateCheck.isDuplicate) {
            this.showAlreadySavedModal(duplicateCheck.savedTrip);
            return;
        }

        this.createSaveModal(tripData);
    }

    createSaveModal(tripData) {
        const modalHtml = `
            <div class="modal fade" id="saveTripModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content modern-modal">
                        <div class="modal-header modern-header">
                            <div class="header-content">
                                <div class="header-icon">
                                    <i class="fas fa-bookmark" style="color: white;"></i>
                                </div>
                                <div class="header-text">
                                    <h4 class="modal-title">Save Your Trip</h4>
                                    <p class="modal-subtitle">Add this trip to your saved collection</p>
                                </div>
                            </div>
                            <button type="button" class="btn-close-modern" data-bs-dismiss="modal">
                                <i class="fas fa-times" style="color: white;"></i>
                            </button>
                        </div>
                        
                        <div class="modal-body modern-body">
                            <div class="save-form-container">
                                <div class="trip-preview-card">
                                    <div class="preview-header">
                                        <i class="fas fa-eye" style="color: var(--primary-color);"></i>
                                        <span>Trip Preview</span>
                                    </div>
                                    <div class="preview-content">
                                        <div class="preview-row">
                                            <div class="preview-item">
                                                <i class="fas fa-map-marker-alt" style="color: var(--primary-color);"></i>
                                                <span>From: ${tripData.start_location || 'Unknown'}</span>
                                            </div>
                                            <div class="preview-item">
                                                <i class="fas fa-calendar-alt" style="color: var(--primary-color);"></i>
                                                <span>Date: ${this.formatDate(tripData.start_date) || 'Unknown'}</span>
                                            </div>
                                        </div>
                                        <div class="preview-row">
                                            <div class="preview-item">
                                                <i class="fas fa-clock" style="color: var(--primary-color);"></i>
                                                <span>Duration: ${tripData.trip_duration || 3}</span>
                                            </div>
                                            <div class="preview-item">
                                                <i class="fas fa-futbol" style="color: var(--primary-color);"></i>
                                                <span>Games: ${this.countTotalGames(tripData)} matches</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="modal-footer modern-footer">
                            <button type="button" class="btn-modern btn-save-primary" id="confirmSaveBtn">
                                <div class="btn-content">
                                    <i class="fas fa-bookmark" style="color: white;"></i>
                                    <span>Save Trip</span>
                                </div>
                                <div class="btn-glow"></div>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    
        // Remove existing modal if present
        const existingModal = document.getElementById('saveTripModal');
        if (existingModal) {
            existingModal.remove();
        }
    
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Initialize Bootstrap modal
        const modal = new bootstrap.Modal(document.getElementById('saveTripModal'));
        modal.show();
    
        // Setup event handlers
        this.setupSaveModalHandlers(tripData, modal);
    }

    async handleSaveTrip(tripData, modal) {
        const saveBtn = document.getElementById('confirmSaveBtn');

        // Show loading state
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = `
            <div class="btn-content">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Saving...</span>
            </div>
        `;

        try {
            // Wait for API service to be available
            await this.waitForApiService();
            
            /* console.log('🔄 Attempting to save trip:', {
                tripData: tripData,
                originalRequest: this.lastSearchRequest
            }); */

            // Prepare the data for saving - no trip name, backend will auto-number
            const saveData = {
                trip_data: tripData,
                original_request: this.lastSearchRequest || {},
                is_favorite: false
            };

            // Use the ApiService instance directly without trip name
            const result = await window.apiService.saveTrip(saveData.trip_data, saveData.original_request, saveData.is_favorite);
            
            // console.log('✅ Trip saved successfully:', result);
            
            modal.hide();
            
            // Show success message with the auto-generated name
            this.showSuccessMessage(`Trip saved successfully!`);
            
            // Log the save action
            await window.apiService.logUserActivity('trip_saved', {
                trip_name: result.trip_name,
                start_location: tripData.start_location,
                trip_duration: tripData.trip_duration,
                games_count: this.countTotalGames(tripData)
            });
            
        } catch (error) {
            console.error('❌ Failed to save trip:', error);
            
            let errorMessage = 'Failed to save trip. Please try again.';
            if (error.message) {
                errorMessage = error.message;
            }
            
            this.showErrorMessage(errorMessage);
            
            // Reset button state
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }

    async waitForApiService() {
        return new Promise((resolve, reject) => {
            const maxWaitTime = 10000; // 10 seconds max
            const checkInterval = 100; // Check every 100ms
            let elapsed = 0;
            
            const checkApiService = () => {
                if (window.apiService && typeof window.apiService.saveTrip === 'function') {
                    // console.log('✅ API service is available');
                    resolve();
                    return;
                }
                
                elapsed += checkInterval;
                if (elapsed >= maxWaitTime) {
                    reject(new Error('API service not available. Please refresh the page and try again.'));
                    return;
                }
                
                setTimeout(checkApiService, checkInterval);
            };
            
            checkApiService();
        });
    }

    showLoginPrompt() {
        const modalHtml = `
            <div class="modal fade" id="loginPromptModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-sign-in-alt me-2 text-primary"></i>Login Required
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <i class="fas fa-bookmark fa-3x text-muted mb-3"></i>
                            <h6>Save Your Trips</h6>
                            <p class="mb-3">Create an account to save trips and access them later from any device.</p>
                        </div>
                        <div class="modal-footer justify-content-center">
                            <a href="./login.html" class="btn btn-primary">
                                <i class="fas fa-sign-in-alt me-2"></i>Login
                            </a>
                            <a href="./register.html" class="btn btn-outline-primary">
                                <i class="fas fa-user-plus me-2"></i>Sign Up
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('loginPromptModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('loginPromptModal'));
        modal.show();

        // Cleanup when modal is closed
        document.getElementById('loginPromptModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('loginPromptModal').remove();
        });
    }

    showSuccessMessage(message) {
        // Create success toast - simple style like the search results
        const toastHtml = `
            <div class="toast align-items-center text-white bg-success border-0" role="alert">
                <div class="toast-body">
                    ${message || 'Trip saved successfully!'}
                </div>
            </div>
        `;
    
        this.showToast(toastHtml);
    }
    
    showErrorMessage(message) {
        // Create error toast - simple style
        const toastHtml = `
            <div class="toast align-items-center text-white bg-danger border-0" role="alert">
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
    
        this.showToast(toastHtml);
    }

    showToast(toastHtml) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '5';
            document.body.appendChild(toastContainer);
        } else {
            // Ensure correct classes and style in case it was created differently before
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '5';
        }
    
        // Add toast
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
        // Show toast
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement, { delay: 4000 });
        toast.show();
    
        // Remove from DOM after hiding
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    // Helper functions
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        } catch {
            return dateString;
        }
    }

    countTotalGames(tripData) {
        if (!tripData || !tripData.trip_groups) return 0;
        
        let totalGames = 0;
        
        tripData.trip_groups.forEach(group => {
            if (group.variation_details && Array.isArray(group.variation_details)) {
                const variation = group.variation_details[0]; // Use first variation
                
                if (variation) {
                    // Method 1: Use the num_games property (most reliable)
                    if (variation.num_games && typeof variation.num_games === 'number') {
                        totalGames = Math.max(totalGames, variation.num_games);
                    }
                    
                    // Method 2: Count games in day_itinerary (fallback)
                    else if (variation.day_itinerary && Array.isArray(variation.day_itinerary)) {
                        let gameCount = 0;
                        variation.day_itinerary.forEach(day => {
                            if (day.games && Array.isArray(day.games)) {
                                gameCount += day.games.length;
                            }
                        });
                        totalGames = Math.max(totalGames, gameCount);
                    }
                }
            }
        });
        
        return totalGames;
    }

    async checkIfTripAlreadySaved(tripData) {
        try {
            // Wait for API service to be available
            await this.waitForApiService();
            
            // Get all saved trips
            const savedTripsResponse = await window.apiService.getSavedTrips(100);
            const savedTrips = savedTripsResponse.trips || [];
            
            // Extract key parameters from current trip
            const currentGames = this.extractAllGames(tripData);
            const currentStartLocation = this.normalizeLocation(tripData.start_location);
            const currentDuration = this.normalizeDuration(tripData.trip_duration);
            const currentStartDate = this.normalizeDate(tripData.start_date);
            
            /* console.log('🔍 Checking for duplicate trip:', {
                currentGames: currentGames.map(g => `${g.homeTeam} vs ${g.awayTeam}`),
                currentStartLocation,
                currentDuration,
                currentStartDate
            }); */
            
            // Compare with each saved trip
            for (const savedTrip of savedTrips) {
                const savedGames = this.extractAllGames(savedTrip);
                const savedStartLocation = this.normalizeLocation(savedTrip.start_location);
                const savedDuration = this.normalizeDuration(savedTrip.trip_duration);
                const savedStartDate = this.normalizeDate(savedTrip.start_date);
                
                /* console.log('🔍 Comparing with saved trip:', savedTrip.trip_name, {
                    savedGames: savedGames.map(g => `${g.homeTeam} vs ${g.awayTeam}`),
                    savedStartLocation,
                    savedDuration,
                    savedStartDate
                }); */
                
                // Check if basic parameters match first (faster)
                const locationMatch = currentStartLocation === savedStartLocation;
                const durationMatch = currentDuration === savedDuration;
                const dateMatch = currentStartDate === savedStartDate;
                
                if (locationMatch && durationMatch && dateMatch) {
                    // Now check if ALL games match exactly
                    const gamesMatch = this.doAllGamesMatch(currentGames, savedGames);
                    
                    if (gamesMatch) {
                        // console.log('✅ Found duplicate trip:', savedTrip.trip_name);
                        return {
                            isDuplicate: true,
                            savedTrip: savedTrip,
                            reason: 'Same games, location, duration, and date'
                        };
                    }
                }
            }
            
            // console.log('✅ No duplicate found - trip can be saved');
            return { isDuplicate: false };
            
        } catch (error) {
            console.error('Error checking for duplicate trips:', error);
            // If we can't check, allow saving (don't block user)
            return { isDuplicate: false };
        }
    }

    showAlreadySavedModal(savedTrip) {
        const modalHtml = `
            <div class="modal fade" id="alreadySavedModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content modern-modal">
                        <div class="modal-header modern-header" style="background: var(--primary-color);">                            <div class="header-content">
                                <div class="header-icon">
                                    <i class="fas fa-info-circle"></i>
                                </div>
                                <div class="header-text">
                                    <h4 class="modal-title">Trip Already Saved</h4>
                                    <p class="modal-subtitle">This trip is already in your collection</p>
                                </div>
                            </div>
                            <button type="button" class="btn-close-modern" data-bs-dismiss="modal">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="modal-body modern-body">
                            <div class="trip-preview-card">
                                <div class="preview-header">
                                    <i class="fas fa-eye"></i>
                                    <span>Saved Trip Details</span>
                                </div>
                                <div class="preview-content">
                                    <div class="preview-row">
                                        <div class="preview-item">
                                            <i class="fas fa-tag" style="color: var(--primary-color);"></i>
                                            <span><strong>Name:</strong> ${savedTrip.trip_name}</span>
                                        </div>
                                        <div class="preview-item">
                                            <i class="fas fa-map-marker-alt" style="color: var(--primary-color);"></i>
                                            <span><strong>From:</strong> ${savedTrip.start_location}</span>
                                        </div>
                                    </div>
                                    <div class="preview-row">
                                        <div class="preview-item">
                                            <i class="fas fa-calendar" style="color: var(--primary-color);"></i>
                                            <span><strong>Date:</strong> ${this.formatDate(savedTrip.start_date)}</span>
                                        </div>
                                        <div class="preview-item">
                                            <i class="fas fa-clock" style="color: var(--primary-color);"></i>
                                            <span><strong>Duration:</strong> ${this.normalizeDuration(savedTrip.trip_duration)} days</span>
                                        </div>
                                    </div>
                                    <div class="preview-row">
                                        <div class="preview-item">
                                            <i class="fas fa-futbol" style="color: var(--primary-color);"></i>
                                            <span><strong>Games:</strong> ${this.countTotalGames(savedTrip)} matches</span>
                                        </div>
                                        <div class="preview-item">
                                            <i class="fas fa-star" style="color: var(--primary-color);"></i>
                                            <span><strong>Favorite:</strong> ${savedTrip.is_favorite ? 'Yes' : 'No'}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="modal-footer modern-footer">
                            <button type="button" class="btn-modern btn-danger" id="unsaveTripBtn">
                                <div class="btn-content">
                                    <i class="fas fa-trash-alt"></i>
                                    <span>Remove Trip</span>
                                </div>
                                <div class="btn-glow"></div>
                            </button>
                            <button type="button" class="btn-modern btn-warning" id="toggleFavoriteBtn">
                                <div class="btn-content">
                                    <i class="fas fa-star"></i>
                                    <span>${savedTrip.is_favorite ? 'Remove from Favorites' : 'Add to Favorites'}</span>
                                </div>
                                <div class="btn-glow"></div>
                            </button>
                            <button type="button" class="btn-modern btn-save-primary" onclick="window.location.href='profile.html'">
                                <div class="btn-content">
                                    <i class="fas fa-tachometer-alt"></i>
                                    <span>View in Dashboard</span>
                                </div>
                                <div class="btn-glow"></div>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    
        // Remove existing modal and add new one
        const existingModal = document.getElementById('alreadySavedModal');
        if (existingModal) existingModal.remove();
    
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('alreadySavedModal'));
        modal.show();
    
        // Handle toggle favorite
        const toggleFavoriteBtn = document.getElementById('toggleFavoriteBtn');
        if (toggleFavoriteBtn) {
            toggleFavoriteBtn.addEventListener('click', async () => {
                await this.handleToggleFavorite(savedTrip.id, toggleFavoriteBtn, modal);
            });
        }
    
        // Handle unsave trip
        const unsaveTripBtn = document.getElementById('unsaveTripBtn');
        if (unsaveTripBtn) {
            unsaveTripBtn.addEventListener('click', () => {
                modal.hide(); // Close current modal
                this.showUnsaveConfirmModal(savedTrip); // Show unsave confirmation
            });
        }
    
        // Cleanup
        document.getElementById('alreadySavedModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('alreadySavedModal').remove();
        });
    }

    async handleToggleFavorite(tripId, button, modal) {
        // Show loading state
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Updating...';

        try {
            await this.waitForApiService();
            const result = await window.apiService.toggleTripFavorite(tripId);
            
            if (result.success) {
                // Update button text
                const newFavoriteStatus = result.trip.is_favorite;
                button.innerHTML = `<i class="fas fa-star me-1"></i>${newFavoriteStatus ? 'Remove from Favorites' : 'Add to Favorites'}`;
                
                // Show success message
                this.showSuccessMessage(
                    newFavoriteStatus ? 'Added to favorites!' : 'Removed from favorites!'
                );
                
                // Close modal after short delay
                setTimeout(() => {
                    modal.hide();
                }, 1500);
            }
            
        } catch (error) {
            console.error('Failed to toggle favorite:', error);
            this.showErrorMessage('Failed to update favorite status.');
            
            // Reset button
            button.innerHTML = originalText;
        } finally {
            button.disabled = false;
        }
    }

    // Add these helper methods to the TripSaver class

    normalizeLocation(location) {
        if (!location) return '';
        
        // Remove common suffixes and normalize
        return location
            .toLowerCase()
            .replace(/\s+(hbf|hauptbahnhof|am main)$/i, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    normalizeDuration(duration) {
        if (!duration) return 0;
        
        // Handle both number and string formats
        if (typeof duration === 'number') {
            return duration;
        }
        
        if (typeof duration === 'string') {
            // Extract number from strings like "3 days", "3", etc.
            const match = duration.match(/(\d+)/);
            return match ? parseInt(match[1]) : 0;
        }
        
        return 0;
    }

    normalizeDate(date) {
        if (!date) return '';
        
        try {
            // Convert various date formats to YYYY-MM-DD
            let dateObj;
            
            if (date instanceof Date) {
                dateObj = date;
            } else if (typeof date === 'string') {
                // Handle formats like "02 July 2025", "2025-07-02", etc.
                dateObj = new Date(date);
            } else {
                return '';
            }
            
            // Return in YYYY-MM-DD format for consistent comparison
            return dateObj.toISOString().split('T')[0];
            
        } catch (error) {
            console.warn('Could not normalize date:', date);
            return String(date).toLowerCase().trim();
        }
    }

    // Add this method to the TripSaver class

    extractAllGames(tripData) {
        const allGames = [];
        
        if (!tripData || !tripData.trip_groups) return allGames;
        
        
        tripData.trip_groups.forEach((group, groupIndex) => {
            
            // Method 1: Check base_trip.Itinerary for matches
            if (group.base_trip && group.base_trip.Itinerary && Array.isArray(group.base_trip.Itinerary)) {
                
                group.base_trip.Itinerary.forEach((day, dayIndex) => {
                    
                    if (day.matches && Array.isArray(day.matches) && day.matches.length > 0) {
                        
                        day.matches.forEach(match => {
                            const gameInfo = this.normalizeGameInfo(match);
                            if (gameInfo) {
                                allGames.push(gameInfo);
                            }
                        });
                    }
                });
            }
            
            // Method 2: Check variation_details for day_itinerary (fallback)
            if (group.variation_details && Array.isArray(group.variation_details)) {
                group.variation_details.forEach((variation, varIndex) => {
                    
                    if (variation.day_itinerary && Array.isArray(variation.day_itinerary)) {
                        variation.day_itinerary.forEach((day, dayIndex) => {
                            
                            // Check for games array
                            if (day.games && Array.isArray(day.games)) {
                                day.games.forEach(game => {
                                    const gameInfo = this.normalizeGameInfo(game);
                                    if (gameInfo) {
                                        allGames.push(gameInfo);
                                    }
                                });
                            }
                            
                            // Check for matches array (alternative structure)
                            if (day.matches && Array.isArray(day.matches)) {
                                day.matches.forEach(match => {
                                    const gameInfo = this.normalizeGameInfo(match);
                                    if (gameInfo) {
                                        allGames.push(gameInfo);
                                    }
                                });
                            }
                        });
                    }
                });
            }
            
            // Method 3: Check variations array (legacy structure)
            if (group.variations && Array.isArray(group.variations)) {
                group.variations.forEach((variation) => {
                    if (variation.games && Array.isArray(variation.games)) {
                        variation.games.forEach(game => {
                            const gameInfo = this.normalizeGameInfo(game);
                            if (gameInfo) {
                                allGames.push(gameInfo);
                            }
                        });
                    }
                });
            }
        });
        
        // console.log(`🎯 Total games extracted: ${allGames.length}`, allGames);
        
        // Remove duplicates and sort for consistent comparison
        const uniqueGames = this.removeDuplicateGames(allGames);
        const sortedGames = this.sortGames(uniqueGames);
        
        // console.log(`🎯 Final unique sorted games: ${sortedGames.length}`, sortedGames);
        
        return sortedGames;
    }

    // Add this method to the TripSaver class

    normalizeGameInfo(game) {
        if (!game) return null;
        
        try {
            // console.log('🔍 Normalizing game info:', game);
            
            let homeTeam = '';
            let awayTeam = '';
            let gameDate = '';
            
            // Method 1: Direct team properties
            if (game.home_team && game.away_team) {
                homeTeam = this.normalizeTeamName(game.home_team);
                awayTeam = this.normalizeTeamName(game.away_team);
                gameDate = this.normalizeDate(game.date || game.game_date);
            }
            // Method 2: Teams array
            else if (game.teams && Array.isArray(game.teams) && game.teams.length >= 2) {
                homeTeam = this.normalizeTeamName(game.teams[0]);
                awayTeam = this.normalizeTeamName(game.teams[1]);
                gameDate = this.normalizeDate(game.date || game.game_date);
            }
            // Method 3: Match object with team properties
            else if (game.team_1 && game.team_2) {
                homeTeam = this.normalizeTeamName(game.team_1);
                awayTeam = this.normalizeTeamName(game.team_2);
                gameDate = this.normalizeDate(game.date || game.match_date);
            }
            // Method 4: Parse from match description
            else if (game.match || game.description || game.title) {
                const matchText = game.match || game.description || game.title;
                
                // Try different vs patterns
                let vsMatch = matchText.match(/(.+?)\s+vs\.?\s+(.+)/i);
                if (!vsMatch) {
                    vsMatch = matchText.match(/(.+?)\s+-\s+(.+)/i);
                }
                if (!vsMatch) {
                    vsMatch = matchText.match(/(.+?)\s+gegen\s+(.+)/i); // German
                }
                
                if (vsMatch) {
                    homeTeam = this.normalizeTeamName(vsMatch[1]);
                    awayTeam = this.normalizeTeamName(vsMatch[2]);
                    gameDate = this.normalizeDate(game.date || game.match_date || game.game_date);
                }
            }
            // Method 5: Check if it's just team names as properties
            else if (typeof game === 'string') {
                // If the game is just a string, try to parse it
                const vsMatch = game.match(/(.+?)\s+vs\.?\s+(.+)/i);
                if (vsMatch) {
                    homeTeam = this.normalizeTeamName(vsMatch[1]);
                    awayTeam = this.normalizeTeamName(vsMatch[2]);
                }
            }
            
            if (!homeTeam || !awayTeam) {
                return null;
            }
            
            const gameInfo = {
                homeTeam,
                awayTeam,
                gameDate,
                gameId: `${homeTeam}_vs_${awayTeam}_${gameDate}`
            };
                        return gameInfo;
            
        } catch (error) {
            return null;
        }
    }

    // Add this method to the TripSaver class

    normalizeTeamName(teamName) {
        if (!teamName) return '';
        
        return teamName
            .toString()
            .toLowerCase()
            .trim()
            // Remove common prefixes/suffixes
            .replace(/^(fc|sc|sv|bv|1\.|bvb|vfl|fsv|spvgg)\s+/i, '')
            .replace(/\s+(fc|sc|sv|bv|ii|2|academy)$/i, '')
            // Normalize spacing
            .replace(/\s+/g, ' ')
            .trim();
    }

    // Add this method to the TripSaver class

    doAllGamesMatch(currentGames, savedGames) {
        // Quick check - if different number of games, they don't match
        if (currentGames.length !== savedGames.length) {
            // console.log(`🔍 Game count mismatch: ${currentGames.length} vs ${savedGames.length}`);
            return false;
        }
        
        if (currentGames.length === 0) {
            // console.log('🔍 Both trips have no games - considering as match');
            return true;
        }
        
        // Check if every game in current trip exists in saved trip
        for (const currentGame of currentGames) {
            const foundMatch = savedGames.some(savedGame => 
                this.areGamesIdentical(currentGame, savedGame)
            );
            
            if (!foundMatch) {
                // console.log(`🔍 Game not found in saved trip: ${currentGame.homeTeam} vs ${currentGame.awayTeam}`);
                return false;
            }
        }
        
        // console.log('🔍 All games match!');
        return true;
    }

    areGamesIdentical(game1, game2) {
        if (!game1 || !game2) return false;
        
        // Compare teams (both directions - home/away might be swapped)
        const sameOrder = (
            game1.homeTeam === game2.homeTeam && 
            game1.awayTeam === game2.awayTeam
        );
        
        const reversedOrder = (
            game1.homeTeam === game2.awayTeam && 
            game1.awayTeam === game2.homeTeam
        );
        
        const teamsMatch = sameOrder || reversedOrder;
        
        // Optionally compare dates too (if available)
        const datesMatch = !game1.gameDate || !game2.gameDate || game1.gameDate === game2.gameDate;
        
        return teamsMatch && datesMatch;
    }

    // Add these utility methods to the TripSaver class

    removeDuplicateGames(games) {
        const unique = [];
        const seen = new Set();
        
        for (const game of games) {
            if (!seen.has(game.gameId)) {
                seen.add(game.gameId);
                unique.push(game);
            }
        }
        
        return unique;
    }

    sortGames(games) {
        return games.sort((a, b) => {
            // Sort by date first, then by team names
            if (a.gameDate && b.gameDate && a.gameDate !== b.gameDate) {
                return a.gameDate.localeCompare(b.gameDate);
            }
            
            // Then by home team, then away team
            const homeCompare = a.homeTeam.localeCompare(b.homeTeam);
            if (homeCompare !== 0) return homeCompare;
            
            return a.awayTeam.localeCompare(b.awayTeam);
        });
    }

    // Add this method to the TripSaver class

    showUnsaveConfirmModal(savedTrip) {
        const modalHtml = `
            <div class="modal fade" id="unsaveTripModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content modern-modal">
                        <div class="modal-header modern-header" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);">
                            <div class="header-content">
                                <div class="header-icon">
                                    <i class="fas fa-trash-alt"></i>
                                </div>
                                <div class="header-text">
                                    <h4 class="modal-title">Remove Saved Trip</h4>
                                    <p class="modal-subtitle">This action cannot be undone</p>
                                </div>
                            </div>
                            <button type="button" class="btn-close-modern" data-bs-dismiss="modal">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="modal-body modern-body">
                            <div class="trip-preview-card">
                                <div class="preview-header">
                                    <i class="fas fa-eye"></i>
                                    <span>Trip to Remove</span>
                                </div>
                                <div class="preview-content">
                                    <div class="preview-row">
                                        <div class="preview-item">
                                            <i class="fas fa-tag" style="color: var(--primary-color);"></i>
                                            <span><strong>Name:</strong> ${savedTrip.trip_name}</span>
                                        </div>
                                        <div class="preview-item">
                                            <i class="fas fa-map-marker-alt" style="color: var(--primary-color);"></i>
                                            <span><strong>From:</strong> ${savedTrip.start_location}</span>
                                        </div>
                                    </div>
                                    <div class="preview-row">
                                        <div class="preview-item">
                                            <i class="fas fa-calendar" style="color: var(--primary-color);"></i>
                                            <span><strong>Date:</strong> ${this.formatDate(savedTrip.start_date)}</span>
                                        </div>
                                        <div class="preview-item">
                                            <i class="fas fa-futbol" style="color: var(--primary-color);"></i>
                                            <span><strong>Games:</strong> ${this.countTotalGames(savedTrip)} matches</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="modal-footer modern-footer">
                            <button type="button" class="btn-modern btn-cancel" data-bs-dismiss="modal">
                                <div class="btn-content">
                                    <i class="fas fa-arrow-left"></i>
                                    <span>Keep Trip</span>
                                </div>
                            </button>
                            <button type="button" class="btn-modern btn-danger" id="confirmUnsaveBtn">
                                <div class="btn-content">
                                    <i class="fas fa-trash-alt"></i>
                                    <span>Remove Trip</span>
                                </div>
                                <div class="btn-glow"></div>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('unsaveTripModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('unsaveTripModal'));
        modal.show();

        // Handle confirm unsave
        const confirmBtn = document.getElementById('confirmUnsaveBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', async () => {
                await this.handleUnsaveTrip(savedTrip, modal);
            });
        }

        // Cleanup
        document.getElementById('unsaveTripModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('unsaveTripModal').remove();
        });
    }

    async handleUnsaveTrip(savedTrip, modal) {
        const confirmBtn = document.getElementById('confirmUnsaveBtn');
        
        // Show loading state
        const originalText = confirmBtn.innerHTML;
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = `
            <div class="btn-content">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Removing...</span>
            </div>
        `;

        try {
            // Wait for API service to be available
            await this.waitForApiService();
            
            // console.log('🗑️ Attempting to unsave trip:', savedTrip);

            // Call the unsave API
            const result = await window.apiService.unsaveTrip(savedTrip.id);
            
            // console.log('✅ Trip unsaved successfully:', result);
            
            // Close modal
            modal.hide();
            
            // Show success message
            this.showSuccessMessage(`Trip removed successfully!`);
            
            // Log additional client-side activity
            await window.apiService.logUserActivity('trip_unsaved_confirmed', {
                trip_id: savedTrip.id,
                trip_name: savedTrip.trip_name,
                removal_method: 'manual_user_action',
                from_location: savedTrip.start_location,
                trip_date: savedTrip.start_date
            });
            
            // If we're on a saved trips page, we might want to refresh the list
            if (typeof window.refreshSavedTripsList === 'function') {
                window.refreshSavedTripsList();
            }
            
        } catch (error) {
            console.error('❌ Failed to unsave trip:', error);
            
            let errorMessage = 'Failed to remove trip. Please try again.';
            if (error.message) {
                errorMessage = error.message;
            }
            
            this.showErrorMessage(errorMessage);
            
            // Reset button state
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
        }
    }

    // Add this method to the TripSaver class:

    setupSaveModalHandlers(tripData, modal) {
        // Handle save button click - no trip name input needed
        const confirmSaveBtn = document.getElementById('confirmSaveBtn');
        
        if (confirmSaveBtn) {
            confirmSaveBtn.addEventListener('click', async () => {
                await this.handleSaveTrip(tripData, modal);
            });
        }
    }

}

// Make globally available
window.TripSaver = TripSaver;
window.tripSaver = new TripSaver();

// Global function to show save dialog (called from trip cards)
window.showSaveTripDialog = function(tripData) {
    window.tripSaver.showSaveDialog(tripData);
}

// Add these global functions at the end:

// Global function to show unsave confirmation (for use in dashboards/lists)
window.showUnsaveTripDialog = function(savedTrip) {
    window.tripSaver.showUnsaveConfirmModal(savedTrip);
};

// Global function to refresh saved trips list (to be implemented by dashboard pages)
window.refreshSavedTripsList = function() {
    // console.log('🔄 Refreshing saved trips list...');
    // This will be implemented by pages that show saved trips lists
};
