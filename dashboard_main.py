"""
dashboard_main.py - 홈쇼핑 방송 분석 대시보드 메인 (전략분석 탭 추가 v21.0.0)
Version: 21.0.0
Updated: 2025-02-16

주요 수정사항:
1. 추세분석 탭 추가
2. 가격 분석 탭 제거
3. 일일 트렌드 탭 성능 개선
4. 카테고리 분석 탭 효율성 그래프 제거
5. 전략 분석 탭 추가 (2025-02-16) - ROI 기반 최적 전략 분석
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sqlite3
import traceback
from io import BytesIO

# 공통 유틸리티 함수 import
from dashboard_utils import (
    safe_to_json,
    json_to_df,
    generate_cache_key,
    format_short_number,
    show_loading_message,
    init_session_state,
    check_database_exists,
    log_error,
    show_debug_panel
)

# 대시보드 모듈 임포트
from dashboard_config import (
    apply_page_config, 
    apply_custom_styles,
    COLORS, 
    PLATFORM_COLORS, 
    CATEGORY_COLORS, 
    WEEKDAY_COLORS,
    DEFAULT_FILTERS, 
    CHART_CONFIG,
    LIVE_CHANNELS,
    MODEL_COST_LIVE,
    MODEL_COST_NON_LIVE,
    CONVERSION_RATE,
    REAL_MARGIN_RATE,
    emergency_hover_fix
)
from dashboard_data import DataManager
from dashboard_visuals import ChartGenerator
from dashboard_tabs_1 import (
    create_dashboard_tab, 
    create_platform_tab, 
    create_time_tab
)
from dashboard_tabs_2_v8_integrated import (
    create_daily_tab,
)

# 정밀분석 탭 import 추가
import_error_msg = None
HAS_PRECISION_ANALYSIS = True  # 무조건 True로 설정

try:
    from dashboard_precision_analysis import create_precision_analysis_tab
    print("✅ dashboard_precision_analysis 모듈 로드 성공")
except ImportError as e:
    import_error_msg = str(e)
    print(f"⚠️ Warning: dashboard_precision_analysis 모듈 로드 실패: {import_error_msg}")
    # import 실패 시 대체 함수 정의
    def create_precision_analysis_tab(df_filtered, chart_generator, data_formatter, 
                                     category_colors, platform_colors, colors):
        import streamlit as st
        st.error(f"정밀분석 모듈 import 오류: {import_error_msg}")
        st.info("dashboard_precision_analysis.py 파일을 확인해주세요.")
        # 기본 데이터 표시
        if df_filtered is not None and len(df_filtered) > 0:
            st.write(f"총 데이터: {len(df_filtered):,}건")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("데이터 건수", f"{len(df_filtered):,}")
            with col2:
                if 'revenue' in df_filtered.columns:
                    st.metric("총 매출", f"{df_filtered['revenue'].sum()/100000000:.1f}억")
            with col3:
                if 'platform' in df_filtered.columns:
                    st.metric("방송사", f"{df_filtered['platform'].nunique()}개")
except Exception as e:
    import_error_msg = str(e)
    print(f"❌ Error: dashboard_precision_analysis 모듈 로드 중 예상치 못한 오류: {import_error_msg}")
    # 오류 시에도 기본 함수 제공
    def create_precision_analysis_tab(df_filtered, chart_generator, data_formatter, 
                                     category_colors, platform_colors, colors):
        import streamlit as st
        st.error(f"정밀분석 탭 로드 오류: {import_error_msg}")

# 추세분석 모듈 import 추가 (새로 추가!)
try:
    from dashboard_trend_tab import create_trend_analysis_tab
    HAS_TREND_ANALYSIS = True
    print("✅ dashboard_trend_analysis 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ Warning: dashboard_trend_analysis 모듈 로드 실패: {e}")
    HAS_TREND_ANALYSIS = False

# 가격 분석 모듈 import 제거 (주석 처리)
HAS_PRICE_ANALYSIS = False  # 강제로 False 설정

# 전략 분석 모듈 추가 (2025-02-16)
try:
    from dashboard_strategy_analysis import create_strategy_analysis_tab
    HAS_STRATEGY_ANALYSIS = True
    print("✅ dashboard_strategy_analysis 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ Warning: dashboard_strategy_analysis 모듈 로드 실패: {e}")
    HAS_STRATEGY_ANALYSIS = False

# 영업 전략 모듈 제거 (탭 삭제)
HAS_SALES_STRATEGY = False  # 영업 전략 탭 비활성화

# ============================================================================
# 페이지 설정
# ============================================================================
apply_page_config()

# Dark Mode + Glassmorphism CSS 스타일 적용 (데이터테이블 스타일 강화)
apply_custom_styles()

# 전략 분석 탭 스타일 제거됨 (2025-01-29)

# 추가 CSS - 입력 필드 가시성 개선
st.markdown("""
<style>
/* 사이드바 number_input 스타일 수정 - 텍스트와 버튼 가시성 개선 */
section[data-testid="stSidebar"] .stNumberInput input {
    color: #000000 !important;
    background: rgba(255, 255, 255, 0.95) !important;
    border: 1px solid rgba(0, 217, 255, 0.3) !important;
}

section[data-testid="stSidebar"] .stNumberInput button {
    color: #000000 !important;
    background: rgba(255, 255, 255, 0.8) !important;
}

section[data-testid="stSidebar"] .stNumberInput button:hover {
    background: rgba(0, 217, 255, 0.2) !important;
}

/* 상세데이터탭 검색 입력 필드 스타일 */
.stTextInput input {
    color: #000000 !important;
    background: rgba(255, 255, 255, 0.95) !important;
}

/* 페이지 번호 입력 필드 */
.stNumberInput input {
    color: #000000 !important;
    background: rgba(255, 255, 255, 0.95) !important;
}

.stNumberInput button {
    color: #000000 !important;
    background: rgba(255, 255, 255, 0.8) !important;
}

/* 다운로드 버튼 텍스트 가시성 */
.stDownloadButton button {
    color: #FFFFFF !important;
    background: linear-gradient(135deg, rgba(0, 217, 255, 0.2), rgba(124, 58, 237, 0.2)) !important;
    border: 1px solid rgba(0, 217, 255, 0.5) !important;
}

