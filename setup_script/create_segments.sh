fai_file=$1
gff3_file=$2
org=$3

work_dir=`dirname $1`

cut -f1,2 $fai_file | sort -k 1,1 >${work_dir}/${org}.genome
cut -f1 $fai_file > ${work_dir}/${org}.chr
grep -P "\s+gene\s+\d+\s+\d+" $gff3_file | grep -Ff ${work_dir}/${org}.chr >${work_dir}/genes.gff3
grep -P "\s+exon\s+\d+\s+\d+" $gff3_file | grep -Ff ${work_dir}/${org}.chr >${work_dir}/exons.gff3
awk 'BEGIN{OFS="\t";} {print $1,$4-1,$5}' ${work_dir}/genes.gff3 >${work_dir}/genes.bed
awk 'BEGIN{OFS="\t";} {print $1,$4-1,$5}' ${work_dir}/exons.gff3 >${work_dir}/exons.bed
bedtools sort -i ${work_dir}/exons.bed | bedtools merge -i - | awk -F"\t" '{print $0"\texonic"}' >${work_dir}/exons_merged.bed
bedtools sort -i ${work_dir}/genes.bed | bedtools subtract -a stdin -b ${work_dir}/exons_merged.bed  | awk '{print $0"\tintronic"}' >${work_dir}/introns.bed
bedtools sort -i ${work_dir}/genes.bed | bedtools complement -i stdin -g ${work_dir}/${org}.genome | awk '{print $0"\tintergenic"}' >${work_dir}/intergenic.bed
cat ${work_dir}/exons_merged.bed ${work_dir}/introns.bed ${work_dir}/intergenic.bed | bedtools sort -i - > ${work_dir}/${org}.segments.bed
