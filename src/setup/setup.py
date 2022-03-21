#!/usr/bin/env python3

import argparse
import sys
import os
from fetch_and_setup_ensembl import *

def print_and_exit(msg):
	print(msg)
	sys.exit(1)

parser = argparse.ArgumentParser(description='This program will download the genome and gene annotation files from Ensembl for the user specified genome and an optional Ensembl annotation version. This program will then load the genome and setup various annotation tracks in JBrowse. This program will also load the gene definitions into MongoDB. Users can control the behavior of this program by passing appropriate command line flags.')

parser.add_argument('-r','--root-path', help="Full path to the root application folder )(eg: /var/www/html) (required)", required=True)
parser.add_argument('-g','--genome',help="Genome name (required). Example: rattus_norvegicus ",required=True)
parser.add_argument('-v','--genome-version',help="Genome version (required). Example: Rnor_6",required=True)
parser.add_argument('-fa2bit','--faToTwoBit-path', help="full path to faToTwoBit executable (required to create .2bit file", required=True)
parser.add_argument('-e','--ensembl-version',help="Ensembl version (optional). Example: 96",type=int)
parser.add_argument('-fa','--genome-file', help="full path to the downloaded genome fasta file (if downloaded to a non JBrowse data folder)")
parser.add_argument('-b','--blastdb-path', help="full path to the NCBI blast bin directory (required to create blast database)")

parser.add_argument('-u','--mongo-user', help="mongo username")
parser.add_argument('-p','--mongo-password', help="mongo password")
parser.add_argument('-d','--mongo-database',help="mongo database name")

parser.add_argument('-sd','--skip-download', help="skip data download from Ensembl", action="store_true",default=False)
parser.add_argument('-sp','--skip-download-processing', help="skip pre-JBrowse processing of fasta and gff files", action="store_true",default=False)

jbrowse_skip_group = parser.add_mutually_exclusive_group(required=False)
jbrowse_skip_group.add_argument('-sj','--skip-jbrowse-load',help="skip loading data into JBrowse",action="store_true",default=False)
jbrowse_skip_group.add_argument('-sg','--skip-jbrowse-load-genome',help="skip loading genome into JBrowse (if only annotation track updates are needed)",action="store_true",default=False)

parser.add_argument('-sm','--skip-mongo-load', help="skip loading gene information into MongoDB",action="store_true",default=False)


parser.add_argument('-sb','--skip-blastdb', help="skip setting up blast database ",action="store_true",default=False)

args = parser.parse_args()

#get the latest ensembl version if --enseml-version argument is not set
ENSEMBL_VERSION = args.ensembl_version if args.ensembl_version is not None else get_latest_ensembl_version()

if int(ENSEMBL_VERSION) == -1 :
	print_and_exit("Cannot fetch Ensembl version. Exiting")

#JBrowse data directory is always data/<genome_version>
if os.path.exists(args.root_path) is False:
    print_and_exit("Error! "+ args.root_path +" is an invalid path!")

jbrowse_path = os.path.join(args.root_path,"jbrowse")
jbrowse_data_directory = os.path.join(jbrowse_path, f"data/{args.genome_version}")
jbrowse_download_directory = os.path.join(jbrowse_data_directory, "downloads")

#create jbrowse data and download directories
if os.path.exists(jbrowse_data_directory) is False :  #check to make sure that the data is already not loaded into this folder. may be check for jbrowse json data folder
    try:
        os.mkdir(jbrowse_data_directory)
        os.chmod(jbrowse_data_directory,0o777)
    except Exception as err:
        print_and_exit(err)
else:
    print("Directory "+ jbrowse_data_directory +" already exists. Skipping creation")
    os.chmod(jbrowse_data_directory,0o777)

if os.path.exists(jbrowse_download_directory) is False:
    try:
        os.mkdir(jbrowse_download_directory)
        os.chmod(jbrowse_download_directory,0o777)
    except Exception as err:
        print_and_exit(err)
else:
    print("Directory "+ jbrowse_download_directory +" already exists. Skipping creation")
    os.chmod(jbrowse_download_directory,0o777)

