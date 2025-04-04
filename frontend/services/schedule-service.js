import { showErrorToast } from './notifications.js';

const API_BASE_URL = 'http://localhost:8000';

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
        const response = await fetch(`${API_BASE_URL}/available-teams`);
        if (!response.ok) {
            throw new Error(`Failed to fetch teams: ${response.status}`);
        }
        
        const data = await response.json();
        
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
        const response = await fetch(`${API_BASE_URL}/available-leagues`);
        if (!response.ok) {
            throw new Error(`Failed to fetch leagues: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Store in cache and global state
        cache.leagues = data.leagues;
        window.globalLeaguesData = data;
        
        return data.leagues;
    } catch (error) {
        console.error('Error fetching leagues:', error);
        throw error;
    }
}

/**
 * Fetch team schedule
 * @param {string} teamName - Name of the team
 * @param {number} days - Days to look ahead (default: 60)
 * @returns {Promise<Object>} Team schedule data
 */
export async function fetchTeamSchedule(teamName, days = 60) {
    try {
        const response = await fetch(`${API_BASE_URL}/team-schedule/${encodeURIComponent(teamName)}?days=${days}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch team schedule: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Error fetching schedule for ${teamName}:`, error);
        throw error;
    }
}

/**
 * Fetch league schedule
 * @param {string} leagueName - Name of the league
 * @param {number} days - Days to look ahead (default: 60)
 * @returns {Promise<Object>} League schedule data
 */
export async function fetchLeagueSchedule(leagueName, days = 60) {
    try {
        const response = await fetch(`${API_BASE_URL}/league-schedule/${encodeURIComponent(leagueName)}?days=${days}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch league schedule: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Error fetching schedule for ${leagueName}:`, error);
        throw error;
    }
}

/**
 * Fetch games by date
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<Object>} Games for the specified date
 */
export async function fetchGamesByDate(date) {
    try {
        const response = await fetch(`${API_BASE_URL}/games-by-date/${date}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch games for date: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Error fetching games for ${date}:`, error);
        throw error;
    }
}

/**
 * Fetch available dates with games
 * @param {number} days - Days to look ahead (default: 60)
 * @returns {Promise<Object>} Dates with available games
 */
export async function fetchAvailableDates(days = 60) {
    try {
        const response = await fetch(`${API_BASE_URL}/available-dates?days=${days}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch available dates: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching available dates:', error);
        throw error;
    }
}