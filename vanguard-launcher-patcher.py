#!/usr/bin/env python3

import hashlib, json, mmap, shutil, struct, sys
from pathlib import Path
from urllib.parse import to_bytes

def main():
    launcher_path = Path(input("Enter path to EVE launcher"
          "\nThis should end with something along the lines of \"app-x.xx.x\" and contain \"eve-online.exe\""
          "\nFor example, with Steam this would probably be /path/to/steam/steamapps/common/Eve Online/app-x.xx.x/"
          "\n: ").strip())

    asar_path = launcher_path / "resources" / "app.asar"
    exe_path = launcher_path / "eve-online.exe"

    if not asar_path.exists():
        print("Couldn't find resources/app.asar")
        sys.exit(1)
    if not exe_path.exists():
        print("Couldn't find eve-online.exe")
        sys.exit(1)

    asar_backup_path = asar_path.with_suffix(".asar.bak")
    exe_backup_path = exe_path.with_suffix(".exe.bak")

    print("Renaming target files")
    if asar_backup_path.exists():
        print("Pre-existing asar backup found. Will patch a copy of that.")
    else:
        shutil.move(asar_path, asar_backup_path)

    if exe_backup_path.exists():
        print("Pre-existing exe backup found. Will patch a copy of that.")
    else:
        shutil.move(exe_path, exe_backup_path)

    #try:
    (original_hash, new_hash) = patch_asar(asar_backup_path, asar_path)

    patch_exe(exe_backup_path, exe_path, original_hash, new_hash)
    #except:
    # TODO: handle errors and restore backups

def update_offsets(header, start_point: int, delta: int):
    for name, node in header["files"].items():
        if "files" in node:
            update_offsets(node, start_point, delta)
        elif "offset" in node:
            offset = int(node["offset"])
            if offset > start_point:
                node["offset"] = str(offset + delta)

def patch_asar(original_path: Path, new_path: Path):
    original_file = open(original_path, "rb")

    # ridiculous asar format is:
    # 4 bytes for length of header_size
    # 4 bytes of header_size data
    # 4 bytes for length of header
    # 4 bytes for string length
    # actual header string

    original_file.seek(8)

    header_pickle_size = struct.unpack('I', original_file.read(4))[0]
    files_offset = header_pickle_size + 12

    original_header_length = struct.unpack('I', original_file.read(4))[0]
    original_header_bytes = original_file.read(original_header_length)

    header = json.loads(original_header_bytes.decode('utf-8'))

    index_file = header["files"][".webpack"]["files"]["main"]["files"]["index.js"]

    index_file_offset = int(index_file["offset"])

    original_file.seek(files_offset + index_file_offset, 0)
    original_index_file_size = index_file["size"]
    index_file_contents = original_file.read(original_index_file_size).decode("utf-8")

    index_file_contents = index_file_contents.replace(
        r".startProcess)(V,ie,{withDetails:!0}",
        r".startProcess)(V,ie,{withDetails:!0,useQuotes:!1}").encode("utf-8")

    new_index_file_size = len(index_file_contents)

    # TODO: error if nothing changed
    size_delta = new_index_file_size - original_index_file_size

    new_blocks = []
    block_size = index_file["integrity"]["blockSize"]
    for i in range(-(new_index_file_size // -block_size)):
        block_start = i * block_size
        h = hashlib.sha256(index_file_contents[block_start: block_start + block_size])
        new_blocks.append(h.hexdigest())
    index_file["integrity"]["blocks"] = new_blocks
    index_file["integrity"]["hash"] = hashlib.sha256(index_file_contents).hexdigest()

    update_offsets(header, index_file_offset, size_delta)
    index_file["size"] += size_delta
    new_header_bytes = json.dumps(header, separators=(',', ':')).encode("utf-8")
    new_header_length = len(new_header_bytes)

    new_header_length_aligned = new_header_length + ((4 - (new_header_length % 4)) % 4)

    new_file = open(new_path, 'wb')
    # size of header_size
    new_file.write((4).to_bytes(4, byteorder='little', signed=False))
    # header_size (size of pickle object)
    new_file.write((new_header_length_aligned + 8).to_bytes(4, byteorder='little', signed=False))
    # size of contents of header pickle
    new_file.write((new_header_length_aligned + 4).to_bytes(4, byteorder='little', signed=False))
    # length of string
    new_file.write(new_header_length.to_bytes(4, byteorder='little', signed=False))
    new_file.write(new_header_bytes)
    print(original_header_length)
    print(new_header_length)
    if new_header_length_aligned != new_header_length:
        new_file.write(b'\x00' * (new_header_length_aligned - new_header_length))

    original_file.seek(files_offset, 0)
    new_file.write(original_file.read(index_file_offset))

    new_file.write(index_file_contents)
    original_file.seek(original_file.tell() + original_index_file_size)

    # copy the rest of the contents
    shutil.copyfileobj(original_file, new_file)

    orig_header_hash = hashlib.sha256(original_header_bytes).hexdigest()
    new_header_hash = hashlib.sha256(new_header_bytes).hexdigest()

    print("asar patched.")
    return orig_header_hash, new_header_hash

def patch_exe(original_path: Path, new_path: Path, original_hash: str, new_hash: str):
    shutil.copy(original_path, new_path)
    with open(new_path, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        mm[:] = mm[:].replace(original_hash.encode("utf-8"), new_hash.encode("utf-8"))
        mm.close()
    print("exe patched.")

if __name__ == "__main__":
    main()
    sys.exit(0)
