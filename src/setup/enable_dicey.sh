#!/bin/bash
# script to determine whether dicey index files for organism of interest are available
# downloads, renames, and puts them into the index directory if so

org_name=$1
genome=$2

# get dir of script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

delete_on_failure=false # flag for whether genome directory existed before

if [ -z $org_name ] || [ -z $genome ]
then
  echo "Please provide the organism name and genome version (e.g. 'Mus_musculus' 'mm10')"
  exit
fi

cd $DIR/../../bin/dicey

if [ ! -d ./indexes ]
then
  sudo mkdir indexes
fi

cd indexes
if [ ! -d ./$genome ]
then
  sudo mkdir $genome
  delete_on_failure=true
fi

cd $genome
if [ -f $genome.fa.fm9 ]
then
  echo "Index file already exists, exiting!"
  exit
fi

echo "Attempting to download index files for organism..."
sudo wget -r -np -nH --cut-dirs 2 -A "$org_name.*" https://gear.embl.de/data/tracy/ .
sudo rename "s/^.*.fa\./$genome.fa./" *

if [ ! -f $genome.fa.fm9 ]
then
  echo "Pre-built index files not available for $org_name."
  cd ..
  if [ "$delete_on_failure" = true ]
  then
    sudo rm -rf $genome
  fi
  exit
fi

# enable reading from web
sudo chgrp www-data *
sudo chmod g+r *

echo "Successfully downloaded index files for $org_name! In Silico PCR check for Primers by Dicey is now enabled"
exit
