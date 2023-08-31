/* Hillary Elrick, August 2018
Javascript functions run from geneFeatures.html to connect to the mongo
database & fetch the primers and guides associated with the gene passed.
All scripts are in python/web/ajaxCalls and return html which is used
to populate the elements on the page.
*/

//set the geneName from the url and page title before loading the body
var geneName = getUrlVars()["gene"];
var ENSID = getUrlVars()["ensid"];
var GENOME = getUrlVars()["org"];

document.title = geneName + " Info";
var existingPrimersCount = 0;

let forcastEnsemblRelease;

// Check if FORCAST is using the most up-to-date Ensembl release
const checkRelease = () => {
  let ensemblRelease;
  $.when(
    $.ajax({
      type: "POST",
      dataType: "html",
      data: { genome: GENOME },
      url: "./ajaxCalls/fetchRelease.py",
      success: function (html) {
        forcastEnsemblRelease = html.toString().trim();
        $("#primer-design-button").prop("disabled", false).text("Design Primers");
      },
    }),
    $.ajax({
      type: "POST",
      dataType: "html",
      url: "./ajaxCalls/fetchEnsemblRelease.py",
      success: function (html) {
        ensemblRelease = html.toString().trim();
      },
    }),
  ).then(() => {
    setTimeout(() => {
      if (ensemblRelease.startsWith("The Ensembl Rest API is not responding")) {
        $("#warningMessage").html(`JBrowse is using release ${forcastEnsemblRelease}. ${ensemblRelease}`);
      } else if (forcastEnsemblRelease !== ensemblRelease) {
        $("#warningMessage").html(
          `Warning: JBrowse is using release ${forcastEnsemblRelease}, Ensembl is on release ${ensemblRelease}`,
        );
      } else {
        $("#warningMessage").html("");
      }
    }, 1000);
  });
};

//boolean to indicate whether the design script has been run yet during this session
var primersDesigned = false;

// after the page has loaded, populate and set elements
function PopulatePage() {
  $("#loadingIcon").hide();
  //$('#designButton').hide();
  getGuides(geneName);
  getPrimers(geneName);
  $("#pageHeading").append(geneName + " Info");
  checkRelease();
  $("#updateNotesSpinner").hide();
}

function unlockLabel(e) {
  if ($(e).attr("class") == "fa fa-lock") {
    $(e).addClass("fa-unlock").removeClass("fa-lock");
    $(".guideLabels").attr("contenteditable", "true");
  } else {
    $(e).addClass("fa-lock").removeClass("fa-unlock");
    $(".guideLabels").attr("contenteditable", "false");
  }
}

function unlockNotes(e) {
  if ($(e).attr("class") == "fa fa-lock") {
    $(e).addClass("fa-unlock").removeClass("fa-lock");
    $(".guideNotes").prop("disabled", false);
  } else {
    $(e).addClass("fa-lock").removeClass("fa-unlock");
    $(".guideNotes").prop("disabled", true);
  }
}

function updateGuideLabel(e, guideID) {
  var newLabel = $(e).html().toString().trim();
  newLabel = encodeURI(newLabel);
  $.ajax({
    type: "POST",
    url: "./ajaxCalls/updateGuideLabel.py",
    data: {
      recordID: guideID,
      newValue: newLabel,
      genome: GENOME,
    },
    dataType: "html",
    success: function (html) {
      if (html.toString().trim() == "Successfully Updated Guide Label") {
        //do nothing
      } else {
        alert(html);
      }
    },
  });
}

function updateGuideNote(e, guideID) {
  var newNote = $(e).val().toString().trim();
  newNote = encodeURI(newNote);
  $.ajax({
    type: "POST",
    url: "./ajaxCalls/updateGuideNote.py",
    data: {
      recordID: guideID,
      newValue: newNote,
      genome: GENOME,
    },
    dataType: "html",
    success: function (html) {
      if (html.toString().trim() == "Successfully Updated Guide Note") {
        // do nothing
      } else {
        alert(html);
      }
    },
  });
}

// fetch the guides associated with the gene from the database based on ensid
function getGuides(geneName) {
  $.ajax({
    type: "POST",
    url: "./ajaxCalls/fetchGuides.py",
    data: {
      geneName: geneName,
      ensid: ENSID,
      genome: GENOME,
    },
    dataType: "html",
    success: function (html) {
      $("#guideTable").append(html);
      if (html.toString().trim() == "<p>No saved guides for " + geneName + "</p>") {
        // if no guides found, don't show options
        $("#guideButtonGroup").hide();
      }
      updateGuideDownloadLinks();
    },
  });
}

