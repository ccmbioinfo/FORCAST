#!/bin/bash
# convert a bedfile to fasta
: ${1?"genome fasta required"}
: ${2?"input bed required"}
: ${3?"tempfile directory required"}

genome_fa=$1
tempfiles=$3
dir_path="${0%/*}"

# check the input bed is a file
if [ -f "${tempfiles}/$2" ]; then
  # extract the basename
  bedfile=$(basename -- "$2")
  ext="${bedfile##*.}"
  basefilename="${fastafile%.*}"
else
  echo "Input bed file ${tempfiles}/$2 not found"
  exit 1
fi

bedtools getfasta -fi "${genome_fa}" -bed ${bedfile} -name

	extendedBed = os.path.join(tempfile_directory, str(batchID)+"_extended.bed")
	extendedFasta = os.path.join(tempfile_directory, str(batchID)+"_extended.fa")
	bashCommand = ["bedtools", "getfasta", "-fi", genome_fa, "-bed", extendedBed, "-name", "-fo", extendedFasta]
