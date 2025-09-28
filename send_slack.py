#!/usr/bin/env python3
"""
Slack 웹훅 알림 전송
라방바 데이터 수집 결과 알림
"""

import json
import os
import requests
from datetime import datetime

def send_slack_notification():
    webhook_url = os.environ.get('SLACK_WEBHOOK')
    
    if not webhook_url:
        print("Slack 웹훅 URL이 설정되지 않음")
        return
    
    # data_check.json 읽기
    if not os.path.exists('data_check.json'):
        print("data_check.json 파일 없음")
        return
    
    with open('data_check.json', 'r') as f:
        data = json.load(f)
    
    # 상태별 이모지 설정
    status_emoji = {
        'OK': '✅',
        'WARNING': '⚠️',
        'CAUTION': '⚡',
        'CRITICAL': '🚨',
        'NO_DATA': '❌'
    }
    
    emoji = status_emoji.get(data['status'], '📊')
    
    # 색상 설정 (Slack attachment 색상)
    if data['status'] == 'OK':
        color = 'good'  # 녹색
    elif data['status'] in ['WARNING', 'CAUTION']:
        color = 'warning'  # 노란색
    else:
        color = 'danger'  # 빨간색
    
    # Slack 메시지 생성
    slack_message = {
        "text": f"{emoji} 라방바 데이터 수집 완료",
        "attachments": [
            {
                "color": color,
                "title": f"상태: {data['status']}",
                "fields": [
                    {
                        "title": "날짜",
                        "value": data['date'],
                        "short": True
                    },
                    {
                        "title": "총 레코드",
                        "value": f"{data['total']:,}개",
                        "short": True
                    },
                    {
                        "title": "0원 매출",
                        "value": f"{data['zero_count']}개 ({data['zero_ratio']:.1f}%)",
                        "short": True
                    },
                    {
                        "title": "평균 매출",
                        "value": f"{data.get('avg_revenue', 0):,.0f}원",
                        "short": True
                    }
                ],
                "footer": "라방바 자동 수집 시스템",
                "footer_icon": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
                "ts": int(datetime.now().timestamp())
            }
        ]
    }
    
    # 메시지 텍스트 추가
    if data['status'] == 'CRITICAL':
        slack_message["attachments"][0]["text"] = "🚨 쿠키 업데이트가 필요합니다!"
    elif data['status'] == 'WARNING':
        slack_message["attachments"][0]["text"] = "⚠️ 0원 매출이 많습니다. 쿠키 상태를 확인하세요."
    else:
        slack_message["attachments"][0]["text"] = data.get('message', '')
    
    # 웹훅 전송
    response = requests.post(webhook_url, json=slack_message)
    
    if response.status_code == 200:
        print("✅ Slack 알림 전송 성공")
    else:
        print(f"❌ Slack 알림 전송 실패: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    send_slack_notification()
