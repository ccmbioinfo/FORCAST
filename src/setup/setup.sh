#!/usr/bin/env bash

set -euo pipefail

ENSEMBL="$1"
SPECIES="$2"
ASSEMBLY="$3"

SETUP_BIN=$(dirname $(realpath "$0"))

mkdir -p "jbrowse/data/$ASSEMBLY/downloads"
cd "jbrowse/data/$ASSEMBLY/downloads"
"$SETUP_BIN/download.sh" "$ENSEMBL" "$SPECIES" "$ASSEMBLY"
"$SETUP_BIN/process.sh" "$ASSEMBLY"
cd - >/dev/null
"$SETUP_BIN/load.sh" jbrowse/bin "jbrowse/data/$ASSEMBLY/processed" "jbrowse/data/$ASSEMBLY" "$SPECIES" "$ASSEMBLY"
python3 "$SETUP_BIN/load_geneInfo.py" jbrowse/data/"$ASSEMBLY"/processed/*.processed.gff3 "$ENSEMBL" "$SPECIES" "$ASSEMBLY"
