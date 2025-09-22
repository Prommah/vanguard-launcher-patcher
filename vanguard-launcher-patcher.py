#!/usr/bin/env python3

"""
get launcher path
parse asar header to find index.js
mutate in-place
change all offsets, recalculate hashes
replace old integrity hash in eve-online.exe
"""

import hashlib, json, shutil, struct
from urllib.parse import to_bytes

def test(filename):
    asarfile = open(filename, 'rb')

    # ridiculous asar format is:
    # 4 bytes for length of header_size
    # 4 bytes of header_size data
    # 4 bytes for length of header
    # 4 bytes for string length
    # actual header string

    asarfile.seek(8)
    # pickle stuff is 4-byte-aligned, so easier to just read this
    header_pickle_size = struct.unpack('I', asarfile.read(4))[0]
    files_offset = header_pickle_size + 12

    header_length = struct.unpack('I', asarfile.read(4))[0]
    header_str = asarfile.read(header_length).decode('utf-8')

    header = json.loads(header_str)

    index_file = header["files"][".webpack"]["files"]["main"]["files"]["index.js"]

    index_file_offset = int(index_file["offset"])

    asarfile.seek(files_offset + index_file_offset, 0)
    index_file_original_size = index_file["size"]
    index_file_contents = asarfile.read(index_file_original_size).decode("utf-8")

    index_file_contents = index_file_contents.replace(
        r".startProcess)(V,ie,{withDetails:!0}",
        r".startProcess)(V,ie,{withDetails:!0,useQuotes:!1}").encode("utf-8")

    size_delta = len(index_file_contents) - index_file_original_size

    new_blocks = []
    block_size = index_file["integrity"]["blockSize"]
    for i in range(-(len(index_file_contents) // -block_size)):
        block_start = i * block_size
        h = hashlib.sha256(index_file_contents[block_start : block_start + block_size])
        new_blocks.append(h.hexdigest())
    index_file["integrity"]["blocks"] = new_blocks
    index_file["integrity"]["hash"] = hashlib.sha256(index_file_contents).hexdigest()

    update_offsets(header, index_file_offset, size_delta)
    index_file["size"] += size_delta
    new_header = json.dumps(header, separators=(',', ':')).encode('utf-8')
    new_header_length = len(new_header)
    header_size_delta = new_header_length - header_length

    new_header_length_aligned = new_header_length + ((4 - (new_header_length % 4)) % 4)

    new_file = open("app.asar.new", 'wb')
    new_file.write((4).to_bytes(4, byteorder='little', signed=False))
    new_file.write((new_header_length_aligned + 8).to_bytes(4, byteorder='little', signed=False))
    new_file.write((new_header_length_aligned + 4).to_bytes(4, byteorder='little', signed=False))
    new_file.write(new_header_length.to_bytes(4, byteorder='little', signed=False))
    new_file.write(new_header)
    if new_header_length_aligned != new_header_length:
        new_file.write(b'\x00' * (new_header_length_aligned - new_header_length))

    asarfile.seek(files_offset, 0)
    new_file.write(asarfile.read(index_file_offset))

    new_file.write(index_file_contents)
    asarfile.seek(asarfile.tell() + index_file_original_size)

    shutil.copyfileobj(asarfile, new_file)


def update_offsets(header, start_point: int, delta: int):
    for name, node in header["files"].items():
        if "files" in node:
            update_offsets(node, start_point, delta)
        elif "offset" in node:
            offset = int(node["offset"])
            if offset > start_point:
                node["offset"] = str(offset + delta)

test("resources/app.asar")
