#!/usr/bin/python3.7

import csv, sys
from pprint import pprint
from typing import Dict
from pymongo.errors import BulkWriteError
from Config import Config


def pop(d: Dict[str, str]) -> Dict[str, str]:
    d.pop("_id", None)
    return d


def reset_guides(d: Dict[str, str]) -> Dict[str, str]:
    d["guides"] = { "rank": "manual", "ids": [] }
    return d


if __name__ == "__main__":
  db = Config(sys.argv[1])
  if sys.argv[2] == "guides":
    with open(sys.argv[3]) as f:
      reader = csv.DictReader(f)
      results = [pop(d) for d in reader]
      try:
        db.guideCollection.insert_many(results)
      except BulkWriteError as e:
        pprint(e.details)
  elif sys.argv[2] == "primers":
    with open(sys.argv[3]) as f:
      reader = csv.DictReader(f)
      results = [reset_guides(pop(d)) for d in reader]
      try:
        db.primerCollection.insert_many(results)
      except BulkWriteError as e:
        pprint(e.details)
