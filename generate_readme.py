#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
README.md 자동 생성 - 당일 모니터링 중심
"""

import sqlite3
import os
from datetime import datetime, timedelta
import json
import pickle

try:
    import pytz
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
    import pytz

def decompress_if_needed():
    """압축된 DB를 임시로 해제"""
    if os.path.exists('schedule.db'):
        return 'schedule.db'
    elif os.path.exists('schedule.db.zst'):
        try:
            import zstandard as zstd
            with open('schedule.db.zst', 'rb') as compressed:
                dctx = zstd.ZstdDecompressor()
                with open('schedule.db', 'wb') as output:
                    output.write(dctx.decompress(compressed.read()))
            return 'schedule.db'
        except:
            return None
    return None

def get_today_stats():
    """오늘 데이터만 집계"""
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    today = now_kst.strftime('%Y-%m-%d')
    
    stats = {
        'last_update': now_kst.strftime('%Y-%m-%d %H:%M:%S KST'),
        'today': today,
        'today_records': 0,
        'today_zero_count': 0,
        'today_revenue': 0,
        'previous_revenue': 0,
        'revenue_change': 0,
        'revenue_change_text': '',
        'status': 'Unknown'
    }
    
    # 이전 실행 결과 읽기
    if os.path.exists('last_revenue.pkl'):
        try:
            with open('last_revenue.pkl', 'rb') as f:
                stats['previous_revenue'] = pickle.load(f)
        except:
            stats['previous_revenue'] = 0
    
    db_file = decompress_if_needed()
    if not db_file:
        return stats
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 오늘 레코드 수
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE date = ?
        """, (today,))
        stats['today_records'] = cursor.fetchone()[0] or 0
        
        # 오늘 총 매출
        cursor.execute("""
            SELECT SUM(CAST(REPLACE(REPLACE(총매출, ',', ''), '원', '') AS INTEGER))
            FROM schedule 
            WHERE date = ? 
            AND 총매출 IS NOT NULL 
            AND 총매출 != '' 
            AND 총매출 != '0'
        """, (today,))
        result = cursor.fetchone()[0]
        stats['today_revenue'] = result if result else 0
        
        # 오늘 0원 매출 카운트
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE date = ? 
            AND (총매출 = '0' OR 총매출 IS NULL OR 총매출 = '' OR CAST(REPLACE(REPLACE(총매출, ',', ''), '원', '') AS INTEGER) = 0)
        """, (today,))
        stats['today_zero_count'] = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # 매출 변화 계산
        if stats['previous_revenue'] > 0:
            change = stats['today_revenue'] - stats['previous_revenue']
            if change > 0:
                stats['revenue_change'] = change
                stats['revenue_change_text'] = f"+{format_number(change)}"
                stats['status'] = '정상'
            elif change == 0:
                stats['revenue_change_text'] = "변화없음 ⚠️"
                stats['status'] = '점검필요'
            else:
                stats['revenue_change'] = change
                stats['revenue_change_text'] = f"{format_number(change)}"
                stats['status'] = '확인필요'
        else:
            stats['revenue_change_text'] = "첫 실행"
            stats['status'] = '시작'
        
        # 현재 매출 저장 (다음 실행 비교용)
        with open('last_revenue.pkl', 'wb') as f:
            pickle.dump(stats['today_revenue'], f)
        
    except Exception as e:
        print(f"DB 오류: {e}")
    finally:
        # 임시 DB 삭제
        if os.path.exists('schedule.db') and os.path.exists('schedule.db.zst'):
            os.remove('schedule.db')
    
    return stats

def format_number(num):
    """숫자를 억원 단위로 포맷"""
    if abs(num) >= 100000000:  # 1억 이상
        return f"{num/100000000:+.1f}억원"
    elif abs(num) >= 10000000:  # 1천만 이상
        return f"{num/10000000:+.0f}천만원"
    elif abs(num) >= 10000:  # 1만 이상
        return f"{num/10000:+.0f}만원"
    else:
        return f"{num:+,}원"

def format_revenue(num):
    """매출 표시"""
    if num >= 100000000:  # 1억 이상
        return f"{num/100000000:.1f}억원"
    elif num >= 10000000:  # 1천만 이상
        return f"{num/10000000:.0f}천만원"
    elif num >= 10000:  # 1만 이상
        return f"{num/10000:.0f}만원"
    elif num > 0:
        return f"{num:,}원"
    else:
        return "0원"

def generate_readme():
    """README.md 생성"""
    stats = get_today_stats()
    
    # 상태 배지
    if stats['status'] == '정상':
        status_badge = "![Status](https://img.shields.io/badge/크롤링-정상-green)"
        status_icon = "✅"
    elif stats['status'] == '점검필요':
        status_badge = "![Status](https://img.shields.io/badge/크롤링-점검필요-yellow)"
        status_icon = "⚠️"
    elif stats['status'] == '확인필요':
        status_badge = "![Status](https://img.shields.io/badge/크롤링-확인필요-orange)"
        status_icon = "⚠️"
    else:
        status_badge = "![Status](https://img.shields.io/badge/크롤링-시작-blue)"
        status_icon = "🚀"
    
    # 매출 변화 아이콘
    if stats['revenue_change'] > 0:
        change_icon = "📈"
    elif stats['revenue_change'] < 0:
        change_icon = "📉"
    else:
        change_icon = "➡️"
    
    readme_content = f"""# 📊 Media Commerce Analytics Platform

{status_badge}

## {status_icon} 오늘 실시간 현황 ({stats['today']})

### 📍 최종 업데이트
- **시간**: {stats['last_update']}
- **상태**: {stats['status']}

### 💰 당일 매출 현황
- **오늘 총 매출**: **{format_revenue(stats['today_revenue'])}**
- **이전 대비**: {change_icon} **{stats['revenue_change_text']}**
- **데이터 건수**: {stats['today_records']}개
- **0원 매출**: {stats['today_zero_count']}개

### 🔍 모니터링 포인트
"""
    
    # 모니터링 메시지
    if stats['revenue_change'] == 0 and stats['previous_revenue'] > 0:
        readme_content += """
⚠️ **주의: 매출 변화 없음**
- 데이터 수집이 정상적으로 되지 않았을 수 있습니다
- API/쿠키 상태 확인 필요
"""
    elif stats['today_records'] == 0:
        readme_content += """
❌ **오늘 데이터 없음**
- 크롤링이 실행되지 않았거나 실패
"""
    elif stats['today_zero_count'] > stats['today_records'] * 0.5:
        readme_content += """
⚠️ **0원 매출 비율 높음**
- 데이터 품질 점검 필요
"""
    else:
        readme_content += """
✅ **정상 수집 중**
"""
    
    readme_content += f"""

## 📈 실행 기록

| 시간 | 매출 | 변화 | 상태 |
|------|------|------|------|
| {stats['last_update'].split()[1][:5]} | {format_revenue(stats['today_revenue'])} | {stats['revenue_change_text']} | {stats['status']} |

---

## 🔗 바로가기

- [⚙️ Actions](../../actions)
- [📝 실행 로그](../../actions/workflows/daily_scraping.yml)
- [📊 대시보드](dashboard/)

---

*자동 업데이트: 매 시간*
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README 업데이트 완료")
    print(f"   오늘 매출: {format_revenue(stats['today_revenue'])}")
    print(f"   변화: {stats['revenue_change_text']}")

if __name__ == "__main__":
    generate_readme()
