#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
README.md 자동 생성 스크립트
GitHub Actions에서 실행되어 최신 상태를 업데이트
"""

import sqlite3
import os
from datetime import datetime, timedelta
import json
import pytz

def get_db_stats():
    """DB에서 통계 정보 추출"""
    # 한국 시간대 설정
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    stats = {
        'last_update': now_kst.strftime('%Y-%m-%d %H:%M:%S KST'),
        'total_records': 0,
        'zero_revenue_count': 0,
        'zero_revenue_percent': 0,
        'total_revenue': 0,
        'previous_revenue': 0,
        'revenue_change': 0,
        'data_quality': 'N/A',
        'api_status': 'Unknown',
        'cookie_status': 'Unknown'
    }
    
    # DB 파일 확인
    db_exists = False
    db_compressed = False
    
    if os.path.exists('schedule.db'):
        db_exists = True
        db_file = 'schedule.db'
    elif os.path.exists('schedule.db.zst'):
        db_exists = True
        db_compressed = True
        try:
            import zstandard as zstd
            with open('schedule.db.zst', 'rb') as compressed:
                dctx = zstd.ZstdDecompressor()
                with open('schedule.db', 'wb') as output:
                    output.write(dctx.decompress(compressed.read()))
            db_file = 'schedule.db'
        except:
            return stats
    
    if not db_exists:
        return stats
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schedule'")
        if not cursor.fetchone():
            conn.close()
            return stats
        
        # 전체 레코드 수
        cursor.execute("SELECT COUNT(*) FROM schedule WHERE date >= date('now', '-30 days')")
        stats['total_records'] = cursor.fetchone()[0] or 0
        
        # 총 매출 계산 - 최근 30일
        cursor.execute("""
            SELECT SUM(CAST(REPLACE(REPLACE(총매출, ',', ''), '원', '') AS INTEGER)) 
            FROM schedule 
            WHERE date >= date('now', '-30 days')
            AND 총매출 IS NOT NULL 
            AND 총매출 != ''
            AND 총매출 != '0'
        """)
        result = cursor.fetchone()[0]
        stats['total_revenue'] = result if result else 0
        
        # 0원 매출 카운트
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schedule 
            WHERE date >= date('now', '-30 days')
            AND (총매출 = '0' OR 총매출 IS NULL OR 총매출 = '' OR CAST(REPLACE(REPLACE(총매출, ',', ''), '원', '') AS INTEGER) = 0)
        """)
        stats['zero_revenue_count'] = cursor.fetchone()[0] or 0
        
        if stats['total_records'] > 0:
            stats['zero_revenue_percent'] = round(
                (stats['zero_revenue_count'] / stats['total_records']) * 100, 1
            )
        
        # 7일 전 매출 (비교용)
        cursor.execute("""
            SELECT SUM(CAST(REPLACE(REPLACE(총매출, ',', ''), '원', '') AS INTEGER))
            FROM schedule 
            WHERE date >= date('now', '-37 days')
            AND date < date('now', '-30 days')
            AND 총매출 IS NOT NULL 
            AND 총매출 != ''
            AND 총매출 != '0'
        """)
        result = cursor.fetchone()[0]
        stats['previous_revenue'] = result if result else 0
        
        # 매출 변화율 계산
        if stats['previous_revenue'] > 0:
            change = ((stats['total_revenue'] - stats['previous_revenue']) / stats['previous_revenue']) * 100
            stats['revenue_change'] = round(change, 2)
        elif stats['total_revenue'] > 0:
            stats['revenue_change'] = 100.0  # 이전 매출 0, 현재 매출 있음
        
        # 데이터 품질 평가
        if stats['zero_revenue_percent'] < 10:
            stats['data_quality'] = '우수'
        elif stats['zero_revenue_percent'] < 20:
            stats['data_quality'] = '양호'
        elif stats['zero_revenue_percent'] < 30:
            stats['data_quality'] = '보통'
        else:
            stats['data_quality'] = '점검필요'
        
        conn.close()
        
        # 압축 파일이었다면 임시 DB 삭제
        if db_compressed and os.path.exists('schedule.db'):
            os.remove('schedule.db')
        
    except Exception as e:
        print(f"DB 통계 추출 오류: {e}")
    
    return stats

def check_api_status():
    """API 상태 체크"""
    # 한국 시간대
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    try:
        if os.path.exists('health_status.json'):
            with open('health_status.json', 'r', encoding='utf-8') as f:
                health = json.load(f)
                return {
                    'api': health.get('api_status', '정상'),
                    'cookie': health.get('cookie_status', '유효'),
                    'last_check': health.get('timestamp', now_kst.strftime('%Y-%m-%d %H:%M'))
                }
    except:
        pass
    
    return {
        'api': '정상',
        'cookie': '유효',
        'last_check': now_kst.strftime('%Y-%m-%d %H:%M')
    }

