"""
dashboard_data.py - 데이터 로드, 전처리, 계산 로직 (최적화 버전 + ROI 개선 + abs() 에러 수정)
Version: 6.3.0
Last Updated: 2025-02-03

주요 수정사항:
1. safe_abs() 함수 추가 및 모든 abs() 호출 대체
2. 데이터 타입 변환 강화
3. 문자열 처리 로직 개선
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import colorsys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import json

from dashboard_config import (
    LIVE_CHANNELS, MODEL_COST_LIVE, MODEL_COST_NON_LIVE,
    CONVERSION_RATE, REAL_MARGIN_RATE,
    PLATFORM_COLORS, CATEGORY_COLORS
)

# ============================================================================
# 안전한 절대값 계산 함수 (최우선 정의)
# ============================================================================


def safe_abs(value):
    """완전히 안전한 절대값 계산 - 모든 타입 처리"""
    import re
    try:
        # 1. None, NaN, 빈 값 체크
        if value is None:
            return 0
        
        # pandas NA 체크
        if pd.isna(value):
            return 0
            
        # 2. 이미 숫자인 경우 (numpy 타입 포함)
        if isinstance(value, (int, float, np.integer, np.floating)):
            if pd.isna(value) or np.isnan(value) or np.isinf(value):
                return 0
            return abs(float(value))
        
        # numpy 타입 체크
        if hasattr(value, 'dtype'):  # numpy 타입
            try:
                val = float(value)
                if np.isnan(val) or np.isinf(val):
                    return 0
                return abs(val)
            except:
                return 0
        
        # 3. 문자열 처리 강화
        if isinstance(value, str):
            # 빈 문자열 및 특수 케이스 체크
            if not value or value.strip() in ['', '-', 'N/A', 'nan', 'None', 'null', 'NaN']:
                return 0
            
            # 먼저 일반적인 불필요 문자 제거
            cleaned = value
            for char in [',', '원', '%', '₩', '$', ' ', '억', '만', '천']:
                cleaned = cleaned.replace(char, '')
            
            # 빈 문자열 체크
            if not cleaned or cleaned == '-':
                return 0
            
            # 숫자와 소수점만 추출 (음수 포함)
            numbers = re.findall(r'[-+]?\d*\.?\d+', cleaned)
            if numbers:
                try:
                    return abs(float(numbers[0]))
                except:
                    return 0
            return 0
        
        # 4. pandas Series나 numpy array의 단일 값 처리
        if hasattr(value, 'item'):
            try:
                return safe_abs(value.item())
            except:
                return 0
        
        # 5. 기타 - 강제 변환 시도
        try:
            return abs(float(str(value)))
        except:
            return 0
            
    except Exception as e:
        # 모든 예외 처리
        return 0

# ============================================================================
# 캐시 키 생성 유틸리티
# ============================================================================

def generate_cache_key(**kwargs) -> str:
    """필터 조합에 대한 고유 캐시 키 생성"""
    sorted_items = sorted(kwargs.items())
    key_string = json.dumps(sorted_items, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()

# ============================================================================
# 최적화된 집계 테이블 로더 클래스
# ============================================================================

class OptimizedAggregateLoader:
    """집계 테이블 전용 로더 - 고속 데이터 로딩"""
    
    def __init__(self, db_path="schedule.db"):
        self.db_path = db_path
        self._cache = {}
        self._check_aggregate_tables()
    
    def _check_aggregate_tables(self):
        """집계 테이블 존재 여부 확인"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        required_tables = [
            'agg_daily', 'agg_hourly', 'agg_platform', 'agg_category',
            'agg_platform_hourly', 'agg_category_hourly', 'agg_weekday',
            'agg_monthly', 'agg_statistics'
        ]
        
        self.has_aggregates = True
        for table in required_tables:
            cur.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cur.fetchone()[0] == 0:
                self.has_aggregates = False
                break
        
        conn.close()
        return self.has_aggregates
    
    @st.cache_data(ttl=300, show_spinner=False)
    def load_daily_stats(_self, start_date=None, end_date=None, exclude_today=False):
        """일별 집계 데이터 로드"""
        cache_key = generate_cache_key(
            type='daily', 
            start=start_date, 
            end=end_date, 
            exclude_today=exclude_today
        )
        
        if cache_key in _self._cache:
            return _self._cache[cache_key]
        
        conn = sqlite3.connect(_self.db_path)
        
        query = "SELECT * FROM agg_daily"
        conditions = []
        
        if exclude_today:
            today = datetime.now().strftime('%Y-%m-%d')
            conditions.append(f"date < '{today}'")
        
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
        
        _self._cache[cache_key] = df
        return df
    
    @st.cache_data(ttl=600, show_spinner=False)
    def load_batch_stats(_self, stat_types: List[str]):
        """여러 통계를 한 번에 로드"""
        conn = sqlite3.connect(_self.db_path)
        results = {}
        
        for stat_type in stat_types:
            if stat_type == 'hourly':
                df = pd.read_sql_query("SELECT * FROM agg_hourly ORDER BY hour", conn)
            elif stat_type == 'platform':
                df = pd.read_sql_query("SELECT * FROM agg_platform ORDER BY revenue_sum DESC", conn)
            elif stat_type == 'category':
                df = pd.read_sql_query("SELECT * FROM agg_category ORDER BY revenue_sum DESC", conn)
            elif stat_type == 'weekday':
                df = pd.read_sql_query("SELECT * FROM agg_weekday ORDER BY weekday", conn)
            else:
                continue
            
            results[stat_type] = df
        
        conn.close()
        return results
    
    @st.cache_data(ttl=60, show_spinner=False)
    def get_today_data(_self):
        """오늘 데이터만 원본에서 가져오기"""
        conn = sqlite3.connect(_self.db_path)
        today = datetime.now().strftime('%Y-%m-%d')
        
        query = f"""
            SELECT * FROM schedule 
            WHERE date = '{today}'
            AND platform != '기타'
            ORDER BY time DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) > 0:
            # 데이터 타입 변환 강화
            numeric_columns = ['revenue', 'units_sold', 'cost']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            df['date'] = pd.to_datetime(df['date'])
            df['hour'] = df['time'].str.split(':').str[0].astype(int)
            df['weekday'] = df['date'].dt.dayofweek
            df['is_weekend'] = df['weekday'].isin([5, 6])
            
            df['is_live'] = df['platform'].isin(LIVE_CHANNELS)
            df['model_cost'] = np.where(df['is_live'], MODEL_COST_LIVE, MODEL_COST_NON_LIVE)
            df['total_cost'] = df['cost'] + df['model_cost']
            
            df['real_profit'] = (df['revenue'] * REAL_MARGIN_RATE) - df['total_cost']
            
            df['roi_calculated'] = np.where(
                df['total_cost'] > 0,
                (df['real_profit'] / df['total_cost']) * 100,
                0
            )
            
            df['efficiency'] = np.where(
                df['total_cost'] > 0,
                df['revenue'] / df['total_cost'],
                0
            )
        
        return df
    
    def check_today_in_aggregate(self):
        """집계 테이블에 오늘 데이터가 있는지 확인"""
        if not self.has_aggregates:
            return False
        
        conn = sqlite3.connect(self.db_path)
        today = datetime.now().strftime('%Y-%m-%d')
        
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM agg_daily WHERE date = '{today}'")
        count = cur.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def load_statistics(self):
        """통계 정보 로드"""
        if not self.has_aggregates:
            return None
        
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query("SELECT * FROM agg_statistics LIMIT 1", conn)
            if len(df) > 0:
                return df.iloc[0].to_dict()
        except:
            pass
        finally:
            conn.close()
        
        return None

# ============================================================================
# 최적화된 데이터 로더 클래스
# ============================================================================

class OptimizedDataLoader:
    """원본 데이터 로더 - 상세 조회 전용"""
    
    def __init__(self, db_path="schedule.db"):
        self.db_path = db_path
        self.aggregate_loader = OptimizedAggregateLoader(db_path)
    
    @st.cache_data(ttl=300, show_spinner=False)
    def load_data(_self, days_back=30, force_all=False):
        """원본 데이터 로드"""
        
        if _self.aggregate_loader.has_aggregates:
            stats = _self.aggregate_loader.load_statistics()
            if stats:
                st.sidebar.success(f"✅ 집계 테이블 사용 (10배 빠름)")
                return pd.DataFrame()
        
        conn = sqlite3.connect(_self.db_path)
        
        if not force_all:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            query = f"""
                SELECT * FROM schedule 
                WHERE date >= '{cutoff_date}'
                AND platform != '기타'
                ORDER BY date DESC, time DESC
                LIMIT 10000
            """
        else:
            query = """
                SELECT * FROM schedule 
                WHERE platform != '기타'
                ORDER BY date DESC, time DESC
                LIMIT 50000
            """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        df = df.drop_duplicates(subset=['date', 'time', 'broadcast', 'platform'])
        df = _self._preprocess_data_optimized(df)
        
        return df
    
    def _preprocess_data_optimized(self, df):
        """최적화된 데이터 전처리"""
        if len(df) == 0:
            return df
        
        # 숫자 컬럼 타입 변환 강화
        numeric_columns = ['revenue', 'units_sold', 'cost', 'roi', 'product_count']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['date'] = pd.to_datetime(df['date'])
        
        df['hour'] = df['time'].str[:2].astype(int)
        df['weekday_num'] = df['date'].dt.dayofweek
        
        # 한글 요일명 직접 매핑
        weekday_map = {
            0: '월요일', 1: '화요일', 2: '수요일',
            3: '목요일', 4: '금요일', 5: '토요일', 6: '일요일'
        }
        df['weekday'] = df['weekday_num'].map(weekday_map)
        
        # 영어 요일명도 추가 (호환성)
        df['weekday_name'] = df['date'].dt.day_name()
        
        df['month'] = df['date'].dt.to_period('M')
        df['week'] = df['date'].dt.to_period('W')
        df['is_weekend'] = df['weekday_num'].isin([5, 6])
        
        df['is_live'] = df['platform'].isin(LIVE_CHANNELS)
        df['model_cost'] = np.where(df['is_live'], MODEL_COST_LIVE, MODEL_COST_NON_LIVE)
        
        df['total_cost'] = df['cost'] + df['model_cost']
        df['real_profit'] = (df['revenue'] * REAL_MARGIN_RATE) - df['total_cost']
        
        df['roi_calculated'] = np.where(
            df['total_cost'] > 0,
            (df['real_profit'] / df['total_cost']) * 100,
            0
        )
        
        df['efficiency'] = np.where(
            df['total_cost'] > 0,
            df['revenue'] / df['total_cost'],
            0
        )
        
        df['channel_type'] = np.where(df['is_live'], '생방송', '비생방송')
        
        df['unit_price'] = np.where(
            df['units_sold'] > 0,
            df['revenue'] / df['units_sold'],
            0
        )
        
        return df

# ============================================================================
# 최적화된 데이터 처리 클래스
# ============================================================================

class OptimizedDataProcessor:
    """데이터 처리 및 계산 로직"""
    
    def __init__(self, db_path="schedule.db"):
        self.aggregate_loader = OptimizedAggregateLoader(db_path)
        self.db_path = db_path
        self._metrics_cache = {}
    
    def apply_filters_optimized(self, df, filters):
        """최적화된 필터 적용"""
        if len(df) == 0:
            return df
        
        cache_key = generate_cache_key(**filters)
        
        if 'start_date' in filters and 'end_date' in filters:
            mask = (df['date'].dt.date >= filters['start_date']) & \
                   (df['date'].dt.date <= filters['end_date'])
            df = df[mask]
        
        if 'revenue_limit' in filters:
            df = df[df['revenue'] <= filters['revenue_limit']]
        
        if 'weekday_filter' in filters:
            if filters['weekday_filter'] == "평일만":
                df = df[~df['is_weekend']]
            elif filters['weekday_filter'] == "주말만":
                df = df[df['is_weekend']]
        
        if 'selected_platforms' in filters and filters['selected_platforms']:
            df = df[df['platform'].isin(filters['selected_platforms'])]
        
        if 'selected_categories' in filters and filters['selected_categories']:
            df = df[df['category'].isin(filters['selected_categories'])]
        
        return df
    
    @st.cache_data(ttl=60, show_spinner=False)
    def calculate_metrics_cached(self, filter_hash: str, start_date: str, end_date: str):
        """캐시된 메트릭 계산"""
        return self._calculate_metrics_internal(start_date, end_date)
    
    def _calculate_metrics_internal(self, start_date=None, end_date=None):
        """내부 메트릭 계산"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        has_today_in_agg = self.aggregate_loader.check_today_in_aggregate()
        
        if not has_today_in_agg and (end_date is None or end_date >= today):
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            past_stats = self.aggregate_loader.load_daily_stats(
                start_date=start_date, 
                end_date=yesterday,
                exclude_today=True
            )
            
            today_data = self.aggregate_loader.get_today_data()
            
            past_metrics = self._calculate_from_aggregate(past_stats)
            today_metrics = self._calculate_from_raw(today_data)
            
            return self._merge_metrics_optimized(past_metrics, today_metrics)
        else:
            stats = self.aggregate_loader.load_daily_stats(start_date, end_date)
            return self._calculate_from_aggregate(stats)
    
    def _calculate_from_aggregate(self, daily_stats):
        """집계 데이터에서 메트릭 계산"""
        if len(daily_stats) == 0:
            return self._empty_metrics()
        
        metrics = {
            'total_revenue': daily_stats['revenue_sum'].sum(),
            'total_broadcast_cost': daily_stats['cost_sum'].sum() * 0.5,
            'total_model_cost': daily_stats['cost_sum'].sum() * 0.5,
            'total_cost': daily_stats['cost_sum'].sum(),
            'total_real_profit': daily_stats['profit_sum'].sum(),
            'total_units': daily_stats['units_sum'].sum(),
            'avg_roi': daily_stats['roi_mean'].mean(),
            'weighted_roi': 0,
            'clean_avg_revenue': daily_stats['revenue_mean'].mean(),
            'avg_efficiency': daily_stats['efficiency_mean'].mean(),
            'total_broadcasts': daily_stats['broadcast_count'].sum(),
            'zero_revenue_count': 0,
            'zero_revenue_ratio': 0
        }
        
        if metrics['total_cost'] > 0:
            metrics['weighted_roi'] = (metrics['total_real_profit'] / metrics['total_cost']) * 100
        
        return metrics
    
    def _calculate_from_raw(self, df):
        """원본 데이터에서 메트릭 계산"""
        if len(df) == 0:
            return self._empty_metrics()
        
        df_nonzero = df[df['revenue'] > 0]
        df_with_cost = df_nonzero[df_nonzero['total_cost'] > 0]
        
        metrics = {
            'total_revenue': df['revenue'].sum(),
            'total_broadcast_cost': df['cost'].sum(),
            'total_model_cost': df['model_cost'].sum(),
            'total_cost': df['total_cost'].sum(),
            'total_real_profit': df['real_profit'].sum(),
            'total_units': df['units_sold'].sum(),
            'avg_roi': df_with_cost['roi_calculated'].mean() if len(df_with_cost) > 0 else 0,
            'weighted_roi': 0,
            'clean_avg_revenue': df_nonzero['revenue'].mean() if len(df_nonzero) > 0 else 0,
            'avg_efficiency': df_with_cost['efficiency'].mean() if len(df_with_cost) > 0 else 0,
            'total_broadcasts': len(df),
            'zero_revenue_count': (df['revenue'] == 0).sum(),
            'zero_revenue_ratio': 0
        }
        
        if metrics['total_broadcasts'] > 0:
            metrics['zero_revenue_ratio'] = (metrics['zero_revenue_count'] / metrics['total_broadcasts']) * 100
        
        if metrics['total_cost'] > 0:
            metrics['weighted_roi'] = (metrics['total_real_profit'] / metrics['total_cost']) * 100
        
        return metrics
    
    def _merge_metrics_optimized(self, past_metrics, today_metrics):
        """최적화된 메트릭 병합"""
        sum_keys = [
            'total_revenue', 'total_broadcast_cost', 'total_model_cost', 
            'total_cost', 'total_real_profit', 'total_units', 
            'total_broadcasts', 'zero_revenue_count'
        ]
        
        merged = {key: past_metrics.get(key, 0) + today_metrics.get(key, 0) 
                  for key in sum_keys}
        
        total_broadcasts = merged['total_broadcasts']
        if total_broadcasts > 0:
            past_weight = past_metrics['total_broadcasts'] / total_broadcasts
            today_weight = today_metrics['total_broadcasts'] / total_broadcasts
            
            merged['avg_roi'] = (past_metrics['avg_roi'] * past_weight + 
                                today_metrics['avg_roi'] * today_weight)
            merged['avg_efficiency'] = (past_metrics['avg_efficiency'] * past_weight + 
                                       today_metrics['avg_efficiency'] * today_weight)
            merged['clean_avg_revenue'] = (past_metrics['clean_avg_revenue'] * past_weight + 
                                          today_metrics['clean_avg_revenue'] * today_weight)
        else:
            merged.update({'avg_roi': 0, 'avg_efficiency': 0, 'clean_avg_revenue': 0})
        
        if merged['total_cost'] > 0:
            merged['weighted_roi'] = (merged['total_real_profit'] / merged['total_cost']) * 100
        else:
            merged['weighted_roi'] = 0
        
        if merged['total_broadcasts'] > 0:
            merged['zero_revenue_ratio'] = (merged['zero_revenue_count'] / merged['total_broadcasts']) * 100
        else:
            merged['zero_revenue_ratio'] = 0
        
        return merged
    
    def get_batch_stats(self, stat_types: List[str]):
        """여러 통계를 한 번에 가져오기"""
        return self.aggregate_loader.load_batch_stats(stat_types)
    
    @staticmethod
    def _empty_metrics():
        """빈 메트릭 반환"""
        return {
            'total_revenue': 0,
            'total_broadcast_cost': 0,
            'total_model_cost': 0,
            'total_cost': 0,
            'total_real_profit': 0,
            'total_units': 0,
            'avg_roi': 0,
            'weighted_roi': 0,
            'clean_avg_revenue': 0,
            'avg_efficiency': 0,
            'total_broadcasts': 0,
            'zero_revenue_count': 0,
            'zero_revenue_ratio': 0
        }

