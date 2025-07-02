// Session Management for Trip Search
class SessionManager {
    constructor() {
        this.storageKey = 'bundestrip_session';
        this.formStateKey = 'bundestrip_form_state';
        this.sessionTimeout = 30 * 60 * 1000; // 30 minutes
        this.formStateTimeout = 24 * 60 * 60 * 1000; // 24 hours
    }

    // Save search results to session storage
    saveSearchSession(searchParams, results, requestId) {
        try {
            // Validate inputs
            if (!searchParams || !results || !Array.isArray(results)) {
                console.warn('⚠️ Invalid session data provided to saveSearchSession');
                return;
            }
            
            // Get current rendered count if available
            const renderedCount = window.tripResults ? window.tripResults.renderedCount : 5;
            
            const sessionData = {
                searchParams,
                results,
                requestId,
                timestamp: Date.now(),
                url: window.location.pathname,
                scrollPosition: window.pageYOffset || document.documentElement.scrollTop || 0,
                renderedCount: renderedCount, // Save how many trips were rendered
                // Save UI state
                uiState: {
                    resultsVisible: true,
                    filterCardVisible: results.length > 0,
                    tripOptionsVisible: results.length > 0,
                    resultsCount: results.length
                }
            };
            
            sessionStorage.setItem(this.storageKey, JSON.stringify(sessionData));
            console.log(`✅ Search session saved successfully (${renderedCount} trips rendered)`);
        } catch (error) {
            console.warn('⚠️ Failed to save search session:', error);
            try {
                sessionStorage.removeItem(this.storageKey);
            } catch (e) {
                console.warn('⚠️ Failed to clear corrupted search session');
            }
        }
    }

    // Save form state separately (persists longer)
    saveFormState(formData) {
        try {
            // Validate formData before saving
            if (!formData || typeof formData !== 'object') {
                console.warn('⚠️ Invalid form data provided to saveFormState');
                return;
            }
            
            const formState = {
                ...formData,
                timestamp: Date.now()
            };
            
            localStorage.setItem(this.formStateKey, JSON.stringify(formState));
            console.log('✅ Form state saved successfully');
        } catch (error) {
            console.warn('⚠️ Failed to save form state:', error);
            // Clear corrupted data
            try {
                localStorage.removeItem(this.formStateKey);
            } catch (e) {
                console.warn('⚠️ Failed to clear corrupted form state');
            }
        }
    }

    // Get search session
    getSearchSession() {
        try {
            const sessionData = sessionStorage.getItem(this.storageKey);
            if (!sessionData) return null;

            const parsed = JSON.parse(sessionData);
            
            // Check if session is expired
            if (Date.now() - parsed.timestamp > this.sessionTimeout) {
                this.clearSearchSession();
                return null;
            }

            // Only restore if we're on the same page
            if (parsed.url !== window.location.pathname) {
                return null;
            }

            return parsed;
        } catch (error) {
            console.warn('⚠️ Failed to get search session:', error);
            this.clearSearchSession(); // Clear corrupted data
            return null;
        }
    }

    // Get form state (longer persistence)
    getFormState() {
        try {
            const formState = localStorage.getItem(this.formStateKey);
            if (!formState) return null;

            const parsed = JSON.parse(formState);
            
            // Form state persists for 24 hours
            if (Date.now() - parsed.timestamp > this.formStateTimeout) {
                this.clearFormState();
                return null;
            }

            return parsed;
        } catch (error) {
            console.warn('⚠️ Failed to get form state:', error);
            this.clearFormState(); // Clear corrupted data
            return null;
        }
    }

    // Clear search session
    clearSearchSession() {
        try {
            sessionStorage.removeItem(this.storageKey);
        } catch (error) {
            console.warn('⚠️ Failed to clear search session:', error);
        }
    }

    // Clear form state
    clearFormState() {
        try {
            localStorage.removeItem(this.formStateKey);
        } catch (error) {
            console.warn('⚠️ Failed to clear form state:', error);
        }
    }

    // Clear everything
    clearAll() {
        this.clearSearchSession();
        this.clearFormState();
    }

