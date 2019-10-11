var geneName = getUrlVars()['gene'];
var ENSID = getUrlVars()['ensid'];
var GENOME = getUrlVars()['org'];
var RELEASE = function (){
	//TODO: get the genome here! (hardcoding for mm10 atm)
        var tempRelease = null;
        $.ajax({
                'type' : "POST",
                'dataType' : "html",
		'data' : {genome: 'mm10'},
                'async' : false,
                'url' : "/primerDesign/python/web/ajaxCalls/fetchRelease.py",
                success : function (html) {
                        tempRelease = html.toString().trim();
                }
        });
        return tempRelease;
}();

document.title = geneName + " Manual Primer Entry";

// thank you anonymous author at html-online.com/articles/get-url-parameters-javascript/
function getUrlVars() {
    var vars = {};
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
        vars[key] = value;
    });
    return vars;
}

function populateOnLoad(){
	$('#page-title').html("Manually Enter Primer Pair for " + geneName);
}

function calculateFields(e){
	var fwdSeq = $("#forwardSequenceInput").val();
	var revSeq = $("#reverseSequenceInput").val();
	
	//check if the fwd input contains a value and called the method
	if (fwdSeq && $(e).attr('id') == "forwardSequenceInput"){
		var fwdSeqLen = String(fwdSeq.length);
		$("#forwardLength").val(fwdSeqLen);
		var fwdGcPercent = calculateGcPercent(fwdSeq.toUpperCase(), fwdSeqLen);
		$("#forwardGC").val(fwdGcPercent);
		setLocation(fwdSeq, $("#forwardLocation"), $("#blastForwardMsg"), true);
	}
	//check if the rev input contains a value and called the method
	if (revSeq && $(e).attr('id') == "reverseSequenceInput"){
		var revSeqLen = String(revSeq.length);
		$("#reverseLength").val(revSeqLen);
		var revGcPercent = calculateGcPercent(revSeq.toUpperCase(), revSeqLen);
		$("#reverseGC").val(revGcPercent);
		setLocation(revSeq, $("#reverseLocation"), $("#blastReverseMsg"), false);
	}
}

function calculateGcPercent(primerString, primerLen){
	var gcCount = 0;
	gcCount += (primerString.split("G").length - 1);
	gcCount += (primerString.split("C").length -1);
	percent = (gcCount/primerLen)*100.000;
	
	return percent.toFixed(2);
}

function setLocation(primerSeq, locationElement, spinner, forward){

	//prevent error on page refresh
	if (primerSeq === ""){
		return
	}
	
	locationElement.hide();
	spinner.css("display","block");
	$("#addToDatabaseButton").prop("disabled", true);
				
	$.ajax({
		dataType: "json",
		url: "/primerDesign/python/web/ajaxCalls/placePrimers.py",
		data: { primer : primerSeq,
			genome : GENOME},
		success: function(json){
			locationElement.show();
			spinner.css("display", "none");
			numBlastHits = Object.keys(json).length;
			if (numBlastHits > 1){
				locationElement.val("Multiple BLAST Hits");
				if (locationElement.hasClass('input-success')){
					locationElement.removeClass('input-success');
				}
				locationElement.addClass("input-warning");
				$("#blastWarning").css("display", "block");
				if (forward === true){
					displayBlastHits(json, $("#forwardBlastResults"), forward);
				}
				else {
					displayBlastHits(json, $("#reverseBlastResults"), forward);
				}
			
			}
			else if (numBlastHits == 0) {
				locationElement.val("No BLAST Hit");
				if (locationElement.hasClass('input-success')){
					locationElement.removeClass('input-success');
				}
				locationElement.addClass("input-warning");
			}
			else{
				// only one hit
				locationElement.val(String(json[0][1]));
				// if a previous result was bad, removes the warning class
				if (locationElement.hasClass('input-warning')){
					locationElement.removeClass('input-warning');
					//$("#blastWarning").css("display", "none");
					// clears the hit table for the type of primer
					if (forward === true){
						$("#forwardBlastResults").html("");
					}
					else {
						$("#reverseBlastResults").html("");
					}
					if ($("#forwardBlastResults").is(':empty') && $("#reverseBlastResults").is(':empty')){
						$("#blastWarning").css("display", "none");
					}
				}
				locationElement.addClass("input-success")			
				$("#addToDatabaseButton").prop("disabled", false);
			}
		},
		error: function(xhr, status, err){
			console.log(err)
			console.log(primerSeq);
			console.log(GENOME);
			console.log("Problem with call to Primer Blast program with input " + primerSeq);
		}
	});	

}

function parseLocation(hit){
	var loc = hit[1];
	var loc = hitObject['0']['chromosome'] + ":" + hitObject['0']['start'] + "-" + hitObject['0']['end'];
	if (hitObject['0']['strand'] === 'minus') {
		loc += ":-";
	}
	else {
		loc += ":+";
	}
	return loc

}

// print a table of the hits in the element passed
function displayBlastHits(hits, element, forward){
	if (forward === true){
		var tableHTML = "<h4>Forward Primer Blast Exact Matches</h4>"
	}
	else{
		var tableHTML = "<h4>Reverse Primer Blast Hits Exact Matches</h4>"
	}
	tableHTML += `
	<table class="table table-bordered">
	<thead>
		<tr>
		<th class="centreCell" scope="col">Location</th>
		</tr>
	</thead>
	<tbody>	
	`;
	
	//iterate through the hits
	for (var i=0; i < hits.length; i++){
		tableHTML += "<tr><td>" + String(hits[i][1]) + "</td></tr>";
	}
	tableHTML += "</tbody></table>"
	$(element).html(tableHTML);
}

function submitForm(){

	var form = $('#primerPairForm').serialize();
	form += '&gene=' + geneName;
	form += '&ensid=' + ENSID;
	form += '&release=' + RELEASE;
	form += '&genome=' + GENOME;
	
	$.ajax({
		type: "POST",
		url: "/primerDesign/python/web/ajaxCalls/manuallyAddPrimer.py",
		data: form,
		dataType: "html",
		success: function(html)
		{
			if (html.toString().trim() == "Successfully Added Primer Pair"){
				alert(html);
				window.opener.location.reload(false); //reload the parent so the new primer is displayed
				window.close();
			}
			else{
				alert(html);
			}
			

		},
		error: function(xhr, status, err, html) {
			alert("Problem Adding to Database: " + String(xhr.responseText));
		}
	});
}