# ============================================================================
# 포매터 클래스 - safe_abs() 적용
# ============================================================================

class DataFormatter:
    """데이터 포매팅 유틸리티 - safe_abs() 사용"""
    
    @staticmethod
    def format_money(value, unit='auto', precision=2):
        """금액 포맷팅 - safe_abs() 사용"""
        if pd.isna(value) or value == 0:
            return "0원"
        
        # safe_abs() 사용으로 변경
        abs_value = safe_abs(value)
        
        # 음수 체크를 위해 원본 값과 비교
        try:
            numeric_value = float(value) if not isinstance(value, (int, float)) else value
            sign = "-" if numeric_value < 0 else ""
        except:
            sign = ""
        
        if unit == 'auto':
            if abs_value >= 100000000:  # 1억 이상
                result = abs_value / 100000000
                if result >= 10:
                    return f"{sign}{result:.1f}억"
                else:
                    return f"{sign}{result:.2f}억"
            elif abs_value >= 10000000:  # 1천만원 이상
                if abs_value >= 50000000:  # 5천만원 이상은 억 단위
                    result = abs_value / 100000000
                    return f"{sign}{result:.2f}억"
                else:
                    result = abs_value / 10000000
                    return f"{sign}{result:.0f}천만"
            elif abs_value >= 1000000:  # 100만원 이상
                result = abs_value / 10000
                return f"{sign}{result:.0f}만원"
            else:
                return f"{sign}{abs_value:,.0f}원"
        
        elif unit == '억':
            result = abs_value / 100000000
            if result >= 10:
                return f"{sign}{result:.1f}억"
            else:
                return f"{sign}{result:.{precision}f}억"
        
        elif unit == '만원':
            result = abs_value / 10000
            if result >= 10000:
                return f"{sign}{result:,.0f}만원"
            else:
                return f"{sign}{result:.0f}만원"
        
        else:  # '원'
            return f"{sign}{abs_value:,.0f}원"
    
    @staticmethod
    def format_money_short(value):
        """축약형 금액 포매팅 - safe_abs() 사용"""
        if pd.isna(value) or value == 0:
            return "0"
        
        # safe_abs() 사용으로 변경
        abs_value = safe_abs(value)
        
        # 음수 체크
        try:
            numeric_value = float(value) if not isinstance(value, (int, float)) else value
            sign = "-" if numeric_value < 0 else ""
        except:
            sign = ""
        
        if abs_value >= 100000000:  # 1억 이상
            result = abs_value / 100000000
            return f"{sign}{result:.2f}억"
        elif abs_value >= 10000000:  # 1천만원 이상
            result = abs_value / 10000000
            return f"{sign}{result:.1f}천만"
        elif abs_value >= 1000000:  # 100만원 이상
            result = abs_value / 10000
            return f"{sign}{result:.0f}만"
        else:
            return f"{sign}{abs_value:,.0f}"
    
    @staticmethod
    def format_price(value):
        """판매단가 포맷"""
        if pd.isna(value):
            return "N/A"
        # safe_abs() 사용
        abs_value = safe_abs(value)
        return f"{int(abs_value):,}원"
    
    @staticmethod
    def format_percentage(value, decimals=1):
        """퍼센트 포맷"""
        if pd.isna(value):
            return "N/A"
        # safe_abs() 사용하여 안전하게 처리
        numeric_value = safe_abs(value)
        # 원본 부호 유지
        try:
            original_value = float(value) if not isinstance(value, (int, float)) else value
            if original_value < 0:
                return f"-{numeric_value:.{decimals}f}%"
        except:
            pass
        return f"{numeric_value:.{decimals}f}%"
    
    @staticmethod
    def format_number(value):
        """숫자 포맷"""
        if pd.isna(value):
            return "N/A"
        # safe_abs() 사용
        abs_value = safe_abs(value)
        return f"{int(abs_value):,}"
    
    @staticmethod
    def format_units(value):
        """판매수량 포맷"""
        if pd.isna(value):
            return "N/A"
        
        # safe_abs() 사용
        abs_value = safe_abs(value)
        
        if abs_value >= 1e6:
            return f"{abs_value/1e6:.1f}백만개"
        elif abs_value >= 1e4:
            return f"{abs_value/1e4:.1f}만개"
        else:
            return f"{int(abs_value):,}개"

