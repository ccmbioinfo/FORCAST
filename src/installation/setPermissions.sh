# need to make sure these files and directories can be run from the web
cd ../..

sudo chgrp -R www-data config
sudo chmod -R 755 config
sudo chgrp -R www-data bin
sudo chmod -R 775 bin

# landing page
sudo chgrp -R www-data src/landing-page
sudo chmod -R 755 src/landing-page

# grant www-data write permissions to the GuideFinder directory
sudo chgrp -R www-data src/guide-finder
sudo chmod -R 775 src/guide-finder

# give www-data full access to the gff track files
sudo find jbrowse -type f -name "*.gff" | sudo xargs chgrp www-data
sudo find jbrowse -type f -name "*.gff" | sudo xargs chmod 774

cd installation
