#!/usr/bin/python

import sys
import cgi
sys.path.append('../..')
from Config import Config

def main():
	
	print ('Content-Type: text/html\n')
        try:
		arg = cgi.FieldStorage()
                genome = arg.getvalue("genome")
        except Exception as e:
                print("Incorrect information passed to script: " + str(e))
                return
	
	from Config import fetchCurrentRelease	
	release = str(fetchCurrentRelease(genome))
	print release
	
		
if __name__ == "__main__":
	main()
