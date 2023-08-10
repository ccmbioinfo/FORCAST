#!/usr/bin/python3.7

import cgi
import os
import sys

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../../helpers"))


def main():
    print("Content-Type: text/html\n")
    try:
        arg = cgi.FieldStorage()
        genome = arg.getvalue("genome")
    except Exception as e:
        print("Missing/incorrect information passed to script: " + str(e))
        return

    if genome:
        from Config import fetchCurrentRelease

        release = str(fetchCurrentRelease(genome))
        print(release)
    else:
        print("No genome passed to script")


if __name__ == "__main__":
    main()
