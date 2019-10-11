#!/usr/bin/python3

"""
Hillary Elrick, October 1st, 2019

Update Records from the previous version of CasCADe to match the new record format for the MongoDB
"""

import os, sys, json, cgi
from subprocess import Popen, PIPE, DEVNULL

dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../primerDesign/python"))
from Config3 import Config
from Config3 import fetchInstalledGenomes

def updateGuideRecords(org):
    """ add the rgen ID to all the records """
    dbConnection = Config(org)
    for guideRecord in dbConnection.guideCollection.find({}): #, {"$snapshot": True}):
        if 'pamSeq' not in guideRecord:
            print('wtf?')
            print(guideRecord)
        if len(guideRecord['pamSeq']) == 3:
            rgenID = "1"
        elif len(guideRecord['pamSeq']) == 4:
            rgenID = "3"
        else:
            sys.exit("Error: unrecognized PAM length ("+str(len(guideRecord['pamSeq'])+")"))

        dbConnection.guideCollection.update_one({"_id": guideRecord['_id']}, {"$set": {"rgenID": rgenID}}) 


def updateDbs():
    available_genomes = fetchInstalledGenomes()
    for genome in available_genomes:
        updateGuideRecords(genome[0])

def main():
    updateDbs()
    
if __name__ == "__main__":
    main()