// fetch primers associated with gene based on ensid (also pass geneName for msgs)
function getPrimers(geneName) {
  $.ajax({
    type: "POST",
    url: "./ajaxCalls/fetchPrimers.py",
    data: {
      gene: geneName,
      ensid: ENSID,
      genome: GENOME,
    },
    dataType: "html",
    success: function (html) {
      $("#collapseTwo").collapse("show");
      $("#existingPrimersTable").html(html);
      $("#updateNotesSpinner").hide();
      setPrimersCount();
      //set the download links
      updateGuideDownloadLinks();
    },
  });
}

function setPrimersCount() {
  var countNotes = 0;
  $("#existingPrimersTable textarea").each(function () {
    countNotes = countNotes + 1;
  });
  existingPrimersCount = countNotes;
}

function checkAllPrimersUpdated() {
  existingPrimersCount = existingPrimersCount - 1;
  if (existingPrimersCount == 0) {
    $("#updateNotesSpinner").hide();
    setPrimersCount();
  }
}

var errorDisplayed = false;

function displayErrorOnce(msg) {
  if (errorDisplayed == false) {
    alert("Error Updating Notes: " + msg);
    errorDisplayed = true;
  }
}

function updatePrimerStatus(e) {
  var primerID = $(e).closest("tr").attr("id");
  if ($(e).html() == "Reject") {
    var new_status = "Rejected";
  } else {
    var new_status = "Accepted";
  }
  $.ajax({
    type: "POST",
    url: "./ajaxCalls/updatePrimerStatus.py",
    data: {
      record: primerID,
      newstatus: new_status,
      genome: GENOME,
    },
    dataType: "html",
    success: function (html) {
      if (html.toString().trim() == "Successfully updated the record") {
        var btn = $(e).parent().prev("button");
        if (new_status == "Rejected") {
          btn.html(new_status);
          btn.removeClass("accepted-dropdown");
          btn.addClass("rejected-dropdown");
          $(e).html("Accept");
        } else {
          btn.html(new_status);
          btn.removeClass("rejected-dropdown");
          btn.addClass("accepted-dropdown");
          $(e).html("Reject");
        }
        //update the download links for accepted primers/guides
        updateGuideDownloadLinks();
      } else {
        alert(html);
      }
    },
    error: function (jqXHR, status, err, html) {
      alert("Problem updating primer record: " + String(jqXHR));
    },
  });
}

function updatePrimerNotes() {
  var notes = new Array();
  $("#updateNotesSpinner").show();
  $("#existingPrimersTable textarea").each(function () {
    primerID = $(this).closest("tr").attr("id");
    primerNotes = encodeURI($(this).val());
    $.ajax({
      type: "POST",
      url: "./ajaxCalls/updatePrimerNotes.py",
      data: {
        record: primerID,
        newNotes: primerNotes,
        genome: GENOME,
      },
      dataType: "html",
      success: function (html) {
        successMsg = html.toString().trim() == "Successfully Updated Notes";
        if (successMsg === true) {
          checkAllPrimersUpdated();
        } else {
          displayErrorOnce(html);
        }
      },
      error: function (jqXHR, status, err, html) {
        displayErrorOnce(html);
      },
    });
  });
}

function manuallyEnterPrimers() {
  url = `${location.protocol}//${location.host}/src/primer-design/web/manualPrimerEntry.html?gene=${geneName}&ensid=${ENSID}&org=${GENOME}`;
  PopupCenter(url, "ManualPrimerEntry", 1200, 350);
}

// credit to user 'Tony M' on stackoverflow (https://stackoverflow.com/questions/4068373/center-a-popup-window-on-screen)
function PopupCenter(url, title, w, h) {
  // Fixes dual-screen position                         Most browsers      Firefox
  var dualScreenLeft = window.parent.screenLeft != undefined ? window.parent.screenLeft : window.parent.screenX;
  var dualScreenTop = window.parent.screenTop != undefined ? window.parent.screenTop : window.parent.screenY;

  var width = window.parent.innerWidth
    ? window.parent.innerWidth
    : document.documentElement.clientWidth
    ? document.documentElement.clientWidth
    : screen.width;
  var height = window.parent.innerHeight
    ? window.parent.innerHeight
    : document.documentElement.clientHeight
    ? document.documentElement.clientHeight
    : screen.height;

  var left = width / 2 - w / 2 + dualScreenLeft;
  var top = height / 2 - h / 2 + dualScreenTop;
  var newWindow = window.open(
    url,
    title,
    "scrollbars=yes, width=" + w + ", height=" + h + ", top=" + top + ", left=" + left,
  );

  // Puts focus on the newWindow
  if (window.focus) {
    newWindow.focus();
  }
}

