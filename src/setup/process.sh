#!/usr/bin/env bash

set -euo pipefail

ASSEMBLY="$1"

SETUP_BIN=$(dirname $(realpath "$0"))

gunzip --keep *.fa.gz *.gff*.gz
FASTA=$(echo *.fa) # only one
GFF=$(basename --suffix=.gz *.gff*.gz) # one or two, find the extracted files
mkdir -p ../processed
mv "$FASTA" $GFF ../processed
cd ../processed

python3 "$SETUP_BIN/process_fasta.py" "$FASTA"
ln -fs *.processed.fa "$ASSEMBLY.fa"
bwa index "$ASSEMBLY.fa" # creates $ASSEMBLY.bwt
faToTwoBit "$ASSEMBLY.fa" $ASSEMBLY.2bit
samtools faidx "$ASSEMBLY.fa" # creates $ASSEMBLY.fa.fai

# Results of indexing the original and the bgzipped processed FASTA are the same
ln -s ../downloads/*.fa.gz "$ASSEMBLY.fa.gz"
# This will silently fail if the source is not gzipped. Also creates $ASSEMBLY.fm9_check
dicey index -o $ASSEMBLY.fm9 "$ASSEMBLY.fa.gz"
# This is for "dicey search -g $ASSEMBLY.fa", which uses the filename stem to find the fm9

python3 "$SETUP_BIN/process_gff3.py" $GFF
rm "$FASTA" $GFF
# *.gff3 is always the non-regulatory build that is always present
"$SETUP_BIN/create_segments.sh" *.fa.fai *.processed.gff3 $ASSEMBLY

mkdir -p ../blastdb
makeblastdb -in $ASSEMBLY.fa -input_type fasta -dbtype nucl \
    -title $ASSEMBLY\_blastdb -parse_seqids -out ../blastdb/$ASSEMBLY\_blastdb
