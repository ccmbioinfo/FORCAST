#!/usr/bin/env python3

import os, sys


def process_fasta(input_filename: str) -> None:
    """
    Adds "chr" to the genome fasta file and removes text after the first space in the header
    """
    name, ext = os.path.splitext(input_filename)
    output_filename = name + ".processed" + ext
    with open(input_filename, "r") as in_file, open(output_filename, "w") as out_file:
        for line in in_file:
            if line.startswith(">"):
                # disregard any text in header after a white space.
                tmpList = line.split(" ")
                if "chr" in tmpList[0].lower():
                    out_file.write(tmpList[0] + "\n")
                else:
                    # ">" + chr + chromosome number
                    out_file.write(tmpList[0][0] + "chr" + tmpList[0][1:] + "\n")
            else:
                out_file.write(line)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for file in sys.argv[1:]:
            print(f"Processing {file}...", file=sys.stderr)
            process_fasta(file)
    else:
        print(f"Usage: {sys.argv[0]} <file.fa> [...additional.fa]", file=sys.stderr)
        exit(1)
