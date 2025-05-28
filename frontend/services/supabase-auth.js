const supabaseUrl = 'https://ouurqpbwidicivdysdnq.supabase.co'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91dXJxcGJ3aWRpY2l2ZHlzZG5xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNTcxMDcsImV4cCI6MjA2MzkzMzEwN30.uieOMYz4Rvzxt5O-_YRg2EvUreu859bJvp14jtUYCSw'

// Initialize Supabase client
const supabase = window.supabase.createClient(supabaseUrl, supabaseAnonKey)

class AuthService {
    constructor() {
        this.currentUser = null
        this.isAdmin = false
        this.authToken = null
        this.initialized = false
        
        // Initialize immediately
        this.init()
    }

    async init() {
        try {
            // Get current session
            const { data: { session } } = await supabase.auth.getSession()
            
            if (session) {
                this.currentUser = session.user
                this.authToken = session.access_token
                await this.checkAdminStatus()
                console.log('✅ User session restored:', session.user.email)
            }
            
            // Listen for auth state changes (INCLUDING TOKEN REFRESH)
            supabase.auth.onAuthStateChange(async (event, session) => {
                console.log('🔄 Auth state changed:', event)
                
                if (event === 'SIGNED_IN' && session) {
                    this.currentUser = session.user
                    this.authToken = session.access_token
                    await this.checkAdminStatus()
                    console.log('✅ User signed in:', session.user.email)
                } else if (event === 'TOKEN_REFRESHED' && session) {
                    // THIS IS THE KEY PART - handle token refresh
                    console.log('🔄 Token refreshed automatically')
                    this.currentUser = session.user
                    this.authToken = session.access_token
                    console.log('✅ New token ready for API calls')
                } else if (event === 'SIGNED_OUT') {
                    this.currentUser = null
                    this.authToken = null
                    this.isAdmin = false
                    console.log('👋 User signed out')
                }
            })
            
            this.initialized = true
            console.log('✅ Supabase Auth Service initialized')
        } catch (error) {
            console.error('❌ Failed to initialize auth service:', error)
        }
    }

