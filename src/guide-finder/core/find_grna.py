import sys
import os.path
import re
import pprint
from pymongo import MongoClient

forward_nuc = 'ATGC'
reverse_nuc = 'TACG'
translate_code = str.maketrans(forward_nuc, reverse_nuc)


def get_rgen_info(rgen_id):

    '''
       
        This function will fetch RGEN information such as PAM sequence and minimum guide
        sequence length from MongoDB based on rgen_id 

    '''
    
    assert (int(rgen_id) >=1), "rgen_id must be 1 or above"
    mongo_client = MongoClient('mongodb://localhost:27017')
    if mongo_client is None:
        sys.exit("Cannot connect to Mongodb")
    
    rgen_result = mongo_client.RGEN.rgenCollection.find_one({'rgenID': str(rgen_id) }, {'_id':0, 'PAM':1, 'PamLocation':1, 'MinGuideLength':1, 'DefaultGuideLength': 1})
    if rgen_result is None:
        sys.exit("Cannot find RGEN info with rgen_id: " +rgen_id)
    if 'DefaultGuideLength' not in rgen_result:
        rgen_result['DefaultGuideLength'] = rgen_result['MinGuideLength']
        
    return (rgen_result['PAM'], rgen_result['DefaultGuideLength'], rgen_result['PamLocation'])

def process_fasta_file(fasta_file):
   
    '''
    
        This function will parse the fasta file to extract the following information
        1) Chromosome, start_pos, end_pos of the sequence from the header
        2) Concatenated sequence information without the new line characters

    '''
    
    sequence_to_return = ''
    with open(fasta_file,"r") as fasta_fh:
        for line in fasta_fh:
            if line.startswith(">"):
                header_match = re.search(r">(.+):(\d+)-(\d+)",line) 
                if header_match is None:
                    sys.exit("Fasta header is not in the format >chromosome:start-end")
                chrom, start_pos, end_pos = header_match.group(1), header_match.group(2), header_match.group(3)
            else:
                sequence_to_return = sequence_to_return + line.strip("\n").upper()
    
    return (chrom, start_pos, end_pos, sequence_to_return)


def return_all_pams(pam):

    '''

        This function will expand a given PAM motif sequence with IUPAC ambiguity codes and 
        will return all possible PAM motifs on both strands. For examples the PAM NGG will
        be expanded to AGG, TGG, CGG, GGG on '+' strand and CCT, CCA, CCG, CCC on '-' strand

    '''

    ambiguity_to_nuc = {
        'A': 'A', 'T': 'T', 'G': 'G', 'C': 'C',
        'R': ['A','G'], 'Y': ['C','T'], 'S': ['G','C'], 'W': ['A','T'], 'K': ['G','T'], 'M': ['A','C'],
        'B': ['C','G','T'], 'D': ['A','G','T'], 'H': ['A','C','T'], 'V': ['A','C','G'],
        'N': ['A','C','G','T']
    }

    forward_pam_motifs = [nuc for nuc in ambiguity_to_nuc[pam[0]]]
    for pam_nuc in pam[1:]:
        tmp_motifs = []
        for motif_nuc in forward_pam_motifs:
            for nuc in ambiguity_to_nuc[pam_nuc]:
                tmp_motifs.append(motif_nuc+nuc)  
        forward_pam_motifs = tmp_motifs
    
    revtrans_pam_motifs = []
    for forward_motif in forward_pam_motifs:
        reverse_motif = "".join(list(reversed(forward_motif))).translate(translate_code)
        revtrans_pam_motifs.append(reverse_motif)
    
    all_pam_motifs = {pam_motif:'+' for pam_motif in forward_pam_motifs}
    all_pam_motifs.update( {pam_motif:'-' for pam_motif in revtrans_pam_motifs} )
    
    return all_pam_motifs

