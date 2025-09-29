#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compress_and_backup.py
GitHub Actions에서 실행되는 압축 및 백업 스크립트
무조건 원본 DB는 삭제하고 압축본만 유지
"""

import os
import shutil
import glob
import re
from datetime import datetime, timedelta

try:
    import zstandard as zstd
except ImportError:
    print("ERROR: zstandard not installed. Installing...")
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
    
    # 크기 비교
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    compressed_size = os.path.getsize(output_file) / (1024 * 1024)
    ratio = (1 - compressed_size / original_size) * 100
    
    print(f"✅ 압축 완료: {original_size:.1f}MB → {compressed_size:.1f}MB ({ratio:.1f}% 감소)")
    return compressed_size

def create_backup():
    """현재 DB의 압축 백업 생성"""
    if not os.path.exists('schedule.db'):
        print("⚠️ schedule.db 파일이 없습니다.")
        return
    
    # backups 폴더 생성
    if not os.path.exists('backups'):
        os.makedirs('backups')
        print("📁 backups 폴더 생성")
    
    # 백업 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f'backups/schedule_backup_{timestamp}.db.zst'
    
    # 압축 백업 생성
    compress_file('schedule.db', backup_name)
    print(f"💾 백업 생성: {backup_name}")
    
    return backup_name

def clean_backups():
    """백업 파일 정리 - 5일 규칙 적용"""
    print("\n🧹 백업 정리 시작...")
    
    # 모든 백업 파일 가져오기
    backup_files = glob.glob('backups/schedule_backup_*.db.zst')
    
    if not backup_files:
        print("백업 파일이 없습니다.")
        return
    
    # 파일명에서 날짜 추출
    file_dates = {}
    for file in backup_files:
        match = re.search(r'schedule_backup_(\d{8})_(\d{6})\.db\.zst', file)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            file_datetime = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
            file_date = file_datetime.date()
            file_dates[file] = (file_date, file_datetime)
    
    # 날짜별로 그룹화
    date_groups = {}
    for file, (file_date, file_datetime) in file_dates.items():
        if file_date not in date_groups:
            date_groups[file_date] = []
        date_groups[file_date].append((file, file_datetime))
    
    today = datetime.now().date()
    files_to_keep = []
    files_to_delete = []
    
    for date, files in date_groups.items():
        days_old = (today - date).days
        files.sort(key=lambda x: x[1])  # 시간순 정렬
        
        if days_old == 0:
            # 오늘: 최신 3개만 유지
            if len(files) > 3:
                files_to_delete.extend([f[0] for f in files[:-3]])
                files_to_keep.extend([f[0] for f in files[-3:]])
            else:
                files_to_keep.extend([f[0] for f in files])
            print(f"📅 오늘 ({date}): {len(files)}개 중 최신 3개 유지")
            
        elif 1 <= days_old <= 5:
            # 1-5일 전: 가장 최신 1개만 유지
            files_to_delete.extend([f[0] for f in files[:-1]])
            files_to_keep.append(files[-1][0])
            print(f"📅 {days_old}일 전 ({date}): {len(files)}개 중 최신 1개 유지")
            
        else:
            # 6일 이상: 모두 삭제
            files_to_delete.extend([f[0] for f in files])
            print(f"📅 {days_old}일 전 ({date}): {len(files)}개 모두 삭제")
    
    # 파일 삭제
    for file in files_to_delete:
        try:
            os.remove(file)
            print(f"   🗑️ 삭제: {os.path.basename(file)}")
        except Exception as e:
            print(f"   ⚠️ 삭제 실패: {file} - {e}")
    
    print(f"\n📊 백업 정리 결과:")
    print(f"   - 유지: {len(files_to_keep)}개")
    print(f"   - 삭제: {len(files_to_delete)}개")
    
    # 현재 백업 상태 표시
    remaining_files = glob.glob('backups/schedule_backup_*.db.zst')
    if remaining_files:
        total_size = sum(os.path.getsize(f) for f in remaining_files) / (1024 * 1024)
        print(f"   - 총 백업 크기: {total_size:.1f}MB")

def compress_main_db():
    """메인 DB를 압축 버전으로 교체 - 무조건 원본 삭제"""
    if not os.path.exists('schedule.db'):
        print("⚠️ schedule.db 파일이 없습니다.")
        # 압축본만 있는지 확인
        if os.path.exists('schedule.db.zst'):
            print("✅ 이미 압축본만 존재합니다.")
        return
    
    print("\n🔄 메인 DB 압축...")
    
    # 압축
    compress_file('schedule.db', 'schedule.db.zst')
    
    # 원본 무조건 삭제!
    print("🗑️ 원본 DB 삭제 중...")
    try:
        os.remove('schedule.db')
        print("✅ 원본 DB 삭제 완료 (압축본만 유지)")
    except Exception as e:
        print(f"❌ 원본 삭제 실패: {e}")
        # 실패해도 계속 진행

def main():
    """메인 실행"""
    print("="*50)
    print("🚀 DB 압축 및 백업 스크립트")
    print("="*50)
    
    # GitHub Actions 환경 확인
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print("✅ GitHub Actions 환경 감지")
    else:
        print("ℹ️ 로컬 환경에서 실행 중")
    
    # 1. 백업 생성
    backup_file = create_backup()
    
    # 2. 백업 정리
    clean_backups()
    
    # 3. 메인 DB 압축 및 원본 삭제
    compress_main_db()
    
    # 4. 최종 상태 확인
    print("\n📊 최종 파일 상태:")
    if os.path.exists('schedule.db'):
        size = os.path.getsize('schedule.db') / (1024 * 1024)
        print(f"   ⚠️ schedule.db: {size:.1f}MB (삭제되어야 함!)")
    if os.path.exists('schedule.db.zst'):
        size = os.path.getsize('schedule.db.zst') / (1024 * 1024)
        print(f"   ✅ schedule.db.zst: {size:.1f}MB")
    
    print("\n✅ 완료!")

if __name__ == "__main__":
    main()
