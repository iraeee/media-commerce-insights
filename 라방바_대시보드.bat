@echo off
title 라방바 대시보드 실행
echo =====================================
echo    라방바 대시보드 실행 프로그램
echo =====================================
echo.

echo [1/3] GitHub에서 최신 데이터 다운로드 중...
python github_sync.py --download-only

echo.
echo [2/3] 데이터 확인 중...
python -c "import sqlite3; conn=sqlite3.connect('schedule.db'); cursor=conn.cursor(); cursor.execute('SELECT COUNT(*), MAX(date) FROM schedule'); total, last_date = cursor.fetchone(); print(f'총 레코드: {total:,}개\n최신 날짜: {last_date}')"

echo.
echo [3/3] 대시보드 실행 중...
echo.
echo 브라우저에서 http://localhost:8501 로 접속하세요
echo 종료하려면 Ctrl+C를 누르세요
echo.

REM 기존 run_and_backup_and_dashboard.py가 있으면 대시보드만 실행
if exist run_and_backup_and_dashboard.py (
    python run_and_backup_and_dashboard.py --dashboard-only
) else (
    streamlit run dashboard_main.py
)

pause