# ============================================================================
# 색상 유틸리티
# ============================================================================

class ColorUtils:
    """색상 관련 유틸리티"""
    
    @staticmethod
    def get_dynamic_colors(items, base_colors):
        """동적 색상 생성"""
        if len(items) <= len(base_colors):
            return {item: list(base_colors.values())[i] for i, item in enumerate(items)}
        
        result = {}
        for i, item in enumerate(items):
            if item in base_colors:
                result[item] = base_colors[item]
            else:
                hue = (i * 360 / len(items)) % 360
                rgb = colorsys.hsv_to_rgb(hue/360, 0.3, 0.95)
                result[item] = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
        return result

# ============================================================================
# 데이터 검증
# ============================================================================

class DataValidator:
    """데이터 유효성 검증"""
    
    @staticmethod
    def validate_data(df):
        """데이터 유효성 검사"""
        issues = []
        warnings = []
        
        required_columns = ['date', 'time', 'platform', 'revenue', 'cost']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"필수 컬럼 누락: {', '.join(missing_columns)}")
        
        if len(df) == 0:
            issues.append("데이터가 비어있습니다")
        elif len(df) < 100:
            warnings.append(f"데이터가 적습니다 ({len(df)}건)")
        
        if 'date' in df.columns:
            date_range = (df['date'].max() - df['date'].min()).days
            if date_range < 7:
                warnings.append(f"데이터 기간이 짧습니다 ({date_range}일)")
        
        if 'revenue' in df.columns:
            zero_ratio = len(df[df['revenue'] == 0]) / len(df) * 100
            if zero_ratio > 50:
                warnings.append(f"매출 0원 비율이 높습니다 ({zero_ratio:.1f}%)")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

