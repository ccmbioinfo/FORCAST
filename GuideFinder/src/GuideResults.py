#!/usr/bin/python3

"""
Hillary Elrick, September 16th, 2019

Class for searching and evaluating guides then formatting the results
Requires: input region, genome, rgen, and gene

Steps:
1) Gets the sequence within the search location (get_sequence.py)
2) Finds the gRNAs within the sequence (find_grna.py)
3) Finds and counts all the off-targets in the genome for each guide (find_offtargets.py)
4) Scores the off-targets and calculates an aggregate score for each guide (score_offtargets.py)
5) Categorizes each off-target into 'intergenic', 'intronic', and 'exonic'
6) Puts the results into a jinja2 template and prints the html

"""

import sys, os, cgi, binascii, re, csv, json, urllib.parse
from collections import OrderedDict
from jinja2 import Template
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../primerDesign/python"))
from Config3 import Config
import get_sequence, find_grna, find_offtargets, score_offtargets, categorize_offtargets

class GuideResults:
    def __init__(self, **kwargs):
        """ class for controlling the guide searching workflow and displaying results """
        # track whether web or cli
        self.cli = kwargs['command-line'] 
        if self.cli:
            self.output_file = kwargs['output']
        else:
            # for debugging:
            import cgitb
            cgitb.enable()

        # validate searchInput
        if 'searchInput' not in kwargs:
            self.sendErrorHTML("'searchInput' parameter not set")
        elif not isValidInput(kwargs['searchInput']):
            self.sendErrorHTML("'searchInput', "+str(kwargs['searchInput'])+" is not valid")
        else:
            self.searchInput = kwargs['searchInput']
       
        # validate genome
        if 'genome' not in kwargs:
            self.sendErrorHTML("'genome' parameter not set")
        else:
            # attempt connection to genome's db before storing
            self.dbConnection = Config(kwargs['genome'])
            self.genome = kwargs['genome']
       
        # check gene sent
        if 'gene' not in kwargs:
            self.sendErrorHTML("'gene' parameter not set")
        else:
            self.gene = kwargs['gene']
      
        # validate rgenID
        if 'rgenID' not in kwargs:
            self.sendErrorHTML("'rgenID' parameter not set")
        else:
            self.rgenID = kwargs['rgenID']
            try:
                self.rgenRecord = self.getRGEN()
            except ValueError as e:
                self.sendErrorHTML("Invalid RGEN ID, " + str(self.rgenID))

        # set optional parameters
        if 'guideLength' in kwargs:
            self.guideLength = kwargs['guideLength']
        if 'offtargetPAMS' in kwargs:
            self.offTargetPAMS = kwargs['offtargetPAMS']
        
        self.guideDict, self.batchID = self.performGuideSearch()
        self.scores = self.setScores()

        if len(self.guideDict.keys()) > 0:
            self.writeCsvFiles()
            self.writeJsonFile()
            if not self.cli:
                self.sendResultHTML()
            else:
                print("Completed.")
        else:
            if not self.cli:
                self.sendNoResultHTML()
            else:
                print("No guides found in input region")

    def setScores(self):
        scores = set({}) # make a set
        for key, guide in self.guideDict.items():
            # ensure that if any of the guides has a score it's displayed
            if 'MIT' in guide:
                scores.add('MIT')
            if 'CFD' in guide:
                scores.add('CFD')
            if len(scores) == 2:
                break
        return scores

    def renderTemplate(self, template_name, template_values):
        """ given the name of the template, goes to the templates folder, renders it, and returns the result """
        template_path = os.path.join(self.dbConnection.ROOT_PATH, "GuideFinder/templates/{template_name}".format(template_name=template_name))
        template = Template(open(template_path, "rb").read().decode("utf-8"))
        html_result = template.render(template_values)
        return html_result

    def guideTableHTML(self):
        """ format the guide dictionary into an HTML table """
        template_values = {
            'guides': self.guideDict,
            'table_heading': self.tableHeadingHTML(),
            'table_body': self.tableBodyHTML()
        }
        return self.renderTemplate('guide_table.html', template_values)

    def tableHeadingHTML(self):
        """ determine which info for the guides is available and display the headings for those """
       
        scoreHeading = ''
        scoreHeaders = '' 
        if len(self.scores) > 0:
            scoreHeading += "<th colspan='{num_scores}'>Scoring</th>".format(num_scores=len(self.scores))
            for score in self.scores:
                scoreHeaders += "<th>{score}</th>".format(score=score)

        template_values = {
            'score_heading': scoreHeading,
            'score_headers': scoreHeaders
        }

        return self.renderTemplate("table_heading.html", template_values)

    def tableBodyHTML(self):
        """ generate HTML row containing info for each potential guide """

        # generate OrderedDict
        if 'MIT' in self.scores:
            sortedIDs = sorted(self.guideDict.keys(), key=lambda x: (int(self.guideDict[x]['MIT'])), reverse=True)
        elif 'CFD' in self.scores:
            sortedIDs = sorted(self.guideDict.keys(), key=lambda x: (self.guideDict[x]['CFD']), reverse=True)
        else:
            # sort by weighted off-target counts
            sortedIDs = sorted(self.guideDict.keys(), key=lambda x: (self.guideDict[x]['Rank']))

        sortedGuides = OrderedDict((x, self.guideDict[x]) for x in sortedIDs)
        bodyHTML = "<tbody>"+self.tableRowsHTML(sortedGuides)+"</tbody>"
        
        return bodyHTML

    def tableRowsHTML(self, sortedGuides):
        """ for each guide, generate the HTML for its row """

        rowsHTML = ''

        for guideID, guide in sortedGuides.items():

            template_values = {
                'guideID': guideID,
                'guide': guide,
                'inDatabase': self.guideExistsInDatabase(guideID),
                'guideSeq': self.formatSequence(guide['guide_seq'],guide['pam_seq']),
                'guideLocation': self.calculateLocation(guide),
                'offtargetModal': self.offtargetHTML(guideID, guide),
                'rowPopover': self.rowPopoverHTML(guideID)
            }
            rowsHTML += self.renderTemplate("table_row.html", template_values)

        return rowsHTML
    
    def rowPopoverHTML(self, guideID):
        """ given a guideID fetch the label and notes if it's already in the database, give the option to add it otherwise """

        button_text, label, notes = self.fetchGuideFromDatabase(guideID)

        template_values = {
            'batch_guideID': str(self.batchID + "_" + guideID),
            'buttonText': button_text,
            'defaultLabel': urllib.parse.unquote(label),
            'defaultNotes': urllib.parse.unquote(notes)
        }
        return self.renderTemplate("row_popover.html", template_values)

    def fetchGuideFromDatabase(self, guideID):
        """ determine whether the given guide is in the database, return its label and notes, plus a descriptor of the available action """
        searchQuery = {
            "guideSeq": self.guideDict[guideID]['guide_seq'],
            "pamSeq": self.guideDict[guideID]['pam_seq'],
            "guideLocation": self.calculateLocation(self.guideDict[guideID]) 
        }
        if self.dbConnection.guideCollection.find(searchQuery).count() > 0:
            existingGuide = self.dbConnection.guideCollection.find_one(searchQuery, {"label": 1, "Notes": 1})
            return 'Update Guide', existingGuide['label'], existingGuide['Notes']
        else:
            return 'Add to Database', '', ''
    
    def guideExistsInDatabase(self, guideID):
        """ return true if the guide is already stored, false otherwise """
        searchQuery = {
            "guideSeq": self.guideDict[guideID]['guide_seq'],
            "pamSeq": self.guideDict[guideID]['pam_seq'],
            "guideLocation": self.calculateLocation(self.guideDict[guideID]) 
        }
        if self.dbConnection.guideCollection.find(searchQuery).count() > 0:
            return True
        else:
            return False

    def formatSequence(self, guide_seq, pam_seq):
        """ uses the rgen record to determine which order to display the pam and sequence in """
        if self.rgenRecord['PamLocation'] == 'downstream':
            return guide_seq + ", " + pam_seq
        elif self.rgenRecord['PamLocation'] == 'upstream':
            return pam_seq + ", " + guide_seq
        else:
            sendErrorHMTL("Unrecognized PAM Location for RGEN: " + str(self.rgenRecord['PamLocation']))
    
    def calculateLocation(self, guide):
        """ using the strand of the guide and the genomic start, format the location string """
        if guide['strand'] == '+':
            return guide['pam_chrom'] + ":" + str(guide['guide_genomic_start']) + "-" + str(int(guide['guide_genomic_start']+len(guide['guide_seq']))-1) + ":+"
        elif guide['strand'] == '-':
            return guide['pam_chrom'] + ":" + str(guide['guide_genomic_start']) + "-" + str(int(guide['guide_genomic_start']-len(guide['guide_seq']))+1) + ":-"
        else:
            sendErrorHTML("Unrecognized strand for guide: " + str(guide['strand']))
    
    def offtargetHTML(self, guideID, guide):
        """ creates the HTML for the off-target modal of a given guide """
        template_values = {
            'guideID': guideID,
            'guide': guide,
            'offtargetCounts': self.offtargetCountsHTML(guideID, guide),
            'offtargetModals': self.offtargetModalHTML(guideID, guide),
            'csvFile': os.path.join('../tempfiles', self.batchID+"_"+guideID+".csv"),
            'totalCount': str(sum(guide['offtarget_counts']))
        }
        return self.renderTemplate("offtarget_cell.html", template_values)
    
    def offtargetCountsHTML(self, guideID, guide):
        """ formats the links to the off-target modals """
        off_target_counts = "<div style='color: #2676ff; font-weight: bold'>"
        for num_mismatches, num_offtargets in enumerate(guide['offtarget_counts']):
            off_target_counts += "<button class='btn btn-link no-padding' data-toggle='modal' data-target='#{guideID}_{num_mismatches}'>{num_offtargets}</button>-".format(**locals())
        off_target_counts = off_target_counts[:-1] # remove trailing dash
        off_target_counts += "</div>"

        return off_target_counts

    def offtargetModalHTML(self, guideID, guide):
        """ format the modals for the off-targets """
        modalsHTML = ''
        for num_mismatches, num_offtargets in enumerate(guide['offtarget_counts']):
            template_values = {
                'guideID': guideID,
                'guide': guide,
                'mismatches': num_mismatches,
                'guideSeq': self.formatSequence(guide['guide_seq'], guide['pam_seq']),
                'offTargetBody': self.offtargetModalBodyHTML(guide, num_mismatches),
                'numOffTargets': len(self.subsetOffTargets(guide, num_mismatches))
            }
            modalsHTML += self.renderTemplate('offtarget_modal.html', template_values)

        return modalsHTML

    def subsetOffTargets(self, guide, num_mismatches):
        """ returns the list of off-targets with the given number of mismatches """
        offtarget_subset = list(filter(lambda x: int(countLower(x['seq'])) == int(num_mismatches), guide['offtargets']))
        return offtarget_subset

    def offtargetModalBodyHTML(self, guide, num_mismatches):
        """ format and print the table for the given number of off-targets"""
        # get only the off-targets with the selected number of mismatches
        offtarget_subset = self.subsetOffTargets(guide, num_mismatches)
        if len(offtarget_subset) > 0:
            num_offtargets = len(offtarget_subset)
            maxShown = 20
            standard_offtargets, none_in_seed = self.separateOffTargets(offtarget_subset)
            resultHTML = ''
            if len(none_in_seed) > 0:
                resultHTML += "<p class='tableTitle left'><b>{count}</b> With No Mismatches in Seed:</p>".format(count=len(none_in_seed))
                resultHTML += self.offTargetTableHTML(none_in_seed, maxShown)
                if len(standard_offtargets) > 0:
                    resultHTML += "<p class='tableTitle left'><b>{count}</b> With Mismatches in Seed:</p>".format(count=str(len(standard_offtargets)))
                    resultHTML += self.offTargetTableHTML(standard_offtargets, maxShown)
            else:
                resultHTML += "<p class='tableTitle left'><b>{count}</b> With Mismatches in Seed:</p>".format(count=str(len(standard_offtargets)))
                resultHTML += self.offTargetTableHTML(standard_offtargets, maxShown)

            return resultHTML
        else:
            return "<p>No Off-Targets with {mismatches} Mismatches</p>".format(mismatches=str(num_mismatches))
    
    def offTargetTableHTML(self, offtarget_list, maxShown):
        """ sorts, formats and returns a table of off-targets from the offtarget list provided """
        
        num_offtargets = len(offtarget_list)
        offtarget_list = offtarget_list[:maxShown]
        
        for offtarget in offtarget_list:
            offtarget.update({'formatted_seq': self.colourLowercaseRed(self.formatSequence(offtarget['seq'], offtarget['pam']))})
        # sort by score if available
        if 'MIT' in self.scores:
            offtarget_list = sorted(offtarget_list, key=lambda x: x['MIT'], reverse=True)
        elif 'CFD' in self.scores:
            offtarget_list = sorted(offtarget_list, key=lambda x: x['CFD'], reverse=True)

        total_count = ''
        if num_offtargets > maxShown:
            total_count = "<p>({max} of {total} shown)</p>".format(max=str(maxShown), total=str(num_offtargets))
      
        template_values = {
            'offtargetSubset': offtarget_list,
            'totalCount': total_count
        }

        return self.renderTemplate('offtarget_table.html', template_values)
 
    def separateOffTargets(self, off_target_subset):
        """ given a list of filtered off-targets, separate the regular ones from those that have no mismatches in the rgen's seed region """
        seedDirection = self.rgenRecord['SeedRegion'][0]
        seedLength = int(self.rgenRecord['SeedRegion'][1:])
        guideLength = len(off_target_subset[0]['seq'])
        standard_offtargets = []
        none_in_seed = []
        for offtarget in off_target_subset:
            if self.hasMismatchInSeed(offtarget['seq'], seedDirection, seedLength, guideLength):
                standard_offtargets.append(offtarget)
            else:
                none_in_seed.append(offtarget)

        return standard_offtargets, none_in_seed

    def hasMismatchInSeed(self, offtargetSeq, seedDirection, seedLength, guideLength):
        """ given an offtarget's guide sequence, returns true if there is a mismatch in the seed region of the rgen and false otherwise """
        if seedDirection == '+':
            for idx in range(0, seedLength):
                if offtargetSeq[idx].islower():
                    return True 
        elif seedDirection == '-':
            for idx in reversed(range(guideLength-seedLength,guideLength)):
                if offtargetSeq[idx].islower():
                    return True 

        return False

    def colourLowercaseRed(self, inputString):
        """ wraps the lowercase letters of a string in a span html tag that has a class to colour items within it red """
        result = ''
        for letter in inputString:
            if letter.islower():
                result += "<span class='green'>"+letter+"</span>"
            else:
                result += letter

        return result

    def sendResultHTML(self):
        """ take the results of the guide search and insert them into the result template"""
        template_values = {
            'guideTable': self.guideTableHTML(),
            'searchInput': self.searchInput,
            'rgen': self.rgenRecord,
            'gene': self.gene
        }
        print(self.renderTemplate("guide_results.html", template_values))
        return

    def sendNoResultHTML(self):
        """ if no guides are found in the input sequence, display message"""
        template_values = {
            'searchInput': self.searchInput,
            'rgen': self.rgenRecord
        }
        print(self.renderTemplate('no_results.html', template_values))
        return

    def sendErrorHTML(self, errorString):
        """ format exceptions in HTML to prevent page from crashing """ 
        if not hasattr(self, 'dbConnection'):
            self.dbConnection = Config()
        
        print(self.renderTemplate('error.html', {'errorString': str(errorString)}))
        sys.exit()

    def getRGEN(self):
        # fetch the correct rgen record using the rgenID attribute
        rgenCollection = self.dbConnection.rgenCollection
        rgenRecord = rgenCollection.find({"rgenID": str(self.rgenID)})
        if rgenRecord.count() == 1:
                return rgenRecord.next()
        else:
                raise ValueError("Incorrect number of records returned from RGEN database for rgenID: " + str(rgenID))
                return


    def writeCsvFiles(self):
        """ for each guide, write a csv file of its off-targets to the tempfiles directory """
        if self.cli:
            # if cli, put all guides into same csv
            total_offtargets_processed = 0
            with open(self.output_file, mode='w') as csv_file:
                writer = csv.writer(csv_file, delimiter=",")
                for guideID, guide in self.guideDict.items():
                    writer.writerow([str(guideID)+":"])
                    if guide['max_exceeded']:
                        writer.writerow(['Max off target sites exceeded ('+str(sum(guide['offtarget_counts']))+" shown)"])
                        total_offtargets_processed += 1000
                    else:
                        writer.writerow(['Total number of potential off-target sites:' + str(sum(guide['offtarget_counts']))])
                        total_offtargets_processed += sum(guide['offtarget_counts']) 
                    writer.writerow(['Off-target Counts: ' + "-".join(map(str,guide['offtarget_counts']))])
                    writer.writerow(['No mismatches in Seed: ' +  "-".join(map(str,guide['offtargets_seed']))])
                    if guide['MIT'] and not guide['max_exceeded']:
                        writer.writerow(['MIT Score: ' + str(guide['MIT'])])
                    if guide['CFD'] and not guide['max_exceeded']:
                        writer.writerow(['CFD Score: ' + str(guide['CFD'])])
                    writer.writerow(['Location', 'Sequence', 'Mismatches', 'Context'])
                    writer.writerow([self.calculateLocation(guide), self.formatSequence(guide['guide_seq'], guide['pam_seq']), '0', 'guide'])
                    for offtarget in guide['offtargets']:
                        row = [offtarget['loc']]
                        row.append(self.formatSequence(offtarget['seq'], offtarget['pam']))
                        row.append(countLower(offtarget['seq']))
                        row.append(offtarget['context'])
                        writer.writerow(row)
                    writer.writerow(['TOTAL PROCESSED: ', str(total_offtargets_processed)])
        else:    
            for guideID, guide in self.guideDict.items():            
                csv_path = os.path.join(self.dbConnection.ROOT_PATH,'GuideFinder/tempfiles', self.batchID+"_"+guideID+".csv")
                try:
                    with open(csv_path, mode='w') as csv_file:
                        writer = csv.writer(csv_file, delimiter=',')
                        # build and write heading row 
                        column_headings = ['chromosome', 'location', 'strand', 'protospacer sequence', 'PAM', 'mismatches', 'context']
                        if 'MIT' in self.scores:
                            column_headings.append('MIT')
                        if 'CFD' in self.scores:
                            column_headings.append('CFD')
                        column_headings.append('no mismatches in seed')
                        writer.writerow(column_headings)

                        # build and write guide row 
                        guide_row = [guide['pam_chrom']]
                        guide_row.append(self.calculateLocation(guide).split(":")[1])
                        guide_row.append(guide['strand'])
                        guide_row.append(guide['guide_seq'])
                        guide_row.append(guide['pam_seq'])
                        guide_row.append('0') # num mismatches
                        guide_row.append('guide') # context
                        if 'MIT' in self.scores:
                            guide_row.append(guide['MIT'])
                        if 'CFD' in self.scores:
                            guide_row.append(guide['CFD'])
                        guide_row.append('')
                        writer.writerow(guide_row)

                        # initialize variables for determining whether offtarget has mismatch in seed
                        seedDirection = self.rgenRecord['SeedRegion'][0]
                        seedLength = int(self.rgenRecord['SeedRegion'][1:])
                        # build and write row for each of the potential off target sites                        
                        for offtarget in guide['offtargets']:
                            offtarget_row = offtarget['loc'].split(':')
                            offtarget_row.append(offtarget['seq'])
                            offtarget_row.append(offtarget['pam'])
                            offtarget_row.append(str(sum(1 for base in offtarget['seq'] if base.islower()))) # num mismatches
                            offtarget_row.append(offtarget['context'])
                            if 'MIT' in self.scores:
                                offtarget_row.append(offtarget['MIT'])
                            if 'CFD' in self.scores:
                                offtarget_row.append(offtarget['CFD'])
                            if self.hasMismatchInSeed(offtarget['seq'], seedDirection, seedLength, len(guide['guide_seq'])):
                                offtarget_row.append('')
                            else:
                                offtarget_row.append('*')
                            writer.writerow(offtarget_row)
                except Exception as e:
                    self.sendErrorHTML(str(e))
        
    def getENSID(self):
        """ given the gene symbol, return the ENSEMBL ID from the stored gene collection """
        geneCollection = self.dbConnection.curr_geneCollection
        result = geneCollection.find({"Name": self.gene}) 
        if result.count() > 1:
            self.sendErrorHTML("More than one result in the database for gene symbol: " + self.gene)
        elif result.count() < 1:
            # TODO: need to deal with tracking regions of interest that aren't in a gene region
            # for now, just use a blank ensembl id
            return ''
        else:
            return result[0]['ENSID']

    def writeJsonFile(self):
        """ for each run, write a json file of the relevant guide info for adding guides to the database """
        # reformat the dictionary
        import copy
        databaseDict = copy.deepcopy(self.guideDict)
        for guideID, guide in databaseDict.items():
            guide['guideLocation'] = self.calculateLocation(guide)
        # add a metadata key
        databaseDict['metadata'] = {
            'genome' : self.genome,
            'gene': self.gene,
            'ENSID': self.getENSID(),
            'rgenID': self.rgenID,
            'inputSearchCoordinates': self.searchInput
        }
        with open(os.path.join(self.dbConnection.ROOT_PATH, 'GuideFinder/tempfiles', self.batchID+'.json'), 'w') as json_file:
            json.dump(databaseDict, json_file)

    def performGuideSearch(self):
        """ runs the backend modules """
        # TODO: look into a collision-free hashing function so don't have to re-run entire pipeline if inputs don't change
        batchID = binascii.b2a_hex(os.urandom(9)).decode('utf-8')

        genome_fa = os.path.join(self.dbConnection.ROOT_PATH,'jbrowse', 'data.'+self.genome,"downloads",self.genome+".fa")
        twoBitToFa_path = os.path.join(self.dbConnection.ROOT_PATH,'bin/twoBitToFa')
        genome_2bit = os.path.join(self.dbConnection.ROOT_PATH,'jbrowse', 'data.'+self.genome,"downloads",self.genome+'.2bit')
        tempfiles_path = os.path.join(self.dbConnection.ROOT_PATH,'GuideFinder/tempfiles')

        get_sequence.fetch_sequence(twoBitToFa_path, self.searchInput, genome_2bit, os.path.join(tempfiles_path,batchID+'_out.fa'))
        if self.cli: print("Determining guides in search region...")
        guideDict = find_grna.find_grna(self.rgenID, 0, os.path.join(tempfiles_path, batchID+'_out.fa'))
        if self.cli: print("Searching for potential off target sites...")
        guideDict = find_offtargets.findOffTargets(guideDict, self.rgenID, self.genome, batchID, genome_fa, tempfiles_path)
        if self.cli: print("Scoring potential off target sites and guides...")
        guideDict = score_offtargets.scoreOffTargets(guideDict, self.rgenID)
        if self.cli: print("Categorizing potential off target sites...")
        guideDict = categorize_offtargets.categorizeOffTargets(guideDict, self.rgenID, self.genome, batchID)

        return guideDict, batchID

