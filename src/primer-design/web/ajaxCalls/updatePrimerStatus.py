#!/usr/bin/env python3.7

"""
Hillary Elrick

Used by AJAX call in src/primer-design/web/js/loadingPage.js which is attached to the
primer design popup. When a user changes the status of a guide (either 'Accepted' or 'Rejected'),
this updates the record in the database and rewrites the Primer GFF.
"""
import cgi
import os
import sys

from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../../helpers"))
import MongoHandler
from Config import Config


def updateDB(recordID, genome, newStatus, dbConnection):
    # get the primer collection and update it
    primerCollection = dbConnection.primerCollection
    update_result = primerCollection.update_one(
        {"_id": ObjectId(recordID)}, {"$set": {"status": newStatus}}
    )

    if update_result.matched_count != 1:
        print("Problem Updating Record, Incorrect number of primer records matched")
    else:
        try:
            MongoHandler.writeGFF(genome)
            print("Successfully updated the record")
        except Exception as e:
            print(f"Problem writing gff file: {e}")


def main():
    arg = cgi.FieldStorage()
    print("Content-Type: text/html\n")

    try:
        recordID = arg.getvalue("record")
        status = arg.getvalue("newstatus")
        genome = arg.getvalue("genome")
    except Exception as e:
        print(f"Incorrect information passed to script: {e}")
        return

    if not recordID or not status or not genome:
        print("Required information not passed to script")
        return

    dbConnection = Config(genome)
    updateDB(recordID, genome, status, dbConnection)


if __name__ == "__main__":
    main()