function addPrimersToDatabase() {
  var values = getSelected();
  var data = {};
  data["gene"] = geneName;
  data["release"] = forcastEnsemblRelease;
  data["wtPair"] = values[0];
  data["emPair"] = values[1];
  data["genome"] = GENOME;

  $.ajax({
    method: "GET",
    url: "./ajaxCalls/addPrimers.py",
    dataType: "html",
    data: data,
    success: function (html) {
      alert(html);
      getPrimers(geneName);
      $("#collapseThree").collapse("hide");
      //update the downloads for saved guides/primers
      updateGuideDownloadLinks();
    },
    error: function (jqXHR, status, err, html) {
      alert("Error: " + status);
    },
  });
}

function backendUpdateStatus(element, recordID) {
  var isChecked = $(element).prop("checked");
  if (isChecked === true) {
    statusValue = "Accepted";
  } else {
    statusValue = "Rejected";
  }
  $.ajax({
    method: "POST",
    url: "./ajaxCalls/updateGuides.py",
    dataType: "html",
    data: {
      record: recordID,
      newstatus: statusValue,
      genome: GENOME,
    },
    success: function (html) {
      //update the csv/ape downloads
      updateGuideDownloadLinks();
    },
    error: function (jqXHR, status, err, html) {
      alert(err, html);
    },
  });
}

// design primers using all accepted guides for the gene
function RunPrimerDesignScript() {
  $("#primerHeading").append("Primers");
  $("#loadingIcon").show();
  $("#collapseThree").collapse("show");
  if (primersDesigned === true) {
    $("#primerResultsTable").html("");
  }
  $.ajax({
    type: "POST",
    url: "../designPrimers.py",
    cache: false,
    data: {
      gene: geneName,
      genome: GENOME,
    },
    dataType: "html",
    tryCount: 0,
    retryLimit: 3,
    success: function (html) {
      $("#primerResultsTable").html(html);
      primersDesigned = true;
      $("#loadingIcon").hide();
      primerSelect();
      inSilica();
      blastPrimers();
    },
    error: function (jqXHR, status, err) {
      if ((jqXHR.status = 504)) {
        this.tryCount++;
        if (this.tryCount <= this.retryLimit) {
          $.ajax(this);
          return;
        } else {
          $("#loadingIcon").attr("src", "img/warning-icon.png");
          $("#loadingIcon").attr("title", "Design Timed Out. Please try again");
        }
      }
    },
  });
}

function blastPrimers() {
  $("#primerResultsTable")
    .find("td")
    .each(function () {
      if ($(this).text() === "Forward" || $(this).text() === "Reverse") {
        primerSeq = $(this).next("td");
        locationElement = primerSeq.next("td").next("td");
        blastCall(primerSeq.text(), locationElement);
      }
    });
}

function inSilica() {
  //check if dicey installed
  $.ajax({
    dataType: "html",
    url: "./ajaxCalls/diceyInstalled.py",
    data: { genome: GENOME },
    success: function (html) {
      if (Number(html.toString().trim()) == 1) {
        var primers = [];
        var productCell = null;
        $("#primerResultsTable")
          .find("td")
          .each(function () {
            if ($(this).text() === "Forward" || $(this).text() === "Reverse") {
              sequence = $(this).next("td");
              primers.push(sequence.text());
              if (primers.length == 2) {
                diceyCall(primers, productCell);
                primers = [];
                productCell = null;
              } else {
                // not the prettiest but this gets the product cell element for the row
                // it's stored in the first row of a primerpair so  when the length of
                // primers is 1 (i.e. we're on the first primer of a pair), the product
                // size cell element is 3 away
                productCell = sequence.next("td").next("td").next("td");
              }
            }
          });
      }
    },
    error: function (xhr, status, err) {
      console.log(err);
    },
  });
}

