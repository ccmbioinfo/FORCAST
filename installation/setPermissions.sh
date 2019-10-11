# need to make sure these files and directories can be run from the web
cd ..

sudo chgrp -R www-data config
sudo chmod -R 755 config
sudo chgrp -R www-data dependencies
sudo chmod -R 775 dependencies

# landing page
sudo chgrp -R www-data landing-page
sudo chmod -R 755 landing-page

# allow www-data to execute all python and cgi scripts in primerDesign
sudo find primerDesign -type f \( -name "*.py" -o -name "*.cgi" \) | sudo xargs chgrp www-data
sudo find primerDesign -type f \( -name "*.py" -o -name "*.cgi" \) | sudo xargs chmod g+x

# grant full permissions to web user for file generation
sudo chgrp -R www-data primerDesign/python/files
sudo chmod -R 774 primerDesign/python/files

# grant all users execute permissions to customPython
sudo chmod -R a+x customPython

# give www-data full access to the gff track files
sudo find jbrowse -type f -name "*.gff" | sudo xargs chgrp www-data
sudo find jbrowse -type f -name "*.gff" | sudo xargs chmod 774

cd installation
