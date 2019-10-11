#!/bin/bash

chgrp www-data ./python/*.cgi
chmod g+rwx ./python/*.cgi

chgrp www-data ./python/*.py
chmod g+rwx ./python/*.py

chgrp www-data ./python/web/ajaxCalls/*
chmod g+rwx ./python/web/ajaxCalls/*

chgrp -R www-data ./python/files
chmod -R g+rw ./python/files

chgrp -R www-data ./python/classes/geneStorage
chmod -R g+rw ./python/classes/geneStorage






