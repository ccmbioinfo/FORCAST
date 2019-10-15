#!/bin/bash
# script to install the dependencies for primer design (Blast, Primer3, Dicey)
set -e

echo "This program must be run by an account with sudo privileges."
echo "This program will install all the dependencies for JBrowse, casFinder and primer design"
echo "It will create a directory, 'dependencies', and will place primer design dependencies in it (Blast, Primer3, Dicey)" 
echo "Then it will generate a configuration file (paths.conf) which stores the paths to Blast, Primer3 and Dicey."
echo "If you wish to move the executables for these tools, please ensure the paths.conf file is updated accordingly"

root_dir=$1

if [ -z $root_dir ]
then
    echo "Need the full path to root(installation) directory as the command line argument"
    exit
fi
if [ ! -d $root_dir ]
then
    echo "$root_dir isnt a valid path"
    exit
fi

#first, update apt-get
apt-get update

#then install sudo
if [ ! -n "$(command -v sudo)" ]
then
    apt-get install -y sudo
fi

#create necessary directories. /data/db is for MongoDB

req_dirs=($root_dir/dependencies /data/db  $root_dir/config)

for i in "${req_dirs[@]}";
do
if [ ! -d $i ]
then
    mkdir -p $i
fi
done

#now install dependencies for Jbrowse and GuideFinder.

echo "Installing dependencies for Jbrowse and GuideFinder"
Jbrowse_crispr_dependencies=(git wget apache2 bwa bedtools krb5-user python2.7 python3 python-pip python3-pip samtools zlib1g-dev)

for i in "${Jbrowse_crispr_dependencies[@]}";
do
if [ -n "$(command -v $i)" ]
then
    echo "$i already installed, skipping installation step..."
else
    apt-get install -y $i
fi
done

#Now install Mongodb 3.6.12
apt-get install -y apt-transport-https
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.6 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.6.list
apt-get update
apt-get install -y mongodb-org

# Now install python modules and jbrowse dependencies
pip2 --default-timeout=10000 install -r requirements.txt
pip3 --default-timeout=10000 install -r requirements_v3.txt

cd $root_dir/jbrowse
./setup.sh

#### Hillary's primer design section begins 
cd $root_dir/dependencies

# check if primer3 already installed and if not, install it
if [ -n "$(command -v primer3/src/primer3_core)" ]
then
        echo "Primer3 installation already performed, skipping installation step..."
        primer3exec=$(pwd)"/primer3/src/primer3_core"
        primer3config=$(pwd)"/primer3/src/primer3_config/"
else
        echo "Installing Primer3...\n"
        sudo apt-get install -y build-essential g++ cmake
        git clone https://github.com/primer3-org/primer3.git primer3
        cd primer3/src
        make
        echo "\nPrimer3 successfully installed. Will now run test to ensure there were no issues with the installation"
        #make test
        # store location to the primer3 executable
        primer3exec=$(pwd)"/primer3_core"
        cd ..
        # store the config file
        primer3config=$(pwd)"/src/primer3_config/"
        cd .. # navigate back to dependencies/
fi

# check if blast already installed and if not, install it
if [ -n "$(command -v ncbi-blast-2.7.1+/bin/blastn)" ]
then
        echo "Blast installation already performed, skipping installation step..."
        blastexec=$(pwd)"/ncbi-blast-2.7.1+/bin/blastn"
else
        echo "Installing BLAST...\n"
        wget "ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/2.7.1/ncbi-blast-2.7.1+-x64-linux.tar.gz"
        tar xvpf ncbi-blast-2.7.1+-x64-linux.tar.gz
        blastexec=$(pwd)"/ncbi-blast-2.7.1+/bin/blastn"
        rm ncbi-blast-2.7.1+-x64-linux.tar.gz # remove the zipped file
        echo "\nSuccessfully installed BLAST"
fi

# check if dicey already installed and if not, install it
if [ -n "$(command -v dicey/bin/dicey)" ]
then
        echo "Dicey installation already performed, skipping installation step..."
        diceyexec=$(pwd)"/dicey/bin/dicey"
        if [ ! -d dicey/dicey_tempfiles ]
        then
                mkdir dicey/dicey_tempfiles
        fi
        diceypath=$(pwd)"/dicey"
else
        sudo apt-get install -y build-essential g++ cmake zlib1g-dev libbz2-dev liblzma-dev libboost-all-dev
        git clone --recursive https://github.com/gear-genomics/dicey.git
        cd dicey/
        make all
        make install
        diceyexec=$(pwd)"/bin/dicey"
        mkdir dicey_tempfiles # directory required for dicey program to run
        diceypath=$(pwd)
        echo "\nSuccessfully installed Dicey"
        cd ..
fi

#enable apache2 cgi module 
sudo a2enmod cgi

cd ..
# now create the config file to store the paths to the dependency executables
# this will be gotten from the root directory supplied by the user
echo -e "PRIMER3_EXEC=$primer3exec\nPRIMER3_CONFIG=$primer3config\nBLAST_EXEC=$blastexec\nDICEY_EXEC=$diceyexec\nDICEY_PATH=$diceypath" > $root_dir/config/paths.conf

if [ ! -d $root_dir/config/primer3settings ]
then
    cp -r $root_dir/templates/primer3settings $root_dir/config/primer3settings
fi
if [ ! -f $root_dir/config/primer3settings.conf ]
then
    cp $root_dir/templates/primer3settings.conf $root_dir/config/primer3settings.conf
fi
