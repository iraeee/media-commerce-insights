#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compress_and_backup.py - DB 무조건 삭제 버전
"""

import os
import glob
from datetime import datetime

try:
    import zstandard as zstd
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "zstandard"])
    import zstandard as zstd

def compress_file(input_file, output_file, level=3):
    """파일을 zstandard로 압축"""
    print(f"📦 압축 중: {input_file} → {output_file}")
    
    with open(input_file, 'rb') as f_in:
        data = f_in.read()
    
    cctx = zstd.ZstdCompressor(level=level)
    compressed = cctx.compress(data)
    
    with open(output_file, 'wb') as f_out:
        f_out.write(compressed)
    
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    compressed_size = os.path.getsize(output_file) / (1024 * 1024)
    ratio = (1 - compressed_size / original_size) * 100
    
    print(f"✅ 압축 완료: {original_size:.1f}MB → {compressed_size:.1f}MB ({ratio:.1f}% 감소)")

def main():
    print("="*50)
    print("🚀 DB 압축 스크립트")
    print("="*50)
    
    # 1. schedule.db가 있으면 압축
    if os.path.exists('schedule.db'):
        print("✅ schedule.db 발견")
        
        # 압축
        compress_file('schedule.db', 'schedule.db.zst')
        
        # 원본 무조건 삭제!!!
        print("🗑️ 원본 DB 삭제 중...")
        try:
            os.remove('schedule.db')
            print("✅ 원본 삭제 완료! (압축본만 유지)")
        except Exception as e:
            print(f"❌ 삭제 실패: {e}")
            # 실패해도 다시 시도
            import time
            time.sleep(1)
            try:
                os.remove('schedule.db')
                print("✅ 재시도 성공!")
            except:
                print("❌ 삭제 최종 실패")
    else:
        print("⚠️ schedule.db 없음")
        if os.path.exists('schedule.db.zst'):
            print("✅ 압축본만 존재 (정상)")
    
    # 2. 최종 확인
    print("\n📊 최종 상태:")
    if os.path.exists('schedule.db'):
        print("❌ 경고: schedule.db가 여전히 존재!")
    if os.path.exists('schedule.db.zst'):
        size = os.path.getsize('schedule.db.zst') / (1024 * 1024)
        print(f"✅ schedule.db.zst: {size:.1f}MB")
    
    print("\n✅ 완료!")

if __name__ == "__main__":
    main()