# ============================================================================
# 메인 데이터 관리자
# ============================================================================

class DataManager:
    """데이터 관리 통합 클래스"""
    
    def __init__(self, db_path="schedule.db"):
        self.db_path = db_path
        self.loader = OptimizedDataLoader(db_path)
        self.processor = OptimizedDataProcessor(db_path)
        self.formatter = DataFormatter()
        self.validator = DataValidator()
        self.color_utils = ColorUtils()
        self.aggregate_loader = OptimizedAggregateLoader(db_path)
        
        self.use_aggregates = self.aggregate_loader.has_aggregates
        
        self._batch_queue = []
    
    def get_data(self, days_back=30, force_all=False):
        """데이터 로드 및 검증"""
        if self.use_aggregates:
            return pd.DataFrame()
        
        df = self.loader.load_data(days_back=days_back, force_all=force_all)
        
        validation = self.validator.validate_data(df)
        if not validation['is_valid']:
            st.error(f"데이터 오류: {', '.join(validation['issues'])}")
            st.stop()
        
        for warning in validation['warnings']:
            st.warning(warning)
        
        return df
    
    def apply_filters(self, df, filters):
        """필터 적용"""
        return self.processor.apply_filters_optimized(df, filters)
    
    def get_metrics(self, df=None, filters=None):
        """메트릭 계산"""
        if self.use_aggregates:
            start_date = filters.get('start_date') if filters else None
            end_date = filters.get('end_date') if filters else None
            
            filter_hash = generate_cache_key(**(filters or {}))
            
            return self.processor.calculate_metrics_cached(
                filter_hash, 
                start_date.strftime('%Y-%m-%d') if start_date else None,
                end_date.strftime('%Y-%m-%d') if end_date else None
            )
        else:
            return self.processor._calculate_from_raw(df)
    
    def get_stats(self, df=None, stat_types=None):
        """통계 계산"""
        if self.use_aggregates and stat_types:
            if isinstance(stat_types, str):
                stat_types = [stat_types]
            
            return self.processor.get_batch_stats(stat_types)
        
        return self._calculate_stats_from_raw(df, stat_types)
    
    def batch_update(self, **kwargs):
        """배치 업데이트"""
        self._batch_queue.append(kwargs)
        
        if len(self._batch_queue) >= 10:
            self.process_batch()
    
    def process_batch(self):
        """배치 작업 처리"""
        if not self._batch_queue:
            return
        
        for operation in self._batch_queue:
            pass
        
        self._batch_queue.clear()
    
    def _calculate_stats_from_raw(self, df, stat_type):
        """원본 데이터에서 통계 계산"""
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        df_nonzero = df[df['revenue'] > 0]
        
        if isinstance(stat_type, list):
            results = {}
            for st in stat_type:
                results[st] = self._calculate_single_stat(df, df_nonzero, st)
            return results
        else:
            return self._calculate_single_stat(df, df_nonzero, stat_type)
    
    def _calculate_single_stat(self, df, df_nonzero, stat_type):
        """단일 통계 계산"""
        if stat_type == 'platform':
            return df_nonzero.groupby('platform').agg({
                'revenue': ['sum', 'mean'],
                'real_profit': 'sum',
                'total_cost': 'sum',
                'units_sold': 'sum',
                'broadcast': 'count',
                'is_live': 'first'
            }).reset_index()
        
        elif stat_type == 'hourly':
            hourly_stats = []
            for hour in range(24):
                hour_mask = df['hour'] == hour
                hour_data = df[hour_mask]
                hour_nonzero = df_nonzero[df_nonzero['hour'] == hour]
                
                if len(hour_data) > 0:
                    hourly_stats.append({
                        'hour': hour,
                        'revenue_mean': hour_nonzero['revenue'].mean() if len(hour_nonzero) > 0 else 0,
                        'revenue_sum': hour_data['revenue'].sum(),
                        'roi_mean': hour_data['roi_calculated'].mean(),
                        'broadcast_count': len(hour_data)
                    })
            
            return pd.DataFrame(hourly_stats)
        
        elif stat_type == 'category':
            return df_nonzero.groupby('category').agg({
                'revenue': ['sum', 'mean'],
                'units_sold': 'sum',
                'broadcast': 'count'
            }).reset_index()
        
        elif stat_type == 'weekday':
            weekday_names_kr = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
            
            weekday_stats = []
            for weekday in range(7):
                wd_mask = df['weekday'] == weekday
                wd_data = df[wd_mask]
                wd_nonzero = df_nonzero[df_nonzero['weekday'] == weekday]
                
                if len(wd_data) > 0:
                    weekday_stats.append({
                        'weekday': weekday,
                        'weekday_name': weekday_names_kr[weekday],
                        'revenue_sum': wd_data['revenue'].sum(),
                        'revenue_mean': wd_nonzero['revenue'].mean() if len(wd_nonzero) > 0 else 0,
                        'units_sum': wd_data['units_sold'].sum(),
                        'broadcast_count': len(wd_data)
                    })
            
            return pd.DataFrame(weekday_stats)
        
        return pd.DataFrame()

