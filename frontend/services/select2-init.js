import { 
    formatTeamOptionWithLogo, 
    formatTeamSelectionWithLogo,
    formatLeagueOptionWithLogo,
    formatLeagueSelectionWithLogo 
} from './team-logos.js';

/**
 * Properly initialize the Must Teams Select2 dropdown with logos
 */
export function initMustTeamsSelect() {
    // Destroy any existing Select2 instance first
    if ($.fn.select2 && $('#mustTeams').data('select2')) {
        $('#mustTeams').select2('destroy');
    }
    
    // Initialize with proper options
    $('#mustTeams').select2({
        placeholder: 'Select Teams',
        width: '100%',
        closeOnSelect: false,
        allowClear: true,
        minimumResultsForSearch: Infinity,
        templateResult: formatTeamOptionWithLogo,
        templateSelection: formatTeamSelectionWithLogo,
        selectionCssClass: 'select2-selection--clean',
        dropdownCssClass: 'select2-dropdown--clean',
        dropdownParent: $('body')
    }).on('select2:open', function() {
        document.body.classList.add('mustteams-dropdown-open');
        
        setTimeout(() => {
            const dropdown = document.querySelector('.select2-dropdown');
            if (dropdown) {
                dropdown.style.zIndex = '10000';
                dropdown.style.position = 'absolute';
            }
        }, 0);
    }).on('select2:close', function() {
        document.body.classList.remove('mustteams-dropdown-open');
    });
}

/**
 * Properly initialize the Preferred Leagues Select2 dropdown with logos
 */
export function initPreferredLeaguesSelect() {
    console.log("Initializing league select with logos");
    
    // Destroy any existing Select2 instance first
    if ($.fn.select2 && $('#preferredLeagues').data('select2')) {
        $('#preferredLeagues').select2('destroy');
    }
    
    // Initialize with proper options
    $('#preferredLeagues').select2({
        placeholder: 'Select Leagues',
        width: '100%',
        closeOnSelect: false,
        allowClear: true,
        minimumResultsForSearch: Infinity,
        templateResult: formatLeagueOptionWithLogo,
        templateSelection: formatLeagueSelectionWithLogo,
        selectionCssClass: 'select2-selection--clean',
        dropdownCssClass: 'select2-dropdown--clean',
        dropdownParent: $('body')
    }).on('select2:open', function() {
        document.body.classList.add('leagues-dropdown-open');
        
        setTimeout(() => {
            const dropdown = document.querySelector('.select2-dropdown');
            if (dropdown) {
                dropdown.style.zIndex = '10000';
                dropdown.style.position = 'absolute';
            }
        }, 0);
    }).on('select2:close', function() {
        document.body.classList.remove('leagues-dropdown-open');
    });
}