data_exists = False
# skip when flag set or genome files already downloaded
if args.skip_download:
    print("--skip-download flag is specified on command line. Skipping download from Ensembl")
elif os.listdir(jbrowse_download_directory):
    data_exists = True
    print("download directory already populated. Skipping download from Ensembl")
else:
    # download files from Ensembl
    return_value = download_files_from_ensembl(jbrowse_path, jbrowse_data_directory, jbrowse_download_directory, args.genome_file, args.genome.lower(), ENSEMBL_VERSION)
    if return_value is not True:
        print_and_exit("Downloading files from Ensembl failed with error: "+ str(return_value))

if args.genome_file:
    print("Copying user specified genome file to " + jbrowse_data_directory)
    return_value  = copy_user_files(args.genome_file, jbrowse_download_directory)
    if return_value is not True:
        print("Copying user specified genome file failed with error" + str(return_value))
    else:
        print("Copying complete")

if args.skip_download_processing:
    print("--skip-download-processing flag is specified on command line. Skipping pre-JBrowse processing.")
elif data_exists:
    print("Skipping processing of data from Ensembl")
else:
    # process downloaded files
    print("Processing downloaded files")
    return_value = process_files_for_upload(args.root_path, jbrowse_download_directory, args.genome_version, args.faToTwoBit_path)
    if return_value is not True:
        print_and_exit("Processing downloaded files failed with error: "+ str(return_value))

if args.skip_jbrowse_load:
    print("--skip-jbrowse-load flag is specified on command line. Skipping loading data into JBrowse.")
elif os.path.exists(os.path.join(jbrowse_data_directory, "gRNA_CRISPR.gff")) and os.path.exists(os.path.join(jbrowse_data_directory, "acceptedPrimers.gff")):
    print("GFF files for genome exist. Skipping loading data into JBrowse")
else:
    # process data & load into JBrowse.
    if args.skip_jbrowse_load_genome is False:
        return_value = load_genome_into_JBrowse(jbrowse_path, jbrowse_data_directory, jbrowse_download_directory)
        if return_value is not True:
            print_and_exit("Loading genome into JBrowse failed with error:" + str(return_value))
        print("Sucessfully loaded genome into JBrowse")
    else:
        print("--skip-jbrowse-load-genome flag is specified on command line. Skipping loading genome into JBrowse.")
    return_value = load_gff_into_JBrowse(args.root_path, jbrowse_path, jbrowse_data_directory, jbrowse_download_directory, args.genome, args.genome_version)
    if not return_value:
        print_and_exit("Loading annotations into JBrowse failed with error:" + str(return_value))
    print("Sucessfully loaded annotations  into JBrowse")

print("JBrowse data directory for this genome is at " + jbrowse_data_directory)

if args.skip_mongo_load:
    print("--skip-mongo-load flag is specified on command line. Skipping loading data into mongodb")
else:
    print("Loading gene annotations and RGENs into Mongo database")
    # insert gene information into Mongo (will skip if already exists)
    return_value = load_geneinfo_RGENs_into_Mongo(jbrowse_download_directory, args.mongo_user, args.mongo_password, args.mongo_database, ENSEMBL_VERSION, args.genome, args.genome_version)
    if not return_value:
        print("Data insertion into Mongo failed with error "+ str(return_value))

blastdb_directory = os.path.join(jbrowse_data_directory,"blastdb")
if args.skip_blastdb:
    print("--skip-blastdb flag is specified on command line. Skipping creating BLAST database")
elif os.path.exists(blastdb_directory) and os.listdir(blastdb_directory):
    print("BLAST database already exists, Skipping creation.")
else:
    if not os.path.exists(blastdb_directory):
        os.mkdir(blastdb_directory)
        os.chmod(blastdb_directory,0o777)
    print("creating BLAST database")
    if args.blastdb_path is None:
        print_and_exit("path to blast bin folder not specified! Exiting")
    return_value = create_blastdb(jbrowse_download_directory, blastdb_directory, args.genome_version, args.blastdb_path)
    if return_value is True:
        print("Succesfully created blast database at " + blastdb_directory)
    else:
        print("Creating blast database failed with error "+ str(return_value))
