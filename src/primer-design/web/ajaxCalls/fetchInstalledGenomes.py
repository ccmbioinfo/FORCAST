#!/usr/bin/python
'''
Hillary Elrick, May 10th
Fetch the genomes currently installed on the server and format them to be used as html select element options
'''

import sys
import os
import cgi

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../../../helpers'))
from Config import Config

def main():
	
	print ('Content-Type: text/html\n')
        try:
		arg = cgi.FieldStorage()
                genome = arg.getvalue("genome")
        except Exception as e:
                print("Incorrect information passed to script: " + str(e))
                return
	
	from Config import fetchInstalledGenomes
	result = fetchInstalledGenomes()
	# print in an html option list for a dropdown selector
	for option in result:
		org = option[0]
		name = option[1]
		print """<option value="{org}">{name}</option>""".format(**locals())

		
if __name__ == "__main__":
	main()
