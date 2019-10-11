$(document).ready(function() {
    $('.js-example-basic-single').select2();
});

function navigateToGenome() {
	genome = $("#genomeSelector option:selected").val();	
	jbrowseURL = window.location.protocol + "//" + window.location.host;
	jbrowseURL += "/jbrowse/index.html?data=data." + genome;
	window.open(jbrowseURL);
}