    // Check if we should restore search results (only on refresh, not navigation)
    shouldRestoreResults() {
        const session = this.getSearchSession();
        const isRefresh = this.isPageRefresh();
        return session && session.results && session.results.length > 0 && isRefresh;
    }

    // Check if we should restore form state
    shouldRestoreForm() {
        return this.getFormState() !== null;
    }

    // Update scroll position immediately
    updateScrollPosition(scrollPosition) {
        try {
            const sessionData = sessionStorage.getItem(this.storageKey);
            if (!sessionData) return;

            const parsed = JSON.parse(sessionData);
            parsed.scrollPosition = scrollPosition;
            parsed.lastScrollUpdate = Date.now();
            
            sessionStorage.setItem(this.storageKey, JSON.stringify(parsed));
        } catch (error) {
            console.warn('⚠️ Failed to update scroll position:', error);
        }
    }

    // Detect if this is a page refresh vs navigation
    isPageRefresh() {
        // Check if we have navigation timing API
        if (window.performance && window.performance.navigation) {
            return window.performance.navigation.type === window.performance.navigation.TYPE_RELOAD;
        }
        
        // Fallback: check if session storage has data and no navigation flag
        const hasSessionData = sessionStorage.getItem(this.storageKey) !== null;
        const navigationFlag = sessionStorage.getItem('navigation_away');
        
        if (navigationFlag) {
            sessionStorage.removeItem('navigation_away');
            return false;
        }
        
        return hasSessionData;
    }

    // Mark that user is navigating away
    markNavigatingAway() {
        try {
            sessionStorage.setItem('navigation_away', 'true');
            console.log('🔄 Navigation away marked');
        } catch (error) {
            console.warn('⚠️ Failed to mark navigation:', error);
        }
    }

    // Clean up on page unload (for navigation detection)
    setupNavigationDetection() {
        // Track if user clicked a navigation link
        let userNavigating = false;
        
        // Listen for any navigation events (links, form submissions, etc.)
        document.addEventListener('click', (event) => {
            const target = event.target.closest('a');
            if (target && target.href && !target.href.includes('#')) {
                // Check if it's an external link or different page
                const currentOrigin = window.location.origin;
                const currentPath = window.location.pathname;
                
                try {
                    const targetUrl = new URL(target.href, currentOrigin);
                    
                    // If it's a different page, mark navigation
                    if (targetUrl.pathname !== currentPath) {
                        userNavigating = true;
                        this.markNavigatingAway();
                        console.log('🔄 User clicked navigation link - marking away');
                    }
                } catch (error) {
                    // Handle invalid URLs
                    console.warn('Invalid URL detected:', target.href);
                }
            }
        });

        // Listen for popstate (back/forward navigation)
        window.addEventListener('popstate', () => {
            userNavigating = true;
            this.markNavigatingAway();
            console.log('🔄 Browser navigation detected - marking away');
        });
        
        // Only clear session on beforeunload if user actually navigated
        window.addEventListener('beforeunload', () => {
            if (userNavigating) {
                // User is actually navigating away, clear the session
                this.clearSearchSession();
                console.log('🔄 Navigation confirmed - search session cleared');
            } else {
                // This might be a refresh, don't clear session
                console.log('🔄 Page unload without navigation flag - keeping session');
            }
        });
        
        // Reset navigation flag when page loads
        window.addEventListener('load', () => {
            userNavigating = false;
        });
    }

    // Add method to update rendered count in real-time
    updateRenderedCount(renderedCount) {
        try {
            const sessionData = sessionStorage.getItem(this.storageKey);
            if (!sessionData) return;

            const parsed = JSON.parse(sessionData);
            parsed.renderedCount = renderedCount;
            parsed.lastUpdate = Date.now();
            
            sessionStorage.setItem(this.storageKey, JSON.stringify(parsed));
        } catch (error) {
            console.warn('⚠️ Failed to update rendered count:', error);
        }
    }
}

// Make it globally available
window.sessionManager = new SessionManager();