const createDiceyMessagesModal = (messages, rowID) => {
  const [warnings, errors] = messages.reduce(
      (acc, { title, type }) => {
        acc[type === "warning" ? 0 : 1].push(title);

        return acc;
      },
      [[], []],
    ),
    numWarnings = warnings.length,
    numErrors = errors.length;

  let html = `
		<button
			type="button"
			class="btn btn-link no-padding"
			style="display: block; margin: 0 auto; background-color: #ffe9a8; border: 1px solid #b90e1e; color: #b90e1e; border-radius: 20px; padding: 0 0.5rem; font-size: 0.75rem;"
			data-toggle="modal"
			data-target="#${rowID}-qa-messages-modal"
		>
			${numErrors} Error${numErrors !== 1 ? "s" : ""} / ${numWarnings} Warning${numWarnings !== 1 ? "s" : ""}
		</button>
		<div class="modal fade" id="${rowID}-qa-messages-modal">
			<div class="modal-dialog modal-lg">
				<div class="modal-content">
					<div class="modal-header" style="padding-bottom: 0.25rem">
						<h4 class="modal-title">Dicey Errors / Warnings</h4>
						<br>
						<button type="button" class="close" data-dismiss="modal">&times;</button>
					</div>
					<div class="modal-body">
						<ul class="nav nav-tabs" role="tablist">
							<li class="nav-item">
								<button class="nav-link active" id="${rowID}-errors-tab" data-toggle="tab" href="#${rowID}-errors" type="button" role="tab" aria-controls="${rowID}-errors" aria-selected="true">Errors (${numErrors})</button>
							</li>
							<li class="nav-item">
								<button class="nav-link" id="${rowID}-warnings-tab" data-toggle="tab" href="#${rowID}-warnings" type="button" role="tab" aria-controls="${rowID}-warnings" aria-selected="false">Warnings (${numWarnings})</button>
							</li>
						</ul>
						<div class="tab-content pt-3 px-3">
							<div class="tab-pane fade show active" id="${rowID}-errors" role="tabpanel" aria-labelledby="${rowID}-errors-tab">
								<ul class="list-group">
								
	`;

  if (errors.length) {
    errors.forEach((error) => {
      html += `
									<li class="list-group-item">${error}</li>
			`;
    });
  } else {
    html += `
									<li class="list-group-item p-1">No errors.</li>
		`;
  }

  html += `
								</ul>
							</div>
							<div class="tab-pane fade" id="${rowID}-warnings" role="tabpanel" aria-labelledby="${rowID}-warnings-tab">
								<ul class="list-group">
	`;

  if (warnings.length) {
    warnings.forEach((warning) => {
      html += `
									<li class="list-group-item">${warning}</li>
			`;
    });
  } else {
    html += `
									<li class="list-group-item p-1">No warnings.</li>	
		`;
  }

  html += `
								</ul>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;

  return html;
};

function diceyCall(primers, productCell) {
  // populate with loading graphic at start of ajax call
  productCell.append('<span id="diceyLoader"><br><i class="fa fa-spinner fa-spin"></i></span>');
  $.ajax({
    dataType: "json",
    url: "./ajaxCalls/primerQA.py",
    data: { primers: JSON.stringify(primers), genome: GENOME },
    success: function (json) {
      // remove spinner
      productCell.children("#diceyLoader").remove();
      const rowID = productCell.parent().attr("id"),
        messages = json["errors"],
        jsonData = json["data"],
        amplicons = jsonData["amplicons"],
        bindingSites = jsonData["primers"],
        numAmplicons = amplicons.length,
        numBindingSites = bindingSites.length;
      if (numAmplicons > 1) {
        productCell.css({
          "background-color": "#f8d7da",
          color: "#b90e1e",
        });
        preformattedString =
          '<br><button type="button" class="btn btn-link no-padding" data-toggle="modal" data-target="#' +
          rowID +
          '-qa-modal">';
        preformattedString +=
          '<pre style="font-size:0.75rem;padding: 0.25rem;color: #b90e1e;text-decoration:underline;">';
        preformattedString += numAmplicons + " Amplicons\n" + numBindingSites + " Binding Sites</pre>";
        preformattedString += "</button>";
        preformattedString += createDiceyModal(rowID, amplicons, bindingSites);
        productCell.append(preformattedString);
        // link to dialog with multiple amplicons
      } else if (numAmplicons == 1 && numBindingSites > 25) {
        productCell.css("background-color", "#ffe9a8");
        preformattedString =
          '<br><button type="button" class="btn btn-link no-padding" data-toggle="modal" data-target="#' +
          rowID +
          '-qa-modal">';
        preformattedString += '<pre style="font-size:0.75rem;padding: 0.25rem;text-decoration:underline;">';
        preformattedString += numAmplicons + " Amplicon\n" + numBindingSites + " Binding Sites</pre>";
        preformattedString += "</button>";
        preformattedString += createDiceyModal(rowID, amplicons, bindingSites);
        productCell.append(preformattedString);
      } else if (numAmplicons == 1) {
        // exactly one amplicon, good.
        productCell.css("background-color", "#dff0d8");
        preformattedString =
          '<br><button type="button" class="btn btn-link no-padding" data-toggle="modal" data-target="#' +
          rowID +
          '-qa-modal">';
        preformattedString += '<pre style="font-size:0.75rem;padding: 0.25rem;text-decoration:underline;">';
        preformattedString += numAmplicons + " Amplicon\n" + numBindingSites + " Binding Sites</pre>";
        preformattedString += "</button>";
        preformattedString += createDiceyModal(rowID, amplicons, bindingSites);
        productCell.append(preformattedString);
      } else {
        //TODO: change, this is for degbug
        productCell.append('<br><pre style="padding: 0.25rem; font-size: 0.75rem;">No Amplicons</pre>');
      }

      if (messages.length) productCell.append(createDiceyMessagesModal(messages, rowID));
    },
    error: function (xhr, status, err) {
      // remove spinner
      productCell.children("#diceyLoader").remove();
      productCell.append(
        '<br><span style="display: inline-block; max-width: 20vw; background-color: #e9f3fd; border: 1px solid #b90e1e; color: #b90e1e; border-radius: 30px; padding: 0.25rem 0.5rem; font-size: 0.75rem; word-break: break-word;"><i class="fa fa-exclamation-triangle"></i><br>An error ocurred while performing primer QA</span>',
      );
      console.log("Problem performing primer QA with locally installed dicey program");
    },
  });
}

function createDiceyModal(rowID, amplicons, bindingSites) {
  // using ` for multiline string here (may not highlight in vim)
  html =
    `<div class="modal fade" id="` +
    rowID +
    `-qa-modal">
		    <div class="modal-dialog modal-lg">
		      <div class="modal-content">
		  
			<div class="modal-header" style="padding-bottom: 0.25rem">
			  <h4 class="modal-title">Primer QA Results</h4>
			  <br>
			  <button type="button" class="close" data-dismiss="modal">&times;</button>
			</div>
		<div class="modal-body">
			<p style="text-align: left;">Generated by in silico PCR tool <a href="https://github.com/gear-genomics/dicey/" target="_blank">Dicey</a></p>`;

  //the ids need to be specific to the row ID (for the divs as well)
  html +=
    `
	<ul class="nav nav-tabs" role="tablist">
  		<li class="nav-item">
    		<a class="nav-link active" id="amplicon-tab-` +
    rowID +
    `" data-toggle="tab" href="#ampliconsTab-` +
    rowID +
    `" role="tab" >Amplicons</a>
  		</li>
  		<li class="nav-item">
    		<a class="nav-link" id="bindingSite-tab-` +
    rowID +
    `" data-toggle="tab" href="#bindingSitesTab-` +
    rowID +
    `" role="tab">Binding Sites</a>
  		</li>
  	</ul>
	<div class="tab-content">
  	<div class="tab-pane fade show active" id="ampliconsTab-` +
    rowID +
    `" role="tabpanel" style="text-align:left; padding:1rem; margin:0;">`;
  // print out all the amplicon details
  Object.keys(amplicons).forEach((a, i) => {
    if (amplicons.hasOwnProperty(a)) {
      rank = amplicons[a]["Id"] + 1;
      if (i !== 0) html += "<br>";
      html += "<b>Amplicon " + rank + "</b><br>";
      html += "Length: " + amplicons[a]["Seq"].length + "<br>";
      html +=
        "Location: chr" + amplicons[a]["Chrom"] + ":" + amplicons[a]["ForPos"] + "-" + amplicons[a]["RevEnd"] + "<br>";

      // dicey doesn't consider the direction of the gene, need to check if reversal of primers required
      if (amplicons[a]["ForName"] == "leftPrimer") {
        html += "Forward Primer: " + amplicons[a]["ForSeq"] + "<br>";
        html += "Forward Tm: " + amplicons[a]["ForTm"].toFixed(2) + "<br>";
        html += "Reverse Primer: " + amplicons[a]["RevSeq"] + "<br>";
        html += "Reverse Tm: " + amplicons[a]["RevTm"].toFixed(2) + "<br>";
        // sequence gets really long. commenting out for now
        //html += "Sequence: " + amplicons[a]['Seq']
      } else if (amplicons[a]["ForName"] == "rightPrimer") {
        html += "Forward Primer: " + amplicons[a]["RevSeq"] + "<br>";
        html += "Forward Tm: " + amplicons[a]["RevTm"].toFixed(2) + "<br>";
        html += "Reverse Primer: " + amplicons[a]["ForSeq"] + "<br>";
        html += "Reverse Tm: " + amplicons[a]["ForTm"].toFixed(2) + "<br>";
      } else {
        console.log("Primer Names not Set Correctly in Dicey Backend");
      }
    }
  });

  // open up the div for the binding sites tab
  html +=
    `	
	</div>
  	<div class="tab-pane fade" id="bindingSitesTab-` +
    rowID +
    `" role="tabpanel"><br>`;

  // split the binding sites so they're separated by primer & can be reported in separate tables
  var forwardBindingSites = {};
  var forwardPrimer = "";
  var reverseBindingSites = {};
  var reversePrimer = "";
  for (var b in bindingSites) {
    if (bindingSites.hasOwnProperty(b)) {
      // names set when running Dicey in backend (direction relative to gene)
      if (bindingSites[b]["Name"] == "leftPrimer") {
        forwardBindingSites[b] = bindingSites[b];
        // if unset, record the primer seq
        if (forwardPrimer == "") {
          forwardPrimer = forwardBindingSites[b]["Seq"];
        }
      } else if (bindingSites[b]["Name"] == "rightPrimer") {
        reverseBindingSites[b] = bindingSites[b];
        if (reversePrimer == "") {
          reversePrimer = reverseBindingSites[b]["Seq"];
        }
      } else {
        console.log("JSON object from dicey returned primer with unknown name");
      }
    }
  }

  // create the tables to report the left/forward primer binding sites
  html +=
    `
	<p style="float: left;">Forward Primer (` +
    forwardPrimer +
    `):</p>	
	<table class="table bordered>" style="margin-bottom: 0.5rem;" id="forwardBindingSitesTable">
	<thead>
	<tr>
	<th class="centreCell" scope="col">Binding Site</th>
	<th class="centreCell" scope="col">Sequence</th>
	<th class="centreCell" scope="col">Tm</th>
	</tr>
	</thead>
	<tbody>`;
  var count = 0;
  var limit = 15;
  for (var b in forwardBindingSites) {
    if (count > limit) {
      break;
    }
    var strand = "";
    if (forwardBindingSites[b]["Ori"] == "forward") {
      strand = "+";
    } else if (forwardBindingSites[b]["Ori"] == "reverse") {
      strand = "-";
    }

    //write the row
    html += "<tr>";
    html +=
      "<td>chr" +
      forwardBindingSites[b]["Chrom"] +
      ":" +
      forwardBindingSites[b]["Pos"] +
      "-" +
      forwardBindingSites[b]["End"] +
      strand +
      "</td>";
    html += "<td>" + forwardBindingSites[b]["Genome"] + "</td>";
    html += "<td>" + forwardBindingSites[b]["Tm"].toFixed(2) + "</td>";
    html += "</tr>";
    count++;
  }
  html += "</tbody></table>";
  // if we cut off early, print a message
  if (count > limit) {
    var numSites = Object.keys(forwardBindingSites).length;
    html += "<p>(" + limit + " of " + numSites + " Binding Sites Listed)</p>";
  } else {
    // formatting purposes
    html += "<br>";
  }

  // print table for reverse primers
  html +=
    `
	<p style="float: left;">Reverse Primer (` +
    reversePrimer +
    `):</p>	
	<table class="table bordered>" style="margin-bottom: 0.5rem;" id="reverseBindingSitesTable">
	<thead>
	<tr>
	<th class="centreCell" scope="col">Binding Site</th>
	<th class="centreCell" scope="col">Sequence</th>
	<th class="centreCell" scope="col">Tm</th>
	</tr>
	</thead>
	<tbody>`;
  count = 0; //reset the count
  for (var b in reverseBindingSites) {
    if (count > limit) {
      break;
    }
    var strand = "";
    if (reverseBindingSites[b]["Ori"] == "forward") {
      strand = "+";
    } else if (reverseBindingSites[b]["Ori"] == "reverse") {
      strand = "-";
    }

    //write the row
    html += "<tr>";
    html +=
      "<td>chr" +
      reverseBindingSites[b]["Chrom"] +
      ":" +
      reverseBindingSites[b]["Pos"] +
      "-" +
      reverseBindingSites[b]["End"] +
      strand +
      "</td>";
    html += "<td>" + reverseBindingSites[b]["Genome"] + "</td>";
    html += "<td>" + reverseBindingSites[b]["Tm"].toFixed(2) + "</td>";
    html += "</tr>";
    count++;
  }
  html += "</tbody></table>";
  if (count > limit) {
    var numSites = Object.keys(reverseBindingSites).length;
    html += "<p>(" + limit + " of " + numSites + " Binding Sites Listed)</p>";
  }

  html += `</div></div></div>
		<div class="modal-footer">
		<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
		</div></div></div></div>`;

  return html;
}