    // Sign up new user
    async signUp(email, password, userData = {}) {
        try {
            const { data, error } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    data: {
                        full_name: userData.fullName || '',
                        ...userData
                    }
                }
            })

            if (error) throw error

            return { 
                success: true, 
                data, 
                user: data.user,
                message: 'Please check your email to verify your account' 
            }
        } catch (error) {
            console.error('Sign up error:', error)
            return { success: false, error: error.message }
        }
    }

    // Sign in existing user
    async signIn(email, password) {
        try {
            const { data, error } = await supabase.auth.signInWithPassword({
                email,
                password
            })

            if (error) throw error

            // Store user info
            this.currentUser = data.user
            this.authToken = data.session.access_token

            // Check if user is admin
            await this.checkAdminStatus()

            return { success: true, user: data.user, message: 'Welcome back!' }
        } catch (error) {
            console.error('Sign in error:', error)
            return { success: false, error: error.message }
        }
    }

    // Enhanced sign out method that handles CSP issues
    async signOut() {
        try {
            // Method 1: Try normal Supabase logout
            console.log('🔓 Attempting Supabase logout...');
            const { error } = await supabase.auth.signOut()
            
            if (!error) {
                console.log('✅ Supabase logout successful');
                this.currentUser = null
                this.authToken = null
                this.isAdmin = false
                return { success: true, message: 'Signed out successfully' }
            } else {
                throw error;
            }
            
        } catch (error) {
            console.warn('⚠️ Supabase logout failed, performing manual logout:', error);
            
            // Method 2: Manual logout - clear everything locally
            try {
                // Clear our service state
                this.currentUser = null;
                this.authToken = null;
                this.isAdmin = false;
                
                // Clear localStorage/sessionStorage
                const keys = Object.keys(localStorage);
                keys.forEach(key => {
                    if (key.startsWith('supabase') || key.includes('auth')) {
                        localStorage.removeItem(key);
                    }
                });
                
                const sessionKeys = Object.keys(sessionStorage);
                sessionKeys.forEach(key => {
                    if (key.startsWith('supabase') || key.includes('auth')) {
                        sessionStorage.removeItem(key);
                    }
                });
                
                console.log('✅ Manual logout completed');
                return { success: true, message: 'Signed out successfully (manual)' };
                
            } catch (manualError) {
                console.error('❌ Manual logout also failed:', manualError);
                return { success: false, error: 'Logout failed' };
            }
        }
    }

    // Get current user
    async getCurrentUser() {
        try {
            // If we already have a current user, return it
            if (this.currentUser) {
                return this.currentUser
            }
            
            // Otherwise fetch from Supabase
            const { data: { user }, error } = await supabase.auth.getUser()
            
            if (error && error.message !== 'Invalid JWT') {
                console.error('Error getting current user:', error)
                return null
            }
            
            this.currentUser = user
            if (user) {
                const { data: { session } } = await supabase.auth.getSession()
                this.authToken = session?.access_token
                await this.checkAdminStatus()
            }

            return user
        } catch (error) {
            console.error('Error getting current user:', error)
            return null
        }
    }

    // Check if current user is admin
    async checkAdminStatus() {
        if (!this.currentUser) {
            this.isAdmin = false
            return false
        }

        try {
            // For now, we'll assume no admin functionality until backend is ready
            this.isAdmin = false
            return this.isAdmin
        } catch (error) {
            console.error('Error checking admin status:', error)
            this.isAdmin = false
            return false
        }
    }

    // Get auth token for API requests
    getAuthToken() {
        // Get fresh token from current session
        if (this.authToken) {
            console.log('🔑 Using cached token:', this.authToken.substring(0, 20) + '...');
            
            // Check if token looks valid (basic validation)
            try {
                const payload = JSON.parse(atob(this.authToken.split('.')[1]));
                const now = Math.floor(Date.now() / 1000);
                
                if (payload.exp && payload.exp < now) {
                    console.warn('⚠️ Token appears to be expired');
                    this.refreshToken();
                    return null;
                }
                
                console.log('✅ Token validation passed, expires at:', new Date(payload.exp * 1000));
                return this.authToken;
            } catch (e) {
                console.warn('⚠️ Token validation failed:', e);
                return this.authToken; // Return anyway, let server validate
            }
        }
        
        console.warn('⚠️ No auth token available');
        return null;
    }

    // Add method to refresh token
    async refreshToken() {
        try {
            console.log('🔄 Refreshing authentication token...');
            const { data: { session }, error } = await supabase.auth.getSession();
            
            if (error) throw error;
            
            if (session) {
                this.currentUser = session.user;
                this.authToken = session.access_token;
                console.log('✅ Token refreshed successfully');
                return session.access_token;
            } else {
                console.warn('⚠️ No session found during refresh');
                this.currentUser = null;
                this.authToken = null;
                return null;
            }
        } catch (error) {
            console.error('❌ Failed to refresh token:', error);
            this.currentUser = null;
            this.authToken = null;
            return null;
        }
    }

    // Update user profile
    async updateProfile(updates) {
        try {
            const { data, error } = await supabase.auth.updateUser({
                data: updates
            })

            if (error) throw error

            return { success: true, data }
        } catch (error) {
            console.error('Update profile error:', error)
            return { success: false, error: error.message }
        }
    }

    // Reset password
    async resetPassword(email) {
        try {
            const { error } = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: `${window.location.origin}/reset-password.html`
            })

            if (error) throw error

            return { success: true, message: 'Password reset email sent' }
        } catch (error) {
            console.error('Reset password error:', error)
            return { success: false, error: error.message }
        }
    }
}

// Create global auth service instance and initialize it
window.authService = new AuthService()

console.log('🔧 Auth service created and initializing...')