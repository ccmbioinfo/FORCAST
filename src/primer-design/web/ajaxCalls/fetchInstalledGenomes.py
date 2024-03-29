#!/usr/bin/env python3.7

"""
Hillary Elrick, May 10th
Fetch the genomes currently installed on the server and format them to be used as html select element options
"""

import cgi
import os
import sys

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))


def main():
    print("Content-Type: text/html\n")
    try:
        cgi.FieldStorage().getvalue("genome")
    except Exception as e:
        print(f"Incorrect information passed to script: {e}")
        return

    sys.path.append(os.path.join(dir_path, "../../../helpers"))
    from Config import fetchInstalledGenomes

    result = fetchInstalledGenomes()
    # print in an html option list for a dropdown selector
    for option in result:
        org = option[0]
        name = option[1]
        ensembl_version = option[2]
        print(
            f"""<option value="{org}">{name} ({org}, Ensembl release {ensembl_version})</option>"""
        )


if __name__ == "__main__":
    main()
