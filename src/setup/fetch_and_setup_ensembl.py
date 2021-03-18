import requests
import sys
import ftplib
from ftplib import FTP
import os
import glob
import subprocess
import re
import pprint
import pymongo
from pymongo import MongoClient
from urllib.parse import quote_plus
import json

dir_path = os.path.dirname(os.path.abspath(__file__))

ENSEMBL_FTP = "ftp.ensembl.org"

def get_latest_ensembl_version():

    '''This function fetches the latest Emsembl annoatation version via Ensembl API'''
    
    print("Fetching latest Ensembl version....")
    ensembl_url = "https://rest.ensembl.org/info/data/?"
    success = 1
    try:
        releaseRequest = requests.get(ensembl_url, headers={"Content-Type": "application/json"}, timeout=5)
    except requests.exceptions.Timeout:
        print("The Ensembl Rest API is not responding (https://rest.ensembl.org). Some functionality may be unavailable")
        return str(-1)
	
    if not releaseRequest.ok:
        releaseRequest.raise_for_status()
        print("Problem fetching information from Ensembl")
        return str(-1)

    release = releaseRequest.json()['releases']
    # check if the release matches what is currently stored in Mongo
    if len(release) != 1:
        print ("Problem with call to Ensembl, multiple releases returned: " + str(",".join(map(str, release))))
        return str(-1)

    return str(release[0])

def check_crcsum(sumfile, file_to_check):

    '''This function checks the crcsum of the file file_to_check'''
    downloaded_crc_sum_list = subprocess.check_output(["sum",file_to_check]).decode("utf-8").strip().split(" ")
    ensembl_crc_sum_list = subprocess.check_output(["grep",os.path.basename(file_to_check),sumfile]).decode("utf-8").strip().split(" ")
    if downloaded_crc_sum_list[0] == ensembl_crc_sum_list[0] and downloaded_crc_sum_list[1] == ensembl_crc_sum_list[1] :
        return True
    return False

def check_md5sum(sumfile,file_to_check):
    
    '''This function checks the md5sum of the file file_to_check'''
    download_file_md5sum = subprocess.check_output(["md5sum",file_to_check]).decode("utf-8").strip().split(" ")
    ensemble_md5sum = subprocess.check_output(["grep",os.path.basename(file_to_check),sumfile]).decode("utf-8").strip().split(" ")
    if download_file_md5sum[0] == ensemble_md5sum[0] :
        return True
    return False

def download_and_check(ftp_handle,ftp_directory,checksum_file,file_type,file_suffix,glob_suffix,jbrowse_download_directory,checksum_func):
    
    ''' This function performs tha actual download of fa, gff files from Ensembl and performs checksums on them '''
    ftp_handle.cwd(ftp_directory)
    for file_name in ftp_handle.nlst():
        if "CHECKSUMS" in file_name:
            print("Downloading " + file_type + " checksum file into directory" + jbrowse_download_directory)
            ftp_handle.retrbinary("RETR " + file_name, open(os.path.join(jbrowse_download_directory,checksum_file),"wb").write)

        if file_suffix in file_name:
            #if file already exists, calculate and compare checksum to make sure the downloaded file is complete
            file_exists = glob.glob(os.path.join(jbrowse_download_directory,glob_suffix))
            if len(file_exists) == 1:
                print(file_type + " file exists in  " + jbrowse_download_directory + " directory. Checking checksum to make sure that the file is downloaded properly")
                if checksum_func(os.path.join(jbrowse_download_directory, checksum_file), file_exists[0]) == True:
                    print(file_type + " checksum  check complete. Skipping download.")
                    return True
                else:
                    #checksums dont match
                    print(file_type + "checksum check failed. Removing and re-downloading the file.")
                    os.remove(file_exists[0])
            print("Downloading file " + file_name + " into directory " + jbrowse_download_directory)
            ftp_handle.retrbinary("RETR " + file_name, open(os.path.join(jbrowse_download_directory,file_name),"wb").write)
            if checksum_func(os.path.join(jbrowse_download_directory,checksum_file), os.path.join(jbrowse_download_directory,file_name)) == True:
                return True
            else:
                return False
    return False

