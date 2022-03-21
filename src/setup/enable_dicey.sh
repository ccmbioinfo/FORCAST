#!/bin/bash

set -euo pipefail

org_name="$1"
genome="$2"

mkdir -p "/opt/dicey/indexes/$genome"
cd "/opt/dicey/indexes/$genome"

if [[ -f "$genome.fa.fm9" ]]; then
  echo "Index file already exists!"
  exit 1
fi

wget -r -np -nH --cut-dirs 2 -A "$org_name.*" https://gear.embl.de/data/tracy/
rename "s/^.*.fa\./$genome.fa./" *

if [ ! -f "$genome.fa.fm9" ]
then
  echo "WARNING: prebuilt index files not available for $org_name!"
  exit 2
fi
