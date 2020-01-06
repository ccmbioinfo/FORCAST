#!/usr/bin/python
'''
Hillary Elrick October 10th, 2018

Importable class that defines standard methods and attributes
for database access and object storage
'''
import os
import sys
import re
import urllib
import cPickle as pickle
import pymongo
from pymongo import MongoClient


class Config:	
	def __init__(self, genome=None):	
		# get the credentials
		self.config = getCredentials()
		# the root directory is 2 levels up, get its dirname
		self.ROOT_PATH = (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
		# set all the paths defined in ROOT/config/paths.conf
		self.setPaths()	
		self.PRIMER3_SETTINGS = os.path.join(self.ROOT_PATH, 'config/primer3settings.conf')
		# where the primer3 in and output files are written
		self.PRIMER3_DIR = os.path.join(self.ROOT_PATH, 'src/primer-design/files/primer3Files')
			
		if genome:
			# connect to the mongoDB
			self.genome = genome	
			mongoDB, release, curr_geneCollection, guideCollection, primerCollection, metadataCollection = self.getAttributes()
			self.mongoDB = mongoDB
			self.release = release
			self.curr_geneCollection = curr_geneCollection
			self.guideCollection = guideCollection
			self.primerCollection = primerCollection
			self.metadataCollection = metadataCollection	
			self.organismName = self.getOrgName()


	def setPaths(self):
		f = open(os.path.join(self.ROOT_PATH, "config/paths.conf"))
		for line in f:
			if re.match(r"^BLAST_EXEC=", line):
				self.BLAST = line.split('=')[1].strip()
			elif re.match(r"^PRIMER3_EXEC=", line):
				self.PRIMER3 = line.split('=')[1].strip()
			elif re.match(r"^PRIMER3_CONFIG=", line):
				self.PRIMER3_CONFIG = line.split('=')[1].strip()
			elif re.match(r"DICEY_EXEC=", line):
				self.DICEY = line.split('=')[1].strip()
			elif re.match(r"DICEY_PATH=", line):
				self.DICEY_PATH = line.split('=')[1].strip()

		if not self.BLAST:
			print("Error: path to BLAST executable not defined in paths.conf")
		elif not self.PRIMER3:
			print("Error: path to primer3 executable not defined in paths.conf")
		elif not self.PRIMER3_CONFIG:
			print("Error: path to primer3 config directory not defined in paths.conf")
		elif not self.DICEY:
			print("Error: path to dicey executable not defined in paths.conf")
		elif not self.DICEY_PATH:
			print("Error: path to dicey program folder not defined in paths.conf")

		return
				

	def getAttributes(self):
		if self.config:
			# if credentials are set, connect to mongodb using them
			client = MongoClient('mongodb://%s:%s@localhost' % (self.config['username'], self.config['password']))
		else:
			# otherwise, attempt connecting without credentials
			client = MongoClient()
		
		db = client[self.genome]
		collections = db.collection_names()
		
		# get the release we're using from the most recent geneInfo collection
		curr_release = fetchCurrentRelease(self.genome, collections)

		# set variables for collection names
		nameGeneCol = "geneInfo_" + str(curr_release)
		nameGuideCol = "gRNAResultCollection"
		namePrimerCol = "primerCollection"
		metadataCol = "metadata"
				
		return db, curr_release, db[nameGeneCol], db[nameGuideCol], db[namePrimerCol], db[metadataCol]


	def getOrgName(self):
		orgName = ''	
		metadataRecords = self.metadataCollection.find({})
		if metadataRecords.count() == 1:
			for record in metadataRecords:	
				orgName = str(record['org_name'])	
		else:
			print("Error: metadata collection for " + str(self.genome) + " is misconfigured")
		
		return orgName
		

	@staticmethod		
	def fetchStrandofGene(ensid, genome):
		curr_geneCollection = getCurrentGeneCollection(genome)
		record = curr_geneCollection.find_one({'ENSID': ensid})
		if record:
			return record['strand']
		else:
			raise ValueError("ENSID:"+str(ensid)+" Does Not Exist in Current Gene Collection")


def getCredentials():
	config = {}
	try:
		config_file = open("/var/www/mongo.cred")
	except Exception, e:
		# this is ok it just means there are no credentials
		return
	for line in config_file:		
		var, value = line.rstrip().split("=")
		if var == "password":
			# passwords need to have special characters escaped
			config[var] = urllib.quote(value)
		else:
			config[var] = value
	
	return config		


def getCurrentGeneCollection(genome):
	# get credentials and connect to mongodb
	config = getCredentials()	
	if config:
		client = MongoClient('mongodb://%s:%s@localhost' % (config['username'], config['password']))
	else:
		# if no credentials defined
		client = MongoClient()
	
	db = client[genome]
	collections = db.collection_names()
	
	# get the release we're using from the most recent geneInfo collection
	curr_release = fetchCurrentRelease(genome, collections)

	# determine the collection name
	nameGeneCol = "geneInfo_" + str(curr_release)
	
	return db[nameGeneCol]


def fetchCurrentRelease(genome, collections=None):
	
	# optionally, if function calling already has list of connections, they can be passed
	# otherwise, connect to mongodb and get them
	if not collections:
		config = getCredentials()
		if config:
			client = MongoClient('mongodb://%s:%s@localhost' % (config['username'], config['password']))
		else:
			client = MongoClient()
		db = client[genome]
		collections = db.collection_names()

	# get the release we're using from the most recent geneInfo collection
	curr_release = -1
	for c in collections:
		if 'geneInfo' in c:
			cltn_release = c.split("_",1)[1]
			if int(cltn_release) > int(curr_release):
				curr_release = cltn_release
	
	return curr_release


def fetchInstalledGenomes():
	# get a list of the installed genomes in the mongodb
	config = getCredentials()
	if config:
		client = MongoClient('mongodb://%s:%s@localhost' % (config['username'], config['password']))
	else:
		client = MongoClient()

	genomes = []	
	dbs = sorted(client.database_names(), key=lambda v: v.upper())
	default_dbs = ['admin', 'local','config']
	for db in dbs:
		if db not in default_dbs:	
			metadataCollection = client[db]['metadata']
			metadataRecords = metadataCollection.find({})
			if metadataRecords.count() == 1:
				orgName = str(metadataCollection.find_one({})['org_name'])
				orgName = orgName.replace("_"," ").capitalize()
				genomes.append((db, orgName)) # store org code and name in list as tuple
			else:
				print("Error: metadata collection for " + str(db) + " is misconfigured")
	return genomes		


def main():
	print "A class for interfacing to the mongo database. Given a genome, connects to the correct database"
	print "and stores the database, release, current gene collection, guide collection, and primer collection."
	print "as attributes which other functions can access. Also stores the root path, i.e. where the web server"
	print "points to and the jbrowse and primer design scripts are located. If the mongodb is secured"
	print "with credentials, these are accessed from the mongo.cred file in var/www"
	print "Databases currently available:"
	genomes = fetchInstalledGenomes()
	for g in genomes:
		orgName = g[1]		
		genomeString = g[0] + " (" + orgName + ")"
		print genomeString
			
	
if __name__ == "__main__":
	main()
	
