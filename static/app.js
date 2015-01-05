$(document).ready(function(){
	// Add and remove form input fields
	$('.multi-field-wrapper').each(function() {
	    var $wrapper = $('.multi-fields', this);
		// Add
	    $(".add-field", $(this)).click(function(e) {
			// Select, clone, and append input prototype
	        var field = $('.multi-field:first-child', $wrapper).clone(true).appendTo($wrapper);			
			// Empty out and focus
			field.find('input').val('').focus();
			// Show "remove" button
			field.find('button').css('display', 'inline');
	    });
		// Remove (hidden by default for first element)
	    $('.multi-field .remove-field', $wrapper).click(function() {
	        if ($('.multi-field', $wrapper).length > 1)
	            $(this).parent('.multi-field').remove();
	    });
	});
	
	// Loading screen
	$("form").submit(function(){
		$("#body").slideUp(400, function(){
			$("#loading").fadeIn(200);
		});
	});
});