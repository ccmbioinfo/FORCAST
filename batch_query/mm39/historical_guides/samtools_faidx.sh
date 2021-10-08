#!/bin/bash

#By: Nour Hanafi
#Purpose: extract PAM sequences
#Usage: sudo sh samtools_faidx.sh <input file> <output file>

#ACTION REQUIRED: add --reverse-complement argument if you are trying to get the sequence from the reverse strand
input=$1

while IFS= read -r line
do
 # echo "$line" >> samtools_output.txt
  samtools faidx /var/www/html/ForCasT/jbrowse/data.GRCm39/downloads/mus_musculus.104.full_genome.processed.fa $line --reverse-complement >> samtools_output.txt
done < "$input"

grep -v ">" samtools_output.txt > $2
