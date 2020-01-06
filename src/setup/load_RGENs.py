#!/user/bin/python3

"""
Hillary Elrick October 29th, 2019

Script to load or replace RGENs stored in the database to be used in designs by CasCADe.
Looks for the rgens.json file in the same directory as the script and requires the CLI of either 'update' or 'replace'.
Warning: replacing the RGEN database will unlink existing guides in the database from their RGENs
"""

script_desc = """This program will load the rgens from the 'rgens.json' file into the mongo database.
Please provide either 'update' or 'replace' as a command-line argument.
 update - modify attributes of existing rgens based on their rgenID and PAM, and add new RGENs
 replace - delete existing RGEN database and replace it with contents of 'rgens.json' file
N.B. When updating, ensure that the rgenID remains unchanged as this is used along with the PAM as a key for identifying RGENs to update.
WARNING: if the 'replace' option is selected, existing guides in the database will be unlinked from their RGENs ('update' is the recommended option).
If the RGEN database does not exist, a new one will be created regardless of the selected option."""

import sys
import os
import glob
import pymongo
from pymongo import MongoClient
import json
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../primerDesign/python"))
from Config3 import Config

def load_RGENs_into_Mongo(action):

    dbConnection = Config() # genome agnostic

    try:
        # load in the rgens.json file
        rgen_file = open('rgens.json', 'r')
    except Exception as e:
        print("Error opening rgens.json file: " + str(e))
        return False
    
    try:
        # read the json file
        rgenJSON = json.load(rgen_file)
    except Exception as e:
        print("Error parsing rgens.json file: " + str(e))
        return False

    if 'RGEN' not in dbConnection.client.list_database_names():
        # create database based on rgens.json file
        print("Building RGEN database from scratch")
        rgenDB = dbConnection.client['RGEN']
        try:
            with open(os.path.join(dir_path,'rgens.json')) as json_file:
                collection = rgenDB['rgenCollection']
                collection.insert(rgenJSON)
                return True
        except Exception as e:
            print("Error inserting RGENs into Mongo database: "+ str(e))
            return False
    else:
        # database already exists, perform user-specified action
        collection = dbConnection.rgenCollection             
        if action == 'replace':
            # delete existing records 
            delete_result = collection.delete_many({})
            print("Removed " + str(delete_result.deleted_count) + " documents from the rgenCollection")
            # replace with contents of rgens.json file
            insert_result = collection.insert_many(rgenJSON)
            num_inserted = len(insert_result.inserted_ids)
            print("Inserted " + str(num_inserted) + " new RGEN records")
            return True

        elif action == 'update':
            # update/insert records into the rgenCollection using the rgenID+PAM to determine which to update
            inserted_count = 0
            updated_count = 0
            for rgen in rgenJSON:
                match_criteria = {"rgenID": rgen['rgenID'], "PAM": rgen['PAM']}
                # remove match fields from update
                rgen.pop('rgenID', None)
                rgen.pop('PAM', None)
                result = collection.update_one(match_criteria, {"$set": rgen}, upsert=True)
                if result.upserted_id:
                    inserted_count += 1
                else:
                    updated_count += result.modified_count
            print(str(inserted_count) + " records inserted, " + str(updated_count) + " updated")
        
        else:
            # this is hypothetically unreachable...
            print("UNRECOGNIZED ACTION " + str(action))
            return False
   
    return True

def main():
    if len(sys.argv) != 2:
        print(script_desc)
    else:
        action = sys.argv[1]
        if action not in ['update', 'replace']:
            print("ERROR: Please provide either 'update' or 'replace' as an option")
            print(script_desc)
            sys.exit()
        
        success = load_RGENs_into_Mongo(action)
        if success:
            print("Successfully " + action + "d RGEN database")


if __name__=="__main__":
    main()
	