# ============================================================================
# 추가 최적화 함수들
# ============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_summary_stats(df):
    """요약 통계"""
    if len(df) == 0:
        return {}
    
    return {
        'total_records': len(df),
        'date_range': f"{df['date'].min().date()} ~ {df['date'].max().date()}",
        'unique_platforms': df['platform'].nunique(),
        'unique_categories': df['category'].nunique(),
        'avg_daily_revenue': df.groupby(df['date'].dt.date)['revenue'].sum().mean(),
        'top_platform': df.groupby('platform')['revenue'].sum().idxmax() if len(df) > 0 else '',
        'top_category': df.groupby('category')['revenue'].sum().idxmax() if len(df) > 0 else ''
    }

@st.cache_data(ttl=1800, show_spinner=False)
def get_time_series_data(df, period='daily'):
    """시계열 데이터 준비"""
    if len(df) == 0:
        return pd.DataFrame()
    
    if period == 'daily':
        return df.groupby(df['date'].dt.date).agg({
            'revenue': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
    elif period == 'weekly':
        return df.groupby(df['date'].dt.to_period('W')).agg({
            'revenue': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
    elif period == 'monthly':
        return df.groupby(df['date'].dt.to_period('M')).agg({
            'revenue': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
    else:
        return df

# ============================================================================
# 성능 모니터링
# ============================================================================

def show_performance_metrics():
    """성능 지표 표시"""
    if 'data_load_time' in st.session_state:
        load_time = st.session_state.data_load_time
        if load_time < 0.1:
            st.sidebar.success(f"⚡ 초고속 로딩: {load_time:.3f}초")
        elif load_time < 0.5:
            st.sidebar.success(f"🚀 빠른 로딩: {load_time:.2f}초")
        elif load_time < 2:
            st.sidebar.info(f"📊 로딩 시간: {load_time:.2f}초")
        else:
            st.sidebar.warning(f"🌐 로딩 시간: {load_time:.2f}초")

# ============================================================================
# 전처리 헬퍼 함수 추가 (정밀 분석 탭에서 사용)
# ============================================================================

def preprocess_numeric_columns(df):
    """숫자 컬럼 데이터 타입 확인 및 변환 - 완전히 안전한 버전"""
    import pandas as pd
    import numpy as np
    
    # 복사본 생성
    df = df.copy()
    
    # 숫자로 변환해야 할 컬럼들
    numeric_columns = ['revenue', 'units_sold', 'cost', 'total_cost', 'real_profit', 
                      'model_cost', 'roi', 'roi_calculated', 'product_count']
    
    for col in numeric_columns:
        if col in df.columns:
            try:
                # Series로 확실히 변환 후 numeric 변환
                if not isinstance(df[col], pd.Series):
                    df[col] = pd.Series(df[col])
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                df[col] = df[col].replace([np.inf, -np.inf], 0)
            except:
                df[col] = 0
    
    # hour와 weekday도 정수로 변환
    if 'hour' in df.columns:
        try:
            if not isinstance(df['hour'], pd.Series):
                df['hour'] = pd.Series(df['hour'])
            df['hour'] = pd.to_numeric(df['hour'], errors='coerce').fillna(0).astype(int)
        except:
            df['hour'] = 0
    
    if 'weekday' in df.columns:
        try:
            if not isinstance(df['weekday'], pd.Series):
                df['weekday'] = pd.Series(df['weekday'])
            df['weekday'] = pd.to_numeric(df['weekday'], errors='coerce').fillna(0).astype(int)
        except:
            df['weekday'] = 0
    
    return df

# ============================================================================
# 가중평균 ROI 계산 함수 추가 (정밀 분석 탭에서 사용)
# ============================================================================

def calculate_weighted_roi(df_group):
    """가중평균 ROI 계산 - 실질 이익의 합 / 비용의 합"""
    # 데이터 타입 확인 및 변환
    if 'revenue' in df_group.columns:
        df_group['revenue'] = pd.to_numeric(df_group['revenue'], errors='coerce').fillna(0)
    
    if 'total_cost' in df_group.columns:
        df_group['total_cost'] = pd.to_numeric(df_group['total_cost'], errors='coerce').fillna(0)
    elif 'cost' in df_group.columns:
        df_group['cost'] = pd.to_numeric(df_group['cost'], errors='coerce').fillna(0)
    
    total_revenue = df_group['revenue'].sum()
    total_cost = df_group['total_cost'].sum() if 'total_cost' in df_group.columns else df_group['cost'].sum()
    
    if total_cost > 0:
        total_real_profit = total_revenue * REAL_MARGIN_RATE - total_cost
        weighted_roi = (total_real_profit / total_cost) * 100
        return weighted_roi
    return 0