#!/usr/bin/python3

"""
Hillary Elrick, September 9th, 2019

Class for getting user input to perform a guide search. Given URL variables, returns appropriate HTML page results.
Prints template for guide searching as well as AJAX calls to the GuideResults.py program which is displayed the 
results section of the HTML template.

Requires: initial searchLocation and genome

Optional parameters: guide length (default is 20), selected non-canon PAMs to consider as off-targets (if not default for RGEN)

Steps:
1) Gets the sequence within the search location (get_sequence.py)
2) Finds the gRNAs within the sequence (find_grna.py)
3) Finds and counts all the off-targets in the genome for each guide (find_offtargets.py)
4) Scores the off-targets and calculates an aggregate score for each guide (score_offtargets.py)
5) Categorizes each off-target into 'intergenic', 'intronic', and 'exonic'
6) Puts the results into a jinja2 template and prints the html
"""

import sys, os, cgi, binascii, re
from jinja2 import Template
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../primerDesign/python"))
from Config3 import Config

# cgi debug module
import cgitb
cgitb.enable()

class GuideSearch:
    def __init__(self, **kwargs):
        """ class for initializing the guide search page and updating it when inputs change """

        # validate action parameter
        if 'action' not in kwargs:
            self.sendErrorHTML("'action' not in URL parameters")
        elif kwargs['action'] not in ['initialize', 'update_input','get_lengths']:
            self.sendErrorHTML("Invalid action string sent: " + str(kwargs['action']))
        else:
            self.action = kwargs['action']
        
        if self.action in ['initialize', 'update_input']:
            # validate searchInput
            if 'searchInput' not in kwargs:
                self.sendErrorHTML("'searchInput' not in URL paramters")
            elif not isValidInput(kwargs['searchInput']):
                self.sendErrorHTML("'searchInput', "+str(kwargs['searchInput'])+" is not valid")
            else:
                self.searchInput = kwargs['searchInput']

            # validate genome
            if 'genome' not in kwargs:
                self.sendErrorHTML("'genome' not in URL parameters")
            else:
                # attempt connection to genome's db before storing
                self.dbConnection = Config(kwargs['genome'])
                self.genome = kwargs['genome']

            # get the length of the input seq and genes that overlap it
            self.regionLength = self.getRegionLength()
            self.overlappedGenes = self.getOverlappingGenes()

            # print correct HTML response
            if self.action == 'initialize':
                print(self.initialHTML())
            else:
                print(self.inputRowHTML())
        elif self.action == 'get_lengths':
            # action is to get the list of guide lengths allowed for selected rgen
            self.rgenID = kwargs['rgenID']
            self.dbConnection = Config() # genome agnostic
            try:
                # attempt to get the rgen record
                self.rgenRecord = self.getRGEN()
            except ValueError as e:
                self.sendErrorHTML("Invalid RGEN ID, " + str(self.rgenID))

            print(self.getLengthsHTML())


    def inputRowHTML(self):
        """ rebuild the form row for the input region and target gene and return it """
        template_values = {
            'search_location': self.getInputHTML(), 
            'available_genes': self.getOverlappingGenesHTML()    
        }
        template_path = os.path.join(self.dbConnection.ROOT_PATH, "GuideFinder/templates/input_region.html")
        region_template = Template(open(template_path, 'rb').read().decode('utf-8'))
        html_result = region_template.render(template_values)
        return html_result

    def initialHTML(self):
        template_values = {
            'search_location': self.getInputHTML(),
            'input_row': self.inputRowHTML(),
            'organism': self.getOrganismHTML(),
            'RGENS': self.getRgenHTML(),
            'guideLengths': self.getLengthsHTML(),
            'available_genes': self.getOverlappingGenesHTML()
        }
        template_path = os.path.join(self.dbConnection.ROOT_PATH, "GuideFinder/templates/select.html")
        initial_template = Template(open(template_path, 'rb').read().decode('utf-8'))
        html_result = initial_template.render(template_values)
        return html_result

    def sendErrorHTML(self, errorString):
        """ format exceptions in HTML to prevent page from crashing """ 
        if not hasattr(self, 'dbConnection'):
            self.dbConnection = Config()
        template_path = os.path.join(self.dbConnection.ROOT_PATH, "GuideFinder/templates/error.html")
        error_template = Template(open(template_path, 'rb').read().decode('utf-8'))
        html_result = error_template.render(errorString=errorString)
        print(html_result)
        sys.exit()
       
    def getOrganismHTML(self):
        """ convert underscored org database string to HTML with italicization """
        org = self.dbConnection.organismName
        org = org.replace("_"," ").capitalize()
        HTML = "<i>{org}</i> ({genome})".format(org=org, genome=self.genome)       
        return HTML
   
    def getOverlappingGenesHTML(self):
        """ Format the overlapped genes into a selection dropdown or text input if no overlap """
        
        # prevent displaying all genes overlapped in case of large input sequence
        if len(self.overlappedGenes) < 20 and len(self.overlappedGenes) > 0:
            HTML = "<select class='form-control' id='gene' required>"
            if len(self.overlappedGenes) == 1:
                HTML += "<option value='{gene}' selected='selected'>{gene}</option>".format(gene=self.overlappedGenes[0])
            else:
                HTML += "<option value selected='selected'></option>"
                for gene in self.overlappedGenes:
                    HTML += "<option value='{gene}'>{gene}</option>".format(gene=gene)
            
            HTML += "</select>" 
        else:
            HTML = "<input class='form-control' id='gene' type='text' required>"

        return HTML
       
    def getRgenHTML(self):
        """ returns the available rgens in a preformmatted HTML select tag """
        HTML = '<select class="form-control" id="RGENS" onchange="getProtospacerLengths()">'
        for rgen in self.dbConnection.rgenCollection.find().sort([("rgenID",1)]):
            HTML += '<option value="{rgenID}">{Shortform}</option>'.format_map(rgen)
        HTML += "</select>"
        
        return HTML

    def getLengthsHTML(self):
        """ given the current rgenID, return the allowable lengths"""
        if getattr(self,'rgenID',False):
            # if we have an rgen selected, get the min, max, and default
            minLength = self.rgenRecord['MinGuideLength']
            maxLength = self.rgenRecord['MaxGuideLength']
            default = self.rgenRecord['DefaultGuideLength'] if 'DefaultGuideLength' in self.rgenRecord else minLength
        else:
            # get the first rgen record
            rgen = next(self.dbConnection.rgenCollection.find().sort([("rgenID",1)]).limit(1))
            # may need to do a next() call here
            minLength = rgen['MinGuideLength']
            maxLength = rgen['MaxGuideLength']
            default = rgen['DefaultGuideLength'] if 'DefaultGuideLength' in rgen else minLength

        HTML = '<select class="form-control" id="protospacerLength">'
        for i in range(int(minLength),int(maxLength)+1):
            if str(i) == str(default):
                HTML+= '<option value="{i}" selected>{i} (Default)</option>'.format(i=str(i))
            else:
                HTML+= '<option value="{i}">{i}</option>'.format(i=str(i))

        HTML += "</select>"

        return HTML

    def getInputHTML(self):
        """ returns the current search location in HTML form input """

        HTML = "<label for='searchInput'>Input Region ({length}bp):</label>".format(length=self.getRegionLength())
        HTML += "<input type='text' class='form-control' required id='searchInput' onchange='updateInput()' onpaste='this.onchange();' value='{search}'>".format(search=self.searchInput)

        return HTML

    def getRegionLength(self):
        """ calculate and return the length of the input sequence """
        try:
            start, end = re.search(r"chr.+?:(\d+)\-(\d+)", self.searchInput).groups()
            length = abs(int(start)-int(end))
        except Exception as e:
            return "N/A"
        return length 

    def getOverlappingGenes(self):
        """ using Teja's query to find genes in the mongodb that overlap the search input """        
        try:
            chm, start, end = re.search(r"(chr.+?):(\d+)\-(\d+)", self.searchInput).groups()
        except Exception as e:
            return ["Invalid Input Sequence"]
        start = int(start)
        end = int(end)
        searchQuery = {
        '$or': [ 
            {'$and': [
                {'start':{'$gte':start}},
                {'start':{'$lte':end}},
                {'chr':chm}
            ]},
            {'$and': [
                {'start':{'$lte':start}},
                {'end':{'$gte':end}},
                {'chr':chm}
            ]}, 
            {'$and': [
                {'end':{'$gte':start}},
                {'end':{'$lte':end}},
                {'chr':chm}
            ]}
        ]}
        overlappedGenes = []
        for gene in self.dbConnection.curr_geneCollection.find(searchQuery, {'Name': 1}):
            overlappedGenes.append(gene['Name'])

        return overlappedGenes
    
    def getRGEN(self):
        # fetch the correct rgen record using the rgenID attribute
        rgenCollection = self.dbConnection.rgenCollection
        rgenRecord = rgenCollection.find({"rgenID": str(self.rgenID)})
        if rgenRecord.count() == 1:
                return rgenRecord.next()
        else:
                raise ValueError("Incorrect number of records returned from RGEN database for rgenID: " + str(rgenID))
                return
    
def isValidInput(inputSeq):
    #TODO: code this. some validation done on front end but not for the chr number/letter
    if len(inputSeq) == 0:
        return False
    return True

def main():
    if 'REQUEST_METHOD' in os.environ:
        # running from web
        print("Content-type: text/html\n")
        inputForm = cgi.FieldStorage()
        paramters = {}
        for arg in ['action', 'searchInput', 'genome', 'rgenID']:
            if inputForm.getvalue(arg) is not None:
                paramters[arg] = inputForm.getvalue(arg)
        GuideSearch(**paramters)

    else:
        print("running from command-line with pre-set parameters")
        parameters = {
            'action': 'initialize',
            'searchInput': 'chr4:20046057-20046185',
            'genome': 'mm10',
            'gene': 'Ggh',
            'rgenID': '1'
        }
        GuideSearch(**parameters)


if __name__ == "__main__":
    main()