#!/usr/bin/env bash

set -euo pipefail

fai_file=$1
gff3_file=$2
org=$3

work_dir=`dirname $1`

cut -f1,2 $fai_file | sort -k 1,1 >${work_dir}/${org}.genome
cut -f1 $fai_file > ${work_dir}/${org}.chr

# get genes into bed format
grep -oP "(chr\S+)\s+\S+\s+gene\s+\d+\s+\d+.+Name=[^;]+" $gff3_file | grep -Ff ${work_dir}/${org}.chr >${work_dir}/genes.gff3
awk 'BEGIN{OFS="\t";} {split($9,i,"Name="); print $1,$4-1,$5,"gene:"i[2]}' ${work_dir}/genes.gff3 > ${work_dir}/genes.bed
# ncRNA_genes
grep -oP "(chr\S+)\s+\S+\s+ncRNA_gene\s+\d+\s+\d+.+Name=[^;]+" $gff3_file | grep -Ff ${work_dir}/${org}.chr >${work_dir}/ncRNA_genes.gff3
awk 'BEGIN{OFS="\t";} {split($9,i,"Name="); print $1,$4-1,$5,"ncRNA_gene:"i[2]}' ${work_dir}/ncRNA_genes.gff3 > ${work_dir}/ncRNA_genes.bed
# pseudogenes
grep -oP "(chr\S+)\s+\S+\s+pseudogene\s+\d+\s+\d+.+Name=[^;]+" $gff3_file | grep -Ff ${work_dir}/${org}.chr >${work_dir}/pseudogenes.gff3
awk 'BEGIN{OFS="\t";} {split($9,i,"Name="); print $1,$4-1,$5,"pseudogene:"i[2]}' ${work_dir}/pseudogenes.gff3 > ${work_dir}/pseudogenes.bed

# combine and sort all the genomic regions
cat ${work_dir}/genes.bed ${work_dir}/ncRNA_genes.bed ${work_dir}/pseudogenes.bed | sort -k1,1 -k2,2n > ${work_dir}/genomic_regions.bed
# complement genomic regions with the genome to get intergenic regions (need to merge features 1bp away to prevent bedtools from making malformed complementary regions)
bedtools merge -i ${work_dir}/genomic_regions.bed -d 1 | bedtools complement -i - -g ${work_dir}/${org}.genome | awk '{print $0"\tintergenic"}' > ${work_dir}/intergenic.bed

# get exons
grep -oP "(chr\S+)\s+\S+\s+exon\s+\d+\s+\d+.+Parent=[^;]+" $gff3_file | grep -Ff ${work_dir}/${org}.chr >${work_dir}/exons.gff3
awk 'BEGIN{OFS="\t";} {split($9,i,"Parent=transcript:"); print $1,$4-1,$5,"exonic"}' ${work_dir}/exons.gff3 > ${work_dir}/exons.bed

# subtract the exons from the genomic regions to get the intronic regions
bedtools subtract -a ${work_dir}/genomic_regions.bed -b ${work_dir}/exons.bed | awk 'BEGIN{OFS="\t";} {split($4,i,":"); print $1,$2,$3,"intronic"}'> ${work_dir}/introns.bed

# to self: maybe should just cat the exons, introns, and intergenic? this will mean that the exons won't have a gene, just a transcript id
# cat the genomic regions with the everything else together and sort
cat ${work_dir}/genomic_regions.bed ${work_dir}/exons.bed ${work_dir}/introns.bed ${work_dir}/intergenic.bed | sort -k1,1 -k2,2n > ${work_dir}/${org}.segments.bed
