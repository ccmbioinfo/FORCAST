#!/usr/bin/env bash

set -euo pipefail

JBROWSE_BIN="$1"
SOURCE="$2"
DESTINATION="$3"
ENSEMBL="$4"
SPECIES="$5"
ASSEMBLY="$6"

SETUP_BIN=$(dirname $(realpath "$0"))
FORCAST_ROOT="$SETUP_BIN/../.."

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
TARGET="$SETUP_BIN/trackList_no_regulatory.json"
# Regulatory_Build
if compgen -G "$SOURCE"/*.processed.gff; then
    TARGET="$SETUP_BIN/trackList.json"
    "$JBROWSE_BIN/flatfile-to-json.pl" \
        --gff "$SOURCE"/*.processed.gff \
        --trackLabel Regulatory_build \
        --out "$DESTINATION"
fi
"$JBROWSE_BIN/generate-names.pl" --out "$DESTINATION"
cp "$TARGET" "$DESTINATION/trackList.json"

echo -e "[general]\ndataset_id = $ASSEMBLY" > "$DESTINATION/tracks.conf"

MATCH_REGEX="\[datasets\.$ASSEMBLY\]\n+url[\s|\t]*=[\s|\t]*.+\n+name[\s|\t]*=[\s|\t]*.+\n+"
REPLACEMENT_STRING="[datasets.$ASSEMBLY]\nurl = ?data=data\/$ASSEMBLY\nname = $SPECIES ($ASSEMBLY, Ensembl release $ENSEMBL)\n\n"
perl -i -0777 -pe "s/$MATCH_REGEX/$REPLACEMENT_STRING/" "$FORCAST_ROOT/jbrowse/jbrowse.conf"

echo -e "[datasets.$ASSEMBLY]\nurl = ?data=data/$ASSEMBLY\nname = $SPECIES ($ASSEMBLY, Ensembl release $ENSEMBL)\n" >> "$FORCAST_ROOT/jbrowse/jbrowse.conf"
touch "$DESTINATION/gRNA_CRISPR.gff" "$DESTINATION/acceptedPrimers.gff"
sudo chown www-data:www-data "$DESTINATION/gRNA_CRISPR.gff" "$DESTINATION/acceptedPrimers.gff"
