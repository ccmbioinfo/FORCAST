#!/usr/bin/env python3.7

import cgi
import os.path
import sys

import requests

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../helpers"))
# cgi debug module
import cgitb

from classes.Gene import Gene, printError
from Config import Config

cgitb.enable()

server = "https://rest.ensembl.org"

"""
Written By Hillary Elrick August 30th, 2018
Updated September 17th, 2019 to allow for search by ENSID

Purpose of this script is to generate an APE file for a gene given it's gene symbol or ENSID.
If it's already been generated, a download link to the pre-exisiting file is provided.

HTML page is minimized so it can be called as a popup from FileMaker
"""

# path where the APE files are stored
APE_PATH = "files/apeFiles"


# print the opening tags for the html and title for page
def printHeader(geneSymbol):
    print("Content-type: text/html\r\n\r")
    print(
        f"""
		<html>
		<head>
			<title>{{geneSymbol}} - APE</title>
			<link rel="stylesheet" href="bootstrap-4.1.3/dist/css/bootstrap.min.css" as="style">
			<style>
			body {{text-align: center;}}
			a {{font-size: 14px;}}
			</style>
		</head>
		<body>
		</br>
		<h3>Fetching APE for {geneSymbol}</h3>"""
    )


def fetchGeneSymbol(ENSID):
    ext = "/lookup/id/" + str(ENSID)

    try:
        symbolRequest = requests.get(
            server + ext, headers={"Content-Type": "application/json"}, timeout=30
        )
    except requests.exceptions.Timeout:
        printError(f"The Ensembl Rest API is not responding ({server + ext})")
    except Exception:
        printError("Problem with Ensembl Rest API call")

    if not symbolRequest.ok:
        try:
            symbolRequest.raise_for_status()
        except Exception as e:
            printError(f"Problem fetching gene symbol from Ensembl: {e}")

    geneInfo = symbolRequest.json()

    try:
        symbol = geneInfo["display_name"]
    except Exception:
        printError(f"Problem parsing result from Ensembl for ENSID: {ENSID}")

    return symbol


def main():
    # gets the gene argument passed to the script
    args = cgi.FieldStorage()
    geneSymbol = args.getvalue("gene")
    ENSID = args.getvalue("ENSID")
    genome = args.getvalue("genome")
    if not genome:
        printError("No genome assembly provided")
    dbConnection = Config(genome)

    # if ENSID is provided, we always use it to infer the geneSymbol
    if ENSID:
        geneSymbol = fetchGeneSymbol(ENSID)

    if geneSymbol == None:
        printError("No gene symbol provided")

    # print beginning of html doc
    printHeader(geneSymbol)

    # check if the file's already been created in the APE directory for the current release

    # global RELEASE
    global APE_PATH

    filename = str(geneSymbol + "_" + dbConnection.release + ".ape")
    if os.path.isfile(os.path.join(APE_PATH, filename)):
        # provide a download to the cached file
        print(
            f"""<a href="{os.path.join(APE_PATH, genome, 'plain', filename)}" download>Download Cached {filename}</a>"""
        )
    else:
        # generate a gene object and write its ape
        try:
            if ENSID:
                geneObject = Gene(geneSymbol, genome, ENSID=ENSID)
            else:
                geneObject = Gene(geneSymbol, genome)

            geneObject.writeAPE(True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
