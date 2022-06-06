define([
    'dojo/_base/declare',
    'dojo/_base/array',
    'dojo/_base/lang',
    'JBrowse/View/FeatureGlyph/ProcessedTranscript',
    'JBrowse/Util'
],
function (
    declare,
    array,
    lang,
    ProcessedTranscript,
    Util
) {
    return declare(ProcessedTranscript, {
        _defaultConfig: function () {
            return Util.deepUpdate(this.inherited(arguments), {
                style: {
                    color: function (feat) {
                        if (feat.get('type') !== 'CDS') return 'black';
			// TEJA's Changes begin
			var ensembl_start_phase = Number(feat.get('ensembl_phase'));
			var ensembl_end_phase =  Number(feat.get('ensembl_end_phase'));
			var myColors = [ 

				['#f00000','#a00000','#500000'],
				['#00f000','#00a000','#005000'],
				['#0000f0','#0000a0','#000050']

			];
			var colors_1 = Array('#f4ce42','#f4ee41','#d9f441');
			var colors_2 = Array('#41f4ac','#41f4d9','#41c4f4');
			if(ensembl_start_phase == -1 && ensembl_end_phase!=-1){

				return colors_1[ensembl_end_phase];

			}
			else if(ensembl_start_phase != -1 && ensembl_end_phase == -1){

				return colors_2[ensembl_start_phase];
	
			}
			else if (ensembl_start_phase == -1 &&  ensembl_end_phase == -1){
		
				return 'black';

			}
			else{

				return myColors[ensembl_start_phase][ensembl_end_phase];
			}
                        //var phase = feat.get('phase');
                        //var start = feat.get('start');
                       // var end = feat.get('end');

                        //var frame = feat.get('strand') === 1 ? (start + phase) % 3 : (end - phase) % 3;
                        /*if (frame === 0) return 'lightblue';
                        else if (frame === 1) return 'pink';
                        else if (frame === 2) return 'lightgreen';*/
                        //return 'black';
			//TEJA's changes end
                    }
                }
            });
        }
    });
});
