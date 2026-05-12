#!/usr/bin/env python3
"""
MHFU ISO Extraction Tool

Extracts and decrypts game files from Monster Hunter PSP ISOs.

Usage:
    python extract_iso.py <iso_path> <output_dir>
"""

import os
import sys
import struct
import hashlib
from pathlib import Path

# Add mhef and mhff to path
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR / 'mhef'))
sys.path.insert(0, str(TOOLS_DIR / 'mhff'))

try:
    import pycdlib
except ImportError:
    print("ERROR: pycdlib not installed. Run: pip install pycdlib")
    sys.exit(1)

# Known ISO hashes
KNOWN_ISOS = {
    '1f76ee9ccbd6d39158f06e6e5354a5bd': ('MHP2G', 'UMD'),
    'cc39d070b2d2c44c9ac8187e00b75dc4': ('MHP2G', 'PSN'),
}


def calculate_md5(filepath):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def extract_iso(iso_path, output_dir):
    """Extract all files from an ISO."""
    print(f"Opening ISO: {iso_path}")

    iso = pycdlib.PyCdlib()
    iso.open(iso_path)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract all files
    for dirname, dirlist, filelist in iso.walk(iso_path='/'):
        for filename in filelist:
            iso_filepath = f"{dirname}/{filename}".replace('//', '/')
            local_filepath = output_path / iso_filepath.lstrip('/')

            local_filepath.parent.mkdir(parents=True, exist_ok=True)

            print(f"  Extracting: {iso_filepath}")
            with open(local_filepath, 'wb') as f:
                iso.get_file_from_iso_fp(f, iso_path=iso_filepath)

    iso.close()
    print(f"\nExtracted to: {output_dir}")


def decrypt_data_bin(data_bin_path, output_path, game='MHP2G'):
    """Decrypt DATA.BIN using mhef."""
    try:
        from mhef.psp import DataCipher
    except ImportError:
        print("ERROR: mhef not properly installed")
        print("Run: cd tools/mhef && pip install -e .")
        return False

    print(f"Decrypting: {data_bin_path}")

    cipher = DataCipher(DataCipher.MHP2G if game == 'MHP2G' else DataCipher.MHP3)

    with open(data_bin_path, 'rb') as f:
        encrypted = f.read()

    print(f"  File size: {len(encrypted):,} bytes")
    print("  Decrypting (this may take a while)...")

    decrypted = cipher.decrypt(encrypted)

    with open(output_path, 'wb') as f:
        f.write(decrypted)

    print(f"  Decrypted to: {output_path}")
    return True


def extract_data_bin(data_bin_path, output_dir):
    """Extract files from decrypted DATA.BIN."""
    print(f"Extracting DATA.BIN contents...")

    with open(data_bin_path, 'rb') as f:
        data = f.read()

    # Read TOC
    toc_size_mult = struct.unpack('<I', data[0:4])[0]
    toc_size = toc_size_mult * 2048

    toc = []
    for i in range(4, toc_size, 4):
        if i + 4 > len(data):
            break
        toc.append(struct.unpack('<I', data[i:i+4])[0])

    # Find file count
    file_size_blocks = len(data) // 2048
    file_count = 0
    for i, entry in enumerate(toc):
        if entry >= file_size_blocks:
            file_count = i
            break

    print(f"  Found {file_count} files")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract files
    for i in range(file_count):
        start_block = toc[i]
        end_block = toc[i + 1] if i + 1 < len(toc) else file_size_blocks

        start_byte = start_block * 2048
        end_byte = end_block * 2048

        file_data = data[start_byte:end_byte]

        # Determine file extension based on magic bytes
        ext = detect_file_type(file_data)
        filename = f"file_{i:05d}{ext}"

        with open(output_path / filename, 'wb') as f:
            f.write(file_data)

        if i % 100 == 0:
            print(f"  Extracted {i}/{file_count} files...")

    print(f"  Extracted all {file_count} files to: {output_dir}")


def detect_file_type(data):
    """Detect file type from magic bytes."""
    if len(data) < 8:
        return '.bin'

    if data[0:8] == b'.TMH0.14':
        return '.tmh'
    elif data[0:4] == b'PSMF':
        return '.pmf'  # Video
    elif data[0:4] == b'RIFF':
        return '.wav'  # Audio
    elif data[0:3] == b'VAG':
        return '.vag'  # PSP Audio

    # Check for PMO (no clear magic, check structure)
    # PMO files have specific patterns in header

    return '.bin'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nExamples:")
        print("  python extract_iso.py game.iso ./extracted")
        print("  python extract_iso.py --decrypt DATA.BIN DATA_decrypted.BIN")
        print("  python extract_iso.py --extract-data DATA_decrypted.BIN ./files")
        sys.exit(1)

    if sys.argv[1] == '--decrypt':
        if len(sys.argv) < 4:
            print("Usage: python extract_iso.py --decrypt <input> <output>")
            sys.exit(1)
        decrypt_data_bin(sys.argv[2], sys.argv[3])

    elif sys.argv[1] == '--extract-data':
        if len(sys.argv) < 4:
            print("Usage: python extract_iso.py --extract-data <data.bin> <output_dir>")
            sys.exit(1)
        extract_data_bin(sys.argv[2], sys.argv[3])

    else:
        iso_path = sys.argv[1]
        output_dir = sys.argv[2]

        # Verify ISO
        print("Calculating ISO hash...")
        iso_hash = calculate_md5(iso_path)
        print(f"MD5: {iso_hash}")

        if iso_hash in KNOWN_ISOS:
            game, source = KNOWN_ISOS[iso_hash]
            print(f"Identified: {game} ({source})")
        else:
            print("WARNING: Unknown ISO hash. Proceeding anyway...")

        # Extract ISO
        extract_iso(iso_path, output_dir)


if __name__ == '__main__':
    main()
