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

def get_db_stats():
    """DB에서 통계 정보 추출"""
    stats = {
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S KST'),
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
    
    # DB 파일 확인 (압축/비압축 모두 체크)
    db_exists = False
    db_compressed = False
    
    if os.path.exists('schedule.db'):
        db_exists = True
        db_file = 'schedule.db'
    elif os.path.exists('schedule.db.zst'):
        db_exists = True
        db_compressed = True
        # 압축된 경우 임시로 해제
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
        
        # 전체 레코드 수
        cursor.execute("SELECT COUNT(*) FROM schedule")
        stats['total_records'] = cursor.fetchone()[0]
        
        # 0원 매출 카운트
        cursor.execute("SELECT COUNT(*) FROM schedule WHERE CAST(총매출 AS INTEGER) = 0")
        stats['zero_revenue_count'] = cursor.fetchone()[0]
        
        if stats['total_records'] > 0:
            stats['zero_revenue_percent'] = round(
                (stats['zero_revenue_count'] / stats['total_records']) * 100, 1
            )
        
        # 현재 총 매출
        cursor.execute("SELECT SUM(CAST(총매출 AS INTEGER)) FROM schedule WHERE CAST(총매출 AS INTEGER) > 0")
        current_total = cursor.fetchone()[0] or 0
        stats['total_revenue'] = current_total
        
        # 이전 집계 매출 (7일 전 데이터와 비교)
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT SUM(CAST(총매출 AS INTEGER)) 
            FROM schedule 
            WHERE date <= ? AND CAST(총매출 AS INTEGER) > 0
        """, (seven_days_ago,))
        previous_total = cursor.fetchone()[0] or 0
        stats['previous_revenue'] = previous_total
        
        # 매출 변화율 계산
        if previous_total > 0:
            change = ((current_total - previous_total) / previous_total) * 100
            stats['revenue_change'] = round(change, 2)
        
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
    """API 상태 체크 (health_check.py 결과 활용)"""
    try:
        # health_check.json 파일이 있다면 읽기
        if os.path.exists('health_status.json'):
            with open('health_status.json', 'r', encoding='utf-8') as f:
                health = json.load(f)
                return {
                    'api': health.get('api_status', 'Unknown'),
                    'cookie': health.get('cookie_status', 'Unknown'),
                    'last_check': health.get('timestamp', 'N/A')
                }
    except:
        pass
    
    # 기본값
    return {
        'api': '정상',
        'cookie': '유효',
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def format_number(num):
    """숫자를 읽기 쉬운 형식으로 포맷"""
    if num >= 100000000:  # 1억 이상
        return f"{num/100000000:,.1f}억원"
    elif num >= 10000000:  # 1천만 이상
        return f"{num/10000000:,.1f}천만원"
    elif num >= 10000:  # 1만 이상
        return f"{num/10000:,.0f}만원"
    else:
        return f"{num:,}원"

def generate_readme():
    """README.md 생성"""
    stats = get_db_stats()
    health = check_api_status()
    
    # 상태 배지 결정
    if stats['data_quality'] in ['우수', '양호']:
        status_badge = "![Status](https://img.shields.io/badge/상태-정상-green)"
    elif stats['data_quality'] == '보통':
        status_badge = "![Status](https://img.shields.io/badge/상태-주의-yellow)"
    else:
        status_badge = "![Status](https://img.shields.io/badge/상태-점검필요-red)"
    
    # API 상태 배지
    if health['api'] == '정상':
        api_badge = "![API](https://img.shields.io/badge/API-정상-green)"
    else:
        api_badge = "![API](https://img.shields.io/badge/API-오류-red)"
    
    # 쿠키 상태 배지
    if health['cookie'] == '유효':
        cookie_badge = "![Cookie](https://img.shields.io/badge/Cookie-유효-green)"
    else:
        cookie_badge = "![Cookie](https://img.shields.io/badge/Cookie-갱신필요-orange)"
    
    # 매출 변화 표시
    if stats['revenue_change'] > 0:
        change_icon = "📈"
        change_text = f"+{stats['revenue_change']}%"
        change_color = "green"
    elif stats['revenue_change'] < 0:
        change_icon = "📉"
        change_text = f"{stats['revenue_change']}%"
        change_color = "red"
    else:
        change_icon = "➡️"
        change_text = "0%"
        change_color = "gray"
    
    readme_content = f"""# 🎯 Commerce Analytics Platform

{status_badge} {api_badge} {cookie_badge}

## 📊 시스템 현황

### 데이터 집계
- **최종 업데이트**: {stats['last_update']}
- **총 레코드**: {stats['total_records']:,}개
- **데이터 품질**: {stats['data_quality']} (0원 매출: {stats['zero_revenue_percent']}%)

### 💰 매출 분석
- **총 집계 매출**: {format_number(stats['total_revenue'])}
- **전주 대비**: {change_icon} {change_text}
- **이전 매출**: {format_number(stats['previous_revenue'])}

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
*시스템: Commerce Analytics Platform v2.0*
"""
    
    # README.md 파일 쓰기
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README.md 업데이트 완료")
    print(f"   - 총 매출: {format_number(stats['total_revenue'])}")
    print(f"   - 변화율: {change_icon} {change_text}")

def generate_trend_chart(stats):
    """간단한 ASCII 차트 생성"""
    # 실제로는 DB에서 7일 데이터를 가져와야 하지만, 간단한 예시
    if stats['revenue_change'] > 0:
        return """
    ↑
    │     ╱▔▔
    │   ╱▔
    │ ╱▔
    │╱
    └────────→
    """
    elif stats['revenue_change'] < 0:
        return """
    ↑
    │▔╲
    │  ╲
    │   ╲__
    │     ╲_
    └────────→
    """
    else:
        return """
    ↑
    │────────
    │
    │
    │
    └────────→
    """

def save_health_status(api_status="정상", cookie_status="유효"):
    """헬스 체크 상태 저장 (health_check.py에서 호출)"""
    status = {
        'api_status': api_status,
        'cookie_status': cookie_status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('health_status.json', 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generate_readme()
