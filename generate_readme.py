#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
README.md 자동 생성 - 매출 비교 명확 버전
"""

import sqlite3
import os
from datetime import datetime
import json

try:
    import pytz
except:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
    import pytz

try:
    import zstandard as zstd
except:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "zstandard"])
    import zstandard as zstd

def decompress_db():
    """압축된 DB 해제"""
    if os.path.exists('schedule.db'):
        return True
    
    if os.path.exists('schedule.db.zst'):
        print("압축 DB 해제 중...")
        try:
            with open('schedule.db.zst', 'rb') as f:
                dctx = zstd.ZstdDecompressor()
                with open('schedule.db', 'wb') as out:
                    out.write(dctx.decompress(f.read()))
            return True
        except Exception as e:
            print(f"압축 해제 실패: {e}")
            return False
    return False

def get_stats():
    """통계 수집"""
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    today = now_kst.strftime('%Y-%m-%d')
    
    stats = {
        'last_update': now_kst.strftime('%Y-%m-%d %H:%M:%S KST'),
        'today': today,
        'current_revenue': 0,
        'previous_revenue': 0,
        'revenue_change': 0,
        'today_records': 0,
        'zero_count': 0,
        'status': '확인필요'
    }
    
    # 이전 매출 읽기
    if os.path.exists('last_stats.json'):
        try:
            with open('last_stats.json', 'r') as f:
                last = json.load(f)
                stats['previous_revenue'] = last.get('current_revenue', 0)
        except:
            print("이전 기록 없음")
    
    # DB 읽기
    if not decompress_db():
        print("DB 파일 없음")
        return stats
    
    try:
        conn = sqlite3.connect('schedule.db')
        cursor = conn.cursor()
        
        # 오늘 전체 매출 합계
        cursor.execute("""
            SELECT SUM(CAST(REPLACE(REPLACE(총매출, ',', ''), '원', '') AS INTEGER))
            FROM schedule 
            WHERE date = ?
            AND 총매출 IS NOT NULL 
            AND 총매출 != ''
            AND 총매출 != '0'
        """, (today,))
        
        result = cursor.fetchone()
        if result and result[0]:
            stats['current_revenue'] = result[0]
        
        # 오늘 레코드 수
        cursor.execute("SELECT COUNT(*) FROM schedule WHERE date = ?", (today,))
        stats['today_records'] = cursor.fetchone()[0] or 0
        
        # 0원 매출 수
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE date = ? 
            AND (총매출 = '0' OR 총매출 IS NULL OR 총매출 = '')
        """, (today,))
        stats['zero_count'] = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # 변화 계산
        if stats['previous_revenue'] > 0:
            stats['revenue_change'] = stats['current_revenue'] - stats['previous_revenue']
            if stats['revenue_change'] > 0:
                stats['status'] = '정상'
            elif stats['revenue_change'] == 0:
                stats['status'] = '점검필요'
            else:
                stats['status'] = '확인필요'
        else:
            stats['status'] = '첫실행'
        
        # 현재 통계 저장
        with open('last_stats.json', 'w') as f:
            json.dump(stats, f)
        
    except Exception as e:
        print(f"DB 읽기 오류: {e}")
    finally:
        # 임시 DB 삭제
        if os.path.exists('schedule.db') and os.path.exists('schedule.db.zst'):
            os.remove('schedule.db')
    
    return stats

def format_money(num):
    """금액 포맷"""
    if num >= 100000000:
        return f"{num/100000000:.1f}억원"
    elif num >= 10000000:
        return f"{num/10000000:.0f}천만원"
    elif num >= 10000:
        return f"{num/10000:.0f}만원"
    elif num > 0:
        return f"{num:,}원"
    else:
        return "0원"

def generate_readme():
    """README 생성"""
    stats = get_stats()
    
    # 상태 배지
    if stats['status'] == '정상':
        badge = "![크롤링](https://img.shields.io/badge/크롤링-정상-green)"
        icon = "✅"
    elif stats['status'] == '점검필요':
        badge = "![크롤링](https://img.shields.io/badge/크롤링-점검필요-yellow)"
        icon = "⚠️"
    elif stats['status'] == '첫실행':
        badge = "![크롤링](https://img.shields.io/badge/크롤링-시작-blue)"
        icon = "🚀"
    else:
        badge = "![크롤링](https://img.shields.io/badge/크롤링-확인필요-orange)"
        icon = "⚠️"
    
    # 변화 표시
    if stats['revenue_change'] > 0:
        change_text = f"📈 +{format_money(stats['revenue_change'])}"
    elif stats['revenue_change'] < 0:
        change_text = f"📉 {format_money(stats['revenue_change'])}"
    else:
        change_text = "➡️ 변화없음"
    
    content = f"""# 📊 Media Commerce Analytics Platform

{badge}

## {icon} 오늘 실시간 현황 ({stats['today']})

### 📍 최종 업데이트
- **시간**: {stats['last_update']}
- **상태**: {stats['status']}

### 💰 당일 매출 현황
- **현재 총 매출**: **{format_money(stats['current_revenue'])}**
- **이전 총 매출**: {format_money(stats['previous_revenue'])}
- **매출 변화**: {change_text}
- **데이터 건수**: {stats['today_records']}개
- **0원 매출**: {stats['zero_count']}개

### 🔍 모니터링 포인트
"""
    
    if stats['revenue_change'] == 0 and stats['previous_revenue'] > 0:
        content += """
⚠️ **매출 변화 없음 - 점검 필요**
- 크롤링이 제대로 작동하지 않을 수 있습니다
- API/쿠키 상태 확인이 필요합니다
"""
    elif stats['current_revenue'] == 0:
        content += """
❌ **매출 데이터 없음**
- 오늘 크롤링이 시작되지 않았거나
- 데이터 수집에 문제가 있을 수 있습니다
"""
    else:
        content += f"""
✅ **정상 수집 중**
- 총 {stats['today_records']}개 데이터 수집
- 매출 합계: {format_money(stats['current_revenue'])}
"""
    
    content += f"""

## 📈 실행 기록

| 구분 | 매출 | 데이터수 |
|------|------|----------|
| 현재 | {format_money(stats['current_revenue'])} | {stats['today_records']}개 |
| 이전 | {format_money(stats['previous_revenue'])} | - |
| 변화 | {change_text} | - |

---

## 🔗 바로가기

- [⚙️ Actions](../../actions)
- [📝 실행 로그](../../actions/workflows/daily_scraping.yml)
- [📊 대시보드](dashboard/)

---

*자동 업데이트: 매 시간*
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("="*40)
    print("README 업데이트 완료")
    print(f"현재 매출: {format_money(stats['current_revenue'])}")
    print(f"이전 매출: {format_money(stats['previous_revenue'])}")
    print(f"변화: {change_text}")
    print("="*40)

if __name__ == "__main__":
    generate_readme()
