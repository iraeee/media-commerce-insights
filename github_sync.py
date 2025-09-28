"""
GitHub DB 동기화 및 대시보드 실행
더블클릭으로 실행 가능
"""

import os
import sys
import subprocess
import requests
from datetime import datetime

class SimpleRunner:
    def __init__(self):
        self.config_file = "github_config.txt"
        self.repo_url = self.load_config()
        
    def load_config(self):
        """저장된 설정 로드 또는 입력받기"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return f.read().strip()
        else:
            print("="*60)
            print("🚀 라방바 대시보드 - 초기 설정")
            print("="*60)
            print("\nGitHub 저장소 URL을 입력하세요.")
            print("예: https://github.com/username/labangba-scraper")
            url = input("\nURL: ").strip()
            
            with open(self.config_file, 'w') as f:
                f.write(url)
            
            print("✅ 설정 저장 완료!")
            return url
    
    def download_latest_db(self):
        """GitHub에서 최신 DB 다운로드"""
        print("\n📥 최신 데이터 다운로드 중...")
        
        # Raw URL 생성
        raw_url = self.repo_url.replace("github.com", "raw.githubusercontent.com")
        raw_url = f"{raw_url}/main/schedule.db.zst"
        
        try:
            # 다운로드
            response = requests.get(raw_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open('schedule.db.zst', 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 진행률 표시
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f'\r   진행률: {percent:.1f}%', end='')
            
            print(f'\n✅ 다운로드 완료!')
            
            # 압축 해제
            print("📦 압축 해제 중...")
            
            # zstd 명령어 시도
            if os.system("zstd -d schedule.db.zst -o schedule.db --force >nul 2>&1") == 0:
                print("✅ 압축 해제 완료!")
                return True
            
            # Python zstandard 시도
            try:
                import zstandard as zstd
                with open('schedule.db.zst', 'rb') as compressed:
                    dctx = zstd.ZstdDecompressor()
                    with open('schedule.db', 'wb') as output:
                        dctx.copy_stream(compressed, output)
                print("✅ 압축 해제 완료!")
                return True
            except ImportError:
                print("\n⚠️ zstandard가 설치되어 있지 않습니다.")
                print("설치 중...")
                os.system(f"{sys.executable} -m pip install zstandard")
                return self.download_latest_db()  # 재시도
                
        except requests.exceptions.RequestException as e:
            print(f"\n❌ 다운로드 실패: {e}")
            print("기존 로컬 DB를 사용합니다.")
            return False
    
    def show_db_status(self):
        """DB 상태 표시"""
        if not os.path.exists('schedule.db'):
            print("❌ DB 파일이 없습니다!")
            return False
        
        try:
            import sqlite3
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            
            # 통계
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    MAX(date) as last_date,
                    MIN(date) as first_date,
                    COUNT(DISTINCT date) as days
                FROM schedule
            """)
            
            total, last_date, first_date, days = cursor.fetchone()
            
            # 오늘 데이터
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM schedule WHERE date = ?", (today,))
            today_count = cursor.fetchone()[0]
            
            print("\n" + "="*60)
            print("📊 데이터베이스 현황")
            print("="*60)
            print(f"총 레코드: {total:,}개")
            print(f"기간: {first_date} ~ {last_date} ({days}일)")
            print(f"오늘 데이터: {today_count:,}개")
            
            # 오늘 데이터 없으면 경고
            if today_count == 0 and datetime.now().hour >= 0:
                print("\n⚠️ 오늘 데이터가 없습니다!")
                print("   GitHub Actions가 23:56에 자동 수집합니다.")
            
            print("="*60)
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ DB 확인 실패: {e}")
            return False
    
    def run_dashboard(self):
        """대시보드 실행"""
        print("\n🚀 대시보드 실행 중...")
        print("-"*60)
        print("브라우저에서 http://localhost:8501 접속")
        print("종료하려면 Ctrl+C를 누르세요")
        print("-"*60)
        
        # 기존 run_and_backup_and_dashboard.py 있으면 우선 실행
        if os.path.exists('run_and_backup_and_dashboard.py'):
            # 대시보드만 실행 (크롤링 안함)
            subprocess.run([sys.executable, 'run_and_backup_and_dashboard.py', '--dashboard-only'])
        elif os.path.exists('dashboard_main.py'):
            # Streamlit 실행
            subprocess.run(['streamlit', 'run', 'dashboard_main.py'])
        else:
            print("❌ 대시보드 파일을 찾을 수 없습니다!")
            print("   dashboard_main.py 또는 run_and_backup_and_dashboard.py가 필요합니다.")
    
    def run(self):
        """메인 실행"""
        print("="*60)
        print("🎯 라방바 대시보드 (GitHub 연동)")
        print("="*60)
        
        # 1. 최신 DB 다운로드
        self.download_latest_db()
        
        # 2. DB 상태 확인
        if not self.show_db_status():
            input("\n종료하려면 Enter...")
            return
        
        # 3. 대시보드 실행 여부 확인
        print("\n대시보드를 실행하시겠습니까?")
        print("1. 예 - 대시보드 실행")
        print("2. 아니오 - DB 다운로드만")
        
        choice = input("\n선택 (1 또는 2): ").strip()
        
        if choice == '1' or choice == '':
            self.run_dashboard()
        else:
            print("\n✅ DB 다운로드 완료!")
            print("   schedule.db 파일이 최신으로 업데이트되었습니다.")
        
        input("\n종료하려면 Enter...")

def main():
    """진입점"""
    # 명령행 인자 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == '--download-only':
            runner = SimpleRunner()
            runner.download_latest_db()
            runner.show_db_status()
            return
    
    # 일반 실행
    runner = SimpleRunner()
    runner.run()

if __name__ == "__main__":
    main()