def copy_user_files(genome_file_path,jbrowse_download_directory):
    
    if os.path.isfile(genome_file_path):
        (user_genome_directory,user_genome_file) = os.path.split(genome_file_path)
        if user_genome_file.endswith('.fa.gz') is False:
            print(genome_file +" must end with .fa.gz ")
        if user_genome_directory != jbrowse_download_directory:
            print("copying " + genome_file_path + " to " + jbrowse_download_directory)
            try:
                subprocess.run(['cp',genome_file_path,jbrowse_download_directory+"/"])
            except Exception as err:
                return(err)
        else:
            return (genome_file + " isnt a valid fasta file.")
    return True

def download_files_from_ensembl(jbrowse_path, jbrowse_data_directory, jbrowse_download_directory, genome_file_path, genome, ensembl_version):

    ''' This function coordinates downloading required files from Ensembl to load into JBrowse and MongoDB in later steps'''
    try:
        with FTP(ENSEMBL_FTP) as ens_ftp:
            ens_ftp.login() and print("Connected to Ensembl ftp directory")

            ftp_genome_directory = os.path.join("pub","release-"+str(ensembl_version), "fasta", genome, "dna")

            if genome_file_path is None:
                # download chromosome files for genome from Ensembl 
                try:
                    ens_ftp.cwd(ftp_genome_directory)
                except ftplib.error_perm:
                    raise Exception("Unable to locate genome files for "+str(genome)+ ". Please ensure "+str(ftp_genome_directory)+" exists and is reachable")

                chr_files = [file_name for file_name in ens_ftp.nlst() if '.dna.chromosome' in file_name]
                ens_ftp.cwd("../../../../../")
                
                for chr_file in chr_files:
                    if download_and_check(ens_ftp,os.path.join("pub","release-"+str(ensembl_version), "fasta", genome, "dna"),"crcsum.fa.txt","Genome fasta file",chr_file,chr_file,jbrowse_download_directory,check_crcsum) == True: 
                        print(chr_file+" successfully downloaded.")
                        ens_ftp.cwd("../../../../../")
                    else:
                        raise Exception("Error downloading "+ chr_file+". Please retry.")
                
                try:
                    chr_file_string = " ".join([os.path.join(jbrowse_download_directory,file_name) for file_name in chr_files])
                    subprocess.run("cat " + chr_file_string+ ">"+os.path.join(jbrowse_download_directory,genome+"."+ensembl_version+"."+"full_genome"+".fa.gz"), shell=True, check=True)
                except:
                    raise Exception("Error creating full_genome.fa.gz file. Aborting")
                
                if os.path.exists(os.path.join(jbrowse_download_directory,genome+"."+ensembl_version+"."+"full_genome"+".fa.gz")):
                    print("full genome file created successfully! Removing chromosome fasta files")
                    subprocess.run("rm "+chr_file_string,shell=True)
                else:
                    raise Exception("Error downloading Genome file. Please retry.")
            
            try:
                ens_ftp.cwd(ftp_genome_directory)
            except ftplib.error_perm:
                raise Exception("Unable to locate genome files for "+str(genome)+ ". Please ensure "+str(ftp_genome_directory)+" exists and is reachable")
            
            # download gff file for gene annotations.
            if download_and_check(ens_ftp,os.path.join("../../../gff3", genome),"crcsum.gff3.txt","Annotation gff file",ensembl_version + ".gff3.gz","*." + ensembl_version + ".gff3.gz",jbrowse_download_directory,check_crcsum) == True:
                print("Annotation gff file successfully downloaded.")
            else:
                raise Exception("Error downloading annotation gff3 file. Please retry.")
            
            if genome.lower() == 'mus_musculus' or genome.lower() == 'homo_sapiens':
                #mus_musculus and homo_sapiens have separate files for regulatory regions in Ensembl.
                if download_and_check(ens_ftp,os.path.join("../../regulation", genome),"md5sum.regulatory.gff.txt","Regulatory regions gff file",".gff.gz","*Regulatory*gff.gz",jbrowse_download_directory,check_md5sum) == True:
                    print("Regulatory regions gff file successfully downloaded.")
                else:
                    raise Exception("Error downloading regulatory regions gff file. Please retry.")
    except Exception as err:
        return(err)

    return True


