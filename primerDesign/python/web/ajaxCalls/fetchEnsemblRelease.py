#!/usr/bin/python

import requests

def getRelease():
	url = "https://rest.ensembl.org/info/data/?"
	
	try:
		releaseRequest = requests.get(url, headers={"Content-Type": "application/json"}, timeout=5)
	except requests.exceptions.Timeout:
		return "The Ensembl Rest API is not responding (https://rest.ensembl.org). Some functionality may be unavailable"
	
	if not releaseRequest.ok:
		releaseRequest.raise_for_status()
		return "Problem fetching information from Ensembl"
	
	release = releaseRequest.json()['releases']
	
	# check if the release matches what is currently stored in Mongo
	if len(release) != 1:
		return ("Problem with call to Ensembl, multiple releases returned: " + str(",".join(map(str, release))))

	return str(release[0])
		

def main():
	
	print ('Content-Type: text/html\n')
	print getRelease()
		
if __name__ == "__main__":
	main()
