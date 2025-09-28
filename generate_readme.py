#!/usr/bin/env python3
"""
README.md 자동 생성 스크립트
GitHub Actions에서 사용
"""

import json
import os
from datetime import datetime

def generate_readme():
    # 체크 결과 로드
    status = {}
    if os.path.exists('data_check.json'):
        with open('data_check.json', 'r') as f:
            status = json.load(f)
    
    # 배지 색상 결정
    badge_color = 'success' if status.get('status') == 'OK' else 'critical'
    badge_text = status.get('message', 'Unknown')
    
    # README 내용 생성
    readme_content = f"""# 라방바 데이터 수집 시스템

![상태](https://img.shields.io/badge/Status-{badge_text.replace(' ', '%20')}-{badge_color})
![업데이트](https://img.shields.io/badge/Updated-{datetime.now().strftime('%Y-%m-%d')}-blue)

## 📊 최근 수집 결과

- **날짜**: {status.get('date', 'N/A')}
- **총 레코드**: {status.get('total', 0):,}개
- **0원 매출**: {status.get('zero_count', 0)}개 ({status.get('zero_ratio', 0):.1f}%)
- **평균 매출**: {status.get('avg_revenue', 0):,.0f}원

## 🔗 빠른 링크

- [Actions](https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'user/repo')}/actions)
- [최근 실행 결과](https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'user/repo')}/actions/workflows/daily_scraping.yml)

---
*자동 업데이트: 매일 23:56 KST*
"""
    
    # README 파일 작성
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ README.md 생성 완료")

if __name__ == "__main__":
    generate_readme()
