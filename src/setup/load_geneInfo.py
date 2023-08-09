#!/usr/bin/python3.7

import json, os, sys
from urllib.parse import quote_plus
from pymongo import MongoClient

dir_path = os.path.dirname(os.path.abspath(__file__))

def load_geneinfo_RGENs(geneInfo_gff, ensembl_version, genome, genome_version,
    mongo_username=None, mongo_password=None, mongo_database=None):

    ''' This function loads gene annoations into Mongo database under collection "geneInfo_<ensembl_version>" '''
    gene_info_collection = "geneInfo_" + str(ensembl_version)
    meta_data_collection = "metadata"

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
                collection.insert_many(rgenJSON)
                print("Successfully inserted RGENs into Mongo database")
        except Exception as e:
            print(f"Error inserting RGENs into Mongo database: {e}")
    else:
        print("RGEN collection already exists in Mongo database, will not overwrite")

    if gene_info_collection in pyMongoClient[mongo_database].list_collection_names():
        print(f"{gene_info_collection} already exists in Mongo database")
        return True

    sys.path.append(os.path.join(dir_path, "../helpers"))
    from Config import fetchCurrentRelease

    curr_release = fetchCurrentRelease(genome_version)

    if int(ensembl_version) <= int(curr_release):
        print(f"Metadata for newer Ensembl release ({curr_release}) already exists in Mongo database")
        return True

    meta_data_collection_obj = pyMongoClient[mongo_database][meta_data_collection]
    meta_data_collection_obj.delete_many({})

    gene_info_collection_obj = pyMongoClient[mongo_database][gene_info_collection]
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

if __name__ == "__main__":
    if len(sys.argv) > 4:
        load_geneinfo_RGENs(
            geneInfo_gff=sys.argv[1],
            ensembl_version=sys.argv[2],
            genome=sys.argv[3],
            genome_version=sys.argv[4]
        )
    else:
        print(f"Usage: {sys.argv[0]} <genes.gff3> <Ensembl version> <species> <assembly>", file=sys.stderr)
        exit(1)