def isValidInput(inputSeq):
    #TODO: code this. some validation done on front end but not for the chr number/letter
    if len(inputSeq) == 0:
        return False
    return True

def countLower(string):
    """ returns the number of lowercase letters in a string """
    count = 0
    for letter in string:
        if letter.islower():
            count+=1
    return count

def main():
    # check if running from web or command-line
    if 'REQUEST_METHOD' in os.environ:
        # running from web
        print("Content-type: text/html\n")
        inputForm = cgi.FieldStorage()
        parameters = {}
        for arg in ['searchInput', 'genome', 'gene', 'rgenID', 'guideLength', 'offtargetPAMs']:
            if inputForm.getvalue(arg) is not None:
                parameters[arg] = inputForm.getvalue(arg)

        parameters['command-line'] = False        
        GuideResults(**parameters)
    else:
        if len(sys.argv) != 6:
            print("Please provide the genome of interest, search input coordinates, gene, rgenID, and output file (.csv) in order")
            print("Optionally, provide the off-target PAMs to consider")
            sys.exit()
		
        parameters = {
            'genome': sys.argv[1],
            'searchInput': sys.argv[2],
            'gene': sys.argv[3],
            'rgenID': sys.argv[4],
            'output': sys.argv[5],
            'command-line': True
        }
        GuideResults(**parameters)

if __name__ == "__main__":
    main()
