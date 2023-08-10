#!/usr/bin/env python3.7

"""
Hillary Elrick

Fetch the current Ensembl release and report if there are problems with the API
"""

import requests


def getRelease():
    url = "https://rest.ensembl.org/info/data/?"

    try:
        releaseRequest = requests.get(
            url, headers={"Content-Type": "application/json"}, timeout=15
        )
    except requests.exceptions.Timeout:
        return "The Ensembl Rest API is not responding (https://rest.ensembl.org). Some functionality may be unavailable"

    if not releaseRequest.ok:
        releaseRequest.raise_for_status()
        return "Problem fetching information from Ensembl"

    release = releaseRequest.json()["releases"]

    # check if the release matches what is currently stored in Mongo
    if len(release) != 1:
        return f"Problem with call to Ensembl, multiple releases returned: {','.join(map(str, release))}"

    return str(release[0])


def main():
    print("Content-Type: text/html\n")
    print(getRelease())


if __name__ == "__main__":
    main()
