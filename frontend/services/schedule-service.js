import { fetchApi } from './api.js';
import { showErrorToast } from './notifications.js';

// Use the same API_BASE_URL as api.js
const API_BASE_URL = 'https://a582-2a06-c701-4572-4000-7c2a-f9b5-463d-9e0b.ngrok-free.app';

/**
 * Service for fetching schedule data
 */

// Cache for storing fetched data
const cache = {
    teams: null,
    leagues: null
};

/**
 * Fetch all available teams
 * @returns {Promise<string[]>} Array of team names
 */
export async function fetchAllTeams() {
    // Check if we already have the data in global state from main page
    if (window.globalTeamsData && window.globalTeamsData.teams) {
        cache.teams = window.globalTeamsData.teams;
        return window.globalTeamsData.teams;
    }
    
    // Check cache first
    if (cache.teams) {
        return cache.teams;
    }
    
    try {
        // Use fetchApi from api.js for consistent error handling
        const data = await fetchApi('/available-teams');
        
        // Store in cache and global state
        cache.teams = data.teams;
        window.globalTeamsData = data;
        
        return data.teams;
    } catch (error) {
        console.error('Error fetching teams:', error);
        throw error;
    }
}

/**
 * Fetch all available leagues
 * @returns {Promise<string[]>} Array of league names
 */
export async function fetchLeagues() {
    // Check if we already have the data in global state from main page
    if (window.globalLeaguesData && window.globalLeaguesData.leagues) {
        cache.leagues = window.globalLeaguesData.leagues;
        return window.globalLeaguesData.leagues;
    }
    
    // Check cache first
    if (cache.leagues) {
        return cache.leagues;
    }
    
    try {
        // Use fetchApi from api.js
        const data = await fetchApi('/available-leagues');
        
        // Store in cache and global state
        cache.leagues = data.leagues;
        window.globalLeaguesData = data;
        
        return data.leagues;
    } catch (error) {
        console.error('Error fetching leagues:', error);
        throw error;
    }
}

// Update other methods to use fetchApi
export async function fetchTeamSchedule(teamName) {
    return fetchApi(`/team-schedule/${encodeURIComponent(teamName)}`);
}

export async function fetchLeagueSchedule(leagueName) {
    return fetchApi(`/league-schedule/${encodeURIComponent(leagueName)}`);
}

export async function fetchGamesByDate(date) {
    return fetchApi(`/games-by-date/${date}`);
}

export async function fetchAvailableDates() {
    return fetchApi('/available-dates');
}