def find_grna(rgen_id, grna_len, fasta_file):
    
    '''

        This function will return a list of PAM motifs along with the associated gRNA information
        in the sequence of interest specified in the fasta file. A dictionary with PAM positions
        as keys and the list of associated gRNA sequence, strand, pam sequence as the value is
        returned. E.g. {'68+': {'pam_chrom': chr1,'pam_location': downstream, 'strand': '+', 'pam_seq': 'AGG',
        'guide_seq': 'AGTGCGTGCTGCGCTCG', 'pam_genomic_start': 1677886, 'guide_genomic_start': 1677889} }

    '''

    pam, default_grna_len, pam_location =  get_rgen_info(rgen_id)
    grna_len = int(default_grna_len) if int(grna_len) == 0 else int(grna_len)

    if not os.path.exists(fasta_file):
        sys.exit("File " + fasta_file + "doesn't exist. Please enter a valid path.")

    (chrom, start_pos, end_pos, input_sequence) = process_fasta_file(fasta_file)

    if len(input_sequence) == 0 :
        sys.exit("input sequence is empty in the fasta file "+ fasta_file)

    #first, get all possible pam motif sequences given the pattern
    
    all_pam_motifs = return_all_pams(pam)
    
    '''
        Now that we have all possible pam motif sequences, search for all of them in the sequence
        Extract subsequences from the input sequence that are the same length as the PAM motif and 
        look for that subsequence in the list of all possible pam motifs generated above. If it is 
        found record the position of the subsequence based on the direction. 
        
        Once a PAM is found, based on the guide sequence properties i.e. the location of PAM W.R.T
        guide sequence and the guide sequence length, extract the guide sequence adjacent to the 
        PAM.
    '''
    
    pams_in_input = {}
    for i in range(0,len(input_sequence)-len(pam)+1):
        substring_to_search = input_sequence[i:i+len(pam)]
        if substring_to_search in all_pam_motifs:

            guide_seq = None
            guide_pos = None
            if all_pam_motifs[substring_to_search] == '+':
                pam_pos = i
                pam_seq = substring_to_search
                if pam_location == 'downstream':
                    if pam_pos - grna_len >=0:
                        guide_seq = input_sequence[pam_pos-grna_len : pam_pos]
                        guide_pos = pam_pos-grna_len
                elif pam_location == 'upstream':
                    if pam_pos + len(pam) + grna_len <= len(input_sequence):
                        guide_seq = input_sequence[pam_pos+len(pam) : pam_pos+len(pam)+grna_len]
                        guide_pos = pam_pos+len(pam)
            else:
                pam_pos = i+len(pam)-1
                pam_seq = "".join(list(reversed(substring_to_search))).translate(translate_code)
                if pam_location == 'downstream':
                    if pam_pos+1+grna_len <= len(input_sequence):
                        guide_seq = input_sequence[pam_pos+1 : pam_pos+1+grna_len]
                        guide_pos = pam_pos+grna_len
                elif pam_location=='upstream':
                     if pam_pos - len(pam) - grna_len + 1 >=0:
                        guide_seq = input_sequence[pam_pos-len(pam)-grna_len+1 : pam_pos-len(pam)+1]
                        guide_pos = pam_pos-len(pam)
                
                if guide_seq is not None:
                    guide_seq = "".join(list(reversed(guide_seq))).translate(translate_code) 

            if guide_seq is not None and len(guide_seq) == grna_len :
                pams_in_input[str(pam_pos)+str(all_pam_motifs[substring_to_search])] = {'pam_chrom':chrom, 'pam_location':pam_location, 'pam_seq': pam_seq, 'guide_seq': guide_seq, 'strand': all_pam_motifs[substring_to_search], 'pam_genomic_start': int(start_pos)+int(pam_pos), 'guide_genomic_start': int(start_pos)+int(guide_pos)}

    return(pams_in_input)
    pprint.pprint(pams_in_input)

#main program 
if __name__ == "__main__" :

    if len(sys.argv) < 3:
        sys.exit("Need  RGEN ID, path to fasta file, gRNA length (optional) as arguments")

    rgen_id, fasta_file = sys.argv[1], sys.argv[2]
    grna_length = sys.argv[3] if len(sys.argv) == 4 else 0

    find_grna(rgen_id, grna_length, fasta_file)
