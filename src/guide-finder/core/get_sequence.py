#!/usr/bin/env python3

import subprocess
import sys
import os
import re

'''

    This program will create a fasta file based on an input genomic twoBit file.
    Requirements: fastaToTwoBit tool, a twoBit genome file

'''

dir_path = os.path.dirname(os.path.abspath(__file__))

def fetch_sequence(chrom_coord, genome_twobit, output_fasta):
    '''
        This function will return sequence for a given chromosome, start, end from the genome_twobit file
    '''

    chrom_match = re.match(r"(.+):(\d+)-(\d+)", chrom_coord)
    if chrom_match is None:
        sys.exit("Chromosomal coordinate must be in the format chrom:start-end")

    chrom, start, end = chrom_match.group(1), chrom_match.group(2), chrom_match.group(3)
    # end for twoBitToFa is non-inclusive, add extra base
    start = str(int(start)-1)
    seq_param, start_param, end_param = '-seq={0}'.format(chrom), '-start={0}'.format(start), '-end={0}'.format(end)
    tmp_fasta = os.path.join(dir_path,"tmp.fa")

    try:
        twoBitToFaOut = (
            subprocess.check_output(
                [
                    "twoBitToFa",
                    seq_param,
                    start_param,
                    end_param,
                    genome_twobit,
                    "stdout",
                ],
                encoding="utf-8",
            )
            .rstrip("\n")
            .splitlines()
        )

        if len(twoBitToFaOut):
            with open(output_fasta, "w") as out_fa:
                out_fa.write(">" + chrom + ":" + str(int(start) + 1) + "-" + end + "\n")
                for line in twoBitToFaOut:
                    if not line.startswith(">"):
                        out_fa.write(line)
        else:
            print(
                "twobitToFasta failed: "
                + " ".join([seq_param, start_param, end_param, genome_twobit, "stdout"])
            )
            sys.exit(
                "sequence is empty for given parameters. Please check your parameters again"
            )
    except Exception as err:
        print(err)

    return 1


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("Need chromosomal coordinates (chr:start-stop), genome_twobit, output fasta file as arguments.")
    chrom_coord, genome_twobit, output_fasta = sys.argv[1:]
    fetch_sequence(chrom_coord, genome_twobit, output_fasta)
