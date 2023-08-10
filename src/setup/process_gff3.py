#!/usr/bin/env python3.7

import os
import re
import sys


def process_gff3(input_filename: str) -> None:
    """
    Adds "chr" to the chromosome column and also copies the ensembl phase information from exon lines to CDS lines for JBrowse
    """
    name, ext = os.path.splitext(input_filename)
    output_filename = name + ".processed" + ext
    all_exons = {}

    # slurp file first
    with open(input_filename, "r") as in_file:
        for line in in_file:
            fields = line.split("\t")
            if len(fields) == 9 and fields[2] == "exon":
                transcript_match = re.search("transcript:(.+?);", fields[8])
                if transcript_match is not None and len(transcript_match.groups()) == 1:
                    transcript = transcript_match.group(1)
                    if transcript not in all_exons:
                        all_exons[transcript] = {}
                    if fields[3] not in all_exons[transcript]:
                        all_exons[transcript][fields[3]] = {}
                    if fields[4] not in all_exons[transcript][fields[3]]:
                        all_exons[transcript][fields[3]][fields[4]] = {}

                    exon = all_exons[transcript][fields[3]][fields[4]]
                    ensembl_end_phase = re.search("ensembl_end_phase=(.+?);", fields[8])
                    if (
                        ensembl_end_phase is not None
                        and len(ensembl_end_phase.groups()) == 1
                    ):
                        exon["ensembl_end_phase"] = ensembl_end_phase.group(0)

                    ensembl_phase = re.search("ensembl_phase=(.+?);", fields[8])
                    if ensembl_phase is not None and len(ensembl_phase.groups()) == 1:
                        exon["ensembl_phase"] = ensembl_phase.group(0)

    # now process the file
    with open(input_filename, "r") as in_file, open(output_filename, "w") as out_file:
        for line in in_file:
            fields = line.split("\t")
            if len(fields) == 9:
                # if this line is not a header line
                if not fields[0].lower().startswith("chr"):
                    # add chr to the first field if it doesnt start with a chr
                    fields[0] = "chr" + fields[0]
                if fields[2] == "CDS":
                    # if the line is CDS, add the ensembl end phase and start phase to the line by matching it to the exon_dict dictionary
                    transcript_match = re.search("transcript:(.+?);", fields[8])
                    if (
                        transcript_match is not None
                        and len(transcript_match.groups()) == 1
                    ):
                        transcript = transcript_match.group(1)
                        if transcript in all_exons:
                            # loop over the exon entries in the exon_dict for this transcript:
                            for start_pos in all_exons[transcript].keys():
                                for end_pos in all_exons[transcript][start_pos].keys():
                                    # if exon start or end position is the same as this CDS or if the exon completely includes the CDS:
                                    if (
                                        int(start_pos) == int(fields[3])
                                        or int(end_pos) == int(fields[4])
                                        or (
                                            int(start_pos) < int(fields[3])
                                            and int(end_pos) > int(fields[4])
                                        )
                                    ):
                                        exon = all_exons[transcript][start_pos][end_pos]
                                        fields[8] = (
                                            exon["ensembl_end_phase"]
                                            + exon["ensembl_phase"]
                                            + fields[8]
                                        )
            out_file.write("\t".join(fields))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for file in sys.argv[1:]:
            print(f"Processing {file}...", file=sys.stderr)
            process_gff3(file)
    else:
        print(f"Usage: {sys.argv[0]} <file.gff3> [...additional.gff3]", file=sys.stderr)
        exit(1)
