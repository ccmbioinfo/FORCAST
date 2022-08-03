$(document).ready(function() {
    $('#genomeSelector').select2();

	$.post("../primer-design/web/ajaxCalls/fetchInstalledGenomes.py", function(data) {
		$("#genomeSelector").html(data);
	});

	$("#goButton").click(function () {
		var genome = $("#genomeSelector option:selected").val();
		location = "/jbrowse/index.html?data=data/" + genome;
	});
});