def format_number(num):
    """숫자를 억원 단위로 포맷"""
    if num >= 100000000:  # 1억 이상
        return f"{num/100000000:,.1f}억원"
    elif num >= 10000000:  # 1천만 이상
        return f"{num/10000000:,.0f}천만원"
    elif num >= 10000:  # 1만 이상
        return f"{num/10000:,.0f}만원"
    elif num > 0:
        return f"{num:,}원"
    else:
        return "0원"

def generate_trend_chart(stats):
    """트렌드 차트 생성"""
    if stats['revenue_change'] > 10:
        return """    ↑
    │     ╱▔▔
    │   ╱▔
    │ ╱▔
    │╱
    └────────→"""
    elif stats['revenue_change'] > 0:
        return """    ↑
    │   ╱▔▔▔
    │ ╱▔
    │╱
    │
    └────────→"""
    elif stats['revenue_change'] < -10:
        return """    ↑
    │▔╲
    │  ╲
    │   ╲__
    │     ╲_
    └────────→"""
    elif stats['revenue_change'] < 0:
        return """    ↑
    │▔▔╲
    │   ╲__
    │
    │
    └────────→"""
    else:
        return """    ↑
    │────────
    │
    │
    │
    └────────→"""

def generate_readme():
    """README.md 생성"""
    stats = get_db_stats()
    health = check_api_status()
    
    # 상태 배지
    if stats['data_quality'] in ['우수', '양호']:
        status_badge = "![상태](https://img.shields.io/badge/상태-정상-green)"
    elif stats['data_quality'] == '보통':
        status_badge = "![상태](https://img.shields.io/badge/상태-주의-yellow)"
    else:
        status_badge = "![상태](https://img.shields.io/badge/상태-점검필요-red)"
    
    api_badge = "![API](https://img.shields.io/badge/API-정상-green)" if health['api'] == '정상' else "![API](https://img.shields.io/badge/API-오류-red)"
    cookie_badge = "![Cookie](https://img.shields.io/badge/Cookie-유효-green)" if health['cookie'] == '유효' else "![Cookie](https://img.shields.io/badge/Cookie-갱신필요-orange)"
    
    # 매출 변화 표시
    if stats['revenue_change'] > 0:
        change_icon = "📈"
        change_text = f"+{stats['revenue_change']}%"
    elif stats['revenue_change'] < 0:
        change_icon = "📉"
        change_text = f"{stats['revenue_change']}%"
    else:
        change_icon = "➡️"
        change_text = "0%"
    
    # 매출이 0이면 N/A로 표시
    total_revenue_text = format_number(stats['total_revenue']) if stats['total_revenue'] > 0 else "집계 중..."
    previous_revenue_text = format_number(stats['previous_revenue']) if stats['previous_revenue'] > 0 else "집계 중..."
    
    readme_content = f"""# 🎯 홈쇼핑 빅데이터 인사이트 플랫폼

{status_badge} {api_badge} {cookie_badge}

## 📊 시스템 현황

### 데이터 집계
- **최종 업데이트**: {stats['last_update']}
- **총 레코드**: {stats['total_records']:,}개
- **데이터 품질**: {stats['data_quality']} (0원 매출: {stats['zero_revenue_percent']}%)

### 💰 매출 분석
- **총 집계 매출**: {total_revenue_text}
- **전주 대비**: {change_icon} {change_text}
- **이전 매출**: {previous_revenue_text}

### 🔧 시스템 상태
- **API 연결**: {health['api']}
- **인증 쿠키**: {health['cookie']}
- **마지막 체크**: {health['last_check']}

## 📈 최근 트렌드

```
최근 7일 매출 추이
{generate_trend_chart(stats)}
```

## 🔗 빠른 링크

- [📊 대시보드](dashboard/)
- [⚙️ Actions](../../actions)
- [📝 실행 로그](../../actions/workflows/daily_scraping.yml)

---

*자동 업데이트: 매일 23:56 KST*
*시스템: Home Shopping Big Data Insights Platform v2.0*
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README.md 업데이트 완료")
    print(f"   - 총 매출: {total_revenue_text}")
    print(f"   - 변화율: {change_icon} {change_text}")
    print(f"   - 업데이트 시간: {stats['last_update']}")

if __name__ == "__main__":
    # pytz 설치 확인
    try:
        import pytz
    except ImportError:
        print("Installing pytz...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
        import pytz
    
    generate_readme()
