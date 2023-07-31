FROM ubuntu/apache2:2.4-20.04_beta
# Match Docker expectations for logging like the Docker Library nginx image
RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stderr /var/log/apache2/error.log && \
    # Enable Common Gateway Interface scripts that comprise much of FORCAST's backend
    a2enmod cgi && \
    # Enable mod_rewrite for the / homepage redirect
    a2enmod rewrite && \
    # Disable directory listings. This is a core module, which requires --force
    a2dismod --force autoindex
RUN apt-get update -y && \
    # needed to add deadsnakes/ppa repo for Python 3.7
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update -y && \
    apt install -y \
    # MongoDB 3.6 for storing guides and primers
    mongodb \
    # General downloads here, unzip JBrowse
    ca-certificates curl unzip \
    # Convenient downloads for Dicey from GEAR Genomics Tracy
    wget rename \
    # FORCAST uses both Python 2 and 3.7 for some reason
    python python3.7 python3-pip python3.7-distutils \
    # Bioinformatics tools used when installing new genomes
    bwa bedtools samtools ncbi-blast+ \
    # FORCAST primer design feature after setup
    primer3 && \
    # Remove lists pulled by apt update for consistent images
    rm -rf /var/lib/apt/lists/* && \
    # python-pip is no longer included in the distribution as Python 2 is out of support
    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py | python
# Add a dummy sudo script as src/setup/load.sh uses sudo;
# the Docker container runs as the root user, but sudo is needed for src/setup/load.sh in local FORCAST installations
RUN echo "#!/bin/bash\n\$@" > /usr/bin/sudo && \
    chmod +x /usr/bin/sudo
RUN mkdir -p /var/www/html/bin
# In-silico PCR tool for primer design
RUN curl -Lo /var/www/html/bin/dicey https://github.com/gear-genomics/dicey/releases/download/v0.1.8/dicey_v0.1.8_linux_x86_64bit && \
    chmod +x /var/www/html/bin/dicey && \
    ln -s /var/www/html/bin/dicey /usr/local/bin/dicey
# UCSC Genome Browser kent binaries
RUN curl -Lo /var/www/html/bin/faToTwoBit https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faToTwoBit \
    -Lo /var/www/html/bin/twoBitToFa https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/twoBitToFa && \
    chmod +x /var/www/html/bin/faToTwoBit /var/www/html/bin/twoBitToFa && \
    ln -s /var/www/html/bin/faToTwoBit /usr/local/bin/faToTwoBit && \
    ln -s /var/www/html/bin/twoBitToFa /usr/local/bin/twoBitToFa
RUN curl -LO https://github.com/GMOD/jbrowse/releases/download/1.12.5-release/JBrowse-1.12.5.zip && \
    unzip JBrowse-1.12.5.zip && \
    mv JBrowse-1.12.5 /var/www/html/jbrowse && \
    rm JBrowse-1.12.5.zip && \
    cd /var/www/html/jbrowse && ./setup.sh && \
    # Default FORCAST configuration for JBrowse. jbrowse/data/datasets.conf is mounted as a volume inside docker-compose.yaml for editing.
    bash -c "echo -e 'classicMenu = true\ninclude += data/datasets.conf\n\n[aboutThisBrowser]\ntitle = FORCAST' >> /var/www/html/jbrowse/jbrowse.conf" && \
    # Add favicon
    sed -i '6i\    <link rel="icon" href="../docs/img/crispr-icon.png" sizes="100x100">' /var/www/html/jbrowse/index.html
# Dependencies for FORCAST CGI scripts + inDelphi
# Python 2
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pymongo==3.12.3 requests==2.27.1
# Python 3.7
RUN python3.7 -m pip install --upgrade pip && \
    python3.7 -m pip install --no-cache-dir pymongo==3.12.3 Jinja2==2.8 markupsafe==2.0.1 pandas==0.23.4 scikit-learn==0.20.0 scipy==1.1.0 numpy==1.15.3
COPY config-template /var/www/html/config
WORKDIR /var/www/html
# Replace the /usr/sbin/apachectl script that is called with the Apache master process that respects signals
ENV APACHE_HTTPD exec /usr/sbin/apache2
CMD chmod 777 ./src/guide-finder/core ./src/guide-finder/logs ./src/guide-finder/tempfiles ./src/primer-design/files/* && \
    mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /var/lib/mongodb && \
    exec apache2-foreground