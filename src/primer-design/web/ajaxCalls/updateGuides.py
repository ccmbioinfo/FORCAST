#!/usr/bin/python3.7

"""
Hillary Elrick

Used by AJAX call in /src/primer-design/web/js/loadingPage.js which is attached to the primer design popup.
When a user changes the status of a Guide, this script updates the database and rewrites the Guide GFF
"""

import cgi
import os
import sys

from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../../helpers"))
from Config import Config


def updateDB(genome, recordID, newStatus, dbConnection):
    guideCollection = dbConnection.guideCollection
    update_result = guideCollection.update_one(
        {"_id": ObjectId(recordID)}, {"$set": {"status": newStatus}}
    )

    if update_result.matched_count != 1:
        print("Problem Updating Record, Incorrect number of guide records matched")
    else:
        try:
            sys.path.insert(0, os.path.join(dbConnection.ROOT_PATH, "customPython/"))
            import MongoHandler

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
        print("Required parameters not passed to script")
        return

    try:
        dbConnection = Config(genome)
        updateDB(genome, recordID, status, dbConnection)
    except Exception as e:
        print(f"Error updating guide records: {e}")


if __name__ == "__main__":
    main()
