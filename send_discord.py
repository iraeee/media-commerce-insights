#!/usr/bin/env python3
"""
Discord 웹훅 알림 전송
"""

import json
import os
import requests

def send_discord_notification():
    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    
    if not webhook_url:
        print("Discord 웹훅 URL이 설정되지 않음")
        return
    
    # data_check.json 읽기
    if not os.path.exists('data_check.json'):
        print("data_check.json 파일 없음")
        return
    
    with open('data_check.json', 'r') as f:
        data = json.load(f)
    
    # 색상 결정
    if data['status'] == 'OK':
        color = 0x00FF00  # 녹색
    elif data['status'] in ['WARNING', 'CAUTION']:
        color = 0xFFA500  # 주황색
    else:
        color = 0xFF0000  # 빨간색
    
    # 임베드 메시지 생성
    embed = {
        "title": f"라방바 크롤링 - {data['status']}",
        "color": color,
        "fields": [
            {"name": "날짜", "value": data['date'], "inline": True},
            {"name": "레코드", "value": f"{data['total']}개", "inline": True},
            {"name": "0원 비율", "value": f"{data['zero_ratio']:.1f}%", "inline": True},
            {"name": "메시지", "value": data['message'], "inline": False}
        ],
        "footer": {
            "text": "라방바 자동 수집 시스템"
        }
    }
    
    # 웹훅 전송
    response = requests.post(webhook_url, json={"embeds": [embed]})
    
    if response.status_code == 204:
        print("✅ Discord 알림 전송 성공")
    else:
        print(f"❌ Discord 알림 전송 실패: {response.status_code}")

if __name__ == "__main__":
    send_discord_notification()