def process_fasta_file(filename, genome_version, faToTwoBit_path):
    
    '''This function adds "chr" to the genome fasta file and removes text after the first space in the header'''
    (fileprefix,ext) = os.path.splitext(filename)
    output_file = fileprefix + ".processed" + ext
    short_genome_name = os.path.join(os.path.dirname(filename),genome_version)+".fa"
    two_bit_file = os.path.join(os.path.dirname(filename),genome_version)+".2bit"
    print("Processing file " + filename)
    with open(filename,"r") as inp_fh, open(output_file,"w") as out_fh :
        for line in inp_fh:
            if line.startswith('>'): 
                tmpList = line.split(" ") #disregard any text in header after a white space.
                if 'chr' in tmpList[0].lower():
                    out_fh.write(tmpList[0]+"\n") 
                else:
                    out_fh.write(tmpList[0][0] + "chr" + tmpList[0][1:]+"\n") # ">"+ chr + chromosome number
            else:
                out_fh.write(line)
    
    if not os.path.exists(short_genome_name+".bwt"):
        print("Generating bwa index files")
        subprocess.run(["ln", "-fs", output_file, short_genome_name])
        subprocess.run(["bwa", "index", short_genome_name])
        if not os.path.exists(short_genome_name+".bwt"):
            print("Cannot create bwt file")
            return False
    if not os.path.exists(two_bit_file):
        print("Generating 2bit file")
        subprocess.run([faToTwoBit_path, short_genome_name, two_bit_file])
        if not os.path.exists(two_bit_file):
            print("cannot create genome 2bit file")
            return False
    if not os.path.exists(short_genome_name+".fai"):
        print("Generating .fai file")
        subprocess.run(["samtools","faidx",short_genome_name])
        if not os.path.exists(short_genome_name+".fai"):
            print("Cannot create genome fai file")
            return False
        
    print("Processing complete!")

def process_gff_file(filename):

    ''' This function adds "chr" to the chromosome column and also copies the ensembl phase information from exon lines to CDS lines for JBrowse load '''
    (fileprefix,ext) = os.path.splitext(filename)
    output_file = fileprefix + ".processed" + ext
    print("Processing file" + filename)
    exon_dict = {}
    with open(filename,"r") as inp_fh: #slurp file first
        for line in inp_fh:
            field_list = line.split("\t") 
            if len(field_list) == 9 and field_list[2] == 'exon':
                transcript_match = re.search("transcript:(.+?);",field_list[8]) 
                if transcript_match is not None and len(transcript_match.groups()) == 1:
                    if transcript_match.group(1) not in exon_dict:
                        exon_dict[transcript_match.group(1)] = {}
                    if field_list[3] not in exon_dict[transcript_match.group(1)]:
                        exon_dict[transcript_match.group(1)][field_list[3]] = {}
                    if field_list[4] not in exon_dict[transcript_match.group(1)][field_list[3]]:
                        exon_dict[transcript_match.group(1)][field_list[3]][field_list[4]] = {}
                 
                ensembl_end_phase = re.search("ensembl_end_phase=(.+?);",field_list[8])
                if ensembl_end_phase is not None and len(ensembl_end_phase.groups()) == 1 :
                    exon_dict[transcript_match.group(1)][field_list[3]][field_list[4]]['ensembl_end_phase'] = ensembl_end_phase.group(0)
                
                ensembl_phase = re.search("ensembl_phase=(.+?);",field_list[8])
                if ensembl_phase is not None and len(ensembl_phase.groups()) == 1 :
                    exon_dict[transcript_match.group(1)][field_list[3]][field_list[4]]['ensembl_phase'] = ensembl_phase.group(0)
    
    with open(filename,"r") as inp_fh, open(output_file,"w") as out_fh:
        #now process the file
        for line in inp_fh:
            field_list = line.split("\t")
            if len(field_list) == 9:
            #if this line is not a header line
                if field_list[0].lower().startswith('chr') is False:
                    # add chr to the first field if it doesnt start with a chr
                    field_list[0] = "chr" + field_list[0]
                if field_list[2] == 'CDS':
                    # if the line is CDS, add the ensembl end phase and start phase to the line by matching it to the exon_dict dictionary
                    transcript_match = re.search("transcript:(.+?);",field_list[8])
                    if transcript_match is not None and len(transcript_match.groups()) == 1:
                        if transcript_match.group(1) in exon_dict:
                            #loop over the exon entries in the exon_dict for this transcript:
                            for start_pos in exon_dict[transcript_match.group(1)].keys():
                                for end_pos in exon_dict[transcript_match.group(1)][start_pos].keys():
                                    # if exon start or end position is the same as this CDS or if the exon completely includes the CDS:
                                    if int(start_pos) == int(field_list[3]) or int(end_pos) == int(field_list[4]) or (int(start_pos) < int(field_list[3]) and int(end_pos) > int(field_list[4])) :
                                        field_list[8] = exon_dict[transcript_match.group(1)][start_pos][end_pos]['ensembl_end_phase'] + exon_dict[transcript_match.group(1)][start_pos][end_pos]['ensembl_phase'] + field_list[8]
            
            out_fh.write("\t".join(field_list))
    print("Processing complete!")


