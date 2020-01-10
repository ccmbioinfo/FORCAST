# CasCADe: a fully integrated and open source pipeline to design CRISPR mutagenesis experiments

## Contents  
[Hardware Requirements](#hardware-requirements)<br>
[Installing With Docker](#installing-with-docker)<br>
[Installing Natively](#installing-natively)<br>
[Customization](#customization)<br>
[Migration](#migration)<br>
[Troubleshooting](#troubleshooting)<br>

## Hardware Requirements
CasCADe can be installed on any machine running a [docker-compatible operating system](https://docs.docker.com/install/). Alternately, to run CasCADe natively, Ubuntu 16.04 is required.

In either case, a minimum of 8GB of RAM and 100GB of hard disk space is recommended.

## Installing with Docker
First, install the [docker engine](https://docs.docker.com/install/). If using Linux, also install [docker compose](https://docs.docker.com/compose/install/) (this is included by default in Mac and Windows installations of docker).

Clone the CasCADe repository:
```
    git clone https://github.com/ccmbioinfo/CasCADe.git
```

Navigate to the `CasCADe` directory. By default, the `.env` file defines yeast (*Saccharomyces_cerevisiae*) as the organism of interest with genome assembly R64-1-1:
```
    ORGANISM=Saccharomyces_cerevisiae
    ASSEMBLY=R64-1-1
```

Change these defaults to your desired organism/genome build if they are different. A full list of available genomes can be found at [ftp://ftp.ensembl.org/pub/release-98/fasta](ftp://ftp.ensembl.org/pub/release-98/fasta/).

From within the `CasCADe` directory, build the docker container:

```docker-compose up```

Depending on the size of your organism, it may take several hours to download the genome and build the index files. Once the setup is complete, the message: ` * Starting Apache httpd web server apache2 * ` will be displayed. CasCADe should be available via web browser at your server's domain address (or at localhost if running locally).

## Installing Natively
(Requires `sudo` privileges and a machine running Ubuntu 16.04)

Install git and apache2:
  ```
    sudo apt-get update
    sudo apt-get install -y git apache2
  ```
 
Navigate to a folder where you would like to install CasCADe. It must be a folder that can be served by apache2 (i.e. `var/www/html`) and remove the index.html file if it exists
```
cd /var/www/html
rm index.html
```

Clone the CasCADe repo:
  ```
    git clone https://github.com/ccmbioinfo/CasCADe.git
  ```    

 Then, run the installation script using the command below
 ```
    cd CasCADe/src/installation
    ./install.sh /var/www/html/CasCADe
 ```

If the installation process halts with a message ```Default Kerberos version 5 realm:```, press Enter

After the installation step is completed, start the mongodb server: `systemctl start mongod`

Then, navigate to the `src/setup` folder under the root directory (e.g.`/var/www/html/CasCADe/src/setup`), and run the following command to setup Jbrowse, the BLAST database and mongodb.
```
    python3 setup.py -r /var/www/html/CasCADe -g Saccharomyces_cerevisiae -v R64-1-1 -fa2bit /var/www/html/CasCADe/bin/faToTwoBit -b /var/www/html/CasCADe/bin/ncbi-blast-2.7.1+/bin
```

Replace the default organism (*Saccharomyces_cerevisiae*) and its genome build (**R64-1-1**) with your organism and build of interest. A full list of available genomes can be found at [ftp://ftp.ensembl.org/pub/release-98/fasta](ftp://ftp.ensembl.org/pub/release-98/fasta/). 

Now, run the script to grant apache the correct file permissions.
```
    cd /var/www/html/CasCADe/src/installation
    ./setPermissions.sh
```

Next, the apache server needs to be configured to make the tool web accessible.

Open the file ```/etc/apache2/sites-available/000-default.conf```, modify the DocumentRoot to the location where CasCADe was installed, and add this section below:
```
    DocumentRoot /var/www/html/CasCADe
     <Directory '/var/www/html/CasCADe'>
        Options +ExecCGI
        AddHandler cgi-script .py
        Allow from all
     </Directory>
```

Then, restart apache2 and start mongo
```
    systemctl restart apache2
    systemctl start mongodb
```

CasCADe should now be accessible from your browser at ```http://<your servers address>```. For example if your VM's IP address is ```172.20.20.20```, you can type : ```http://172.20.20.20``` in your browser to access CasCADe.

To enable In Silico PCR tool [Dicey](https://github.com/gear-genomics/dicey) (a.k.a. [Silica](https://www.gear-genomics.com/silica/)), run the ```enable_dicey.sh``` script. Again provide your organism of interest and genome assembly in place of *Saccharomyces_cerevisiae* and R64-1-1:
```
 cd /var/www/html/CasCADe/src/setup
 ./enable_dicey Saccharomyces_cerevisiae R64-1-1
```
Which will fetch and name the index files if they're available.

If you want your installation of CasCADe to be secured by https, please refer to apache2's documentation on how to enable https module.

## Customization

### Custom Primer Design Settings
First, go to to [the primer3 website](http://bioinfo.ut.ee/primer3/) and enter the custom settings that you would like to use for the first attempt of primer design and click 'Download Settings' to save the file. Additionally, you may also specify and download 'retry attempt' settings to be used if no primers are found with the default settings. There is no limit to the number of retry attempts you can define.

Once all the settings files have been generated, ssh into the server hosting CasCADe and navigate to where the application is rooted (e.g. ```/var/www/html/CasCADe```). Within the ```config``` directory there should be a ```primer3settings.conf``` file and a directory, ```primer3settings```, where the default primer3 settings are stored. Replace these with your custom settings and edit the ```primer3settings.conf``` file to point to the new files like so:
```
ATTEMPT_0_FILE=primer3settings/filename.txt
ATTEMPT_1_FILE=primer3settings/filename1.txt
ATTEMPT_1_DESC="Description of changes in ATTEMPT_1 file"
ATTEMPT_2_FILE=primer3settings/filename2.txt
ATTEMPT_2_DESC="Description of changes in ATTEMPT_2 file"
```
The descriptions are optional but will be displayed to users if a design failure occurs.

### Custom RNA-guided Endonuclease (RGEN) Settings

The `src/setup/rgens.json` defines the default RGEN settings:

| Shortform | PAM | PamLocation | MinGuideLength | MaxGuideLength | DefaultGuideLength | SeedRegion | Cleaves | OffTargetPAMs | Scores |
| --------- | --- | ----------- | -------------- | -------------- | ------------------ | ---------- | ------- | ------------- | ------ |
| SpCas9 (NGG) | NGG | downstream | 17 | 20 | 20 | -12 | -3 | NGG, NAG | MIT, CFD |
| AsCpf1/Cas12a | TTTV | upstream | 20 | 23 | - | +6 | +19,+23 | TTTV, TTTT, CTTA, TTCA | - |
| ScCas9 (NNG) | NNG | downstream | 20 | 20 | - | -12 | -3 | NNG | - |
| ScCas9 (NNGT) | NNGT | downstream | 20 | 20 | - | -12 | -3 | NNGT | - |
| SaCas9 | NNGRRT | downstream | 21 | 23 | - | -8 | -3 | NNGRRT, NNGRR | - |

However, we recognize that these settings and defaults may not be applicable to all users. New RGENs can be added by specifying the RGEN parameters in the template below and appending to the `rgens.json` file.

```
{"rgenID" : "6", "Shortform" : "<shortform>", "Longform" : "<optional>", "PAM" : "<nucleotide sequence>", "PamLocation" : "<downstream or upstream>", "MinGuideLength" : "<required>", "MaxGuideLength" : "<required>", "DefaultGuideLength": "<optional>", "SeedRegion" : "<direction and length of seed>", "Cleaves" : [ "<cleavage site>" ], "OffTargetPAMS" : [ "<actual PAM>", "<optional off-targets>" ], "Scores" : []}
```

Existing RGENs can have their settings and defaults modified in the file as well. In order to keep existing guides associated to their RGENs, it's recommended that the rgenIDs remain unchanged for existing entries.

After modifying the `rgens.json` file, you can run the `load_RGENs.py` script in the same directory (`python3 load_RGENS.py`) and provide the desired command-line argument:
- `update`: modifies existing records based on the rgenID and adds new RGENs to the database (recommended)
- `replace`: wipes and replaces RGEN database with new entries, potentially unlinking existing gRNA records from their RGEN.

## Migration
If using a previous version of CasCADe, existing Primers and Guides can be migrated to the new version by performing the following steps:

1) Navigate to the _existing_ CasCADe installation and make copies of the collections to migrate. Replace mm10 with your genome version, if it is different, and define a directory where the database files should be output. 
```
 mongodump --db=mm10 --collection=gRNAResultCollection -o <output_directory>
 mongodump --db=mm10 --collection=primerCollection -o <output_directory>
```
This will place the .bson and .json files into a folder in your specified output directory. Transfer this folder to the new CasCADe installation if it is on a different machine.

2) On the server hosting the new CasCADe, run:
```
 mongorestore --db=mm10 --collection gRNAResultCollection <path_to_transferred_folder>/gRNAResultCollection.bson
 mongorestore --db=mm10 --collection primerCollection <path_to_transferred_folder>/primerCollection.bson
```
3) After restoring the database, the database documents need to be converted to the new format via a Python script:
```
cd /var/www/html/CasCADe
sudo python3 customPython/MongoConverter.py
```
4) Finally, the GFF files need to be re-written for the JBrowse tracks by a python script:
```
sudo python customPython/MongoHandler.py mm10
```

Your existing Primer and Guide designs should now be accessible in the new CasCADe installation!

## Troubleshooting

If you encounter issues installing or using CasCADe, raise a GitHub Issue or send an email to hillary(dot)elrick(at)sickkids(dot)ca
