"""
ROI 계산 오류를 수정하는 통합 스크립트
schedule 테이블의 모든 ROI 관련 컬럼을 올바르게 재계산합니다.
"""

import sqlite3
import pandas as pd
from datetime import datetime
import numpy as np

# ============================================================================
# ROI 계산 관련 상수 정의
# ============================================================================

# 전환율 및 비용 구조
CONVERSION_RATE = 0.75      # 전환률 75%
PRODUCT_COST_RATE = 0.13    # 제품 원가율 13%
COMMISSION_RATE = 0.10      # 판매 수수료율 10%

# 실질 마진율 계산
REAL_MARGIN_RATE = (1 - COMMISSION_RATE - PRODUCT_COST_RATE) * CONVERSION_RATE
# REAL_MARGIN_RATE = 0.5775 (57.75%)

# 생방송 채널 정의
LIVE_CHANNELS = {
    '현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', 
    '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑'
}

# 모델비 정의
MODEL_COST_LIVE = 10400000      # 생방송: 1,040만원
MODEL_COST_NON_LIVE = 2000000   # 비생방송: 200만원

def fix_roi_calculations(db_path="schedule.db"):
    """모든 ROI 관련 컬럼을 수정"""
    
    print("=" * 60)
    print("🔧 ROI 계산 오류 수정 시작")
    print("=" * 60)
    print(f"실질 마진율: {REAL_MARGIN_RATE*100:.2f}%")
    print(f"계산식: ROI = ((매출×{REAL_MARGIN_RATE:.4f}) - (방송비+모델비)) / (방송비+모델비) × 100")
    print()
    
    # DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. roi_calculated 컬럼이 없으면 추가
    cursor.execute("PRAGMA table_info(schedule)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'roi_calculated' not in columns:
        print("📌 roi_calculated 컬럼 추가 중...")
        cursor.execute("ALTER TABLE schedule ADD COLUMN roi_calculated REAL DEFAULT 0")
    
    if 'real_profit' not in columns:
        print("📌 real_profit 컬럼 추가 중...")
        cursor.execute("ALTER TABLE schedule ADD COLUMN real_profit REAL DEFAULT 0")
    
    if 'model_cost' not in columns:
        print("📌 model_cost 컬럼 추가 중...")
        cursor.execute("ALTER TABLE schedule ADD COLUMN model_cost REAL DEFAULT 0")
    
    if 'total_cost' not in columns:
        print("📌 total_cost 컬럼 추가 중...")
        cursor.execute("ALTER TABLE schedule ADD COLUMN total_cost REAL DEFAULT 0")
    
    # 2. 모든 데이터 로드
    df = pd.read_sql_query("SELECT * FROM schedule", conn)
    print(f"\n📊 총 {len(df)}개 레코드 처리 중...")
    
    # 3. 계산 수행
    # 생방송 여부 판별
    df['is_live'] = df['platform'].isin(LIVE_CHANNELS)
    
    # 모델비 계산
    df['model_cost'] = df['is_live'].apply(
        lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
    )
    
    # 총 비용 계산
    df['total_cost'] = df['cost'] + df['model_cost']
    
    # 실질 수익 계산
    df['real_profit'] = (df['revenue'] * REAL_MARGIN_RATE) - df['total_cost']
    
    # ROI 계산
    df['roi_calculated'] = np.where(
        df['total_cost'] > 0,
        (df['real_profit'] / df['total_cost']) * 100,
        0
    )
    
    # roi 컬럼도 동일하게 업데이트 (일관성 유지)
    df['roi'] = df['roi_calculated']
    
    # 4. 예시 데이터 확인 (NS홈쇼핑 케이스)
    ns_example = df[
        (df['date'] == '2025-06-24') & 
        (df['time'] == '07:25') & 
        (df['platform'] == 'NS홈쇼핑')
    ]
    
    if not ns_example.empty:
        row = ns_example.iloc[0]
        print("\n📋 문제 케이스 검증 (2025-06-24 07:25 NS홈쇼핑):")
        print(f"  매출액: {row['revenue']:,.0f}원")
        print(f"  방송비: {row['cost']:,.0f}원")
        print(f"  모델비: {row['model_cost']:,.0f}원")
        print(f"  총비용: {row['total_cost']:,.0f}원")
        print(f"  실질수익: {row['real_profit']:,.0f}원")
        print(f"  계산된 ROI: {row['roi_calculated']:.2f}%")
        print(f"  기존 ROI: {row['roi']:.2f}%")
    
    # 5. DB에 업데이트
    print("\n💾 데이터베이스 업데이트 중...")
    
    # 방법 1: 전체 테이블 교체 (빠르지만 위험할 수 있음)
    # df.to_sql('schedule', conn, if_exists='replace', index=False)
    
    # 방법 2: 개별 업데이트 (안전함)
    update_count = 0
    for index, row in df.iterrows():
        cursor.execute("""
            UPDATE schedule 
            SET model_cost = ?, 
                total_cost = ?, 
                real_profit = ?, 
                roi_calculated = ?,
                roi = ?
            WHERE id = ?
        """, (
            row['model_cost'],
            row['total_cost'],
            row['real_profit'],
            row['roi_calculated'],
            row['roi_calculated'],  # roi도 동일하게 설정
            row['id']
        ))
        
        update_count += 1
        if update_count % 1000 == 0:
            print(f"  - {update_count}개 완료...")
    
    # 6. 커밋
    conn.commit()
    
    # 7. 통계 출력
    cursor.execute("""
        SELECT 
            AVG(roi_calculated) as avg_roi,
            MAX(roi_calculated) as max_roi,
            MIN(roi_calculated) as min_roi,
            COUNT(*) as total_count,
            COUNT(CASE WHEN roi_calculated > 0 THEN 1 END) as positive_count,
            COUNT(CASE WHEN roi_calculated < 0 THEN 1 END) as negative_count
        FROM schedule
        WHERE revenue > 0 AND total_cost > 0
    """)
    
    stats = cursor.fetchone()
    
    print("\n📊 수정 완료 통계:")
    print(f"  평균 ROI: {stats[0]:.2f}%")
    print(f"  최대 ROI: {stats[1]:.2f}%")
    print(f"  최소 ROI: {stats[2]:.2f}%")
    print(f"  전체 건수: {stats[3]:,}건")
    print(f"  양수 ROI: {stats[4]:,}건")
    print(f"  음수 ROI: {stats[5]:,}건")
    
    conn.close()
    
    print("\n✅ ROI 계산 수정 완료!")
    print("📌 이제 집계 테이블도 업데이트해야 합니다.")
    print("   다음 명령을 실행하세요:")
    print("   python update_aggregate_tables.py")
    
    return True

def verify_fix(db_path="schedule.db"):
    """수정 결과 검증"""
    conn = sqlite3.connect(db_path)
    
    # NS홈쇼핑 케이스 재확인
    query = """
        SELECT date, time, platform, broadcast, revenue, cost, 
               model_cost, total_cost, real_profit, roi_calculated, roi
        FROM schedule
        WHERE date = '2025-06-24' 
          AND time = '07:25' 
          AND platform = 'NS홈쇼핑'
          AND broadcast LIKE '%텀블러믹서기%'
    """
    
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        print("\n🔍 수정 결과 검증:")
        for _, row in df.iterrows():
            print(f"\n상품: {row['broadcast'][:30]}...")
            print(f"매출: {row['revenue']:,.0f}원")
            print(f"방송비: {row['cost']:,.0f}원")
            print(f"모델비: {row['model_cost']:,.0f}원")
            print(f"총비용: {row['total_cost']:,.0f}원")
            print(f"실질수익: {row['real_profit']:,.0f}원")
            print(f"ROI: {row['roi_calculated']:.2f}%")
            
            # 수동 계산 검증
            manual_profit = (row['revenue'] * REAL_MARGIN_RATE) - row['total_cost']
            manual_roi = (manual_profit / row['total_cost']) * 100 if row['total_cost'] > 0 else 0
            
            print(f"\n검증 계산:")
            print(f"  실질마진: {row['revenue'] * REAL_MARGIN_RATE:,.0f}원")
            print(f"  수동계산 ROI: {manual_roi:.2f}%")
            print(f"  차이: {abs(row['roi_calculated'] - manual_roi):.2f}%")
    
    conn.close()

if __name__ == "__main__":
    import shutil
    import os
    
    # 백업 생성
    if os.path.exists("schedule.db"):
        backup_name = f"schedule_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2("schedule.db", backup_name)
        print(f"💾 백업 생성: {backup_name}\n")
    
    # ROI 수정 실행
    try:
        if fix_roi_calculations():
            verify_fix()
            print("\n✨ 모든 작업 완료!")
            print("📌 대시보드를 새로고침하면 올바른 ROI가 표시됩니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("백업 파일에서 복원할 수 있습니다.")