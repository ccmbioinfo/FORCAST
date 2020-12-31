#/bin/python3

import json
import random
import sys
import re
import subprocess

from subprocess import PIPE, DEVNULL

import pandas as pd

from pymongo import MongoClient


""" 
REQUIRES A FORCAST DATABASE FOR THE GIVEN GENOME TO BE RUNNING ON THE SERVER
run via:
python3 batchGuideQuery.py <sheet> mm10
"""

def revSeq(seq):
	""" given a sequence returns the complement (preserving direction, i.e. 5'->3' is converted to 5'->3' on opposite strand) """
	complement = {'A':'T','C':'G','G':'C','T':'A', 'N':'N', 'a':'t', 'c':'g', 'g':'c', 't':'a'}
	return ''.join([complement[base] for base in seq[::-1]])

def selectRandomRegion(genome, length):
  # select a random gene from the given organism and return a region of the specified length within the gene
  try:
    # connect to the db
    client = MongoClient()
    db = client[genome]
  except Exception as e:
    print("Error fetching genome for: "+str(genome))

  # get most recent ensembl release
  curr_release = -1
  for c in db.collection_names():
    if 'geneInfo' in c:
      if int(c.split("_",1)[1]) > int(curr_release):
        gene_collection = db[c]
        curr_release = int(c.split("_",1)[1])

  # fetch random gene from collection
  rand_gene = None
  # re-retrive until non-predicted gene found
  while not rand_gene or rand_gene['Name'].startswith("Gm") or rand_gene['Name'].endswith("Rik"):
    rand_gene = list(gene_collection.aggregate([{"$match": {}}, {"$sample": {"size": 1}}]))[0]
  # get random location in gene range
  coord = random.randrange(int(rand_gene['start']), int(rand_gene['end']), int(length))

  # return random location
  gene = rand_gene['Name']
  loc = str(rand_gene['chr'])+":"+str(coord)+"-"+str(int(coord)+int(length))
  print(gene + " " + loc)
  return gene, loc

def locationSearchCommand(org):
		"""
		Returns BLAST command for mm10 optimized for parsing the location from a search.
		"""
		# base shell command with path
		blastCommand = ["/var/www/html/ForCasT/bin/ncbi-blast-2.7.1+/bin/blastn"]
		blastCommand.append('-db')

		# blast db that was created by makeblastdb command on mm10.fa files from ensembl
		blastCommand.append("/var/www/html/ForCasT/jbrowse/data.mm10/blastdb/"+str(org)+'_blastdb')
		blastCommand.append('-task')

		# since the primers are short, need to pass this argument or no hits will be found
		blastCommand.append('blastn-short')
	
		# specify output format (just need location and nident)
		blastCommand.append('-outfmt')
		blastCommand.append('7 qseqid sseqid nident sstrand sstart send')	
		
		return blastCommand

def blastSeq(seq, blastLocation, hitSearch):
  # convert sequence to fasta format
  printfCommand = ['printf', ">primerBLAST\n " + str(seq)]
  try:
    # bash command pipes the print command in fasta format to blast
    printfProcess = subprocess.Popen(printfCommand, stdout=subprocess.PIPE)
    blastProcess = subprocess.Popen(blastLocation, stdin=printfProcess.stdout, stdout=subprocess.PIPE)
    (blastOut, blastErr) = blastProcess.communicate()
  except Exception as e:
    print("Error running BLAST: " + str(e))
    sys.exit()
  if blastErr:
    print(blastErr)

  hits = [] # to store locations
  seqLength = len(str(seq))	
  for line in blastOut.splitlines():
    try:
      hitMatch = hitSearch.search(line.decode())
    except Exception:
      sys.stderr(line)
      continue
    
    if hitMatch:
      identLength = int(hitMatch.group(2))
      if seqLength == identLength:
        offset = 23 - seqLength # for 23 bp guide+PAM in case PAM not in sequence
        direction = hitMatch.group(3)
        try:
          if direction == "minus":
            start = str(int(hitMatch.group(5))-offset)
            end = hitMatch.group(4)
            location = hitMatch.group(1)+":"+start+"-"+end+":-"
          elif direction == "plus":
            start = hitMatch.group(4)
            end = str(int(hitMatch.group(5))+offset)
            location = hitMatch.group(1)+":"+start+"-"+end+":+"
          else:
            print("Error parsing direction of match: " + str(hitMatch.group(3)))
        except Exception as e:
          print(str(e))
          print(seqLength)
          for i in range(0,5):
            print(hitMatch.group(i))
          print(offset)
          continue

        hits.append(location)
        continue # don't need to look through hits anymore
  
  return hits

