// Session Restoration Service
class SessionRestore {
    constructor() {
        this.isRestoring = false;
        this.restoredFromSession = false;
    }

    // Main restore function - call this on page load
    async restorePage() {
        try {
            // Always try to restore form state first
            const formRestored = await this.restoreFormState();
            
            // Only restore results if it's a refresh, not navigation
            const resultsRestored = await this.restoreSearchResults();
            
            this.restoredFromSession = formRestored || resultsRestored;
            
            if (this.restoredFromSession) {
                console.log('✅ Page restored from session');
                // Disable animations for restored content
                document.body.classList.add('no-animations');
                
                // Re-enable animations after a short delay
                setTimeout(() => {
                    document.body.classList.remove('no-animations');
                }, 100);
            }
            
            return this.restoredFromSession;
        } catch (error) {
            console.warn('⚠️ Failed to restore page:', error);
            return false;
        }
    }

    // Restore form state
    async restoreFormState() {
        if (!window.sessionManager.shouldRestoreForm()) return false;

        const formState = window.sessionManager.getFormState();
        if (!formState) return false;

        console.log('🔄 Restoring form state...');

        try {
            // Wait for form elements to be ready
            await this.waitForFormElements();

            // Restore basic fields
            this.setFieldValue('startLocation', formState.startLocation);
            this.setFieldValue('startDate', formState.startDate);
            this.setFieldValue('tripDuration', formState.tripDuration);
            this.setFieldValue('minGames', formState.minGames);
            this.setFieldValue('maxTravelTime', formState.maxTravelTime);

            // Restore team selections
            this.setFieldValue('mustTeam1', formState.mustTeam1);
            this.setFieldValue('mustTeam2', formState.mustTeam2);
            this.setFieldValue('mustTeam3', formState.mustTeam3);
            this.setFieldValue('mustTeam4', formState.mustTeam4);

            // Restore league selections
            if (formState.preferredLeagues && formState.preferredLeagues.length > 0) {
                const leaguesSelect = document.getElementById('preferredLeagues');
                if (leaguesSelect) {
                    // Clear current selections
                    Array.from(leaguesSelect.options).forEach(option => {
                        option.selected = formState.preferredLeagues.includes(option.value);
                    });
                    
                    // Trigger change event for Select2
                    if (window.jQuery && $(leaguesSelect).hasClass('select2-hidden-accessible')) {
                        $(leaguesSelect).trigger('change');
                    }
                }
            }

            // Refresh all Select2 instances
            if (window.jQuery && $('.select2-hidden-accessible').length > 0) {
                $('.select2-hidden-accessible').trigger('change');
            }

            console.log('✅ Form state restored');
            return true;
        } catch (error) {
            console.warn('⚠️ Failed to restore form state:', error);
            return false;
        }
    }

