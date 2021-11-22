FROM ubuntu/apache2:2.4-20.04_beta

RUN ln -sf /dev/stdout /var/log/apache2/access.log && ln -sf /dev/stderr /var/log/apache2/error.log && a2enmod cgi
RUN apt update -y && apt install -y mongodb ca-certificates curl python python3-pip && rm -rf /var/lib/apt/lists/* && curl https://bootstrap.pypa.io/pip/2.7/get-pip.py | python 
RUN pip install --no-cache-dir numpy==1.11.2 pymongo==3.8.0 requests==2.22.0 && pip3 install --no-cache-dir numpy==1.17.2 pymongo==3.8.0 requests==2.20.0 Jinja2==2.10.1 GitPython==3.0.5

CMD service mongodb start && exec apache2-foreground
# Install JBrowse
# Install GuideFinder dependencies?
# Install Primer3, NCBI Blast, Dicey



#FROM ubuntu:16.04
#LABEL maintainer="hillary.elrick@sickkids.ca"
#ENV DEBIAN_FRONTEND noninteractive

# INSTALL BASE REQUIREMENTS
#RUN apt-get update && \
#    apt-get install -y git sudo apache2 && \
#    cd /var/www/html && \
#    rm index.html

# CHANGE DOCUMENT ROOT AND SERVERNAME
#WORKDIR /etc/apache2
#RUN sed -i -e "/DocumentRoot/a \ \t\<Directory \'\/var\/www\/html\'\>\n\t\tOptions +ExecCGI\n\t\tAddHandler cgi-script .py\n\t\tAllow from all\n\t</Directory\>" sites-available/000-default.conf
#RUN sed -i '1 i\ServerName FORCAST' apache2.conf

# GET HOST CODE
#COPY . /var/www/html/
#WORKDIR /var/www/html/

# INSTALL DEPENDENCIES
#RUN cd src/installation && \
#    ./install.sh /var/www/html && \
#    ./setPermissions.sh
