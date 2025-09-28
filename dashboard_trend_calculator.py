"""
dashboard_trend_calculator.py - 추세 지표 계산 모듈
Version: 1.1.0
Created: 2025-01-25
Updated: 2025-09-12 - 타입 안정성 강화

홈쇼핑 매출 데이터의 추세 지표를 계산하는 핵심 모듈
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TrendCalculator:
    """추세 지표 계산 클래스 (타입 안정성 강화)"""
    
    def __init__(self):
        """초기화"""
        self.min_periods_ma = 1  # 이동평균 최소 기간
        self.anomaly_threshold = 3  # 이상치 감지 Z-score 임계값
        
    def _validate_numeric_column(self, series, column_name):
        """
        숫자 컬럼 검증 및 변환
        
        Parameters:
        -----------
        series : Series
            검증할 시리즈
        column_name : str
            컬럼 이름
            
        Returns:
        --------
        Series : 검증된 숫자 시리즈
        """
        # 먼저 Series로 변환
        if not isinstance(series, pd.Series):
            series = pd.Series(series)
            
        # 숫자 타입이 아닌 경우 변환
        if series.dtype not in ['float64', 'int64', 'float32', 'int32']:
            print(f"⚠️ {column_name} 컬럼 타입 변환: {series.dtype} → float64")
            series = pd.to_numeric(series, errors='coerce')
            series = series.fillna(0)
        
        # NaN 값 처리
        if series.isna().any():
            series = series.fillna(0)
            
        return series.astype('float64')
    
    def _safe_division(self, numerator, denominator, default=0):
        """
        안전한 나눗셈 (0으로 나누기 방지)
        
        Parameters:
        -----------
        numerator : array-like
            분자
        denominator : array-like
            분모
        default : float
            기본값
            
        Returns:
        --------
        array-like : 나눗셈 결과
        """
        return np.where(denominator != 0, numerator / denominator, default)
    
    def calculate_growth_rates(self, df):
        """
        각종 성장률 계산 (타입 검증 포함)
        
        Parameters:
        -----------
        df : DataFrame
            date와 revenue 컬럼이 있는 데이터프레임
            
        Returns:
        --------
        DataFrame : 성장률 컬럼이 추가된 데이터프레임
        """
        df = df.copy()
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            print("⚠️ revenue 컬럼이 없습니다")
            return df
        
        df = df.sort_values('date')
        
        # 전일 대비 (Day over Day)
        df['revenue_dod'] = df['revenue'].pct_change() * 100
        
        # 전주 대비 (Week over Week) - 7일 전
        df['revenue_wow'] = df['revenue'].pct_change(periods=7) * 100
        
        # 전월 대비 (Month over Month) - 30일 전
        df['revenue_mom'] = df['revenue'].pct_change(periods=30) * 100
        
        # 전년 동기 대비 (Year over Year) - 365일 전
        df['revenue_yoy'] = df['revenue'].pct_change(periods=365) * 100
        
        # 누적 성장률
        first_value = df['revenue'].iloc[0] if len(df) > 0 else 1
        if first_value > 0:
            df['cumulative_growth'] = ((df['revenue'].cumsum() / first_value) - 1) * 100
        else:
            df['cumulative_growth'] = 0
        
        # 복합 연간 성장률 (CAGR) - 최근 30일 기준
        def calculate_cagr(values):
            if len(values) < 2 or values.iloc[0] == 0:
                return np.nan
            periods = len(values) - 1
            return (((values.iloc[-1] / values.iloc[0]) ** (365 / periods)) - 1) * 100
        
        df['cagr_30d'] = df['revenue'].rolling(window=30, min_periods=2).apply(calculate_cagr)
        
        return df
    
    def calculate_moving_averages(self, df):
        """
        이동평균 계산 (타입 검증 포함)
        
        Parameters:
        -----------
        df : DataFrame
            
        Returns:
        --------
        DataFrame : 이동평균 컬럼이 추가된 데이터프레임
        """
        df = df.copy()
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return df
        
        # 단순 이동평균 (SMA)
        df['ma_7'] = df['revenue'].rolling(window=7, min_periods=self.min_periods_ma).mean()
        df['ma_30'] = df['revenue'].rolling(window=30, min_periods=self.min_periods_ma).mean()
        df['ma_90'] = df['revenue'].rolling(window=90, min_periods=self.min_periods_ma).mean()
        
        # 지수 이동평균 (EMA)
        df['ema_7'] = df['revenue'].ewm(span=7, adjust=False).mean()
        df['ema_30'] = df['revenue'].ewm(span=30, adjust=False).mean()
        
        # 가중 이동평균 (WMA) - 최근 데이터에 더 큰 가중치
        def weighted_average(values):
            weights = np.arange(1, len(values) + 1)
            return np.average(values, weights=weights)
        
        df['wma_7'] = df['revenue'].rolling(window=7, min_periods=self.min_periods_ma).apply(weighted_average)
        
        # 이동평균 대비 현재값 비율 (0으로 나누기 방지)
        df['ma_ratio_7'] = self._safe_division(df['revenue'], df['ma_7'], 100) * 100
        df['ma_ratio_30'] = self._safe_division(df['revenue'], df['ma_30'], 100) * 100
        
        return df
    
    def calculate_volatility(self, df):
        """
        변동성 지표 계산 (타입 검증 포함)
        
        Parameters:
        -----------
        df : DataFrame
            
        Returns:
        --------
        DataFrame : 변동성 지표가 추가된 데이터프레임
        """
        df = df.copy()
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return df
        
        # 일별 변동성 (표준편차)
        df['volatility_7'] = df['revenue'].rolling(window=7).std()
        df['volatility_30'] = df['revenue'].rolling(window=30).std()
        
        # 변동계수 (CV = 표준편차/평균) - 0으로 나누기 방지
        if 'ma_7' in df.columns:
            df['cv_7'] = self._safe_division(df['volatility_7'], df['ma_7'], 0)
        if 'ma_30' in df.columns:
            df['cv_30'] = self._safe_division(df['volatility_30'], df['ma_30'], 0)
        
        # 볼린저 밴드
        if 'ma_30' in df.columns:
            df['bb_upper'] = df['ma_30'] + (2 * df['volatility_30'].fillna(0))
            df['bb_lower'] = df['ma_30'] - (2 * df['volatility_30'].fillna(0))
            df['bb_width'] = df['bb_upper'] - df['bb_lower']
            df['bb_position'] = self._safe_division(
                df['revenue'] - df['bb_lower'], 
                df['bb_width'], 
                0.5
            )
        
        # 일중 변동률 (전일 대비 절대값)
        df['daily_volatility'] = df['revenue'].pct_change().abs() * 100
        
        # ATR (Average True Range) 유사 지표
        df['range'] = df['revenue'].rolling(window=14).apply(lambda x: x.max() - x.min())
        
        # 변동성 지수 (VIX 유사)
        df['volatility_index'] = df['daily_volatility'].rolling(window=30).mean()
        
        return df
    
    def detect_trend_direction(self, df):
        """
        추세 방향 감지 (타입 검증 포함)
        
        Parameters:
        -----------
        df : DataFrame
            
        Returns:
        --------
        DataFrame : 추세 방향이 추가된 데이터프레임
        """
        df = df.copy()
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            # 더 확실한 타입 변환
            try:
                df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0).astype(float)
            except Exception as e:
                print(f"Revenue 컬럼 타입 변환 실패: {e}")
                return df
        else:
            return df
        
        def get_trend(values):
            """선형 회귀로 추세 계산"""
            # 타입 체크 및 변환
            if not isinstance(values, np.ndarray):
                values = np.array(values, dtype=float)
            
            # 숫자 타입 보장
            values = values.astype(float)
            
            if len(values) < 3:
                return 'stable'
            
            x = np.arange(len(values))
            # 결측값 제거
            mask = ~np.isnan(values)
            if mask.sum() < 3:
                return 'stable'
            
            x_clean = x[mask]
            y_clean = values[mask]
            
            try:
                # 선형 회귀
                slope, _ = np.polyfit(x_clean, y_clean, 1)
                
                # 기울기를 평균값 대비 비율로 정규화
                mean_val = np.mean(y_clean)
                if mean_val > 0:
                    normalized_slope = slope / mean_val
                    
                    if normalized_slope > 0.01:  # 1% 이상 상승
                        return 'up'
                    elif normalized_slope < -0.01:  # 1% 이상 하락
                        return 'down'
            except:
                return 'stable'
            
            return 'stable'
        
        # 7일 윈도우로 추세 방향 계산
        df['trend_direction_7'] = df['revenue'].rolling(window=7).apply(get_trend, raw=True)
        
        # 30일 윈도우로 장기 추세
        df['trend_direction_30'] = df['revenue'].rolling(window=30).apply(get_trend, raw=True)
        
        # 추세 강도 계산 (0~1)
        def calculate_trend_strength(values):
            """추세 강도 계산 (R-squared)"""
            if len(values) < 3:
                return 0
            
            x = np.arange(len(values))
            mask = ~np.isnan(values)
            if mask.sum() < 3:
                return 0
            
            x_clean = x[mask]
            y_clean = values[mask]
            
            try:
                # 상관계수의 제곱 (R²)
                correlation = np.corrcoef(x_clean, y_clean)[0, 1]
                return abs(correlation)
            except:
                return 0
        
        df['trend_strength_7'] = df['revenue'].rolling(window=7).apply(calculate_trend_strength, raw=True)
        df['trend_strength_30'] = df['revenue'].rolling(window=30).apply(calculate_trend_strength, raw=True)
        
        # 모멘텀 지표
        df['momentum_3'] = df['revenue'] - df['revenue'].shift(3)
        df['momentum_7'] = df['revenue'] - df['revenue'].shift(7)
        
        # RSI (Relative Strength Index) 계산
        def calculate_rsi(values, period=14):
            if len(values) < period:
                return 50  # 중립값
            
            try:
                deltas = np.diff(values)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gain = np.mean(gains[-period:])
                avg_loss = np.mean(losses[-period:])
                
                if avg_loss == 0:
                    return 100
                
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                return rsi
            except:
                return 50
        
        df['rsi_14'] = df['revenue'].rolling(window=15).apply(lambda x: calculate_rsi(x, 14), raw=True)
        
        return df
    
    def calculate_seasonality(self, df):
        """
        계절성 지표 계산 (타입 검증 포함)
        
        Parameters:
        -----------
        df : DataFrame
            date 컬럼이 datetime 형식이어야 함
            
        Returns:
        --------
        DataFrame : 계절성 지표가 추가된 데이터프레임
        """
        df = df.copy()
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return df
        
        # datetime 변환
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # 날짜 관련 특성 추출
        df['month'] = df['date'].dt.month
        df['weekday'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['week_of_year'] = df['date'].dt.isocalendar().week
        df['quarter'] = df['date'].dt.quarter
        
        # 월별 평균 대비 현재 값의 비율
        monthly_avg = df.groupby('month')['revenue'].transform('mean')
        df['seasonal_index_month'] = self._safe_division(df['revenue'], monthly_avg, 100) * 100
        
        # 요일별 패턴
        weekday_avg = df.groupby('weekday')['revenue'].transform('mean')
        df['weekday_index'] = self._safe_division(df['revenue'], weekday_avg, 100) * 100
        
        # 분기별 패턴
        quarterly_avg = df.groupby('quarter')['revenue'].transform('mean')
        df['quarterly_index'] = self._safe_division(df['revenue'], quarterly_avg, 100) * 100
        
        # 월초/월중/월말 패턴
        df['month_period'] = pd.cut(df['day_of_month'], 
                                    bins=[0, 10, 20, 31], 
                                    labels=['월초', '월중', '월말'])
        month_period_avg = df.groupby('month_period')['revenue'].transform('mean')
        df['month_period_index'] = self._safe_division(df['revenue'], month_period_avg, 100) * 100
        
        # 연간 추세 제거 후 계절성 (Detrended)
        if len(df) > 365:
            # 365일 이동평균으로 추세 제거
            df['yearly_trend'] = df['revenue'].rolling(window=365, center=True, min_periods=30).mean()
            df['detrended'] = df['revenue'] - df['yearly_trend'].fillna(df['revenue'].mean())
            df['seasonal_component'] = df['detrended'].rolling(window=30, center=True).mean()
        
        return df
    
    def detect_anomalies(self, df, threshold=None):
        """
        이상치 감지 (타입 안전)
        
        Parameters:
        -----------
        df : DataFrame
        threshold : float
            Z-score 임계값 (기본값: 3)
            
        Returns:
        --------
        DataFrame : 이상치 정보가 추가된 데이터프레임
        """
        df = df.copy()
        
        if threshold is None:
            threshold = self.anomaly_threshold
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return df
        
        # Z-score 기반 이상치 감지
        revenue_mean = df['revenue'].mean()
        revenue_std = df['revenue'].std()
        
        if revenue_std > 0:
            df['z_score'] = np.abs((df['revenue'] - revenue_mean) / revenue_std)
        else:
            df['z_score'] = 0
        
        df['is_anomaly_zscore'] = df['z_score'] > threshold
        
        # IQR 기반 이상치 감지
        Q1 = df['revenue'].quantile(0.25)
        Q3 = df['revenue'].quantile(0.75)
        IQR = Q3 - Q1
        df['is_outlier_iqr'] = ((df['revenue'] < (Q1 - 1.5 * IQR)) | 
                                (df['revenue'] > (Q3 + 1.5 * IQR)))
        
        # 이동평균 대비 편차 기반 감지
        if 'ma_30' in df.columns:
            df['ma_30'] = self._validate_numeric_column(df['ma_30'], 'ma_30')
            df['deviation_from_ma'] = self._safe_division(
                abs(df['revenue'] - df['ma_30']), 
                df['ma_30'], 
                0
            ) * 100
            df['is_anomaly_ma'] = df['deviation_from_ma'] > 50  # 50% 이상 편차
        
        # Isolation Forest 유사 방법 (간단 버전)
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            # 볼린저 밴드 밖의 값
            df['is_anomaly_bb'] = ((df['revenue'] > df['bb_upper']) | 
                                   (df['revenue'] < df['bb_lower']))
        
        # 종합 이상치 플래그
        anomaly_columns = [col for col in df.columns if col.startswith('is_anomaly') or col.startswith('is_outlier')]
        if anomaly_columns:
            df['is_anomaly'] = df[anomaly_columns].any(axis=1)
        else:
            df['is_anomaly'] = False
        
        # 이상치 점수 (0~1)
        if anomaly_columns:
            df['anomaly_score'] = df[anomaly_columns].sum(axis=1) / len(anomaly_columns)
        else:
            df['anomaly_score'] = 0
        
        return df
    
    def calculate_forecast_metrics(self, df, forecast_days=7):
        """
        예측 관련 메트릭 계산 (간단한 선형 추세)
        
        Parameters:
        -----------
        df : DataFrame
        forecast_days : int
            예측할 일수
            
        Returns:
        --------
        dict : 예측 메트릭
        """
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return {
                'trend_slope': 0,
                'forecast_revenue': 0,
                'confidence_interval': (0, 0),
                'r_squared': 0
            }
        
        if len(df) < 7:
            return {
                'trend_slope': 0,
                'forecast_revenue': df['revenue'].mean() if len(df) > 0 else 0,
                'confidence_interval': (0, 0),
                'r_squared': 0
            }
        
        # 최근 데이터로 선형 회귀
        recent_days = min(30, len(df))
        recent_data = df.tail(recent_days).copy()
        recent_data['day_num'] = range(len(recent_data))
        
        # 선형 회귀 계수 계산
        x = recent_data['day_num'].values
        y = recent_data['revenue'].values
        
        # 결측값 제거
        mask = ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return {
                'trend_slope': 0,
                'forecast_revenue': df['revenue'].mean(),
                'confidence_interval': (0, 0),
                'r_squared': 0
            }
        
        try:
            slope, intercept = np.polyfit(x_clean, y_clean, 1)
            
            # 예측값 계산
            forecast_x = len(recent_data) + forecast_days - 1
            forecast_revenue = slope * forecast_x + intercept
            
            # 신뢰구간 (간단한 버전)
            std_error = np.std(y_clean - (slope * x_clean + intercept))
            confidence_interval = (
                forecast_revenue - 2 * std_error,
                forecast_revenue + 2 * std_error
            )
            
            # R-squared 계산
            r_squared = np.corrcoef(x_clean, y_clean)[0, 1] ** 2 if len(x_clean) > 1 else 0
            
            return {
                'trend_slope': slope,
                'forecast_revenue': max(0, forecast_revenue),  # 음수 방지
                'confidence_interval': (max(0, confidence_interval[0]), confidence_interval[1]),
                'r_squared': r_squared
            }
        except:
            return {
                'trend_slope': 0,
                'forecast_revenue': df['revenue'].mean(),
                'confidence_interval': (0, 0),
                'r_squared': 0
            }
    
    def calculate_comparative_metrics(self, df, comparison_df=None):
        """
        비교 메트릭 계산 (전기 대비, 벤치마크 대비 등)
        
        Parameters:
        -----------
        df : DataFrame
            현재 데이터
        comparison_df : DataFrame
            비교 대상 데이터 (선택)
            
        Returns:
        --------
        dict : 비교 메트릭
        """
        metrics = {}
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return metrics
        
        # 기간별 평균 매출
        metrics['daily_avg'] = df['revenue'].mean()
        metrics['weekly_avg'] = df['revenue'].rolling(7).mean().iloc[-1] if len(df) >= 7 else metrics['daily_avg']
        metrics['monthly_avg'] = df['revenue'].rolling(30).mean().iloc[-1] if len(df) >= 30 else metrics['daily_avg']
        
        # 최고/최저 실적
        metrics['max_revenue'] = df['revenue'].max()
        metrics['min_revenue'] = df['revenue'].min()
        metrics['max_date'] = df.loc[df['revenue'].idxmax(), 'date'] if not df.empty else None
        metrics['min_date'] = df.loc[df['revenue'].idxmin(), 'date'] if not df.empty else None
        
        # 성장 추세
        if 'revenue_dod' in df.columns:
            metrics['avg_growth_rate'] = df['revenue_dod'].mean()
            metrics['growth_volatility'] = df['revenue_dod'].std()
        
        # 비교 데이터가 있는 경우
        if comparison_df is not None and not comparison_df.empty:
            if 'revenue' in comparison_df.columns:
                comparison_df['revenue'] = self._validate_numeric_column(
                    comparison_df['revenue'], 'comparison_revenue'
                )
                
                comp_mean = comparison_df['revenue'].mean()
                if comp_mean > 0:
                    metrics['vs_benchmark_avg'] = (
                        (df['revenue'].mean() - comp_mean) / comp_mean * 100
                    )
                    metrics['vs_benchmark_total'] = (
                        (df['revenue'].sum() - comparison_df['revenue'].sum()) / 
                        comparison_df['revenue'].sum() * 100
                    )
        
        return metrics
    
    def create_summary_statistics(self, df):
        """
        종합 통계 요약 생성 (타입 안전)
        
        Parameters:
        -----------
        df : DataFrame
            
        Returns:
        --------
        dict : 종합 통계
        """
        summary = {}
        
        # revenue 컬럼 타입 검증
        if 'revenue' in df.columns:
            df['revenue'] = self._validate_numeric_column(df['revenue'], 'revenue')
        else:
            return summary
        
        try:
            summary['기간'] = f"{df['date'].min()} ~ {df['date'].max()}"
            summary['총_일수'] = len(df)
            summary['총_매출'] = df['revenue'].sum()
            summary['평균_매출'] = df['revenue'].mean()
            summary['중앙값_매출'] = df['revenue'].median()
            summary['표준편차'] = df['revenue'].std()
            
            mean_revenue = df['revenue'].mean()
            if mean_revenue > 0:
                summary['변동계수'] = df['revenue'].std() / mean_revenue
            else:
                summary['변동계수'] = 0
            
            # 성장률 통계
            if 'revenue_dod' in df.columns:
                summary['평균_일일_성장률'] = df['revenue_dod'].mean()
                summary['최대_성장률'] = df['revenue_dod'].max()
                summary['최소_성장률'] = df['revenue_dod'].min()
            
            # 추세 통계
            if 'trend_direction_7' in df.columns:
                trend_counts = df['trend_direction_7'].value_counts()
                summary['상승_일수'] = trend_counts.get('up', 0)
                summary['하락_일수'] = trend_counts.get('down', 0)
                summary['보합_일수'] = trend_counts.get('stable', 0)
            
            # 이상치 통계
            if 'is_anomaly' in df.columns:
                summary['이상치_건수'] = df['is_anomaly'].sum()
                summary['이상치_비율'] = df['is_anomaly'].mean() * 100
            
        except Exception as e:
            print(f"요약 통계 생성 중 오류: {e}")
        
        return summary


# 유틸리티 함수들
def prepare_trend_data(df, date_col='date', revenue_col='revenue'):
    """
    추세 분석을 위한 데이터 전처리
    
    Parameters:
    -----------
    df : DataFrame
        원본 데이터
    date_col : str
        날짜 컬럼명
    revenue_col : str
        매출 컬럼명
        
    Returns:
    --------
    DataFrame : 전처리된 데이터
    """
    df_prep = df.copy()
    
    # 컬럼명 표준화
    if date_col != 'date':
        df_prep.rename(columns={date_col: 'date'}, inplace=True)
    if revenue_col != 'revenue':
        df_prep.rename(columns={revenue_col: 'revenue'}, inplace=True)
    
    # 날짜 형식 변환
    df_prep['date'] = pd.to_datetime(df_prep['date'], errors='coerce')
    
    # 정렬
    df_prep = df_prep.sort_values('date')
    
    # 타입 변환
    calculator = TrendCalculator()
    if 'revenue' in df_prep.columns:
        df_prep['revenue'] = calculator._validate_numeric_column(df_prep['revenue'], 'revenue')
    
    # 결측값 처리 (전방 채우기)
    df_prep['revenue'].fillna(method='ffill', inplace=True)
    
    return df_prep


def calculate_all_trend_metrics(df, include_forecast=False):
    """
    모든 추세 메트릭을 한 번에 계산 (안전한 버전)
    
    Parameters:
    -----------
    df : DataFrame
        전처리된 데이터
    include_forecast : bool
        예측 메트릭 포함 여부
        
    Returns:
    --------
    DataFrame : 모든 추세 메트릭이 포함된 데이터프레임
    """
    calculator = TrendCalculator()
    
    # 순차적으로 모든 메트릭 계산 (에러 처리 포함)
    try:
        df = calculator.calculate_growth_rates(df)
    except Exception as e:
        print(f"성장률 계산 실패: {e}")
    
    try:
        df = calculator.calculate_moving_averages(df)
    except Exception as e:
        print(f"이동평균 계산 실패: {e}")
    
    try:
        df = calculator.calculate_volatility(df)
    except Exception as e:
        print(f"변동성 계산 실패: {e}")
    
    try:
        df = calculator.detect_trend_direction(df)
    except Exception as e:
        print(f"추세 방향 계산 실패: {e}")
    
    try:
        df = calculator.calculate_seasonality(df)
    except Exception as e:
        print(f"계절성 계산 실패: {e}")
    
    try:
        df = calculator.detect_anomalies(df)
    except Exception as e:
        print(f"이상치 감지 실패: {e}")
    
    # 예측 메트릭 (선택)
    if include_forecast:
        try:
            forecast_metrics = calculator.calculate_forecast_metrics(df)
            for key, value in forecast_metrics.items():
                df[f'forecast_{key}'] = value
        except Exception as e:
            print(f"예측 메트릭 계산 실패: {e}")
    
    return df