    // Restore search results
    async restoreSearchResults() {
        if (this.isRestoring) return false;
        
        // Enhanced check for restoration validity
        if (!window.sessionManager.shouldRestoreResults()) {
            console.log('🚫 Search results restoration not needed');
            return false;
        }

        const session = window.sessionManager.getSearchSession();
        if (!session || !session.results) {
            console.log('🚫 No valid search session found');
            return false;
        }

        // Check for navigation flag - but don't immediately abort
        const navigationFlag = sessionStorage.getItem('navigation_away');
        if (navigationFlag) {
            // Check if this was actually a refresh vs navigation
            const isActualRefresh = window.performance && 
                                   window.performance.navigation && 
                                   window.performance.navigation.type === window.performance.navigation.TYPE_RELOAD;
            
            if (isActualRefresh) {
                // This is a refresh, clear the flag and proceed
                sessionStorage.removeItem('navigation_away');
                console.log('🔄 Navigation flag detected but this is a refresh - proceeding with restore');
            } else {
                // This is actual navigation, abort restore
                console.log('🚫 Navigation flag detected - clearing session and aborting restore');
                sessionStorage.removeItem('navigation_away');
                window.sessionManager.clearSearchSession();
                return false;
            }
        }

        console.log('🔄 Restoring search results...');
        this.isRestoring = true;

        try {
            // *** CRITICAL: Show all UI elements BEFORE rendering ***
            const resultsSection = document.getElementById('results');
            const resultsCountContainer = document.getElementById('resultsCountContainer');
            const filterCard = document.getElementById('filterResultsCard');
            const loadingContainer = document.getElementById('loading');
            
            // Show results section immediately
            if (resultsSection) {
                resultsSection.classList.remove('d-none');
                resultsSection.style.opacity = '1';
            }
            
            // Show results count container immediately
            if (resultsCountContainer) {
                resultsCountContainer.classList.remove('d-none');
                resultsCountContainer.style.opacity = '1';
            }
            
            // Hide filter card (we use drawer instead)
            if (filterCard) {
                filterCard.classList.add('d-none');
            }
            
            // Hide loading container
            if (loadingContainer) {
                loadingContainer.classList.add('d-none');
            }
            
            // Enable scrolling
            document.body.classList.remove('no-scroll');
            
            // Update body class for filter drawer
            document.body.classList.add('has-filter-drawer');

            // Render the trips with restoration flag
            if (window.renderResults) {
                const mockResponse = {
                    trip_groups: session.results,
                    request_id: session.requestId,
                    trip_duration: session.searchParams.trip_duration,
                    start_location: session.searchParams.start_location,
                    start_date: session.searchParams.start_date,
                    max_travel_time: session.searchParams.max_travel_time,
                    preferred_leagues: session.searchParams.preferred_leagues,
                    must_teams: session.searchParams.must_teams,
                    min_games: session.searchParams.min_games
                };
                
                await window.renderResults(mockResponse, true); // true = isRestore
                
                // *** RESTORE THE CORRECT NUMBER OF TRIPS ***
                const renderedCount = session.renderedCount || 5; // Default to 5 if not saved
                if (renderedCount > 5) {
                    // Import and use the multiple batch renderer
                    const { renderMultipleBatches } = await import('../components/results-display.js');
                    renderMultipleBatches(renderedCount);
                    console.log(`✅ Restored ${renderedCount} trips from session`);
                }
            }

            // Restore scroll position after rendering is complete
            if (session.scrollPosition > 0) {
                // Multiple attempts to ensure scroll position is restored
                const restoreScroll = () => {
                    window.scrollTo(0, session.scrollPosition);
                };
                
                // Immediate scroll
                restoreScroll();
                
                // Delayed attempts with longer delays for more content
                setTimeout(restoreScroll, 200);
                setTimeout(restoreScroll, 500);
                
                // Final attempt after animations
                requestAnimationFrame(() => {
                    setTimeout(restoreScroll, 200);
                });
            }

            console.log('✅ Search results restored');
            return true;
        } catch (error) {
            console.warn('⚠️ Failed to restore search results:', error);
            return false;
        } finally {
            this.isRestoring = false;
        }
    }

    // Helper methods
    async waitForFormElements() {
        return new Promise((resolve) => {
            const checkElements = () => {
                const required = ['startLocation', 'startDate', 'tripDuration'];
                const allExist = required.every(id => document.getElementById(id));
                
                if (allExist) {
                    resolve();
                } else {
                    setTimeout(checkElements, 50);
                }
            };
            checkElements();
        });
    }

    setFieldValue(fieldId, value) {
        if (!value) return;
        
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = value;
            
            // Trigger events for different field types
            if (field.tagName === 'SELECT') {
                field.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery && $(field).hasClass('select2-hidden-accessible')) {
                    $(field).trigger('change');
                }
            } else {
                field.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    }

    // Check if content was restored from session
    wasRestoredFromSession() {
        return this.restoredFromSession;
    }
}

// Make it globally available
window.sessionRestore = new SessionRestore();