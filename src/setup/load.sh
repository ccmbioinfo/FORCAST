#!/usr/bin/env bash

set -euo pipefail

JBROWSE_BIN="$1"
SOURCE="$2"
DESTINATION="$3"
SPECIES="$4"
ASSEMBLY="$5"

"$JBROWSE_BIN/prepare-refseqs.pl" --fasta "$SOURCE"/*.processed.fa --out "$DESTINATION"

"$JBROWSE_BIN/flatfile-to-json.pl" \
    --gff "$SOURCE"/*.processed.gff3 \
    --trackLabel Genes \
    --type gene,ncRNA_gene,pseudogene \
    --noSubfeatures \
    --out "$DESTINATION"
"$JBROWSE_BIN/flatfile-to-json.pl" \
    --gff "$SOURCE"/*.processed.gff3 \
    --trackLabel Transcripts \
    --type transcript,pseudogenic_transcript,mRNA,miRNA,ncRNA,scRNA,snoRNA,snRNA,lnc_RNA,rRNA,tRNA \
    --trackType CanvasFeatures \
    --out "$DESTINATION"
TARGET=src/setup/trackList_no_regulatory.json
# Regulatory_Build
if compgen -G "$SOURCE"/*.processed.gff; then
    TARGET=src/setup/trackList.json
    "$JBROWSE_BIN/flatfile-to-json.pl" \
        --gff "$SOURCE"/*.processed.gff \
        --trackLabel Regulatory_build \
        --out "$DESTINATION"
fi
cp "$TARGET" "$DESTINATION/trackList.json"

echo -e "[general]\ndataset_id = $ASSEMBLY" > "$DESTINATION/tracks.conf"
echo -e "[datasets.$ASSEMBLY]\nurl = ?data=data/$ASSEMBLY\nname = $SPECIES ($ASSEMBLY)\n\n" >> jbrowse/jbrowse.conf
touch "$DESTINATION/gRNA_CRISPR.gff"
touch "$DESTINATION/acceptedPrimers.gff"
