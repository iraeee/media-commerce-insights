#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
decompress_db.py
GitHub Actions에서 압축된 DB 해제용
"""

import os
import sys

try:
    import zstandard as zstd
except ImportError:
    print("ERROR: zstandard not installed")
    sys.exit(1)

def decompress_db():
    """schedule.db.zst를 schedule.db로 압축 해제"""
    
    if not os.path.exists('schedule.db.zst'):
        print("No compressed DB found (schedule.db.zst)")
        return False
    
    print("Decompressing schedule.db.zst...")
    
    try:
        with open('schedule.db.zst', 'rb') as compressed:
            dctx = zstd.ZstdDecompressor()
            decompressed_data = dctx.decompress(compressed.read())
        
        with open('schedule.db', 'wb') as output:
            output.write(decompressed_data)
        
        original_size = os.path.getsize('schedule.db.zst') / (1024 * 1024)
        decompressed_size = os.path.getsize('schedule.db') / (1024 * 1024)
        
        print(f"Decompressed: {original_size:.1f}MB -> {decompressed_size:.1f}MB")
        return True
        
    except Exception as e:
        print(f"Decompression failed: {e}")
        return False

if __name__ == "__main__":
    decompress_db()