.stDownloadButton button:hover {
    background: linear-gradient(135deg, rgba(0, 217, 255, 0.3), rgba(124, 58, 237, 0.3)) !important;
    box-shadow: 0 0 20px rgba(0, 217, 255, 0.5) !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 헬퍼 함수
# ============================================================================

# 콜백 함수 정의
def toggle_platform(platform):
    """플랫폼 선택 토글"""
    with st.spinner('필터를 적용하는 중...'):
        if platform in st.session_state.selected_platforms:
            st.session_state.selected_platforms.remove(platform)
        else:
            st.session_state.selected_platforms.append(platform)

def toggle_category(category):
    """카테고리 선택 토글"""
    with st.spinner('필터를 적용하는 중...'):
        if category in st.session_state.selected_categories:
            st.session_state.selected_categories.remove(category)
        else:
            st.session_state.selected_categories.append(category)

def select_all_platforms():
    """모든 플랫폼 선택"""
    st.session_state.selected_platforms = all_platforms.copy()

def deselect_all_platforms():
    """모든 플랫폼 선택 해제"""
    st.session_state.selected_platforms = []

def select_all_categories():
    """모든 카테고리 선택"""
    st.session_state.selected_categories = all_categories.copy()

def deselect_all_categories():
    """모든 카테고리 선택 해제"""
    st.session_state.selected_categories = []

def set_period(period_type):
    """기간 설정 콜백"""
    if period_type == "오늘":
        st.session_state.start_date = actual_max_date
        st.session_state.end_date = actual_max_date
    elif period_type == "어제":
        st.session_state.start_date = actual_max_date - timedelta(days=1)
        st.session_state.end_date = actual_max_date - timedelta(days=1)
    elif period_type == "7일":
        st.session_state.start_date = max(actual_min_date, actual_max_date - timedelta(days=6))
        st.session_state.end_date = actual_max_date
    elif period_type == "14일":
        st.session_state.start_date = max(actual_min_date, actual_max_date - timedelta(days=13))
        st.session_state.end_date = actual_max_date
    elif period_type == "30일":
        st.session_state.start_date = max(actual_min_date, actual_max_date - timedelta(days=29))
        st.session_state.end_date = actual_max_date
    elif period_type == "8월~현재":
        # 8월 1일부터 현재까지
        august_first = datetime(actual_max_date.year, 8, 1).date()
        st.session_state.start_date = max(actual_min_date, august_first)
        st.session_state.end_date = actual_max_date
    else:  # 전체
        st.session_state.start_date = actual_min_date
        st.session_state.end_date = actual_max_date
    st.session_state.period_selection = period_type

def reset_all_filters():
    """전체 필터 초기화"""
    # 8월 1일부터 현재까지로 초기화
    august_first = datetime(actual_max_date.year, 8, 1).date()
    st.session_state.start_date = max(actual_min_date, august_first)
    st.session_state.end_date = actual_max_date
    st.session_state.revenue_limit = 1000000000
    st.session_state.revenue_limit_temp = 10
    st.session_state.day_type_filter = "평일만"
    st.session_state.selected_platforms = ['NS홈쇼핑']
    st.session_state.selected_categories = all_categories.copy()
    st.session_state.period_selection = "8월~현재"

def apply_revenue_filter():
    """매출액 필터 적용"""
    st.session_state.revenue_limit = st.session_state.revenue_limit_temp * 100000000

# ============================================================================
# 세션 상태 초기화
# ============================================================================

# dashboard_utils의 init_session_state 사용
init_session_state(
    current_tab=0,
    revenue_limit=1000000000,
    revenue_limit_temp=10,
    day_type_filter="평일만",
    start_date=None,
    end_date=None,
    selected_platforms=None,
    selected_categories=None,
    period_selection="8월~현재"  # 기본값을 8월~현재로 변경
)

# ============================================================================
# 데이터 로드 - ROI 계산법 변경 적용
# ============================================================================

# 데이터베이스 파일 존재 확인
if not check_database_exists("schedule.db"):
    st.error("⚠️ 데이터베이스 파일(schedule.db)을 찾을 수 없습니다.")
    st.info("💡 먼저 run_and_backup_and_dashboard.py를 실행하여 데이터를 수집하세요.")
    st.code("""
    # 터미널에서 실행:
    python run_and_backup_and_dashboard.py
    """)
    st.stop()

@st.cache_data(ttl=300)
def load_data(days_back=None):
    """데이터 로드 - ROI 계산법 변경 적용"""
    try:
        conn = sqlite3.connect("schedule.db")
        
        query = """
            SELECT * FROM schedule 
            WHERE platform != '기타'
            ORDER BY date DESC, time DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) == 0:
            st.error("데이터베이스에 데이터가 없습니다.")
            st.info("💡 데이터 수집을 먼저 실행해주세요.")
            return pd.DataFrame()
        
        # 데이터 타입 변환 강화 (데이터 로드 직후)
        numeric_columns = ['revenue', 'cost', 'units_sold', 'product_count', 'roi']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 데이터 전처리
        df['date'] = pd.to_datetime(df['date'])
        df['hour'] = df['time'].str.split(':').str[0].astype(int)
        df['weekday'] = df['date'].dt.dayofweek
        df['weekday_name'] = df['date'].dt.day_name()
        
        # Period 타입 대신 문자열 사용 (JSON 직렬화 문제 해결)
        df['month'] = df['date'].dt.strftime('%Y-%m')
        df['week'] = df['date'].dt.strftime('%Y-W%U')
        df['is_weekend'] = df['weekday'].isin([5, 6])
        
        # 채널 구분
        def is_live_channel(platform):
            platform_lower = platform.lower().strip()
            for live_ch in LIVE_CHANNELS:
                if live_ch.lower() in platform_lower:
                    if any(suffix in platform_lower for suffix in ['플러스', '마이샵', '샵플']):
                        return False
                    return True
            return False
        
        df['is_live'] = df['platform'].apply(is_live_channel)
        df['channel_type'] = np.where(df['is_live'], '생방송', '비생방송')
        
        # cost가 숫자 타입인지 확인 후 계산
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(float)
        
        # 비용 계산
        df['model_cost'] = np.where(df['is_live'], MODEL_COST_LIVE, MODEL_COST_NON_LIVE)
        df['total_cost'] = df['cost'].astype(float) + df['model_cost'].astype(float)
        
        # 실질 수익 계산 - 새로운 ROI 계산법 적용
        df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0).astype(float)
        df['real_profit'] = (df['revenue'] * REAL_MARGIN_RATE) - df['total_cost']
        
        # ROI 계산 (실질 수익 기반)
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
        
        # 단가 계산
        df['unit_price'] = np.where(
            df['units_sold'] > 0,
            df['revenue'] / df['units_sold'],
            0
        )
        
        return df
        
    except sqlite3.Error as e:
        st.error(f"데이터베이스 연결 실패: {e}")
        log_error(e, "load_data - database connection")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        log_error(e, "load_data - general error")
        if st.session_state.get('debug_mode', False):
            st.code(traceback.format_exc())
        return pd.DataFrame()

# 초기 데이터 로드
with show_loading_message('데이터를 불러오는 중...'):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        log_error(e, "initial data load")
        if st.session_state.get('debug_mode', False):
            st.code(traceback.format_exc())
        st.stop()

if len(df) == 0:
    st.error("데이터베이스에 데이터가 없습니다.")
    st.stop()

# 실제 날짜 범위
actual_min_date = df['date'].min().date()
actual_max_date = df['date'].max().date()

# 전체 방송사/카테고리 목록
all_platforms = sorted(df['platform'].unique())
all_categories = sorted(df['category'].unique())

# 초기화
if st.session_state.selected_platforms is None:
    st.session_state.selected_platforms = ['NS홈쇼핑']
    
if st.session_state.selected_categories is None:
    st.session_state.selected_categories = all_categories.copy()

# 날짜 기본값 설정 - 8월1일부터 현재까지 기본
if st.session_state.start_date is None:
    # 8월 1일로 설정 (현재 년도의 8월 1일)
    august_first = datetime(actual_max_date.year, 8, 1).date()
    # 만약 8월 1일이 데이터 최소 날짜보다 이전이면 최소 날짜 사용
    st.session_state.start_date = max(actual_min_date, august_first)
if st.session_state.end_date is None:
    st.session_state.end_date = actual_max_date

# ============================================================================
# 사이드바 필터 - 텍스트 가시성 개선
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div class="version-badge" style="background: linear-gradient(135deg, rgba(0, 217, 255, 0.2), rgba(124, 58, 237, 0.2));
                backdrop-filter: blur(10px);
                border: 1px solid rgba(0, 217, 255, 0.5);
                border-radius: 10px;
                padding: 10px;
                text-align: center;
                margin-bottom: 20px;
                color: #FFFFFF;
                font-weight: 700;
                text-shadow: 0 0 10px rgba(0, 217, 255, 0.5);">
        🚀 홈쇼핑 분석 대시보드 v20.4.0
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🎯 필터 설정")
    
    # 디버그 패널 표시
    show_debug_panel()
    
    # 필터 초기화
    st.button("🔄 전체 초기화", use_container_width=True, on_click=reset_all_filters)
    
    st.markdown("---")
    
    # 매출액 상한선 필터
    st.markdown("#### 💰 매출액 상한선")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        revenue_limit_input = st.number_input(
            "상한액 (억원)",
            min_value=1,
            max_value=100,
            value=int(st.session_state.revenue_limit_temp),
            step=1,
            key="revenue_limit_input_key_v20_4_0",
            label_visibility="collapsed"
        )
        if revenue_limit_input != st.session_state.revenue_limit_temp:
            st.session_state.revenue_limit_temp = revenue_limit_input
    
    with col2:
        st.button("적용", key="apply_revenue_limit_v20_4_0", use_container_width=True, 
                 on_click=apply_revenue_filter)
    
    st.markdown(f"""
    <div style="background: rgba(0, 217, 255, 0.1); 
                padding: 8px; 
                border-radius: 5px; 
                border-left: 3px solid #00D9FF;
                color: #FFFFFF;">
        현재 설정: <strong>{st.session_state.revenue_limit/100000000:.0f}억원</strong> 이하
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 기간 선택 - 수정된 옵션들
    st.markdown("#### 📅 기간 선택")
    
    period_options = ["8월~현재", "전체", "오늘", "어제", "7일", "14일", "30일", "사용자 지정"]
    selected_period = st.selectbox(
        "기간 선택",
        options=period_options,
        index=period_options.index(st.session_state.period_selection) 
              if st.session_state.period_selection in period_options else 0,  # 기본값 8월~현재
        label_visibility="collapsed"
    )
    
    if selected_period != "사용자 지정":
        set_period(selected_period)
    
    # 날짜 선택 (사용자 지정일 때만 활성화)
    if selected_period == "사용자 지정" or st.session_state.period_selection == "사용자 지정":
        col1, col2 = st.columns(2)
        with col1:
            st.date_input(
                "시작일",
                min_value=actual_min_date,
                max_value=actual_max_date,
                key="start_date"
            )

        with col2:
            st.date_input(
                "종료일",
                min_value=actual_min_date,
                max_value=actual_max_date,
                key="end_date"
            )
    
    start_date = st.session_state.start_date
    end_date = st.session_state.end_date
    
    # 현재 선택된 기간 표시
    if st.session_state.period_selection == "전체":
        st.success(f"📊 전체 기간 선택됨")
    else:
        st.info(f"📊 {start_date} ~ {end_date}")
    
    # 평일/주말
    st.markdown("#### 📆 요일 필터")
    day_type_options = ["전체", "평일만", "주말만"]
    st.selectbox(
        "데이터 필터",
        options=day_type_options,
        index=day_type_options.index(st.session_state.day_type_filter),
        key="day_type_filter",
        label_visibility="collapsed"
    )
    
    # 방송사 필터
    st.markdown("#### 📺 방송사 선택")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("✅ 전체", key="all_plat", use_container_width=True,
                 on_click=select_all_platforms)
    with col2:
        st.button("❌ 해제", key="none_plat", use_container_width=True,
                 on_click=deselect_all_platforms)
    
    # 방송사 체크박스
    st.markdown("""
    <div class="filter-card" style="max-height: 200px; overflow-y: auto; 
                background: rgba(255, 255, 255, 0.03); 
                padding: 10px; 
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);">
    """, unsafe_allow_html=True)
    
    # 주요 방송사 먼저 표시
    major_platforms = ['NS홈쇼핑', 'GS홈쇼핑', '현대홈쇼핑', 'CJ온스타일', '롯데홈쇼핑', '홈앤쇼핑']
    other_platforms = [p for p in all_platforms if p not in major_platforms]
    
    st.markdown("**주요 방송사**")
    cols = st.columns(2)
    for idx, platform in enumerate(major_platforms):
        if platform in all_platforms:
            col_idx = idx % 2
            with cols[col_idx]:
                is_selected = platform in st.session_state.selected_platforms
                label = platform if platform else "방송사"
                st.checkbox(
                    label,
                    value=is_selected,
                    key=f"p_{platform}_v20_4_0",
                    on_change=toggle_platform,
                    args=(platform,)
                )
    
    if other_platforms:
        st.markdown("**기타 방송사**")
        cols = st.columns(2)
        for idx, platform in enumerate(other_platforms):
            col_idx = idx % 2
            with cols[col_idx]:
                if platform:
                    display_name = platform[:10] + ".." if len(platform) > 12 else platform
                else:
                    display_name = "미지정"
                
                is_selected = platform in st.session_state.selected_platforms
                st.checkbox(
                    display_name,
                    value=is_selected,
                    key=f"p_{platform}_v20_4_0",
                    help=platform if len(platform) > 12 else None,
                    on_change=toggle_platform,
                    args=(platform,)
                )
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.info(f"선택: {len(st.session_state.selected_platforms)}/{len(all_platforms)}개")
    
    # 카테고리 필터
    st.markdown("#### 📦 카테고리 선택")
    col1, col2 = st.columns(2)
    with col1:
        st.button("✅ 전체", key="all_cat", use_container_width=True,
                 on_click=select_all_categories)
    with col2:
        st.button("❌ 해제", key="none_cat", use_container_width=True,
                 on_click=deselect_all_categories)
    
    # 카테고리 체크박스
    st.markdown("""
    <div class="filter-card" style="max-height: 200px; overflow-y: auto;
                background: rgba(255, 255, 255, 0.03);
                padding: 10px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);">
    """, unsafe_allow_html=True)
    
    # 주요 카테고리 먼저 표시
    major_categories = ['화장품/미용', '식품', '패션의류', '생활용품', '가전/디지털', '건강식품']
    other_categories = [c for c in all_categories if c not in major_categories]
    
    st.markdown("**주요 카테고리**")
    cols = st.columns(2)
    for idx, category in enumerate(major_categories):
        if category in all_categories:
            col_idx = idx % 2
            with cols[col_idx]:
                is_selected = category in st.session_state.selected_categories
                label = category if category else "카테고리"
                st.checkbox(
                    label,
                    value=is_selected,
                    key=f"c_{category}_v20_4_0",
                    on_change=toggle_category,
                    args=(category,)
                )
    
    if other_categories:
        st.markdown("**기타 카테고리**")
        cols = st.columns(2)
        for idx, category in enumerate(other_categories):
            col_idx = idx % 2
            with cols[col_idx]:
                if category:
                    display_name = category[:10] + ".." if len(category) > 12 else category
                else:
                    display_name = "미지정"
                
                is_selected = category in st.session_state.selected_categories
                st.checkbox(
                    display_name,
                    value=is_selected,
                    key=f"c_{category}_v20_4_0",
                    help=category if len(category) > 12 else None,
                    on_change=toggle_category,
                    args=(category,)
                )
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.info(f"선택: {len(st.session_state.selected_categories)}/{len(all_categories)}개")

# ============================================================================
# 필터 적용
# ============================================================================

with show_loading_message('데이터를 처리하는 중...'):
    try:
        df_filtered = df[(df['date'].dt.date >= start_date) & 
                         (df['date'].dt.date <= end_date)].copy()
        
        # 평일/주말 필터
        if st.session_state.day_type_filter == "평일만":
            df_filtered = df_filtered[df_filtered['weekday'].isin([0, 1, 2, 3, 4])]
        elif st.session_state.day_type_filter == "주말만":
            df_filtered = df_filtered[df_filtered['weekday'].isin([5, 6])]
        
        # 매출 상한 필터
        df_filtered = df_filtered[df_filtered['revenue'] <= st.session_state.revenue_limit]
        
        # 방송사 필터
        if len(st.session_state.selected_platforms) > 0:
            df_filtered = df_filtered[df_filtered['platform'].isin(st.session_state.selected_platforms)]
        else:
            df_filtered = df_filtered.iloc[0:0]
        
        # 카테고리 필터
        if len(st.session_state.selected_categories) > 0:
            df_filtered = df_filtered[df_filtered['category'].isin(st.session_state.selected_categories)]
        else:
            df_filtered = df_filtered.iloc[0:0]
    except Exception as e:
        st.error(f"필터 적용 중 오류: {e}")
        log_error(e, "apply filters")
        df_filtered = pd.DataFrame()

# 데이터 체크
if len(df_filtered) == 0:
    st.warning("선택된 필터 조건에 맞는 데이터가 없습니다.")
    st.info("💡 필터 조건을 조정해주세요.")
    st.stop()

# 매니저 인스턴스 생성
data_manager = DataManager("schedule.db")
chart_generator = ChartGenerator(COLORS, CHART_CONFIG)
data_formatter = data_manager.formatter

# ============================================================================
# 메인 대시보드 - Dark Mode + Glassmorphism
# ============================================================================

# 제목
st.markdown(
    '<h1 class="main-title">홈쇼핑 빅데이터 인사이트 플랫폼</h1>',
    unsafe_allow_html=True
)

# 날짜 범위 표시
date_range_text = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
st.markdown(f"<p style='text-align: center; color: {COLORS['text_secondary']}; margin-bottom: 10px;'>📅 분석 기간: {date_range_text}</p>", 
           unsafe_allow_html=True)

# ROI 계산법 변경 안내 표시
st.markdown(f"""
<div style='background: linear-gradient(135deg, rgba(16, 249, 129, 0.1), rgba(0, 217, 255, 0.1));
            border: 1px solid rgba(16, 249, 129, 0.3);
            border-radius: 10px;
            padding: 10px 15px;
            margin-bottom: 20px;
            text-align: center;'>
    <span style='color: #10F981; font-weight: bold;'>ℹ️ ROI 계산법 업데이트</span>
    <span style='color: #FFFFFF;'> | 실질 마진율 57.75% 적용 (전환율 75%, 원가율 13%, 수수료율 10%)</span>
</div>
""", unsafe_allow_html=True)

# 핵심 메트릭 계산 (새로운 ROI 계산법 반영)
try:
    metrics = {
        'total_revenue': df_filtered['revenue'].sum(),
        'total_broadcasts': len(df_filtered),
        'total_units': df_filtered['units_sold'].sum(),
        'total_cost': df_filtered['total_cost'].sum(),
        'total_real_profit': df_filtered['real_profit'].sum(),  # 새로운 계산법 적용된 값
        'weighted_roi': 0
    }

    if metrics['total_cost'] > 0:
        metrics['weighted_roi'] = (metrics['total_real_profit'] / metrics['total_cost']) * 100
except Exception as e:
    st.error(f"메트릭 계산 중 오류: {e}")
    log_error(e, "calculate metrics")
    metrics = {
        'total_revenue': 0,
        'total_broadcasts': 0,
        'total_units': 0,
        'total_cost': 0,
        'total_real_profit': 0,
        'weighted_roi': 0
    }

# 메트릭 카드박스 표시 - Dark Mode 스타일
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    profit_color = "positive" if metrics['total_revenue'] > 0 else "negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">📈 총 매출액</div>
        <div class="metric-value">{data_formatter.format_money(metrics['total_revenue'])}</div>
        <div class="metric-delta {profit_color}">{metrics['total_broadcasts']:,}건 방송</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💸 총 투자액</div>
        <div class="metric-value">{data_formatter.format_money(metrics['total_cost'])}</div>
        <div class="metric-delta positive">방송비+모델비</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    profit_color = "positive" if metrics['total_real_profit'] > 0 else "negative"
    profit_rate = (metrics['total_real_profit'] / metrics['total_revenue'] * 100) if metrics['total_revenue'] > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💰 실질 수익</div>
        <div class="metric-value">{data_formatter.format_money(metrics['total_real_profit'])}</div>
        <div class="metric-delta {profit_color}">수익률 {profit_rate:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    roi_color = "positive" if metrics['weighted_roi'] >= 0 else "negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">📊 투자수익률</div>
        <div class="metric-value">{metrics['weighted_roi']:.2f}%</div>
        <div class="metric-delta {roi_color}">가중평균 ROI</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    avg_units = metrics['total_units']/metrics['total_broadcasts'] if metrics['total_broadcasts'] > 0 else 0
    units_display = format_short_number(metrics['total_units'])
    avg_units_display = format_short_number(avg_units)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">📦 총 판매량</div>
        <div class="metric-value">{units_display}개</div>
        <div class="metric-delta positive">평균 {avg_units_display}/방송</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================================
# 개선된 상세 데이터 탭 생성 함수 - 수정 계획 적용
# ============================================================================

def create_detail_tab(df_filtered, data_formatter):
    """상세 데이터 탭 - UI 개선 버전 v20.4.0"""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">📋 상세 데이터</h2>', unsafe_allow_html=True)
    
    # 데이터 요약
    st.subheader("📊 데이터 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 레코드", f"{len(df_filtered):,}개")
    with col2:
        if len(df_filtered) > 0:
            date_range = f"{df_filtered['date'].min().strftime('%Y-%m-%d')} ~ {df_filtered['date'].max().strftime('%Y-%m-%d')}"
        else:
            date_range = "데이터 없음"
        st.metric("데이터 기간", date_range)
    with col3:
        st.metric("방송사 수", f"{df_filtered['platform'].nunique()}개")
    with col4:
        st.metric("카테고리 수", f"{df_filtered['category'].nunique()}개")
    
    # ========== 수정 1: 검색 기능 개선 - 1차, 2차 검색 한 줄에 배치 ==========
    st.subheader("🔍 검색")
    
    # 1차 검색과 2차 검색을 한 줄에 배치
    search_col1, search_col2 = st.columns([1, 1])
    
    with search_col1:
        # 1차 검색 - 크기 축소
        with st.form(key='search_form_1'):
            search_text_1 = st.text_input(
                "1차 검색",
                placeholder="검색어 입력 후 Enter",
                key="search_input_1",
                label_visibility="visible"
            )
            search_submitted_1 = st.form_submit_button("🔍", use_container_width=True)
    
    # 1차 검색 결과 처리
    df_after_search1 = df_filtered.copy()
    
    if search_text_1:
        mask = (
            df_after_search1['broadcast'].str.contains(search_text_1, case=False, na=False) | 
            df_after_search1['platform'].str.contains(search_text_1, case=False, na=False) | 
            df_after_search1['category'].str.contains(search_text_1, case=False, na=False)
        )
        df_after_search1 = df_after_search1[mask].copy()
        st.success(f"1차 검색 '{search_text_1}' 결과: {len(df_after_search1):,}개")
    
    with search_col2:
        # 2차 검색 - 1차 검색 결과를 다시 필터링
        with st.form(key='search_form_2'):
            search_text_2 = st.text_input(
                "2차 검색 (1차 결과 내 검색)",
                placeholder="추가 검색어 입력 후 Enter",
                key="search_input_2",
                label_visibility="visible"
            )
            search_submitted_2 = st.form_submit_button("🔍", use_container_width=True)
    
    # 2차 검색 결과 처리
    df_display = df_after_search1.copy()
    
    if search_text_2 and len(df_after_search1) > 0:
        mask = (
            df_display['broadcast'].str.contains(search_text_2, case=False, na=False) | 
            df_display['platform'].str.contains(search_text_2, case=False, na=False) | 
            df_display['category'].str.contains(search_text_2, case=False, na=False)
        )
        df_display = df_display[mask].copy()
        st.success(f"2차 검색 '{search_text_2}' 결과: {len(df_display):,}개")
    
    # ========== 수정 2: 정렬 옵션 한 줄 배치 ==========
    st.subheader("⚙️ 데이터 필터 및 정렬")
    
    # 시간대 선택, 가격대 선택, 정렬기준, 정렬순서를 한 줄에 배치
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.5, 1.5, 1.5, 1.5, 0.5])
    
    with filter_col1:
        # 시간대 선택 (크기 축소)
        time_filter = st.selectbox(
            "시간대",
            ["전체"] + [f"{h:02d}시" for h in range(24)],
            key="time_filter_v2",
            label_visibility="visible"
        )
        
        if time_filter != "전체":
            hour = int(time_filter.replace("시", ""))
            df_display = df_display[df_display['hour'] == hour]
    
    with filter_col2:
        # 가격대 선택 필터 추가
        price_ranges = ["전체", "3만원 미만", "3-5만원", "5-10만원", "10-15만원", "15-20만원", "20만원 이상"]
        price_filter = st.selectbox(
            "가격대",
            price_ranges,
            key="price_filter_v2",
            label_visibility="visible"
        )
        
        if price_filter != "전체":
            # 단가 계산
            df_display['unit_price'] = df_display['revenue'] / df_display['units_sold']
            df_display = df_display[df_display['unit_price'] > 0]
            
            if price_filter == "3만원 미만":
                df_display = df_display[df_display['unit_price'] < 30000]
            elif price_filter == "3-5만원":
                df_display = df_display[(df_display['unit_price'] >= 30000) & (df_display['unit_price'] < 50000)]
            elif price_filter == "5-10만원":
                df_display = df_display[(df_display['unit_price'] >= 50000) & (df_display['unit_price'] < 100000)]
            elif price_filter == "10-15만원":
                df_display = df_display[(df_display['unit_price'] >= 100000) & (df_display['unit_price'] < 150000)]
            elif price_filter == "15-20만원":
                df_display = df_display[(df_display['unit_price'] >= 150000) & (df_display['unit_price'] < 200000)]
            elif price_filter == "20만원 이상":
                df_display = df_display[df_display['unit_price'] >= 200000]
    
    # 표시할 컬럼 선택
    st.subheader("📋 데이터 표시")
    
    default_cols = ['date', 'time', 'platform', 'broadcast', 'category', 
                   'revenue', 'units_sold', 'cost', 'model_cost', 'roi_calculated']
    
    # 사용 가능한 컬럼만 선택
    available_cols = df_display.columns.tolist()
    default_selection = [col for col in default_cols if col in available_cols]
    
    selected_cols = st.multiselect(
        "표시할 컬럼 선택",
        options=available_cols,
        default=default_selection,
        key="display_columns_selection"
    )
    
    if selected_cols and len(df_display) > 0:
        with filter_col3:
            # 정렬 기준 (크기 축소)
            sort_col = st.selectbox(
                "정렬 기준",
                options=selected_cols,
                index=0 if 'date' not in selected_cols else selected_cols.index('date'),
                key="sort_column_v2",
                label_visibility="visible"
            )
        
        with filter_col4:
            # 정렬 순서 (버튼 크기 축소)
            sort_order = st.radio(
                "정렬 순서",
                options=['내림차순', '오름차순'],
                horizontal=True,
                key="sort_order_v2",
                label_visibility="visible"
            )
        
        with filter_col5:
            # 필터 적용 정보
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; margin-top: 20px;">
                <strong>{len(df_display):,}</strong>개
            </div>
            """, unsafe_allow_html=True)
        
        # 데이터 정렬
        df_display = df_display.sort_values(
            by=sort_col,
            ascending=(sort_order == '오름차순')
        )
        
        # ========== 수정 3 & 4: 페이지네이션 개선 ==========
        st.subheader("📄 페이지 설정")
        
        # 페이지 설정을 더 컴팩트하게
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        
        with page_col1:
            # 페이지당 행 수 (크기 축소)
            rows_per_page = st.selectbox(
                "페이지당 행 수",
                options=[10, 25, 50, 100],
                index=2,  # 기본값 50
                key="rows_per_page_v2",
                label_visibility="visible"
            )
        
        # 페이지 계산
        total_pages = max(1, len(df_display) // rows_per_page + (1 if len(df_display) % rows_per_page > 0 else 0))
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        
        # 현재 페이지가 총 페이지를 초과하지 않도록
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = total_pages
        
        with page_col2:
            # 페이지 네비게이션 버튼들 (컴팩트하게 배치)
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 1, 1])
            
            with nav_col1:
                if st.button("⏮", help="처음", key="first_page_v2"):
                    st.session_state.current_page = 1
            
            with nav_col2:
                if st.button("◀️", help="이전", disabled=(st.session_state.current_page == 1), key="prev_page_v2"):
                    st.session_state.current_page -= 1
            
            with nav_col3:
                # 페이지 직접 입력 (크기 축소)
                page_input = st.number_input(
                    "페이지",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.current_page,
                    key="page_input_v2",
                    label_visibility="collapsed"
                )
                if page_input != st.session_state.current_page:
                    st.session_state.current_page = page_input
            
            with nav_col4:
                if st.button("▶️", help="다음", disabled=(st.session_state.current_page >= total_pages), key="next_page_v2"):
                    st.session_state.current_page += 1
            
            with nav_col5:
                if st.button("⏭", help="마지막", key="last_page_v2"):
                    st.session_state.current_page = total_pages
        
        with page_col3:
            # 페이지 정보 표시
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; margin-top: 20px;">
                페이지 <strong>{st.session_state.current_page}</strong> / {total_pages}
            </div>
            """, unsafe_allow_html=True)
        
        # 현재 페이지 데이터 추출
        start_idx = (st.session_state.current_page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, len(df_display))
        
        # 데이터 포맷팅
        df_formatted = df_display.iloc[start_idx:end_idx][selected_cols].copy()
        
        # 인덱스를 1부터 시작하도록 재설정
        df_formatted.index = range(start_idx + 1, end_idx + 1)
        
        # 컬럼명 한글화
        column_mapping = {
            'date': '날짜',
            'time': '시간',
            'platform': '방송사',
            'broadcast': '방송명',
            'category': '카테고리',
            'revenue': '매출액',
            'cost': '방송정액비',
            'model_cost': '모델비용',
            'total_cost': '총비용',
            'units_sold': '판매량',
            'roi_calculated': 'ROI',
            'unit_price': '단가'
        }
        
        # 숫자 컬럼 포맷팅
        for col in df_formatted.columns:
            if col == 'date':
                # 날짜 형식 변경 (시간 제거)
                df_formatted[col] = pd.to_datetime(df_formatted[col]).dt.strftime('%Y-%m-%d')
            elif col in ['revenue', 'cost', 'model_cost', 'total_cost']:
                # 억원 단위로 변환
                df_formatted[col] = df_formatted[col].apply(lambda x: f"{x/100000000:.2f}억" if pd.notna(x) else "")
            elif col == 'roi_calculated':
                df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            elif col == 'units_sold':
                df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:,}개" if pd.notna(x) else "")
            elif col == 'unit_price':
                df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:,.0f}원" if pd.notna(x) else "")
        
        # 컬럼명을 한글로 변경
        df_formatted.columns = [column_mapping.get(col, col) for col in df_formatted.columns]
        
        # 데이터프레임 표시
        st.dataframe(
            df_formatted,
            use_container_width=True,
            height=min(600, len(df_formatted) * 35 + 50)
        )
        
        # 현재 표시 중인 행 정보
        st.caption(f"📊 {start_idx + 1:,} ~ {end_idx:,} / 전체 {len(df_display):,}행")
        
        # 엑셀 다운로드
        st.subheader("💾 데이터 내보내기")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 현재 페이지만 다운로드
            if st.button("📥 현재 페이지 다운로드", key="download_page"):
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_display.iloc[start_idx:end_idx][selected_cols].to_excel(
                        writer, 
                        index=False, 
                        sheet_name='데이터'
                    )
                
                st.download_button(
                    label="💾 Excel 다운로드",
                    data=output.getvalue(),
                    file_name=f"data_page_{st.session_state.current_page}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_page"
                )
        
        with col2:
            # 전체 데이터 다운로드
            if st.button("📥 전체 데이터 다운로드", key="download_all"):
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_display[selected_cols].to_excel(
                        writer, 
                        index=False, 
                        sheet_name='전체데이터'
                    )
                
                st.download_button(
                    label="💾 Excel 다운로드 (전체)",
                    data=output.getvalue(),
                    file_name=f"data_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_all"
                )
    
    elif len(df_display) == 0:
        st.warning("표시할 데이터가 없습니다.")
    else:
        st.info("표시할 컬럼을 선택해주세요.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# 탭 구성 - 하나의 그룹, 2줄 레이아웃
# ============================================================================

# 모든 탭을 하나의 리스트로 정의
tab_names = [
    "🎯 종합현황",        
    "📈 일일트렌드",      
    "⏰ 시간대분석",      
    "🏢 채널분석",        
    "📋 상세데이터"       
]

# 고급 분석 탭들 추가
advanced_start_idx = len(tab_names)  # 고급 분석 시작 인덱스 저장

if HAS_PRECISION_ANALYSIS:
    tab_names.append("🔬 정밀분석")

if HAS_TREND_ANALYSIS:
    tab_names.append("📊 추세분석")

if HAS_STRATEGY_ANALYSIS:
    tab_names.append("📈 전략분석")

# CSS로 탭을 2줄로 배치 - grid 레이아웃 사용
st.markdown(f"""
<style>
/* 전체 탭 컨테이너 스타일 */
.stTabs {{
    background: rgba(0, 0, 0, 0.2);
    border-radius: 10px;
    padding: 1rem;
    position: relative;
}}

/* 탭 리스트를 grid로 설정하여 2줄 배치 */
.stTabs [data-baseweb="tab-list"] {{
    display: grid !important;
    grid-template-columns: repeat(5, 1fr) !important;
    grid-template-rows: auto auto !important;
    gap: 0.5rem !important;
    background: transparent !important;
    padding: 0.5rem 0 !important;
}}

/* 첫 5개 탭 (기본 분석) - 첫번째 줄 */
.stTabs [data-baseweb="tab-list"] button:nth-child(1) {{ grid-column: 1; grid-row: 1; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(2) {{ grid-column: 2; grid-row: 1; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(3) {{ grid-column: 3; grid-row: 1; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(4) {{ grid-column: 4; grid-row: 1; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(5) {{ grid-column: 5; grid-row: 1; }}

/* 6번째 탭부터 (고급 분석) - 두번째 줄 */
.stTabs [data-baseweb="tab-list"] button:nth-child(6) {{ grid-column: 1 / span 1; grid-row: 2; margin-top: 1rem !important; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(7) {{ grid-column: 2 / span 1; grid-row: 2; margin-top: 1rem !important; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(8) {{ grid-column: 3 / span 1; grid-row: 2; margin-top: 1rem !important; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(9) {{ grid-column: 4 / span 1; grid-row: 2; margin-top: 1rem !important; }}

/* 탭 버튼 기본 스타일 */
.stTabs [data-baseweb="tab"] {{
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 0.5rem !important;
    padding: 0.75rem 1.2rem !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: rgba(255, 255, 255, 0.7) !important;
    transition: all 0.3s ease !important;
    white-space: nowrap !important;
    min-height: 45px !important;
    border-bottom: 2px solid transparent !important;
    position: relative !important;
}}

/* 탭 호버 효과 - 푸른색 계통 */
.stTabs [data-baseweb="tab"]:hover {{
    background-color: rgba(59, 130, 246, 0.08) !important;
    border-color: rgba(59, 130, 246, 0.2) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 6px rgba(59, 130, 246, 0.08) !important;
}}

/* 선택된 탭 스타일 - 푸른색 계통으로 변경 */
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%) !important;
    border: 1px solid rgba(59, 130, 246, 0.4) !important;
    border-bottom: 3px solid #3B82F6 !important;  /* 푸른색 밑줄 */
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2) !important;
    color: #60A5FA !important;  /* 밝은 푸른색 텍스트 */
    font-weight: 600 !important;
}}

/* Streamlit 기본 탭 하이라이트 바 완전히 숨기기 */
.stTabs [data-baseweb="tab-highlight"] {{
    display: none !important;
}}

/* 탭 하이라이트 관련 모든 요소 제거 */
.stTabs [data-baseweb="tab-highlight-underline"] {{
    display: none !important;
}}

/* 탭 보더 라인 제거 */
.stTabs [data-baseweb="tab-border"] {{
    display: none !important;
}}

/* 탭 리스트 하단 보더 제거 */
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: none !important;
}}

/* 탭 패널 상단 여백 */
.stTabs [data-baseweb="tab-panel"] {{
    padding-top: 2rem !important;
}}

/* 줄 사이 구분선 추가 (은은하게) */
.stTabs [data-baseweb="tab-list"]::after {{
    content: "" !important;
    position: absolute !important;
    width: calc(100% - 2rem) !important;
    height: 1px !important;
    background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.05), transparent) !important;
    bottom: calc(50% - 0.5rem) !important;
    left: 1rem !important;
}}

/* 선택되지 않은 탭의 밑줄 제거 - 명시적으로 설정 */
.stTabs [aria-selected="false"] {{
    border-bottom: 2px solid transparent !important;
}}

/* 모든 탭 버튼에서 기본 밑줄 제거 */
.stTabs button[data-baseweb="tab"]::after {{
    display: none !important;
}}

/* 탭의 기본 underline 제거 */
.stTabs button[role="tab"] {{
    border-bottom-width: 2px !important;
    border-bottom-style: solid !important;
    border-bottom-color: transparent !important;
}}

/* 선택된 탭에만 밑줄 표시 */
.stTabs button[role="tab"][aria-selected="true"] {{
    border-bottom-color: #3B82F6 !important;
}}
</style>
""", unsafe_allow_html=True)

# 하나의 탭 그룹 생성
tabs = st.tabs(tab_names)

# 각 탭 내용
tab_idx = 0

# 1. 종합현황 탭
with tabs[tab_idx]:
    with show_loading_message('차트를 생성하는 중...'):
        try:
            create_dashboard_tab(
                df_filtered, df_filtered[df_filtered['total_cost'] > 0], 
                chart_generator, data_formatter, COLORS, PLATFORM_COLORS, CATEGORY_COLORS
            )
        except Exception as e:
            st.error(f"대시보드 탭 생성 중 오류: {e}")
            log_error(e, "create_dashboard_tab")
tab_idx += 1

# 2. 일일트렌드 탭
with tabs[tab_idx]:
    with show_loading_message('트렌드를 분석하는 중...'):
        try:
            create_daily_tab(
                df_filtered, chart_generator, data_formatter,
                WEEKDAY_COLORS, COLORS
            )
        except Exception as e:
            st.error(f"트렌드 탭 생성 중 오류: {e}")
            log_error(e, "create_daily_tab")
tab_idx += 1

# 3. 시간대분석 탭
with tabs[tab_idx]:
    with show_loading_message('시간대 데이터를 분석하는 중...'):
        try:
            create_time_tab(
                df_filtered, df_filtered[df_filtered['total_cost'] > 0],
                chart_generator, data_formatter, COLORS, CATEGORY_COLORS, 
                WEEKDAY_COLORS, PLATFORM_COLORS
            )
        except Exception as e:
            st.error(f"시간대 탭 생성 중 오류: {e}")
            log_error(e, "create_time_tab")
tab_idx += 1

# 4. 채널분석 탭
with tabs[tab_idx]:
    with show_loading_message('채널 데이터를 분석하는 중...'):
        try:
            create_platform_tab(
                df_filtered, df_filtered[df_filtered['revenue'] > 0],
                chart_generator, data_manager.processor, data_formatter, 
                PLATFORM_COLORS, COLORS
            )
        except Exception as e:
            st.error(f"채널 탭 생성 중 오류: {e}")
            log_error(e, "create_platform_tab")
tab_idx += 1

# 5. 상세데이터 탭
with tabs[tab_idx]:
    create_detail_tab(df_filtered, data_formatter)
tab_idx += 1

# 6. 정밀분석 탭 (있는 경우)
if HAS_PRECISION_ANALYSIS:
    with tabs[tab_idx]:
        with show_loading_message('정밀 분석 차트를 생성하는 중...'):
            try:
                create_precision_analysis_tab(
                    df_filtered, chart_generator, data_formatter,
                    CATEGORY_COLORS, PLATFORM_COLORS, COLORS
                )
            except Exception as e:
                st.error(f"정밀 분석 탭 생성 중 오류: {e}")
                # 오류가 있어도 기본 화면 표시
                st.info("정밀분석 기능에 일시적인 문제가 있습니다.")
                if df_filtered is not None and len(df_filtered) > 0:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("총 데이터", f"{len(df_filtered):,}건")
                    with col2:
                        if 'revenue' in df_filtered.columns:
                            st.metric("총 매출", f"{df_filtered['revenue'].sum()/100000000:.1f}억")
                    with col3:
                        if 'platform' in df_filtered.columns:
                            st.metric("방송사 수", f"{df_filtered['platform'].nunique()}개")
                    with col4:
                        if 'category' in df_filtered.columns:
                            st.metric("카테고리 수", f"{df_filtered['category'].nunique()}개")
                log_error(e, "create_precision_analysis_tab")
    tab_idx += 1

# 7. 추세분석 탭
if HAS_TREND_ANALYSIS:
    with tabs[tab_idx]:
        with show_loading_message('추세를 분석하는 중...'):
            try:
                create_trend_analysis_tab(
                    df_filtered,
                    chart_generator,
                    data_formatter,
                    COLORS
                )
            except Exception as e:
                st.error(f"추세 분석 탭 생성 중 오류: {e}")
                log_error(e, "create_trend_analysis_tab")
                if st.session_state.get('debug_mode', False):
                    st.code(traceback.format_exc())
    tab_idx += 1

# 8. 전략분석 탭
if HAS_STRATEGY_ANALYSIS:
    with tabs[tab_idx]:
        with show_loading_message('전략을 분석하는 중...'):
            try:
                create_strategy_analysis_tab(
                    df_filtered,
                    df_filtered[df_filtered['total_cost'] > 0],
                    chart_generator
                )
            except Exception as e:
                st.error(f"전략 분석 탭 생성 중 오류: {e}")
                log_error(e, "create_strategy_analysis_tab")
                if st.session_state.get('debug_mode', False):
                    st.code(traceback.format_exc())
    tab_idx += 1

# 9. 영업전략 탭 (제거됨)
# 영업 전략 탭 기능이 제거되었습니다.


st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: {COLORS['text_secondary']}; padding: 20px; 
                background: linear-gradient(135deg, rgba(0, 217, 255, 0.05) 0%, rgba(124, 58, 237, 0.05) 100%); 
                border-radius: 10px; margin-top: 20px; border: 1px solid {COLORS['border']};'>
        <p style='font-size: 16px; margin: 0;'>📊 홈쇼핑 빅데이터 인사이트 플랫폼 v20.5.0</p>
        <p style='font-size: 12px; margin: 5px 0 0 0; color: {COLORS['text_muted']};'>Dark Mode + Glassmorphism Theme | 전략분석 탭 제거</p>
        <p style='font-size: 11px; margin: 5px 0 0 0; color: {COLORS['border']};'>© 2025 All rights reserved</p>
    </div>
    """,
    unsafe_allow_html=True
)