#!/usr/bin/env bash
# script to ensure these files and directories can be run from the web

curr_dir=${PWD##*/}
if [ $curr_dir == "installation" ]; then
    cd ../..
else
    echo "this script must be run from the installation folder"
    exit
fi

sudo chgrp -R www-data config
sudo chmod -R 755 config
sudo chgrp -R www-data bin
sudo chmod -R 775 bin

# CODE
sudo chgrp -R www-data src
sudo chmod -R 755 src
# GUIDES
sudo chmod g+w src/guide-finder/tempfiles
sudo chmod g+w src/guide-finder/core
# PRIMER DESIGN
sudo chmod -R g+w src/primer-design/files

# give www-data full access to the gff track files
sudo find jbrowse -type f -name "*.gff" | sudo xargs chgrp www-data
sudo find jbrowse -type f -name "*.gff" | sudo xargs chmod 774

cd src/installation