def process_files_for_upload(root_path, jbrowse_download_directory, genome_version, faToTwoBit_path):
   
    '''This function unzips the downloaded files and coordinates processing of those files for JBrowse load'''
    print("Unzipping downloaded files.")
    downloaded_files = glob.glob(os.path.join(jbrowse_download_directory,"*[fagff3].gz"))
    if len(downloaded_files) > 0 :
        for gzipped_file in downloaded_files:
            try:
                subprocess.run(["gunzip","-fk",gzipped_file])
            except Exception as err:
                return(err)
    print("Unzipping complete.")
    for gzipped_file in downloaded_files:
        (filename,filext) = os.path.splitext(gzipped_file)
        try:
            if os.path.isfile(filename):
                if filename.endswith('.fa'):
                    process_fasta_file(filename, genome_version, faToTwoBit_path)
                elif '.gff' in filename:
                    process_gff_file(filename)
            else:
                return(filename + "not found in " + jbrowse_download_directory + ". Aborting.")
        except Exception as err:
            return(err)

    return_value = create_segments_bed(root_path, jbrowse_download_directory, genome_version)
    if return_value is not True:
        return return_value

    return True 

def create_segments_bed(root_path, jbrowse_download_directory, genome_version):

    segments_script = os.path.join(root_path,"src/setup","create_segments.sh")
    fai_file = None
    annotation_gff3 = None
    for glob_file in glob.glob(os.path.join(jbrowse_download_directory,"*fa.fai")):
        fai_file = glob_file

    for gff_file in glob.glob(os.path.join(jbrowse_download_directory,"*processed*gff*")):
        if 'Regulatory_Build' not in gff_file:
            annotation_gff3 = gff_file
    
    if fai_file is None or annotation_gff3 is None:
        return("fai fasta file or annotation gff file not found in the directory" + jbrowse_download_directory)

    try:
        subprocess.run(['sh', segments_script, fai_file, annotation_gff3, genome_version])
    except Exception as err:
        return(err)
    return True

def load_genome_into_JBrowse(jbrowse_path, jbrowse_data_directory, jbrowse_download_directory):

    ''' This function loads the genome fasta file into JBrowse '''
    print("Loading genome file into JBrowse. This might take a while.")
    genome_file = glob.glob(os.path.join(jbrowse_download_directory,"*processed*fa"))
    if len(genome_file) >0:
        try:
            subprocess.run([os.path.join(jbrowse_path,"bin","prepare-refseqs.pl"), "--fasta", genome_file[0], '--out', jbrowse_data_directory ])
        except Exception as err:
            return(err)
    else:
        return("Processed genome fasta file not found in the directory "+ jbrowse_download_directory)
    return True


