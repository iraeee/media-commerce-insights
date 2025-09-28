"""
dashboard_precision_analysis.py - 홈쇼핑 매출 정밀분석 탭 (Dark Mode + Glassmorphism) - 완전 수정 버전
Version: 16.0.0
Updated: 2025-02-03

주요 수정사항 (v16.0.0):
1. 매출액 호버값 0.00억 표시 문제 수정 - customdata 활용
2. 그래프 Y축 20% 확대 및 ROI 축 20단위 세분화
3. 가격대별 효율성 탭에 평균선 및 방송횟수 추가
4. 가격 최적화 분석탭 HTML 렌더링 에러 수정
5. 효율성 인사이트 상세화 및 실행 가이드 추가
6. 종합 효율성 점수 그래프 삭제
7. 방송 내역 조회 테이블 추가
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from scipy import stats
import time
import warnings
import json
warnings.filterwarnings('ignore')

# dashboard_data에서 safe_abs 함수 import
try:
    from dashboard_data import safe_abs
except ImportError:
    def safe_abs(x):
        """안전한 절댓값 함수"""
        try:
            return abs(float(x)) if x is not None else 0
        except:
            return 0

# dashboard_config에서 새로운 마진율 및 채널 정보 import 추가
try:
    from dashboard_config import (
        REAL_MARGIN_RATE, REAL_MARGIN_RATE_NO_BROADCAST, 
        CONVERSION_RATE, PRODUCT_COST_RATE, COMMISSION_RATE, COMMISSION_RATE_HIGH,
        LIVE_CHANNELS, MODEL_COST_LIVE, MODEL_COST_NON_LIVE
    )
except ImportError:
    # 폴백 값 설정 (dashboard_config가 없거나 수정되지 않은 경우)
    CONVERSION_RATE = 0.75
    PRODUCT_COST_RATE = 0.13
    COMMISSION_RATE = 0.10  # 일반 수수료율 (방송정액비 있는 경우)
    COMMISSION_RATE_HIGH = 0.42  # 높은 수수료율 (방송정액비 없는 경우)
    
    # 실질 마진율 계산
    # 방송정액비 있는 경우: 전환율 × (1 - 원가율 - 수수료율10%)
    REAL_MARGIN_RATE = CONVERSION_RATE * (1 - PRODUCT_COST_RATE - COMMISSION_RATE)  # 0.75 × 0.77 = 0.5775
    
    # 방송정액비 없는 경우: 전환율 × (1 - 원가율 - 수수료율42%)
    REAL_MARGIN_RATE_NO_BROADCAST = CONVERSION_RATE * (1 - PRODUCT_COST_RATE - COMMISSION_RATE_HIGH)  # 0.75 × 0.45 = 0.3375
    
    # Live 채널 정의
    LIVE_CHANNELS = {
        '현대홈쇼핑', 'GS홈쇼핑', 'gs홈쇼핑', '롯데홈쇼핑', 
        'CJ온스타일', 'cj온스타일', '홈앤쇼핑', 'NS홈쇼핑', 
        'ns홈쇼핑', '공영쇼핑', '공영홈쇼핑'
    }
    
    # 모델 비용
    MODEL_COST_LIVE = 10400000
    MODEL_COST_NON_LIVE = 2000000

# ============================================================================
# Dark Mode + 네온 색상 팔레트
# ============================================================================

DARK_NEON_THEME = {
    # 배경 - Dark Mode
    'bg_primary': 'rgba(0, 0, 0, 0)',           # 완전 투명 (차트)
    'bg_secondary': 'rgba(255, 255, 255, 0.02)', # 거의 투명 (플롯)
    'bg_card': 'rgba(255, 255, 255, 0.05)',      # 카드 배경
    'bg_hover': 'rgba(255, 255, 255, 0.08)',     # 호버 상태
    
    # 네온 액센트 색상
    'accent_cyan': '#00D9FF',      # 메인 시안
    'accent_purple': '#7C3AED',    # 퍼플
    'accent_green': '#10F981',     # 그린
    'accent_red': '#FF3355',       # 레드
    'accent_orange': '#FF6B35',    # 오렌지
    'accent_yellow': '#FFD93D',    # 옐로우
    'accent_pink': '#FF0080',      # 핑크
    'accent_teal': '#00FFB9',      # 틸
    'accent_blue': '#3498DB',      # 블루
    
    # 텍스트 - 흰색 계열
    'text_primary': '#FFFFFF',
    'text_secondary': 'rgba(255, 255, 255, 0.85)',
    'text_muted': 'rgba(255, 255, 255, 0.60)',
    'text_disabled': 'rgba(255, 255, 255, 0.38)',
    
    # 테두리
    'border_light': 'rgba(255, 255, 255, 0.06)',
    'border_medium': 'rgba(255, 255, 255, 0.12)',
    'border_focus': 'rgba(0, 217, 255, 0.5)',
}

# Dark Mode 차트 기본 레이아웃 - hoverlabel 포함
DARK_CHART_LAYOUT = {
    'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    'plot_bgcolor': 'rgba(255, 255, 255, 0.02)',
    'font': dict(
        color='#FFFFFF',
        size=13,
        family="'Inter', 'Pretendard', system-ui, sans-serif"
    ),
    'hoverlabel': dict(
        bgcolor='rgba(10, 11, 30, 0.95)',  # 어두운 배경
        bordercolor='#00D9FF',
        font=dict(
            size=15,
            family="'Inter', sans-serif",
            color='#FFFFFF'  # 흰색 텍스트
        )
    ),
    'xaxis': dict(
        gridcolor='rgba(255, 255, 255, 0.06)',
        linecolor='rgba(255, 255, 255, 0.12)',
        tickfont=dict(color='rgba(255, 255, 255, 0.85)')
    ),
    'yaxis': dict(
        gridcolor='rgba(255, 255, 255, 0.06)',
        linecolor='rgba(255, 255, 255, 0.12)',
        tickfont=dict(color='rgba(255, 255, 255, 0.85)')
    )
}

# hoverlabel 충돌 방지를 위한 헬퍼 함수
def get_layout_without_hoverlabel():
    """hoverlabel을 제외한 DARK_CHART_LAYOUT 반환"""
    layout = DARK_CHART_LAYOUT.copy()
    if 'hoverlabel' in layout:
        del layout['hoverlabel']
    return layout

# ============================================================================
# 유틸리티 함수
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

def safe_dropna(data):
    """데이터 타입에 관계없이 안전하게 dropna 처리"""
    import pandas as pd
    import numpy as np
    
    if isinstance(data, pd.Series):
        return data.dropna()
    elif isinstance(data, pd.DataFrame):
        return data.dropna()
    elif isinstance(data, np.ndarray):
        # numpy array를 Series로 변환 후 dropna
        return pd.Series(data).dropna()
    elif isinstance(data, list):
        # list를 Series로 변환 후 dropna
        return pd.Series(data).dropna()
    else:
        # 기타 타입은 Series로 변환 시도
        try:
            return pd.Series(data).dropna()
        except:
            return pd.Series([])

def safe_trim_mean(data, proportion):
    """안전한 trim_mean 계산"""
    import pandas as pd
    from scipy import stats
    
    # 데이터를 안전하게 Series로 변환하고 dropna 처리
    clean_data = safe_dropna(data)
    
    # 숫자로 변환
    if len(clean_data) > 0:
        try:
            numeric_data = pd.to_numeric(clean_data, errors='coerce').dropna()
            if len(numeric_data) >= 5:
                return stats.trim_mean(numeric_data, proportion)
            elif len(numeric_data) > 0:
                return numeric_data.mean()
        except:
            pass
    return 0

def safe_quantile(data, q):
    """안전한 quantile 계산"""
    import pandas as pd
    
    # 데이터를 안전하게 Series로 변환하고 dropna 처리
    clean_data = safe_dropna(data)
    
    # 숫자로 변환
    if len(clean_data) > 0:
        try:
            numeric_data = pd.to_numeric(clean_data, errors='coerce').dropna()
            if len(numeric_data) > 0:
                return numeric_data.quantile(q)
        except:
            pass
    return 0

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
                
                # 문자열인 경우 정리 작업 수행
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace(',', '')
                    df[col] = df[col].str.replace('원', '')
                    df[col] = df[col].str.replace('₩', '')
                    df[col] = df[col].str.replace('%', '')
                    df[col] = df[col].str.replace('억', '')
                    df[col] = df[col].str.replace('만', '')
                    df[col] = df[col].str.replace('천', '')
                    df[col] = df[col].str.strip()
                
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                df[col] = df[col].replace([np.inf, -np.inf], 0)
            except:
                df[col] = 0
    
    # hour 정수로 변환
    if 'hour' in df.columns:
        try:
            if not isinstance(df['hour'], pd.Series):
                df['hour'] = pd.Series(df['hour'])
            df['hour'] = pd.to_numeric(df['hour'], errors='coerce').fillna(0).astype(int)
        except:
            df['hour'] = 0
    
    # weekday는 한글 문자열로 유지
    
    return df

def safe_calculate_elasticity(analysis_df):
    """안전한 가격 탄력성 계산 - 완전한 문자열 처리 버전"""
    import pandas as pd
    import numpy as np
    
    elasticity = []
    
    # DataFrame 복사본으로 작업 (원본 보호)
    df = analysis_df.copy()
    
    # 모든 필요한 컬럼을 숫자로 강제 변환
    for col in ['center_price', 'avg_units']:
        if col in df.columns:
            # 각 값을 개별적으로 변환
            converted_values = []
            for val in df[col]:
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    converted_values.append(0.0)
                elif isinstance(val, str):
                    # 문자열 정리
                    cleaned = str(val).replace(',', '').replace('원', '').replace('%', '').replace('개', '').strip()
                    try:
                        converted_values.append(float(cleaned) if cleaned and cleaned != '-' else 0.0)
                    except:
                        converted_values.append(0.0)
                else:
                    try:
                        converted_values.append(float(val))
                    except:
                        converted_values.append(0.0)
            df[col] = converted_values
    
    # 이제 모든 값이 float이므로 안전하게 계산
    for i in range(1, len(df)):
        try:
            curr_price = df.iloc[i]['center_price'] if 'center_price' in df.columns else 0
            prev_price = df.iloc[i-1]['center_price'] if 'center_price' in df.columns else 0
            curr_units = df.iloc[i]['avg_units'] if 'avg_units' in df.columns else 0
            prev_units = df.iloc[i-1]['avg_units'] if 'avg_units' in df.columns else 0
            
            # 이미 float으로 변환되어 있음
            curr_price = float(curr_price) if curr_price else 0
            prev_price = float(prev_price) if prev_price else 0
            curr_units = float(curr_units) if curr_units else 0
            prev_units = float(prev_units) if prev_units else 0
            
            # 변화율 계산
            if prev_price > 0 and prev_units > 0:
                price_change = (curr_price - prev_price) / prev_price
                quantity_change = (curr_units - prev_units) / prev_units
                
                if price_change != 0:
                    elasticity_value = quantity_change / price_change
                    # safe_abs 사용 - 절대값 계산
                    elasticity.append(safe_abs(elasticity_value))
                else:
                    elasticity.append(0)
            else:
                elasticity.append(0)
                
        except Exception as e:
            # 어떤 오류든 0으로 처리
            elasticity.append(0)
    
    return [0] + elasticity

# ============================================================================
# 메인 함수
# ============================================================================

def create_precision_analysis_tab(df_filtered, chart_generator, data_formatter, 
                                 category_colors, platform_colors, colors):
    """정밀분석 탭 - Dark Mode + Glassmorphism + 수정사항 반영"""
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">🔬 홈쇼핑 매출 정밀분석</h2>', unsafe_allow_html=True)
    
    # 데이터 준비 - 전처리 함수를 먼저 호출
    df = df_filtered.copy()
    
    # 중요: 숫자 컬럼 전처리를 먼저 수행
    df = preprocess_numeric_columns(df)
    
    # 모든 숫자 컬럼을 명시적으로 변환
    numeric_columns = ['revenue', 'units_sold', 'cost', 'total_cost', 
                      'real_profit', 'model_cost', 'roi', 'roi_calculated', 
                      'product_count']
    
    for col in numeric_columns:
        if col in df.columns:
            # 문자열을 숫자로 변환
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 시간 컬럼 생성 (없는 경우)
    if 'hour' not in df.columns:
        try:
            df['hour'] = pd.to_datetime(df['time'], errors='coerce').dt.hour
        except:
            df['time'] = df['time'].astype(str)
            df['hour'] = df['time'].str.split(':').str[0].astype(int)
    
    if 'weekday' not in df.columns:
        df['weekday'] = pd.to_datetime(df['date']).dt.weekday
    
    # ROI 계산법 변경 안내 표시
    st.info(f"""
    **📊 ROI 계산법 업데이트 안내**
    - 실질 마진율: {REAL_MARGIN_RATE:.2%} (전환율 {CONVERSION_RATE:.0%}, 원가율 {PRODUCT_COST_RATE:.0%}, 수수료율 {COMMISSION_RATE:.0%})
    - ROI = ((매출 × {REAL_MARGIN_RATE:.4f}) - 총비용) / 총비용 × 100
    - 평균 ROI는 가중평균으로 계산 (총 실질이익 / 총 비용)
    """)
    
    # 매출이 0원인 데이터 제외 옵션
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        exclude_zero = st.checkbox(
            "매출 0원 제외",
            value=True,
            key="precision_exclude_zero_v16",
            help="매출이 0원인 방송을 분석에서 제외합니다"
        )
    
    with col2:
        outlier_method = st.selectbox(
            "이상치 처리 방법",
            ["IQR 1.5배", "표준편차 3배", "상위 5% 제외"],
            key="precision_outlier_method_v16",
            help="이상치를 판단하는 기준을 선택합니다"
        )
    
    with col3:
        st.metric(
            "분석 데이터",
            f"{len(df):,}건",
            f"전체 중 {len(df)/len(df_filtered)*100:.1f}%"
        )
    
    if exclude_zero:
        df = df[df['revenue'] > 0]
    
    if len(df) == 0:
        st.warning("분석할 데이터가 없습니다.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # 핵심 통계 지표 계산
    _render_key_statistics_dark(df, data_formatter)
    
    # 탭 스타일 강조 CSS 추가
    st.markdown("""
    <style>
    /* 정밀분석 하위 탭 강조 */
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1));
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 20px;
        border: 1px solid rgba(0, 217, 255, 0.3);
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 16px;
        padding: 12px 20px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        margin: 0 5px;
        transition: all 0.3s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.3), rgba(124, 58, 237, 0.3));
        border: 1px solid #00D9FF;
        box-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
    }
    
    /* 테이블 스타일 */
    .broadcast-table {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(0, 217, 255, 0.2);
    }
    
    .broadcast-table th {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.2), rgba(124, 58, 237, 0.2));
        color: #FFFFFF;
        font-weight: 600;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid rgba(0, 217, 255, 0.3);
    }
    
    .broadcast-table td {
        padding: 10px 12px;
        color: rgba(255, 255, 255, 0.85);
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    .broadcast-table tr:hover {
        background: rgba(0, 217, 255, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 시간대별 통계 종합",
        "🗓️ 요일×시간대 히트맵", 
        "💰 가격대별 효율성",
        "📊 가격 최적화 분석"
    ])
    
    with tab1:
        _create_hourly_comprehensive_analysis_dark_v16(df, data_formatter)
    
    with tab2:
        _create_weekday_hourly_heatmap_dark_improved_v16(df, data_formatter)
    
    with tab3:
        _create_price_efficiency_analysis_dark_improved_v16(df, data_formatter, platform_colors, category_colors)
    
    with tab4:
        _create_price_optimization_analysis_v16(df, data_formatter)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# 핵심 통계 지표 - Dark Mode
# ============================================================================

def _render_key_statistics_dark(df, data_formatter):
    """핵심 통계 지표 표시 - Dark Mode + 네온"""
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1)); 
                backdrop-filter: blur(12px);
                border: 1px solid rgba(0, 217, 255, 0.3);
                padding: 20px; border-radius: 15px; margin-bottom: 20px;">
        <h3 style="color: white; text-align: center; margin: 0; font-weight: 700; 
                   text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);">
            💎 핵심 통계 지표
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    mean_revenue = df['revenue'].mean()
    with col1:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); 
                    backdrop-filter: blur(10px);
                    padding: 15px; border-radius: 10px; 
                    border: 1px solid {DARK_NEON_THEME['accent_cyan']};
                    box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
                    text-align: center;">
            <p style="color: {DARK_NEON_THEME['text_muted']}; font-size: 12px; margin: 0; font-weight: 600;">평균 매출</p>
            <h3 style="color: {DARK_NEON_THEME['accent_cyan']}; margin: 5px 0; font-weight: 700;
                       text-shadow: 0 0 10px rgba(0, 217, 255, 0.5);">
                {data_formatter.format_money(mean_revenue)}
            </h3>
            <p style="color: {DARK_NEON_THEME['text_secondary']}; font-size: 11px; margin: 0;">전체 평균</p>
        </div>
        """, unsafe_allow_html=True)
    
    median_revenue = df['revenue'].median()
    with col2:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    padding: 15px; border-radius: 10px;
                    border: 1px solid {DARK_NEON_THEME['accent_green']};
                    box-shadow: 0 0 20px rgba(16, 249, 129, 0.3);
                    text-align: center;">
            <p style="color: {DARK_NEON_THEME['text_muted']}; font-size: 12px; margin: 0; font-weight: 600;">중위값</p>
            <h3 style="color: {DARK_NEON_THEME['accent_green']}; margin: 5px 0; font-weight: 700;
                       text-shadow: 0 0 10px rgba(16, 249, 129, 0.5);">
                {data_formatter.format_money(median_revenue)}
            </h3>
            <p style="color: {DARK_NEON_THEME['text_secondary']}; font-size: 11px; margin: 0;">50% 지점</p>
        </div>
        """, unsafe_allow_html=True)
    
    trimmed_mean = safe_trim_mean(df['revenue'], 0.1)
    with col3:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    padding: 15px; border-radius: 10px;
                    border: 1px solid {DARK_NEON_THEME['accent_orange']};
                    box-shadow: 0 0 20px rgba(255, 107, 53, 0.3);
                    text-align: center;">
            <p style="color: {DARK_NEON_THEME['text_muted']}; font-size: 12px; margin: 0; font-weight: 600;">절사평균</p>
            <h3 style="color: {DARK_NEON_THEME['accent_orange']}; margin: 5px 0; font-weight: 700;
                       text-shadow: 0 0 10px rgba(255, 107, 53, 0.5);">
                {data_formatter.format_money(trimmed_mean)}
            </h3>
            <p style="color: {DARK_NEON_THEME['text_secondary']}; font-size: 11px; margin: 0;">상하 10% 제외</p>
        </div>
        """, unsafe_allow_html=True)
    
    q1 = safe_quantile(df['revenue'], 0.25)
    q3 = safe_quantile(df['revenue'], 0.75)
    iqr = q3 - q1
    with col4:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    padding: 15px; border-radius: 10px;
                    border: 1px solid {DARK_NEON_THEME['accent_purple']};
                    box-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
                    text-align: center;">
            <p style="color: {DARK_NEON_THEME['text_muted']}; font-size: 12px; margin: 0; font-weight: 600;">IQR</p>
            <h3 style="color: {DARK_NEON_THEME['accent_purple']}; margin: 5px 0; font-weight: 700;
                       text-shadow: 0 0 10px rgba(124, 58, 237, 0.5);">
                {data_formatter.format_money(iqr)}
            </h3>
            <p style="color: {DARK_NEON_THEME['text_secondary']}; font-size: 11px; margin: 0;">Q3-Q1</p>
        </div>
        """, unsafe_allow_html=True)
    
    cv = (df['revenue'].std() / df['revenue'].mean() * 100) if df['revenue'].mean() > 0 else 0
    with col5:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    padding: 15px; border-radius: 10px;
                    border: 1px solid {DARK_NEON_THEME['accent_teal']};
                    box-shadow: 0 0 20px rgba(0, 255, 185, 0.3);
                    text-align: center;">
            <p style="color: {DARK_NEON_THEME['text_muted']}; font-size: 12px; margin: 0; font-weight: 600;">변동계수</p>
            <h3 style="color: {DARK_NEON_THEME['accent_teal']}; margin: 5px 0; font-weight: 700;
                       text-shadow: 0 0 10px rgba(0, 255, 185, 0.5);">
                {cv:.1f}%
            </h3>
            <p style="color: {DARK_NEON_THEME['text_secondary']}; font-size: 11px; margin: 0;">상대 변동성</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# 1. 시간대별 통계 종합 - 수정: 방송 내역 조회 테이블 추가
# ============================================================================

