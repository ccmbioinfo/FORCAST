#!/usr/bin/python3.5

"""
Hillary Elrick, September 24th, 2019

Class for adding or updating guides in the database
Requires: batch id, guideID, label, and notes

"""

import os, sys, json, cgi, git, datetime
from subprocess import Popen, PIPE, DEVNULL

dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../helpers"))
from Config3 import Config

# for debugging:
import cgitb
cgitb.enable()

class GuideAdd:
    def __init__(self, **kwargs):
        """ class for interfacing to the guide collection """
        # check required inputs set 
        for parameter in ['batchID', 'guideID', 'label']:
            if parameter not in kwargs:
                self.sendErrorHTML("'{parameter}' not set".format(**locals())) 
        self.dbConnection = Config()
        self.batchID = kwargs['batchID']
        self.guideID = kwargs['guideID']
        self.label = kwargs['label']
        self.notes = kwargs['notes'] if 'notes' in kwargs else ''
        
        # fetch the stored guide info
        self.metadata, self.guide = self.parseJSON()
        self.rgen = self.getRGEN(str(self.metadata['rgenID']))
        # redefine the connection to the database based on the genome
        self.dbConnection = Config(self.metadata['genome']) 
        # determine if the guide already exists
        self.existingGuide = self.existingGuideInDatabase()

        if self.existingGuide:
            # update the guide's notes and label
            self.updateGuide()
            self.rewriteGFF()
            print("Successfully Updated Guide")
        else:
            # insert the guide into the database 
            self.insertGuide()
            self.rewriteGFF()
            print("Successfully Inserted Guide")

    
    def rewriteGFF(self):
        """ rewrite the gff file """
        # intialize the strings
        featureStr = ''
        pamStr = ''
        grnaStr = ''
        idCounter = 1
        for guideRecord in self.dbConnection.guideCollection.find({}):
            # parse out location
            chrom, guideCoordinates, strand = guideRecord['guideLocation'].split(':')
            sortedGuideCoordinates = sorted([int(x) for x in guideCoordinates.split('-')])
            # calculate the pam coordinates
            rgen = self.getRGEN(guideRecord['rgenID'])
            pamLocation = rgen['PamLocation'] 
            if (pamLocation == 'downstream' and strand == '+') or (pamLocation == 'upstream' and strand == '-'):
                pamStart = sortedGuideCoordinates[-1]
                pamEnd = int(pamStart) + len(guideRecord['pamSeq'])
            elif (pamLocation == 'downstream' and strand == '-') or (pamLocation == 'upstream' and strand == '+'):
                pamEnd = sortedGuideCoordinates[0]
                pamStart = int(pamEnd) - len(guideRecord['pamSeq'])
            # sort all coordinates
            sortedCoordinates = list(sortedGuideCoordinates)
            sortedCoordinates.extend([pamStart, pamEnd])
            sortedCoordinates.sort()
            # format the entire feature GFF (guide+pam)
            score = guideRecord['guideScore'] if 'guideScore' in guideRecord else ''
            gffDict = {
                'featureID': idCounter,
                'featureName': self.combineSequence(rgen, guideRecord['guideSeq'], guideRecord['pamSeq']),
                'score': score,
                'otDesc': guideRecord['otDesc'],
                'batchName': guideRecord['batchName'] if 'batchName' in guideRecord else '',
                'ENSID': guideRecord['ENSID'] if 'ENSID' in guideRecord else '',
                'status': guideRecord['status'] if 'status' in guideRecord else '',
                'notes': guideRecord['Notes'] if 'Notes' in guideRecord else '',
                'label': guideRecord['label'] if 'label' in guideRecord else ''
            }
            featureCol9 = "ID={featureID};Name={featureName};guideScore={score};otDesc={otDesc};batchName={batchName};ENSID={ENSID};status={status};Notes={notes};label={label}".format(**gffDict)
            featureStr += "\t".join([chrom,'.','mRNA',str(sortedCoordinates[0]), str(sortedCoordinates[-1]),'.',strand,'.',featureCol9])
            featureStr += '\n'

            # now just the PAM feature
            pamID = chrom+":"+str(guideRecord['pamGenomicStart'])+"_"+guideRecord['pamSeq']
            pamCol9 = "ID={ID};Name={Name};Parent={Parent}".format(ID=pamID,Name=guideRecord['pamSeq'],Parent=idCounter)
            pamStr += "\t".join([chrom,'.','three_prime_UTR',str(pamStart),str(pamEnd),'.',strand,'-1', pamCol9])
            pamStr += '\n'

            # finally, the guide itself
            grnaID = chrom+":"+str(sortedGuideCoordinates[0])+"_"+guideRecord['guideSeq']
            grnaCol9 = "ID={ID};Name={Name};Parent={Parent}".format(ID=grnaID, Name=guideRecord['guideSeq'],Parent=idCounter)
            grnaStr += "\t".join([chrom,'.','CDS',str(sortedGuideCoordinates[0]), str(sortedGuideCoordinates[1]),'.',strand,'0',grnaCol9])
            grnaStr += '\n'

            # increment the count
            idCounter += 1
            
        #try:
        guideGFF = os.path.join(self.dbConnection.ROOT_PATH, str('jbrowse/data.'+self.metadata['genome']+"/gRNA_CRISPR.gff"))
        gffFile = open(guideGFF, 'wb')
        gffFile.write(featureStr.encode('utf-8'))
        gffFile.write(pamStr.encode('utf-8'))
        gffFile.write(grnaStr.encode('utf-8'))
        gffFile.close()
        #except Exception as e:
        #    self.sendErrorHTML(str(e))

            
    def getRGEN(self, rgenID):
        # fetch the correct rgen record using the rgenID attribute
        rgenCollection = self.dbConnection.rgenCollection
        rgenRecord = rgenCollection.find({"rgenID": rgenID})
        if rgenRecord.count() == 1:
                return rgenRecord.next()
        else:
            self.sendErrorHTML("Invalid number of records returned for rgenID: "+str(self.metadata['rgenID']))

    def combineSequence(self, rgen, guideSeq, pamSeq):
        """ uses the rgen record to determine which order to display the pam and sequence in """
        if rgen['PamLocation'] == 'downstream':
            return guideSeq.upper() + ", " + pamSeq
        elif rgen['PamLocation'] == 'upstream':
            return pamSeq.upper() + ", " + guideSeq.upper() 
        else:
            sendErrorHMTL("Unrecognized PAM Location for RGEN: " + str(self.rgen['PamLocation']))
    
    def insertGuide(self):
        """ create a new record in the database for the guide """

        # get the current git commit hash
        try:
            repo = git.Repo(search_parent_directories=True)
            git_hash = repo.head.object.hexsha
        except Exception as e:
            # don't prevent guide from being added
            git_hash = ''
        # build the dict
        newGuideRecord = {
            'batchName': self.metadata['gene'],
            'status': 'Accepted',
            'guideScore': self.guide['MIT'] if 'MIT' in self.guide else '', 
            'guideSeq': self.guide['guide_seq'],
            'Notes': self.notes,
            'inputSearchCoordinates': self.metadata['inputSearchCoordinates'],
            'pamGenomicStart': self.guide['pam_genomic_start'],
            'pamSeq': self.guide['pam_seq'],
            'guideGenomicStart': self.guide['guide_genomic_start'],
            'pamId': '', # this should probably be replaced by guideID
            'otDesc': '-'.join(str(count) for count in self.guide['offtarget_counts']),
            'label': self.label,
            'ENSID': self.metadata['ENSID'],
            'guideLocation': self.guide['guideLocation'],
            'rgenID': self.metadata['rgenID'],
            'commitHash': git_hash,
            'dateAdded': datetime.datetime.utcnow()
        }
        # TODO: think about how best to display the scores -> on primer end need to allow for possibility of no score
        # store the off-targets as well
        # probably should store the batch
        result = self.dbConnection.guideCollection.insert_one(newGuideRecord)
        if not result:
            self.sendErrorHTML("Problem inserting record into Database")
    
    def updateGuide(self):
        """ find the existing guide and update its notes and label"""
        existing_id = self.existingGuide['_id']
        update_result = self.dbConnection.guideCollection.update_one({"_id": existing_id}, {'$set': {'Notes': self.notes, 'label': self.label}})
        if update_result.matched_count != 1:
            self.sendErrorHTML("Problem Updating Guide Record")

    def existingGuideInDatabase(self):
        """ determine whether the given guide is in the database, return its label and notes, plus a descriptor of the available action """
        searchQuery = {
            "guideSeq": self.guide['guide_seq'],
            "pamSeq": self.guide['pam_seq'],
            "guideLocation": self.guide['guideLocation'] 
        }
        if self.dbConnection.guideCollection.find(searchQuery).count() > 0:
            existingGuide = self.dbConnection.guideCollection.find_one(searchQuery)
            return existingGuide
        else:
            return None

    def parseJSON(self):
        """ access the batch's json file, parse the metadata for the run as well as the details of the guide of interest """
        with open(os.path.join(self.dbConnection.ROOT_PATH, 'src/guide-finder/tempfiles', self.batchID+'.json'), 'r') as json_file:
            jsonData = json.load(json_file)

        if 'metadata' in jsonData:
            if self.guideID in jsonData:
                return jsonData['metadata'], jsonData[self.guideID]
            else:
                self.sendErrorHTML("Unable to find guide in batch JSON file")
        else:
            self.sendErrorHTML("Batch JSON file is misconfigured; no metadata found")

    def sendErrorHTML(self, errorString):
        """ write error and exit the program """ 
        print(errorString)
        sys.exit()


def main():
    # check if running from web or command-line
    if 'REQUEST_METHOD' in os.environ:
            # running from web
            print("Content-type: text/html\n")
            inputForm = cgi.FieldStorage()
            paramters = {}
            try:
                for arg in ['batchID', 'guideID', 'label', 'notes']:
                    if inputForm.getvalue(arg) is not None:
                        paramters[arg] = inputForm.getvalue(arg)

                GuideAdd(**paramters)
            except Exception as e:
                import traceback
                print(traceback.format_exc())
    else:
        #parameters = {'guideID': '92+', 'label': 'TestLabel', 'batchID': 'dda41408f7b56fcb3b', 'notes': 'nospecialcharacters'}
        #parameters = {'notes': "Le'sfjkd%20fsj#%20s", 'batchID': 'bfd5911343bde9a7cd', 'label': 'Testing%20Update', 'guideID': '6-'} 
        #{'label': 'testinglabel', 'guideID': '6-', 'notes': 'testing notes', 'batchID': '6aa1c0912c773384c7'}
        try:
            GuideAdd(**parameters)
        except Exception as e:
            print(str(e))

if __name__ == "__main__":
    main()
