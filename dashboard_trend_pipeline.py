"""
dashboard_trend_pipeline.py - 추세분석 데이터 파이프라인
Version: 1.1.0
Created: 2025-01-25
Updated: 2025-09-12 - 데이터 타입 안정성 강화

데이터 흐름: Raw Data → 전처리 → 집계 → 지표계산 → 캐싱 → 시각화
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# 추세 계산기 import
from dashboard_trend_calculator import TrendCalculator

class TrendDataPipeline:
    """추세분석 데이터 파이프라인 클래스"""
    
    def __init__(self, db_path="schedule.db", cache_dir="cache"):
        """
        초기화
        
        Parameters:
        -----------
        db_path : str
            데이터베이스 경로
        cache_dir : str
            캐시 디렉토리 경로
        """
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_ttl = 3600  # 1시간 캐시
        self.calculator = TrendCalculator()
        
        # 생방송 채널 정의 (dashboard_config와 동일)
        self.LIVE_CHANNELS = {
            '현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', 
            '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑'
        }
        
        # 모델비 설정
        self.MODEL_COST_LIVE = 10400000
        self.MODEL_COST_NON_LIVE = 2000000
        
        # ROI 계산 설정
        self.CONVERSION_RATE = 0.75
        self.PRODUCT_COST_RATE = 0.13
        self.COMMISSION_RATE = 0.10
        self.REAL_MARGIN_RATE = (1 - self.COMMISSION_RATE - self.PRODUCT_COST_RATE) * self.CONVERSION_RATE
    
    def execute_pipeline(self, 
                        date_range: Tuple[str, str] = None,
                        filters: Dict[str, Any] = None,
                        use_cache: bool = True,
                        source: str = 'schedule') -> Dict[str, pd.DataFrame]:
        """
        전체 파이프라인 실행
        
        Parameters:
        -----------
        date_range : tuple
            (시작일, 종료일) 형식
        filters : dict
            필터 조건 (platforms, categories 등)
        use_cache : bool
            캐시 사용 여부
        source : str
            데이터 소스 ('schedule' or 'broadcasts')
            
        Returns:
        --------
        dict : 처리된 데이터 딕셔너리
        """
        # 캐시 키 생성
        cache_key = self._generate_cache_key(date_range, filters)
        
        # 캐시 확인
        if use_cache:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                print("📦 캐시에서 데이터 로드")
                return cached_data
        
        print("🔄 데이터 파이프라인 실행 중...")
        
        # Step 1: 데이터 추출 (타입 안정성 강화)
        raw_data = self.extract_data(date_range, filters, source)
        
        if raw_data.empty:
            print("⚠️ 데이터가 없습니다")
            return {'daily': pd.DataFrame(), 'category': pd.DataFrame()}
        
        # Step 2: 데이터 정제 (타입 검증 강화)
        cleaned_data = self.clean_data(raw_data)
        
        # Step 3: 시계열 집계
        aggregated_data = self.aggregate_timeseries(cleaned_data)
        
        # Step 4: 추세 지표 계산
        trend_metrics = self.calculate_trends(aggregated_data)
        
        # Step 5: 카테고리별 분석
        category_trends = self.analyze_category_trends(cleaned_data)
        
        # Step 6: 결과 구성
        result = {
            'daily': trend_metrics['daily'],
            'weekly': trend_metrics.get('weekly', pd.DataFrame()),
            'monthly': trend_metrics.get('monthly', pd.DataFrame()),
            'category': category_trends,
            'raw': cleaned_data,
            'summary': self._create_summary(trend_metrics)
        }
        
        # Step 7: 캐싱
        if use_cache:
            self._save_to_cache(cache_key, result)
        
        print("✅ 파이프라인 실행 완료")
        return result
    
    def extract_data(self, date_range: Tuple[str, str] = None, 
                    filters: Dict[str, Any] = None,
                    source: str = 'schedule') -> pd.DataFrame:
        """
        데이터베이스에서 데이터 추출 (타입 안정성 강화)
        
        Parameters:
        -----------
        date_range : tuple
            (시작일, 종료일)
        filters : dict
            필터 조건
        source : str
            데이터 소스 ('schedule' or 'broadcasts')
            
        Returns:
        --------
        DataFrame : 추출된 데이터
        """
        conn = sqlite3.connect(self.db_path)
        
        # 데이터 소스에 따른 쿼리 선택
        if source == 'schedule':
            # schedule 테이블 사용 (데이터 완전성이 더 높음)
            query = """
                SELECT 
                    date, 
                    time, 
                    broadcast, 
                    platform, 
                    category,
                    CAST(revenue AS REAL) as revenue,
                    CAST(COALESCE(cost, 0) AS REAL) as cost,
                    CAST(COALESCE(roi_calculated, 0) AS REAL) as roi,
                    CAST(units_sold AS INTEGER) as units_sold,
                    CAST(product_count AS INTEGER) as product_count
                FROM schedule 
                WHERE platform != '기타'
            """
        else:
            # broadcasts 테이블 사용 시 NULL 제외 및 타입 캐스팅
            query = """
                SELECT 
                    date, 
                    time, 
                    broadcast_name as broadcast, 
                    platform, 
                    category,
                    CAST(revenue AS REAL) as revenue,
                    CAST(COALESCE(cost, 0) AS REAL) as cost,
                    CAST(COALESCE(roi, 0) AS REAL) as roi,
                    CAST(units_sold AS INTEGER) as units_sold,
                    CAST(product_count AS INTEGER) as product_count
                FROM broadcasts
                WHERE platform != '기타'
                  AND revenue IS NOT NULL
            """
        
        conditions = []
        params = []
        
        # 날짜 필터
        if date_range:
            start_date, end_date = date_range
            conditions.append("date BETWEEN ? AND ?")
            params.extend([start_date, end_date])
        
        # 플랫폼 필터
        if filters and 'platforms' in filters and filters['platforms']:
            placeholders = ','.join(['?' for _ in filters['platforms']])
            conditions.append(f"platform IN ({placeholders})")
            params.extend(filters['platforms'])
        
        # 카테고리 필터
        if filters and 'categories' in filters and filters['categories']:
            placeholders = ','.join(['?' for _ in filters['categories']])
            conditions.append(f"category IN ({placeholders})")
            params.extend(filters['categories'])
        
        # 매출 상한 필터
        if filters and 'revenue_limit' in filters:
            conditions.append("revenue <= ?")
            params.append(filters['revenue_limit'])
        
        # 조건 추가
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY date, time"
        
        # 데이터 로드
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        # 추가 타입 변환 보장
        numeric_columns = ['revenue', 'cost', 'roi', 'units_sold', 'product_count']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        print(f"📊 {len(df):,}개 레코드 추출 (소스: {source})")
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 정제 및 전처리 (타입 검증 강화)
        
        Parameters:
        -----------
        df : DataFrame
            원본 데이터
            
        Returns:
        --------
        DataFrame : 정제된 데이터
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 날짜 변환
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # 숫자 컬럼 강제 변환 및 검증
        numeric_columns = ['revenue', 'cost', 'roi', 'units_sold', 'product_count']
        
        for col in numeric_columns:
            if col in df.columns:
                # 변환 전 데이터 타입 로깅
                original_dtype = df[col].dtype
                
                # 숫자로 변환
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # NULL 값 처리
                if col in ['cost', 'roi']:
                    # cost와 roi는 0으로 채우기
                    df[col] = df[col].fillna(0)
                else:
                    # 다른 컬럼은 전방 채우기 후 0으로 채우기
                    df[col] = df[col].fillna(method='ffill').fillna(0)
                
                # 변환 결과 검증
                if df[col].dtype not in ['float64', 'int64']:
                    print(f"⚠️ {col} 컬럼 타입 변환 경고: {original_dtype} → {df[col].dtype}")
        
        # 시간 관련 컬럼 생성
        df['hour'] = df['time'].str.split(':').str[0].astype(int)
        df['weekday'] = df['date'].dt.dayofweek
        df['weekday_name'] = df['date'].dt.day_name()
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['year'] = df['date'].dt.year
        df['week'] = df['date'].dt.strftime('%Y-W%U')
        df['year_month'] = df['date'].dt.strftime('%Y-%m')
        df['is_weekend'] = df['weekday'].isin([5, 6])
        
        # 채널 구분
        df['is_live'] = df['platform'].isin(self.LIVE_CHANNELS).astype(int)
        df['channel_type'] = df['is_live'].map({1: '생방송', 0: '비생방송'})
        
        # 비용 계산
        df['model_cost'] = np.where(df['is_live'], 
                                    self.MODEL_COST_LIVE, 
                                    self.MODEL_COST_NON_LIVE)
        df['total_cost'] = df['cost'] + df['model_cost']
        
        # 실질 수익 계산 (새로운 ROI 계산법 적용)
        df['real_profit'] = (df['revenue'] * self.REAL_MARGIN_RATE) - df['total_cost']
        
        # ROI 계산
        df['roi_calculated'] = np.where(
            df['total_cost'] > 0,
            (df['real_profit'] / df['total_cost']) * 100,
            0
        )
        
        # 효율성 지표
        df['efficiency'] = np.where(
            df['total_cost'] > 0,
            df['revenue'] / df['total_cost'],
            0
        )
        
        # 단가 계산
        df['unit_price'] = np.where(
            df['units_sold'] > 0,
            df['revenue'] / df['units_sold'],
            0
        )
        
        # 이상치 제거 (음수 매출)
        df = df[df['revenue'] >= 0]
        
        print(f"✨ 데이터 정제 완료 ({len(df)}개 레코드)")
        return df
    
    def aggregate_timeseries(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        시계열 집계
        
        Parameters:
        -----------
        df : DataFrame
            정제된 데이터
            
        Returns:
        --------
        dict : 기간별 집계 데이터
        """
        aggregations = {}
        
        # 일별 집계
        daily = df.groupby('date').agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'total_cost': 'sum',
            'real_profit': 'sum',
            'broadcast': 'count',
            'efficiency': 'mean'
        }).reset_index()
        
        daily.columns = ['date', 'revenue', 'units_sold', 'avg_roi', 
                         'total_cost', 'real_profit', 'broadcast_count', 'avg_efficiency']
        aggregations['daily'] = daily
        
        # 주별 집계
        weekly = df.groupby('week').agg({
            'date': ['min', 'max'],
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'total_cost': 'sum',
            'real_profit': 'sum',
            'broadcast': 'count'
        }).reset_index()
        
        weekly.columns = ['week', 'start_date', 'end_date', 'revenue', 
                         'units_sold', 'avg_roi', 'total_cost', 'real_profit', 'broadcast_count']
        aggregations['weekly'] = weekly
        
        # 월별 집계
        monthly = df.groupby('year_month').agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'total_cost': 'sum',
            'real_profit': 'sum',
            'broadcast': 'count'
        }).reset_index()
        
        monthly.columns = ['year_month', 'revenue', 'units_sold', 'avg_roi', 
                          'total_cost', 'real_profit', 'broadcast_count']
        aggregations['monthly'] = monthly
        
        print(f"📈 시계열 집계 완료 (일별: {len(daily)}, 주별: {len(weekly)}, 월별: {len(monthly)})")
        return aggregations
    
    def calculate_trends(self, aggregated_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        추세 지표 계산
        
        Parameters:
        -----------
        aggregated_data : dict
            집계된 데이터
            
        Returns:
        --------
        dict : 추세 지표가 추가된 데이터
        """
        result = {}
        
        # 일별 추세
        if 'daily' in aggregated_data and not aggregated_data['daily'].empty:
            daily = aggregated_data['daily'].copy()
            
            # 모든 추세 메트릭 계산
            daily = self.calculator.calculate_growth_rates(daily)
            daily = self.calculator.calculate_moving_averages(daily)
            daily = self.calculator.calculate_volatility(daily)
            daily = self.calculator.detect_trend_direction(daily)
            daily = self.calculator.calculate_seasonality(daily)
            daily = self.calculator.detect_anomalies(daily)
            
            result['daily'] = daily
        
        # 주별 추세
        if 'weekly' in aggregated_data and not aggregated_data['weekly'].empty:
            weekly = aggregated_data['weekly'].copy()
            weekly['revenue_wow'] = weekly['revenue'].pct_change() * 100
            weekly['revenue_4w'] = weekly['revenue'].pct_change(periods=4) * 100
            weekly['ma_4w'] = weekly['revenue'].rolling(window=4, min_periods=1).mean()
            result['weekly'] = weekly
        
        # 월별 추세
        if 'monthly' in aggregated_data and not aggregated_data['monthly'].empty:
            monthly = aggregated_data['monthly'].copy()
            monthly['revenue_mom'] = monthly['revenue'].pct_change() * 100
            monthly['revenue_yoy'] = monthly['revenue'].pct_change(periods=12) * 100
            
            # 계절 지수
            monthly_avg = monthly['revenue'].mean()
            monthly['seasonal_index'] = (monthly['revenue'] / monthly_avg) * 100
            
            result['monthly'] = monthly
        
        print("📊 추세 지표 계산 완료")
        return result
    
    def analyze_category_trends(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        카테고리별 추세 분석
        
        Parameters:
        -----------
        df : DataFrame
            정제된 데이터
            
        Returns:
        --------
        DataFrame : 카테고리별 추세 데이터
        """
        if df.empty:
            return pd.DataFrame()
        
        # 카테고리별 일별 집계
        category_daily = df.groupby(['date', 'category']).agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        # 일별 총 매출로 시장 점유율 계산
        daily_total = category_daily.groupby('date')['revenue'].sum().reset_index()
        daily_total.columns = ['date', 'total_revenue']
        
        category_daily = category_daily.merge(daily_total, on='date')
        category_daily['market_share'] = (category_daily['revenue'] / 
                                          category_daily['total_revenue']) * 100
        
        # 카테고리별 성장률
        category_daily['growth_rate'] = category_daily.groupby('category')['revenue'].pct_change() * 100
        
        # 주별 집계로 변환 (히트맵용)
        category_daily['week'] = pd.to_datetime(category_daily['date']).dt.strftime('%Y-W%U')
        
        category_weekly = category_daily.groupby(['week', 'category']).agg({
            'revenue': 'sum',
            'market_share': 'mean',
            'growth_rate': 'mean',
            'broadcast': 'sum'
        }).reset_index()
        
        # 추세 방향 계산
        def calculate_trend(group):
            if len(group) < 3:
                return 'stable'
            recent_avg = group['revenue'].tail(3).mean()
            prev_avg = group['revenue'].head(3).mean()
            if recent_avg > prev_avg * 1.1:
                return 'up'
            elif recent_avg < prev_avg * 0.9:
                return 'down'
            return 'stable'
        
        category_trends = category_daily.groupby('category').apply(calculate_trend).reset_index()
        category_trends.columns = ['category', 'trend_direction']
        
        # 모멘텀 스코어
        momentum = category_daily.groupby('category')['growth_rate'].mean().reset_index()
        momentum.columns = ['category', 'momentum_score']
        
        # 병합
        category_weekly = category_weekly.merge(category_trends, on='category', how='left')
        category_weekly = category_weekly.merge(momentum, on='category', how='left')
        
        print(f"📦 카테고리 추세 분석 완료 ({len(category_weekly)}개 레코드)")
        return category_weekly
    
    def _generate_cache_key(self, date_range: Tuple[str, str] = None, 
                           filters: Dict[str, Any] = None) -> str:
        """
        캐시 키 생성
        
        Parameters:
        -----------
        date_range : tuple
            날짜 범위
        filters : dict
            필터 조건
            
        Returns:
        --------
        str : 캐시 키
        """
        key_data = {
            'date_range': date_range,
            'filters': filters,
            'version': '1.1.0'
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        캐시에서 데이터 로드
        
        Parameters:
        -----------
        cache_key : str
            캐시 키
            
        Returns:
        --------
        dict or None : 캐시된 데이터
        """
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        # 캐시 만료 확인
        file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if file_age > self.cache_ttl:
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"⚠️ 캐시 로드 실패: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """
        캐시에 데이터 저장
        
        Parameters:
        -----------
        cache_key : str
            캐시 키
        data : dict
            저장할 데이터
        """
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            print(f"💾 캐시 저장 완료")
        except Exception as e:
            print(f"⚠️ 캐시 저장 실패: {e}")
    
    def _create_summary(self, trend_metrics: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        종합 요약 생성
        
        Parameters:
        -----------
        trend_metrics : dict
            추세 메트릭 데이터
            
        Returns:
        --------
        dict : 요약 통계
        """
        summary = {}
        
        if 'daily' in trend_metrics and not trend_metrics['daily'].empty:
            daily = trend_metrics['daily']
            
            summary['기간'] = f"{daily['date'].min()} ~ {daily['date'].max()}"
            summary['총_일수'] = len(daily)
            summary['총_매출'] = daily['revenue'].sum()
            summary['평균_일매출'] = daily['revenue'].mean()
            summary['최대_일매출'] = daily['revenue'].max()
            summary['최소_일매출'] = daily['revenue'].min()
            
            if 'revenue_dod' in daily.columns:
                summary['평균_성장률'] = daily['revenue_dod'].mean()
                summary['성장률_표준편차'] = daily['revenue_dod'].std()
            
            if 'trend_direction_7' in daily.columns:
                trend_counts = daily['trend_direction_7'].value_counts().to_dict()
                summary['상승_일수'] = trend_counts.get('up', 0)
                summary['하락_일수'] = trend_counts.get('down', 0)
                summary['보합_일수'] = trend_counts.get('stable', 0)
            
            if 'is_anomaly' in daily.columns:
                summary['이상치_건수'] = daily['is_anomaly'].sum()
                summary['이상치_비율'] = daily['is_anomaly'].mean() * 100
            
            if 'cv_30' in daily.columns:
                summary['평균_변동성'] = daily['cv_30'].mean()
        
        return summary
    
    def clear_cache(self):
        """캐시 전체 삭제"""
        cache_files = list(self.cache_dir.glob("*.pkl"))
        for file in cache_files:
            file.unlink()
        print(f"🗑️ {len(cache_files)}개 캐시 파일 삭제")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 반환"""
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)  # MB
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_mb': round(total_size, 2),
            'ttl_seconds': self.cache_ttl
        }


# 유틸리티 함수들
def create_trend_tables(db_path="schedule.db"):
    """
    추세분석용 테이블 생성
    
    Parameters:
    -----------
    db_path : str
        데이터베이스 경로
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔨 추세분석 테이블 생성 중...")
    
    # trend_daily 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trend_daily (
        date TEXT PRIMARY KEY,
        revenue REAL,
        units_sold INTEGER,
        broadcast_count INTEGER,
        avg_roi REAL,
        revenue_dod REAL,
        revenue_wow REAL,
        revenue_mom REAL,
        revenue_yoy REAL,
        ma_7 REAL,
        ma_30 REAL,
        ma_90 REAL,
        trend_direction TEXT,
        volatility REAL,
        z_score REAL,
        is_anomaly INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # trend_weekly 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trend_weekly (
        year_week TEXT PRIMARY KEY,
        start_date TEXT,
        end_date TEXT,
        revenue REAL,
        units_sold INTEGER,
        broadcast_count INTEGER,
        avg_roi REAL,
        revenue_wow REAL,
        revenue_4w REAL,
        trend_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # trend_monthly 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trend_monthly (
        year_month TEXT PRIMARY KEY,
        revenue REAL,
        units_sold INTEGER,
        broadcast_count INTEGER,
        avg_roi REAL,
        revenue_mom REAL,
        revenue_yoy REAL,
        seasonal_index REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # trend_category 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trend_category (
        date TEXT,
        category TEXT,
        revenue REAL,
        market_share REAL,
        growth_rate REAL,
        trend_direction TEXT,
        momentum_score REAL,
        PRIMARY KEY (date, category)
    )
    """)
    
    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_daily_date ON trend_daily(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_weekly_week ON trend_weekly(year_week)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_monthly_month ON trend_monthly(year_month)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_category_date ON trend_category(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_category_cat ON trend_category(category)")
    
    conn.commit()
    conn.close()
    
    print("✅ 추세분석 테이블 생성 완료")


def populate_trend_tables(db_path="schedule.db"):
    """
    기존 데이터로 추세 테이블 채우기
    
    Parameters:
    -----------
    db_path : str
        데이터베이스 경로
    """
    pipeline = TrendDataPipeline(db_path)
    
    print("📊 추세 데이터 생성 중...")
    
    # 전체 데이터로 파이프라인 실행
    result = pipeline.execute_pipeline(use_cache=False, source='schedule')
    
    if not result or 'daily' not in result:
        print("❌ 데이터 생성 실패")
        return
    
    conn = sqlite3.connect(db_path)
    
    try:
        # 일별 데이터 저장
        if 'daily' in result and not result['daily'].empty:
            daily = result['daily'].copy()
            daily['date'] = daily['date'].dt.strftime('%Y-%m-%d')
            daily.to_sql('trend_daily', conn, if_exists='replace', index=False)
            print(f"✔ 일별 추세: {len(daily)}개 레코드")
        
        # 주별 데이터 저장
        if 'weekly' in result and not result['weekly'].empty:
            weekly = result['weekly'].copy()
            if 'start_date' in weekly.columns:
                weekly['start_date'] = pd.to_datetime(weekly['start_date']).dt.strftime('%Y-%m-%d')
            if 'end_date' in weekly.columns:
                weekly['end_date'] = pd.to_datetime(weekly['end_date']).dt.strftime('%Y-%m-%d')
            weekly.to_sql('trend_weekly', conn, if_exists='replace', index=False)
            print(f"✔ 주별 추세: {len(weekly)}개 레코드")
        
        # 월별 데이터 저장
        if 'monthly' in result and not result['monthly'].empty:
            monthly = result['monthly']
            monthly.to_sql('trend_monthly', conn, if_exists='replace', index=False)
            print(f"✔ 월별 추세: {len(monthly)}개 레코드")
        
        # 카테고리별 데이터 저장
        if 'category' in result and not result['category'].empty:
            category = result['category'].copy()
            if 'date' in category.columns:
                category['date'] = pd.to_datetime(category['date']).dt.strftime('%Y-%m-%d')
            # week 컬럼은 제외하고 저장
            columns_to_save = ['date', 'category', 'revenue', 'market_share', 
                              'growth_rate', 'trend_direction', 'momentum_score']
            columns_to_save = [col for col in columns_to_save if col in category.columns]
            
            if 'week' in category.columns and 'date' not in category.columns:
                # week를 date로 변환
                category['date'] = pd.to_datetime(category['week'] + '-1', format='%Y-W%U-%w')
                category['date'] = category['date'].dt.strftime('%Y-%m-%d')
            
            if columns_to_save:
                category[columns_to_save].to_sql('trend_category', conn, 
                                                if_exists='replace', index=False)
                print(f"✔ 카테고리별 추세: {len(category)}개 레코드")
        
        conn.commit()
        print("\n✅ 추세 데이터 생성 완료!")
        
    except Exception as e:
        print(f"❌ 데이터 저장 중 오류: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    """테스트 실행"""
    print("=" * 60)
    print("📊 추세분석 파이프라인 테스트")
    print("=" * 60)
    
    # 테이블 생성
    create_trend_tables()
    
    # 파이프라인 테스트
    pipeline = TrendDataPipeline()
    
    # 최근 30일 데이터로 테스트
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    result = pipeline.execute_pipeline(
        date_range=(start_date, end_date),
        filters={'platforms': ['NS홈쇼핑']},
        use_cache=True,
        source='schedule'  # schedule 테이블 사용
    )
    
    # 결과 출력
    print("\n📈 파이프라인 실행 결과:")
    for key, df in result.items():
        if isinstance(df, pd.DataFrame):
            print(f"  - {key}: {len(df)}개 레코드")
        elif isinstance(df, dict):
            print(f"  - {key}: {len(df)}개 항목")
    
    # 캐시 정보
    cache_info = pipeline.get_cache_info()
    print(f"\n💾 캐시 정보:")
    print(f"  - 파일 수: {cache_info['file_count']}개")
    print(f"  - 총 크기: {cache_info['total_size_mb']}MB")
    print(f"  - TTL: {cache_info['ttl_seconds']}초")
    
    print("\n✨ 테스트 완료!")