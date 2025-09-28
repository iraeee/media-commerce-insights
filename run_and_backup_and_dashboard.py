"""
라방바 홈쇼핑 데이터 수집 및 대시보드 실행 스크립트
API 상태 체크 및 집계 테이블 자동 업데이트 통합 버전
Version: 2.1.0 - 0원 매출 경고 비율 50%로 상향
"""

import subprocess
import shutil
import os
import sys
import time
from datetime import datetime, timedelta
import sqlite3
import json

# health_check 모듈 import
try:
    from health_check import HealthChecker
except ImportError:
    print("⚠️ health_check.py 파일이 없습니다. 기본 모드로 실행합니다.")
    HealthChecker = None

# 집계 테이블 업데이트 모듈 import
try:
    from update_aggregate_tables import update_aggregates_if_needed
    AGGREGATE_AVAILABLE = True
except ImportError:
    print("⚠️ update_aggregate_tables.py 파일이 없습니다. 집계 테이블 업데이트를 건너뜁니다.")
    update_aggregates_if_needed = None
    AGGREGATE_AVAILABLE = False

class EnhancedRunner:
    """개선된 실행 관리자"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []
        # 0원 매출 경고 비율 기준 (50%로 상향)
        self.ZERO_REVENUE_WARNING_THRESHOLD = 50.0
        
    def print_status(self, message, status="INFO"):
        """상태 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "RUNNING": "🔄"
        }
        symbol = symbols.get(status, "📌")
        print(f"[{timestamp}] {symbol} {message}")
        
        # 에러/경고 수집
        if status == "ERROR":
            self.errors.append(message)
        elif status == "WARNING":
            self.warnings.append(message)
    
    def check_api_health(self):
        """API 상태 체크"""
        if not HealthChecker:
            self.print_status("Health Check 모듈 없이 진행", "WARNING")
            return True
            
        self.print_status("API 상태 점검 시작...", "RUNNING")
        
        try:
            checker = HealthChecker()
            check_result = checker.check_all()
            
            # 결과 분석
            if check_result['status'] == 'CRITICAL':
                print("\n" + "="*60)
                print("🚨 심각한 문제 발견!")
                print("="*60)
                
                for issue in check_result['issues']:
                    print(f"  ❌ {issue}")
                
                print("\n📋 권장 조치사항:")
                for action in check_result['recommendations']:
                    print(f"  → {action}")
                
                print("="*60)
                
                # 사용자 확인
                response = input("\n계속 진행하시겠습니까? (y/n): ")
                if response.lower() != 'y':
                    self.print_status("사용자가 실행을 취소했습니다", "WARNING")
                    return False
                    
            elif check_result['status'] == 'WARNING':
                print("\n" + "="*60)
                print("⚠️ 경고 사항 발견")
                print("="*60)
                
                for issue in check_result['issues']:
                    print(f"  ⚠️ {issue}")
                    self.warnings.append(issue)
                
                print("="*60)
                time.sleep(3)  # 3초 대기
                
            else:  # OK
                self.print_status("API 상태 정상 ✨", "SUCCESS")
                
            # 샘플 데이터 표시
            if 'sample_data' in check_result and check_result['sample_data']:
                print("\n📊 수집된 샘플 데이터:")
                sample = check_result['sample_data']
                print(f"  - 날짜: {sample.get('date', 'N/A')}")
                print(f"  - 시간: {sample.get('time', 'N/A')}")
                print(f"  - 방송: {sample.get('broadcast', 'N/A')[:50]}...")
                print(f"  - 매출: {sample.get('revenue', 0):,}원")
                
            return True
            
        except Exception as e:
            self.print_status(f"Health Check 실행 실패: {e}", "ERROR")
            return True  # 체크 실패해도 계속 진행
    
    def run_scrape_schedule(self):
        """데이터 수집 실행"""
        self.print_status("데이터 수집 시작...", "RUNNING")
        
        try:
            # 오늘 날짜로 실행
            today = datetime.now().strftime("%y%m%d")
            
            result = subprocess.run(
                [sys.executable, "scrape_schedule.py", "--date", today, "--debug"],
                capture_output=True,
                text=True,
                timeout=60  # 60초 타임아웃
            )
            
            # 결과 분석
            if "매출 0원 항목" in result.stdout:
                # 0원 비율 체크
                lines = result.stdout.split('\n')
                for line in lines:
                    if "매출 0원 항목:" in line:
                        try:
                            # "매출 0원 항목: 223개 (46.5%)" 형태에서 퍼센트 추출
                            percent_str = line.split('(')[1].split('%')[0]
                            zero_percent = float(percent_str)
                            
                            # 50%로 기준 상향 조정
                            if zero_percent > self.ZERO_REVENUE_WARNING_THRESHOLD:
                                self.print_status(
                                    f"매출 0원 비율이 {zero_percent}%로 높습니다! (기준: {self.ZERO_REVENUE_WARNING_THRESHOLD}%)", 
                                    "WARNING"
                                )
                                self.warnings.append(f"매출 0원 비율: {zero_percent}%")
                            else:
                                self.print_status(
                                    f"매출 0원 비율: {zero_percent}% (정상 범위)", 
                                    "INFO"
                                )
                        except:
                            pass
            
            if result.returncode != 0:
                self.print_status("데이터 수집 실패!", "ERROR")
                print("📤 오류 내용:")
                print(result.stderr)
                return False
            else:
                # 성공 메시지에서 데이터 수 추출
                if "완료" in result.stdout and "개 방송 데이터" in result.stdout:
                    self.print_status("데이터 수집 성공", "SUCCESS")
                return True
                
        except subprocess.TimeoutExpired:
            self.print_status("데이터 수집 시간 초과 (60초)", "ERROR")
            return False
        except Exception as e:
            self.print_status(f"데이터 수집 중 오류: {e}", "ERROR")
            return False
    
    def update_aggregate_tables(self):
        """집계 테이블 자동 업데이트"""
        self.print_status("집계 테이블 업데이트 확인 중...", "RUNNING")
        
        if not AGGREGATE_AVAILABLE:
            self.print_status("집계 테이블 모듈이 없어 건너뜁니다", "WARNING")
            return False
        
        try:
            # 집계 테이블 존재 여부 확인
            conn = sqlite3.connect("schedule.db")
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='agg_daily'
            """)
            has_agg_tables = cur.fetchone()[0] > 0
            conn.close()
            
            if not has_agg_tables:
                # 집계 테이블이 없으면 생성
                self.print_status("집계 테이블이 없습니다. 생성을 시작합니다...", "INFO")
                try:
                    from create_aggregate_tables import AggregateTableCreator
                    creator = AggregateTableCreator("schedule.db")
                    creator.create_all_tables()
                    self.print_status("집계 테이블 생성 완료", "SUCCESS")
                except ImportError:
                    self.print_status("create_aggregate_tables.py가 필요합니다", "WARNING")
                    return False
                except Exception as e:
                    self.print_status(f"집계 테이블 생성 실패: {e}", "WARNING")
                    return False
            
            # 집계 테이블 업데이트 필요 여부 확인 및 실행
            result = update_aggregates_if_needed("schedule.db")
            
            if result:
                self.print_status("집계 테이블 업데이트 완료", "SUCCESS")
                
                # 업데이트 통계 출력
                conn = sqlite3.connect("schedule.db")
                cur = conn.cursor()
                
                today = datetime.now().strftime('%Y-%m-%d')
                cur.execute(f"""
                    SELECT revenue_sum, broadcast_count 
                    FROM agg_daily 
                    WHERE date = '{today}'
                """)
                result = cur.fetchone()
                
                if result:
                    revenue, count = result
                    self.print_status(
                        f"오늘 집계: {count}건, 매출 {revenue:,.0f}원", 
                        "INFO"
                    )
                
                # 전체 통계
                cur.execute("SELECT * FROM agg_statistics")
                stats = cur.fetchone()
                if stats:
                    self.print_status(
                        f"전체 기간: {stats[4]}, 총 {stats[1]:,}건", 
                        "INFO"
                    )
                
                conn.close()
            else:
                self.print_status("집계 테이블이 이미 최신 상태", "INFO")
            
            return True
                
        except Exception as e:
            self.print_status(f"집계 테이블 업데이트 실패: {e}", "WARNING")
            self.warnings.append(f"집계 테이블 업데이트 실패: {e}")
            return False
    
    def backup_db(self):
        """DB 백업"""
        self.print_status("데이터베이스 백업 중...", "RUNNING")
        
        try:
            db_path = "schedule.db"
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # 백업 파일명 (시간 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"schedule_{timestamp}.db")
            
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_path)
                
                # 백업 파일 크기 확인
                file_size = os.path.getsize(backup_path) / 1024 / 1024  # MB
                self.print_status(f"백업 완료: {backup_path} ({file_size:.2f}MB)", "SUCCESS")
                
                # 오래된 백업 정리 (30일 이상)
                self.cleanup_old_backups(backup_dir, days=30)
                return True
            else:
                self.print_status("schedule.db 파일이 없습니다", "ERROR")
                return False
                
        except Exception as e:
            self.print_status(f"백업 실패: {e}", "ERROR")
            return False
    
    def cleanup_old_backups(self, backup_dir, days=30):
        """오래된 백업 파일 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned = 0
            
            for filename in os.listdir(backup_dir):
                filepath = os.path.join(backup_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_date:
                    os.remove(filepath)
                    cleaned += 1
            
            if cleaned > 0:
                self.print_status(f"{cleaned}개의 오래된 백업 파일 삭제", "INFO")
                
        except Exception as e:
            self.print_status(f"백업 정리 중 오류: {e}", "WARNING")
    
    def check_recent_data(self):
        """최근 데이터 확인"""
        self.print_status("최근 수집 데이터 확인 중...", "RUNNING")
        
        try:
            conn = sqlite3.connect("schedule.db")
            cursor = conn.cursor()
            
            # 오늘 데이터 확인
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT COUNT(*), SUM(revenue), AVG(revenue)
                FROM schedule
                WHERE date = ?
            """, (today,))
            
            count, total_revenue, avg_revenue = cursor.fetchone()
            
            if count and count > 0:
                self.print_status(f"오늘 수집: {count}건, 총 매출: {total_revenue:,.0f}원", "INFO")
                
                # 매출 0원 비율 체크 (50% 기준)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM schedule
                    WHERE date = ? AND revenue = 0
                """, (today,))
                
                zero_count = cursor.fetchone()[0]
                zero_percent = (zero_count / count) * 100
                
                if zero_percent > self.ZERO_REVENUE_WARNING_THRESHOLD:
                    self.print_status(
                        f"매출 0원 비율이 {zero_percent:.1f}%로 높습니다 (기준: {self.ZERO_REVENUE_WARNING_THRESHOLD}%)", 
                        "WARNING"
                    )
                else:
                    self.print_status(
                        f"매출 0원 비율: {zero_percent:.1f}% (정상 범위)", 
                        "INFO"
                    )
            else:
                self.print_status("오늘 수집된 데이터가 없습니다", "WARNING")
            
            conn.close()
            
        except Exception as e:
            self.print_status(f"데이터 확인 실패: {e}", "WARNING")
    
    def launch_dashboard(self):
        """대시보드 실행"""
        self.print_status("대시보드 준비 중...", "RUNNING")
        
        # 최종 상태 표시
        print("\n" + "="*60)
        print("📊 실행 결과 요약")
        print("="*60)
        
        total_time = (datetime.now() - self.start_time).total_seconds()
        print(f"⏱️ 총 소요시간: {total_time:.1f}초")
        print(f"📌 0원 매출 경고 기준: {self.ZERO_REVENUE_WARNING_THRESHOLD}%")
        
        if self.errors:
            print(f"\n❌ 오류 {len(self.errors)}건:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️ 경고 {len(self.warnings)}건:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors:
            print("\n✨ 모든 작업이 정상적으로 완료되었습니다!")
        
        # 집계 테이블 상태 표시
        if AGGREGATE_AVAILABLE:
            print("\n📊 집계 테이블 상태:")
            print("  ✅ 집계 테이블 사용 가능 (10배 성능 향상)")
            print("  ✅ 오늘 데이터는 실시간 처리")
        else:
            print("\n⚠️ 집계 테이블 미사용 (표준 성능)")
        
        print("="*60)
        
        # 대시보드 실행
        print("\n🚀 대시보드를 실행합니다...")
        print("💡 브라우저가 자동으로 열립니다. 잠시만 기다려주세요...")
        
        try:
            subprocess.run(["streamlit", "run", "dashboard_main.py"])
        except KeyboardInterrupt:
            self.print_status("대시보드가 종료되었습니다", "INFO")
        except Exception as e:
            self.print_status(f"대시보드 실행 실패: {e}", "ERROR")
    
    def run(self):
        """전체 프로세스 실행"""
        print("\n" + "="*60)
        print("🚀 라방바 데이터 수집 및 대시보드 시스템")
        print("="*60)
        print(f"📅 실행시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⚙️ 0원 매출 경고 기준: {self.ZERO_REVENUE_WARNING_THRESHOLD}%")
        print("="*60 + "\n")
        
        # 1. API 상태 체크
        if not self.check_api_health():
            print("\n⛔ API 상태 체크 실패로 실행을 중단합니다.")
            return
        
        print()  # 줄바꿈
        
        # 2. 데이터 수집
        if not self.run_scrape_schedule():
            print("\n⚠️ 데이터 수집에 실패했지만 계속 진행합니다...")
        
        print()  # 줄바꿈
        
        # 2-1. 집계 테이블 업데이트
        self.update_aggregate_tables()
        
        print()  # 줄바꿈
        
        # 3. DB 백업
        if not self.backup_db():
            print("\n⚠️ 백업에 실패했지만 계속 진행합니다...")
        
        print()  # 줄바꿈
        
        # 4. 최근 데이터 확인
        self.check_recent_data()
        
        print()  # 줄바꿈
        
        # 5. 대시보드 실행
        self.launch_dashboard()


def main():
    """메인 함수"""
    runner = EnhancedRunner()
    
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램이 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()