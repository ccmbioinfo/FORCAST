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

# saccharomyces_cerevisiae only has toplevel

# Ensembl has configured its HTTPS server incorrectly, missing an intermediate certificate in the chain
# This is a workaround that still verifies the certificate chain, but it would still permit an attack
# from whatismychaincert.com or somebody compromising that website.
curl --output ensembl.org.chained.crt 'https://whatsmychaincert.com/generate?include_leaf=1;host=ftp.ensembl.org'
# URLs are case-sensitive. Directories are lowercase, files are mixed.
curl --cacert ensembl.org.chained.crt --fail-early --fail \
    --output fasta.sum https://ftp.ensembl.org/pub/release-$ENSEMBL/fasta/${SPECIES,,}/dna/CHECKSUMS \
    --remote-name      https://ftp.ensembl.org/pub/release-$ENSEMBL/fasta/${SPECIES,,}/dna/$SPECIES.$ASSEMBLY.dna.primary_assembly.fa.gz \
    --output gff3.sum  https://ftp.ensembl.org/pub/release-$ENSEMBL/gff3/${SPECIES,,}/CHECKSUMS \
    --remote-name      https://ftp.ensembl.org/pub/release-$ENSEMBL/gff3/${SPECIES,,}/$SPECIES.$ASSEMBLY.$ENSEMBL.gff3.gz
check_sum $SPECIES.$ASSEMBLY.dna.primary_assembly.fa.gz fasta.sum
check_sum $SPECIES.$ASSEMBLY.$ENSEMBL.gff3.gz gff3.sum

# Could check if the regulation directory exists (not 404) but that's another network request
if [[ $SPECIES == Homo_sapiens || $SPECIES == Mus_musculus ]]; then
    wget2 --ca-certificate ensembl.org.chained.crt \
        --execute robots=off --recursive --level=1 --no-parent --no-directories \
        --accept "CHECKSUMS" --accept "*.gff.gz" \
        https://ftp.ensembl.org/pub/release-$ENSEMBL/regulation/${SPECIES,,}/
    DOWNLOAD=./${SPECIES,,}.$ASSEMBLY.Regulatory_Build.regulatory_features.*.gff.gz
    if [[ $(md5sum $DOWNLOAD) != $(grep $DOWNLOAD CHECKSUMS) ]]; then
        >&2 echo "Checksum mismatch for $DOWNLOAD"
        exit 1
    fi
fi
