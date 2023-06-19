#!/usr/bin/env bash

set -euo pipefail

check_sum() {
    LINE=$(grep $1 $2)
    # Remove the name of the file from the checksum line.
    # Alternatively, we could append it to the `sum` output OR remove the extra spaces from it:
    # [[ $(echo $(sum $1)) != $(grep $1 $2 | awk '{print $1" "$2}' -) ]]
    if [[ $(sum $1) != ${LINE% $1} ]]; then
        >&2 echo "Checksum mismatch for $1"
        exit 1
    fi
}

ENSEMBL="$1"
SPECIES="$2"
ASSEMBLY="$3"

# Ensembl has configured its HTTPS server incorrectly, missing an intermediate certificate in the chain
# This is a workaround that still verifies the certificate chain, but it would still permit an attack
# from whatismychaincert.com or somebody compromising that website.
curl --fail --output ensembl.org.chained.crt 'https://whatsmychaincert.com/generate?include_leaf=1;host=ftp.ensembl.org'

# URLs are case-sensitive. Directories are lowercase, files are mixed.
TARGETS=(
    --output fasta.sum https://ftp.ensembl.org/pub/release-$ENSEMBL/fasta/${SPECIES,,}/dna/CHECKSUMS
    --output gff3.sum  https://ftp.ensembl.org/pub/release-$ENSEMBL/gff3/${SPECIES,,}/CHECKSUMS
    --remote-name      https://ftp.ensembl.org/pub/release-$ENSEMBL/gff3/${SPECIES,,}/$SPECIES.$ASSEMBLY.$ENSEMBL.gff3.gz
)

# Could check if the regulation directory exists (not 404) but that's an extra network request
if [[ $SPECIES == Homo_sapiens || $SPECIES == Mus_musculus ]]; then
    >&2 echo $SPECIES is expected to have a regulatory build.
    TARGETS+=(
        --output reg.sum
        https://ftp.ensembl.org/pub/release-$ENSEMBL/regulation/${SPECIES,,}/CHECKSUMS
    )
fi

>&2 echo Downloading all checksums and the GFF3...
# Since checksums are small, we can parallelize
curl --cacert ensembl.org.chained.crt --fail-early --fail --parallel ${TARGETS[@]}
check_sum $SPECIES.$ASSEMBLY.$ENSEMBL.gff3.gz gff3.sum

# Download the primary assembly to avoid weird contigs. If the file isn't there then
# the top level and the primary assembly are identical. (e.g. Saccharomyces_cerevisiae)
if grep "$SPECIES.$ASSEMBLY.dna.primary_assembly.fa.gz" fasta.sum; then
    FASTA=$SPECIES.$ASSEMBLY.dna.primary_assembly.fa.gz
else
    FASTA=$SPECIES.$ASSEMBLY.dna.toplevel.fa.gz
fi
>&2 echo Selected FASTA file $FASTA
TARGETS=(--remote-name https://ftp.ensembl.org/pub/release-$ENSEMBL/fasta/${SPECIES,,}/dna/$FASTA)

if [[ $SPECIES == Homo_sapiens || $SPECIES == Mus_musculus ]]; then
    # Get the name of the regulatory file without the ./ prefix (if applicable; i.e., for Ensembl release 103-106) from md5sum output
    # Ensembl release 103-106 mouse builds also have an extraneous checksum for a file that's not there so use END to select the last one
    FILENAME=$(grep "${SPECIES,,}.$ASSEMBLY.Regulatory_Build.regulatory_features.*.gff.gz" reg.sum | awk 'END{print $2}' | sed "s/^\.\///")
    >&2 echo Found regulatory build $FILENAME
    TARGETS+=(--remote-name https://ftp.ensembl.org/pub/release-$ENSEMBL/regulation/${SPECIES,,}/$FILENAME)
fi

>&2 echo Downloading remaining files...
curl --cacert ensembl.org.chained.crt --fail-early --fail --parallel ${TARGETS[@]}
check_sum $FASTA fasta.sum
if [[ ( $SPECIES == Homo_sapiens || $SPECIES == Mus_musculus ) && $(md5sum ./$FILENAME) != $(grep $FILENAME reg.sum) ]]; then
    >&2 echo "Checksum mismatch for $FILENAME"
    exit 1
fi
