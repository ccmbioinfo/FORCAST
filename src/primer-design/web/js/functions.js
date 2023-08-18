function hideInitial() {
  var firstlink = document.getElementById("initialDownload");
  if ($("#apeDownload").length) {
    firstlink.style.display = "none";
  }
}

//updates the download link depending on which primers were chosen
function updateDownloadLink() {
  var values = new Array();
  $.each($("input:checked").closest("td").siblings("td"), function () {
    values.push($(this).text());
  });

  var oldLocation = $("#apeDownload").attr("href");
  newLocation = String(
    oldLocation.substring(0, oldLocation.length - 7) + String(values[0] - 1) + "_" + String(values[8] - 1) + ".ape",
  ).replace(/\s+/g, "");
  //newLocation = String(oldLocation.substring(0, oldLocation.length-7) + "2" + "_" + "1"  + ".ape")

  //alert(newLocation)
  $("#apeDownload").attr("href", newLocation);
  //alert(values[0] + " " + values[8])
  //alert("val---" + values.join(","));
}

window.onload = function () {
  //hideInitial(); //commented out for testing
  $(".selectCheckbox-WT").click(function () {
    $(".selectCheckbox-WT").not(this).prop("checked", false);
    updateDownloadLink();
  });
  $(".selectCheckbox-EM").click(function () {
    $(".selectCheckbox-EM").not(this).prop("checked", false);
    updateDownloadLink();
  });

  //$('input').click(updateDownloadLink());
};
