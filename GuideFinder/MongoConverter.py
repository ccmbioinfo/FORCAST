#!/usr/bin/python3

"""
Hillary Elrick, October 1st, 2019

SCRIPT FOR MIGRATING FROM INITIAL BETA RELEASE OF CASCADE TO VERSION 1.0
"""

import os, sys, json, cgi
from subprocess import Popen, PIPE, DEVNULL

dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../primerDesign/python"))
from Config3 import Config
from Config3 import fetchInstalledGenomes

def updateGuideRecords(org):
    """ add the rgen ID to all the records """
    # NOTE: THIS PRESUMES THAT THE DEFAULT RGEN DATABASE IS BEING USED
    dbConnection = Config(org)
    for guideRecord in dbConnection.guideCollection.find({}): 
        if 'pamSeq' not in guideRecord:
            sys.exit("Error: invalid guide record " + str(guideRecord))
        if len(guideRecord['pamSeq']) == 3:
            if guideRecord['pamSeq'].endswith('GG'):
                rgenID = "1"
        elif len(guideRecord['pamSeq']) == 4:
            if guideRecord['pamSeq'].startswith('TTT'):
                rgenID = "2"
            elif guideRecord['pamSeq'].endswith('GT'):
                rgenID = "4"
        elif len(guideRecord['pamSeq']) == 6:
            regneID = "5"
        else:
            sys.exit("Error: unrecognized PAM ("+str(guideRecord['pamSeq'])+")")

        dbConnection.guideCollection.update_one({"_id": guideRecord['_id']}, {"$set": {"rgenID": rgenID}}) 


def updateDbs():
    available_genomes = fetchInstalledGenomes()
    for genome in available_genomes:
        updateGuideRecords(genome[0])

def main():
    updateDbs()
    
if __name__ == "__main__":
    main()