def _create_hourly_comprehensive_analysis_dark_v16(df, data_formatter):
    """시간대별 종합 통계 분석 - 방송 내역 조회 테이블 추가"""
    
    # 데이터 타입 확인 및 변환
    df = preprocess_numeric_columns(df.copy())
    
    st.subheader("📈 시간대별 매출 통계 종합 분석")
    
    st.info("""
    **📊 분석 설명**
    - **평균값**: 모든 데이터를 합산하여 나눈 값으로, 극단값의 영향을 받습니다
    - **중위값**: 데이터를 정렬했을 때 중간에 위치한 값으로, 극단값의 영향이 적습니다
    - **절사평균**: 상하위 20%를 제외한 평균으로, 안정적인 중심 경향을 보여줍니다
    - **25-75% 구간**: 데이터의 중간 50%가 분포하는 범위를 나타냅니다
    - **변동계수**: (표준편차÷평균)×100으로 계산하며, 값이 작을수록 안정적입니다
    - **ROI**: 가중평균으로 계산 (총 실질이익 / 총 비용)
    """)
    
    # 그래프 타입 선택
    graph_type = st.radio(
        "그래프 타입",
        ["선 그래프", "막대 그래프"],
        horizontal=True,
        key="hourly_graph_type_v16"
    )
    
    # 시간대별 통계 계산
    hourly_stats = []
    for hour in range(24):
        hour_data = df[df['hour'] == hour]
        if len(hour_data) >= 5:
            # 가중평균 ROI 계산
            weighted_roi = calculate_weighted_roi(hour_data)
            
            # 절사평균 ROI 계산 (상하위 20% 제거)
            trimmed_roi = safe_trim_mean(hour_data['roi_calculated'], 0.2)
            
            hourly_stats.append({
                'hour': hour,
                'mean': hour_data['revenue'].mean(),
                'median': hour_data['revenue'].median(),
                'trimmed_mean': safe_trim_mean(hour_data['revenue'], 0.2),
                'q25': safe_quantile(hour_data['revenue'], 0.25),
                'q75': safe_quantile(hour_data['revenue'], 0.75),
                'std': hour_data['revenue'].std(),
                'count': len(hour_data),
                'cv': (hour_data['revenue'].std() / hour_data['revenue'].mean() * 100) if hour_data['revenue'].mean() > 0 else 0,
                'weighted_roi': weighted_roi,
                'trimmed_roi': trimmed_roi  # 절사평균 ROI 추가
            })
    
    if not hourly_stats:
        st.info("분석에 충분한 데이터가 없습니다.")
        return
    
    hourly_df = pd.DataFrame(hourly_stats)
    
    # ============================================================================
    # 인사이트를 먼저 표시
    # ============================================================================
    st.markdown("### 💡 시간대별 인사이트")
    
    # 00~05시, 13~16시 제외한 데이터만 필터링
    valid_hours = hourly_df[
        ~hourly_df['hour'].isin([0, 1, 2, 3, 4, 5, 13, 14, 15, 16])
    ]
    
    if len(valid_hours) > 0:
        best_hour = valid_hours.loc[valid_hours['median'].idxmax()]
        worst_hour = valid_hours.loc[valid_hours['median'].idxmin()]
        most_stable = valid_hours.loc[valid_hours['cv'].idxmin()]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success(f"""
            **🏆 최고 실적 시간대**
            {best_hour['hour']}시
            중위값: {data_formatter.format_money(best_hour['median'])}
            변동계수: {best_hour['cv']:.1f}%
            가중평균 ROI: {best_hour['weighted_roi']:.1f}%
            """)
        with col2:
            st.warning(f"""
            **📉 최저 실적 시간대**
            {worst_hour['hour']}시
            중위값: {data_formatter.format_money(worst_hour['median'])}
            변동계수: {worst_hour['cv']:.1f}%
            가중평균 ROI: {worst_hour['weighted_roi']:.1f}%
            """)
        with col3:
            st.info(f"""
            **🎯 가장 안정적인 시간대**
            {most_stable['hour']}시
            변동계수: {most_stable['cv']:.1f}%
            중위값: {data_formatter.format_money(most_stable['median'])}
            가중평균 ROI: {most_stable['weighted_roi']:.1f}%
            """)
    
    # ============================================================================
    # 시간대별 매출 차트
    # ============================================================================
    
    if graph_type == "선 그래프":
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 25-75% 구간 표시
        fig1.add_trace(
            go.Scatter(
                x=list(hourly_df['hour']) + list(hourly_df['hour'][::-1]),
                y=list(hourly_df['q75']) + list(hourly_df['q25'][::-1]),
                fill='toself',
                fillcolor='rgba(0, 217, 255, 0.1)',
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=True,
                name='25-75% 구간'
            ),
            secondary_y=False
        )
        
        # 평균값 - 네온 시안
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['mean'],
                mode='lines+markers',
                name='평균값',
                line=dict(color=DARK_NEON_THEME['accent_cyan'], width=3, dash='dash'),
                marker=dict(size=8, color=DARK_NEON_THEME['accent_cyan']),
                # 수정: customdata로 포맷팅된 값 전달
                customdata=[data_formatter.format_money(v, unit='억') for v in hourly_df['mean']],
                hovertemplate='<b>%{x}시</b><br>평균: %{customdata}<extra></extra>'
            ),
            secondary_y=False
        )
        
        # 중위값 - 네온 그린
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['median'],
                mode='lines+markers',
                name='중위값',
                line=dict(color=DARK_NEON_THEME['accent_green'], width=4),
                marker=dict(size=10, color=DARK_NEON_THEME['accent_green']),
                customdata=[data_formatter.format_money(v, unit='억') for v in hourly_df['median']],
                hovertemplate='<b>%{x}시</b><br>중위값: %{customdata}<extra></extra>'
            ),
            secondary_y=False
        )
        
        # 절사평균 - 네온 오렌지 (다시 활성화)
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['trimmed_mean'],
                mode='lines+markers',
                name='절사평균 (20%)',
                line=dict(color=DARK_NEON_THEME['accent_orange'], width=3),
                marker=dict(size=8, color=DARK_NEON_THEME['accent_orange']),
                customdata=[data_formatter.format_money(v, unit='억') for v in hourly_df['trimmed_mean']],
                hovertemplate='<b>%{x}시</b><br>절사평균: %{customdata}<extra></extra>'
            ),
            secondary_y=False
        )
        
        # ROI 라인 추가 - 네온 핑크
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['weighted_roi'],
                mode='lines+markers',
                name='ROI (%)',
                line=dict(color=DARK_NEON_THEME['accent_pink'], width=3),
                marker=dict(size=8, color=DARK_NEON_THEME['accent_pink']),
                hovertemplate='<b>%{x}시</b><br>ROI: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True
        )
        
        # 절사평균 ROI 라인 추가 - 노란색
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['trimmed_roi'],
                mode='lines+markers',
                name='절사평균 ROI (%)',
                line=dict(color='#FFD93D', width=3, dash='dash'),  # 노란색, 점선
                marker=dict(size=8, color='#FFD93D'),
                hovertemplate='<b>%{x}시</b><br>절사평균 ROI: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True
        )
        
        fig1.update_yaxes(title_text="매출액", secondary_y=False, **DARK_CHART_LAYOUT['yaxis'])
        fig1.update_yaxes(title_text="ROI (%)", secondary_y=True, color=DARK_NEON_THEME['accent_pink'])
        
    else:  # 막대 그래프
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 중위값 막대
        fig1.add_trace(
            go.Bar(
                x=hourly_df['hour'],
                y=hourly_df['median'],
                name='중위값',
                marker_color=DARK_NEON_THEME['accent_green'],
                opacity=0.9,
                customdata=[data_formatter.format_money(v, unit='억') for v in hourly_df['median']],
                hovertemplate='<b>%{x}시</b><br>중위값: %{customdata}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 절사평균 막대
        fig1.add_trace(
            go.Bar(
                x=hourly_df['hour'],
                y=hourly_df['trimmed_mean'],
                name='절사평균',
                marker_color=DARK_NEON_THEME['accent_orange'],
                opacity=0.9,
                customdata=[data_formatter.format_money(v, unit='억') for v in hourly_df['trimmed_mean']],
                hovertemplate='<b>%{x}시</b><br>절사평균: %{customdata}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 평균값 마커
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['mean'],
                mode='markers',
                name='평균값',
                marker=dict(
                    symbol='diamond',
                    size=14,
                    color=DARK_NEON_THEME['accent_cyan'],
                    line=dict(color='white', width=2)
                ),
                customdata=[data_formatter.format_money(v, unit='억') for v in hourly_df['mean']],
                hovertemplate='<b>%{x}시</b><br>평균: %{customdata}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # ROI 선 - 네온 핑크
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['weighted_roi'],
                mode='lines+markers',
                name='ROI (%)',
                line=dict(color=DARK_NEON_THEME['accent_pink'], width=3),
                marker=dict(size=8, color=DARK_NEON_THEME['accent_pink']),
                hovertemplate='<b>%{x}시</b><br>ROI: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True,
        )
        
        # 절사평균 ROI 선 - 노란색
        fig1.add_trace(
            go.Scatter(
                x=hourly_df['hour'],
                y=hourly_df['trimmed_roi'],
                mode='lines+markers',
                name='절사평균 ROI (%)',
                line=dict(color='#FFD93D', width=3, dash='dash'),  # 노란색, 점선
                marker=dict(size=8, color='#FFD93D'),
                hovertemplate='<b>%{x}시</b><br>절사평균 ROI: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True,
        )
        
        fig1.update_yaxes(title_text="매출액", secondary_y=False, **DARK_CHART_LAYOUT['yaxis'])
        fig1.update_yaxes(title_text="ROI (%)", secondary_y=True, color=DARK_NEON_THEME['accent_pink'])
        fig1.update_layout(barmode='group')
    
    # 레이아웃 업데이트
    layout_config = get_layout_without_hoverlabel()
    layout_config.update({
        'title': "시간대별 매출 통계 및 ROI 비교",
        'xaxis': dict(
            title="시간대",
            tickmode='array',
            tickvals=list(range(24)),
            ticktext=[f"{i}시" for i in range(24)],
            **DARK_CHART_LAYOUT['xaxis']
        ),
        'height': 500,
        'hovermode': 'x unified',
        'hoverlabel': DARK_CHART_LAYOUT['hoverlabel']
    })
    
    fig1.update_layout(**layout_config)
    st.plotly_chart(fig1, use_container_width=True)
    
    # ============================================================================
    # 포맷팅 함수 정의
    # ============================================================================
    def format_money(value, unit='억'):
        """금액을 포맷팅하는 함수"""
        if pd.isna(value):
            return "0.00억"
        
        if unit == '억':
            formatted = value / 100_000_000
            return f"{formatted:,.2f}억"
        elif unit == '만':
            formatted = value / 10_000
            return f"{formatted:,.0f}만"
        else:
            return f"{value:,.0f}"
    
    # ============================================================================
    # 시간대별 시뮬레이션 분석 - 새로 추가 (2025-01-20) - 수정 v2
    # ============================================================================
    
    # 시간대별 방송정액비 데이터 로드
    @st.cache_data
    def load_broadcasting_costs():
        """시간대별 방송정액비 데이터 로드"""
        try:
            import os
            # 파일 경로 찾기
            excel_files = [f for f in os.listdir('.') if '방송정액비' in f or 'broadcasting' in f.lower()]
            if not excel_files:
                # 인코딩된 파일명 시도
                excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
            
            if excel_files:
                excel_file = excel_files[0]
                df_cost = pd.read_excel(excel_file, sheet_name=None)
                
                # 첫 번째 시트 가져오기
                first_sheet = list(df_cost.values())[0]
                
                # 시간대별 비용 딕셔너리 생성
                hourly_costs = {}
                
                # 헤더 행 찾기 (방송사가 있는 행)
                for idx, row in first_sheet.iterrows():
                    if '방송사' in str(row.values[0]) or idx == 0:
                        # 다음 행부터 데이터
                        for i in range(idx + 1, min(idx + 20, len(first_sheet))):
                            platform = str(first_sheet.iloc[i, 0]).strip()
                            if platform and platform != 'nan':
                                if platform not in hourly_costs:
                                    hourly_costs[platform] = {}
                                # 시간대별 비용 추출 (2열부터 25열까지가 0시~23시)
                                for hour in range(24):
                                    col_idx = hour + 1
                                    if col_idx < len(first_sheet.columns):
                                        cost = first_sheet.iloc[i, col_idx]
                                        if pd.notna(cost):
                                            hourly_costs[platform][hour] = float(cost)
                        break
                
                return hourly_costs
            else:
                # 기본값 반환
                return get_default_broadcasting_costs()
        except Exception as e:
            print(f"방송정액비 로드 에러: {e}")
            return get_default_broadcasting_costs()
    
    def get_default_broadcasting_costs():
        """기본 시간대별 방송정액비"""
        # 평일 기준: 00~05시, 13~16시는 0원
        default_cost = {
            0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0,
            6: 45000000, 7: 70000000, 8: 105000000, 9: 125000000,
            10: 135000000, 11: 145000000, 12: 145000000, 
            13: 0, 14: 0, 15: 0, 16: 0,  # 13~16시 방송비 없음
            17: 105000000,
            18: 125000000, 19: 135000000, 20: 145000000, 21: 145000000,
            22: 135000000, 23: 90000000
        }
        platforms = ['현대홈쇼핑', 'gs홈쇼핑', '롯데홈쇼핑', 'cj온스타일', '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑']
        return {platform: default_cost.copy() for platform in platforms}
    
    # 방송정액비 데이터 로드
    broadcasting_costs = load_broadcasting_costs()
    
    st.markdown("---")
    st.markdown("### 🎯 시간대별 시뮬레이션 분석")
    
    # 데이터 요약 정보 표시 (디버깅용)
    with st.expander("📊 데이터 현황 보기", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("전체 데이터", f"{len(df):,}건")
        with col2:
            st.metric("방송사 수", f"{df['platform'].nunique()}개")
        with col3:
            st.metric("카테고리 수", f"{df['category'].nunique()}개")
        with col4:
            date_range = f"{df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}"
            st.metric("기간", date_range)
        
        # 시간대별 데이터 분포
        st.markdown("**시간대별 전체 데이터 분포:**")
        hour_dist = df['hour'].value_counts().sort_index()
        hour_dist_str = ", ".join([f"{h:02d}시:{c}건" for h, c in hour_dist.items()])
        st.text(hour_dist_str)
        
        # 데이터 컬럼 확인
        st.markdown("**데이터 컬럼 목록:**")
        st.text(f"컬럼: {', '.join(df.columns.tolist())}")
        
        # weekday 컬럼 확인
        if 'weekday' in df.columns:
            st.markdown("**요일 데이터 샘플:**")
            weekday_sample = df['weekday'].value_counts().head(10)
            st.text(f"요일 데이터 타입: {df['weekday'].dtype}")
            st.text(f"요일 종류: {weekday_sample.to_dict()}")
        else:
            st.warning("⚠️ weekday 컬럼이 없습니다. date 컬럼에서 자동 생성됩니다.")
        
        # 방송사별 데이터 분포
        st.markdown("**방송사별 데이터 분포:**")
        platform_dist = df['platform'].value_counts()
        for platform, count in platform_dist.items():
            st.text(f"  {platform}: {count}건")
        
        # 카테고리별 데이터 분포  
        st.markdown("**카테고리별 데이터 분포:**")
        category_dist = df['category'].value_counts()
        for category, count in category_dist.head(10).items():
            st.text(f"  {category}: {count}건")
    
    st.info("""
    **📊 시뮬레이션 분석 설명**
    - 선택한 시간대의 평균/절사평균 매출을 기준으로 순이익을 계산합니다
    - 시간대별 방송정액비와 모델비용을 반영한 정확한 ROI를 산출합니다
    - 여러 시간대를 선택하여 통합 분석이 가능합니다
    - 분석 결과를 저장하여 HTML 보고서로 다운로드할 수 있습니다
    """)
    
    # 세션 상태 초기화
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = []
    
    # 시간대 선택 상태 관리
    if 'hour_selection' not in st.session_state:
        st.session_state.hour_selection = [False] * 24
    
    # 체크박스 초기화 플래그
    if 'should_reset_checkboxes' not in st.session_state:
        st.session_state.should_reset_checkboxes = False
    
    # 체크박스 리셋 처리
    if st.session_state.should_reset_checkboxes:
        st.session_state.hour_selection = [False] * 24
        st.session_state.should_reset_checkboxes = False
    
    # 체크박스 초기화 완료 후 페이지 새로고침
    if 'reset_complete' in st.session_state and st.session_state.reset_complete:
        st.session_state.reset_complete = False
        st.rerun()
    
    # 전체 선택/해제 버튼 (form 외부에 위치)
    st.markdown("#### ⏰ 시간대 선택 도구")
    button_col1, button_col2, button_col3 = st.columns([1, 1, 3])
    with button_col1:
        if st.button("✅ 전체 선택", key="select_all_hours"):
            st.session_state.hour_selection = [True] * 24
            st.rerun()
    with button_col2:
        if st.button("❌ 전체 해제", key="deselect_all_hours"):
            st.session_state.hour_selection = [False] * 24
            st.rerun()
    
    # Form으로 전체를 감싸서 필터/체크박스 클릭시 리로딩 방지
    with st.form(key="simulation_form"):
        # 필터링 섹션
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 2])
        
        with filter_col1:
            # 방송사 선택 - 데이터가 많은 순서로 정렬
            platform_counts = df.groupby('platform').size().sort_values(ascending=False)
            platform_list = platform_counts.index.tolist()
            
            # 방송사가 없는 경우 대비
            if not platform_list:
                platform_list = ['전체']
                
            selected_sim_platform = st.selectbox(
                "방송사",
                platform_list,
                index=0,  # 데이터가 가장 많은 방송사 기본 선택
                key="sim_platform"
            )
        
        with filter_col2:
            # 카테고리 선택
            category_list = ['전체카테고리'] + sorted(df['category'].unique().tolist())
            selected_sim_category = st.selectbox(
                "카테고리",
                category_list,
                index=0,  # 전체카테고리 기본 선택
                key="sim_category"
            )
        
        with filter_col3:
            # 분석기간 시작일
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            # 기본값: 2025년 8월 1일부터
            default_start = pd.to_datetime('2025-08-01') if pd.to_datetime('2025-08-01') >= min_date else min_date
            
            selected_sim_start = st.date_input(
                "분석기간 시작",
                value=default_start,
                min_value=min_date,
                max_value=max_date,
                key="sim_start_date"
            )
        
        with filter_col4:
            # 분석기간 종료일
            selected_sim_end = st.date_input(
                "분석기간 종료",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key="sim_end_date"
            )
        
        # 요일 선택 (평일/주말/전체)
        weekday_col1, weekday_col2 = st.columns([4, 4])
        
        with weekday_col1:
            weekday_options = ['평일', '주말', '전체']
            selected_sim_weekday = st.selectbox(
                "요일 구분",
                weekday_options,
                index=0,  # 평일 기본 선택
                key="sim_weekday"
            )
        
        # 시간대 복수 선택 (체크박스)
        st.markdown("#### ⏰ 시간대 선택 (복수 선택 가능)")
        
        # 6개씩 4행으로 표시
        selected_hours = []
        
        # 각 행마다 새로운 columns 생성
        for row in range(4):  # 4행 (0-5, 6-11, 12-17, 18-23)
            time_cols = st.columns(6)
            for col_idx in range(6):
                hour = row * 6 + col_idx
                if hour < 24:
                    with time_cols[col_idx]:
                        # 세션 상태에서 기본값 가져오기
                        default_value = st.session_state.hour_selection[hour]
                        
                        # 체크박스 생성 및 상태 업데이트
                        is_checked = st.checkbox(
                            f"{hour:02d}시", 
                            key=f"sim_hour_{hour}",  # 키 이름 변경
                            value=default_value
                        )
                        
                        if is_checked:
                            selected_hours.append(hour)
                        
                        # 세션 상태 업데이트
                        st.session_state.hour_selection[hour] = is_checked
        
        # 분석 버튼
        st.markdown("---")
        analyze_button = st.form_submit_button("🔍 분석 시작", type="primary")
    
    # Form 밖에서 초기화 버튼들
    clear_col1, clear_col2, clear_col3 = st.columns([1, 1, 4])
    with clear_col1:
        if st.button("🗑️ 결과 초기화", key="clear_sim"):
            st.session_state.simulation_results = []
            st.rerun()
    
    with clear_col2:
        if st.button("🔄 필터 초기화", key="reset_filters"):
            # 필터를 초기 설정으로 복원
            st.session_state.sim_platform = "전체"
            st.session_state.sim_weekday = "전체"
            st.session_state.sim_category = "전체"
            st.session_state.sim_price_range = "전체"
            st.session_state.sim_product_filter = ""
            st.session_state.hour_selection = [False] * 24  # 시간대 체크 모두 해제
            st.rerun()
    
    # 분석 완료 플래그 확인 - 삭제 (analyze_button 후에서 처리)
    
    # 분석 실행
    if analyze_button:
        if not selected_hours:
            st.warning("⚠️ 최소 1개 이상의 시간대를 선택해주세요.")
        else:
            with st.spinner('분석중입니다...'):
                # 데이터 필터링
                sim_df = df.copy()
                
                # 디버깅 정보 추가
                debug_info = []
                debug_info.append(f"초기 데이터: {len(sim_df)}건")
                
                # 방송사 필터링
                if selected_sim_platform != '전체':
                    sim_df = sim_df[sim_df['platform'] == selected_sim_platform]
                    debug_info.append(f"방송사({selected_sim_platform}) 필터링 후: {len(sim_df)}건")
                
                # 카테고리 필터링
                if selected_sim_category != '전체카테고리':
                    sim_df = sim_df[sim_df['category'] == selected_sim_category]
                    debug_info.append(f"카테고리({selected_sim_category}) 필터링 후: {len(sim_df)}건")
                
                # 날짜 필터링 - 안전한 날짜 변환
                try:
                    start_date = pd.Timestamp(selected_sim_start)
                    end_date = pd.Timestamp(selected_sim_end)
                    # date 컬럼도 timestamp로 변환
                    sim_df['date'] = pd.to_datetime(sim_df['date'])
                    sim_df = sim_df[(sim_df['date'] >= start_date) & 
                                   (sim_df['date'] <= end_date)]
                    debug_info.append(f"날짜({selected_sim_start} ~ {selected_sim_end}) 필터링 후: {len(sim_df)}건")
                except Exception as e:
                    debug_info.append(f"날짜 필터링 오류: {e}")
                    st.error(f"날짜 필터링 중 오류 발생: {e}")
                
                # 요일 필터링
                if selected_sim_weekday != '전체':
                    # weekday 컬럼의 실제 값 확인
                    if 'weekday' in sim_df.columns:
                        unique_weekdays = sim_df['weekday'].unique()
                        debug_info.append(f"요일 데이터 종류: {unique_weekdays[:10]}")  # 처음 10개만 표시
                        
                        # 요일이 숫자인 경우와 한글인 경우 모두 처리
                        if selected_sim_weekday == '평일':
                            # 평일: 월요일(0) ~ 금요일(4)
                            # 숫자인 경우 - dtype 체크 개선
                            if pd.api.types.is_numeric_dtype(sim_df['weekday']):
                                sim_df = sim_df[sim_df['weekday'].isin([0, 1, 2, 3, 4])]
                                debug_info.append(f"숫자형 요일 데이터로 평일 필터링 적용")
                            # 문자열인 경우
                            else:
                                sim_df = sim_df[sim_df['weekday'].isin(['월요일', '화요일', '수요일', '목요일', '금요일', 
                                                                        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                                                                        '월', '화', '수', '목', '금'])]
                                debug_info.append(f"문자형 요일 데이터로 평일 필터링 적용")
                        elif selected_sim_weekday == '주말':
                            # 주말: 토요일(5), 일요일(6)
                            # 숫자인 경우
                            if pd.api.types.is_numeric_dtype(sim_df['weekday']):
                                sim_df = sim_df[sim_df['weekday'].isin([5, 6])]
                                debug_info.append(f"숫자형 요일 데이터로 주말 필터링 적용")
                            # 문자열인 경우
                            else:
                                sim_df = sim_df[sim_df['weekday'].isin(['토요일', '일요일', 
                                                                        'Saturday', 'Sunday',
                                                                        '토', '일'])]
                                debug_info.append(f"문자형 요일 데이터로 주말 필터링 적용")
                    else:
                        # weekday 컬럼이 없는 경우 date에서 생성
                        sim_df['weekday'] = pd.to_datetime(sim_df['date']).dt.dayofweek
                        if selected_sim_weekday == '평일':
                            sim_df = sim_df[sim_df['weekday'] < 5]
                        elif selected_sim_weekday == '주말':
                            sim_df = sim_df[sim_df['weekday'] >= 5]
                    debug_info.append(f"요일({selected_sim_weekday}) 필터링 후: {len(sim_df)}건")
                
                # 디버깅 정보 표시 (접힌 상태)
                with st.expander("🔍 필터링 과정 디버깅", expanded=False):
                    for info in debug_info:
                        st.text(info)
                    
                    # 선택한 시간대의 데이터 분포 확인
                    if len(sim_df) > 0:
                        hour_counts = sim_df['hour'].value_counts().sort_index()
                        st.text(f"\n현재 필터링된 데이터의 시간대별 분포:")
                        for h in selected_hours:
                            count = hour_counts.get(h, 0)
                            st.text(f"  {h:02d}시: {count}건")
                    else:
                        st.error("⚠️ 필터링 후 데이터가 없습니다!")
                
                # 선택한 시간대별 분석
                hour_results = []
                missing_hours = []  # 데이터가 없는 시간대 추적
                insufficient_hours = []  # 데이터가 부족한 시간대 추적
                
                st.write(f"📌 분석 대상 시간대: {', '.join([f'{h:02d}시' for h in selected_hours])}")
                st.write(f"📊 필터링된 총 데이터: {len(sim_df)}건")
                
                if len(sim_df) == 0:
                    st.error("⚠️ 필터링 후 데이터가 없어 분석을 진행할 수 없습니다.")
                    hour_results = []  # 빈 결과로 설정
                else:
                    for hour in selected_hours:
                        hour_data = sim_df[sim_df['hour'] == hour]
                        
                        st.write(f"  - {hour:02d}시: {len(hour_data)}건")  # 각 시간대별 데이터 건수 표시
                        
                        if len(hour_data) == 0:
                            missing_hours.append(hour)
                        elif len(hour_data) >= 1:  # 최소 1건 이상 데이터가 있을 때 분석 (3건에서 1건으로 완화)
                            # 평균 및 절사평균 계산
                            mean_revenue = hour_data['revenue'].mean()
                            # 데이터가 3건 미만인 경우 평균 사용, 그 이상인 경우 절사평균 사용
                            if len(hour_data) < 3:
                                trimmed_mean_revenue = mean_revenue
                                insufficient_hours.append(f"{hour}시 (데이터 {len(hour_data)}건)")
                            else:
                                trimmed_mean_revenue = safe_trim_mean(hour_data['revenue'], 0.2)
                            
                            mean_units = hour_data['units_sold'].mean()
                            if len(hour_data) < 3:
                                trimmed_mean_units = mean_units
                            else:
                                trimmed_mean_units = safe_trim_mean(hour_data['units_sold'], 0.2)
                            
                            # po 컬럼이 있는 경우에만 계산, 없으면 0
                            if 'po' in hour_data.columns:
                                if len(hour_data) < 3:
                                    trimmed_mean_po = hour_data['po'].mean() if len(hour_data) > 0 else 0
                                else:
                                    trimmed_mean_po = safe_trim_mean(hour_data['po'], 0.2)
                            else:
                                trimmed_mean_po = 0
                            
                            # 방송정액비 및 모델비용 계산
                            platform_key = selected_sim_platform.lower().replace('홈쇼핑', '홈쇼핑')
                            
                            # 요일 구분 (평일/주말)
                            is_weekday = selected_sim_weekday == '평일'
                            is_weekend = selected_sim_weekday == '주말'
                            
                            # 방송정액비 계산
                            broadcast_cost = 0
                            if is_weekday:
                                # 평일: 00~05시, 13~16시는 방송비 없음
                                if not (0 <= hour <= 5 or 13 <= hour <= 16):
                                    for platform in broadcasting_costs.keys():
                                        if platform.lower() in platform_key or platform_key in platform.lower():
                                            broadcast_cost = broadcasting_costs.get(platform, {}).get(hour, 0)
                                            break
                                    # 기본값 설정 (못찾은 경우)
                                    if broadcast_cost == 0:
                                        default_costs = get_default_broadcasting_costs()
                                        broadcast_cost = list(default_costs.values())[0].get(hour, 0)
                            else:
                                # 주말 또는 전체: 00~05시만 방송비 없음
                                if not (0 <= hour <= 5):
                                    for platform in broadcasting_costs.keys():
                                        if platform.lower() in platform_key or platform_key in platform.lower():
                                            broadcast_cost = broadcasting_costs.get(platform, {}).get(hour, 0)
                                            break
                                    # 기본값 설정 (못찾은 경우)
                                    if broadcast_cost == 0:
                                        default_costs = get_default_broadcasting_costs()
                                        broadcast_cost = list(default_costs.values())[0].get(hour, 0)
                            
                            # 모델비용 계산
                            if 0 <= hour <= 5:
                                model_cost = 0  # 00시~05시는 모델비용 0원
                            else:
                                # 06시~23시는 모델비용 있음
                                # Live 채널 여부 확인
                                is_live = selected_sim_platform in LIVE_CHANNELS
                                model_cost = MODEL_COST_LIVE if is_live else MODEL_COST_NON_LIVE
                            
                            # 총비용 계산
                            total_cost = broadcast_cost + model_cost
                            
                            # 시간대별 실질 마진율 적용
                            # 방송정액비가 없는 시간대 확인
                            if broadcast_cost == 0:
                                # 방송정액비가 없는 시간대: 수수료율 42%
                                # 실질 마진율 = 전환율(75%) × (1 - 원가율(13%) - 수수료율(42%))
                                # = 0.75 × (1 - 0.13 - 0.42) = 0.75 × 0.45 = 0.3375 (33.75%)
                                margin_rate = REAL_MARGIN_RATE_NO_BROADCAST  # 0.3375
                            else:
                                # 방송정액비가 있는 시간대: 수수료율 10%
                                # 실질 마진율 = 전환율(75%) × (1 - 원가율(13%) - 수수료율(10%))
                                # = 0.75 × (1 - 0.13 - 0.10) = 0.75 × 0.77 = 0.5775 (57.75%)
                                margin_rate = REAL_MARGIN_RATE  # 0.5775
                            
                            # 실질 이익 = 매출 * 시간대별 마진율
                            real_profit = trimmed_mean_revenue * margin_rate
                            mean_profit = mean_revenue * margin_rate
                            
                            # ROI 계산 (총비용이 0인 경우 처리)
                            if total_cost > 0:
                                mean_roi = ((mean_profit - total_cost) / total_cost * 100)
                                trimmed_roi = ((real_profit - total_cost) / total_cost * 100)
                            else:
                                # 비용이 0인 경우 - 이익이 있으면 매우 높은 ROI, 없으면 0
                                if mean_profit > 0:
                                    mean_roi = 999.9  # 9999 대신 999.9로 표시
                                else:
                                    mean_roi = 0
                                
                                if real_profit > 0:
                                    trimmed_roi = 999.9  # 9999 대신 999.9로 표시
                                else:
                                    trimmed_roi = 0
                            
                            # 순이익 계산
                            net_profit = real_profit - total_cost
                            
                            # 방송횟수
                            broadcast_count = len(hour_data)
                            
                            hour_results.append({
                                'hour': hour,
                                'mean_revenue': mean_revenue,
                                'trimmed_mean_revenue': trimmed_mean_revenue,
                                'mean_units': mean_units,
                                'trimmed_mean_units': trimmed_mean_units,
                                'trimmed_mean_po': trimmed_mean_po,
                                'mean_roi': mean_roi,
                                'trimmed_roi': trimmed_roi,
                                'broadcast_cost': broadcast_cost,
                                'model_cost': model_cost,
                                'total_cost': total_cost,
                                'broadcast_count': broadcast_count,
                                'real_profit': real_profit,
                                'net_profit': net_profit,
                                'platform': selected_sim_platform,
                                'category': selected_sim_category,
                                'weekday': selected_sim_weekday,
                                'period': f"{selected_sim_start} ~ {selected_sim_end}"
                            })
                
                if hour_results:
                    # 현재 분석 결과를 세션에 추가
                    current_analysis = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'filters': {
                            'platform': selected_sim_platform,
                            'category': selected_sim_category,
                            'weekday': selected_sim_weekday,
                            'period': f"{selected_sim_start} ~ {selected_sim_end}",
                            'hours': selected_hours
                        },
                        'results': hour_results,
                        'total_mean_revenue': sum([r['mean_revenue'] for r in hour_results]),
                        'total_trimmed_revenue': sum([r['trimmed_mean_revenue'] for r in hour_results]),
                        'total_real_profit': sum([r['real_profit'] for r in hour_results]),
                        'total_net_profit': sum([r['net_profit'] for r in hour_results]),
                        'total_costs': sum([r['total_cost'] for r in hour_results]),
                        'total_broadcasts': sum([r['broadcast_count'] for r in hour_results]),
                        'avg_mean_roi': np.mean([r['mean_roi'] for r in hour_results]),
                        'avg_trimmed_roi': np.mean([r['trimmed_roi'] for r in hour_results])
                    }
                    
                    st.session_state.simulation_results.append(current_analysis)
                    
                    # 체크박스 초기화 (분석 완료 후)
                    st.session_state.hour_selection = [False] * 24
                    
                    # 결과 표시
                    success_msg = f"✅ {len(hour_results)}개 시간대 분석 완료 | 총 순이익: {format_money(current_analysis['total_net_profit'], unit='억')}"
                    st.success(success_msg)
                    
                    # 체크박스 초기화 안내
                    st.info("💡 새로운 분석을 위해서는 위의 **'🔄 필터 초기화'** 버튼을 클릭해주세요.")
                    
                    # 데이터 부족 경고 추가
                    if insufficient_hours:
                        success_msg += f"\n⚠️ 일부 시간대는 데이터가 부족하여 평균값으로 계산됨: {', '.join(insufficient_hours)}"
                    
                    success_msg += "\n\n📌 분석 결과가 아래에 표시됩니다."
                    
                    st.success(success_msg)
                    
                    # 시간대별 분석 결과 표시
                    st.markdown("#### 📊 시간대별 분석 결과")
                    
                    # 카드 표시 (4개씩 한 행에) - Streamlit 네이티브 컴포넌트만 사용
                    for i in range(0, len(hour_results), 4):
                        cols = st.columns(4, gap="small")
                        for j in range(4):
                            if i + j < len(hour_results):
                                result = hour_results[i + j]
                                with cols[j]:
                                    # 수익/손실 판단
                                    is_profit = result['net_profit'] > 0
                                    
                                    # 카드 컨테이너
                                    with st.container():
                                        # 헤더와 순이익/손실
                                        if is_profit:
                                            st.success(f"🟢 **{result['hour']:02d}:00시**")
                                            st.markdown(f"<p style='text-align: center; color: #10F981; font-size: 13px; margin: -10px 0 10px 0;'><b>✨ 순이익: {result['net_profit']/100000000:.3f}억</b></p>", unsafe_allow_html=True)
                                        else:
                                            st.error(f"🔴 **{result['hour']:02d}:00시**")
                                            st.markdown(f"<p style='text-align: center; color: #FF3355; font-size: 13px; margin: -10px 0 10px 0;'><b>⚠️ 순손실: {result['net_profit']/100000000:.3f}억</b></p>", unsafe_allow_html=True)
                                        
                                        # 컴팩트한 정보 표시
                                        # 매출
                                        st.markdown("**📈 매출**", help=None)
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.caption(f"평균: {result['mean_revenue']/100000000:.3f}억")
                                        with col_b:
                                            st.caption(f"절사: {result['trimmed_mean_revenue']/100000000:.3f}억")
                                        
                                        # 수량
                                        st.markdown("**📦 수량**", help=None)
                                        col_c, col_d = st.columns(2)
                                        with col_c:
                                            st.caption(f"평균: {result['mean_units']:.0f}개")
                                        with col_d:
                                            st.caption(f"절사: {result['trimmed_mean_units']:.0f}개")
                                        
                                        # ROI
                                        st.markdown("**💹 ROI**", help=None)
                                        col_e, col_f = st.columns(2)
                                        with col_e:
                                            roi_mean_str = f"{result['mean_roi']:.1f}%"
                                            if result['mean_roi'] > 0:
                                                st.caption(f"평균: :green[{roi_mean_str}]")
                                            else:
                                                st.caption(f"평균: :red[{roi_mean_str}]")
                                        with col_f:
                                            roi_trim_str = f"{result['trimmed_roi']:.1f}%"
                                            if result['trimmed_roi'] > 0:
                                                st.caption(f"절사: :green[{roi_trim_str}]")
                                            else:
                                                st.caption(f"절사: :red[{roi_trim_str}]")
                                        
                                        # 비용
                                        st.markdown("**💰 비용**", help=None)
                                        col_g, col_h = st.columns(2)
                                        with col_g:
                                            st.caption(f"방송: {result['broadcast_cost']/100000000:.3f}억")
                                            st.caption(f"총합: {result['total_cost']/100000000:.3f}억")
                                        with col_h:
                                            st.caption(f"모델: {result['model_cost']/100000000:.3f}억")
                                            st.caption(f"종비: {result.get('trimmed_mean_po', 0)/100000000:.3f}억")
                                        
                                        # 하단 정보
                                        st.caption(f"📺 방송 {result['broadcast_count']}회")
                                        
                                        # 구분선
                                        st.markdown("---")
                    
                    # 종합 인사이트 추가 - st.info로 변경하여 HTML 렌더링 문제 해결
                    st.markdown("---")
                    st.markdown("#### 💡 종합 인사이트")
                    
                    # 최고/최저 성과 시간대 찾기
                    best_hour = max(hour_results, key=lambda x: x['net_profit'])
                    worst_hour = min(hour_results, key=lambda x: x['net_profit'])
                    avg_net_profit = np.mean([r['net_profit'] for r in hour_results])
                    positive_hours = [r for r in hour_results if r['net_profit'] > 0]
                    
                    # 인사이트를 메트릭과 컬럼으로 표시
                    col1, col2 = st.columns(2)
                    with col1:
                        st.success(f"🏆 **최고 성과 시간대: {best_hour.get('hour', 0):02d}:00**")
                        st.write(f"• 순이익: {format_money(best_hour.get('net_profit', 0), unit='억')}")
                        st.write(f"• ROI: {best_hour.get('trimmed_roi', 0):.1f}%")
                        st.write(f"• 방송횟수: {best_hour.get('broadcast_count', 0)}회")
                    
                    with col2:
                        st.error(f"⚠️ **최저 성과 시간대: {worst_hour.get('hour', 0):02d}:00**")
                        st.write(f"• 순이익: {format_money(worst_hour.get('net_profit', 0), unit='억')}")
                        st.write(f"• ROI: {worst_hour.get('trimmed_roi', 0):.1f}%")
                        st.write(f"• 방송횟수: {worst_hour.get('broadcast_count', 0)}회")
                    
                    # 핵심 인사이트 박스
                    with st.info("💎 **핵심 인사이트**"):
                        insights_text = f"""
                        • **수익성:** 분석한 {len(hour_results)}개 시간대 중 {len(positive_hours)}개({len(positive_hours)/len(hour_results)*100:.0f}%)가 수익 발생
                        • **평균 순이익:** 시간대당 평균 {format_money(avg_net_profit, unit='억')} {'(수익)' if avg_net_profit > 0 else '(손실)'}
                        • **최적 시간대:** {', '.join([f"{r.get('hour', 0):02d}시" for r in sorted(positive_hours, key=lambda x: x.get('net_profit', 0), reverse=True)[:3]])} 순으로 높은 수익
                        • **권장사항:** {'수익성 높은 시간대에 집중 편성 권장' if len(positive_hours) > 0 else '전반적인 수익구조 개선 필요'}
                        """
                        st.markdown(insights_text)
                    
                    # 투자 대비 효과
                    total_cost = sum([r['total_cost'] for r in hour_results])
                    total_net_profit = sum([r['net_profit'] for r in hour_results])
                    total_roi = np.mean([r['trimmed_roi'] for r in hour_results])
                    
                    with st.warning(f"💰 **투자 대비 효과**"):
                        st.write(f"• 총 투자비용: {format_money(total_cost, unit='억')}")
                        st.write(f"• 총 순이익: {format_money(total_net_profit, unit='억')}")
                        st.write(f"• 평균 ROI: {total_roi:.1f}%")
                        st.write(f"• 투자 효율성: {'양호' if total_roi > 50 else '보통' if total_roi > 0 else '개선 필요'}")
                    
                    # 분석 완료 메시지만 표시
                    st.success(f"✅ {len(hour_results)}개 시간대 분석 완료")
                else:
                    # 더 상세한 경고 메시지 제공
                    warning_msg = "⚠️ 선택한 조건에 해당하는 데이터가 충분하지 않습니다.\n\n"
                    
                    # 필터링된 데이터의 건수 표시
                    total_filtered_data = len(sim_df)
                    warning_msg += f"📊 필터링된 전체 데이터: {total_filtered_data}건\n"
                    
                    if total_filtered_data > 0:
                        # 시간대별 데이터 분포 표시
                        hour_distribution = sim_df['hour'].value_counts().sort_index()
                        warning_msg += "\n📈 시간대별 데이터 분포:\n"
                        for h in range(24):
                            count = hour_distribution.get(h, 0)
                            if count > 0:
                                warning_msg += f"  - {h:02d}시: {count}건\n"
                        
                        # 선택한 시간대의 데이터 상황
                        warning_msg += f"\n⏰ 선택한 시간대 ({', '.join([f'{h:02d}시' for h in selected_hours])}):\n"
                        if missing_hours:
                            warning_msg += f"  - 데이터가 없는 시간대: {', '.join([f'{h:02d}시' for h in missing_hours])}\n"
                        
                        # 조언 추가
                        warning_msg += "\n💡 **해결 방법:**\n"
                        warning_msg += "1. 다른 시간대를 선택해보세요\n"
                        warning_msg += "2. 분석 기간을 늘려보세요\n"
                        warning_msg += "3. 카테고리 필터를 '전체카테고리'로 변경해보세요\n"
                    else:
                        warning_msg += "\n💡 **해결 방법:**\n"
                        warning_msg += "1. 필터 조건을 확인해주세요 (방송사, 카테고리, 기간)\n"
                        warning_msg += "2. 선택한 기간에 데이터가 있는지 확인해주세요\n"
                    
                    st.warning(warning_msg)
    
    # 통합 대시보드 표시
    if st.session_state.simulation_results:
        st.markdown("---")
        st.markdown("### 📈 통합 대시보드")
        
        # 전체 통계
        total_analyses = len(st.session_state.simulation_results)
        total_trimmed_revenue_sum = sum([a.get('total_trimmed_revenue', a.get('total_revenue', 0)) for a in st.session_state.simulation_results])
        total_net_profit_sum = sum([a.get('total_net_profit', a.get('total_profit', 0)) for a in st.session_state.simulation_results])
        total_costs_sum = sum([a.get('total_costs', 0) for a in st.session_state.simulation_results])
        total_broadcasts_sum = sum([a['total_broadcasts'] for a in st.session_state.simulation_results])
        avg_roi = np.mean([a.get('avg_trimmed_roi', 0) for a in st.session_state.simulation_results])
        
        dash_col1, dash_col2, dash_col3 = st.columns(3)
        
        with dash_col1:
            st.metric("분석 횟수", f"{total_analyses}회")
            st.metric("총 방송 횟수", f"{total_broadcasts_sum}회")
        with dash_col2:
            st.metric("총 예상 매출", format_money(total_trimmed_revenue_sum))
            st.metric("총 비용", format_money(total_costs_sum))
        with dash_col3:
            st.metric("총 순이익", format_money(total_net_profit_sum))
            st.metric("평균 ROI", f"{avg_roi:.1f}%")
        
        # 저장된 분석 내역 표시
        st.markdown("#### 📋 저장된 분석 내역")
        
        for idx, analysis in enumerate(st.session_state.simulation_results, 1):
            with st.expander(f"분석 {idx}: {analysis['timestamp']} - {analysis['filters']['platform']}", expanded=False):
                st.write(f"**필터 조건:**")
                st.write(f"- 방송사: {analysis['filters']['platform']}")
                st.write(f"- 카테고리: {analysis['filters']['category']}")
                st.write(f"- 요일: {analysis['filters']['weekday']}")
                st.write(f"- 기간: {analysis['filters']['period']}")
                st.write(f"- 선택 시간대: {', '.join([f'{h}시' for h in analysis['filters']['hours']])}")
                
                st.write(f"**분석 결과:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"- 평균 매출: {format_money(analysis.get('total_mean_revenue', 0))}")
                    st.write(f"- 절사평균 매출: {format_money(analysis.get('total_trimmed_revenue', analysis.get('total_revenue', 0)))}")
                    st.write(f"- 총 비용: {format_money(analysis.get('total_costs', 0))}")
                with col2:
                    st.write(f"- 실질 이익: {format_money(analysis.get('total_real_profit', analysis.get('total_profit', 0)))}")
                    st.write(f"- 순이익: {format_money(analysis.get('total_net_profit', analysis.get('total_profit', 0)))}")
                    st.write(f"- 평균 ROI: {analysis.get('avg_trimmed_roi', 0):.1f}%")
        
        # HTML 보고서 다운로드 버튼
        if st.button("📥 HTML 보고서 다운로드", key="download_sim_report"):
            html_report = generate_simulation_html_report(
                st.session_state.simulation_results
            )
            
            # 다운로드 버튼
            st.download_button(
                label="💾 보고서 다운로드",
                data=html_report,
                file_name=f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html"
            )
    
    # ============================================================================
    # 방송 내역 조회 테이블 추가 (수정사항 1)
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### 📋 방송 내역 상세 조회")
    
    # 필터 옵션 - 5개 컬럼으로 변경 (요일 필터 추가)
    col1, col2, col3, col4, col5 = st.columns([1.8, 1.5, 1.5, 1.5, 1.2])
    
    # 방송사 목록 추출
    platform_list = ['전체'] + sorted(df['platform'].unique().tolist())
    
    # 요일 목록
    weekday_list = ['전체', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    
    # 시간대 목록
    hour_list = ['전체'] + [f"{i}시" for i in range(24)]
    
    # 카테고리 목록
    category_list = ['전체'] + sorted(df['category'].unique().tolist())
    
    # 정렬 옵션
    sort_options = {
        '매출 (높은순)': ('revenue', False),
        '매출 (낮은순)': ('revenue', True),
        '날짜 (최신순)': ('date', False),
        '날짜 (과거순)': ('date', True),
        'ROI (높은순)': ('roi_calculated', False),
        'ROI (낮은순)': ('roi_calculated', True),
        '판매량 (높은순)': ('units_sold', False),
        '방송사명': ('platform', True),
        '카테고리': ('category', True)
    }
    
    with col1:
        # NS홈쇼핑이 있으면 선택, 없으면 첫 번째 방송사
        default_platform = 'NS홈쇼핑' if 'NS홈쇼핑' in platform_list else platform_list[1] if len(platform_list) > 1 else '전체'
        selected_platform = st.selectbox(
            "방송사 선택",
            platform_list,
            index=platform_list.index(default_platform) if default_platform in platform_list else 0,
            key="broadcast_platform_filter_v16"
        )
    
    with col2:
        selected_weekday = st.selectbox(
            "요일 선택",
            weekday_list,
            index=0,  # 전체 선택 기본값
            key="broadcast_weekday_filter_v16"
        )
    
    with col3:
        selected_hour = st.selectbox(
            "시간대 선택",
            hour_list,
            index=11,  # 10시 선택 (인덱스 11)
            key="broadcast_hour_filter_v16"
        )
    
    with col4:
        selected_category = st.selectbox(
            "카테고리 선택",
            category_list,
            index=0,  # 전체 선택
            key="broadcast_category_filter_v16"
        )
    
    with col5:
        selected_sort = st.selectbox(
            "정렬 방식",
            list(sort_options.keys()),
            index=0,  # 기본값: 매출 (높은순)
            key="broadcast_sort_v16"
        )
    
    # 요일 컬럼 확인 및 변환 (더 강력한 처리)
    try:
        # date 컬럼을 datetime으로 변환
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # weekday_num 생성 (0=월요일, 6=일요일)
        df['weekday_num'] = df['date'].dt.dayofweek
        
        # 한글 요일명 매핑
        weekday_num_map = {
            0: '월요일', 1: '화요일', 2: '수요일',
            3: '목요일', 4: '금요일', 5: '토요일', 6: '일요일'
        }
        
        # weekday 컬럼 생성 또는 재생성
        df['weekday'] = df['weekday_num'].map(weekday_num_map)
        
        # NaN 값 처리 (날짜가 없는 경우)
        df['weekday'] = df['weekday'].fillna('알수없음')
        
    except Exception as e:
        st.warning(f"요일 데이터 처리 중 오류: {e}")
        df['weekday'] = '알수없음'
        df['weekday_num'] = -1
    
    # 분석중 메시지 표시 (화면 전환 없이 현재 위치에서 표시)
    with st.spinner('분석중입니다...'):
        # 데이터 필터링
        filtered_data = df.copy()
        
        if selected_platform != '전체':
            filtered_data = filtered_data[filtered_data['platform'] == selected_platform]
        
        if selected_weekday != '전체':
            filtered_data = filtered_data[filtered_data['weekday'] == selected_weekday]
        
        if selected_hour != '전체':
            hour_num = int(selected_hour.replace('시', ''))
            filtered_data = filtered_data[filtered_data['hour'] == hour_num]
        
        if selected_category != '전체':
            filtered_data = filtered_data[filtered_data['category'] == selected_category]
    
    # 정렬 적용
    sort_col, ascending = sort_options[selected_sort]
    
    # ROI 계산 (가중평균 방식)
    if 'roi_calculated' not in filtered_data.columns:
        filtered_data['roi_calculated'] = filtered_data.apply(
            lambda row: calculate_weighted_roi(pd.DataFrame([row])), axis=1
        )
    
    # 판매가 계산 (단가)
    filtered_data['unit_price'] = filtered_data.apply(
        lambda row: row['revenue'] / row['units_sold'] if row['units_sold'] > 0 else 0, 
        axis=1
    )
    
    # 방송정액비 및 모델비용 계산 추가
    filtered_data['broadcast_cost'] = 0
    filtered_data['model_cost'] = 0
    filtered_data['total_broadcast_cost'] = 0  # 총 방송비용
    
    # 시간대별 방송정액비 적용
    for idx, row in filtered_data.iterrows():
        platform_key = row['platform'].lower()
        hour = row['hour']
        
        # 방송정액비 가져오기
        broadcast_cost = 0
        for platform in broadcasting_costs.keys():
            if platform.lower() in platform_key or platform_key in platform.lower():
                broadcast_cost = broadcasting_costs.get(platform, {}).get(hour, 0)
                break
        
        # 기본값 설정 (못찾은 경우)
        if broadcast_cost == 0 and hour >= 6:
            default_costs = get_default_broadcasting_costs()
            broadcast_cost = list(default_costs.values())[0].get(hour, 0)
        
        # 모델비용 (Live 채널 여부 확인)
        is_live = row['platform'] in LIVE_CHANNELS
        model_cost = MODEL_COST_LIVE if is_live else MODEL_COST_NON_LIVE
        
        filtered_data.at[idx, 'broadcast_cost'] = broadcast_cost
        filtered_data.at[idx, 'model_cost'] = model_cost
        # 총 방송비용 = 방송정액비 + 모델비용
        filtered_data.at[idx, 'total_broadcast_cost'] = broadcast_cost + model_cost
    
    # 정렬 적용
    filtered_data = filtered_data.sort_values(sort_col, ascending=ascending)
    
    # 표시할 컬럼 선택 - 비용 컬럼 추가
    display_columns = ['date', 'time', 'platform', 'broadcast', 'category', 
                      'unit_price', 'revenue', 'units_sold', 'roi_calculated', 
                      'total_broadcast_cost', 'broadcast_cost', 'model_cost']
    
    # 날짜 기준 내림차순 정렬 후 상위 30개만 표시 (스크롤 가능)
    display_df = filtered_data[display_columns].head(30).copy()
    
    # 컬럼명 변경 - 비용 컬럼 추가
    display_df.columns = ['방송날짜', '시간', '방송사명', '방송명', '카테고리', 
                          '판매가', '매출액', '수량', 'ROI(%)', '총방송비용',
                          '방송정액비', '모델비용']
    
    # 포맷팅
    display_df['판매가'] = display_df['판매가'].apply(lambda x: f"{x:,.0f}원" if x > 0 else "-")
    display_df['매출액'] = display_df['매출액'].apply(lambda x: f"{x/100_000_000:.3f}억")
    display_df['수량'] = display_df['수량'].apply(lambda x: f"{x:,.0f}개")
    display_df['ROI(%)'] = display_df['ROI(%)'].apply(lambda x: f"{x:.1f}%")
    display_df['총방송비용'] = display_df['총방송비용'].apply(lambda x: f"{x/100_000_000:.3f}억")
    display_df['방송정액비'] = display_df['방송정액비'].apply(lambda x: f"{x/100_000_000:.3f}억")
    display_df['모델비용'] = display_df['모델비용'].apply(lambda x: f"{x/100_000_000:.3f}억")
    
    # 결과 표시
    st.markdown(f"""
    <div style="background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(0, 217, 255, 0.2);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;">
        <p style="color: white; font-size: 14px; margin: 0;">
            <strong>조회 결과:</strong> 총 {len(filtered_data):,}건 | 
            <strong>총 매출:</strong> {filtered_data['revenue'].sum()/100_000_000:.3f}억 | 
            <strong>평균 ROI:</strong> {calculate_weighted_roi(filtered_data):.1f}%
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 테이블 표시 (스크롤 가능한 높이 설정)
    st.markdown("""
    <style>
    .broadcast-table {
        max-height: 400px;
        overflow-y: auto;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        border: 1px solid rgba(0, 217, 255, 0.2);
    }
    .broadcast-table th {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.2), rgba(124, 58, 237, 0.2));
        color: #FFFFFF;
        font-weight: 600;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid rgba(0, 217, 255, 0.3);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .broadcast-table td {
        padding: 10px 12px;
        color: rgba(255, 255, 255, 0.85);
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .broadcast-table tr:hover {
        background: rgba(0, 217, 255, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # DataFrame을 HTML 테이블로 변환
    html_table = display_df.to_html(
        index=False,
        classes='broadcast-table',
        table_id='broadcast-detail-table',
        escape=False
    )
    
    # HTML 표시
    st.markdown(f'<div class="broadcast-table">{html_table}</div>', unsafe_allow_html=True)
    
    if len(filtered_data) > 30:
        st.info(f"전체 {len(filtered_data)}건 중 상위 30건만 표시됩니다.")

# ============================================================================
# 2. 요일×시간대 히트맵 - 수정: Y축 20% 확대, 절사평균선 추가
# ============================================================================

def _create_weekday_hourly_heatmap_dark_improved_v16(df, data_formatter):
    """요일별 시간대별 히트맵 - 절사평균선 추가 및 세로축 20% 확대"""
    
    # 데이터 타입 확인 및 변환
    df = preprocess_numeric_columns(df.copy())
    
    st.subheader("🗓️ 요일×시간대별 매출 분석")
    
    # 요일 이름 설정
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']
    
    # weekday가 이미 한글인 경우와 숫자인 경우 모두 처리 (더 안전한 방법)
    try:
        # 첫 번째 값으로 타입 판단
        if len(df) > 0:
            first_value = df['weekday'].iloc[0]
            if isinstance(first_value, (int, float)) or (isinstance(first_value, str) and first_value.isdigit()):
                # 숫자인 경우 (0=월요일)
                df['weekday_name'] = df['weekday'].apply(lambda x: weekday_names[int(x)] if pd.notna(x) and int(x) < len(weekday_names) else str(x))
            else:
                # 이미 한글인 경우
                korean_to_short = {
                    '월요일': '월', '화요일': '화', '수요일': '수',
                    '목요일': '목', '금요일': '금', '토요일': '토', '일요일': '일'
                }
                df['weekday_name'] = df['weekday'].map(korean_to_short).fillna(df['weekday'])
        else:
            df['weekday_name'] = df['weekday']
    except Exception as e:
        # 에러 발생 시 기본 처리
        korean_to_short = {
            '월요일': '월', '화요일': '화', '수요일': '수',
            '목요일': '목', '금요일': '금', '토요일': '토', '일요일': '일'
        }
        df['weekday_name'] = df['weekday'].map(korean_to_short).fillna(df['weekday'])
    
    st.info("""
    **📊 분석 설명**
    - **히트맵**: 색상의 진한 정도로 매출 규모를 한눈에 파악
    - **평균값 vs 중위값**: 평균값은 대형 매출의 영향을 받지만, 중위값은 일반적인 매출 수준을 보여줍니다
    - **요일별 패턴**: 주중과 주말의 시간대별 매출 패턴 차이를 분석합니다
    - **ROI 분석**: 가중평균 방식으로 정확한 수익성을 파악합니다
    - **절사평균선**: 상하위 10%를 제외한 평균으로 안정적인 기준선을 제공합니다
    """)
    
    metric_type = st.radio(
        "표시 지표",
        ["평균값", "중위값", "절사평균(20%)", "75% 분위수", "안정적 기댓값"],
        horizontal=True,
        index=0,
        key="precision_heatmap_metric_v16"
    )
    
    # 히트맵 데이터 생성
    if metric_type == "평균값":
        pivot_df = df.pivot_table(
            values='revenue',
            index='hour',
            columns='weekday_name',
            aggfunc='mean',
            fill_value=0
        )
    elif metric_type == "중위값":
        pivot_df = df.pivot_table(
            values='revenue',
            index='hour',
            columns='weekday_name',
            aggfunc='median',
            fill_value=0
        )
    elif metric_type == "절사평균(20%)":
        pivot_df = df.pivot_table(
            values='revenue',
            index='hour',
            columns='weekday_name',
            aggfunc=lambda x: safe_trim_mean(x, 0.2),
            fill_value=0
        )
    elif metric_type == "75% 분위수":
        pivot_df = df.pivot_table(
            values='revenue',
            index='hour',
            columns='weekday_name',
            aggfunc=lambda x: safe_quantile(x, 0.75),
            fill_value=0
        )
    else:  # 안정적 기댓값
        pivot_data = []
        for weekday in weekday_names:
            for hour in range(24):
                data = df[(df['weekday_name'] == weekday) & (df['hour'] == hour)]['revenue']
                if len(data) >= 3:
                    median_val = data.median()
                    trimmed_val = safe_trim_mean(data, 0.2)
                    q75_val = data.quantile(0.75)
                    stable_value = median_val * 0.5 + trimmed_val * 0.3 + q75_val * 0.2
                    pivot_data.append({
                        'weekday_name': weekday,
                        'hour': hour,
                        'value': stable_value
                    })
        
        if pivot_data:
            pivot_df = pd.DataFrame(pivot_data).pivot(
                index='hour', columns='weekday_name', values='value'
            )
        else:
            st.info("데이터가 부족합니다.")
            return
    
    # 컬럼 순서 정렬
    pivot_df = pivot_df.reindex(columns=weekday_names, fill_value=0)
    
    # 절사평균 계산 (히트맵 전체 데이터의 상하위 10% 제외)
    all_values = pivot_df.values.flatten()
    trimmed_mean_value = safe_trim_mean(all_values[all_values > 0], 0.1) if len(all_values[all_values > 0]) > 0 else 0
    
    text_values = [[data_formatter.format_money(val) if val > 0 else "" 
                   for val in row] for row in pivot_df.values]
    
    # Dark Mode 네온 컬러스케일
    dark_neon_colorscale = [
        [0, 'rgba(5, 5, 17, 1)'],           # 거의 검정
        [0.2, 'rgba(124, 58, 237, 0.3)'],   # 어두운 퍼플
        [0.4, 'rgba(0, 217, 255, 0.4)'],    # 어두운 시안
        [0.6, 'rgba(16, 249, 129, 0.5)'],   # 밝은 그린
        [0.8, 'rgba(255, 215, 61, 0.6)'],   # 밝은 옐로우
        [1, '#FF3355']                       # 네온 레드
    ]
    
    # 히트맵 그리기
    fig = go.Figure()
    
    # 히트맵 추가
    fig.add_trace(go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=[f"{i}시" for i in pivot_df.index],
        colorscale=dark_neon_colorscale,
        text=text_values,
        texttemplate='%{text}',
        textfont={"size": 14, "color": DARK_NEON_THEME['text_primary']},
        hovertemplate='%{y} %{x}요일<br>%{text}<extra></extra>',
        xgap=0,
        ygap=0,
        colorbar=dict(
            title=dict(
                text=f"{metric_type}",
                font=dict(color=DARK_NEON_THEME['text_primary'], size=14)
            ),
            tickfont=dict(color=DARK_NEON_THEME['text_primary'], size=12),
            thickness=20,
            len=0.7,
            bgcolor='rgba(0, 0, 0, 0)',
            bordercolor=DARK_NEON_THEME['accent_cyan']
        )
    ))
    
    # 절사평균선 제거 (요청사항에 따라 삭제)
    
    # 레이아웃 업데이트
    layout_config = get_layout_without_hoverlabel()
    layout_config.update({
        'title': f"요일×시간대별 {metric_type}",
        'xaxis': dict(
            side="bottom", 
            color=DARK_NEON_THEME['text_primary'],
            tickfont=dict(size=13, color=DARK_NEON_THEME['text_primary']),
            showgrid=False,
            zeroline=False,
            showline=False
        ),
        'yaxis': dict(
            autorange="reversed", 
            color=DARK_NEON_THEME['text_primary'],
            tickfont=dict(size=13, color=DARK_NEON_THEME['text_primary']),
            showgrid=False,
            zeroline=False,
            showline=False
        ),
        'height': 600,
        'hoverlabel': DARK_CHART_LAYOUT['hoverlabel']
    })
    
    fig.update_layout(**layout_config)
    st.plotly_chart(fig, use_container_width=True)
    
    # 추가 분석 그래프 1: 요일별 시간대 매출 추이 비교 (Y축 20% 확대)
    st.markdown("### 📈 요일별 시간대 매출 추이 비교")
    
    # 요일 선택 - 모든 요일 기본 선택
    selected_days = st.multiselect(
        "비교할 요일 선택",
        options=weekday_names,
        default=['월', '화', '수', '목', '금', '토', '일'],
        key="weekday_comparison_v16"
    )
    
    if selected_days:
        fig2 = go.Figure()
        
        # 네온 색상 리스트
        neon_colors = [DARK_NEON_THEME['accent_cyan'], DARK_NEON_THEME['accent_green'], 
                      DARK_NEON_THEME['accent_red'], DARK_NEON_THEME['accent_orange'], 
                      DARK_NEON_THEME['accent_purple'], DARK_NEON_THEME['accent_teal'], 
                      DARK_NEON_THEME['accent_pink']]
        
        # 요일별 라인 추가
        all_values = []
        for idx, day_name in enumerate(selected_days):
            day_data = df[df['weekday_name'] == day_name].groupby('hour')['revenue'].mean()
            all_values.extend(day_data.values)
            
            # 수정: customdata로 포맷팅된 값 전달
            hover_values = [data_formatter.format_money(v, unit='억') for v in day_data.values]
            
            # 평균값 실선
            fig2.add_trace(go.Scatter(
                x=list(range(24)),
                y=day_data.values,
                mode='lines+markers',
                name=f'{day_name}요일',
                line=dict(color=neon_colors[idx % len(neon_colors)], width=3),
                marker=dict(size=8, color=neon_colors[idx % len(neon_colors)]),
                customdata=hover_values,
                hovertemplate='<b>%{fullData.name} %{x}시</b><br>매출: %{customdata}<extra></extra>'
            ))
        
        # 시간별 평균선 추가 (점선)
        hourly_mean = df.groupby('hour')['revenue'].mean()
        hover_mean = [data_formatter.format_money(v, unit='억') for v in hourly_mean.values]
        
        fig2.add_trace(go.Scatter(
            x=list(range(24)),
            y=hourly_mean.values,
            mode='lines',
            name='시간별 평균',
            line=dict(
                color='#10F981',
                width=3,
                dash='dash'
            ),
            opacity=0.8,
            customdata=hover_mean,
            hovertemplate='시간별 평균<br>%{customdata}<extra></extra>'
        ))
        
        # 시간별 절사평균 추가 (수정사항 2)
        hourly_trimmed = []
        for hour in range(24):
            hour_data = df[df['hour'] == hour]['revenue']
            if len(hour_data) >= 5:
                trimmed = safe_trim_mean(hour_data, 0.2)
            else:
                trimmed = hour_data.mean() if len(hour_data) > 0 else 0
            hourly_trimmed.append(trimmed)
        
        hover_trimmed = [data_formatter.format_money(v, unit='억') for v in hourly_trimmed]
        
        fig2.add_trace(go.Scatter(
            x=list(range(24)),
            y=hourly_trimmed,
            mode='lines',
            name='시간별 절사평균',
            line=dict(
                color='#FFD93D',
                width=3,
                dash='dot'
            ),
            opacity=0.8,
            customdata=hover_trimmed,
            hovertemplate='시간별 절사평균<br>%{customdata}<extra></extra>'
        ))
        
        # Y축 범위 계산 (20% 확대)
        if all_values:
            y_min = min(all_values)
            y_max = max(all_values)
            y_range = y_max - y_min
            y_expanded_min = max(0, y_min - (y_range * 0.2))  # 20% 아래 여백
            y_expanded_max = y_max + (y_range * 0.2)  # 20% 위 여백
        else:
            y_expanded_min = 0
            y_expanded_max = 100000000
        
        # 레이아웃 업데이트
        layout_config2 = get_layout_without_hoverlabel()
        layout_config2.update({
            'title': "요일별 시간대 매출 추이 (평균값 + 시간별 평균 + 시간별 절사평균)",
            'xaxis': dict(
                title="시간대",
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i}시" for i in range(24)],
                **DARK_CHART_LAYOUT['xaxis']
            ),
            'yaxis': dict(
                title="매출액",
                range=[y_expanded_min, y_expanded_max],  # 20% 확대된 범위
                **DARK_CHART_LAYOUT['yaxis']
            ),
            'height': 600,  # 높이도 증가
            'hovermode': 'x unified',
            'legend': dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                font=dict(size=11, color=DARK_NEON_THEME['text_primary']),
                bgcolor='rgba(0, 0, 0, 0)',
                bordercolor='rgba(255, 255, 255, 0.1)'
            ),
            'hoverlabel': DARK_CHART_LAYOUT['hoverlabel']
        })
        
        fig2.update_layout(**layout_config2)
        st.plotly_chart(fig2, use_container_width=True)
    
    # 추가 분석 그래프 2: 요일별 시간대 ROI 추이 비교 (세로축 세분화)
    st.markdown("### 📊 요일별 시간대 ROI 추이 비교")
    
    # 요일 선택 - 월-금 기본 선택
    selected_days_roi = st.multiselect(
        "비교할 요일 선택",
        options=weekday_names,
        default=['월', '화', '수', '목', '금'],
        key="weekday_roi_comparison_v16"
    )
    
    if selected_days_roi:
        fig3 = go.Figure()
        
        all_roi_values = []
        # 요일별 ROI 라인 추가
        for idx, day_name in enumerate(selected_days_roi):
            # 시간대별 가중평균 ROI 계산
            hourly_roi = []
            hours = []
            for hour in range(24):
                hour_day_data = df[(df['weekday_name'] == day_name) & (df['hour'] == hour)]
                if len(hour_day_data) > 0:
                    weighted_roi = calculate_weighted_roi(hour_day_data)
                    hourly_roi.append(weighted_roi)
                    hours.append(hour)
                    all_roi_values.append(weighted_roi)
            
            # ROI 라인 추가
            if hourly_roi:
                fig3.add_trace(go.Scatter(
                    x=hours,
                    y=hourly_roi,
                    mode='lines+markers',
                    name=f'{day_name}요일 ROI',
                    line=dict(color=neon_colors[idx % len(neon_colors)], width=3),
                    marker=dict(size=8, color=neon_colors[idx % len(neon_colors)]),
                    hovertemplate='<b>%{fullData.name} %{x}시</b><br>ROI: %{y:.1f}%<extra></extra>'
                ))
        
        # 시간별 평균 ROI 추가 (점선)
        hourly_avg_roi = []
        for hour in range(24):
            hour_data = df[df['hour'] == hour]
            if len(hour_data) > 0:
                weighted_roi = calculate_weighted_roi(hour_data)
                hourly_avg_roi.append(weighted_roi)
                all_roi_values.append(weighted_roi)
            else:
                hourly_avg_roi.append(0)
        
        # 시간별 평균 ROI 라인 추가
        fig3.add_trace(go.Scatter(
            x=list(range(24)),
            y=hourly_avg_roi,
            mode='lines',
            name='시간별 평균 ROI',
            line=dict(
                color='#FFD93D',
                width=4,
                dash='dash'
            ),
            opacity=0.9,
            hovertemplate='시간별 평균 ROI<br>%{y:.1f}%<extra></extra>'
        ))
        
        # 0% 기준선 추가
        fig3.add_hline(
            y=0, 
            line_dash="solid", 
            line_color="rgba(255, 255, 255, 0.3)",
            line_width=1
        )
        
        # 레이아웃 업데이트 (ROI Y축 세분화)
        layout_config3 = get_layout_without_hoverlabel()
        layout_config3.update({
            'title': "요일별 시간대 ROI 추이 (가중평균)",
            'xaxis': dict(
                title="시간대",
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i}시" for i in range(24)],
                **DARK_CHART_LAYOUT['xaxis']
            ),
            'yaxis': dict(
                title="ROI (%)",
                range=[-100, 100],  # 고정 범위
                dtick=20,  # 20 단위로 세분화 (수정사항)
                tickmode='linear',
                tickformat='.0f',
                gridcolor='rgba(255, 255, 255, 0.1)',  # 그리드 더 진하게
                zeroline=True,
                zerolinecolor='rgba(255, 255, 255, 0.3)',
                zerolinewidth=2
            ),
            'height': 600,  # 높이도 600으로 통일
            'hovermode': 'x unified',
            'legend': dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                font=dict(size=11, color=DARK_NEON_THEME['text_primary']),
                bgcolor='rgba(0, 0, 0, 0)',
                bordercolor='rgba(255, 255, 255, 0.1)'
            ),
            'hoverlabel': DARK_CHART_LAYOUT['hoverlabel']
        })
        
        fig3.update_layout(**layout_config3)
        st.plotly_chart(fig3, use_container_width=True)

# ============================================================================
# 3. 가격대별 효율성 분석 - 수정: 평균선 추가, 방송 횟수 표시
# ============================================================================

def _create_price_efficiency_analysis_dark_improved_v16(df, data_formatter, platform_colors, category_colors):
    """가격대별 매출 효율성 분석 - 평균선 및 방송 횟수 추가"""
    
    # 데이터 타입 확인 및 변환
    df = preprocess_numeric_columns(df.copy())
    
    st.subheader("💰 가격대별 매출 효율성 분석")
    
    st.info(f"""
    **📊 분석 설명** 
    - **분석 범위**: 3만원-19만원 구간의 상품만 분석 (주력 가격대)
    - **효율성 점수**: 방송당 평균 매출액과 판매수량을 중심으로 평가
    - **목적**: 가장 효율적인 가격대를 발견하여 상품 기획에 활용
    - **ROI 계산**: 실질 마진율 {REAL_MARGIN_RATE:.2%} 적용 (가중평균)
    """)
    
    # 단가 계산
    df_analysis = df.copy()
    df_analysis['unit_price'] = df_analysis['revenue'] / df_analysis['units_sold']
    df_analysis = df_analysis[df_analysis['unit_price'] > 0]
    
    # 3만원-19만원 구간만 필터링 (19~20만원 제외)
    df_analysis = df_analysis[(df_analysis['unit_price'] >= 30000) & 
                             (df_analysis['unit_price'] < 190000)]
    
    if len(df_analysis) == 0:
        st.warning("3만원-19만원 구간의 데이터가 없습니다.")
        return
    
    # 가격 구간 정의 (3만원부터 19만원까지 1만원 단위)
    price_bins = list(range(30000, 200000, 10000))
    
    price_labels = []
    for i in range(len(price_bins)-1):
        if price_bins[i+1] <= 190000:  # 19만원까지만 라벨 생성
            price_labels.append(f"{price_bins[i]//10000}-{price_bins[i+1]//10000}만원")
    
    df_analysis['price_range'] = pd.cut(df_analysis['unit_price'], bins=price_bins, labels=price_labels)
    
    # 가격대별 효율성 계산
    price_efficiency = pd.DataFrame()
    
    for label in price_labels:
        range_data = df_analysis[df_analysis['price_range'] == label]
        if len(range_data) > 0:
            # 가중평균 ROI 계산
            weighted_roi = calculate_weighted_roi(range_data)
            
            # 평균 계산 (방송당 평균)
            avg_revenue = range_data['revenue'].mean()
            avg_units = range_data['units_sold'].mean()
            
            # 데이터 검증
            total_revenue = range_data['revenue'].sum()
            broadcast_count = len(range_data)
            
            # 평균값 검증 (총합 / 방송횟수와 일치하는지)
            verified_avg_revenue = total_revenue / broadcast_count if broadcast_count > 0 else 0
            verified_avg_units = range_data['units_sold'].sum() / broadcast_count if broadcast_count > 0 else 0
            
            price_efficiency = pd.concat([price_efficiency, pd.DataFrame({
                'price_range': [label],
                '총매출': [total_revenue],
                '평균매출': [verified_avg_revenue],  # 검증된 평균 사용
                '총판매량': [range_data['units_sold'].sum()],
                '평균판매량': [verified_avg_units],  # 검증된 평균 사용
                '가중평균ROI': [weighted_roi],
                '방송횟수': [broadcast_count]
            })])
    
    if len(price_efficiency) == 0:
        st.warning("분석할 데이터가 부족합니다.")
        return
    
    price_efficiency = price_efficiency.set_index('price_range')
    
    # 방송당 평균 계산
    price_efficiency['방송당매출'] = price_efficiency['총매출'] / price_efficiency['방송횟수'].replace(0, 1)
    price_efficiency['방송당판매량'] = price_efficiency['총판매량'] / price_efficiency['방송횟수'].replace(0, 1)
    
    # 효율성 점수 계산
    max_rev_per_broadcast = price_efficiency['방송당매출'].max() if price_efficiency['방송당매출'].max() > 0 else 1
    max_units_per_broadcast = price_efficiency['방송당판매량'].max() if price_efficiency['방송당판매량'].max() > 0 else 1
    
    price_efficiency['효율성점수'] = (
        (price_efficiency['방송당매출'] / max_rev_per_broadcast) * 50 +
        (price_efficiency['방송당판매량'] / max_units_per_broadcast) * 30 +
        (price_efficiency['가중평균ROI'] / 100).clip(upper=1) * 20
    )
    
    # 그래프 1: 가격대별 총매출, 방송횟수, ROI
    st.markdown("### 📊 가격대별 총매출 및 방송횟수")
    
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 총매출 막대
    revenue_hover = []
    avg_revenue_list = []
    avg_units_list = []
    
    for idx, row in price_efficiency.iterrows():
        revenue_hover.append(data_formatter.format_money(row['총매출'], unit='억'))
        avg_revenue_list.append(data_formatter.format_money(row['평균매출']))
        avg_units_list.append(f"{row['평균판매량']:.0f}개")
    
    fig1.add_trace(
        go.Bar(
            x=price_efficiency.index,
            y=price_efficiency['총매출'],
            marker_color=DARK_NEON_THEME['accent_cyan'],
            text=[data_formatter.format_money_short(val) for val in price_efficiency['총매출']],
            textposition='outside',
            name='총매출',
            marker=dict(
                line=dict(color='rgba(255, 255, 255, 0.2)', width=1)
            ),
            customdata=list(zip(revenue_hover, avg_revenue_list, avg_units_list)),
            hovertemplate='<b>%{x}</b><br>총매출: %{customdata[0]}<br>' +
                         '평균매출: %{customdata[1]}<br>' +
                         '평균판매량: %{customdata[2]}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # 평균매출 라인 (스케일 개선)
    avg_revenue_scaled = price_efficiency['평균매출'].values
    max_total_revenue = price_efficiency['총매출'].max()
    avg_revenue_max = price_efficiency['평균매출'].max()
    
    # 평균매출을 총매출의 30% 정도 스케일로 조정
    if avg_revenue_max > 0:
        scale_factor = (max_total_revenue * 0.3) / avg_revenue_max
        avg_revenue_display = avg_revenue_scaled * scale_factor
    else:
        avg_revenue_display = avg_revenue_scaled
    
    fig1.add_trace(
        go.Scatter(
            x=price_efficiency.index,
            y=avg_revenue_display,
            mode='lines+markers',
            name='평균매출',
            line=dict(color='#FFD93D', width=3, dash='dash'),
            marker=dict(size=8, color='#FFD93D'),
            customdata=[data_formatter.format_money(val) for val in price_efficiency['평균매출']],
            hovertemplate='<b>%{x}</b><br>평균매출: %{customdata}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # 평균판매량 라인 (색상 변경: 녹색 -> 보라색)
    # 판매량을 적절한 스케일로 조정
    max_units = price_efficiency['평균판매량'].max()
    if max_units > 0:
        units_scale_factor = (max_total_revenue * 0.2) / max_units
        units_display = price_efficiency['평균판매량'] * units_scale_factor
    else:
        units_display = price_efficiency['평균판매량']
    
    fig1.add_trace(
        go.Scatter(
            x=price_efficiency.index,
            y=units_display,
            mode='lines+markers',
            name='평균판매량',
            line=dict(color='#9370DB', width=3, dash='dot'),  # 보라색으로 변경
            marker=dict(size=8, color='#9370DB'),
            text=[f"{val:.0f}개" for val in price_efficiency['평균판매량']],
            textposition='top center',
            hovertemplate='<b>%{x}</b><br>평균판매량: %{text}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # 방송횟수 라인
    fig1.add_trace(
        go.Scatter(
            x=price_efficiency.index,
            y=price_efficiency['방송횟수'],
            mode='lines+markers',
            name='방송횟수',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=10, color='#FF6B6B'),
            text=[f"{val}회" for val in price_efficiency['방송횟수']],
            textposition='top center',
            hovertemplate='<b>%{x}</b><br>방송횟수: %{y}회<extra></extra>'
        ),
        secondary_y=True
    )
    
    # 가중평균 ROI 라인 (더 나은 스케일링)
    roi_values = price_efficiency['가중평균ROI'].values
    roi_min = roi_values.min()
    roi_max = roi_values.max()
    roi_range = roi_max - roi_min
    
    # ROI를 secondary_y에 맞게 스케일 조정
    if roi_range > 0:
        # 방송횟수와 비슷한 스케일로 조정
        max_broadcast = price_efficiency['방송횟수'].max()
        roi_scaled = ((roi_values - roi_min) / roi_range) * max_broadcast * 0.8 + max_broadcast * 0.1
    else:
        roi_scaled = roi_values
    
    fig1.add_trace(
        go.Scatter(
            x=price_efficiency.index,
            y=roi_scaled,
            mode='lines+markers',
            name='가중평균 ROI (%)',
            line=dict(color=DARK_NEON_THEME['accent_teal'], width=3),  # 틸 색상으로 변경
            marker=dict(size=10, color=DARK_NEON_THEME['accent_teal'], symbol='diamond'),
            text=[f"{val:.1f}%" for val in price_efficiency['가중평균ROI']],
            textposition='bottom center',
            hovertemplate='<b>%{x}</b><br>ROI: %{text}<extra></extra>'
        ),
        secondary_y=True
    )
    
    # Y축 범위 계산 (20% 확대)
    y_min = 0
    y_max = price_efficiency['총매출'].max()
    y_range = y_max - y_min
    y_expanded_max = y_max + (y_range * 0.2)  # 20% 위 여백
    
    fig1.update_xaxes(
        title_text="가격대",
        tickangle=-45,
        **DARK_CHART_LAYOUT['xaxis']
    )
    fig1.update_yaxes(
        title_text="총매출액",
        secondary_y=False,
        range=[y_min, y_expanded_max],  # 20% 확대
        **DARK_CHART_LAYOUT['yaxis']
    )
    fig1.update_yaxes(
        title_text="방송횟수 / ROI (%)",
        secondary_y=True,
        color=DARK_NEON_THEME['accent_red']
    )
    
    # 레이아웃 업데이트
    layout_config1 = get_layout_without_hoverlabel()
    layout_config1.update({
        'height': 600,  # 높이 20% 증가
        'hovermode': 'x unified',
        'showlegend': True,
        'legend': dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        'hoverlabel': DARK_CHART_LAYOUT['hoverlabel']
    })
    
    fig1.update_layout(**layout_config1)
    st.plotly_chart(fig1, use_container_width=True)
    
    # 그래프 2: 방송당 평균 지표 + 방송횟수
    st.markdown("### 📈 가격대별 방송당 평균 지표 및 방송횟수")
    
    fig2 = make_subplots(
        specs=[[{"secondary_y": True}]],
        subplot_titles=['방송당 평균 지표 및 방송횟수']
    )
    
    # 방송당 매출 막대 (수정: customdata 추가)
    revenue_per_broadcast = [data_formatter.format_money(val, unit='억') for val in price_efficiency['방송당매출']]
    
    fig2.add_trace(
        go.Bar(
            x=price_efficiency.index,
            y=price_efficiency['방송당매출'],
            name='방송당 평균 매출',
            marker_color=DARK_NEON_THEME['accent_orange'],
            text=[data_formatter.format_money_short(val) for val in price_efficiency['방송당매출']],
            textposition='outside',
            customdata=revenue_per_broadcast,
            hovertemplate='<b>%{x}</b><br>방송당 매출: %{customdata}<extra></extra>'
        ),
        secondary_y=False,
    )
    
    # 방송횟수 라인 추가 (수정사항: 새로 추가)
    fig2.add_trace(
        go.Scatter(
            x=price_efficiency.index,
            y=price_efficiency['방송횟수'],
            mode='lines+markers+text',
            name='방송횟수',
            line=dict(color='#7C3AED', width=3, dash='dot'),  # 보라색 점선
            marker=dict(size=8, symbol='diamond', color='#7C3AED'),
            text=[f"{val}회" for val in price_efficiency['방송횟수']],
            textposition='bottom center',
            textfont=dict(size=9, color='#7C3AED'),
            hovertemplate='<b>%{x}</b><br>방송횟수: %{y}회<extra></extra>'
        ),
        secondary_y=True
    )
    
    # 방송당 평균 판매량 선
    fig2.add_trace(
        go.Scatter(
            x=price_efficiency.index,
            y=price_efficiency['방송당판매량'],
            mode='lines+markers',
            name='방송당 평균 판매량',
            marker=dict(size=12, color=DARK_NEON_THEME['accent_green']),
            line=dict(color=DARK_NEON_THEME['accent_green'], width=3),
            hovertemplate='<b>%{x}</b><br>방송당 판매량: %{y:,.0f}개<extra></extra>'
        ),
        secondary_y=True,
    )
    
    # Y축 설정
    fig2.update_xaxes(
        title_text="가격대", 
        tickangle=-45,
        **DARK_CHART_LAYOUT['xaxis']
    )
    fig2.update_yaxes(
        title_text="방송당 평균 매출",
        secondary_y=False,
        tickformat=',.0f'
    )
    fig2.update_yaxes(
        title_text="방송횟수 / 판매량",
        secondary_y=True,
        color='#7C3AED',
        tickformat='.0f'
    )
    
    # 레이아웃 업데이트
    layout_config2 = get_layout_without_hoverlabel()
    layout_config2.update({
        'height': 600,  # 높이 증가
        'hovermode': 'x unified',
        'hoverlabel': DARK_CHART_LAYOUT['hoverlabel']
    })
    
    fig2.update_layout(**layout_config2)
    st.plotly_chart(fig2, use_container_width=True)
    
    # 효율성 인사이트 (수정사항: 상세화)
    st.markdown("##### 📈 가격대별 효율성 심층 분석")
    
    if len(price_efficiency) > 0:
        best_price_range = price_efficiency['효율성점수'].idxmax()
        best_data = price_efficiency.loc[best_price_range]
        
        # 평균값 계산
        avg_roi = price_efficiency['가중평균ROI'].mean()
        avg_revenue_per = price_efficiency['방송당매출'].mean()
        avg_units_per = price_efficiency['방송당판매량'].mean()
        
        # HTML 렌더링 문제 해결 - 스타일과 컨텐츠 분리
        st.markdown("""
        <style>
        .efficiency-analysis-card {
            background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1));
            border: 2px solid #00D9FF;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            color: white;
        }
        .efficiency-analysis-title {
            color: #00D9FF;
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .efficiency-analysis-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .efficiency-analysis-section h4 {
            color: white;
            margin: 0 0 10px 0;
        }
        .efficiency-analysis-section ul {
            color: rgba(255,255,255,0.9);
            line-height: 1.8;
            list-style-type: disc;
            padding-left: 20px;
        }
        .efficiency-analysis-section strong {
            color: #00D9FF;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # HTML 내용 (분리된 버전)
        html_content = f"""
        <div class="efficiency-analysis-card">
            <div class="efficiency-analysis-title">
                🏆 최고 효율 가격대: {best_price_range}
            </div>
            <div class="efficiency-analysis-grid">
                <div class="efficiency-analysis-section">
                    <h4>📊 핵심 지표</h4>
                    <ul>
                        <li>효율성 점수: <strong>{best_data['효율성점수']:.1f}점</strong></li>
                        <li>방송당 매출: <strong>{data_formatter.format_money(best_data['방송당매출'])}</strong></li>
                        <li>가중평균 ROI: <strong>{best_data['가중평균ROI']:.1f}%</strong></li>
                        <li>방송당 판매량: <strong>{best_data['방송당판매량']:.0f}개</strong></li>
                        <li>총 방송횟수: <strong>{best_data['방송횟수']:.0f}회</strong></li>
                    </ul>
                </div>
                <div class="efficiency-analysis-section">
                    <h4>📈 평균 대비 성과</h4>
                    <ul>
                        <li>ROI: 평균 대비 <strong>{'+' if best_data['가중평균ROI'] > avg_roi else ''}{best_data['가중평균ROI'] - avg_roi:.1f}%p</strong></li>
                        <li>방송당 매출: 평균 대비 <strong>{((best_data['방송당매출']/avg_revenue_per - 1) * 100):.1f}%</strong></li>
                        <li>방송당 판매: 평균 대비 <strong>{((best_data['방송당판매량']/avg_units_per - 1) * 100):.1f}%</strong></li>
                    </ul>
                </div>
            </div>
        </div>
        """
        
        # HTML 렌더링
        st.markdown(html_content, unsafe_allow_html=True)
        
        # 추가: Streamlit 메트릭 카드로 보완
        st.markdown("---")
        metric_cols = st.columns(4)
        
        with metric_cols[0]:
            st.metric(
                label="효율성 점수",
                value=f"{best_data['효율성점수']:.1f}점",
                delta="최고 효율"
            )
        
        with metric_cols[1]:
            revenue_perf = ((best_data['방송당매출']/avg_revenue_per - 1) * 100)
            st.metric(
                label="방송당 매출",
                value=data_formatter.format_money_short(best_data['방송당매출']),
                delta=f"{revenue_perf:+.1f}%"
            )
        
        with metric_cols[2]:
            roi_diff = best_data['가중평균ROI'] - avg_roi
            st.metric(
                label="가중평균 ROI",
                value=f"{best_data['가중평균ROI']:.1f}%",
                delta=f"{roi_diff:+.1f}%p"
            )
        
        with metric_cols[3]:
            st.metric(
                label="방송 횟수",
                value=f"{best_data['방송횟수']:.0f}회",
                delta="검증완료" if best_data['방송횟수'] > 20 else "추가필요"
            )
        
        # 상세 분석 및 개선 방안
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💡 성공 요인 분석")
            
            success_factors = []
            
            # ROI 기반 분석
            if best_data['가중평균ROI'] > 70:
                success_factors.append("✅ **탁월한 수익성**: 업계 최고 수준의 ROI 달성")
            elif best_data['가중평균ROI'] > 50:
                success_factors.append("✅ **우수한 수익성**: 안정적인 수익 창출 가능")
            elif best_data['가중평균ROI'] > 30:
                success_factors.append("⚠️ **보통 수익성**: 개선 여지 존재")
            else:
                success_factors.append("❌ **낮은 수익성**: 긴급 개선 필요")
            
            # 판매량 기반 분석
            if best_data['방송당판매량'] > 150:
                success_factors.append("✅ **높은 구매 전환율**: 고객 니즈 정확히 포착")
            elif best_data['방송당판매량'] > 100:
                success_factors.append("✅ **양호한 판매 성과**: 안정적 수요 확보")
            else:
                success_factors.append("⚠️ **판매 개선 필요**: 상품력 강화 검토")
            
            # 데이터 신뢰도
            if best_data['방송횟수'] > 50:
                success_factors.append("✅ **높은 신뢰도**: 충분한 데이터로 검증 완료")
            elif best_data['방송횟수'] > 20:
                success_factors.append("⚠️ **중간 신뢰도**: 추가 검증 권장")
            else:
                success_factors.append("❌ **낮은 신뢰도**: 더 많은 테스트 필요")
            
            for factor in success_factors:
                st.markdown(factor)
        
        with col2:
            st.markdown("#### 🚀 개선 방안 및 전략")
            
            improvements = []
            
            # ROI 개선 전략
            if best_data['가중평균ROI'] < 50:
                improvements.append("📌 **수익성 개선**")
                improvements.append("  • 원가 절감 방안 모색")
                improvements.append("  • 번들 상품으로 객단가 상승")
                improvements.append("  • 프리미엄 포지셔닝 검토")
            
            # 판매량 개선 전략
            if best_data['방송당판매량'] < 100:
                improvements.append("📌 **판매 효율 개선**")
                improvements.append("  • 상품 설명 방식 개선")
                improvements.append("  • 시연 콘텐츠 강화")
                improvements.append("  • 타겟 시간대 재조정")
            
            # 확대 전략
            if best_data['가중평균ROI'] > 70 and best_data['방송횟수'] > 30:
                improvements.append("📌 **사업 확대 전략**")
                improvements.append("  • 프라임 시간대 확보")
                improvements.append("  • 유사 가격대 상품 확대")
                improvements.append("  • 크로스 채널 전개")
            
            # 리스크 관리
            if best_data['방송횟수'] < 20:
                improvements.append("📌 **리스크 관리**")
                improvements.append("  • 단계적 확대 전략")
                improvements.append("  • A/B 테스트 지속")
                improvements.append("  • 시장 반응 모니터링")
            
            for improvement in improvements:
                st.markdown(improvement)
        
        # 추가 인사이트 박스
        st.info(f"""
        **📊 데이터 기반 의사결정 가이드**
        
        🎯 **즉시 실행 가능한 액션**
        1. {best_price_range} 가격대 상품의 방송 슬롯 {20 if best_data['가중평균ROI'] > 50 else 10}% 확대
        2. 해당 가격대 신규 상품 {3 if best_data['방송당판매량'] > 100 else 2}종 추가 기획
        3. 프라임 시간대(10-12시, 20-22시) 배치 우선순위 상향
        
        ⚡ **중기 전략 (3개월)**
        - 유사 가격대(±1만원) 상품군 확대
        - 번들/세트 상품 개발로 객단가 상승
        - 성공 사례 분석 및 벤치마킹
        
        🔍 **모니터링 지표**
        - 주간 ROI 추이 (목표: {best_data['가중평균ROI'] + 10:.1f}%)
        - 방송당 판매량 (목표: {best_data['방송당판매량'] * 1.2:.0f}개)
        - 고객 만족도 및 재구매율
        """)

# ============================================================================
# 4. 가격 최적화 분석 - 수정: HTML 에러 해결
# ============================================================================

def _create_price_optimization_analysis_v16(df, data_formatter):
    """가격 최적화 분석 - HTML 렌더링 에러 수정 및 상세 설명 추가"""
    
    # 데이터 타입 확인 및 변환
    df = preprocess_numeric_columns(df.copy())
    
    st.subheader("🎯 가격 최적화 종합 분석")
    
    # CPI 계산법 설명 (수정사항: 비중 변경)
    st.info("""
    **📊 CPI (Comprehensive Profitability Index) 계산법 - 2025.09.15 수정**
    - **매출액: 40%** (매출 기여도)
    - **판매수량: 40%** (판매 효율성)
    - **방송횟수: 10%** (노출 빈도)
    - **평균 ROI: 10%** (수익성)
    
    6만원~18만원 가격대를 분석하여 고가 상품의 전략적 가치를 평가합니다.
    (19만원 이상 초고가 상품은 분석에서 제외)
    종합 점수가 높을수록 해당 가격대의 전략적 가치가 높습니다.
    """)
    
    # 데이터 준비
    df_price = df[df['units_sold'] > 0].copy()
    
    # 단가 계산 전 타입 확인
    df_price["revenue"] = pd.to_numeric(df_price["revenue"], errors="coerce").fillna(0)
    df_price["units_sold"] = pd.to_numeric(df_price["units_sold"], errors="coerce").fillna(0)
    
    # 0으로 나누기 방지
    df_price = df_price[df_price["units_sold"] > 0]
    df_price['unit_price'] = df_price['revenue'] / df_price['units_sold']
    
    # 가격대별 분석 (6만원 이상 18만원까지)
    price_analysis = []
    for i in range(6, 19):  # 6만원부터 18만원까지 (19-20만원 제외)
        lower = i * 10000
        upper = (i + 1) * 10000
        mask = (df_price['unit_price'] >= lower) & (df_price['unit_price'] < upper)
        
        if mask.sum() >= 5:  # 최소 5건 이상
            subset = df_price[mask]
            
            # 매출액 (35%) - 매출 기여도
            revenue_contribution = subset['revenue'].sum() / df_price['revenue'].sum() * 100
            
            # 평균 판매수량 (30%) - 판매 효율성
            avg_units = subset['units_sold'].mean()
            max_units = df_price.groupby(pd.cut(df_price['unit_price'], 
                                               bins=range(30000, 220000, 10000)))['units_sold'].mean().max()
            sales_efficiency = (avg_units / max_units * 100) if max_units > 0 else 0
            
            # 평균 ROI (30%) - 수익성
            avg_roi = calculate_weighted_roi(subset)
            profitability = min(max(avg_roi / 2, 0), 100)  # ROI를 0-100 범위로 정규화
            
            # 방송횟수 (5%) - 노출 빈도
            broadcast_count = len(subset)
            max_broadcasts = df_price.groupby(pd.cut(df_price['unit_price'], 
                                                    bins=range(30000, 220000, 10000))).size().max()
            broadcast_frequency = (broadcast_count / max_broadcasts * 100) if max_broadcasts > 0 else 0
            
            # CPI 계산 (새로운 가중치 - 수정됨)
            cpi = (revenue_contribution * 0.40 +     # 40% - 매출액
                  sales_efficiency * 0.40 +          # 40% - 판매수량
                  broadcast_frequency * 0.10 +       # 10% - 방송횟수
                  profitability * 0.10)              # 10% - 평균 ROI
            
            price_analysis.append({
                'price_range': f'{i}~{i+1}만원',
                'center_price': float((lower + upper) / 2),
                'count': int(mask.sum()),
                'revenue_contribution': float(revenue_contribution),
                'profitability': float(profitability),
                'efficiency': float(sales_efficiency),  # 판매 효율성으로 변경
                'stability': float(broadcast_frequency),  # 방송횟수 빈도로 변경
                'cpi': float(cpi),
                'avg_revenue': float(subset['revenue'].mean()),
                'avg_roi': float(avg_roi),
                'total_revenue': float(subset['revenue'].sum()),
                'total_units': float(subset['units_sold'].sum()),
                'avg_units': float(avg_units) if not pd.isna(avg_units) else 0.0
            })
    
    if not price_analysis:
        st.warning("가격 최적화 분석을 위한 충분한 데이터가 없습니다.")
        return
    
    analysis_df = pd.DataFrame(price_analysis)
    
    # 숫자 컬럼 타입 확인 및 변환
    numeric_cols = ['center_price', 'count', 'revenue_contribution', 'profitability', 'efficiency', 'stability', 'cpi', 'avg_revenue', 'avg_roi', 'total_revenue', 'total_units', 'avg_units']
    for col in numeric_cols:
        if col in analysis_df.columns:
            analysis_df[col] = pd.to_numeric(analysis_df[col], errors='coerce').fillna(0)
    
    # 가격 탄력성 계산 (안전한 방법)
    analysis_df['elasticity'] = safe_calculate_elasticity(analysis_df)
    
    # ============================================================================
    # 최적 가격 전략 추천 (수정: Streamlit 네이티브 컴포넌트 사용)
    # ============================================================================
    
    st.markdown("### 🎯 데이터 기반 최적 가격 전략 추천")
    
    # Top 3 CPI 가격대 선정
    top_cpi = analysis_df.nlargest(3, 'cpi')
    
    for rank, (idx, row) in enumerate(top_cpi.iterrows(), 1):
        # 전략 타입 결정
        if row['profitability'] > 70:
            strategy_type = "고수익 전략"
            strategy_color = "#00ff88"
            strategy_icon = "💎"
        elif row['efficiency'] > 70:
            strategy_type = "고효율 전략"
            strategy_color = "#00d9ff"
            strategy_icon = "⚡"
        elif row['stability'] > 70:
            strategy_type = "안정성 전략"
            strategy_color = "#7c3aed"
            strategy_icon = "🛡️"
        else:
            strategy_type = "균형 전략"
            strategy_color = "#ffaa00"
            strategy_icon = "⚖️"
        
        # Streamlit 네이티브 컴포넌트로 변경
        with st.container():
            # 헤더
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {strategy_icon} {row['price_range']} - {strategy_type}")
            with col2:
                st.markdown(f"""
                <div style="background: {strategy_color}; 
                           color: black; 
                           padding: 5px 15px; 
                           border-radius: 20px; 
                           text-align: center;
                           font-weight: bold;">
                    #{rank} 추천
                </div>
                """, unsafe_allow_html=True)
            
            # 메인 메트릭
            metric_cols = st.columns(2)
            with metric_cols[0]:
                st.metric(
                    "CPI 종합점수",
                    f"{row['cpi']:.1f}점",
                    delta=f"평균 대비 +{row['cpi'] - analysis_df['cpi'].mean():.1f}점"
                )
            with metric_cols[1]:
                st.metric(
                    "평균 매출",
                    data_formatter.format_money_short(row['avg_revenue']),
                    delta=f"ROI {row['avg_roi']:.1f}%"
                )
            
            # 추천 근거 (expander 사용)
            with st.expander("📋 추천 근거 및 타당성 분석", expanded=True):
                # 추천 이유 생성
                reasons = []
                
                # 매출 기여도 평가
                if row['revenue_contribution'] > 15:
                    reasons.append(f"✅ 전체 매출의 {row['revenue_contribution']:.1f}%를 차지하는 핵심 가격대")
                elif row['revenue_contribution'] > 10:
                    reasons.append(f"✅ 매출 기여도 {row['revenue_contribution']:.1f}%로 중요 가격대")
                elif row['revenue_contribution'] > 5:
                    reasons.append(f"✅ 매출 기여도 {row['revenue_contribution']:.1f}%의 성장 잠재력 보유")
                
                # ROI 평가
                if row['avg_roi'] > 100:
                    reasons.append(f"✅ ROI {row['avg_roi']:.1f}%로 매우 높은 수익성")
                elif row['avg_roi'] > 50:
                    reasons.append(f"✅ ROI {row['avg_roi']:.1f}%로 양호한 수익성")
                elif row['avg_roi'] > 0:
                    reasons.append(f"✅ ROI {row['avg_roi']:.1f}%로 안정적 수익 창출")
                
                # 효율성 평가
                if row['efficiency'] > 70:
                    reasons.append(f"✅ 판매 효율성 {row['efficiency']:.1f}점으로 우수")
                elif row['efficiency'] > 40:
                    reasons.append(f"✅ 판매 효율성 {row['efficiency']:.1f}점으로 양호")
                
                # 안정성 평가
                if row['stability'] > 80:
                    reasons.append(f"✅ 매출 안정성 {row['stability']:.1f}점으로 매우 안정적")
                elif row['stability'] > 60:
                    reasons.append(f"✅ 매출 안정성 {row['stability']:.1f}점으로 예측 가능")
                
                # 방송 횟수
                if row['count'] > 50:
                    reasons.append(f"✅ {row['count']}회 방송으로 충분히 검증됨")
                elif row['count'] > 20:
                    reasons.append(f"⚠️ {row['count']}회 방송으로 추가 테스트 권장")
                else:
                    reasons.append(f"⚠️ {row['count']}회 방송으로 더 많은 테스트 필요")
                
                # 탄력성 분석
                if row['elasticity'] > 1.5:
                    reasons.append("✅ 가격 민감도가 높아 가격 인하 시 매출 증대 가능")
                elif row['elasticity'] < 0.5 and row['elasticity'] > 0:
                    reasons.append("✅ 가격 탄력성이 낮아 프리미엄 전략 가능")
                
                for reason in reasons:
                    st.markdown(reason)
            
            # 세부 지표 (columns 사용)
            st.markdown("#### 📊 세부 지표")
            detail_cols = st.columns(4)
            
            with detail_cols[0]:
                st.markdown(f"""
                <div style="text-align: center; 
                           padding: 15px; 
                           background: rgba(0, 217, 255, 0.1);
                           border-radius: 10px;
                           border: 1px solid rgba(0, 217, 255, 0.3);">
                    <p style="margin: 0; color: rgba(255,255,255,0.6); font-size: 12px;">
                        매출기여도
                    </p>
                    <p style="margin: 5px 0 0 0; color: #00d9ff; font-size: 20px; font-weight: bold;">
                        {row['revenue_contribution']:.1f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with detail_cols[1]:
                st.markdown(f"""
                <div style="text-align: center; 
                           padding: 15px; 
                           background: rgba(0, 255, 136, 0.1);
                           border-radius: 10px;
                           border: 1px solid rgba(0, 255, 136, 0.3);">
                    <p style="margin: 0; color: rgba(255,255,255,0.6); font-size: 12px;">
                        수익성
                    </p>
                    <p style="margin: 5px 0 0 0; color: #00ff88; font-size: 20px; font-weight: bold;">
                        {row['profitability']:.1f}점
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with detail_cols[2]:
                st.markdown(f"""
                <div style="text-align: center; 
                           padding: 15px; 
                           background: rgba(255, 170, 0, 0.1);
                           border-radius: 10px;
                           border: 1px solid rgba(255, 170, 0, 0.3);">
                    <p style="margin: 0; color: rgba(255,255,255,0.6); font-size: 12px;">
                        효율성
                    </p>
                    <p style="margin: 5px 0 0 0; color: #ffaa00; font-size: 20px; font-weight: bold;">
                        {row['efficiency']:.1f}점
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with detail_cols[3]:
                st.markdown(f"""
                <div style="text-align: center; 
                           padding: 15px; 
                           background: rgba(124, 58, 237, 0.1);
                           border-radius: 10px;
                           border: 1px solid rgba(124, 58, 237, 0.3);">
                    <p style="margin: 0; color: rgba(255,255,255,0.6); font-size: 12px;">
                        안정성
                    </p>
                    <p style="margin: 5px 0 0 0; color: #7c3aed; font-size: 20px; font-weight: bold;">
                        {row['stability']:.1f}점
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # 실행 제안
            if rank == 1:
                execution_msg = "이 가격대에 마케팅 자원을 집중하여 시장 점유율 확대"
            elif rank == 2:
                execution_msg = "보조 가격대로 활용하여 리스크 분산"
            else:
                execution_msg = "테스트 마케팅을 통해 잠재력 검증"
            
            st.success(f"💡 **실행 제안**: {execution_msg}")
            
            # 구분선
            if rank < len(top_cpi):
                st.markdown("---")

# ============================================================================
# 시뮬레이션 HTML 보고서 생성 함수
# ============================================================================

def generate_simulation_html_report(simulation_results):
    """시간대별 시뮬레이션 분석 HTML 보고서 생성"""
    
    # format_money 함수 로컬 정의
    def format_money(value, unit='억'):
        """금액을 포맷팅하는 함수"""
        if pd.isna(value):
            return "0.00억"
        
        if unit == '억':
            formatted = value / 100_000_000
            return f"{formatted:,.2f}억"
        elif unit == '만':
            formatted = value / 10_000
            return f"{formatted:,.0f}만"
        else:
            return f"{value:,.0f}"
    
    # 현재 시간
    report_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    
    # 모든 차트 데이터를 미리 준비
    all_chart_scripts = []  # 차트 스크립트를 저장할 배열 초기화
    all_chart_scripts = []
    
    # HTML 템플릿 시작
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>시간대별 시뮬레이션 분석 보고서</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Noto Sans KR', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                line-height: 1.6;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1600px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2);
                padding: 40px;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 30px;
                border-bottom: 3px solid #E0E0E0;
            }}
            
            h1 {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 32px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            
            .report-time {{
                color: #666;
                font-size: 14px;
            }}
            
            .summary {{
                background: linear-gradient(135deg, #E3F2FD 0%, #E8EAF6 100%);
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 30px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin-top: 15px;
            }}
            
            .summary-item {{
                text-align: center;
                background: white;
                padding: 20px 15px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            
            .summary-item:hover {{
                transform: translateY(-5px);
                box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            }}
            
            .summary-label {{
                color: #666;
                font-size: 13px;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .summary-value {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 24px;
                font-weight: bold;
            }}
            
            .analysis-section {{
                margin-bottom: 50px;
            }}
            
            .section-title {{
                color: #333;
                font-size: 22px;
                margin-bottom: 25px;
                padding-bottom: 12px;
                border-bottom: 2px solid #E0E0E0;
                font-weight: 600;
            }}
            
            .chart-container {{
                position: relative;
                width: 100%;
                height: 450px;
                margin: 35px 0;
                padding: 25px;
                background: linear-gradient(135deg, #FAFAFA 0%, #F5F5F5 100%);
                border-radius: 15px;
                border: 1px solid #E0E0E0;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}
            
            .chart-title {{
                text-align: center;
                color: #333;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 25px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            
            .table-wrapper {{
                width: 100%;
                overflow-x: auto;
                margin-bottom: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            table {{
                width: 100%;
                min-width: 1200px;
                border-collapse: separate;
                border-spacing: 0;
                background: white;
            }}
            
            th {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 10px;
                text-align: center;
                font-weight: 600;
                font-size: 13px;
                white-space: nowrap;
                position: sticky;
                top: 0;
                z-index: 10;
            }}
            
            th:first-child {{
                border-top-left-radius: 10px;
            }}
            
            th:last-child {{
                border-top-right-radius: 10px;
            }}
            
            td {{
                padding: 10px 8px;
                text-align: center;
                border-bottom: 1px solid #E8E8E8;
                font-size: 13px;
                white-space: nowrap;
                background: white;
            }}
            
            tr:hover td {{
                background: linear-gradient(90deg, #F5F5FF 0%, #F8F5FF 100%);
            }}
            
            tr:last-child td {{
                border-bottom: none;
            }}
            
            tr:last-child td:first-child {{
                border-bottom-left-radius: 10px;
            }}
            
            tr:last-child td:last-child {{
                border-bottom-right-radius: 10px;
            }}
            
            .profit-positive {{
                color: #2E7D32;
                font-weight: bold;
                background: rgba(76, 175, 80, 0.1);
                padding: 2px 6px;
                border-radius: 4px;
            }}
            
            .profit-negative {{
                color: #C62828;
                font-weight: bold;
                background: rgba(244, 67, 54, 0.1);
                padding: 2px 6px;
                border-radius: 4px;
            }}
            
            .insights {{
                background: linear-gradient(135deg, #FFF8E1 0%, #FFE0B2 100%);
                border-left: 5px solid #FF9800;
                padding: 25px;
                margin-top: 35px;
                border-radius: 10px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            }}
            
            .insights h3 {{
                color: #E65100;
                margin-bottom: 18px;
                font-size: 20px;
                font-weight: 600;
            }}
            
            .insights ul {{
                list-style: none;
                color: #666;
                padding: 0;
            }}
            
            .insights li {{
                margin-bottom: 12px;
                padding-left: 25px;
                position: relative;
            }}
            
            .insights li:before {{
                content: "▸";
                position: absolute;
                left: 0;
                color: #FF9800;
                font-weight: bold;
            }}
            
            .footer {{
                margin-top: 50px;
                padding-top: 25px;
                border-top: 2px solid #E0E0E0;
                text-align: center;
                color: #999;
                font-size: 13px;
            }}
            
            .comparison-chart-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 25px;
                margin: 35px 0;
            }}
            
            @media (max-width: 1200px) {{
                .comparison-chart-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            canvas {{
                max-width: 100%;
                height: auto !important;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 시간대별 시뮬레이션 분석 보고서</h1>
                <div class="report-time">생성 시간: {report_time}</div>
            </div>
    """
    
    # 각 분석 결과별로 섹션 생성
    for idx, analysis in enumerate(simulation_results, 1):
        # 분석별 총 매출, 비용, 순이익 재계산
        total_mean_revenue = 0  # 총 평균매출
        total_trimmed_revenue = 0  # 총 절사평균매출
        total_mean_profit = 0  # 총 평균순이익
        total_trimmed_profit = 0  # 총 절사평균순이익
        total_cost_sum = 0  # 총 비용 (변수명 변경)
        
        # 디버그용 비용 내역
        cost_details = []
        
        for result in analysis['results']:
            hour = result['hour']
            # 방송정액비가 있는 시간대 확인
            has_fixed_cost = (6 <= hour <= 12) or (17 <= hour <= 23)
            margin_rate = 0.5775 if has_fixed_cost else 0.3375
            
            mean_revenue = result.get('mean_revenue', 0)
            mean_trimmed_revenue = result.get('trimmed_mean_revenue', 0)
            
            # 비용 계산 - total_cost 직접 사용
            result_cost = result.get('total_cost', 0)
            
            # 비용이 0이 아닌 경우만 기록 (디버그용)
            if result_cost > 0:
                cost_details.append(f"{hour:02d}시: {result_cost/100_000_000:.3f}억")
            
            # 평균매출 순이익
            mean_net_profit = (mean_revenue * margin_rate) - result_cost
            # 절사평균매출 순이익
            trimmed_net_profit = (mean_trimmed_revenue * margin_rate) - result_cost
            
            total_mean_revenue += mean_revenue
            total_trimmed_revenue += mean_trimmed_revenue
            total_mean_profit += mean_net_profit
            total_trimmed_profit += trimmed_net_profit
            total_cost_sum += result_cost  # 누적 합산
        
        # 가중평균 ROI 계산 (절사평균 순이익 / 총비용 * 100)
        weighted_roi = (total_trimmed_profit / total_cost_sum * 100) if total_cost_sum > 0 else 0
        
        # 시간대별 순이익 계산 (평균매출 기반, 절사평균매출 기반)
        hourly_profits_mean = []
        hourly_profits_trimmed = []
        hour_labels = []
        
        for result in analysis['results']:
            hour_labels.append(f"{result['hour']:02d}시")
            
            # 시간대와 요일 확인 (방송정액비 여부 판단)
            hour = result['hour']
            # 방송정액비가 있는 시간대 확인 (평일 기준)
            has_fixed_cost = (6 <= hour <= 12) or (17 <= hour <= 23)
            
            # 마진율 설정
            margin_rate = 0.5775 if has_fixed_cost else 0.3375
            
            # 평균매출 기반 순이익 계산
            mean_revenue = result.get('mean_revenue', 0)
            mean_trimmed_revenue = result.get('trimmed_mean_revenue', 0)
            total_cost = result.get('total_cost', 0)  # 비용은 항상 포함
            
            # 평균매출 순이익 = 평균매출 * 마진율 - 총비용
            mean_net_profit = (mean_revenue * margin_rate) - total_cost
            hourly_profits_mean.append(round(mean_net_profit / 100_000_000, 3))  # 억 단위
            
            # 절사평균매출 기반 순이익
            trimmed_net_profit = (mean_trimmed_revenue * margin_rate) - total_cost
            hourly_profits_trimmed.append(round(trimmed_net_profit / 100_000_000, 3))  # 억 단위
        
        # 차트 ID를 위한 고유 식별자 (언더스코어 없이)
        chart_id = f"profitChart{idx}"
        # 비용 상세 정보를 화면에 표시 (디버그용)
        cost_debug_html = f"""
            <div style="background: #FFF3E0; padding: 10px; margin: 10px 0; border-left: 3px solid #FF9800; font-size: 12px;">
                <strong>🔍 비용 상세 (디버그):</strong><br>
                {' / '.join(cost_details) if cost_details else '비용 없음'}<br>
                <strong>총 비용 합계: {total_cost_sum/100_000_000:.3f}억</strong>
            </div>
        """
        
        html_content += f"""
            <div class="analysis-section">
                <h2 class="section-title">
                    📊 분석 {idx}: {analysis['filters']['platform']} - {analysis['filters']['category']}
                </h2>
                
                {cost_debug_html}
                
                <div class="summary">
                    <strong>분석 조건:</strong> 
                    {analysis['filters']['period']} | 
                    {analysis['filters']['weekday']} | 
                    시간대: {', '.join([f"{h:02d}시" for h in analysis['filters']['hours']])}
                    
                    <div class="summary-grid" style="grid-template-columns: repeat(3, 1fr); gap: 15px;">
                        <div class="summary-item">
                            <div class="summary-label">총 평균매출</div>
                            <div class="summary-value">{(total_mean_revenue / 100_000_000):.3f}억</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">총 절사평균매출</div>
                            <div class="summary-value">{(total_trimmed_revenue / 100_000_000):.3f}억</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">총 비용</div>
                            <div class="summary-value">{(total_cost_sum / 100_000_000):.3f}억</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">총 평균순이익</div>
                            <div class="summary-value">{(total_mean_profit / 100_000_000):.3f}억</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">총 절사평균순이익</div>
                            <div class="summary-value">{(total_trimmed_profit / 100_000_000):.3f}억</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">가중평균 ROI</div>
                            <div class="summary-value">{weighted_roi:.1f}%</div>
                        </div>
                    </div>
                </div>
                
                <!-- 시간대별 순이익 막대그래프 -->
                <div class="chart-container">
                    <div class="chart-title">📊 시간대별 순이익 비교 (평균매출 vs 절사평균매출)</div>
                    <div style="position: relative; height: 350px;">
                        <canvas id="{chart_id}"></canvas>
                    </div>
                </div>
                
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>시간대</th>
                                <th>평균매출</th>
                                <th>절사평균매출</th>
                                <th>평균수량</th>
                                <th>절사평균수량</th>
                                <th>평균ROI</th>
                                <th>절사평균ROI</th>
                                <th>방송횟수</th>
                                <th>총비용</th>
                                <th style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);">평균매출<br>순이익</th>
                                <th style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);">절사평균매출<br>순이익</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # 각 시간대별 데이터 추가
        for result in analysis['results']:
            # 시간대별 마진율 적용
            hour = result['hour']
            has_fixed_cost = (6 <= hour <= 12) or (17 <= hour <= 23)
            margin_rate = 0.5775 if has_fixed_cost else 0.3375
            
            # 매출 데이터
            mean_revenue = result.get('mean_revenue', 0)
            mean_trimmed_revenue = result.get('trimmed_mean_revenue', 0) 
            hour_cost = result.get('total_cost', 0)  # 변수명 변경: total_cost -> hour_cost
            
            # 순이익 계산 (수정된 마진율 적용)
            mean_net_profit = (mean_revenue * margin_rate) - hour_cost
            trimmed_net_profit = (mean_trimmed_revenue * margin_rate) - hour_cost
            
            profit_class_mean = 'profit-positive' if mean_net_profit > 0 else 'profit-negative'
            profit_class_trimmed = 'profit-positive' if trimmed_net_profit > 0 else 'profit-negative'
            
            html_content += f"""
                            <tr>
                                <td style="font-weight: bold; background: rgba(103, 126, 234, 0.05);">{result['hour']:02d}:00</td>
                                <td>{(mean_revenue / 100_000_000):.3f}억</td>
                                <td>{(mean_trimmed_revenue / 100_000_000):.3f}억</td>
                                <td>{result.get('mean_units', 0):.0f}</td>
                                <td>{result.get('trimmed_mean_units', 0):.0f}</td>
                                <td>{result.get('mean_roi', 0):.1f}%</td>
                                <td>{result.get('trimmed_roi', 0):.1f}%</td>
                                <td>{result.get('broadcast_count', 0)}</td>
                                <td>{(hour_cost / 100_000_000):.3f}억</td>
                                <td class="{profit_class_mean}">{(mean_net_profit / 100_000_000):.3f}억</td>
                                <td class="{profit_class_trimmed}">{(trimmed_net_profit / 100_000_000):.3f}억</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
        """
        
        # 차트 스크립트를 바로 추가 (데이터를 직접 삽입)
        # 선택된 시간대 문자열 생성
        selected_hours_str = ', '.join([f"{h:02d}시" for h in analysis['filters']['hours'][:3]]) + ('...' if len(analysis['filters']['hours']) > 3 else '')
        
        all_chart_scripts.append(f"""
            // 차트 {idx} - 시간대별 순이익 비교
            (function() {{
                const chartId = 'profitChart{idx}';
                const canvas = document.getElementById(chartId);
                if (!canvas) {{
                    console.error('Canvas not found: ' + chartId);
                    return;
                }}
                
                // 기존 차트 제거
                destroyExistingChart(chartId);
                
                try {{
                    const ctx = canvas.getContext('2d');
                    const hourlyProfitsMean = {json.dumps([round(x, 3) for x in hourly_profits_mean])};
                    const hourlyProfitsTrimmed = {json.dumps([round(x, 3) for x in hourly_profits_trimmed])};
                    
                    chartManager.instances[chartId] = new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(hour_labels)},
                            datasets: [
                                {{
                                    label: '평균매출 순이익',
                                    data: hourlyProfitsMean,
                                    backgroundColor: 'rgba(76, 175, 80, 0.8)',
                                    borderColor: 'rgba(76, 175, 80, 1)',
                                    borderWidth: 2,
                                    borderRadius: 8
                                }},
                                {{
                                    label: '절사평균매출 순이익',
                                    data: hourlyProfitsTrimmed,
                                    backgroundColor: 'rgba(255, 152, 0, 0.8)',
                                    borderColor: 'rgba(255, 152, 0, 1)',
                                    borderWidth: 2,
                                    borderRadius: 8
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            layout: {{
                                padding: {{
                                    top: 30
                                }}
                            }},
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'top',
                                    labels: {{
                                        padding: 15,
                                        font: {{
                                            size: 14,
                                            weight: 'bold'
                                        }},
                                        usePointStyle: true
                                    }}
                                }},
                                tooltip: {{
                                    enabled: true,
                                    backgroundColor: 'rgba(0,0,0,0.8)',
                                    titleFont: {{
                                        size: 14,
                                        weight: 'bold'
                                    }},
                                    bodyFont: {{
                                        size: 13
                                    }},
                                    padding: 12,
                                    cornerRadius: 8,
                                    callbacks: {{
                                        label: function(context) {{
                                            let label = context.dataset.label || '';
                                            if (label) {{
                                                label += ': ';
                                            }}
                                            label += context.parsed.y.toFixed(3) + '억';
                                            return label;
                                        }}
                                    }}
                                }},
                                datalabels: {{
                                    display: true,
                                    anchor: 'end',
                                    align: 'top',
                                    color: '#333',
                                    font: {{
                                        weight: 'bold',
                                        size: 11
                                    }},
                                    formatter: function(value) {{
                                        return value.toFixed(3) + '억';
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    display: true,
                                    grid: {{
                                        display: false
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 12,
                                            weight: 'bold'
                                        }}
                                    }}
                                }},
                                y: {{
                                    display: true,
                                    beginAtZero: true,
                                    grace: '10%',
                                    grid: {{
                                        borderDash: [3, 3],
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        callback: function(value) {{
                                            return value.toFixed(3) + '억';
                                        }},
                                        font: {{
                                            size: 11
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                    console.log('Chart {idx} created successfully');
                }} catch (error) {{
                    console.error('Error creating chart {idx}:', error);
                }}
            }})();
        """)
        
        # 인사이트 추가
        positive_hours = [r for r in analysis['results'] if r.get('net_profit', 0) > 0]
        best_hour = max(analysis['results'], key=lambda x: x.get('net_profit', 0))
        worst_hour = min(analysis['results'], key=lambda x: x.get('net_profit', 0))
        
        html_content += f"""
                <div class="insights">
                    <h3>💡 분석 인사이트</h3>
                    <ul>
                        <li><strong>수익성 분석:</strong> 전체 {len(analysis['results'])}개 시간대 중 {len(positive_hours)}개 시간대에서 수익 발생 ({len(positive_hours)/len(analysis['results'])*100:.0f}%)</li>
                        <li><strong>최고 성과:</strong> {best_hour.get('hour', 0):02d}:00 (순이익: {format_money(best_hour.get('net_profit', 0), unit='억')}, ROI: {best_hour.get('trimmed_roi', 0):.1f}%)</li>
                        <li><strong>최저 성과:</strong> {worst_hour.get('hour', 0):02d}:00 (순이익: {format_money(worst_hour.get('net_profit', 0), unit='억')}, ROI: {worst_hour.get('trimmed_roi', 0):.1f}%)</li>
                        <li><strong>권장사항:</strong> """
        
        if len(positive_hours) >= len(analysis['results']) * 0.5:
            html_content += "수익성이 검증된 시간대가 많아 안정적인 운영이 가능합니다. 수익성 높은 시간대에 추가 투자를 고려하세요."
        elif len(positive_hours) > 0:
            positive_hours_str = ', '.join([f"{r.get('hour', 0):02d}시" for r in sorted(positive_hours, key=lambda x: x.get('net_profit', 0), reverse=True)[:3]])
            html_content += f"수익성 있는 {positive_hours_str} 시간대에 집중 편성을 권장합니다."
        else:
            html_content += "전반적인 수익구조 개선이 필요합니다. 상품 구성이나 가격 정책을 재검토하세요."
        
        html_content += """
                        </li>
                    </ul>
                </div>
            </div>
        """
    
    # 종합 의견 추가
    if len(simulation_results) > 1:
        html_content += """
            <div style="background: #E8F5E9; border-radius: 10px; padding: 25px; margin: 30px 0; border: 2px solid #4CAF50;">
                <h2 style="color: #2E7D32; margin-bottom: 20px;">📊 종합 분석 의견</h2>
        """
        
        # 종합 그래프를 위한 데이터 준비
        analysis_labels = []
        analysis_labels_detailed = []
        total_revenues = []
        total_costs = []
        total_profits = []
        avg_rois = []
        
        for i, analysis in enumerate(simulation_results, 1):
            # 선택된 시간대 문자열
            selected_hours = analysis['filters']['hours']
            hours_str = ', '.join([f"{h:02d}시" for h in selected_hours[:3]]) + ('...' if len(selected_hours) > 3 else '')
            
            # 각 분석별 총합 재계산
            chart_total_revenue = 0
            chart_total_cost = 0
            chart_total_profit = 0
            
            for result in analysis['results']:
                hour = result['hour']
                has_fixed_cost = (6 <= hour <= 12) or (17 <= hour <= 23)
                margin_rate = 0.5775 if has_fixed_cost else 0.3375
                
                mean_trimmed_revenue = result.get('trimmed_mean_revenue', 0)
                result_cost = result.get('total_cost', 0)
                net_profit = (mean_trimmed_revenue * margin_rate) - result_cost
                
                chart_total_revenue += mean_trimmed_revenue
                chart_total_cost += result_cost
                chart_total_profit += net_profit
            
            chart_avg_roi = (chart_total_profit / chart_total_cost * 100) if chart_total_cost > 0 else 0
            
            analysis_labels.append(f"분석{i}")
            analysis_labels_detailed.append(f"분석{i}({hours_str})")
            total_revenues.append(round(chart_total_revenue / 100_000_000, 3))
            total_costs.append(round(chart_total_cost / 100_000_000, 3))
            total_profits.append(round(chart_total_profit / 100_000_000, 3))
            avg_rois.append(round(chart_avg_roi, 1))
        
        # 종합 비교 그래프들
        html_content += f"""
                <!-- 분석 내역별 종합 이익 그래프들 -->
                <div class="comparison-chart-grid">
                    <!-- 매출/비용/이익 비교 그래프 -->
                    <div class="chart-container">
                        <div class="chart-title">💰 분석별 매출/비용/이익 비교</div>
                        <div style="position: relative; height: 350px;">
                            <canvas id="comparisonChart1"></canvas>
                        </div>
                    </div>
                    
                    <!-- ROI 비교 그래프 -->
                    <div class="chart-container">
                        <div class="chart-title">📈 분석별 ROI 비교</div>
                        <div style="position: relative; height: 350px;">
                            <canvas id="comparisonChart2"></canvas>
                        </div>
                    </div>
                    
                    <!-- 순이익 트렌드 라인 그래프 -->
                    <div class="chart-container">
                        <div class="chart-title">📊 순이익 트렌드</div>
                        <div style="position: relative; height: 350px;">
                            <canvas id="comparisonChart3"></canvas>
                        </div>
                    </div>
                    
                    <!-- 수익성 파이 차트 -->
                    <div class="chart-container">
                        <div class="chart-title">🥧 총 이익 구성비</div>
                        <div style="position: relative; height: 350px;">
                            <canvas id="comparisonChart4"></canvas>
                        </div>
                    </div>
                </div>
        """
        
        # 종합 차트 스크립트를 all_chart_scripts에 추가
        all_chart_scripts.append(f"""
            // 종합 비교 차트들
            (function() {{
                // 차트 1 - 매출/비용/이익
                const chartId1 = 'comparisonChart1';
                const canvas1 = document.getElementById(chartId1);
                if (canvas1) {{
                    destroyExistingChart(chartId1);
                    try {{
                        chartManager.instances[chartId1] = new Chart(canvas1.getContext('2d'), {{
                            type: 'bar',
                            data: {{
                                labels: {json.dumps(analysis_labels_detailed)},
                                datasets: [
                                    {{
                                        label: '총 매출',
                                        data: {json.dumps(total_revenues)},
                                        backgroundColor: 'rgba(103, 126, 234, 0.8)',
                                        borderColor: 'rgba(103, 126, 234, 1)',
                                        borderWidth: 2,
                                        borderRadius: 8
                                    }},
                                    {{
                                        label: '총 비용',
                                        data: {json.dumps(total_costs)},
                                        backgroundColor: 'rgba(244, 67, 54, 0.8)',
                                        borderColor: 'rgba(244, 67, 54, 1)',
                                        borderWidth: 2,
                                        borderRadius: 8
                                    }},
                                    {{
                                        label: '순이익',
                                        data: {json.dumps(total_profits)},
                                        backgroundColor: 'rgba(76, 175, 80, 0.8)',
                                        borderColor: 'rgba(76, 175, 80, 1)',
                                        borderWidth: 2,
                                        borderRadius: 8
                                    }}
                                ]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    legend: {{ 
                                        display: true, 
                                        position: 'top',
                                        labels: {{
                                            usePointStyle: true,
                                            font: {{ size: 13, weight: 'bold' }}
                                        }}
                                    }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                return context.dataset.label + ': ' + context.parsed.y.toFixed(3) + '억';
                                            }}
                                        }}
                                    }},
                                    datalabels: {{
                                        display: true,
                                        anchor: function(context) {{
                                            const value = context.dataset.data[context.dataIndex];
                                            return value >= 0 ? 'end' : 'start';
                                        }},
                                        align: function(context) {{
                                            const value = context.dataset.data[context.dataIndex];
                                            return value >= 0 ? 'top' : 'bottom';
                                        }},
                                        color: '#333',
                                        font: {{ weight: 'bold', size: 10 }},
                                        formatter: function(value) {{
                                            return value.toFixed(3) + '억';
                                        }}
                                    }}
                                }},
                                scales: {{
                                    x: {{ grid: {{ display: false }} }},
                                    y: {{
                                        beginAtZero: true,
                                        ticks: {{
                                            callback: function(value) {{ return value + '억'; }}
                                        }}
                                    }}
                                }}
                            }}
                        }});
                        console.log('Comparison chart 1 created');
                    }} catch(e) {{ console.error('Error in chart 1:', e); }}
                }}
                
                // 차트 2 - ROI (가중평균)
                const chartId2 = 'comparisonChart2';
                const canvas2 = document.getElementById(chartId2);
                if (canvas2) {{
                    destroyExistingChart(chartId2);
                    try {{
                        // 가중평균 ROI 계산 (총이익 / 총비용 * 100)
                        const weightedRois = [];
                        const revenues = {json.dumps(total_revenues)};
                        const costs = {json.dumps(total_costs)};
                        const profits = {json.dumps(total_profits)};
                        
                        for (let i = 0; i < profits.length; i++) {{
                            if (costs[i] > 0) {{
                                const roi = (profits[i] / costs[i]) * 100;
                                weightedRois.push(roi);
                            }} else {{
                                weightedRois.push(0);
                            }}
                        }}
                        
                        const roiColors = weightedRois.map(v => v > 50 ? 'rgba(76, 175, 80, 0.8)' : v > 0 ? 'rgba(255, 193, 7, 0.8)' : 'rgba(244, 67, 54, 0.8)');
                        
                        chartManager.instances[chartId2] = new Chart(canvas2.getContext('2d'), {{
                            type: 'bar',
                            data: {{
                                labels: {json.dumps(analysis_labels_detailed)},
                                datasets: [{{
                                    label: '가중평균 ROI',
                                    data: weightedRois,
                                    backgroundColor: roiColors,
                                    borderWidth: 2,
                                    borderRadius: 8
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    legend: {{ display: false }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                return 'ROI: ' + context.parsed.y.toFixed(1) + '%';
                                            }}
                                        }}
                                    }},
                                    datalabels: {{
                                        display: true,
                                        anchor: 'center',
                                        align: 'center',
                                        color: '#fff',
                                        font: {{ 
                                            weight: 'bold', 
                                            size: 12 
                                        }},
                                        formatter: function(value) {{
                                            return value.toFixed(1) + '%';
                                        }}
                                    }}
                                }},
                                scales: {{
                                    x: {{ grid: {{ display: false }} }},
                                    y: {{
                                        beginAtZero: true,
                                        ticks: {{
                                            callback: function(value) {{ return value + '%'; }}
                                        }}
                                    }}
                                }}
                            }}
                        }});
                        console.log('Comparison chart 2 created');
                    }} catch(e) {{ console.error('Error in chart 2:', e); }}
                }}
                
                // 차트 3 - 순이익 트렌드
                const chartId3 = 'comparisonChart3';
                const canvas3 = document.getElementById(chartId3);
                if (canvas3) {{
                    destroyExistingChart(chartId3);
                    try {{
                        chartManager.instances[chartId3] = new Chart(canvas3.getContext('2d'), {{
                            type: 'line',
                            data: {{
                                labels: {json.dumps(analysis_labels)},
                                datasets: [{{
                                    label: '순이익 트렌드',
                                    data: {json.dumps(total_profits)},
                                    borderColor: 'rgba(103, 126, 234, 1)',
                                    backgroundColor: 'rgba(103, 126, 234, 0.1)',
                                    borderWidth: 3,
                                    tension: 0.4,
                                    fill: true,
                                    pointRadius: 6,
                                    pointHoverRadius: 8,
                                    pointBackgroundColor: 'rgba(103, 126, 234, 1)',
                                    pointBorderColor: '#fff',
                                    pointBorderWidth: 2
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    legend: {{ display: false }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                return '순이익: ' + context.parsed.y.toFixed(2) + '억';
                                            }}
                                        }}
                                    }}
                                }},
                                scales: {{
                                    x: {{ grid: {{ display: false }} }},
                                    y: {{
                                        beginAtZero: true,
                                        ticks: {{
                                            callback: function(value) {{ return value + '억'; }}
                                        }}
                                    }}
                                }}
                            }}
                        }});
                        console.log('Comparison chart 3 created');
                    }} catch(e) {{ console.error('Error in chart 3:', e); }}
                }}
                
                // 차트 4 - 이익 구성 (막대 그래프로 변경)
                const chartId4 = 'comparisonChart4';
                const canvas4 = document.getElementById(chartId4);
                if (canvas4) {{
                    destroyExistingChart(chartId4);
                    try {{
                        const profitData = {json.dumps(total_profits)};
                        const profitColors = profitData.map(v => 
                            v > 0 ? 'rgba(76, 175, 80, 0.8)' : 'rgba(244, 67, 54, 0.8)'
                        );
                        
                        chartManager.instances[chartId4] = new Chart(canvas4.getContext('2d'), {{
                            type: 'bar',
                            data: {{
                                labels: {json.dumps(analysis_labels_detailed)},
                                datasets: [{{
                                    label: '순이익',
                                    data: profitData,
                                    backgroundColor: profitColors,
                                    borderWidth: 2,
                                    borderRadius: 8
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    legend: {{ display: false }},
                                    title: {{
                                        display: true,
                                        text: '분석별 순이익 비교',
                                        font: {{ size: 14, weight: 'bold' }}
                                    }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                const value = context.parsed.y;
                                                const label = value >= 0 ? '이익: ' : '손실: ';
                                                return label + Math.abs(value).toFixed(3) + '억';
                                            }}
                                        }}
                                    }},
                                    datalabels: {{
                                        display: true,
                                        anchor: function(context) {{
                                            const value = context.dataset.data[context.dataIndex];
                                            return value >= 0 ? 'end' : 'start';
                                        }},
                                        align: function(context) {{
                                            const value = context.dataset.data[context.dataIndex];
                                            return value >= 0 ? 'top' : 'bottom';
                                        }},
                                        color: '#333',
                                        font: {{ 
                                            weight: 'bold', 
                                            size: 11
                                        }},
                                        formatter: function(value) {{
                                            return value.toFixed(3) + '억';
                                        }}
                                    }}
                                }},
                                scales: {{
                                    x: {{ 
                                        grid: {{ display: false }},
                                        ticks: {{
                                            font: {{ size: 11, weight: 'bold' }},
                                            maxRotation: 45,
                                            minRotation: 45
                                        }}
                                    }},
                                    y: {{
                                        beginAtZero: false,
                                        grace: '20%',
                                        grid: {{
                                            borderDash: [3, 3],
                                            color: 'rgba(0, 0, 0, 0.05)',
                                            drawBorder: true,
                                            drawOnChartArea: true,
                                            drawTicks: true,
                                            lineWidth: 1,
                                            zeroLineColor: 'rgba(0, 0, 0, 0.5)',
                                            zeroLineWidth: 2
                                        }},
                                        ticks: {{
                                            callback: function(value) {{ 
                                                return value.toFixed(1) + '억'; 
                                            }},
                                            font: {{ size: 11 }}
                                        }}
                                    }}
                                }},
                                indexAxis: 'x'
                            }}
                        }});
                        console.log('Comparison chart 4 created');
                    }} catch(e) {{ console.error('Error in chart 4:', e); }}
                }}
            }})();
        """)
        
        
        # 각 분석의 성과 평가
        analysis_scores = []
        for idx, analysis in enumerate(simulation_results, 1):
            # 각 분석별 총 매출, 순이익 재계산
            total_revenue = 0
            total_profit = 0
            total_cost = 0
            
            for result in analysis['results']:
                hour = result['hour']
                has_fixed_cost = (6 <= hour <= 12) or (17 <= hour <= 23)
                margin_rate = 0.5775 if has_fixed_cost else 0.3375
                
                mean_trimmed_revenue = result.get('trimmed_mean_revenue', 0)
                result_cost = result.get('total_cost', 0)
                net_profit = (mean_trimmed_revenue * margin_rate) - result_cost
                
                total_revenue += mean_trimmed_revenue
                total_cost += result_cost
                total_profit += net_profit
            
            avg_roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
            profitable_hours = len([r for r in analysis['results'] if r.get('net_profit', 0) > 0])
            total_hours = len(analysis['results'])
            profit_rate = (profitable_hours / total_hours * 100) if total_hours > 0 else 0
            
            # 종합 점수 계산 (ROI 40%, 순이익 40%, 수익률 20%)
            score = (avg_roi * 0.4) + (total_profit / 100_000_000 * 0.4) + (profit_rate * 0.2)
            
            analysis_scores.append({
                'index': idx,
                'score': score,
                'profit': total_profit,
                'revenue': total_revenue,  # revenue 추가
                'roi': avg_roi,
                'profit_rate': profit_rate,
                'platform': analysis['filters']['platform'],
                'category': analysis['filters']['category'],
                'hours': analysis['filters']['hours']
            })
        
        # 최고 성과 분석 찾기 (순이익률 기준)
        best_analysis = max(analysis_scores, key=lambda x: x['profit'] / x['revenue'] if x.get('revenue', 1) > 0 else 0)
        
        # 순이익률로 정렬
        sorted_by_profit_rate = sorted(analysis_scores, 
                                       key=lambda x: x['profit'] / x.get('revenue', 1) if x.get('revenue', 1) > 0 else 0, 
                                       reverse=True)
        
        html_content += f"""
                <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #1976D2; margin-bottom: 15px;">🏆 최고 성과 분석</h3>
                    <div style="background: #FFFDE7; padding: 15px; border-radius: 5px; border-left: 4px solid #FBC02D;">
                        <p style="font-size: 18px; font-weight: bold; color: #F57C00; margin-bottom: 10px;">
                            분석 {best_analysis['index']}: {best_analysis['platform']} - {best_analysis['category']}
                        </p>
                        <ul style="list-style: none; padding: 0;">
                            <li>📈 <strong>ROI:</strong> {best_analysis['roi']:.1f}%</li>
                            <li>💰 <strong>총 순이익:</strong> {(best_analysis['profit'] / 100_000_000):.3f}억</li>
                            <li>✅ <strong>순이익률:</strong> {(best_analysis['profit'] / best_analysis.get('revenue', 1) * 100 if best_analysis.get('revenue', 1) > 0 else 0):.1f}%</li>
                            <li>⏰ <strong>분석 시간대:</strong> {', '.join([f"{h:02d}시" for h in best_analysis['hours'][:5]])}{'...' if len(best_analysis['hours']) > 5 else ''}</li>
                        </ul>
                    </div>
                </div>
                
                <div style="background: white; padding: 20px; border-radius: 8px;">
                    <h3 style="color: #1976D2; margin-bottom: 15px;">💡 전체 분석 순위</h3>
        """
        
        # 모든 분석 순위 표시 (순이익률 기준)
        for rank, analysis in enumerate(sorted_by_profit_rate, 1):
            if rank <= 3:
                medal = ["🥇", "🥈", "🥉"][rank-1]
                rank_text = f"{medal} {rank}위"
            else:
                rank_text = f"{rank}위"
            
            profit_rate = (analysis['profit'] / analysis.get('revenue', 1) * 100) if analysis.get('revenue', 1) > 0 else 0
            
            html_content += f"""
                    <div style="background: #F5F5F5; padding: 12px; margin: 10px 0; border-radius: 5px; 
                               border-left: 3px solid {'#FFD700' if rank == 1 else '#C0C0C0' if rank == 2 else '#CD7F32' if rank == 3 else '#E0E0E0'};">
                        <strong>{rank_text} 분석 {analysis['index']}</strong>: 
                        {analysis['platform']} - {analysis['category']} | 
                        ROI: {analysis['roi']:.1f}% | 
                        순이익: {(analysis['profit'] / 100_000_000):.3f}억 | 
                        순이익률: {profit_rate:.1f}% 
                        종합점수: {analysis['score']:.1f}점
                    </div>
            """
        
        html_content += """
                </div>
                
                <div style="background: #FFF3E0; padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <h3 style="color: #E65100; margin-bottom: 15px;">🎯 실행 권장사항</h3>
                    <ol style="line-height: 1.8;">
        """
        
        # 권장사항 생성
        if best_analysis['roi'] > 50:
            html_content += f"""
                        <li><strong>즉시 실행 권장:</strong> 분석 {best_analysis['index']}번의 {best_analysis['platform']} - {best_analysis['category']} 조합이 
                            {best_analysis['roi']:.1f}%의 높은 ROI를 보여 즉시 실행을 권장합니다.</li>
            """
        
        if best_analysis['profit_rate'] >= 70:
            html_content += f"""
                        <li><strong>안정적 운영 가능:</strong> {best_analysis['profit_rate']:.0f}%의 시간대에서 수익이 발생하여 
                            리스크가 낮고 안정적인 운영이 가능합니다.</li>
            """
        elif best_analysis['profit_rate'] >= 50:
            html_content += f"""
                        <li><strong>선택적 집중 필요:</strong> 수익 시간대가 {best_analysis['profit_rate']:.0f}%로, 
                            수익성 높은 시간대에 집중 편성하는 전략이 필요합니다.</li>
            """
        else:
            html_content += f"""
                        <li><strong>신중한 접근 필요:</strong> 수익 시간대가 {best_analysis['profit_rate']:.0f}%로 제한적이므로, 
                            추가 분석과 상품 구성 개선이 필요합니다.</li>
            """
        
        # 시간대별 권장사항
        profitable_hours_list = []
        for analysis in simulation_results:
            for result in analysis['results']:
                if result.get('net_profit', 0) > 0:
                    profitable_hours_list.append(result['hour'])
        
        if profitable_hours_list:
            from collections import Counter
            hour_counts = Counter(profitable_hours_list)
            best_hours = [h for h, _ in hour_counts.most_common(3)]
            
            html_content += f"""
                        <li><strong>최적 방송 시간대:</strong> 복수 분석에서 공통적으로 수익성이 높은 
                            {', '.join([f'{h:02d}시' for h in best_hours])} 시간대를 우선 편성하세요.</li>
            """
        
        html_content += """
                        <li><strong>지속적 모니터링:</strong> 시장 상황과 경쟁사 동향을 지속적으로 모니터링하며 
                            분석 결과를 주기적으로 업데이트하세요.</li>
                    </ol>
                </div>
            </div>
        """
    
    # HTML 마무리 및 모든 차트 렌더링 스크립트
    html_content += f"""
            <div class="footer">
                <p>본 보고서는 시뮬레이션 분석 결과를 바탕으로 작성되었습니다.</p>
                <p>© 2025 홈쇼핑 매출 분석 시스템</p>
            </div>
        </div>
        
        <!-- 모든 차트를 렌더링하는 통합 스크립트 -->
        <script>
            // 전역 변수 선언
            const chartManager = {{
                instances: {{}},
                initialized: false
            }};
            
            // 기존 차트 제거 함수
            function destroyExistingChart(chartId) {{
                if (chartManager.instances[chartId]) {{
                    chartManager.instances[chartId].destroy();
                    delete chartManager.instances[chartId];
                    console.log('Destroyed chart: ' + chartId);
                }}
            }}
            
            // 차트 생성 함수
            function createAllCharts() {{
                // 이미 초기화되었으면 중단
                if (chartManager.initialized) {{
                    console.log('Charts already initialized');
                    return;
                }}
                
                console.log('Starting chart creation...');
                
                // Chart.js 로드 확인
                if (typeof Chart === 'undefined') {{
                    console.error('Chart.js is not loaded yet, retrying...');
                    setTimeout(createAllCharts, 500);
                    return;
                }}
                
                console.log('Chart.js version:', Chart.version);
                
                // Chart.js 기본 설정
                Chart.defaults.font.family = "'Noto Sans KR', sans-serif";
                Chart.defaults.responsive = true;
                Chart.defaults.maintainAspectRatio = false;
                
                // 데이터 레이블 플러그인 등록
                if (typeof ChartDataLabels !== 'undefined') {{
                    Chart.register(ChartDataLabels);
                    console.log('DataLabels plugin registered');
                    
                    // 기본 데이터 레이블 설정
                    Chart.defaults.plugins.datalabels = {{
                        display: true,
                        color: '#333',
                        font: {{
                            weight: 'bold',
                            size: 11
                        }},
                        formatter: function(value) {{
                            if (typeof value === 'number') {{
                                return value.toFixed(3) + '억';
                            }}
                            return value;
                        }}
                    }};
                }}
                
                try {{
                    // 각 분석별 차트 렌더링
                    {''.join(all_chart_scripts)}
                    
                    // 초기화 완료 표시
                    chartManager.initialized = true;
                    console.log('All charts created successfully');
                }} catch (error) {{
                    console.error('Chart rendering error:', error);
                }}
            }}
            
            // 초기화 실행 (한 번만 실행되도록 보장)
            (function() {{
                let initStarted = false;
                
                function tryInit() {{
                    if (initStarted) return;
                    initStarted = true;
                    
                    // Chart.js가 로드될 때까지 대기
                    if (typeof Chart === 'undefined') {{
                        console.log('Waiting for Chart.js to load...');
                        setTimeout(function() {{
                            initStarted = false;
                            tryInit();
                        }}, 100);
                        return;
                    }}
                    
                    // 차트 생성 실행
                    createAllCharts();
                }}
                
                // DOM 로드 상태 확인
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', tryInit);
                }} else {{
                    // 이미 로드된 경우 즉시 실행
                    setTimeout(tryInit, 100);
                }}
            }})();
        </script>
    </body>
    </html>
    """
    
    return html_content
