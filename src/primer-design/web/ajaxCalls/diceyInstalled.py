#!/usr/bin/env python3.7

"""
Hillary Elrick February 13th, 2018

Defintes the functions for performing in silico PCR using the locally installed dicey program. Called when
designing primers to check the amplicons and binding sites of a pair of primers.
"""

import cgi
import os
import sys

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../../helpers"))
from Config import Config

sys.path.append(os.path.join(dir_path, "../.."))


def main():
    print("Content-type: application/html\n")

    try:
        # get the ajax values
        args = cgi.FieldStorage()
        # get genome variable
        genome = args.getvalue("genome")
    except Exception:
        sys.exit("Problem fetching genome variable passed to function")

    if not genome:
        print("Genome not passed to script")
        return

    dbConnection = Config(genome)
    if os.path.isfile(
        os.path.join(
            dbConnection.ROOT_PATH,
            "jbrowse",
            "data",
            genome,
            "processed",
            genome + ".fm9",
        )
    ):
        print("1")
    else:
        print("0")


if __name__ == "__main__":
    main()
