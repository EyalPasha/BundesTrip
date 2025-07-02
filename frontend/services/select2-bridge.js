document.addEventListener('DOMContentLoaded', function() {
  setTimeout(() => {
    // Import the logo formatter functions from the module
    import('./team-logos.js').then(module => {
      const { formatTeamOptionWithLogo, formatLeagueOptionWithLogo } = module;
      
      // Initialize with logo formatting
      $('#leagueFilter').select2({
        width: '100%',
        dropdownParent: $('body'),
        templateResult: formatLeagueOptionWithLogo,
        templateSelection: formatLeagueOptionWithLogo
      }).on('change', function() {
        const value = $(this).val();
        // console.log('League filter changed to:', value);
        window.applyScheduleFilters && window.applyScheduleFilters('league', value);
      });
      
      $('#teamFilter').select2({
        width: '100%',
        dropdownParent: $('body'),
        templateResult: formatTeamOptionWithLogo,
        templateSelection: formatTeamOptionWithLogo
      }).on('change', function() {
        const value = $(this).val();
        // console.log('Team filter changed to:', value);
        window.applyScheduleFilters && window.applyScheduleFilters('team', value);
      });
      
      // Add the select2-ready class to make elements visible
      document.body.classList.add('select2-ready');
      
      // Dispatch an event that the mobile filter can listen for
      document.dispatchEvent(new CustomEvent('select2Initialized'));
      
      // console.log('Select2 bridge initialized with logos and filters connected');
    }).catch(error => {
      console.error('Failed to load team-logos module:', error);
      
      // Fallback initialization without logos
      initializeWithoutLogos();
    });
  }, 300);

  function initializeWithoutLogos() {
    $('#leagueFilter, #teamFilter').select2({
      width: '100%',
      dropdownParent: $('body')
    }).on('change', function() {
      const id = $(this).attr('id');
      const value = $(this).val();
      const type = id === 'leagueFilter' ? 'league' : 'team';
      window.applyScheduleFilters && window.applyScheduleFilters(type, value);
    });
    
    document.body.classList.add('select2-ready');
    
    // Dispatch an event even in fallback mode
    document.dispatchEvent(new CustomEvent('select2Initialized'));
  }
});
