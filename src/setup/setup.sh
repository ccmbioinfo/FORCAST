#!/usr/bin/env bash

set -euo pipefail

ENSEMBL="$1"
SPECIES="$2"
ASSEMBLY="$3"

SETUP_BIN=$(dirname $(realpath "$0"))
FORCAST_ROOT="$SETUP_BIN/../.."

mkdir -p "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL/downloads"
cd "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL/downloads"
"$SETUP_BIN/download.sh" "$ENSEMBL" "$SPECIES" "$ASSEMBLY"
"$SETUP_BIN/process.sh" "$ASSEMBLY"
cd - >/dev/null
"$SETUP_BIN/load.sh" "$FORCAST_ROOT/jbrowse/bin" "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL/processed" "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL" "$ENSEMBL" "$SPECIES" "$ASSEMBLY"
python3.7 "$SETUP_BIN/load_geneInfo.py" "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL/processed/"*.processed.gff3 "$ENSEMBL" "$SPECIES" "$ASSEMBLY"

find "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY" -mindepth 1 -maxdepth 1 ! -name "$ENSEMBL" -exec rm -rf {} \;
mv "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL/"* "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY"
rm -rf "$FORCAST_ROOT/jbrowse/data/$ASSEMBLY/$ENSEMBL"