def parseOutput(output, strand):
  """ take the output of the guide search and return relevant fields """
  output = output.decode() # encode to bytes
  lines = output.split("\n")
  result_dict = {}
  count = 0
  for line in lines:
    if "Strand=" in line:
      count += 1
      if line.split("=")[1] == strand:
        record = True
      else:
        record = False
    if "=" in line and record == True:
      field, value = line.split("=")
      result_dict[field] = value

  if count > 2:
    print("ummm?? too many found:")
    print(output)
  if not result_dict:
    print("nothing found:")
    print(output)
  
  return result_dict


def processGuides(file, org):
  conversion = {key+str(i):str for i in range(1,5) for key in ['MIT_Score','CFD_Score','Total_Off-targets','Off-target_Profile','Off-target_Profile_Seed','Strand']} 
  df = pd.read_excel(file, converters=conversion)
  blastLocation = locationSearchCommand(org)
  hitSearch = re.compile("^primerBLAST[\s]([^\s]+)\s([0-9]*)[\s]*(minus|plus)[\s]*([0-9]*)[\s]*([0-9]*)")

  for index, row in df.iterrows():
    for g in [str(x) for x in range(1,5)]:
      gRNA_idx = 'gRNA'+g
      if not pd.isnull(row[gRNA_idx]):
        seq = row[gRNA_idx]
        ignoring = False
        if len(seq) == 23 and not seq.endswith('GG'):
          # reverse the (known) 3' to 5' guides
          seq = revSeq(seq)
          print("flipped "+str(row[gRNA_idx])+" -> "+str(seq))
          ignoring = True

        hits = blastSeq(seq, blastLocation, hitSearch)
        if len(hits) != 1:
          sys.exit("Guide Sequence "+str(seq)+" in row "+str(index)+" has "+str(len(hits))+" identical matches in the genome")
        # check that the guide location matches what's stored
        print("Found: "+hits[0])
        print("Stored: "+str(row['Location'+g]))

        if not(pd.isnull(row['Location'+g])) and hits[0].rsplit(":",1)[0] != str(row['Location'+g]) and not ignoring:
          print("Computed and stored location do not match")
          print(hits[0])
          print(row['Location'+g])
        
        just_location = hits[0].rsplit(":",1)[0]
        df.at[index,'Location'+g] = just_location 

        gene = row['Target']
        location, strand = hits[0].rsplit(":",1)
        p = subprocess.Popen(["python3","/var/www/html/ForCasT/src/guide-finder/GuideSearchAndScore.py", "--genome=mm10", "--gene="+str(gene), "--input="+str(location),"--output=output/"+str(gene)+".csv","--maxOffTargets=-1"], stdout=PIPE)
        out, err = p.communicate()
        result_dict = parseOutput(out, strand)
        for field, value in result_dict.items():
          if field == 'Guide':
            revised_seq = value.split(", ")[0]
            df.at[index, 'gRNA'+g] = str(revised_seq)
          elif field == 'Location':
            if value != hits[0]:
              print("Location doesn't match guide search")
              print(value)
              print(hits)
            df.at[index, field+g] = str(location)
          else:
            df.at[index, field+g] = str(value)

  from openpyxl.utils import get_column_letter
  df.to_excel("Results.xlsx", index=False)
  return

def main():
  # parse command-line args
  if len(sys.argv) != 3:
    print("Please provide a sample file and genome")
    sys.exit()

  processGuides(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
  main()