function blastCall(primerSeq, locationElement) {
  // call to the python script that runs blast
  $.ajax({
    dataType: "json",
    url: "./ajaxCalls/blastPrimers.py",
    data: {
      primer: primerSeq,
      genome: GENOME,
    },
    success: function (json) {
      numBlastHits = Object.keys(json).length;
      if (numBlastHits == 1) {
        locationElement.html(parseLocation(json));
        locationElement.css("background-color", "#dff0d8");
      } else if (numBlastHits == 0) {
        locationElement.html("No BLAST Hits");
        locationElement.css("background-color", "rgba(0,0,0,0.075)");
      } else {
        rowID = locationElement.parent().attr("id");
        primerModal = displayHitResults(json, rowID);
        locationElement.html(primerModal);
        locationElement.css("background-color", "#f8d7da");
      }
    },
    error: function (xhr, status, err) {
      console.log("Primer Blast program stopped before completing search for: " + primerSeq);
      locationElement.html(
        '<span style="font-size: 0.75rem;"><i class="fa fa-exclamation-triangle"></i><br>An error occured while getting BLAST results</span>',
      );
      locationElement.css("color", "#b90e1e");
    },
  });
}

function displayHitResults(hitsObject, rowID) {
  html =
    `<button type="button" class="btn btn-link no-padding" style="color: #b90e1e; text-decoration: underline;" data-toggle="modal" data-target="#` +
    rowID +
    `-hits-modal">
    		Multiple BLAST Hits
  		</button>
		<div class="modal fade" id="` +
    rowID +
    `-hits-modal">
		    <div class="modal-dialog modal-lg">
		      <div class="modal-content">
		  
			<div class="modal-header">
			  <h4 class="modal-title">BLAST Hits With > 83% Identity</h4>
			  <button type="button" class="close" data-dismiss="modal">&times;</button>
			</div>
			
			<div class="modal-body">
			` +
    String(displayBlastHits(hitsObject)) +
    `
			</div>
	
			<div class="modal-footer">
			  <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
			</div>
			
		      </div>
		    </div>
		  </div>`;

  return html;
}

