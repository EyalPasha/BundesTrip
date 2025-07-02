// Global navigation state management

async function updateNavigationState() {
    try {
        const user = await window.authService?.getCurrentUser();
        
        // Get navigation elements
        const loginMenuItem = document.getElementById('loginMenuItem');
        const registerMenuItem = document.getElementById('registerMenuItem');
        const userDropdown = document.getElementById('userDropdown');
        const userDisplayName = document.getElementById('userDisplayName');
        const adminLink = document.getElementById('adminLink');
        
        if (user) {
            // User is logged in - show user dropdown, hide login/register
            if (loginMenuItem) loginMenuItem.style.display = 'none';
            if (registerMenuItem) registerMenuItem.style.display = 'none';
            if (userDropdown) userDropdown.classList.remove('d-none');
            
            // Set user display name
            if (userDisplayName) {
                const displayName = user.user_metadata?.full_name || 
                                   user.email?.split('@')[0] || 
                                   'User';
                userDisplayName.textContent = displayName;
            }
            
            // Show admin link if user is admin
            if (adminLink && window.authService?.isAdmin) {
                adminLink.style.display = 'block';
            }
            
        } else {
            // User is not logged in - show login/register, hide user dropdown
            if (loginMenuItem) loginMenuItem.style.display = 'block';
            if (registerMenuItem) registerMenuItem.style.display = 'block';
            if (userDropdown) userDropdown.classList.add('d-none');
            if (adminLink) adminLink.style.display = 'none';
        }
    } catch (error) {
        console.error('Error updating navigation state:', error);
    }
}

async function logoutUser() {
    // console.log('🔓 Attempting to log out...');
    
    try {
        // Clear local state first
        if (window.authService) {
            window.authService.currentUser = null;
            window.authService.authToken = null;
            window.authService.isAdmin = false;
        }
        
        // Update navigation immediately
        await updateNavigationState();
        
        // Attempt to sign out from Supabase
        let signOutSuccess = false;
        
        try {
            const result = await window.authService?.signOut();
            signOutSuccess = result?.success || false;
            // console.log('Supabase sign out result:', result);
        } catch (supabaseError) {
            console.warn('Supabase sign out failed (but continuing with local logout):', supabaseError);
        }
        
        // Clear any stored tokens in localStorage
        try {
            localStorage.removeItem('supabase.auth.token');
            sessionStorage.removeItem('supabase.auth.token');
        } catch (storageError) {
            console.warn('Error clearing storage:', storageError);
        }
        
        // REMOVED: showNavigationToast('Logged out successfully', 'success');
        
        // Redirect to home if on protected page
        const protectedPages = ['profile.html', 'admin.html'];
        const currentPage = window.location.pathname.split('/').pop();
        if (protectedPages.includes(currentPage)) {
            setTimeout(() => {
                window.location.href = './index.html';
            }, 1000);
        } else {
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
        
    } catch (error) {
        console.error('Logout error:', error);
        
        // Even if Supabase logout fails, clear local state
        if (window.authService) {
            window.authService.currentUser = null;
            window.authService.authToken = null;
            window.authService.isAdmin = false;
        }
        
        await updateNavigationState();
        // REMOVED: showNavigationToast('Logged out (with some issues)', 'warning');
        
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

function showNavigationToast(message, type = 'info') {
    // Create toast if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'navToast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert">
            <div class="toast-header text-${type === 'error' ? 'danger' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'primary'}">
                <i class="fas fa-info-circle me-2"></i>
                <strong class="me-auto">BundesTrip</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const bsToast = new bootstrap.Toast(toastElement);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Export for use in modules
window.updateNavigationState = updateNavigationState;
window.logoutUser = logoutUser;