def load_gff_into_JBrowse(root_dir,jbrowse_path, jbrowse_data_directory, jbrowse_download_directory, genome, genome_version):

    ''' This function loads genes, transcripts and regulatoary regions from gff files into JBrowse and copies the trackList.json template to the JBrowse data folder '''
    print("Loading annotations in JBrowse")
    to_copy_json = os.path.join(root_dir,"src/setup","trackList_no_regulatory.json") 
    gff_files = glob.glob(os.path.join(jbrowse_download_directory,"*processed*gff*"))
    try:
        for gff_file in gff_files:
            if 'Regulatory_Build' in gff_file:
                to_copy_json = os.path.join(root_dir,"src/setup","trackList.json")
                subprocess.run([os.path.join(jbrowse_path,"bin","flatfile-to-json.pl"), "--gff", gff_file, "--trackLabel", "Regulatory_build", '--out', jbrowse_data_directory])
            else:
                subprocess.run([os.path.join(jbrowse_path,"bin","flatfile-to-json.pl"), "--gff", gff_file, "--trackLabel", "Genes", "--type", "gene,ncRNA_gene,pseudogene", "--noSubfeatures", '--out', jbrowse_data_directory])
                subprocess.run([os.path.join(jbrowse_path,"bin","flatfile-to-json.pl"), "--gff", gff_file, "--trackLabel", "Transcripts", "--type", "transcript,pseudogenic_transcript,mRNA,miRNA,ncRNA,scRNA,snoRNA,snRNA,lnc_RNA,rRNA,tRNA", "--trackType", "CanvasFeatures", '--out', jbrowse_data_directory])
        subprocess.run([os.path.join(jbrowse_path,"bin","generate-names.pl"),'--out', jbrowse_data_directory])
        subprocess.run(['cp',to_copy_json,os.path.join(jbrowse_data_directory,"trackList.json")])
        
        #this section will write tracks.conf file to the jbrowse data folder and adds the genome name on Jbrowse menu
        with open(os.path.join(jbrowse_data_directory,"tracks.conf"),"w") as out_fh:
            out_fh.write("[general]\ndataset_id = "+str(genome_version))
        
        dataset_id = '[datasets.'+genome_version+']'
        dataset_id_exists = False
        with open(os.path.join(jbrowse_path,"jbrowse.conf"),"a+") as jbrowse_fh:
            jbrowse_fh.seek(0,0)
            for line in jbrowse_fh:
                if line.startswith(dataset_id):
                    dataset_id_exists = True
            if dataset_id_exists is False:
                jbrowse_fh.write(dataset_id+"\n")
                jbrowse_fh.write('url  = ?data='+os.path.basename(jbrowse_data_directory)+"\n")
                jbrowse_fh.write('name = '+ genome.lower())

        gRNA_gff = os.path.join(jbrowse_data_directory,"gRNA_CRISPR.gff")
        primer_gff = os.path.join(jbrowse_data_directory,"acceptedPrimers.gff")

        if not os.path.exists(gRNA_gff):
            subprocess.run(['touch',gRNA_gff])
            os.chmod(gRNA_gff,0o777)
    
        if not os.path.exists(primer_gff):
            subprocess.run(['touch',primer_gff])
            os.chmod(primer_gff,0o777)

    except Exception as err:
        return(err)
    return True