function displayBlastHits(hitsObject) {
  tableHTML = '<p style="text-align: left;">Search Sequence: ' + String(hitsObject[0]["inputseq"]) + "</p>";
  tableHTML += `
	<table class="table table-bordered" id="blastHitsTable">
	<thead>
		<tr>
		<th class="centreCell" scope="col">Location</th>
		<th class="centreCell" scope="col">Match Sequence</th>
		<th class="centreCell" scope="col">E-Value</th>
		</tr>
	</thead>
	<tbody>
	`;
  for (var hit in hitsObject) {
    //var eval = hitsObject[hit]['evalue'];
    var loc = hitsObject[hit]["chromosome"] + ":" + hitsObject[hit]["start"] + "-" + hitsObject[hit]["end"];
    //var inputseq = hitsObject[hit]['inputseq'];
    //var matchseq = hitsObject[hit]['matchseq'];
    if (hitsObject[hit]["strand"] === "minus") {
      loc += "-";
    } else {
      loc += "+";
    }
    tableHTML += "<tr><td>" + loc + "</td>";
    //tableHTML += "<td>" + String(hitsObject[hit]['inputseq']) + "</td>";
    tableHTML += "<td>" + String(hitsObject[hit]["matchseq"]) + "</td>";
    tableHTML += "<td>" + String(hitsObject[hit]["evalue"]) + "</td></tr>";
  }
  tableHTML += "</tbody></table>";
  return tableHTML;
}

