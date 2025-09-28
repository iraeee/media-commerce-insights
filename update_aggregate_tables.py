"""
update_aggregate_tables.py - 집계 테이블 증분 업데이트 스크립트
Version: 1.0.0
Created: 2024-01-25

오늘 데이터만 집계 테이블에 추가/업데이트하는 스크립트
run_and_backup_and_dashboard.py와 함께 사용
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
# 증분 업데이트 클래스
# ============================================================================

class AggregateTableUpdater:
    def __init__(self, db_path="schedule.db"):
        """집계 테이블 업데이터 초기화"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self.today = datetime.now().strftime('%Y-%m-%d')
        
    def update_today_only(self):
        """오늘 데이터만 집계 테이블에 업데이트"""
        print("=" * 60)
        print(f"집계 테이블 증분 업데이트 - {self.today}")
        print("=" * 60)
        
        # 집계 테이블 존재 확인
        if not self._check_aggregate_tables():
            print("❌ 집계 테이블이 없습니다. create_aggregate_tables.py를 먼저 실행하세요.")
            return False
        
        # 오늘 데이터 로드 및 전처리
        df_today = self._load_today_data()
        
        if len(df_today) == 0:
            print("ℹ️ 오늘 데이터가 없습니다.")
            return False
        
        print(f"✓ 오늘 데이터 {len(df_today)}개 레코드 발견")
        print(f"ℹ️ 실질 마진율: {REAL_MARGIN_RATE:.2%} 적용")
        
        # 각 집계 테이블 업데이트
        self._update_daily_aggregate(df_today)
        self._update_hourly_aggregate(df_today)
        self._update_platform_aggregate(df_today)
        self._update_category_aggregate(df_today)
        self._update_platform_hourly_aggregate(df_today)
        self._update_category_hourly_aggregate(df_today)
        self._update_weekday_aggregate(df_today)
        self._update_monthly_aggregate(df_today)
        self._update_statistics()
        
        self.conn.commit()
        print("\n✅ 집계 테이블 업데이트 완료!")
        
        # 업데이트 결과 확인
        self._verify_update()
        
        self.conn.close()
        return True
    
    def _check_aggregate_tables(self):
        """집계 테이블 존재 여부 확인"""
        required_tables = [
            'agg_daily', 'agg_hourly', 'agg_platform', 'agg_category',
            'agg_platform_hourly', 'agg_category_hourly', 'agg_weekday',
            'agg_monthly', 'agg_statistics'
        ]
        
        for table in required_tables:
            self.cur.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            if self.cur.fetchone()[0] == 0:
                return False
        return True
    
    def _load_today_data(self):
        """오늘 데이터 로드 및 전처리"""
        query = f"""
            SELECT * FROM schedule 
            WHERE date = '{self.today}' 
            AND platform != '기타'
        """
        
        df = pd.read_sql_query(query, self.conn)
        
        if len(df) == 0:
            return df
        
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
        
        return df
    
    def _update_daily_aggregate(self, df):
        """일별 집계 업데이트"""
        print("\n[1/9] 일별 집계 업데이트 중...")
        
        # 기존 오늘 데이터 삭제
        self.cur.execute(f"DELETE FROM agg_daily WHERE date = '{self.today}'")
        
        # 새로운 집계 삽입
        daily = df.groupby('date').agg({
            'revenue': ['sum', 'mean', 'std', 'min', 'max'],
            'units_sold': ['sum', 'mean'],
            'total_cost': 'sum',
            'real_profit': 'sum',
            'roi_calculated': 'mean',
            'efficiency': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        daily.columns = [
            'date', 'revenue_sum', 'revenue_mean', 'revenue_std', 'revenue_min', 'revenue_max',
            'units_sum', 'units_mean', 'cost_sum', 'profit_sum', 
            'roi_mean', 'efficiency_mean', 'broadcast_count'
        ]
        
        daily['profit_rate'] = (daily['profit_sum'] / daily['revenue_sum'] * 100).fillna(0)
        daily['weekday'] = pd.to_datetime(daily['date']).dt.dayofweek
        daily['is_weekend'] = daily['weekday'].isin([5, 6]).astype(int)
        
        # DB에 삽입
        daily.to_sql('agg_daily', self.conn, if_exists='append', index=False)
        print(f"  ✓ 일별 집계 업데이트 완료")
    
    def _update_hourly_aggregate(self, df):
        """시간대별 집계 업데이트"""
        print("[2/9] 시간대별 집계 업데이트 중...")
        
        # 전체 데이터 다시 계산 (누적이므로)
        all_data_query = "SELECT * FROM schedule WHERE platform != '기타'"
        df_all = pd.read_sql_query(all_data_query, self.conn)
        
        # 전처리 (간략화)
        df_all['hour'] = df_all['time'].str.split(':').str[0].astype(int)
        df_all['is_live'] = df_all['platform'].isin(LIVE_CHANNELS).astype(int)
        df_all['model_cost'] = df_all['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        df_all['total_cost'] = df_all['cost'] + df_all['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df_all['real_profit'] = (df_all['revenue'] * REAL_MARGIN_RATE) - df_all['total_cost']
        df_all['roi_calculated'] = np.where(
            df_all['total_cost'] > 0,
            (df_all['real_profit'] / df_all['total_cost']) * 100,
            0
        )
        df_all['efficiency'] = np.where(
            df_all['total_cost'] > 0,
            df_all['revenue'] / df_all['total_cost'],
            0
        )
        
        # 시간대별 집계
        hourly = df_all.groupby('hour').agg({
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
        
        hourly['stability'] = np.where(
            hourly['revenue_mean'] > 0,
            1 / (1 + hourly['revenue_std'] / hourly['revenue_mean']),
            0
        )
        
        # 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_hourly")
        hourly.to_sql('agg_hourly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ 시간대별 집계 업데이트 완료")
    
    def _update_platform_aggregate(self, df):
        """방송사별 집계 업데이트"""
        print("[3/9] 방송사별 집계 업데이트 중...")
        
        # 전체 데이터 다시 계산
        all_data_query = "SELECT * FROM schedule WHERE platform != '기타'"
        df_all = pd.read_sql_query(all_data_query, self.conn)
        
        # 전처리
        df_all['is_live'] = df_all['platform'].isin(LIVE_CHANNELS).astype(int)
        df_all['model_cost'] = df_all['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        df_all['total_cost'] = df_all['cost'] + df_all['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df_all['real_profit'] = (df_all['revenue'] * REAL_MARGIN_RATE) - df_all['total_cost']
        df_all['roi_calculated'] = np.where(
            df_all['total_cost'] > 0,
            (df_all['real_profit'] / df_all['total_cost']) * 100,
            0
        )
        df_all['efficiency'] = np.where(
            df_all['total_cost'] > 0,
            df_all['revenue'] / df_all['total_cost'],
            0
        )
        
        # 방송사별 집계
        platform = df_all.groupby('platform').agg({
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
        
        platform['roi_weighted'] = (platform['profit_sum'] / platform['cost_sum'] * 100).fillna(0)
        platform['channel_type'] = platform['is_live'].apply(
            lambda x: '생방송' if x else '비생방송'
        )
        
        # 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_platform")
        platform.to_sql('agg_platform', self.conn, if_exists='replace', index=False)
        print(f"  ✓ 방송사별 집계 업데이트 완료")
    
    def _update_category_aggregate(self, df):
        """카테고리별 집계 업데이트"""
        print("[4/9] 카테고리별 집계 업데이트 중...")
        
        # 전체 데이터 다시 계산
        all_data_query = "SELECT * FROM schedule WHERE platform != '기타'"
        df_all = pd.read_sql_query(all_data_query, self.conn)
        
        # 전처리
        df_all['is_live'] = df_all['platform'].isin(LIVE_CHANNELS).astype(int)
        df_all['model_cost'] = df_all['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        df_all['total_cost'] = df_all['cost'] + df_all['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df_all['real_profit'] = (df_all['revenue'] * REAL_MARGIN_RATE) - df_all['total_cost']
        df_all['roi_calculated'] = np.where(
            df_all['total_cost'] > 0,
            (df_all['real_profit'] / df_all['total_cost']) * 100,
            0
        )
        
        # 카테고리별 집계
        category = df_all.groupby('category').agg({
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
        
        # 인기도 점수
        category['popularity_score'] = (
            category['revenue_sum'] / category['revenue_sum'].max() * 0.7 +
            category['broadcast_count'] / category['broadcast_count'].max() * 0.3
        ) * 100
        
        # 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_category")
        category.to_sql('agg_category', self.conn, if_exists='replace', index=False)
        print(f"  ✓ 카테고리별 집계 업데이트 완료")
    
    def _update_platform_hourly_aggregate(self, df):
        """방송사-시간대별 집계 업데이트"""
        print("[5/9] 방송사-시간대별 집계 업데이트 중...")
        
        # 전체 데이터 다시 계산
        all_data_query = "SELECT * FROM schedule WHERE platform != '기타'"
        df_all = pd.read_sql_query(all_data_query, self.conn)
        
        df_all['hour'] = df_all['time'].str.split(':').str[0].astype(int)
        df_all['is_live'] = df_all['platform'].isin(LIVE_CHANNELS).astype(int)
        df_all['model_cost'] = df_all['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        df_all['total_cost'] = df_all['cost'] + df_all['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df_all['real_profit'] = (df_all['revenue'] * REAL_MARGIN_RATE) - df_all['total_cost']
        df_all['roi_calculated'] = np.where(
            df_all['total_cost'] > 0,
            (df_all['real_profit'] / df_all['total_cost']) * 100,
            0
        )
        
        platform_hourly = df_all.groupby(['platform', 'hour']).agg({
            'revenue': ['sum', 'mean'],
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        platform_hourly.columns = [
            'platform', 'hour', 'revenue_sum', 'revenue_mean',
            'roi_mean', 'broadcast_count'
        ]
        
        # 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_platform_hourly")
        platform_hourly.to_sql('agg_platform_hourly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ 방송사-시간대별 집계 업데이트 완료")
    
    def _update_category_hourly_aggregate(self, df):
        """카테고리-시간대별 집계 업데이트"""
        print("[6/9] 카테고리-시간대별 집계 업데이트 중...")
        
        # 전체 데이터 다시 계산
        all_data_query = "SELECT * FROM schedule WHERE platform != '기타'"
        df_all = pd.read_sql_query(all_data_query, self.conn)
        
        df_all['hour'] = df_all['time'].str.split(':').str[0].astype(int)
        df_all['is_live'] = df_all['platform'].isin(LIVE_CHANNELS).astype(int)
        df_all['model_cost'] = df_all['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        df_all['total_cost'] = df_all['cost'] + df_all['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df_all['real_profit'] = (df_all['revenue'] * REAL_MARGIN_RATE) - df_all['total_cost']
        df_all['roi_calculated'] = np.where(
            df_all['total_cost'] > 0,
            (df_all['real_profit'] / df_all['total_cost']) * 100,
            0
        )
        
        category_hourly = df_all.groupby(['category', 'hour']).agg({
            'revenue': ['sum', 'mean'],
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        category_hourly.columns = [
            'category', 'hour', 'revenue_sum', 'revenue_mean',
            'roi_mean', 'broadcast_count'
        ]
        
        # 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_category_hourly")
        category_hourly.to_sql('agg_category_hourly', self.conn, if_exists='replace', index=False)
        print(f"  ✓ 카테고리-시간대별 집계 업데이트 완료")
    
    def _update_weekday_aggregate(self, df):
        """요일별 집계 업데이트"""
        print("[7/9] 요일별 집계 업데이트 중...")
        
        # 전체 데이터 다시 계산
        all_data_query = "SELECT * FROM schedule WHERE platform != '기타'"
        df_all = pd.read_sql_query(all_data_query, self.conn)
        
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_all['weekday'] = df_all['date'].dt.dayofweek
        df_all['is_live'] = df_all['platform'].isin(LIVE_CHANNELS).astype(int)
        df_all['model_cost'] = df_all['is_live'].apply(
            lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
        )
        df_all['total_cost'] = df_all['cost'] + df_all['model_cost']
        
        # 실질 수익 계산 - 새로운 계산법 적용
        df_all['real_profit'] = (df_all['revenue'] * REAL_MARGIN_RATE) - df_all['total_cost']
        df_all['roi_calculated'] = np.where(
            df_all['total_cost'] > 0,
            (df_all['real_profit'] / df_all['total_cost']) * 100,
            0
        )
        
        weekday = df_all.groupby('weekday').agg({
            'revenue': ['sum', 'mean'],
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        weekday.columns = [
            'weekday', 'revenue_sum', 'revenue_mean',
            'units_sum', 'roi_mean', 'broadcast_count'
        ]
        
        weekday_names = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
        weekday['weekday_name'] = weekday['weekday'].map(weekday_names)
        
        # 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_weekday")
        weekday.to_sql('agg_weekday', self.conn, if_exists='replace', index=False)
        print(f"  ✓ 요일별 집계 업데이트 완료")
    
    def _update_monthly_aggregate(self, df):
        """월별 집계 업데이트"""
        print("[8/9] 월별 집계 업데이트 중...")
        
        # 현재 월 데이터만 업데이트
        current_month = df['month'].iloc[0] if len(df) > 0 else None
        
        if current_month:
            # 기존 현재 월 데이터 삭제
            self.cur.execute(f"DELETE FROM agg_monthly WHERE month = '{current_month}'")
            
            # 현재 월 전체 데이터 다시 계산
            month_data_query = f"""
                SELECT * FROM schedule 
                WHERE strftime('%Y-%m', date) = '{current_month[:7]}'
                AND platform != '기타'
            """
            df_month = pd.read_sql_query(month_data_query, self.conn)
            
            if len(df_month) > 0:
                df_month['month'] = current_month
                df_month['is_live'] = df_month['platform'].isin(LIVE_CHANNELS).astype(int)
                df_month['model_cost'] = df_month['is_live'].apply(
                    lambda x: MODEL_COST_LIVE if x else MODEL_COST_NON_LIVE
                )
                df_month['total_cost'] = df_month['cost'] + df_month['model_cost']
                
                # 실질 수익 계산 - 새로운 계산법 적용
                df_month['real_profit'] = (df_month['revenue'] * REAL_MARGIN_RATE) - df_month['total_cost']
                df_month['roi_calculated'] = np.where(
                    df_month['total_cost'] > 0,
                    (df_month['real_profit'] / df_month['total_cost']) * 100,
                    0
                )
                
                monthly = df_month.groupby('month').agg({
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
                
                monthly.to_sql('agg_monthly', self.conn, if_exists='append', index=False)
        
        print(f"  ✓ 월별 집계 업데이트 완료")
    
    def _update_statistics(self):
        """통계 정보 업데이트"""
        print("[9/9] 통계 정보 업데이트 중...")
        
        # 전체 통계 재계산
        self.cur.execute("SELECT COUNT(*) FROM schedule WHERE platform != '기타'")
        total_records = self.cur.fetchone()[0]
        
        self.cur.execute("SELECT COUNT(*) FROM schedule WHERE platform = '기타'")
        others_count = self.cur.fetchone()[0]
        
        self.cur.execute("SELECT COUNT(*) FROM schedule")
        total_original = self.cur.fetchone()[0]
        
        # 새로운 계산법으로 통계 계산
        self.cur.execute(f"""
            SELECT 
                MIN(date) as min_date, 
                MAX(date) as max_date,
                COUNT(DISTINCT platform) as platforms,
                COUNT(DISTINCT category) as categories,
                SUM(revenue) as total_revenue,
                SUM((revenue * {REAL_MARGIN_RATE}) - (cost + 
                    CASE 
                        WHEN platform IN ('현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑')
                        THEN {MODEL_COST_LIVE} 
                        ELSE {MODEL_COST_NON_LIVE} 
                    END)) as total_profit
            FROM schedule 
            WHERE platform != '기타'
        """)
        
        stats_row = self.cur.fetchone()
        
        # ROI 평균 계산 - 새로운 계산법
        self.cur.execute(f"""
            SELECT AVG(roi_calculated) FROM (
                SELECT 
                    CASE 
                        WHEN (cost + CASE 
                            WHEN platform IN ('현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑')
                            THEN {MODEL_COST_LIVE} 
                            ELSE {MODEL_COST_NON_LIVE} 
                        END) > 0
                        THEN ((revenue * {REAL_MARGIN_RATE}) - (cost + CASE 
                            WHEN platform IN ('현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑')
                            THEN {MODEL_COST_LIVE} 
                            ELSE {MODEL_COST_NON_LIVE} 
                        END)) / (cost + CASE 
                            WHEN platform IN ('현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑')
                            THEN {MODEL_COST_LIVE} 
                            ELSE {MODEL_COST_NON_LIVE} 
                        END) * 100
                        ELSE 0
                    END as roi_calculated
                FROM schedule 
                WHERE platform != '기타'
            )
        """)
        
        avg_roi = self.cur.fetchone()[0] or 0
        
        stats = {
            'created_at': datetime.now().isoformat(),
            'total_records': total_records,
            'others_excluded': others_count,
            'others_ratio': (others_count / total_original * 100) if total_original > 0 else 0,
            'date_range': f"{stats_row[0]} ~ {stats_row[1]}",
            'platforms': stats_row[2],
            'categories': stats_row[3],
            'total_revenue': int(stats_row[4] or 0),
            'total_profit': int(stats_row[5] or 0),
            'avg_roi': float(avg_roi),
            'real_margin_rate': REAL_MARGIN_RATE,  # 새로운 마진율 저장
            'conversion_rate': CONVERSION_RATE,     # 전환율 저장
            'product_cost_rate': PRODUCT_COST_RATE, # 제품 원가율 저장
            'commission_rate': COMMISSION_RATE      # 판매 수수료율 저장
        }
        
        # 통계 테이블 재생성
        self.cur.execute("DROP TABLE IF EXISTS agg_statistics")
        stats_df = pd.DataFrame([stats])
        stats_df.to_sql('agg_statistics', self.conn, if_exists='replace', index=False)
        
        print(f"  ✓ 통계 정보 업데이트 완료")
        print(f"  ℹ️ 적용된 실질 마진율: {REAL_MARGIN_RATE:.2%}")
    
    def _verify_update(self):
        """업데이트 결과 확인"""
        print("\n📊 업데이트 결과 확인")
        print("=" * 60)
        
        # 오늘 데이터 확인
        self.cur.execute(f"""
            SELECT COUNT(*) as count, SUM(revenue_sum) as revenue
            FROM agg_daily 
            WHERE date = '{self.today}'
        """)
        
        result = self.cur.fetchone()
        if result and result[0] > 0:
            print(f"✅ 일별 집계: {self.today} 데이터 존재")
            print(f"   - 총 매출: {result[1]:,.0f}원")
        else:
            print(f"⚠️ 일별 집계: {self.today} 데이터 없음")
        
        # 통계 정보 확인
        self.cur.execute("SELECT * FROM agg_statistics")
        stats = self.cur.fetchone()
        if stats:
            print(f"\n📈 전체 통계:")
            print(f"   - 기간: {stats[4]}")
            print(f"   - 총 레코드: {stats[1]:,}개")
            print(f"   - 평균 ROI: {stats[8]:.2f}%")
            if len(stats) > 9:  # 새로운 필드가 있는지 확인
                print(f"   - 실질 마진율: {stats[9]:.2%}")

# ============================================================================
# 자동 실행 함수
# ============================================================================

def update_aggregates_if_needed(db_path="schedule.db"):
    """필요시 집계 테이블 업데이트"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 오늘 원본 데이터 확인
        today = datetime.now().strftime('%Y-%m-%d')
        cur.execute(f"SELECT COUNT(*) FROM schedule WHERE date = '{today}'")
        today_count = cur.fetchone()[0]
        
        if today_count == 0:
            print("ℹ️ 오늘 데이터가 없어 집계 업데이트를 건너뜁니다.")
            conn.close()
            return False
        
        # 집계 테이블의 오늘 데이터 확인
        cur.execute(f"SELECT COUNT(*) FROM agg_daily WHERE date = '{today}'")
        agg_count = cur.fetchone()[0]
        
        conn.close()
        
        # 집계 테이블에 오늘 데이터가 없거나 오래된 경우 업데이트
        if agg_count == 0:
            print("📊 집계 테이블에 오늘 데이터가 없어 업데이트를 시작합니다.")
            updater = AggregateTableUpdater(db_path)
            return updater.update_today_only()
        else:
            print("✅ 집계 테이블이 최신 상태입니다.")
            return True
            
    except Exception as e:
        print(f"❌ 집계 테이블 업데이트 중 오류: {e}")
        return False

# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="집계 테이블 증분 업데이트")
    parser.add_argument("--db", default="schedule.db", help="데이터베이스 경로")
    parser.add_argument("--check", action="store_true", help="업데이트 필요 여부만 확인")
    
    args = parser.parse_args()
    
    if args.check:
        # 업데이트 필요 여부 확인만
        conn = sqlite3.connect(args.db)
        cur = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 원본 데이터 확인
        cur.execute(f"SELECT COUNT(*) FROM schedule WHERE date = '{today}'")
        today_count = cur.fetchone()[0]
        
        # 집계 데이터 확인
        cur.execute(f"SELECT COUNT(*) FROM agg_daily WHERE date = '{today}'")
        agg_count = cur.fetchone()[0]
        
        conn.close()
        
        print(f"\n📊 집계 테이블 상태 확인")
        print(f"  - 오늘 원본 데이터: {today_count}건")
        print(f"  - 오늘 집계 데이터: {'있음' if agg_count > 0 else '없음'}")
        
        if today_count > 0 and agg_count == 0:
            print("  ⚠️ 업데이트 필요!")
        else:
            print("  ✅ 최신 상태")
    else:
        # 실제 업데이트 실행
        update_aggregates_if_needed(args.db)