def load_geneinfo_RGENs_into_Mongo(jbrowse_download_directory, mongo_username, mongo_password, mongo_database, ensembl_version, genome, genome_version):
    
    ''' This function loads gene annoations into Mongo database under collection "geneInfo_<ensembl_version>" '''
    gene_info_collection = "geneInfo_" + str(ensembl_version)
    meta_data_collection = "metadata"

    geneInfo_gff = None
    gff_files = glob.glob(os.path.join(jbrowse_download_directory,"*processed*gff*"))
    for gff_file in gff_files:
        if 'Regulatory_Build' not in gff_file:
            geneInfo_gff = gff_file
    if geneInfo_gff is None:
        return("Cannot find annotation gff file in directory" + jbrowse_download_directory)
   
    mongo_uri = "mongodb://localhost:27017"
    if mongo_username is not None and mongo_password is not None:
       mongo_uri = "mongodb://%s:%s@%s" % (quote_plus(mongo_username), quote_plus(mongo_password), "localhost") #straight up copied from api.mongodb.com 

    try:
        pyMongoClient = MongoClient(mongo_uri)
    except Exception as err:
        return(err)

    print("Successfully connected to Mongodb")
    if mongo_database is None: #fix this.
        mongo_database = genome_version

    # load the RGEN json file into the RGEN database if it doesn't already exist
    if 'RGEN' not in pyMongoClient.list_database_names():
        rgenDB = pyMongoClient['RGEN']
        try:
            with open(os.path.join(dir_path,'rgens.json')) as json_file:
                rgenJSON = json.load(json_file)
                collection = rgenDB['rgenCollection']
                collection.insert(rgenJSON)
                print("Successfully inserted RGENs into Mongo database")
        except Exception as e:
            print("Error inserting RGENs into Mongo database: "+ str(e))
    else:
        print("RGEN collection already exists in Mongo database, will not overwrite")
    
    for collection_name in (gene_info_collection, meta_data_collection):
        if collection_name in pyMongoClient[mongo_database].collection_names():
            print(collection_name + " already exists in Mongo database")
            return True
    
    gene_info_collection_obj = pyMongoClient[mongo_database][gene_info_collection]
    meta_data_collection_obj = pyMongoClient[mongo_database][meta_data_collection]
    geneDict = {}
    with open(geneInfo_gff,"r") as inp_fh:
        for line in inp_fh:
            if line.startswith('#') is False:
                tmpArr = line.split("\t")
                if 'gene' in tmpArr[2].lower():
                    tmpDict = dict([[val for val in column.split("=")] for column in tmpArr[8].split(";")])
                    tmpDict['ID'] = tmpDict['ID'].replace("gene:","")
                    if 'Name' not in tmpDict:
                        tmpDict['Name'] = tmpDict['ID']
                    if tmpDict['ID'] not in geneDict:
                        geneDict[tmpDict['ID']] = {"ENSID":tmpDict['ID'],"Name": tmpDict['Name'], "chr":tmpArr[0], "start":int(tmpArr[3]), "end": int(tmpArr[4]), "strand": tmpArr[6]}    
    try:
        gene_info_collection_obj.insert_many(list(geneDict.values()))
        gene_info_collection_obj.create_index("ENSID")
        meta_data_collection_obj.insert_one({'org_name': genome.lower()})
    except Exception as err:
        return(err)

    print("Succesfully inserted gene annotations and RGENs into Mongo database.")
    return True

def create_blastdb(jbrowse_download_directory, blastdb_directory, genome_version, blast_path):
    
    ''' This function will create a blast database '''
    
    blast_input_fasta_file = genome_version + ".fa"
    blast_output_db = genome_version + "_blastdb"

    fasta_file = glob.glob(os.path.join(jbrowse_download_directory,"*processed*fa"))
    if len(fasta_file) == 0:
        return("Genome fasta file not found in "+ jbrowse_download_directory)
    
    try:
        os.chdir(blastdb_directory)
        subprocess.run(['ln', '-s', fasta_file[0], blast_input_fasta_file])
        subprocess.run([os.path.join(blast_path,"makeblastdb"), '-in', blast_input_fasta_file, '-input_type', 'fasta', '-dbtype', 'nucl', '-title', blast_output_db, '-parse_seqids', '-out', blast_output_db])
    except Exception as err:
        return(err)
    
    return True

if __name__=="__main__":
    main()
	
