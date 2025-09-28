"""
create_aggregate_tables.py - 대시보드 성능 최적화를 위한 집계 테이블 생성
Version: 1.0.0
Created: 2024-01-24

이 스크립트는 schedule.db에 사전 집계 테이블을 생성하여
대시보드 로딩 속도를 10배 이상 향상시킵니다.

"기타" 데이터는 집계에서 제외하여 의미 있는 데이터만 분석합니다.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

# ============================================================================
# 설정
# ============================================================================

# 생방송 채널 정의
LIVE_CHANNELS = {
    '현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', 
    '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑'
}

# 모델비 설정
MODEL_COST_LIVE = 10400000
MODEL_COST_NON_LIVE = 2000000

# 전환율 및 마진율 설정 - ROI 계산법 변경 (2025-02-03)
CONVERSION_RATE = 0.75      # 전환률 75%
PRODUCT_COST_RATE = 0.13    # 제품 원가율 13%
COMMISSION_RATE = 0.10      # 판매 수수료율 10%
REAL_MARGIN_RATE = (1 - COMMISSION_RATE - PRODUCT_COST_RATE) * CONVERSION_RATE  # 0.5775 (57.75%)

# ============================================================================
# 집계 테이블 생성 클래스
# ============================================================================

class AggregateTableCreator:
    def __init__(self, db_path="schedule.db"):
        """집계 테이블 생성기 초기화"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        
    def create_all_tables(self, exclude_others=True):
        """모든 집계 테이블 생성"""
        print("=" * 60)
        print("집계 테이블 생성 시작")
        print("=" * 60)
        
        # 기존 집계 테이블 삭제
        self._drop_existing_tables()
        
        # 원본 데이터 로드 및 전처리
        df = self._load_and_preprocess_data(exclude_others)
        
        if len(df) == 0:
            print("❌ 데이터가 없습니다.")
            return
        
        # 각 집계 테이블 생성
        self._create_daily_aggregate(df)
        self._create_hourly_aggregate(df)
        self._create_platform_aggregate(df)
        self._create_category_aggregate(df)
        self._create_platform_hourly_aggregate(df)
        self._create_category_hourly_aggregate(df)
        self._create_weekday_aggregate(df)
        self._create_monthly_aggregate(df)
        
        # 인덱스 생성
        self._create_indexes()
        
        # 통계 정보 저장
        self._save_statistics(df)
        
        print("\n✅ 모든 집계 테이블 생성 완료!")
        self.conn.close()
    
    def _drop_existing_tables(self):
        """기존 집계 테이블 삭제"""
        print("\n[1/9] 기존 집계 테이블 삭제 중...")
        
        tables = [
            'agg_daily', 'agg_hourly', 'agg_platform', 'agg_category',
            'agg_platform_hourly', 'agg_category_hourly', 'agg_weekday',
            'agg_monthly', 'agg_statistics'
        ]
        
        for table in tables:
            self.cur.execute(f"DROP TABLE IF EXISTS {table}")
        
        self.conn.commit()
        print("  ✓ 기존 테이블 삭제 완료")
    
    def _load_and_preprocess_data(self, exclude_others=True):
        """원본 데이터 로드 및 전처리"""
        print("\n[2/9] 원본 데이터 로드 중...")
        
        # 기타 제외 옵션에 따라 쿼리 수정
        if exclude_others:
            query = "SELECT * FROM schedule WHERE platform != '기타'"
            print("  ℹ️ '기타' 데이터 제외")
        else:
            query = "SELECT * FROM schedule"
        
        df = pd.read_sql_query(query, self.conn)
        print(f"  ✓ {len(df):,}개 레코드 로드")
        
        # 날짜 변환
        df['date'] = pd.to_datetime(df['date'])
        
        # 시간 관련 컬럼 생성
        df['hour'] = df['time'].str.split(':').str[0].astype(int)
        df['weekday'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.to_period('M').astype(str)
        df['week'] = df['date'].dt.to_period('W').astype(str)
        df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)
        
        # 채널 구분
        df['is_live'] = df['platform'].isin(LIVE_CHANNELS).astype(int)
        df['model_cost'] = df['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        
        # 비용 계산
        df['total_cost'] = df['cost'] + df['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df['real_profit'] = (df['revenue'] * REAL_MARGIN_RATE) - df['total_cost']
        
        # ROI 계산
        df['roi_calculated'] = np.where(
            df['total_cost'] > 0,
            (df['real_profit'] / df['total_cost']) * 100,
            0
        )
        
        # 효율성 계산
        df['efficiency'] = np.where(
            df['total_cost'] > 0,
            df['revenue'] / df['total_cost'],
            0
        )
        
        print("  ✓ 데이터 전처리 완료")
        print(f"  ℹ️ 실질 마진율: {REAL_MARGIN_RATE:.2%} 적용")
        return df
    
    def _create_daily_aggregate(self, df):
        """일별 집계 테이블 생성"""
        print("\n[3/9] 일별 집계 테이블 생성 중...")
        
        daily = df.groupby('date').agg({
            'revenue': ['sum', 'mean', 'std', 'min', 'max'],
            'units_sold': ['sum', 'mean'],
            'total_cost': 'sum',
            'real_profit': 'sum',
            'roi_calculated': 'mean',
            'efficiency': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        # 컬럼명 정리
        daily.columns = [
            'date', 'revenue_sum', 'revenue_mean', 'revenue_std', 'revenue_min', 'revenue_max',
            'units_sum', 'units_mean', 'cost_sum', 'profit_sum', 
            'roi_mean', 'efficiency_mean', 'broadcast_count'
        ]
        
        # 추가 지표
        daily['profit_rate'] = (daily['profit_sum'] / daily['revenue_sum'] * 100).fillna(0)
        daily['weekday'] = pd.to_datetime(daily['date']).dt.dayofweek
        daily['is_weekend'] = daily['weekday'].isin([5, 6]).astype(int)
        
        # DB 저장
        daily.to_sql('agg_daily', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(daily)}개 일별 레코드 저장")
    
    def _create_hourly_aggregate(self, df):
        """시간대별 집계 테이블 생성"""
        print("\n[4/9] 시간대별 집계 테이블 생성 중...")
        
        hourly = df.groupby('hour').agg({
            'revenue': ['sum', 'mean', 'std'],
            'units_sold': ['sum', 'mean'],
            'total_cost': 'sum',
            'real_profit': 'sum',
            'roi_calculated': 'mean',
            'efficiency': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        hourly.columns = [
            'hour', 'revenue_sum', 'revenue_mean', 'revenue_std',
            'units_sum', 'units_mean', 'cost_sum', 'profit_sum',
            'roi_mean', 'efficiency_mean', 'broadcast_count'
        ]
        
        # 안정성 지표 (변동계수의 역수)
        hourly['stability'] = np.where(
            hourly['revenue_mean'] > 0,
            1 / (1 + hourly['revenue_std'] / hourly['revenue_mean']),
            0
        )
        
        hourly.to_sql('agg_hourly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(hourly)}개 시간대별 레코드 저장")
    
    def _create_platform_aggregate(self, df):
        """방송사별 집계 테이블 생성"""
        print("\n[5/9] 방송사별 집계 테이블 생성 중...")
        
        platform = df.groupby('platform').agg({
            'revenue': ['sum', 'mean', 'std'],
            'units_sold': 'sum',
            'total_cost': 'sum',
            'real_profit': 'sum',
            'roi_calculated': 'mean',
            'efficiency': 'mean',
            'broadcast': 'count',
            'is_live': 'first'
        }).reset_index()
        
        platform.columns = [
            'platform', 'revenue_sum', 'revenue_mean', 'revenue_std',
            'units_sum', 'cost_sum', 'profit_sum', 'roi_mean',
            'efficiency_mean', 'broadcast_count', 'is_live'
        ]
        
        # 가중평균 ROI 계산
        platform['roi_weighted'] = (platform['profit_sum'] / platform['cost_sum'] * 100).fillna(0)
        
        # 채널 타입
        platform['channel_type'] = platform['is_live'].apply(
            lambda x: '생방송' if x else '비생방송'
        )
        
        platform.to_sql('agg_platform', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(platform)}개 방송사별 레코드 저장")
    
    def _create_category_aggregate(self, df):
        """카테고리별 집계 테이블 생성"""
        print("\n[6/9] 카테고리별 집계 테이블 생성 중...")
        
        category = df.groupby('category').agg({
            'revenue': ['sum', 'mean', 'std'],
            'units_sold': 'sum',
            'total_cost': 'sum',
            'real_profit': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        category.columns = [
            'category', 'revenue_sum', 'revenue_mean', 'revenue_std',
            'units_sum', 'cost_sum', 'profit_sum', 'roi_mean', 'broadcast_count'
        ]
        
        # 인기도 점수 (매출 + 빈도 고려)
        category['popularity_score'] = (
            category['revenue_sum'] / category['revenue_sum'].max() * 0.7 +
            category['broadcast_count'] / category['broadcast_count'].max() * 0.3
        ) * 100
        
        category.to_sql('agg_category', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(category)}개 카테고리별 레코드 저장")
    
    def _create_platform_hourly_aggregate(self, df):
        """방송사-시간대별 집계 테이블 생성"""
        print("\n[7/9] 방송사-시간대별 집계 테이블 생성 중...")
        
        platform_hourly = df.groupby(['platform', 'hour']).agg({
            'revenue': ['sum', 'mean'],
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        platform_hourly.columns = [
            'platform', 'hour', 'revenue_sum', 'revenue_mean',
            'roi_mean', 'broadcast_count'
        ]
        
        platform_hourly.to_sql('agg_platform_hourly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(platform_hourly)}개 방송사-시간대별 레코드 저장")
    
    def _create_category_hourly_aggregate(self, df):
        """카테고리-시간대별 집계 테이블 생성"""
        print("\n[8/9] 카테고리-시간대별 집계 테이블 생성 중...")
        
        category_hourly = df.groupby(['category', 'hour']).agg({
            'revenue': ['sum', 'mean'],
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        category_hourly.columns = [
            'category', 'hour', 'revenue_sum', 'revenue_mean',
            'roi_mean', 'broadcast_count'
        ]
        
        category_hourly.to_sql('agg_category_hourly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(category_hourly)}개 카테고리-시간대별 레코드 저장")
    
    def _create_weekday_aggregate(self, df):
        """요일별 집계 테이블 생성"""
        print("\n[9/9] 요일별 집계 테이블 생성 중...")
        
        weekday = df.groupby('weekday').agg({
            'revenue': ['sum', 'mean'],
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        weekday.columns = [
            'weekday', 'revenue_sum', 'revenue_mean',
            'units_sum', 'roi_mean', 'broadcast_count'
        ]
        
        # 요일명 추가
        weekday_names = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
        weekday['weekday_name'] = weekday['weekday'].map(weekday_names)
        
        weekday.to_sql('agg_weekday', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(weekday)}개 요일별 레코드 저장")
    
    def _create_monthly_aggregate(self, df):
        """월별 집계 테이블 생성"""
        print("\n[10/10] 월별 집계 테이블 생성 중...")
        
        monthly = df.groupby('month').agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'total_cost': 'sum',
            'real_profit': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        monthly.columns = [
            'month', 'revenue_sum', 'units_sum', 'cost_sum',
            'profit_sum', 'roi_mean', 'broadcast_count'
        ]
        
        monthly.to_sql('agg_monthly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ {len(monthly)}개 월별 레코드 저장")
    
    def _create_indexes(self):
        """인덱스 생성으로 쿼리 성능 향상"""
        print("\n인덱스 생성 중...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_agg_daily_date ON agg_daily(date)",
            "CREATE INDEX IF NOT EXISTS idx_agg_daily_weekday ON agg_daily(weekday)",
            "CREATE INDEX IF NOT EXISTS idx_agg_hourly_hour ON agg_hourly(hour)",
            "CREATE INDEX IF NOT EXISTS idx_agg_platform_name ON agg_platform(platform)",
            "CREATE INDEX IF NOT EXISTS idx_agg_platform_revenue ON agg_platform(revenue_sum DESC)",
            "CREATE INDEX IF NOT EXISTS idx_agg_category_name ON agg_category(category)",
            "CREATE INDEX IF NOT EXISTS idx_agg_platform_hourly ON agg_platform_hourly(platform, hour)",
            "CREATE INDEX IF NOT EXISTS idx_agg_category_hourly ON agg_category_hourly(category, hour)",
        ]
        
        for idx_query in indexes:
            self.cur.execute(idx_query)
        
        self.conn.commit()
        print("  ✓ 인덱스 생성 완료")
    
    def _save_statistics(self, df):
        """통계 정보 저장"""
        print("\n통계 정보 저장 중...")
        
        # 기타 제외 통계
        total_records = len(df)
        
        # 원본 데이터에서 기타 비율 계산
        self.cur.execute("SELECT COUNT(*) FROM schedule WHERE platform = '기타'")
        others_count = self.cur.fetchone()[0]
        
        self.cur.execute("SELECT COUNT(*) FROM schedule")
        total_original = self.cur.fetchone()[0]
        
        stats = {
            'created_at': datetime.now().isoformat(),
            'total_records': total_records,
            'others_excluded': others_count,
            'others_ratio': (others_count / total_original * 100) if total_original > 0 else 0,
            'date_range': f"{df['date'].min().date()} ~ {df['date'].max().date()}",
            'platforms': len(df['platform'].unique()),
            'categories': len(df['category'].unique()),
            'total_revenue': int(df['revenue'].sum()),
            'total_profit': int(df['real_profit'].sum()),
            'avg_roi': float(df['roi_calculated'].mean()),
            'real_margin_rate': REAL_MARGIN_RATE,  # 새로운 마진율 저장
            'conversion_rate': CONVERSION_RATE,     # 전환율 저장
            'product_cost_rate': PRODUCT_COST_RATE, # 제품 원가율 저장
            'commission_rate': COMMISSION_RATE      # 판매 수수료율 저장
        }
        
        # 통계 테이블 생성
        stats_df = pd.DataFrame([stats])
        stats_df.to_sql('agg_statistics', self.conn, if_exists='replace', index=False)
        
        print("\n" + "=" * 60)
        print("📊 집계 통계")
        print("=" * 60)
        print(f"생성 시각: {stats['created_at']}")
        print(f"처리 레코드: {stats['total_records']:,}개")
        print(f"제외된 '기타': {stats['others_excluded']:,}개 ({stats['others_ratio']:.1f}%)")
        print(f"기간: {stats['date_range']}")
        print(f"방송사: {stats['platforms']}개")
        print(f"카테고리: {stats['categories']}개")
        print(f"총 매출: {stats['total_revenue']:,}원")
        print(f"평균 ROI: {stats['avg_roi']:.2f}%")
        print(f"적용된 실질 마진율: {stats['real_margin_rate']:.2%}")

# ============================================================================
# 유틸리티 함수
# ============================================================================

def check_aggregate_tables(db_path="schedule.db"):
    """집계 테이블 상태 확인"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("\n" + "=" * 60)
    print("집계 테이블 상태 확인")
    print("=" * 60)
    
    # 테이블 목록
    tables = [
        'agg_daily', 'agg_hourly', 'agg_platform', 'agg_category',
        'agg_platform_hourly', 'agg_category_hourly', 'agg_weekday',
        'agg_monthly', 'agg_statistics'
    ]
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = cur.fetchone()[0] > 0
        
        if exists:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"✅ {table:20} : {count:8,} rows")
        else:
            print(f"❌ {table:20} : 없음")
    
    # 통계 정보 출력
    try:
        stats_df = pd.read_sql_query("SELECT * FROM agg_statistics", conn)
        if len(stats_df) > 0:
            stats = stats_df.iloc[0]
            print("\n📊 마지막 집계 정보:")
            print(f"  - 생성 시각: {stats['created_at']}")
            print(f"  - 제외된 '기타': {stats['others_excluded']:,}개")
            print(f"  - 기간: {stats['date_range']}")
            if 'real_margin_rate' in stats:
                print(f"  - 실질 마진율: {stats['real_margin_rate']:.2%}")
            if 'conversion_rate' in stats:
                print(f"  - 전환율: {stats['conversion_rate']:.0%}")
    except:
        pass
    
    conn.close()

def drop_aggregate_tables(db_path="schedule.db"):
    """모든 집계 테이블 삭제"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    tables = [
        'agg_daily', 'agg_hourly', 'agg_platform', 'agg_category',
        'agg_platform_hourly', 'agg_category_hourly', 'agg_weekday',
        'agg_monthly', 'agg_statistics'
    ]
    
    print("\n집계 테이블 삭제 중...")
    for table in tables:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  - {table} 삭제")
    
    conn.commit()
    conn.close()
    print("✅ 모든 집계 테이블 삭제 완료")

# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="대시보드 집계 테이블 생성")
    parser.add_argument("--db", default="schedule.db", help="데이터베이스 경로")
    parser.add_argument("--include-others", action="store_true", 
                       help="'기타' 데이터도 포함 (기본: 제외)")
    parser.add_argument("--check", action="store_true", 
                       help="집계 테이블 상태 확인")
    parser.add_argument("--drop", action="store_true", 
                       help="모든 집계 테이블 삭제")
    
    args = parser.parse_args()
    
    if args.check:
        check_aggregate_tables(args.db)
    elif args.drop:
        drop_aggregate_tables(args.db)
    else:
        # 집계 테이블 생성
        creator = AggregateTableCreator(args.db)
        creator.create_all_tables(exclude_others=not args.include_others)
        
        # 상태 확인
        check_aggregate_tables(args.db)
        
        print("\n" + "=" * 60)
        print("✨ 집계 테이블 생성 완료!")
        print("대시보드에서 집계 테이블을 사용하면 성능이 10배 이상 향상됩니다.")
        print("=" * 60)