function parseLocation(hitObject) {
  var loc = hitObject["0"]["chromosome"] + ":" + hitObject["0"]["start"] + "-" + hitObject["0"]["end"];
  if (hitObject["0"]["strand"] === "minus") {
    loc += ":-";
  } else {
    loc += ":+";
  }
  return loc;
}

// thank you anonymous author at html-online.com/articles/get-url-parameters-javascript/
function getUrlVars(url = window.location.href) {
  var vars = {};
  var parts = url.replace(/[?&]+([^=&]+)=([^&]*)/gi, function (m, key, value) {
    vars[key] = value;
  });
  return vars;
}

//updates the download links below the Guide table
function updateGuideDownloadLinks() {
  // get the ids of the checked guides
  var ids = {};
  ids["gene"] = geneName;
  ids["genome"] = GENOME;
  count = 0;
  $.each($("#guideTable input:checked").closest("tr"), function () {
    ids[count] = $(this).attr("id");
    count = count + 1;
  });
  updateGuideAPE(ids);
  updateGuideCSV(ids);
  updateGuideDOC(ids);
}

function updateGuideAPE(ids) {
  $.ajax({
    type: "POST",
    dataType: "html",
    data: ids,
    url: "./ajaxCalls/generateAPE.py",
    success: function (html) {
      link = html.toString().trim();
      $("#DownloadGuideAPE").attr("href", link);
    },
    error: function (jqXHR, status, err, html) {
      console.log(err);
    },
  });
}

