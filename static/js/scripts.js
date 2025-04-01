$(document).ready(function() {
    // Simple toggle approach for user dropdown
    $('#userDropdown').click(function(e) {
        e.stopPropagation();
        $('#userMenu').toggle();
    });
    
    // Close dropdown when clicking elsewhere on the page
    $(document).click(function() {
        $('#userMenu').hide();
    });
    
    // Resources collapsible toggle
    $('.collapsible-header').click(function() {
        const target = $(this).data('target');
        $(target).collapse('toggle');
    });
});
