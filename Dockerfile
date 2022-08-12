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
# In-silico PCR tool for primer design
RUN curl -Lo /usr/local/bin/dicey https://github.com/gear-genomics/dicey/releases/download/v0.1.8/dicey_v0.1.8_linux_x86_64bit && \
    chmod +x /usr/local/bin/dicey
# UCSC Genome Browser kent binaries
RUN curl -Lo /usr/local/bin/faToTwoBit https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faToTwoBit \
    -Lo /usr/local/bin/twoBitToFa https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/twoBitToFa && \
    chmod +x /usr/local/bin/faToTwoBit /usr/local/bin/twoBitToFa
RUN curl -LO https://github.com/GMOD/jbrowse/releases/download/1.12.5-release/JBrowse-1.12.5.zip && \
    unzip JBrowse-1.12.5.zip && \
    mv JBrowse-1.12.5 /var/www/html/jbrowse && \
    rm JBrowse-1.12.5.zip && \
    cd /var/www/html/jbrowse && ./setup.sh && \
    # Default FORCAST configuration for JBrowse. jbrowse/data/datasets.conf is bind-mounted for editing.
    echo -e "classicMenu = true\ninclude += data/datasets.conf\n\n[aboutThisBrowser]\ntitle = FORCAST" >> /var/www/html/jbrowse/jbrowse.conf && \
    # Add favicon
    sed -i '6i\    <link rel="icon" href="../docs/img/crispr-icon.png" sizes="100x100">' /var/www/html/jbrowse/index.html
# Dependencies for FORCAST CGI scripts + inDelphi
RUN pip install --no-cache-dir pymongo==3.12.3 requests==2.27.1 && \
    pip3 install --no-cache-dir pymongo==3.12.3 requests==2.27.1 Jinja2==3.1.2 pandas=0.23.4 scikit-learn=0.20.0 scipy=1.1.0 numpy=1.15.3
COPY config-template /var/www/html/config
WORKDIR /var/www/html
# Replace the /usr/sbin/apachectl script that is called with the Apache master process that respects signals
ENV APACHE_HTTPD exec /usr/sbin/apache2
CMD service mongodb start && exec apache2-foreground
