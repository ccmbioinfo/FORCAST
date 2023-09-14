# Finding, Optimizing, and Reporting Cas Targets (FORCAST)

A fully-integrated and open-source pipeline to design CRISPR mutagenesis experiments.

## Contents

- [Hardware Requirements](#hardware-requirements)
- [Installing with Docker](#installing-with-docker)
  - [Setup](#setup)
  - [Production environment](#for-production-environment-using-stable-tagged-docker-image)
  - [Staging environment](#for-staging-environment-using-latest-tagged-docker-image)
  - [Local development environment](#for-local-development-environment-using-locally-built-docker-image)
- [Customization](#customization)
- [Migration](#migration)
- [Citation](#citation)
- [Troubleshooting](#troubleshooting)

## Hardware Requirements

Minimum 8 GB RAM, 100 GB available storage

Storage should expand as needed to store however many genome assemblies you wish to work with.

## Installing with Docker

### Setup

On the host computer or server, install the [Docker Engine](https://docs.docker.com/engine/install/) and, if you are not using Docker Desktop, [Docker Compose](https://docs.docker.com/compose/install/linux/) on Linux. Note the licensing requirements for
Docker Desktop, though the Docker Engine and Compose for Linux remain free and open source.

Clone this repository:

```bash
git clone https://github.com/ccmbioinfo/FORCAST.git
```

Navigate to the cloned repository folder, copy the sample `config-sample` directory and `datasets.sample.conf` file, build the Docker image, and start the service container.

```bash
cp apache2/sites-enabled/sample/* apache2/sites-enabled && cp -r config-sample config && cp jbrowse/data/datasets.sample.conf jbrowse/data/datasets.conf
```

#### SSL certificate (for production and staging environment)

Copy the relevant SSL certificate files into the `apache2/certs` directory and modify the `forcast-ssl.conf` file accordingly (e.g., modify the `SSLCertificateFile`, `SSLCertificateKeyFile`, and `SSLCertificateChainFile` directives where applicable). Note that the `apache2/certs` directory is mounted as a volume at `/etc/apache2/certs` inside `docker-compose-dev.yaml` and `docker-compose-prod.yaml`.

### For production environment (using `stable` tagged Docker image)

To start and run the FORCAST Docker container:

```bash
docker compose -f docker-compose-prod.yaml up
```

To stop and remove the FORCAST Docker container:

```bash
docker compose -f docker-compose-prod.yaml down
```

### For staging environment (using `latest` tagged Docker image)

To start and run the FORCAST Docker container:

```bash
docker compose -f docker-compose-dev.yaml up
```

To stop and remove the FORCAST Docker container:

```bash
docker compose -f docker-compose-dev.yaml down
```

### For local development environment (using locally built Docker image)

To start and run the FORCAST Docker container:

```bash
docker compose up
```

To stop and remove the FORCAST Docker container:

```bash
docker compose down
```

---

FORCAST should now be available on `localhost:80` or port 80 (and `localhost:443` or port 443 if you are running FORCAST in a staging or production) of the hosting machine.

Genomes are downloaded from Ensembl. For a full list from the current release, see [Ensembl](https://ftp.ensembl.org/pub/current_fasta/).
Not all of these have been tested with FORCAST. Please keep in mind the Ensembl release version
(106, as of writing), the species of organism, and the assembly name for the following step to
download the assembly and install for FORCAST. This performs all steps necessary to index the
assemblies and load tracks into JBrowse. Depending on the size of the genome, this could take
several hours to complete.

```bash
docker compose exec forcast ./src/setup/setup.sh ENSEMBL_RELEASE Organism_name ASSEMBLY
```

**Tested examples**

```bash
docker compose exec forcast ./src/setup/setup.sh 106 Saccharomyces_cerevisiae R64-1-1
docker compose exec forcast ./src/setup/setup.sh 102 Mus_musculus GRCm38
docker compose exec forcast ./src/setup/setup.sh 109 Mus_musculus GRCm39
docker compose exec forcast ./src/setup/setup.sh 106 Homo_sapiens GRCh38
```

_Drosophila melanogaster_ is known to not install properly due to using a different naming scheme.

## Customization

### Custom Primer Design Settings

First, go to to [the primer3 website](http://bioinfo.ut.ee/primer3/) and enter the custom settings that you would like to use for the first attempt of primer design and click 'Download Settings' to save the file. Additionally, you may also specify and download 'retry attempt' settings to be used if no primers are found with the default settings. There is no limit to the number of retry attempts you can define.

Once all the settings files have been generated, ssh into the server hosting FORCAST and navigate to where the application is rooted (e.g. `/var/www/html/FORCAST`). Within the `config` directory there should be a `primer3settings.conf` file and a directory, `primer3settings`, where the default primer3 settings are stored. Replace these with your custom settings and edit the `primer3settings.conf` file to point to the new files like so:

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

| Shortform     | PAM    | PamLocation | MinGuideLength | MaxGuideLength | DefaultGuideLength | SeedRegion | Cleaves | OffTargetPAMs          | Scores   |
| ------------- | ------ | ----------- | -------------- | -------------- | ------------------ | ---------- | ------- | ---------------------- | -------- |
| SpCas9 (NGG)  | NGG    | downstream  | 17             | 20             | 20                 | -12        | -3      | NGG, NAG               | MIT, CFD |
| AsCpf1/Cas12a | TTTV   | upstream    | 20             | 23             | -                  | +6         | +19,+23 | TTTV, TTTT, CTTA, TTCA | -        |
| ScCas9 (NNG)  | NNG    | downstream  | 20             | 20             | -                  | -12        | -3      | NNG                    | -        |
| ScCas9 (NNGT) | NNGT   | downstream  | 20             | 20             | -                  | -12        | -3      | NNGT                   | -        |
| SaCas9        | NNGRRT | downstream  | 21             | 23             | -                  | -8         | -3      | NNGRRT, NNGRR          | -        |

However, we recognize that these settings and defaults may not be applicable to all users. New RGENs can be added by specifying the RGEN parameters in the template below and appending to the `rgens.json` file.

```
{"rgenID" : "6", "Shortform" : "<shortform>", "Longform" : "<optional>", "PAM" : "<nucleotide sequence>", "PamLocation" : "<downstream or upstream>", "MinGuideLength" : "<required>", "MaxGuideLength" : "<required>", "DefaultGuideLength": "<optional>", "SeedRegion" : "<direction and length of seed>", "Cleaves" : [ "<cleavage site>" ], "OffTargetPAMS" : [ "<actual PAM>", "<optional off-targets>" ], "Scores" : []}
```

Existing RGENs can have their settings and defaults modified in the file as well. In order to keep existing guides associated to their RGENs, it's recommended that the rgenIDs remain unchanged for existing entries.

After modifying the `rgens.json` file, you can run the `load_RGENs.py` script in the same directory (`python3 load_RGENS.py`) and provide the desired command-line argument:

- `update`: modifies existing records based on the rgenID and adds new RGENs to the database (recommended)
- `replace`: wipes and replaces RGEN database with new entries, potentially unlinking existing gRNA records from their RGEN.

## Migration

If using a previous version of FORCAST, existing Primers and Guides can be migrated to the new version by performing the following steps:

1. Navigate to the _existing_ FORCAST installation and make copies of the collections to migrate. Replace mm10 with your genome version, if it is different, and define a directory where the database files should be output.

```
 mongodump --db=mm10 --collection=gRNAResultCollection -o <output_directory>
 mongodump --db=mm10 --collection=primerCollection -o <output_directory>
```

This will place the .bson and .json files into a folder in your specified output directory. Transfer this folder to the new FORCAST installation if it is on a different machine.

2. On the server hosting the new FORCAST, run:

```
 mongorestore --db=mm10 --collection gRNAResultCollection <path_to_transferred_folder>/gRNAResultCollection.bson
 mongorestore --db=mm10 --collection primerCollection <path_to_transferred_folder>/primerCollection.bson
```

3. After restoring the database, the database documents need to be converted to the new format via a Python script:

```
python3 src/helpers/MongoConverter.py
```

4. Finally, the GFF files need to be re-written for the JBrowse tracks by a python script:

```
python src/helpers/MongoHandler.py mm10
```

Your existing Primer and Guide designs should now be accessible in the new FORCAST installation!

## Citation

<a href="https://doi.org/10.1101/2020.04.21.053090">

```
FORCAST: a fully integrated and open source pipeline to design Cas-mediated mutagenesis experiments
Hillary Elrick, Viswateja Nelakuditi, Greg Clark, Michael Brudno, Arun K. Ramani, Lauryl M.J. Nutter
bioRxiv 2020.04.21.053090; doi: https://doi.org/10.1101/2020.04.21.053090
```

</a>

## Troubleshooting

If you encounter issues installing or using FORCAST, raise a GitHub issue or start a GitHub discussion.
