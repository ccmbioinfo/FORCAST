FROM ubuntu:16.04
LABEL maintainer="hillary.elrick@sickkids.ca"
ENV DEBIAN_FRONTEND noninteractive

# INSTALL BASE REQUIREMENTS
RUN apt-get update && \
    apt-get install -y git sudo apache2 && \
    cd /var/www/html && \
    rm index.html

# CHANGE DOCUMENT ROOT
WORKDIR /etc/apache2/sites-available
RUN sed -i -e "/DocumentRoot/a \ \t\<Directory \'\/var\/www\/html\'\>\n\t\tOptions +ExecCGI\n\t\tAddHandler cgi-script .py\n\t\tAllow from all\n\t</Directory\>" 000-default.conf

# GET HOST CODE
COPY . /var/www/html/
WORKDIR /var/www/html/

# INSTALL DEPENDENCIES
RUN cd installation && \
    ./install_debian.sh /var/www/html && \
    ./setPermissions.sh
