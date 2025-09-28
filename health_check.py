"""
라방바 API 상태 체크 모듈
API 변경, 쿠키 만료, 데이터 수집 이상 감지
쿠키 업데이트: 2025-01-27
매출 0원 임계값: 50% (2025-01-27 수정)
"""

import requests
import json
import sqlite3
from datetime import datetime, timedelta
import re

class HealthChecker:
    """API 상태 체크 클래스"""
    
    def __init__(self):
        self.api_url = "https://live.ecomm-data.com/schedule/list_hs"
        self.headers = {
            "accept": "*/*",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://live.ecomm-data.com",
            "referer": "https://live.ecomm-data.com/schedule/hs",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Cookie": "_ga=GA1.1.1148900813.1753071738; _gcl_au=1.1.2127562858.1753071789.734155396.1753071810.1753071813; _fwb=8206MdvNQcDXiuEel5llWx.1753071736391; sales2=eyJoaXN0b3J5IjpbNTAwMDAwMDNdLCJsYWJhbmdfb2JqIjp7fSwicGFzdF9rZXl3b3JkMiI6Iu2DgO2IrOq3uOumrOuqqCIsInVzZXIiOnsidXNlcl9pZCI6IjlqOTE3YldXdHktQ29FSU9Qa2wzTiIsIm5pY2tuYW1lIjoiaXJhZSIsInNlc3NfaWQiOiI1bjl1MmNDMmxkZm9aYzN1cDVacUYiLCJ1c2VyX3R5cGUiOjAsInZvdWNoZXIiOjAsInByZWZlciI6MX19; sales2.sig=H_m259PdzJTw0F1uUNfLmzSg51s; _ga_VN7F3DELDK=GS2.1.s1756172082$o26$g1$t1756173157$j10$l0$h0; _ga_NLGYGNTN3F=GS2.1.s1756172082$o26$g1$t1756173157$j10$l0$h0"
        }
        self.issues = []
        self.warnings = []
        
        # 매출 0원 임계값 설정 (50%로 상향)
        self.ZERO_REVENUE_THRESHOLD = 50  # 심각한 문제로 판단하는 기준
        self.ZERO_REVENUE_WARNING = 40    # 경고 수준
        
    def check_api_response(self):
        """API 응답 체크"""
        print("🔍 API 응답 테스트...")
        
        try:
            # 오늘 날짜로 테스트
            date_str = datetime.now().strftime("%y%m%d")
            post_data = {"date": date_str}
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=post_data,
                timeout=10
            )
            
            if response.status_code != 200:
                self.issues.append(f"API 응답 코드 이상: {response.status_code}")
                return False
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                self.issues.append("API 응답이 JSON 형식이 아님")
                return False
            
            # 데이터 구조 확인 - 딕셔너리 형태로 오는 경우 처리
            if isinstance(data, dict):
                if "list" in data:
                    actual_data = data["list"]
                    print(f"  ✅ API 응답 정상 ({len(actual_data)}개 데이터)")
                    return actual_data
                else:
                    self.issues.append("예상치 못한 API 응답 구조 - list 필드 없음")
                    return False
            elif isinstance(data, list):
                if len(data) == 0:
                    self.issues.append("API가 빈 리스트 반환")
                    return False
                print(f"  ✅ API 응답 정상 ({len(data)}개 데이터)")
                return data
            else:
                self.issues.append("예상치 못한 API 응답 타입")
                return False
            
        except requests.exceptions.Timeout:
            self.issues.append("API 응답 시간 초과 (10초)")
            return False
        except requests.exceptions.RequestException as e:
            self.issues.append(f"API 요청 실패: {str(e)}")
            return False
    
    def check_data_quality(self, data, debug=False):
        """데이터 품질 체크 - 현재 시간 이전 방송만 체크"""
        print(f"🔍 데이터 품질 검사... [임계값: {self.ZERO_REVENUE_THRESHOLD}%]")
        
        if not data:
            return False
        
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # 현재 시간을 분 단위로 변환 (0시부터의 분)
        current_minutes = current_hour * 60 + current_minute
        
        # 샘플 데이터 체크
        past_broadcasts = []
        future_broadcasts = []
        zero_revenue_past = 0
        sample_data = None
        
        # 디버깅: 첫 번째 아이템의 모든 필드 출력
        if data and debug:
            print("\n[DEBUG] 첫 번째 데이터 아이템의 필드:")
            first_item = data[0]
            for key, value in first_item.items():
                if 'sale' in key.lower() or 'amt' in key.lower() or 'revenue' in key.lower():
                    print(f"  - {key}: {value}")
        
        for idx, item in enumerate(data):
            # 시작 시간 파싱
            start_time_str = item.get('hsshow_datetime_start', '')
            if not start_time_str:
                continue
                
            try:
                # YYYYMMDDHHMM 형식 파싱
                start_dt = datetime.strptime(start_time_str, "%Y%m%d%H%M")
                broadcast_hour = start_dt.hour
                broadcast_minute = start_dt.minute
                broadcast_minutes = broadcast_hour * 60 + broadcast_minute
                
                # 현재 시간 이전 방송인지 확인
                if broadcast_minutes < current_minutes:
                    past_broadcasts.append(item)
                    
                    # 매출 확인 - 더 많은 필드 체크
                    revenue = 0
                    revenue_fields = ['sales_amt', 'salesAmt', 'sales_amount', 'salesAmount', 'sale_amt', 'revenue']
                    found_field = None
                    
                    for field in revenue_fields:
                        if field in item:
                            val = item.get(field)
                            # None이 아니고, 빈 문자열이 아니고, 0이 아닌 경우
                            if val is not None and val != '' and val != 0:
                                try:
                                    revenue = int(val)
                                    found_field = field
                                    break
                                except (ValueError, TypeError):
                                    pass
                            # 0인 경우도 유효한 값으로 처리
                            elif val == 0:
                                revenue = 0
                                found_field = field
                                break
                    
                    # 디버깅: 처음 5개 과거 방송의 매출 정보 출력
                    if debug and idx < 5 and broadcast_minutes < current_minutes:
                        print(f"\n[DEBUG] 과거 방송 #{idx+1}:")
                        print(f"  - 시간: {broadcast_hour:02d}:{broadcast_minute:02d}")
                        print(f"  - 제목: {item.get('hsshow_title', '')[:30]}")
                        print(f"  - 매출 필드: {found_field}")
                        print(f"  - 매출액: {revenue}")
                        if revenue == 0:
                            print(f"  - 가능한 필드들: {[k for k in item.keys() if 'sale' in k.lower() or 'amt' in k.lower()]}")
                    
                    if revenue == 0:
                        zero_revenue_past += 1
                    elif not sample_data:  # 첫 번째 유효한 샘플 저장
                        sample_data = {
                            'date': datetime.now().strftime("%Y-%m-%d"),
                            'time': f"{broadcast_hour:02d}:{broadcast_minute:02d}",
                            'broadcast': item.get('hsshow_title', ''),
                            'platform': item.get('platform_name', ''),
                            'revenue': revenue
                        }
                else:
                    future_broadcasts.append(item)
                    
            except ValueError:
                continue
        
        # 통계 출력
        print(f"  ℹ️ 현재 시간: {current_hour:02d}:{current_minute:02d}")
        print(f"  - 과거 방송: {len(past_broadcasts)}개")
        print(f"  - 미래 방송: {len(future_broadcasts)}개")
        
        # 과거 방송이 없으면 문제
        if len(past_broadcasts) == 0:
            self.issues.append("과거 방송 데이터가 없음")
            return sample_data
        
        # 과거 방송 중 매출 0원 비율 체크 (50% 이상이면 문제)
        if len(past_broadcasts) > 0:
            zero_percent_past = (zero_revenue_past / len(past_broadcasts)) * 100
            
            print(f"  - 과거 방송 중 매출 0원: {zero_revenue_past}개 ({zero_percent_past:.1f}%)")
            
            # 임계값을 50%로 상향 조정
            if zero_percent_past > self.ZERO_REVENUE_THRESHOLD:
                self.issues.append(f"과거 방송 매출 0원 비율이 {zero_percent_past:.1f}%로 너무 높음 (기준: {self.ZERO_REVENUE_THRESHOLD}%)")
                return sample_data
            elif zero_percent_past > self.ZERO_REVENUE_WARNING:
                self.warnings.append(f"과거 방송 매출 0원 비율 {zero_percent_past:.1f}% (경고 수준: {self.ZERO_REVENUE_WARNING}%)")
        
        print(f"  ✅ 데이터 품질 정상")
        return sample_data
    
    def check_cookie_validity(self):
        """쿠키 유효성 체크"""
        print("🔍 쿠키 유효성 검사...")
        
        # 쿠키에서 세션 정보 추출
        cookie_str = self.headers.get('Cookie', '')
        
        # sales2 쿠키 체크
        if 'sales2=' not in cookie_str:
            self.issues.append("sales2 쿠키가 없음")
            return False
        
        # 세션 ID 체크 - 업데이트된 세션 ID 확인
        if 'sess_id' in cookie_str:
            if '5njl2cC2ldfoZc3up5ZqF' in cookie_str:
                print("  ✅ 쿠키 세션 ID 최신 (2025-01-27 업데이트)")
            else:
                self.warnings.append("쿠키 세션 ID가 최신이 아닐 수 있음")
        
        print("  ✅ 쿠키 형식 정상")
        return True
    
    def check_historical_data(self):
        """과거 데이터와 비교"""
        print("🔍 과거 데이터 비교...")
        
        try:
            conn = sqlite3.connect("schedule.db")
            cursor = conn.cursor()
            
            # 최근 7일 데이터 통계
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    AVG(revenue) as avg_revenue,
                    MAX(date) as last_date
                FROM schedule
                WHERE date >= ?
            """, (week_ago,))
            
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                print(f"  ℹ️ 최근 7일: {result[0]}건, 평균 매출: {result[1]:,.0f}원")
                
                # 오늘 데이터 체크
                today = datetime.now().strftime("%Y-%m-%d")
                
                # 현재 시간 기준으로 과거 방송만 체크
                current_hour = datetime.now().hour
                cursor.execute("""
                    SELECT COUNT(*), AVG(revenue)
                    FROM schedule
                    WHERE date = ? AND CAST(SUBSTR(time, 1, 2) AS INTEGER) < ?
                """, (today, current_hour))
                
                today_result = cursor.fetchone()
                
                if today_result and today_result[0] > 0:
                    # 시간당 평균으로 비교
                    avg_per_hour_week = result[1] / 24 if result[1] else 0
                    avg_per_hour_today = today_result[1] if today_result[1] else 0
                    
                    if avg_per_hour_today < avg_per_hour_week * 0.3:  # 평균의 30% 미만
                        self.warnings.append("오늘 매출이 평소보다 매우 낮음")
                else:
                    if current_hour > 6:  # 아침 6시 이후인데 데이터가 없으면
                        self.warnings.append("오늘 수집된 데이터 없음")
            
            conn.close()
            print("  ✅ 과거 데이터 비교 완료")
            return True
            
        except Exception as e:
            print(f"  ⚠️ DB 접근 실패: {e}")
            return True  # DB 오류는 무시
    
    def check_all(self, debug=False):
        """전체 상태 체크"""
        print("\n" + "="*60)
        print("🏥 라방바 API 상태 진단 시작")
        print(f"📄 쿠키 업데이트: 2025-01-27")
        print(f"⚙️ 매출 0원 임계값: {self.ZERO_REVENUE_THRESHOLD}%")
        if debug:
            print("🔧 디버그 모드 활성화")
        print("="*60 + "\n")
        
        # 1. API 응답 체크
        api_data = self.check_api_response()
        
        # 2. 쿠키 체크
        self.check_cookie_validity()
        
        # 3. 데이터 품질 체크 (디버그 모드 전달)
        sample_data = None
        if api_data:
            sample_data = self.check_data_quality(api_data, debug=debug)
        
        # 4. 과거 데이터 비교
        self.check_historical_data()
        
        # 결과 종합
        print("\n" + "="*60)
        print("📊 진단 결과")
        print("="*60)
        
        status = "OK"
        if self.issues:
            status = "CRITICAL"
            print("❌ 심각한 문제:")
            for issue in self.issues:
                print(f"  - {issue}")
        
        if self.warnings:
            if status == "OK":
                status = "WARNING"
            print("⚠️ 경고 사항:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if status == "OK":
            print("✅ 모든 시스템 정상")
        
        print("="*60 + "\n")
        
        # 권장 조치
        recommendations = []
        if "쿠키" in str(self.issues):
            recommendations.append("브라우저에서 새로운 쿠키 값을 복사하여 업데이트")
        if "API 응답 코드" in str(self.issues):
            recommendations.append("API URL 또는 요청 방식 변경 확인 필요")
        if "매출 0원" in str(self.issues):
            recommendations.append("API 응답 필드명 변경 확인 (sales_amt, salesAmt 등)")
        
        return {
            'status': status,
            'issues': self.issues,
            'warnings': self.warnings,
            'recommendations': recommendations,
            'sample_data': sample_data,
            'timestamp': datetime.now().isoformat(),
            'zero_revenue_threshold': self.ZERO_REVENUE_THRESHOLD
        }


def main():
    """독립 실행용 메인 함수"""
    import sys
    
    # 디버그 모드 체크
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv
    
    checker = HealthChecker()
    result = checker.check_all(debug=debug_mode)
    
    # 결과를 JSON 파일로 저장
    with open('health_check_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"📄 결과가 health_check_result.json에 저장되었습니다")
    print(f"📊 매출 0원 임계값: {result['zero_revenue_threshold']}%")
    
    # 상태 코드 반환 (CI/CD 연동용)
    if result['status'] == 'CRITICAL':
        return 2
    elif result['status'] == 'WARNING':
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit(main())