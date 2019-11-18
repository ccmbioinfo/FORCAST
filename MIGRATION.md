### Migration from previous versions of CasCADe
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
