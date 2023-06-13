#!/usr/bin/python3.7

import csv, sys
from Config3 import Config


if __name__ == "__main__":
  db = Config(sys.argv[1])
  guides = db.guideCollection.find()
  with open("guides-%s.csv" % sys.argv[1], 'w') as f:
    writer = csv.DictWriter(f, fieldnames=list(guides[0].keys()) + ["pamLocation","org","dateAdded","commitHash","strand"])
    writer.writeheader()
    writer.writerows(guides)
  primers = db.primerCollection.find()
  with open("primers-%s.csv" % sys.argv[1], 'w') as f:
    writer = csv.DictWriter(f, fieldnames=list(primers[0].keys()) + ["pamLocation","org","dateAdded","commitHash","strand"])
    writer.writeheader()
    writer.writerows(primers)
