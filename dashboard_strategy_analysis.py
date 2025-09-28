"""
dashboard_strategy_analysis.py - 전략 분석 탭
Version: 3.0.0
Created: 2025-02-16
Updated: 2025-09-16 - 완벽 수정 버전

홈쇼핑 전략 분석을 위한 대시보드 탭 - 최종 완벽 버전
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import traceback
from io import BytesIO
import plotly.io as pio

# 실질 마진율 설정
REAL_MARGIN_RATE = 0.5775  # 57.75% (전환율 75%, 원가율 13%, 수수료율 10%)

# 절사평균 계산 함수
def calculate_trimmed_mean(values, trim_percent=0.15):
    """절사평균 계산 - 상하위 15% 제외"""
    if len(values) == 0:
        return 0
    
    values = np.array(values)
    values = values[~np.isnan(values)]  # NaN 제거
    
    if len(values) == 0:
        return 0
    
    if len(values) < 10:  # 데이터가 너무 적으면 일반 평균
        return np.mean(values)
    
    trim_count = int(len(values) * trim_percent)
    if trim_count == 0:
        return np.mean(values)
    
    sorted_values = np.sort(values)
    trimmed_values = sorted_values[trim_count:-trim_count] if trim_count > 0 else sorted_values
    
    return np.mean(trimmed_values) if len(trimmed_values) > 0 else np.mean(values)

# 컬럼명 매핑 - 다양한 형식 지원
COLUMN_MAPPING = {
    'platform': ['platform', '채널명', 'channel', '방송사'],
    'date': ['date', '방송일자', 'broadcast_date', '날짜'],
    'time': ['time', '방송시간', 'broadcast_time', '시간'],
    'category': ['category', '카테고리', 'product_category'],
    'broadcast': ['broadcast', '방송명', 'broadcast_name', '상품명', 'product'],
    'unit_price': ['unit_price', '판매단가', 'price', '단가'],
    'units_sold': ['units_sold', '판매개수', 'quantity', '수량'],
    'revenue': ['revenue', '매출', 'sales', '매출액'],
    'cost': ['cost', '비용', 'broadcast_cost'],
    'total_cost': ['total_cost', '총비용', 'total_broadcast_cost'],
    'roi_calculated': ['roi_calculated', 'roi', 'ROI']
}

def get_column_name(df, column_key):
    """데이터프레임에서 실제 컬럼명 찾기"""
    possible_names = COLUMN_MAPPING.get(column_key, [column_key])
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# 공통 유틸리티 함수 import
from dashboard_utils import (
    safe_to_json,
    json_to_df,
    generate_cache_key,
    format_short_number,
    show_loading_message,
    log_error
)

# dashboard_config에서 설정 import
from dashboard_config import (
    COLORS,
    PLATFORM_COLORS,
    CATEGORY_COLORS,
    WEEKDAY_COLORS,
    DEFAULT_HOVER_CONFIG,
    get_hover_config,
    emergency_hover_fix,
    MODEL_COST_LIVE,
    MODEL_COST_NON_LIVE,
    CONVERSION_RATE
)

def calculate_roi_metrics(df, broadcaster=None):
    """ROI 및 관련 메트릭 계산 - 수정된 ROI 공식 적용 (실질 마진율 57.75%)"""
    try:
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        
        # 컬럼명 자동 감지
        col_platform = get_column_name(df, 'platform')
        col_date = get_column_name(df, 'date')
        col_time = get_column_name(df, 'time')
        col_revenue = get_column_name(df, 'revenue')
        col_unit_price = get_column_name(df, 'unit_price')
        col_units_sold = get_column_name(df, 'units_sold')
        col_total_cost = get_column_name(df, 'total_cost')
        
        # 매출 0원 데이터 제외
        if col_revenue:
            df = df[df[col_revenue] > 0].copy()
        
        # total_cost 컬럼이 없으면 기본값 설정
        if col_total_cost is None:
            col_total_cost = 'total_cost'
            if col_total_cost not in df.columns:
                col_cost = get_column_name(df, 'cost')
                if col_cost:
                    df[col_total_cost] = df[col_cost]
                else:
                    # 비용 정보가 없으면 매출의 일정 비율로 추정
                    if col_revenue:
                        df[col_total_cost] = df[col_revenue] * 0.7
        
        # 방송사 필터링
        if broadcaster and broadcaster != '전체' and col_platform:
            df = df[df[col_platform] == broadcaster]
        
        # 시간대 정보 추가
        if 'hour' not in df.columns and col_time:
            df['hour'] = df[col_time].apply(
                lambda x: int(str(x).split(':')[0]) if ':' in str(x) else int(x) if str(x).isdigit() else 0
            )
        
        # 요일 정보 추가
        if 'weekday' not in df.columns and col_date:
            df['weekday_name'] = pd.to_datetime(df[col_date], errors='coerce').dt.day_name()
            # 한글 요일로 변환
            weekday_map = {
                'Monday': '월요일', 'Tuesday': '화요일', 'Wednesday': '수요일',
                'Thursday': '목요일', 'Friday': '금요일', 'Saturday': '토요일', 'Sunday': '일요일'
            }
            df['weekday'] = df['weekday_name'].map(weekday_map)
            df['is_weekend'] = df['weekday'].isin(['토요일', '일요일'])
        
        # 매출액 처리 - 단위 통일
        if col_revenue:
            df['revenue'] = pd.to_numeric(df[col_revenue], errors='coerce')
            # 매출액이 10000 이상이면 억원 단위로 변환
            if df['revenue'].mean() > 10000:
                df['revenue'] = df['revenue'] / 100000000
        
        # 비용도 동일한 단위로 변환
        if col_total_cost in df.columns:
            df[col_total_cost] = pd.to_numeric(df[col_total_cost], errors='coerce')
            # 비용도 억원 단위로 변환
            if df[col_total_cost].mean() > 10000:
                df[col_total_cost] = df[col_total_cost] / 100000000
        
        # ROI 계산 - 실질 마진율 57.75% 적용 (수정된 버전)
        if 'revenue' in df.columns and col_total_cost in df.columns:
            # ROI = ((매출 × 0.5775) - 총비용) / 총비용 × 100
            df['real_profit'] = df['revenue'] * REAL_MARGIN_RATE  # revenue 컬럼 사용
            df['roi'] = ((df['real_profit'] - df[col_total_cost]) / df[col_total_cost]) * 100
            # 무한대나 NaN 값 처리
            df['roi'] = df['roi'].replace([np.inf, -np.inf], 0)
            df['roi'] = df['roi'].fillna(0)
            # ROI가 비정상적으로 높은 경우 제한 (최대 200%)
            df['roi'] = df['roi'].clip(upper=200)
        elif 'roi_calculated' in df.columns or 'roi' in df.columns:
            # 기존 ROI가 있으면 사용
            if 'roi_calculated' in df.columns:
                df['roi'] = pd.to_numeric(df['roi_calculated'], errors='coerce')
            elif 'roi' in df.columns:
                df['roi'] = pd.to_numeric(df['roi'], errors='coerce')
            df['roi'] = df['roi'].fillna(0)
        else:
            # ROI 계산 불가능
            df['roi'] = 0
        
        return df
        
    except Exception as e:
        st.error(f"ROI 메트릭 계산 오류: {str(e)}")
        return pd.DataFrame()

def analyze_optimal_hours(df, is_weekend=False):
    """최적 시간대 분석 (상위 5개) - 00~05시, 12~16시 제외"""
    try:
        if df.empty or 'hour' not in df.columns:
            return pd.DataFrame()
        
        # 00시~05시, 12시~16시 제외
        excluded_hours = list(range(0, 6)) + list(range(12, 17))
        df_filtered = df[~df['hour'].isin(excluded_hours)].copy()
        
        if df_filtered.empty:
            return pd.DataFrame()
        
        # 컬럼명 감지
        col_units_sold = get_column_name(df_filtered, 'units_sold')
        col_unit_price = get_column_name(df_filtered, 'unit_price')
        
        # 시간대별 집계
        hour_stats = []
        for hour in df_filtered['hour'].unique():
            hour_df = df_filtered[df_filtered['hour'] == hour]
            if len(hour_df) > 0:
                stats = {
                    'hour': hour,
                    'roi': calculate_trimmed_mean(hour_df['roi'].values),
                    'avg_revenue': calculate_trimmed_mean(hour_df['revenue'].values),
                    'total_revenue': hour_df['revenue'].sum(),
                    'count': len(hour_df),
                    'avg_units': calculate_trimmed_mean(hour_df[col_units_sold].values) if col_units_sold else 0,
                    'total_units': hour_df[col_units_sold].sum() if col_units_sold else 0
                }
                
                # 가장 높은 매출을 한 방송의 단가대와 가장 낮은 매출의 단가대
                if col_unit_price:
                    best_broadcast = hour_df.loc[hour_df['revenue'].idxmax()]
                    best_price = best_broadcast[col_unit_price]
                    stats['best_price_range'] = f"{int(best_price/10000)}만원대"
                    
                    # 최저매출 단가대 추가
                    worst_broadcast = hour_df.loc[hour_df['revenue'].idxmin()]
                    worst_price = worst_broadcast[col_unit_price]
                    stats['worst_price_range'] = f"{int(worst_price/10000)}만원대"
                else:
                    stats['best_price_range'] = "정보없음"
                    stats['worst_price_range'] = "정보없음"
                
                # 긍정적 ROI 비율
                positive_rate = (hour_df['roi'] > 0).mean() * 100
                stats['positive_rate'] = positive_rate
                
                # 스코어 계산
                max_revenue = df_filtered.groupby('hour')['revenue'].sum().max()
                if max_revenue > 0:
                    stats['score'] = (
                        stats['roi'] * 0.6 + 
                        (stats['total_revenue'] / max_revenue * 100) * 0.4
                    )
                else:
                    stats['score'] = stats['roi']
                
                # 시간대별 설명 추가
                hour = stats['hour']
                if hour in [10, 11]:
                    reason = "오전 골든타임"
                    detail1 = "주부층과 시니어층의 활발한 시청"
                    detail2 = "구매 결정 시간이 충분하여 높은 전환율"
                elif hour in [20, 21]:
                    reason = "저녁 프라임타임"
                    detail1 = "전 연령층의 시청률 최고치"
                    detail2 = "가족 단위 시청으로 고가 상품 구매력 상승"
                elif hour in [17, 18, 19]:
                    reason = "퇴근 후 시간대"
                    detail1 = "직장인층의 활발한 시청"
                    detail2 = "여유있는 쇼핑 시간으로 신중한 구매 결정"
                elif hour in [22]:
                    reason = "심야 시간대"
                    detail1 = "특가 상품과 한정 수량 판매 효과적"
                    detail2 = "충동구매 경향이 높은 시간"
                elif hour in [7, 8, 9]:
                    reason = "아침 시간대"
                    detail1 = "출근 전 짧은 시청이지만 집중도 높음"
                    detail2 = "건강식품과 뷰티 제품 판매 유리"
                else:
                    reason = "일반 시간대"
                    detail1 = "안정적인 시청률 유지"
                    detail2 = "다양한 상품군 판매 가능"
                
                stats['reason'] = reason
                stats['detail1'] = detail1
                stats['detail2'] = detail2
                
                hour_stats.append(stats)
        
        if not hour_stats:
            return pd.DataFrame()
        
        # DataFrame 생성
        hour_stats_df = pd.DataFrame(hour_stats)
        
        # 상위 7개 선택 - 절사평균 ROI 기준 내림차순 정렬
        hour_stats_df = hour_stats_df.sort_values('roi', ascending=False)
        top_hours = hour_stats_df.head(7).reset_index(drop=True)
        
        return top_hours
        
    except Exception as e:
        st.error(f"최적 시간대 분석 오류: {str(e)}")
        return pd.DataFrame()

def analyze_optimal_price_ranges(df):
    """최적 단가대 분석 (7-16만원, 1만원 단위)"""
    try:
        if df.empty:
            return pd.DataFrame()
        
        # 매출 0원 데이터 제외
        df = df[df['revenue'] > 0].copy()
        
        # 컬럼명 자동 감지
        col_unit_price = get_column_name(df, 'unit_price')
        col_units_sold = get_column_name(df, 'units_sold')
        
        if not col_unit_price:
            return pd.DataFrame()
        
        # 7-16만원 범위 필터링
        df = df[(df[col_unit_price] >= 70000) & (df[col_unit_price] <= 160000)].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        # 1만원 단위 가격대 구간 생성
        price_bins = list(range(70000, 170000, 10000))
        price_labels = [f'{i//10000}만원대' for i in price_bins[:-1]]
        
        df['price_range'] = pd.cut(df[col_unit_price], bins=price_bins, labels=price_labels, include_lowest=True)
        
        # 가격대별 집계
        price_stats = []
        for price_range in df['price_range'].dropna().unique():
            range_df = df[df['price_range'] == price_range]
            if len(range_df) > 0:
                stats = {
                    'price_range': str(price_range),
                    'roi': calculate_trimmed_mean(range_df['roi'].values),
                    'avg_revenue': calculate_trimmed_mean(range_df['revenue'].values),
                    'total_revenue': range_df['revenue'].sum(),
                    'avg_units': calculate_trimmed_mean(range_df[col_units_sold].values) if col_units_sold else 0,
                    'total_units': range_df[col_units_sold].sum() if col_units_sold else 0,
                    'count': len(range_df)  # 방송횟수 추가
                }
                
                # 가장 많은 매출을 한 시간대와 가장 적은 매출의 가격대
                hour_revenue = range_df.groupby('hour')['revenue'].sum()
                if not hour_revenue.empty:
                    best_hour = hour_revenue.idxmax()
                    stats['best_hour'] = f"{int(best_hour)}시"
                else:
                    stats['best_hour'] = "정보없음"
                
                # 최저매출 단가대 계산 (해당 가격대에서 성과가 낮은 서브 가격대)
                if len(range_df) > 1:
                    # 더 세분화된 가격대별 매출 분석
                    sub_price_bins = np.percentile(range_df[col_unit_price], [0, 33, 67, 100])
                    sub_labels = ['하위', '중위', '상위']
                    range_df['sub_price'] = pd.cut(range_df[col_unit_price], bins=sub_price_bins, labels=sub_labels, include_lowest=True)
                    sub_revenue = range_df.groupby('sub_price')['revenue'].mean()
                    if not sub_revenue.empty:
                        worst_sub = sub_revenue.idxmin()
                        stats['worst_price_range'] = f"{str(price_range)}-{worst_sub}"
                    else:
                        stats['worst_price_range'] = "정보없음"
                else:
                    stats['worst_price_range'] = "정보없음"
                
                # 긍정적 ROI 비율
                positive_rate = (range_df['roi'] > 0).mean() * 100
                stats['positive_rate'] = positive_rate
                
                # 스코어 계산 (ROI가 음수여도 상대적 비교 가능하도록)
                max_revenue = df.groupby('price_range')['revenue'].sum().max()
                if max_revenue > 0:
                    # ROI가 음수일 때도 처리
                    roi_score = max(0, stats['roi'] + 100) / 100  # -100을 0으로, 0을 1로 변환
                    revenue_score = stats['total_revenue'] / max_revenue
                    stats['score'] = (roi_score * 0.6 + revenue_score * 0.4) * 100
                else:
                    stats['score'] = max(0, stats['roi'])
                
                # 가격대별 설명 추가
                price_str = str(price_range)
                if '7만원대' in price_str:
                    reason = "합리적 가격대의 엔트리 포인트"
                    detail1 = "품질 대비 가격 만족도 높은 스위트 스팟"
                    detail2 = "신규 고객 유입에 유리하며 재구매율 높음"
                elif '8만원대' in price_str:
                    reason = "주력 판매 가격대로 안정적 수익 창출"
                    detail1 = "브랜드 인지도와 가격 경쟁력의 균형점"
                    detail2 = "다양한 카테고리 상품 배치 가능"
                elif '9만원대' in price_str or '10만원대' in price_str:
                    reason = "심리적 저항선 직전의 최적 가격대"
                    detail1 = "구매 결정이 빠르며 객단가 상승 효과"
                    detail2 = "번들 상품이나 세트 구성에 유리"
                elif '11만원대' in price_str or '12만원대' in price_str or '13만원대' in price_str:
                    reason = "중가 프리미엄 전략 구간"
                    detail1 = "품질 중시 고객층 타겟팅 효과적"
                    detail2 = "브랜드 가치 제고 및 마진율 개선"
                elif '14만원대' in price_str or '15만원대' in price_str or '16만원대' in price_str:
                    reason = "프리미엄 가격대로 높은 마진율 확보"
                    detail1 = "충성 고객 중심 판매로 안정적 수익"
                    detail2 = "차별화된 상품 포지셔닝 가능"
                else:
                    reason = "프리미엄 가격대"
                    detail1 = "고가치 상품 판매 전략"
                    detail2 = "타겟 고객층 특화 마케팅"
                
                stats['reason'] = reason
                stats['detail1'] = detail1
                stats['detail2'] = detail2
                
                price_stats.append(stats)
        
        if not price_stats:
            return pd.DataFrame()
        
        # DataFrame 생성
        price_stats_df = pd.DataFrame(price_stats)
        
        # 상위 7개 가격대 - score 기준 내림차순 정렬
        top_prices = price_stats_df.nlargest(7, 'score').reset_index(drop=True)
        
        return top_prices
        
    except Exception as e:
        st.error(f"최적 가격대 분석 오류: {str(e)}")
        return pd.DataFrame()

def analyze_weekday_optimization(df):
    """요일별 최적 시간대 분석 (ROI와 평균 매출, 판매량 포함)"""
    try:
        if df.empty:
            return {}
        
        weekday_map = {
            '월요일': '월', '화요일': '화', '수요일': '수',
            '목요일': '목', '금요일': '금', '토요일': '토', '일요일': '일'
        }
        
        # 00시~05시, 12시~16시 제외
        excluded_hours = list(range(0, 6)) + list(range(12, 17))
        df = df[~df['hour'].isin(excluded_hours)].copy()
        
        if df.empty:
            return {}
        
        # 컬럼명 감지
        col_units_sold = get_column_name(df, 'units_sold')
        
        result = {}
        
        # 평일만 분석 (주말 데이터 제외)
        weekdays = ['월요일', '화요일', '수요일', '목요일', '금요일']
        df_weekday = df[df['weekday'].isin(weekdays)]
        
        if df_weekday.empty:
            return {}
        
        for weekday in weekdays:
            weekday_df = df_weekday[df_weekday['weekday'] == weekday].copy()
            
            if not weekday_df.empty and 'hour' in weekday_df.columns:
                # 시간대별 집계 (절사평균 적용)
                hour_data = []
                for hour in weekday_df['hour'].unique():
                    hour_df = weekday_df[weekday_df['hour'] == hour]
                    
                    # 판매량 데이터 계산
                    if col_units_sold and col_units_sold in hour_df.columns:
                        avg_units = hour_df[col_units_sold].mean()  # 평균 판매량
                        trimmed_avg_units = calculate_trimmed_mean(hour_df[col_units_sold].values)  # 절사평균 판매량
                    else:
                        avg_units = 0
                        trimmed_avg_units = 0
                    
                    hour_data.append({
                        'hour': hour,
                        'roi': calculate_trimmed_mean(hour_df['roi'].values),
                        'revenue': calculate_trimmed_mean(hour_df['revenue'].values),
                        'count': len(hour_df),  # 방송횟수 추가
                        'avg_units': avg_units,  # 평균 판매량
                        'trimmed_avg_units': trimmed_avg_units  # 절사평균 판매량
                    })
                
                hour_stats = pd.DataFrame(hour_data)
                
                # 상위 5개 선택 - ROI가 음수여도 제대로 정렬되도록 수정
                if len(hour_stats) > 0:
                    # ROI를 기준으로 내림차순 정렬 (음수 값도 고려)
                    hour_stats_sorted = hour_stats.sort_values('roi', ascending=False)
                    top_hours = hour_stats_sorted.head(min(5, len(hour_stats_sorted)))
                    
                    result[weekday_map[weekday]] = [
                        {
                            'hour': int(row['hour']), 
                            'roi': row['roi'],
                            'avg_revenue': row['revenue'],
                            'count': row['count'],  # 방송횟수 포함
                            'avg_units': row['avg_units'],  # 평균 판매량
                            'trimmed_avg_units': row['trimmed_avg_units']  # 절사평균 판매량
                        } 
                        for _, row in top_hours.iterrows()
                    ]
        
        return result
        
    except Exception as e:
        st.error(f"요일별 최적화 분석 오류: {str(e)}")
        return {}

def analyze_challenge_and_avoid_hours(df, is_weekend=False):
    """도전 가능 시간대 및 회피 시간대 분석 (각 3개씩)"""
    try:
        if df.empty or 'hour' not in df.columns:
            return [], []
        
        # 컬럼명 감지
        col_units_sold = get_column_name(df, 'units_sold')
        col_unit_price = get_column_name(df, 'unit_price')
        
        # 제외할 시간대 설정 (선택하면 안되는 시간)
        if is_weekend:
            # 주말: 00시~05시만 제외
            exclude_hours = list(range(0, 6))
        else:
            # 평일: 00시~05시, 12시~16시 제외
            exclude_hours = list(range(0, 6)) + list(range(12, 17))
        
        # 제외 시간대를 필터링
        df_filtered = df[~df['hour'].isin(exclude_hours)]
        
        if df_filtered.empty:
            return [], []
        
        # 시간대별 ROI 계산 (절사평균 적용)
        hour_stats = []
        for hour in df_filtered['hour'].unique():
            hour_df = df_filtered[df_filtered['hour'] == hour]
            if len(hour_df) >= 2:  # 최소 2개 이상의 데이터
                stats = {
                    'hour': hour,
                    'roi': calculate_trimmed_mean(hour_df['roi'].values),
                    'avg_revenue': calculate_trimmed_mean(hour_df['revenue'].values),
                    'count': len(hour_df),
                    'avg_units': calculate_trimmed_mean(hour_df[col_units_sold].values) if col_units_sold else 0
                }
                hour_stats.append(stats)
        
        if not hour_stats:
            return [], []
        
        hour_stats = pd.DataFrame(hour_stats)
        
        # 도전 가능 시간대: ROI가 -20 ~ 10 사이인 시간대 중 상위 3개
        challenge_hours = hour_stats[(hour_stats['roi'] >= -30) & (hour_stats['roi'] <= 10)]
        if len(challenge_hours) < 3:
            # 부족하면 ROI가 낮지만 개선 가능성 있는 시간대 추가
            challenge_hours = hour_stats[hour_stats['roi'] < 20]
        challenge_hours = challenge_hours.nlargest(min(3, len(challenge_hours)), 'roi')
        
        challenge_list = []
        for _, row in challenge_hours.iterrows():
            hour = int(row['hour'])
            roi = row['roi']
            
            # 가장 매출이 높은/낮은 판매가 찾기
            hour_df = df_filtered[df_filtered['hour'] == hour]
            if col_unit_price and not hour_df.empty:
                # 최고 매출 단가
                best_broadcast = hour_df.loc[hour_df['revenue'].idxmax()]
                best_price = best_broadcast[col_unit_price]
                best_price_str = f"{int(best_price/10000)}만원대"
                
                # 최저 매출 단가
                worst_broadcast = hour_df.loc[hour_df['revenue'].idxmin()]
                worst_price = worst_broadcast[col_unit_price]
                worst_price_str = f"{int(worst_price/10000)}만원대"
            else:
                best_price_str = "정보없음"
                worst_price_str = "정보없음"
            
            if hour in [7, 8]:
                reason = "이른 아침 시간대지만 출근 준비 시청층 존재"
                detail1 = "모바일 최적화와 간편결제 강화로 전환율 개선 가능"
                detail2 = "건강식품과 뷰티 제품 집중 배치로 구매율 상승"
                detail3 = "타겟팅 광고와 앱 푸시 알림 활용 권장"
            elif hour in [9]:
                reason = "출근 시간대 막바지로 짧은 시청이지만 구매력 있음"
                detail1 = "타겟팅 정확도를 높이면 ROI 개선 여지 충분"
                detail2 = "간편 조리 식품과 생활용품 중심 편성"
                detail3 = "모바일 전용 할인 쿠폰 제공으로 구매 유도"
            elif hour in [17, 18]:
                reason = "퇴근 초반 이동 중 시청으로 접근성 개선 필요"
                detail1 = "모바일 전용 프로모션과 앱 푸시 알림 활용 권장"
                detail2 = "저녁 준비 관련 상품과 간편식 중심 배치"
                detail3 = "실시간 라이브 특가로 즉시 구매 유도"
            elif hour in [19]:
                reason = "저녁 준비 시간대로 바쁘지만 습관적 시청층 존재"
                detail1 = "조리기구나 식품류 카테고리 집중 배치로 효과 극대화"
                detail2 = "패밀리 세트 상품으로 객단가 상승 유도"
                detail3 = "요일별 테마 운영으로 고정 시청층 확보"
            elif hour in [22]:
                reason = "심야 전환 시간대로 특정 타겟층 공략 가능"
                detail1 = "1인 가구 맞춤 상품과 특가 프로모션 효과적"
                detail2 = "인기 상품 재방송으로 놓친 고객 흡수"
                detail3 = "다음날 배송 보장으로 구매 결정 촉진"
            elif hour in [6]:
                reason = "새벽 시간대지만 일찍 일어나는 시니어층 존재"
                detail1 = "건강식품과 실버용품 집중 배치로 매출 가능"
                detail2 = "전화 주문 강화와 상담원 배치 필요"
                detail3 = "반복 구매 유도 프로그램 운영"
            elif hour in [10, 11]:
                reason = "오전 시간대로 주부층 시청이 많지만 경쟁 치열"
                detail1 = "차별화된 상품 구성과 독점 상품 필요"
                detail2 = "실시간 시청자 참여 이벤트로 관심 유도"
                detail3 = "멤버십 혜택 강화로 충성 고객 확보"
            else:
                reason = "개선 가능성이 있는 시간대"
                detail1 = "상품 구성과 프로모션 전략 재검토 필요"
                detail2 = "경쟁사 분석을 통한 차별화 전략 수립"
                detail3 = "고객 피드백 반영한 맞춤형 편성"
            
            challenge_list.append({
                'hour': hour, 
                'roi': roi,
                'avg_revenue': row['avg_revenue'],
                'avg_units': row.get('avg_units', 0),
                'best_price': best_price_str,
                'worst_price': worst_price_str,
                'reason': reason,
                'detail1': detail1,
                'detail2': detail2,
                'detail3': detail3
            })
        
        # 절대 피해야 할 시간대: ROI 하위 시간대 (23시 제외, 제외 시간대도 제외)
        avoid_exclude = exclude_hours + [23]  # 23시도 제외
        df_avoid = df[~df['hour'].isin(avoid_exclude)]
        
        if not df_avoid.empty:
            # 절사평균 적용
            hour_stats_avoid = []
            for hour in df_avoid['hour'].unique():
                hour_df = df_avoid[df_avoid['hour'] == hour]
                if len(hour_df) >= 2:  # 최소 2개 이상의 데이터
                    stats = {
                        'hour': hour,
                        'roi': calculate_trimmed_mean(hour_df['roi'].values),
                        'avg_revenue': calculate_trimmed_mean(hour_df['revenue'].values),
                        'count': len(hour_df),
                        'avg_units': calculate_trimmed_mean(hour_df[col_units_sold].values) if col_units_sold else 0
                    }
                    hour_stats_avoid.append(stats)
            
            if hour_stats_avoid:
                hour_stats_avoid = pd.DataFrame(hour_stats_avoid)
                avoid_hours = hour_stats_avoid.nsmallest(min(3, len(hour_stats_avoid)), 'roi')
            else:
                avoid_hours = pd.DataFrame()
            
            avoid_list = []
            for _, row in avoid_hours.iterrows():
                hour = int(row['hour'])
                roi = row['roi']
                
                # 가장 매출이 높은/낮은 판매가 찾기
                hour_df = df_avoid[df_avoid['hour'] == hour]
                if col_unit_price and not hour_df.empty:
                    # 최고 매출 단가
                    best_broadcast = hour_df.loc[hour_df['revenue'].idxmax()]
                    best_price = best_broadcast[col_unit_price]
                    best_price_str = f"{int(best_price/10000)}만원대"
                    
                    # 최저 매출 단가
                    worst_broadcast = hour_df.loc[hour_df['revenue'].idxmin()]
                    worst_price = worst_broadcast[col_unit_price]
                    worst_price_str = f"{int(worst_price/10000)}만원대"
                else:
                    best_price_str = "정보없음"
                    worst_price_str = "정보없음"
                
                if hour in [17]:
                    reason = "퇴근 시작 시간으로 시청 불안정"
                    detail1 = "이동 중 시청으로 구매 결정 어려움"
                    detail2 = "경쟁 채널과의 시청률 경쟁 심화"
                    detail3 = "광고 비용 대비 효율성 최저"
                elif hour in [6]:
                    reason = "이른 아침 시간대로 시청률 저조"
                    detail1 = "구매 전환 극히 낮아 방송 비용 대비 효율성 없음"
                    detail2 = "제한적인 시청층으로 상품 다양성 부족"
                    detail3 = "물류 준비 시간 부족으로 당일 배송 불가"
                else:
                    reason = "비효율 시간대"
                    detail1 = "ROI 지속 마이너스로 즉시 개편 필요"
                    detail2 = "시청률과 구매율 모두 최하위"
                    detail3 = "운영 비용 절감을 위한 편성 축소 권장"
                
                avoid_list.append({
                    'hour': hour,
                    'roi': roi,
                    'avg_revenue': row['avg_revenue'],
                    'avg_units': row.get('avg_units', 0),
                    'best_price': best_price_str,
                    'worst_price': worst_price_str,
                    'reason': reason,
                    'detail1': detail1,
                    'detail2': detail2,
                    'detail3': detail3
                })
        else:
            avoid_list = []
        
        return challenge_list[:3], avoid_list[:3]
        
    except Exception as e:
        st.error(f"도전/회피 시간대 분석 오류: {str(e)}")
        return [], []

def generate_html_report_advanced(analysis_df, report_data, channel, date_str, 
                                  top_hours, top_prices, weekday_opt, 
                                  challenge_hours, avoid_hours):
    """고급 HTML 리포트 생성 - 현재 화면과 동일한 디자인"""
    
    # Plotly 차트를 HTML로 변환
    hours_chart_html = ""
    prices_chart_html = ""
    
    if not top_hours.empty:
        fig_hours = go.Figure()
        
        # 그라데이션 색상 설정
        colors_gradient = []
        for roi in top_hours['roi']:
            if roi > 30:
                colors_gradient.append('#10B981')  # 녹색
            elif roi > 10:
                colors_gradient.append('#3B82F6')  # 파란색
            elif roi > 0:
                colors_gradient.append('#60A5FA')  # 연한 파란색
            elif roi > -10:
                colors_gradient.append('#FBBF24')  # 노란색
            else:
                colors_gradient.append('#EF4444')  # 빨간색
        
        fig_hours.add_trace(go.Bar(
            x=[f"{int(h)}시" for h in top_hours['hour']],
            y=top_hours['roi'],
            text=[f"<b>{roi:.1f}%</b>" for roi in top_hours['roi']],
            textposition='outside',
            marker=dict(
                color=colors_gradient,
                line=dict(color='rgba(0,0,0,0.1)', width=1)
            ),
            hovertemplate="<b>%{x}</b><br>절사평균 ROI: %{y:.1f}%<br>절사평균 매출: %{customdata:.2f}억<extra></extra>",
            customdata=top_hours['avg_revenue']
        ))
        
        fig_hours.update_layout(
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(250,250,250,1)',
            xaxis=dict(
                title=dict(text="시간대", font=dict(size=14, color='#2d3748')),
                tickfont=dict(size=12, color='#2d3748'),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title=dict(text='ROI (%)', font=dict(size=14, color='#2d3748')),
                tickfont=dict(size=12, color='#2d3748'),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            showlegend=False,
            margin=dict(l=60, r=20, t=40, b=60)
        )
        hours_chart_html = pio.to_html(fig_hours, include_plotlyjs='cdn', div_id="hours_chart")
    
    if not top_prices.empty:
        fig_prices = go.Figure()
        
        # 점수에 따른 그라데이션 색상
        colors_price = []
        for score in top_prices['score']:
            if score > 80:
                colors_price.append('#10B981')
            elif score > 60:
                colors_price.append('#3B82F6')
            elif score > 40:
                colors_price.append('#60A5FA')
            elif score > 20:
                colors_price.append('#FBBF24')
            else:
                colors_price.append('#F87171')
        
        fig_prices.add_trace(go.Bar(
            x=top_prices['price_range'].astype(str),
            y=top_prices['score'],
            text=[f"<b>{score:.1f}</b>" for score in top_prices['score']],
            textposition='outside',
            marker=dict(
                color=colors_price,
                line=dict(color='rgba(0,0,0,0.1)', width=1)
            ),
            hovertemplate="<b>%{x}</b><br>종합 점수: %{y:.1f}<extra></extra>"
        ))
        
        fig_prices.update_layout(
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(250,250,250,1)',
            xaxis=dict(
                title=dict(text="가격대", font=dict(size=14, color='#2d3748')),
                tickangle=-45,
                tickfont=dict(size=12, color='#2d3748'),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title=dict(text='종합 점수', font=dict(size=14, color='#2d3748')),
                tickfont=dict(size=12, color='#2d3748'),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            showlegend=False,
            margin=dict(l=60, r=20, t=40, b=80)
        )
        prices_chart_html = pio.to_html(fig_prices, include_plotlyjs='', div_id="prices_chart")
    
    # 요일별 최적 시간대 HTML
    weekday_html = ""
    colors = {'월': '#EF4444', '화': '#F59E0B', '수': '#10B981', '목': '#3B82F6', '금': '#8B5CF6'}
    for day in ['월', '화', '수', '목', '금']:
        day_data = ""
        if day in weekday_opt and weekday_opt[day]:
            for rank, hour_data in enumerate(weekday_opt[day][:3], 1):
                roi_color = "#34D399" if hour_data['roi'] > 0 else "#EF4444"
                day_data += f"""
                <div class="weekday-item">
                    <strong style="font-size: 16px; color: #1e293b;">{rank}위: {hour_data['hour']}시</strong><br>
                    <span style="font-size: 14px; color: #334155;">
                        절사평균 ROI: <span style="color: {roi_color}; font-weight: bold;">{hour_data['roi']:.1f}%</span><br>
                        절사평균 매출: <span style="color: #3B82F6; font-weight: bold;">{hour_data['avg_revenue']:.2f}억</span>
                    </span>
                </div>
                """
        else:
            day_data = '<div class="weekday-item">데이터 없음</div>'
        
        weekday_html += f"""
        <div class="weekday-box" style="border-color: {colors.get(day, '#666')};">
            <h4 style="color: {colors.get(day, '#666')};">{day}요일</h4>
            {day_data}
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>홈쇼핑 전략 분석 리포트 - {channel}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');
            body {{
                font-family: 'Noto Sans KR', sans-serif;
                background: linear-gradient(135deg, #ffffff 0%, #f7fafc 100%);
                color: #1a202c;
                margin: 0;
                padding: 20px;
                font-weight: 500;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                text-align: center;
                color: white;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            }}
            h1 {{
                font-size: 2.8rem;
                margin: 0 0 10px 0;
                color: white;
                font-weight: 900;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            .subtitle {{
                font-size: 1.2rem;
                opacity: 1;
                color: white;
                font-weight: 600;
            }}
            .metric-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .metric-card {{
                background: white;
                padding: 25px;
                border-radius: 16px;
                text-align: center;
                border: 2px solid;
                box-shadow: 0 6px 20px rgba(0,0,0,0.12);
            }}
            .metric-card:nth-child(1) {{ border-color: #60A5FA; }}
            .metric-card:nth-child(2) {{ border-color: #34D399; }}
            .metric-card:nth-child(3) {{ border-color: #FBBF24; }}
            .metric-card:nth-child(4) {{ border-color: #F87171; }}
            .metric-card:nth-child(5) {{ border-color: #A78BFA; }}
            .metric-value {{
                font-size: 2.5rem;
                font-weight: 900;
                margin: 10px 0;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
            .metric-label {{
                font-size: 1rem;
                color: #475569;
                margin-bottom: 5px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            .analysis-card {{
                background: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 25px;
                border: 2px solid #e5e7eb;
                box-shadow: 0 6px 20px rgba(0,0,0,0.1);
            }}
            .chart-container {{
                background: #ffffff;
                padding: 25px;
                border-radius: 12px;
                margin: 20px 0;
                border: 1px solid #e5e7eb;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }}
            .detail-box {{
                padding: 18px;
                background: linear-gradient(135deg, #f0f7ff 0%, #e6f2ff 100%);
                border-left: 5px solid #667eea;
                border-radius: 8px;
                margin-bottom: 15px;
                color: #1e293b;
                font-weight: 600;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
            }}
            .weekday-container {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .weekday-box {{
                background: white;
                padding: 15px;
                border-radius: 12px;
                border: 2px solid;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                min-height: 180px;
            }}
            .weekday-item {{
                padding: 8px;
                margin: 5px 0;
                background: #f1f5f9;
                border-radius: 6px;
                font-size: 13px;
                color: #1e293b;
                font-weight: 600;
                line-height: 1.5;
            }}
            .challenge-box {{
                background: #fffbeb;
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #fbbf24;
                margin-bottom: 15px;
                color: #78350f;
                font-weight: 500;
            }}
            .avoid-box {{
                background: #fef2f2;
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #f87171;
                margin-bottom: 15px;
                color: #7f1d1d;
                font-weight: 500;
            }}
            .strategy-card {{
                background: #faf5ff;
                padding: 20px;
                border-radius: 12px;
                border: 1px solid #a78bfa;
                margin-bottom: 15px;
                color: #4c1d95;
                font-weight: 500;
            }}
            h2 {{
                color: #0f172a;
                font-weight: 800;
                font-size: 1.8rem;
            }}
            h3 {{
                color: #1e293b;
                font-weight: 700;
                font-size: 1.4rem;
            }}
            h4 {{
                color: #334155;
                font-weight: 700;
                font-size: 1.2rem;
            }}
            .analysis-card h3 {{
                color: #1e293b;
                font-weight: 700;
            }}
            .two-column {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            @media (max-width: 768px) {{
                .two-column {{
                    grid-template-columns: 1fr;
                }}
                .weekday-container {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 홈쇼핑 전략 분석 리포트</h1>
                <div class="subtitle">
                    <strong>방송사:</strong> {channel} | <strong>분석 기간:</strong> {date_str}<br>
                    <strong>생성일시:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
            
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">총 방송 횟수</div>
                    <div class="metric-value" style="color: #60A5FA;">{report_data.get('total_count', 0):,}건</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">총 매출</div>
                    <div class="metric-value" style="color: #34D399;">{report_data.get('total_revenue', 0):.1f}억</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">평균 매출</div>
                    <div class="metric-value" style="color: #FBBF24;">{report_data.get('avg_revenue', 0):.2f}억</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">평균 ROI</div>
                    <div class="metric-value" style="color: {'#34D399' if report_data.get('avg_roi', 0) > 0 else '#EF4444'};">
                        {report_data.get('avg_roi', 0):.1f}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">최적 시간</div>
                    <div class="metric-value" style="color: #A78BFA;">
                        {report_data.get('best_hour', {}).get('hour', 0)}시
                    </div>
                </div>
            </div>
            
            <div class="two-column">
                <div class="analysis-card">
                    <h2>⏰ 최적 판매 시간대 TOP 5</h2>
                    <div class="chart-container">
                        {hours_chart_html}
                    </div>
                    {''.join([f'''
                    <div class="detail-box">
                        <strong style="color: #667eea; font-size: 16px;">{int(row['hour'])}시</strong>
                        <span style="float: right; color: #34D399;">ROI: {row['roi']:.1f}%</span><br>
                        <div style="color: #94A3B8; font-size: 14px; margin: 5px 0;">
                            📊 평균매출: {row['avg_revenue']:.2f}억 | 평균 판매수량: {row.get('avg_units', 0):.0f}개<br>
                            💰 최고매출 단가대: {row.get('best_price_range', '정보없음')}
                        </div>
                        <div style="color: #CBD5E1; font-size: 13px;">
                            💡 {row.get('reason', '')}<br>
                            📌 {row.get('detail1', '')}
                        </div>
                    </div>
                    ''' for _, row in top_hours.iterrows()]) if not top_hours.empty else '<p>데이터가 충분하지 않습니다.</p>'}
                </div>
                
                <div class="analysis-card">
                    <h2>💰 최적 단가대 TOP 5</h2>
                    <div class="chart-container">
                        {prices_chart_html}
                    </div>
                    {''.join([f'''
                    <div class="detail-box" style="border-color: #10B981;">
                        <strong style="color: #10B981; font-size: 16px;">{row['price_range']}</strong>
                        <span style="float: right; color: #60A5FA;">ROI: {row['roi']:.1f}%</span><br>
                        <div style="color: #94A3B8; font-size: 14px; margin: 5px 0;">
                            💰 총매출: {row['total_revenue']:.1f}억 | 평균 판매수량: {row.get('avg_units', 0):.0f}개<br>
                            ⏰ 최고매출 시간대: {row.get('best_hour', '정보없음')}
                        </div>
                        <div style="color: #CBD5E1; font-size: 13px;">
                            💡 {row.get('reason', '')}<br>
                            📌 {row.get('detail1', '')}
                        </div>
                    </div>
                    ''' for _, row in top_prices.iterrows()]) if not top_prices.empty else '<p>데이터가 충분하지 않습니다.</p>'}
                </div>
            </div>
            
            <div class="analysis-card">
                <h2>📅 요일별 최적 시간대 TOP 3</h2>
                <div class="weekday-container">
                    {weekday_html}
                </div>
            </div>
            
            <div class="two-column">
                <div class="analysis-card">
                    <h2>⚡ 도전해볼 만한 시간대 (TOP 3)</h2>
                    {''.join([f'''
                    <div class="challenge-box">
                        <h3 style="color: #92400E; font-size: 20px;">{hour_data['hour']}시</h3>
                        <div style="color: #78350F; margin-bottom: 10px; font-size: 15px; font-weight: 600;">
                            절사평균 ROI: {hour_data['roi']:.1f}% | 절사평균 매출: {hour_data['avg_revenue']:.2f}억<br>
                            평균 판매수량: {hour_data.get('avg_units', 0):.0f}개 | 최저매출 단가: {hour_data.get('worst_price', '정보없음')}
                        </div>
                        <div style="color: #451A03; font-size: 15px; line-height: 1.8; font-weight: 500;">
                            📍 {hour_data['reason']}<br>
                            💡 {hour_data.get('detail1', '')}<br>
                            🎯 {hour_data.get('detail2', '')}<br>
                            ⚡ {hour_data.get('detail3', '')}
                        </div>
                    </div>
                    ''' for hour_data in challenge_hours]) if challenge_hours else '<p>분석할 데이터가 충분하지 않습니다.</p>'}
                </div>
                
                <div class="analysis-card">
                    <h2>⚠️ 절대 피해야 할 시간대 (TOP 3)</h2>
                    {''.join([f'''
                    <div class="avoid-box">
                        <h3 style="color: #7F1D1D; font-size: 20px;">{hour_data['hour']}시</h3>
                        <div style="color: #991B1B; margin-bottom: 10px; font-size: 15px; font-weight: 600;">
                            절사평균 ROI: {hour_data['roi']:.1f}% | 절사평균 매출: {hour_data['avg_revenue']:.2f}억<br>
                            평균 판매수량: {hour_data.get('avg_units', 0):.0f}개 | 최저매출 단가: {hour_data.get('worst_price', '정보없음')}
                        </div>
                        <div style="color: #450A0A; font-size: 15px; line-height: 1.8; font-weight: 500;">
                            📍 {hour_data['reason']}<br>
                            ⚠️ {hour_data.get('detail1', '')}<br>
                            ❌ {hour_data.get('detail2', '')}<br>
                            🚫 {hour_data.get('detail3', '')}
                        </div>
                    </div>
                    ''' for hour_data in avoid_hours]) if avoid_hours else '<p>분석할 데이터가 충분하지 않습니다.</p>'}
                </div>
            </div>
            
            <div class="analysis-card">
                <h2>✨ 전략적 제언</h2>
                <div class="two-column">
                    <div class="strategy-card">
                        <h3 style="color: #8B5CF6;">⏰ 시간대 최적화</h3>
                        <p>오전 {top_hours.iloc[0]['hour'] if not top_hours.empty else 10}시와 저녁 {top_hours.iloc[1]['hour'] if len(top_hours) > 1 else 20}시에 주력 상품 배치</p>
                        <ul style="color: #CBD5E1; font-size: 14px;">
                            <li>피크 시간대 집중 운영으로 효율성 극대화</li>
                            <li>타겟 고객층의 시청 패턴에 최적화된 편성</li>
                        </ul>
                    </div>
                    
                    <div class="strategy-card">
                        <h3 style="color: #8B5CF6;">💰 가격 전략</h3>
                        <p>{top_prices.iloc[0]['price_range'] if not top_prices.empty else '9만원대'} 중심의 가격 구성</p>
                        <ul style="color: #CBD5E1; font-size: 14px;">
                            <li>심리적 가격대를 활용한 구매 전환율 향상</li>
                            <li>가격 경쟁력과 수익성의 균형점 확보</li>
                        </ul>
                    </div>
                    
                    <div class="strategy-card">
                        <h3 style="color: #8B5CF6;">📅 요일별 차별화</h3>
                        <p>화요일과 금요일 특별 프로모션 강화</p>
                        <ul style="color: #CBD5E1; font-size: 14px;">
                            <li>요일별 고객 특성을 반영한 맞춤 전략</li>
                            <li>주중/주말 구매 패턴 차이를 활용한 운영</li>
                        </ul>
                    </div>
                    
                    <div class="strategy-card">
                        <h3 style="color: #8B5CF6;">🎯 리스크 관리</h3>
                        <p>새벽 시간대와 낮 12-16시 방송 최소화</p>
                        <ul style="color: #CBD5E1; font-size: 14px;">
                            <li>비효율 시간대 회피로 손실 최소화</li>
                            <li>투자 대비 수익률 개선을 통한 전체 ROI 상승</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding: 20px; border-top: 2px solid rgba(255,255,255,0.1);">
                <p style="color: #94A3B8;">
                    <strong>ROI 계산 기준:</strong> 실질 마진율 57.75% (전환율 75%, 원가율 13%, 수수료율 10%)<br>
                    <strong>분석 방법:</strong> 가중평균 ROI = (총 실질이익 / 총 비용) × 100<br>
                    <strong>© 2024 홈쇼핑 데이터 분석 시스템</strong> | Powered by Streamlit
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def create_strategy_analysis_tab(df_filtered, df_with_cost, chart_generator):
    """전략 분석 탭 생성 - 완벽 수정 버전"""
    
    # CSS 스타일 개선 - 버튼 위치 조정 및 디자인 개선
    st.markdown("""
    <style>
    .strategy-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        color: white;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    .filter-container {
        background: rgba(255, 255, 255, 0.08);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
    }
    .metric-card {
        background: linear-gradient(145deg, #1e293b 0%, #334155 100%);
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        border: 2px solid;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, currentColor, transparent);
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.4);
    }
    .metric-card:nth-child(1) { border-color: #60A5FA; }
    .metric-card:nth-child(1)::before { background: linear-gradient(90deg, transparent, #60A5FA, transparent); }
    .metric-card:nth-child(2) { border-color: #34D399; }
    .metric-card:nth-child(2)::before { background: linear-gradient(90deg, transparent, #34D399, transparent); }
    .metric-card:nth-child(3) { border-color: #FBBF24; }
    .metric-card:nth-child(3)::before { background: linear-gradient(90deg, transparent, #FBBF24, transparent); }
    .metric-card:nth-child(4) { border-color: #F87171; }
    .metric-card:nth-child(4)::before { background: linear-gradient(90deg, transparent, #F87171, transparent); }
    .metric-card:nth-child(5) { border-color: #A78BFA; }
    .metric-card:nth-child(5)::before { background: linear-gradient(90deg, transparent, #A78BFA, transparent); }
    .metric-card h4 { 
        margin-bottom: 12px; 
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.9;
    }
    .metric-card h2 {
        margin: 0;
        font-size: 32px;
        font-weight: 800;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .analysis-card {
        background: rgba(255, 255, 255, 0.08);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .challenge-box {
        background: linear-gradient(135deg, rgba(251,191,36,0.15) 0%, rgba(245,158,11,0.1) 100%);
        padding: 20px;
        border-radius: 12px;
        border: 2px solid rgba(251,191,36,0.4);
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(251,191,36,0.15);
    }
    .avoid-box {
        background: linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(220,38,38,0.1) 100%);
        padding: 20px;
        border-radius: 12px;
        border: 2px solid rgba(239,68,68,0.4);
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(239,68,68,0.15);
    }
    .strategy-card {
        background: linear-gradient(135deg, rgba(139,92,246,0.1) 0%, rgba(124,58,237,0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(139,92,246,0.3);
        height: 100%;
        transition: transform 0.2s;
    }
    .strategy-card:hover {
        transform: translateY(-2px);
    }
    /* 달력 선택기 스타일 - 다크 테마 최적화 */
    .stDateInput > div > div {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid #667eea !important;
        border-radius: 8px !important;
    }
    .stDateInput input {
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #1e293b !important;
        font-weight: 600 !important;
        border: none !important;
    }
    .stDateInput label {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    /* 달력 팝업 스타일 */
    div[data-baseweb="calendar"] {
        background-color: #ffffff !important;
    }
    div[data-baseweb="calendar"] * {
        color: #1e293b !important;
    }
    div[role="gridcell"] button {
        color: #1e293b !important;
        background-color: transparent !important;
    }
    div[role="gridcell"] button:hover {
        background-color: #667eea !important;
        color: white !important;
    }
    div[data-baseweb="calendar"] div[role="presentation"] {
        color: #64748b !important;
    }
    /* 버튼 위치 조정을 위한 스타일 */
    div[data-testid="column"]:nth-of-type(5) {
        display: flex;
        align-items: flex-end;
        padding-bottom: 0px;
    }
    div[data-testid="column"]:nth-of-type(5) .stButton {
        margin-bottom: 0;
    }
    div[data-testid="column"]:nth-of-type(5) .stButton > button {
        background: linear-gradient(135deg, #FF6B6B 0%, #667eea 50%, #764ba2 100%) !important;
        color: white !important;
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 8px 20px !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.5) !important;
        width: 100% !important;
        min-height: 38px !important;
        transition: all 0.3s !important;
    }
    div[data-testid="column"]:nth-of-type(5) .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 50%, #FF6B6B 100%) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.7) !important;
        transform: scale(1.02) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="strategy-header">
            <h1 style="font-size: 2.5rem; margin-bottom: 10px;">📊 전략 분석</h1>
            <p style="font-size: 1.1rem; opacity: 0.95;">ROI 기반 최적 판매 전략 분석 시스템</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 필터 섹션 전에 데이터 확인
    has_data = len(df_filtered) > 0
    
    if not has_data:
        st.error("⚠️ 데이터가 로드되지 않았습니다. 다른 탭에서 먼저 데이터를 확인해주세요.")
        return
    
    # 필터 섹션
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    
    # 필터 안내
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255,107,107,0.1) 0%, rgba(102,126,234,0.1) 100%); 
                    padding: 12px 20px; border-radius: 10px; border-left: 4px solid #667eea; margin-bottom: 20px;">
            <span style="color: #667eea; font-weight: bold; font-size: 16px;">
                📌 필터를 설정한 후, 오른쪽의 <span style="background: linear-gradient(135deg, #FF6B6B 0%, #667eea 100%); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: bold;">
                🔍 전략분석 시작</span> 버튼을 클릭하세요
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1.5])
    
    # 컬럼명 자동 감지
    col_platform = get_column_name(df_filtered, 'platform')
    col_date = get_column_name(df_filtered, 'date')
    col_category = get_column_name(df_filtered, 'category')
    
    with col1:
        # 방송사 선택 - NS홈쇼핑을 기본값으로
        if col_platform:
            platforms = sorted(df_filtered[col_platform].unique().tolist())
            channels = ['전체'] + platforms
            
            # NS홈쇼핑이 있으면 선택, 없으면 첫 번째 방송사 선택
            if 'NS홈쇼핑' in channels:
                default_idx = channels.index('NS홈쇼핑')
            elif len(platforms) > 0:
                default_idx = 1  # 첫 번째 방송사
            else:
                default_idx = 0  # 전체
                
            selected_channel = st.selectbox(
                "📺 방송사 선택",
                channels,
                index=default_idx,
                key='strategy_channel'
            )
        else:
            selected_channel = '전체'
            st.warning("방송사 정보가 없습니다.")
    
    with col2:
        # 날짜 범위 - 8월 1일부터 오늘까지
        if col_date:
            try:
                df_dates = pd.to_datetime(df_filtered[col_date], errors='coerce')
                df_dates = df_dates[df_dates.notna()]
                
                if len(df_dates) > 0:
                    data_min_date = df_dates.min().date()
                    data_max_date = df_dates.max().date()
                    
                    # 8월 1일 또는 데이터 시작일 중 더 늦은 날짜
                    current_year = datetime.now().year
                    aug_first = datetime(current_year, 8, 1).date()
                    default_start = max(data_min_date, aug_first)
                    default_end = min(data_max_date, datetime.now().date())
                else:
                    default_end = datetime.now().date()
                    default_start = datetime(datetime.now().year, 8, 1).date()
            except:
                default_end = datetime.now().date()
                default_start = datetime(datetime.now().year, 8, 1).date()
        else:
            default_end = datetime.now().date()
            default_start = datetime(datetime.now().year, 8, 1).date()
        
        date_range = st.date_input(
            "📅 기간 선택",
            value=[default_start, default_end],
            key='strategy_date',
            min_value=data_min_date if 'data_min_date' in locals() else None,
            max_value=data_max_date if 'data_max_date' in locals() else None
        )
    
    with col3:
        # 카테고리 선택 - 전체 기본값
        if col_category:
            categories = df_filtered[col_category].dropna().unique().tolist()
            if categories:
                categories = ['전체'] + sorted(categories)
                selected_category = st.selectbox(
                    "📦 카테고리",
                    categories,
                    index=0,  # 전체
                    key='strategy_category'
                )
            else:
                selected_category = '전체'
                st.info("카테고리 정보가 없습니다.")
        else:
            selected_category = '전체'
    
    with col4:
        # 요일 선택 - 평일 기본값
        weekday_options = ['전체', '평일', '주말']
        selected_weekday = st.selectbox(
            "📆 요일 선택",
            weekday_options,
            index=1,  # 평일
            key='strategy_weekday'
        )
    
    with col5:
        # 분석 시작 버튼
        analyze_button = st.button(
            "🔍 전략분석 시작",
            key='strategy_analyze',
            type="primary",
            use_container_width=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 분석 실행
    if analyze_button or st.session_state.get('strategy_analysis_done', False):
        st.session_state.strategy_analysis_done = True
        
        # 디버깅 체크박스
        debug_mode = st.checkbox("🐛 데이터 필터링 과정 확인", key="debug_filtering", value=False)
        
        # 로딩 표시
        with st.spinner("🔄 전략을 분석하고 있습니다... 잠시만 기다려주세요."):
            # 데이터 복사
            analysis_df = df_with_cost.copy()
            
            if debug_mode:
                st.write("=" * 50)
                st.write("### 📊 데이터 필터링 디버깅 정보")
                st.write(f"**초기 데이터**: {len(analysis_df)}행")
                st.write(f"**사용 가능한 컬럼**: {', '.join(analysis_df.columns.tolist())}")
            
            # 방송사 필터
            if selected_channel != '전체' and col_platform:
                before_count = len(analysis_df)
                analysis_df = analysis_df[analysis_df[col_platform] == selected_channel]
                after_count = len(analysis_df)
                
                if debug_mode:
                    st.write(f"✅ **방송사 필터** ({selected_channel}): {before_count}행 → {after_count}행")
            
            # 날짜 필터
            if len(date_range) == 2 and col_date:
                start_date, end_date = date_range
                before_count = len(analysis_df)
                
                analysis_df[col_date] = pd.to_datetime(analysis_df[col_date], errors='coerce')
                analysis_df = analysis_df[analysis_df[col_date].notna()]
                analysis_df = analysis_df[
                    (analysis_df[col_date].dt.date >= start_date) &
                    (analysis_df[col_date].dt.date <= end_date)
                ]
                after_count = len(analysis_df)
                
                if debug_mode:
                    st.write(f"✅ **날짜 필터** ({start_date} ~ {end_date}): {before_count}행 → {after_count}행")
            
            # ROI 계산 (실질 마진율 57.75% 적용)
            before_count = len(analysis_df)
            analysis_df = calculate_roi_metrics(analysis_df, selected_channel if selected_channel != '전체' else None)
            after_count = len(analysis_df)
            
            # col_total_cost 변수 정의
            col_total_cost = get_column_name(analysis_df, 'total_cost')
            if col_total_cost is None:
                col_total_cost = 'total_cost'
            
            if debug_mode:
                st.write(f"✅ **ROI 계산** (실질 마진율 57.75%): {before_count}행 → {after_count}행")
                if 'roi' in analysis_df.columns:
                    # 가중평균 ROI 계산
                    if 'revenue' in analysis_df.columns and col_total_cost in analysis_df.columns:
                        total_real_profit = (analysis_df['revenue'] * REAL_MARGIN_RATE).sum()
                        total_cost = analysis_df[col_total_cost].sum()
                        weighted_avg_roi = ((total_real_profit - total_cost) / total_cost * 100) if total_cost > 0 else 0
                        st.write(f"가중평균 ROI: {weighted_avg_roi:.2f}%")
                    else:
                        st.write(f"평균 ROI: {analysis_df['roi'].mean():.2f}%")
                    st.write(f"평균 매출: {analysis_df['revenue'].mean():.2f}억")
            
            # 카테고리 필터
            if selected_category != '전체' and col_category:
                before_count = len(analysis_df)
                analysis_df = analysis_df[analysis_df[col_category] == selected_category]
                after_count = len(analysis_df)
                
                if debug_mode:
                    st.write(f"✅ **카테고리 필터** ({selected_category}): {before_count}행 → {after_count}행")
            
            # 요일 필터 및 weekday 컬럼 추가
            if col_date and col_date in analysis_df.columns:
                # date 컬럼이 datetime 타입인지 확인
                if not pd.api.types.is_datetime64_any_dtype(analysis_df[col_date]):
                    analysis_df[col_date] = pd.to_datetime(analysis_df[col_date], errors='coerce')
                
                # weekday 컬럼 추가 (영어 요일명)
                analysis_df['weekday'] = analysis_df[col_date].dt.day_name()
                
            if selected_weekday != '전체':
                before_count = len(analysis_df)
                if selected_weekday == '평일':
                    analysis_df = analysis_df[~analysis_df['is_weekend']]
                elif selected_weekday == '주말':
                    analysis_df = analysis_df[analysis_df['is_weekend']]
                after_count = len(analysis_df)
                
                if debug_mode:
                    st.write(f"✅ **요일 필터** ({selected_weekday}): {before_count}행 → {after_count}행")
            
            if debug_mode:
                st.write("=" * 50)
                st.write(f"### 🎯 **최종 결과**: {len(analysis_df)}행")
            
            # 데이터가 있는지 확인
            if len(analysis_df) == 0:
                st.error("""
                    ### ❌ 선택한 조건에 해당하는 데이터가 없습니다.
                    
                    **해결 방법:**
                    1. ✅ **'🐛 데이터 필터링 과정 확인'**을 체크하여 문제를 파악하세요
                    2. 📅 날짜 범위를 더 넓게 설정해보세요
                    3. 🏢 방송사를 '전체'로 변경해보세요
                    4. 📦 카테고리를 '전체'로 변경해보세요
                    5. 📆 요일을 '전체'로 변경해보세요
                """)
            else:
                # 주요 지표 계산 (절사평균 적용)
                total_broadcasts = len(analysis_df)
                total_revenue = analysis_df['revenue'].sum()
                avg_revenue = calculate_trimmed_mean(analysis_df['revenue'].values)
                
                # col_total_cost 변수 정의
                col_total_cost = get_column_name(analysis_df, 'total_cost')
                if col_total_cost is None:
                    col_total_cost = 'total_cost'
                
                # 절사평균 ROI 계산
                if 'roi' in analysis_df.columns:
                    avg_roi = calculate_trimmed_mean(analysis_df['roi'].values)
                else:
                    avg_roi = 0
                
                # 최적 시간 계산 (제외 시간대 적용)
                if 'hour' in analysis_df.columns:
                    # 주말/평일 구분
                    is_weekend = selected_weekday == '주말'
                    if is_weekend:
                        # 주말: 00시~05시 제외
                        excluded_hours = list(range(0, 6))
                    else:
                        # 평일: 00시~05시, 12시~16시 제외
                        excluded_hours = list(range(0, 6)) + list(range(12, 17))
                    
                    # 제외 시간대를 뺀 데이터만 사용
                    valid_hours_df = analysis_df[~analysis_df['hour'].isin(excluded_hours)]
                    if not valid_hours_df.empty:
                        best_hour_data = valid_hours_df.groupby('hour')['roi'].mean().idxmax()
                    else:
                        best_hour_data = 0
                else:
                    best_hour_data = 0
                
                # 주요 지표 표시 (디자인 개선)
                st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                st.subheader("📈 주요 지표")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                        <div class="metric-card">
                            <h4 style="color: #60A5FA;">
                                <span style="font-size: 24px;">📊</span><br>총 방송
                            </h4>
                            <h2 style="color: #60A5FA;">{total_broadcasts:,}건</h2>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                        <div class="metric-card">
                            <h4 style="color: #34D399;">
                                <span style="font-size: 24px;">💰</span><br>총 매출
                            </h4>
                            <h2 style="color: #34D399;">{total_revenue:.1f}억</h2>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                        <div class="metric-card">
                            <h4 style="color: #FBBF24;">
                                <span style="font-size: 24px;">📈</span><br>절사평균 매출
                            </h4>
                            <h2 style="color: #FBBF24;">{avg_revenue:.2f}억</h2>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    roi_color = "#34D399" if avg_roi > 0 else "#EF4444"
                    st.markdown(f"""
                        <div class="metric-card">
                            <h4 style="color: {roi_color};">
                                <span style="font-size: 24px;">📊</span><br>절사평균 ROI
                            </h4>
                            <h2 style="color: {roi_color};">{avg_roi:.1f}%</h2>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                        <div class="metric-card">
                            <h4 style="color: #A78BFA;">
                                <span style="font-size: 24px;">⏰</span><br>최적 시간
                            </h4>
                            <h2 style="color: #A78BFA;">{best_hour_data}시</h2>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 최적 판매 시간대 & 최적 단가대
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                    st.subheader("⏰ 최적 판매 시간대 TOP 7 (절사평균 기준)")
                    
                    # 주말/평일 구분하여 분석
                    is_weekend = selected_weekday == '주말'
                    top_hours = analyze_optimal_hours(analysis_df, is_weekend)
                    
                    if not top_hours.empty:
                        # 차트 생성
                        fig_hours = go.Figure()
                        
                        fig_hours.add_trace(go.Bar(
                            x=[f"{int(h)}시" for h in top_hours['hour']],
                            y=top_hours['roi'],
                            text=[f"<b>{roi:.1f}%</b>" for roi in top_hours['roi']],
                            textposition='outside',
                            textfont=dict(size=16),  # 폰트 크기 증가
                            marker=dict(
                                color=top_hours['roi'],
                                colorscale='Viridis',
                                showscale=False
                            ),
                            hovertemplate="<b>%{x}</b><br>절사평균 ROI: %{y:.1f}%<br>절사평균 매출: %{customdata:.2f}억<extra></extra>",
                            customdata=top_hours['avg_revenue']
                        ))
                        
                        fig_hours.update_layout(
                            height=385,  # 10% 증가
                            margin=dict(t=40, b=40, l=40, r=40),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0.05)',
                            xaxis=dict(
                                gridcolor='rgba(255,255,255,0.1)',
                                title="시간대",
                                title_font=dict(size=14),  # 폰트 크기 증가
                                tickfont=dict(size=12)
                            ),
                            yaxis=dict(
                                gridcolor='rgba(255,255,255,0.1)',
                                title='절사평균 ROI (%)',
                                title_font=dict(size=14),  # 폰트 크기 증가
                                tickfont=dict(size=12)
                            ),
                            hoverlabel=dict(
                                bgcolor='rgba(0,0,0,0.8)',
                                font_size=14  # 폰트 크기 증가
                            ),
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_hours, use_container_width=True, config={'displayModeBar': False})
                        
                        # 상세 설명 (폰트 크기 증가)
                        for idx, row in top_hours.iterrows():
                            rank = idx + 1  # 순위 계산
                            st.markdown(f"""
                                <div style="padding: 15px; background: rgba(102,126,234,0.1); border-left: 4px solid #667eea; border-radius: 8px; margin-bottom: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <strong style="color: #667eea; font-size: 18px;">{rank}위: {int(row['hour'])}시</strong>
                                        <span style="color: #34D399; font-weight: bold; font-size: 16px;">절사평균 ROI: {row['roi']:.1f}%</span>
                                    </div>
                                    <div style="color: #94A3B8; font-size: 15px; margin-bottom: 5px;">
                                        📊 절사평균 매출: {row['avg_revenue']:.2f}억 | 평균 판매수량: {row.get('total_units', 0) / row.get('count', 1) if row.get('count', 0) > 0 else 0:.0f}개 | 절사평균 판매수량: {row.get('avg_units', 0):.0f}개<br>
                                        🎬 방송횟수: {row.get('count', 0)}회 | 💰 최고매출 단가대: {row.get('best_price_range', '정보없음')} | 최저매출 단가대: {row.get('worst_price_range', '정보없음')}<br>
                                        📈 긍정 ROI 비율: {row.get('positive_rate', 0):.1f}%
                                    </div>
                                    <div style="color: #CBD5E1; font-size: 14px; line-height: 1.5;">
                                        💡 {row.get('reason', '')}<br>
                                        📌 {row.get('detail1', '')}<br>
                                        ✨ {row.get('detail2', '')}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info(f"{'주말' if is_weekend else '평일'} 시간대별 데이터가 충분하지 않습니다.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                    st.subheader("💰 최적 단가대 TOP 7 (절사평균 기준)")
                    
                    top_prices = analyze_optimal_price_ranges(analysis_df)
                    if not top_prices.empty:
                        # 차트 생성
                        fig_prices = go.Figure()
                        
                        fig_prices.add_trace(go.Bar(
                            x=top_prices['price_range'].astype(str),
                            y=top_prices['score'],
                            text=[f"<b>{score:.1f}</b>" for score in top_prices['score']],
                            textposition='outside',
                            textfont=dict(size=16),  # 폰트 크기 증가
                            marker=dict(
                                color=top_prices['score'],
                                colorscale='Tealgrn',
                                showscale=False
                            ),
                            hovertemplate="<b>%{x}</b><br>점수: %{y:.1f}<br>절사평균 ROI: %{customdata[0]:.1f}%<br>총매출: %{customdata[1]:.1f}억<extra></extra>",
                            customdata=top_prices[['roi', 'total_revenue']].values
                        ))
                        
                        fig_prices.update_layout(
                            height=385,  # 10% 증가
                            margin=dict(t=40, b=40, l=40, r=40),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0.05)',
                            xaxis=dict(
                                gridcolor='rgba(255,255,255,0.1)',
                                tickangle=-45,
                                title="가격대",
                                title_font=dict(size=14),  # 폰트 크기 증가
                                tickfont=dict(size=12)
                            ),
                            yaxis=dict(
                                gridcolor='rgba(255,255,255,0.1)',
                                title='종합 점수',
                                title_font=dict(size=14),  # 폰트 크기 증가
                                tickfont=dict(size=12)
                            ),
                            hoverlabel=dict(
                                bgcolor='rgba(0,0,0,0.8)',
                                font_size=14  # 폰트 크기 증가
                            ),
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_prices, use_container_width=True, config={'displayModeBar': False})
                        
                        # 상세 설명 (폰트 크기 증가)
                        for idx, row in top_prices.iterrows():
                            rank = idx + 1  # 순위 계산
                            st.markdown(f"""
                                <div style="padding: 15px; background: rgba(16,185,129,0.1); border-left: 4px solid #10B981; border-radius: 8px; margin-bottom: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <strong style="color: #10B981; font-size: 18px;">{rank}위: {row['price_range']}</strong>
                                        <span style="color: #60A5FA; font-weight: bold; font-size: 16px;">절사평균 ROI: {row['roi']:.1f}%</span>
                                    </div>
                                    <div style="color: #94A3B8; font-size: 15px; margin-bottom: 5px;">
                                        💰 총매출: {row['total_revenue']:.1f}억 | 평균 판매수량: {row.get('total_units', 0) / row.get('count', 1) if row.get('count', 0) > 0 else 0:.0f}개 | 절사평균 판매수량: {row.get('avg_units', 0):.0f}개<br>
                                        🎬 방송횟수: {row.get('count', 0)}회 | ⏰ 최고매출 시간대: {row.get('best_hour', '정보없음')} | 최저매출 단가대: {row.get('worst_price_range', '정보없음')}<br>
                                        📊 절사평균 매출: {row['avg_revenue']:.2f}억
                                    </div>
                                    <div style="color: #CBD5E1; font-size: 14px; line-height: 1.5;">
                                        💡 {row.get('reason', '')}<br>
                                        📌 {row.get('detail1', '')}<br>
                                        ✨ {row.get('detail2', '')}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("가격대별 데이터가 충분하지 않습니다. (7-16만원 범위, 상하위 15% 절사)")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # 요일별 최적 시간대
                st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                st.subheader("📅 요일별 최적 시간대 TOP 5")
                
                # 디버깅 정보 확인
                if 'weekday' not in analysis_df.columns:
                    st.warning("⚠️ 'weekday' 컬럼이 생성되지 않았습니다. 날짜 데이터를 확인해주세요.")
                    if debug_mode:
                        st.write(f"현재 컬럼: {analysis_df.columns.tolist()}")
                
                weekday_optimization = analyze_weekday_optimization(analysis_df)
                
                if debug_mode:
                    st.write(f"요일별 최적화 결과: {weekday_optimization}")
                
                if weekday_optimization:
                    cols = st.columns(5)
                    weekdays = ['월', '화', '수', '목', '금']
                    colors = ['#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6']
                    
                    for idx, day in enumerate(weekdays):
                        with cols[idx]:
                            st.markdown(f"""
                                <div style="background: linear-gradient(135deg, {colors[idx]}20 0%, {colors[idx]}10 100%); 
                                         padding: 6px; border-radius: 8px; border: 1px solid {colors[idx]}40; min-height: 220px;">
                                    <h5 style="color: {colors[idx]}; text-align: center; margin: 2px 0 6px 0; font-size: 13px; font-weight: bold; padding: 2px 0;">{day}요일</h5>
                            """, unsafe_allow_html=True)
                            
                            if day in weekday_optimization and weekday_optimization[day]:
                                for rank, hour_data in enumerate(weekday_optimization[day][:5], 1):  # TOP 5까지
                                    roi_color = "#34D399" if hour_data['roi'] > 0 else "#EF4444"
                                    st.markdown(f"""
                                        <div style="padding: 5px; margin: 3px 0; background: rgba(255,255,255,0.08); border-radius: 5px; border-left: 2px solid {colors[idx]};">
                                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                                <span style="font-weight: bold; color: white; font-size: 13px;">{rank}위: {hour_data['hour']}시</span>
                                            </div>
                                            <div style="font-size: 11px; color: #CBD5E1; margin-top: 2px; line-height: 1.4;">
                                                절사평균 ROI: <span style="color: {roi_color}; font-weight: bold; font-size: 12px;">{hour_data['roi']:.1f}%</span><br>
                                                절사평균 매출: <span style="color: #60A5FA; font-weight: bold; font-size: 12px;">{hour_data['avg_revenue']:.1f}억</span><br>
                                                평균판매량: <span style="color: #A78BFA; font-weight: bold;">{hour_data.get('avg_units', 0):.0f}개</span><br>
                                                절사평균 판매량: <span style="color: #10B981; font-weight: bold;">{hour_data.get('trimmed_avg_units', 0):.0f}개</span><br>
                                                방송횟수: <span style="color: #FBBF24; font-weight: bold;">{hour_data.get('count', 0)}회</span>
                                            </div>
                                        </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.markdown("<div style='text-align: center; color: #6B7280; margin-top: 40px;'>데이터 없음</div>", unsafe_allow_html=True)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("요일별 데이터가 충분하지 않습니다. 날짜 범위를 확인해주세요.")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 도전 가능 & 회피 시간대
                col1, col2 = st.columns(2)
                
                # 주말/평일 구분하여 분석
                is_weekend = selected_weekday == '주말'
                challenge_hours, avoid_hours = analyze_challenge_and_avoid_hours(analysis_df, is_weekend)
                
                with col1:
                    st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                    st.subheader("⚡ 도전해볼 만한 시간대 (TOP 3)")
                    
                    if challenge_hours and len(challenge_hours) > 0:
                        for hour_data in challenge_hours[:3]:
                            st.markdown(f"""
                                <div class="challenge-box">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <h4 style="color: #92400E; font-size: 20px; font-weight: bold;">
                                            {hour_data['hour']}시
                                        </h4>
                                        <div style="text-align: right;">
                                            <span style="color: #D97706; font-weight: bold; font-size: 15px;">절사평균 ROI: {hour_data['roi']:.1f}%</span><br>
                                            <span style="color: #B45309; font-size: 14px;">절사평균 매출: {hour_data['avg_revenue']:.2f}억</span>
                                        </div>
                                    </div>
                                    <div style="color: #92400E; font-size: 15px; margin-bottom: 10px; font-weight: 600;">
                                        📊 절사평균 판매수량: {hour_data.get('avg_units', 0):.0f}개<br>
                                        💰 최고매출 단가: {hour_data.get('best_price', '정보없음')} | 최저매출 단가: {hour_data.get('worst_price', '정보없음')}
                                    </div>
                                    <div style="color: #78350F; font-size: 15px; line-height: 1.8; font-weight: 500;">
                                        📍 {hour_data['reason']}<br>
                                        💡 {hour_data.get('detail1', '')}<br>
                                        🎯 {hour_data.get('detail2', '')}<br>
                                        ⚡ {hour_data.get('detail3', '')}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("분석할 데이터가 충분하지 않습니다. (최소 2건 이상 필요)")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                    st.subheader("⚠️ 절대 피해야 할 시간대 (TOP 3)")
                    
                    if avoid_hours and len(avoid_hours) > 0:
                        for hour_data in avoid_hours[:3]:
                            st.markdown(f"""
                                <div class="avoid-box">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <h4 style="color: #7F1D1D; font-size: 20px; font-weight: bold;">
                                            {hour_data['hour']}시
                                        </h4>
                                        <div style="text-align: right;">
                                            <span style="color: #B91C1C; font-weight: bold; font-size: 15px;">절사평균 ROI: {hour_data['roi']:.1f}%</span><br>
                                            <span style="color: #991B1B; font-size: 14px;">절사평균 매출: {hour_data['avg_revenue']:.2f}억</span>
                                        </div>
                                    </div>
                                    <div style="color: #991B1B; font-size: 15px; margin-bottom: 10px; font-weight: 600;">
                                        📊 절사평균 판매수량: {hour_data.get('avg_units', 0):.0f}개<br>
                                        💰 최고매출 단가: {hour_data.get('best_price', '정보없음')} | 최저매출 단가: {hour_data.get('worst_price', '정보없음')}
                                    </div>
                                    <div style="color: #7F1D1D; font-size: 15px; line-height: 1.8; font-weight: 500;">
                                        📍 {hour_data['reason']}<br>
                                        ⚠️ {hour_data.get('detail1', '')}<br>
                                        ❌ {hour_data.get('detail2', '')}<br>
                                        🚫 {hour_data.get('detail3', '')}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("분석할 데이터가 충분하지 않습니다.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # 전략적 제언
                st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                st.subheader("✨ 전략적 제언")
                
                # 전략적 제언 카드들
                recommendations = [
                    {
                        "icon": "⏰",
                        "title": "시간대 최적화",
                        "content": f"오전 {top_hours.iloc[0]['hour'] if not top_hours.empty else 10}시와 저녁 {top_hours.iloc[1]['hour'] if len(top_hours) > 1 else 20}시에 주력 상품 배치",
                        "detail1": "피크 시간대 집중 운영으로 효율성 극대화",
                        "detail2": "타겟 고객층의 시청 패턴에 최적화된 편성"
                    },
                    {
                        "icon": "💰",
                        "title": "가격 전략",
                        "content": f"{top_prices.iloc[0]['price_range'] if not top_prices.empty else '9만원대'} 중심의 가격 구성",
                        "detail1": "심리적 가격대를 활용한 구매 전환율 향상",
                        "detail2": "가격 경쟁력과 수익성의 균형점 확보"
                    },
                    {
                        "icon": "📅",
                        "title": "요일별 차별화",
                        "content": "화요일과 금요일 특별 프로모션 강화",
                        "detail1": "요일별 고객 특성을 반영한 맞춤 전략",
                        "detail2": "주중/주말 구매 패턴 차이를 활용한 운영"
                    },
                    {
                        "icon": "🎯",
                        "title": "리스크 관리",
                        "content": "새벽 시간대와 낮 12-16시 방송 최소화",
                        "detail1": "비효율 시간대 회피로 손실 최소화",
                        "detail2": "투자 대비 수익률 개선을 통한 전체 ROI 상승"
                    }
                ]
                
                cols = st.columns(2)
                for idx, rec in enumerate(recommendations):
                    with cols[idx % 2]:
                        st.markdown(f"""
                            <div class="strategy-card">
                                <h3 style="color: #8B5CF6; font-size: 20px; margin-bottom: 12px;">
                                    {rec['icon']} {rec['title']}
                                </h3>
                                <p style="color: white; font-size: 14px; font-weight: bold; margin-bottom: 10px;">
                                    {rec['content']}
                                </p>
                                <p style="color: #CBD5E1; font-size: 12px; line-height: 1.6;">
                                    • {rec['detail1']}<br>
                                    • {rec['detail2']}
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                    if idx % 2 == 1:
                        st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # HTML 리포트 다운로드 버튼
                st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("""
                        <div style="padding: 15px; background: rgba(139,92,246,0.1); border-radius: 10px;">
                            <h4 style="color: #8B5CF6;">📄 분석 리포트 다운로드</h4>
                            <p style="color: #CBD5E1; font-size: 12px; margin-top: 5px;">
                                현재 화면과 동일한 디자인의 상세 HTML 리포트를 다운로드할 수 있습니다.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # 리포트 데이터 준비
                    report_data = {
                        'total_count': total_broadcasts,
                        'total_revenue': total_revenue,
                        'avg_revenue': avg_revenue,
                        'avg_roi': avg_roi,
                        'best_hour': {
                            'hour': best_hour_data,
                            'roi': analysis_df[analysis_df['hour'] == best_hour_data]['roi'].mean() if best_hour_data else 0,
                            'avg_revenue': analysis_df[analysis_df['hour'] == best_hour_data]['revenue'].mean() if best_hour_data else 0
                        } if best_hour_data else {}
                    }
                    
                    # 고급 HTML 리포트 생성
                    date_str = f"{date_range[0]} ~ {date_range[1]}" if len(date_range) == 2 else "전체 기간"
                    html_content = generate_html_report_advanced(
                        analysis_df, report_data, selected_channel, date_str,
                        top_hours, top_prices, weekday_optimization,
                        challenge_hours, avoid_hours
                    )
                    
                    st.download_button(
                        label="📥 HTML 리포트 다운로드",
                        data=html_content,
                        file_name=f"strategy_report_{selected_channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                        mime="text/html",
                        key="download_html_report"
                    )
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        # 분석 시작 전 안내
        st.info("📊 필터를 선택하고 '🔍 전략분석 시작' 버튼을 클릭하여 분석을 시작하세요.")
        
        # 안내 카드
        st.markdown("""
            <div class="analysis-card" style="text-align: center; padding: 60px 40px;">
                <h2 style="color: #8B5CF6; margin-bottom: 30px; font-size: 32px;">전략 분석 시스템</h2>
                <p style="color: #CBD5E1; line-height: 1.8; font-size: 16px; margin-bottom: 40px;">
                    ROI 기반으로 최적의 판매 시간대와 가격대를 분석하여<br>
                    데이터 기반의 전략적 의사결정을 지원합니다.
                </p>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; max-width: 800px; margin: 0 auto;">
                    <div style="background: rgba(96,165,250,0.1); padding: 25px; border-radius: 12px; border: 1px solid rgba(96,165,250,0.3);">
                        <h3 style="color: #60A5FA; font-size: 32px; margin-bottom: 10px;">🕐</h3>
                        <p style="color: white; font-weight: bold;">최적 시간대</p>
                        <p style="color: #94A3B8; font-size: 12px; margin-top: 5px;">ROI 기반 분석</p>
                    </div>
                    <div style="background: rgba(52,211,153,0.1); padding: 25px; border-radius: 12px; border: 1px solid rgba(52,211,153,0.3);">
                        <h3 style="color: #34D399; font-size: 32px; margin-bottom: 10px;">💵</h3>
                        <p style="color: white; font-weight: bold;">최적 가격대</p>
                        <p style="color: #94A3B8; font-size: 12px; margin-top: 5px;">1만원 단위 분석</p>
                    </div>
                    <div style="background: rgba(251,191,36,0.1); padding: 25px; border-radius: 12px; border: 1px solid rgba(251,191,36,0.3);">
                        <h3 style="color: #FBBF24; font-size: 32px; margin-bottom: 10px;">📈</h3>
                        <p style="color: white; font-weight: bold;">요일별 전략</p>
                        <p style="color: #94A3B8; font-size: 12px; margin-top: 5px;">매출 최적화</p>
                    </div>
                    <div style="background: rgba(239,68,68,0.1); padding: 25px; border-radius: 12px; border: 1px solid rgba(239,68,68,0.3);">
                        <h3 style="color: #EF4444; font-size: 32px; margin-bottom: 10px;">⚡</h3>
                        <p style="color: white; font-weight: bold;">리스크 관리</p>
                        <p style="color: #94A3B8; font-size: 12px; margin-top: 5px;">손실 최소화</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# Export the function
__all__ = ['create_strategy_analysis_tab']
