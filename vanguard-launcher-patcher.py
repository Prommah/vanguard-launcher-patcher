#!/usr/bin/env python3

"""
get launcher path
parse asar header to find index.js
mutate in-place
change all offsets, recalculate hashes
replace old integrity hash in eve-online.exe
"""

import json, struct

def test(filename):
    asarfile = open(filename, 'rb')

    # ridiculous asar format is:
    # 4 bytes for length of header_size
    # 4 bytes of header_size data
    # 4 bytes for length of header
    # 4 bytes for string length
    # actual header string

    asarfile.seek(8)
    # pickle stuff is 4-byte-aligned, so easier to just read this as well
    header_pickle_size = struct.unpack('I', asarfile.read(4))[0]
    header_length = struct.unpack('I', asarfile.read(4))[0]
    header_str = asarfile.read(header_length).decode('utf-8')

    header = json.loads(header_str)

    index_file = header["files"][".webpack"]["files"]["main"]["files"]["index.js"]

    files_offset = header_pickle_size + 12

    index_file_offset = int(index_file["offset"])

    asarfile.seek(files_offset + index_file_offset, 0)
    index_file_contents = asarfile.read(index_file["size"]).decode("utf-8")

    index_file_contents = index_file_contents.replace(
        r".startProcess)(V,ie,{withDetails:!0}",
        r".startProcess)(V,ie,{withDetails:!0,useQuotes:!1}").encode("utf-8")
    
    size_delta = len(index_file_contents) - index_file["size"]
    print(size_delta)

test("resources/app.asar")
