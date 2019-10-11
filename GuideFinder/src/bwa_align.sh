#!/bin/bash
# given a genome and input fasta file, perform bwa align with predefined parameters
# check parameters were passed
: ${1?"path to bwa index of genome required"}
: ${2?"input fasta required"}
: ${3?"tempfile directory required"}
# store the genome and module directory

bwa_index=$1
tempfiles=$3
dir_path="${0%/*}"

# check the input fasta is a file
if [ -f "${tempfiles}/$2" ]; then
	# extract the basename and extension of the file
	fastafile=$(basename -- "$2")
	ext="${fastafile##*.}"
	basefilename="${fastafile%.*}"
else
	echo "Input fasta file ${tempfiles}/$2 not found"
	exit 1
fi

# bwa alignment produces a sai file
saifile=$basefilename.sai
bwa aln -n 4 -l 0 -o 0 -t 2 -N "${bwa_index}" "${tempfiles}/${fastafile}" > "${tempfiles}/${saifile}"


if [ ! -f "${tempfiles}/$saifile" ]; then
	echo "Error at bwa aln step, check bwa index or input fasta ${2}"	
	exit 1
fi

# convert the sai file to sam, and convert multiple alignments to individual reads
samfile=$basefilename.sam
bwa samse -n 1000000 "${bwa_index}" "${tempfiles}/${saifile}" "${tempfiles}/${fastafile}" | "${dir_path}/xa2multi.pl" > "${tempfiles}/${samfile}"

if [ ! -f "${tempfiles}/$samfile" ]; then
	echo "Error at bwa samse or xa2multi.pl step"	
	exit 1
fi

# convert the sam to bam
bamfile=$basefilename.bam
samtools view -Sb "${tempfiles}/${samfile}" > "${tempfiles}/${bamfile}"

if [ ! -f "${tempfiles}/$bamfile" ]; then
	echo "Error converting sam to bam with samtools"	
	exit 1
fi

# then bam to bed
bedfile=$basefilename.bed
bedtools bamtobed -i "${tempfiles}/${bamfile}" > "${tempfiles}/${bedfile}"

if [ ! -f "${tempfiles}/$bedfile" ]; then
	echo "Error converting bam to bed with bedtools"	
	exit 1
fi

# end result is a bed file which has its coordinates extended to include a PAM and is then converted to fasta

