FROM ubuntu/apache2:2.4-20.04_beta
# Match Docker expectations for logging like the Docker Library nginx image
RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stderr /var/log/apache2/error.log && \
# Enable Common Gateway Interface scripts that comprise much of FORCAST's backend
    a2enmod cgi
RUN apt update -y && \
    apt install -y \
# MongoDB 3.6 for storing guides and primers
        mongodb \
# General downloads here, unzip JBrowse
        ca-certificates curl unzip \
# Convenient downloads for Dicey from GEAR Genomics Tracy
        wget rename \
# FORCAST uses both Python 2 and 3 for some reason
        python python3-pip \
# Bioinformatics tools used when installing new genomes
        bwa bedtools samtools ncbi-blast+ \
# FORCAST primer design feature after setup
        primer3 && \
# Remove lists pulled by apt update for consistent images
    rm -rf /var/lib/apt/lists/* && \
# python-pip is no longer included in the distribution as Python 2 is out of support
    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py | python
RUN curl -Lo /usr/local/bin/dicey https://github.com/gear-genomics/dicey/releases/download/v0.1.8/dicey_v0.1.8_linux_x86_64bit && \
    chmod +x /usr/local/bin/dicey
ARG JBROWSE_VERSION=1.12.3
RUN curl -LO https://jbrowse.org/releases/JBrowse-${JBROWSE_VERSION}/JBrowse-${JBROWSE_VERSION}.zip && \
    unzip JBrowse-${JBROWSE_VERSION}.zip && \
    mv JBrowse-${JBROWSE_VERSION} /var/www/html/jbrowse && \
    rm JBrowse-${JBROWSE_VERSION}.zip && \
    cd /var/www/html/jbrowse && ./setup.sh
RUN pip install --no-cache-dir pymongo==3.8.0 requests==2.22.0 && \
    pip3 install --no-cache-dir pymongo==3.8.0 requests==2.20.0 Jinja2==3.1.2
RUN curl -Lo /usr/local/bin/faToTwoBit https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faToTwoBit \
         -Lo /usr/local/bin/twoBitToFa https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/twoBitToFa && \
    chmod +x /usr/local/bin/faToTwoBit /usr/local/bin/twoBitToFa
COPY config-template /var/www/html/config
WORKDIR /var/www/html
RUN echo -e "classicMenu = true\ninclude += data/datasets.conf\n\n[aboutThisBrowser]\ntitle = FORCAST" >> jbrowse/jbrowse.conf
RUN a2enmod rewrite
CMD service mongodb start && exec apache2-foreground
