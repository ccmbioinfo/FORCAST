define( ["dojo/_base/declare", 'dojo/_base/array','dojo/_base/lang','dojo/aspect','dojo/on',"dojo/window", "dojo/dom-construct","JBrowse/View/Track/Sequence"],
   function(declare,array,lang,aspect,on,dojoWindow,dom,Sequence) {
   return declare(Sequence, {
       _trackMenuOptions: function() {
	  var visibleRegion = this.browser.view.visibleRegion();
	  var startCoord =  String(visibleRegion.start);
	  startCoord = startCoord.replace(/\.\d+$/,'');
	  var endCoord = String(visibleRegion.end);
	  endCoord = endCoord.replace(/\.\d+$/,'');
	  //var coordStr = visibleRegion.ref+":"+visibleRegion.start+"-"+visibleRegion.end;
	  var current_url = window.location.href;
	  var genome_regex = /data\=data%2F(.+?)\&/;
	  var genome_regex_matches = current_url.match(genome_regex);
	  var coordStr = "searchInput=" + visibleRegion.ref+":"+startCoord+"-"+endCoord;
	  //console.log(genome_regex_matches[1]);
	  if (genome_regex_matches!== null && genome_regex_matches[1].length >0){

	  	coordStr +="&genome="+genome_regex_matches[1];

	  }
          var opts=this.inherited(arguments); //call the parent classes function
           opts.push( // add an extra menu item to the array returned from parent class function
               {
                   label: "Search for Guides",
                   type: 'dijit/LinkPane',
                   onClick: function() {

			window.open(`${location.protocol}//${location.host}/src/guide-finder/GuideInitialize.py?action=initialize&${coordStr}`);

                   },
                   iconClass: "dijitIconPackage"
               }
           );
           return opts;
       }
   });
   }
);