function updateGuideCSV(ids) {
  $.ajax({
    type: "POST",
    dataType: "html",
    data: ids,
    url: "./ajaxCalls/generateCSV.py",
    success: function (html) {
      link = html.toString().trim();
      $("#DownloadGuideCSV").attr("href", link);
    },
    error: function (jqXHR, status, err, html) {
      console.log(html);
    },
  });
}

function updateGuideDOC(ids) {
  //add the ensid for this one since it's needed to determine the primer locations
  ids["ENSID"] = ENSID;
  $.ajax({
    type: "POST",
    dataType: "html",
    data: ids,
    url: "./ajaxCalls/generateDOC.py",
    success: function (html) {
      link = html.toString().trim();
      $("#DownloadGuideDOC").attr("href", link);
    },
    error: function (jqXHR, status, err, html) {
      console.log(html);
    },
  });
}

//updates the download link for newly designed primers
function updateDownloadLink() {
  const wtPrimerRankIndex = parseInt($(".wtPrimerTable input:checked").parent().next().text()) - 1 || 0,
    emPrimerRankIndex = parseInt($(".emPrimerTable input:checked").parent().next().text()) - 1 || 0,
    oldAPELocation = $("#apeDownload").attr("href"),
    oldCSVLocation = $("#csvDownload").attr("href"),
    newAPELocation = `${oldAPELocation.slice(0, -7)}${wtPrimerRankIndex}_${emPrimerRankIndex}.ape`,
    newCSVLocation = `${oldCSVLocation.slice(0, -7)}${wtPrimerRankIndex}_${emPrimerRankIndex}.csv`;

  $("#apeDownload").attr("href", newAPELocation);
  $("#csvDownload").attr("href", newCSVLocation);
}

function getSelected() {
  var result = [null, null];
  // for every row in the results table
  $("#primerResultsTable tr").each(function () {
    // check if the first checkbox is checked
    if ($(this).find(":checkbox:first:checked").length > 0) {
      //check the id of the parent row
      ids = this.id.split("-");
      if (ids[0] == "WT") {
        // need to divide by 2 since two rows per pair
        result[0] = Math.floor(ids[1] / 2);
      } else if (ids[0] == "EM") {
        // if em store in second slot
        result[1] = Math.floor(ids[1] / 2);
      }
    }
  });

  return result;
}

function primerSelect() {
  $(".selectCheckbox-WT").click(function () {
    $(".selectCheckbox-WT").not(this).prop("checked", false);
    updateDownloadLink();
  });
  $(".selectCheckbox-EM").click(function () {
    $(".selectCheckbox-EM").not(this).prop("checked", false);
    updateDownloadLink();
  });
}
