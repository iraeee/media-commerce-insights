"""
dashboard_tabs_1.py - 주요 탭 (대시보드, 방송사, 시간대) - 통합 호버 개선 
Version: 20.0.0
Last Updated: 2025-02-03

주요 개선사항:
1. 히트 상품 분석 섹션 삭제
2. 실시간 대시보드에 화장품 카테고리 TOP5 추가
3. 누적 히트 TOP5 추가 (방송별 누적매출)
4. 순서: 오늘의 화장품 TOP5 / 오늘의 히트 / 주간히트 / 월간히트 / 누적히트
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# 공통 유틸리티 함수 import
from dashboard_utils import (
    safe_to_json,
    json_to_df,
    generate_cache_key,
    format_short_number,
    show_loading_message,
    log_error
)

# dashboard_config에서 통합 호버 설정 import
from dashboard_config import (
    COLORS,
    PLATFORM_COLORS,
    CATEGORY_COLORS,
    WEEKDAY_COLORS,
    HEATMAP_COLORSCALE_REVENUE,
    HEATMAP_COLORSCALE_ROI,
    # 통합 호버 설정들
    DEFAULT_HOVER_CONFIG,
    HEATMAP_HOVER_CONFIG,
    TREEMAP_HOVER_CONFIG,
    PIE_HOVER_CONFIG,
    get_hover_config,
    emergency_hover_fix,
    create_heatmap_with_fix,
    HoverTemplates
)

# 한국식 숫자 포맷 함수 추가
def format_korean_number(value):
    """숫자를 한국식 단위로 포맷"""
    if value >= 100000000:  # 1억 이상
        return f"{value/100000000:.1f}억"
    elif value >= 10000000:  # 1천만 이상
        return f"{value/10000000:.0f}천만"
    elif value >= 1000000:   # 백만 이상
        return f"{value/1000000:.0f}백만"
    else:
        return f"{value:,.0f}"

# ============================================================================
# 대시보드 탭 - Dark Mode + Glassmorphism 테마
# ============================================================================

def create_dashboard_tab(df_filtered, df_with_cost, chart_generator, 
                        data_formatter, colors, platform_colors, category_colors):
    """대시보드 탭 생성 - 통합 호버 설정 적용"""
    
    # 세션 상태로 렌더링 제어
    if 'dashboard_rendered' not in st.session_state:
        st.session_state.dashboard_rendered = False
    
    # 이미 렌더링된 경우 캐시된 결과 사용
    if st.session_state.dashboard_rendered and 'dashboard_cache' in st.session_state:
        _render_cached_dashboard(st.session_state.dashboard_cache)
        return
    
    # Dark Mode + Glassmorphism 카드박스 스타일
    st.markdown("""
    <style>
    .dashboard-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 
            0 4px 24px rgba(0, 0, 0, 0.3),
            inset 0 0 60px rgba(255, 255, 255, 0.02);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .dashboard-card:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(0, 217, 255, 0.5);
        transform: translateY(-2px);
        box-shadow: 
            0 8px 32px rgba(0, 217, 255, 0.2),
            inset 0 0 60px rgba(0, 217, 255, 0.05);
    }
    .efficiency-card {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1));
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 217, 255, 0.3);
        color: #FFFFFF;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin: 5px;
        box-shadow: 
            0 0 20px rgba(0, 217, 255, 0.3),
            inset 0 0 20px rgba(0, 217, 255, 0.05);
        font-weight: 600;
    }
    .hit-card-box {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        height: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 실시간 대시보드 섹션
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">📊 실시간 대시보드</h2>', unsafe_allow_html=True)
    
    # 5개 칼럼으로 변경 (오늘의 화장품 / 오늘의 히트 / 주간 / 월간 / 누적)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # 캐시된 TOP 히트 계산 - safe_to_json 사용
    df_json = safe_to_json(df_filtered)
    top_hits = _calculate_top_hits_cached(df_json)
    
    with col1:
        st.markdown('<div class="hit-card-box">', unsafe_allow_html=True)
        _render_top_cosmetics(top_hits['cosmetics_today'], "💄 오늘의 화장품 TOP 5", data_formatter.format_money)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="hit-card-box">', unsafe_allow_html=True)
        _render_top_hits(top_hits['today'], "🔥 오늘의 히트 TOP 5", data_formatter.format_money)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="hit-card-box">', unsafe_allow_html=True)
        _render_top_hits(top_hits['week'], "📈 주간 히트 TOP 5", data_formatter.format_money)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="hit-card-box">', unsafe_allow_html=True)
        _render_top_hits(top_hits['month'], "🏆 월간 히트 TOP 5", data_formatter.format_money)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col5:
        st.markdown('<div class="hit-card-box">', unsafe_allow_html=True)
        _render_cumulative_hits(top_hits['cumulative'], "👑 누적 히트 TOP 5", data_formatter.format_money)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 트리맵 - 지연 로딩
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<h3 style="color: #FFFFFF;">📊 계층적 매출 구조</h3>', unsafe_allow_html=True)
    
    with st.spinner('차트 생성 중...'):
        fig_treemap = chart_generator.create_revenue_treemap_cached(df_json)
        
        # 트리맵 전용 호버 설정 적용
        fig_treemap.update_layout(hoverlabel=TREEMAP_HOVER_CONFIG)
        
        st.plotly_chart(fig_treemap, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 렌더링 완료 표시
    st.session_state.dashboard_rendered = True

@st.cache_data(ttl=60)
def _calculate_top_hits_cached(df_json):
    """TOP 히트 계산 - 캐시"""
    try:
        # JSON을 DataFrame으로 변환
        df = json_to_df(df_json)
        
        result = {}
        max_date = df['date'].max()
        
        # 오늘의 화장품 TOP 5 (새로 추가)
        today_cosmetics = df[(df['date'] == max_date) & (df['category'] == '화장품/미용')]
        result['cosmetics_today'] = today_cosmetics.nlargest(5, 'revenue')[
            ['broadcast', 'time', 'platform', 'revenue', 'roi_calculated']
        ].to_dict('records')
        
        # 오늘
        today_data = df[df['date'] == max_date]
        result['today'] = today_data.nlargest(5, 'revenue')[
            ['broadcast', 'time', 'category', 'platform', 'revenue', 'roi_calculated']
        ].to_dict('records')
        
        # 주간
        week_ago = max_date - timedelta(days=7)
        week_data = df[df['date'] > week_ago]
        result['week'] = week_data.nlargest(5, 'revenue')[
            ['broadcast', 'time', 'category', 'platform', 'revenue', 'roi_calculated']
        ].to_dict('records')
        
        # 월간 - month 컬럼 재생성
        df['month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)
        month_data = df[df['month'] == df['month'].max()]
        result['month'] = month_data.nlargest(5, 'revenue')[
            ['broadcast', 'time', 'category', 'platform', 'revenue', 'roi_calculated']
        ].to_dict('records')
        
        # 누적 히트 TOP 5 (새로 추가) - 방송별 누적 매출과 시간대
        cumulative = df.groupby('broadcast').agg({
            'revenue': 'sum',
            'roi_calculated': 'mean',
            'platform': 'first',
            'category': 'first',
            'time': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]  # 가장 많이 나온 시간대
        }).reset_index()
        result['cumulative'] = cumulative.nlargest(5, 'revenue')[
            ['broadcast', 'time', 'category', 'platform', 'revenue', 'roi_calculated']
        ].to_dict('records')
        
        return result
    except Exception as e:
        log_error(e, "_calculate_top_hits_cached")
        return {
            'cosmetics_today': [],
            'today': [],
            'week': [],
            'month': [],
            'cumulative': []
        }

@st.cache_data(ttl=60)
def _calculate_efficient_hours_cached(df_json):
    """효율적인 시간대 계산 - 캐시"""
    try:
        df = json_to_df(df_json)
        
        # 벡터화 연산으로 필터링
        mask = ((df['hour'].between(6, 11)) | (df['hour'].between(17, 23)))
        df_valid = df[mask]
        
        # 빠른 집계
        hourly_eff = df_valid.groupby('hour').agg({
            'revenue': 'mean',
            'total_cost': 'mean',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).rename(columns={'broadcast': 'count'})
        
        # 필터링 및 정렬
        hourly_eff = hourly_eff[hourly_eff['count'] >= 5]
        hourly_eff['efficiency'] = hourly_eff['revenue'] / hourly_eff['total_cost']
        
        return hourly_eff.nlargest(5, 'roi_calculated').to_dict('index')
    except Exception as e:
        log_error(e, "_calculate_efficient_hours_cached")
        return {}

def _render_top_cosmetics(data, title, format_money):
    """화장품 TOP 5 렌더링 - 네온 색상"""
    st.markdown(f'<div style="font-weight: bold; font-size: 16px; margin-bottom: 15px; color: #FF69B4;">{title}</div>', 
                unsafe_allow_html=True)
    
    # 화장품 전용 색상 (핑크/보라)
    rank_colors = {0: "#FF69B4", 1: "#DA70D6", 2: "#BA55D3", 3: "#9370DB", 4: "#8B7AA8"}
    
    for idx, item in enumerate(data):
        broadcast_text = item['broadcast'][:35] + "..." if len(item['broadcast']) > 35 else item['broadcast']
        
        st.markdown(f"""
        <div style="margin-bottom: 10px; padding: 8px; background: rgba(255, 105, 180, 0.05); 
                    border-radius: 6px; border-left: 3px solid {rank_colors.get(idx, '#FF69B4')};">
            <span style="background: {rank_colors.get(idx, '#FF69B4')}; color: #0A0B1E; padding: 1px 6px; 
                         border-radius: 50%; font-weight: bold; margin-right: 8px; font-size: 11px;">{idx+1}</span>
            <div style="margin-top: 5px;">
                <strong style="color: #FFFFFF; font-size: 13px;">{broadcast_text}</strong><br>
                <span style="color: #FFFFFF; font-size: 12px; opacity: 0.8;">
                    {item['time']} | {item['platform']}
                </span><br>
                <span style="color: #00D9FF; font-weight: bold; font-size: 12px;">{format_money(item['revenue'])}</span> | 
                <span style="color: #10F981; font-size: 11px;">ROI {item['roi_calculated']:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def _render_top_hits(data, title, format_money):
    """TOP 히트 렌더링 - Dark Mode 네온 색상"""
    st.markdown(f'<div style="font-weight: bold; font-size: 16px; margin-bottom: 15px; color: #00D9FF;">{title}</div>', 
                unsafe_allow_html=True)
    
    # 네온 순위 색상
    rank_colors = {0: "#00D9FF", 1: "#7C3AED", 2: "#FF0080", 3: "#FFD93D", 4: "#10F981"}
    
    for idx, item in enumerate(data):
        broadcast_text = item['broadcast'][:35] + "..." if len(item['broadcast']) > 35 else item['broadcast']
        
        st.markdown(f"""
        <div style="margin-bottom: 10px; padding: 8px; background: rgba(255, 255, 255, 0.03); 
                    border-radius: 6px; border-left: 3px solid {rank_colors.get(idx, '#FFD93D')};">
            <span style="background: {rank_colors.get(idx, '#FFD93D')}; color: #0A0B1E; padding: 1px 6px; 
                         border-radius: 50%; font-weight: bold; margin-right: 8px; font-size: 11px;">{idx+1}</span>
            <div style="margin-top: 5px;">
                <strong style="color: #FFFFFF; font-size: 13px;">{broadcast_text}</strong><br>
                <span style="color: #FFFFFF; font-size: 12px; opacity: 0.8;">
                    {item['time']} | {item['category'][:8]} | {item['platform']}
                </span><br>
                <span style="color: #00D9FF; font-weight: bold; font-size: 12px;">{format_money(item['revenue'])}</span> | 
                <span style="color: #10F981; font-size: 11px;">ROI {item['roi_calculated']:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def _render_cumulative_hits(data, title, format_money):
    """누적 히트 TOP 5 렌더링 - 누적 매출과 주요 시간대 표시"""
    st.markdown(f'<div style="font-weight: bold; font-size: 16px; margin-bottom: 15px; color: #FFD700;">{title}</div>', 
                unsafe_allow_html=True)
    
    # 골드 계열 색상 (누적 강조)
    rank_colors = {0: "#FFD700", 1: "#FFA500", 2: "#FF8C00", 3: "#FF6347", 4: "#CD853F"}
    
    for idx, item in enumerate(data):
        broadcast_text = item['broadcast'][:35] + "..." if len(item['broadcast']) > 35 else item['broadcast']
        
        st.markdown(f"""
        <div style="margin-bottom: 10px; padding: 8px; background: rgba(255, 215, 0, 0.05); 
                    border-radius: 6px; border-left: 3px solid {rank_colors.get(idx, '#FFD700')};">
            <span style="background: {rank_colors.get(idx, '#FFD700')}; color: #0A0B1E; padding: 1px 6px; 
                         border-radius: 50%; font-weight: bold; margin-right: 8px; font-size: 11px;">{idx+1}</span>
            <div style="margin-top: 5px;">
                <strong style="color: #FFFFFF; font-size: 13px;">{broadcast_text}</strong><br>
                <span style="color: #FFFFFF; font-size: 12px; opacity: 0.8;">
                    주시간대: {item['time']} | {item['category'][:8]} | {item['platform']}
                </span><br>
                <span style="color: #FFD700; font-weight: bold; font-size: 12px;">누적: {format_money(item['revenue'])}</span> | 
                <span style="color: #10F981; font-size: 11px;">평균 ROI {item['roi_calculated']:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def _render_efficient_hours(data, colors, format_money):
    """효율적인 시간대 렌더링 - Dark Mode 네온 색상"""
    cols = st.columns(5)
    
    for idx, (hour, metrics) in enumerate(data.items()):
        with cols[idx]:
            st.markdown(f"""
            <div class="efficiency-card">
                <div style="font-size: 28px; font-weight: 700; margin-bottom: 10px; color: #FFFFFF;">{hour}시</div>
                <div style="font-size: 12px; color: #FFFFFF; opacity: 0.9; margin-bottom: 5px;">실질 ROI</div>
                <div style="font-size: 24px; font-weight: 600; margin-bottom: 10px; color: #10F981;">
                    {metrics['roi_calculated']:.1f}%
                </div>
                <div style="font-size: 11px; color: #FFFFFF; opacity: 0.8;">효율성 {metrics['efficiency']:.2f}</div>
                <div style="font-size: 10px; color: #FFFFFF; opacity: 0.7; margin-top: 5px;">
                    예상: {format_money(metrics['revenue'])}
                </div>
            </div>
            """, unsafe_allow_html=True)

def _render_cached_dashboard(cache_data):
    """캐시된 대시보드 렌더링"""
    st.info("📊 캐시된 대시보드 데이터를 표시합니다")

# ============================================================================
# 방송사 분석 탭 - 통합 호버 설정 적용
# ============================================================================

def create_platform_tab(df_filtered, df_filtered_nonzero, chart_generator,
                       data_processor, data_formatter, platform_colors, colors):
    """방송사 분석 탭 - 통합 호버 설정 적용"""
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">🏢 방송사별 분석</h2>', unsafe_allow_html=True)
    
    # 탭 내 상태 관리
    if 'platform_tab_state' not in st.session_state:
        st.session_state.platform_tab_state = {
            'trend_platform': None,
            'heatmap_platform': None
        }
    
    # 중위값 및 사분위수 그래프 추가
    st.subheader("📊 방송사별 시간대 매출 분포 (중위값 및 사분위수)")
    
    # 방송사 목록 준비
    platform_list = sorted(df_filtered['platform'].unique())
    platform_options = ['전체'] + platform_list
    
    # NS홈쇼핑 기본값
    default_index = next((i for i, p in enumerate(platform_options) 
                         if 'NS' in p or 'ns' in p), 0)
    
    selected_platform_trend = st.selectbox(
        "방송사 선택",
        options=platform_options,
        index=default_index,
        key="platform_boxplot_select_v20"
    )
    
    # 캐시된 그래프 생성
    df_json = safe_to_json(df_filtered)
    platform_colors_json = json.dumps(PLATFORM_COLORS)
    
    if selected_platform_trend == '전체':
        fig_boxplot = _create_all_platforms_boxplot_cached(df_json, platform_colors_json)
    else:
        fig_boxplot = _create_single_platform_boxplot_cached(df_json, selected_platform_trend)
    
    if fig_boxplot:
        # 기본 호버 설정 적용
        fig_boxplot.update_layout(hoverlabel=DEFAULT_HOVER_CONFIG)
        st.plotly_chart(fig_boxplot, use_container_width=True)
        st.info("📊 박스플롯: 중위값(선), 1사분위수~3사분위수(박스), 최소/최대값(수염)")
    
    # 방송사별 종합 성과
    st.subheader("🏢 방송사별 종합 성과")
    
    fig_platform = _create_platform_comparison_optimized(
        df_filtered_nonzero,
        PLATFORM_COLORS,
        data_formatter.format_money
    )
    # 기본 호버 설정 적용
    fig_platform.update_layout(hoverlabel=DEFAULT_HOVER_CONFIG)
    st.plotly_chart(fig_platform, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# 새로운 캐시 함수들 추가 - 통합 호버 설정 적용

@st.cache_data(ttl=300)
def _create_single_platform_boxplot_cached(df_json, platform):
    """개별 방송사 시간대별 박스플롯 - 캐시"""
    try:
        df = json_to_df(df_json)
        platform_data = df[df['platform'] == platform]
        
        if len(platform_data) == 0:
            return None
        
        fig = go.Figure()
        
        for hour in range(24):
            hour_data = platform_data[platform_data['hour'] == hour]['revenue']
            if len(hour_data) > 0:
                fig.add_trace(go.Box(
                    y=hour_data,
                    name=f"{hour}시",
                    boxmean='sd',  # 평균과 표준편차 표시
                    marker_color='#00D9FF',  # 네온 시안
                    hovertemplate=HoverTemplates.BOXPLOT
                ))
        
        fig.update_layout(
            title=f"{platform} 시간대별 매출 분포",
            xaxis_title="시간대",
            yaxis_title="매출액",
            height=460,
            showlegend=False,
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            xaxis=dict(color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)'),
            yaxis=dict(color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)'),
            hoverlabel=DEFAULT_HOVER_CONFIG
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_single_platform_boxplot_cached")
        return None

@st.cache_data(ttl=300)
def _create_all_platforms_boxplot_cached(df_json, platform_colors_json):
    """전체 방송사 비교 박스플롯 - 캐시"""
    try:
        df = json_to_df(df_json)
        
        # platform_colors_json이 이미 dict인지 확인
        if isinstance(platform_colors_json, dict):
            platform_colors = platform_colors_json
        else:
            platform_colors = json.loads(platform_colors_json)
        
        # 상위 8개 방송사만 선택
        top_platforms = df.groupby('platform')['revenue'].sum().nlargest(8).index.tolist()
        
        fig = make_subplots(
            rows=2, cols=4,
            subplot_titles=top_platforms,
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # 네온 색상 리스트
        neon_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', '#FFD93D', '#FF6B35', '#00FFB9', '#FF3355']
        
        for idx, platform in enumerate(top_platforms):
            row = idx // 4 + 1
            col = idx % 4 + 1
            
            platform_data = df[df['platform'] == platform]
            
            # 방송사별 고정 색상 또는 네온
            if platform in platform_colors:
                color = platform_colors[platform]
            else:
                color = neon_colors[idx % len(neon_colors)]
            
            # 시간대별 데이터 수집
            for hour in range(24):
                hour_data = platform_data[platform_data['hour'] == hour]['revenue']
                if len(hour_data) > 0:
                    fig.add_trace(
                        go.Box(
                            y=hour_data,
                            name=f"{hour}시",
                            marker_color=color,
                            showlegend=False
                        ),
                        row=row, col=col
                    )
        
        fig.update_layout(
            title="상위 8개 방송사 시간대별 매출 분포",
            height=690,
            showlegend=False,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=DEFAULT_HOVER_CONFIG
        )
        
        # 모든 축 색상 흰색으로
        fig.update_xaxes(color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)')
        fig.update_yaxes(color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)')
        
        return fig
    except Exception as e:
        log_error(e, "_create_all_platforms_boxplot_cached")
        return None

@st.cache_data(ttl=300)
def _create_all_platforms_trend_cached(df_json, platform_colors_json):
    """전체 방송사 시간대 추이 - 캐시"""
    try:
        df = json_to_df(df_json)
        
        # platform_colors_json이 이미 dict인지 확인
        if isinstance(platform_colors_json, dict):
            platform_colors = platform_colors_json
        else:
            platform_colors = json.loads(platform_colors_json)
        
        # 상위 16개 방송사
        top_platforms = df.groupby('platform')['revenue'].sum().nlargest(16).index.tolist()
        
        fig = go.Figure()
        
        # 네온 색상 리스트
        neon_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', '#FFD93D', 
                      '#FF6B35', '#00FFB9', '#FF3355', '#4ECDC4', '#B24BF3',
                      '#54E346', '#FFB700', '#FEB692', '#48DBFB', '#32FF7E', '#7EFFF5']
        
        # 벡터화된 집계
        for idx, platform in enumerate(top_platforms):
            platform_data = df[df['platform'] == platform]
            
            # numpy 배열로 빠른 집계
            hourly_trend = platform_data.groupby('hour')['revenue'].mean().reindex(
                range(24), fill_value=0
            )
            
            # 색상 결정 - 방송사별 고정 색상 우선, 없으면 네온
            if platform in platform_colors:
                color = platform_colors[platform]
                line_width = 3
            else:
                color = neon_colors[idx % len(neon_colors)]
                line_width = 2
            
            # NS홈쇼핑 강조
            if 'NS' in platform or 'ns' in platform:
                line_width = 4
            
            fig.add_trace(go.Scatter(
                x=list(range(24)),
                y=hourly_trend.values,
                mode='lines+markers',
                name=platform[:20],
                line=dict(color=color, width=line_width),
                marker=dict(size=8 if line_width >= 3 else 6),
                visible=True if idx < 8 else 'legendonly',
                hovertemplate=HoverTemplates.TIMESERIES
            ))
        
        fig.update_layout(
            title="상위 16개 방송사 시간대별 평균 매출",
            xaxis=dict(
                title="시간대",
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i}시" for i in range(24)],
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            yaxis=dict(
                title="평균 매출 (원)", 
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            height=600,
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=DEFAULT_HOVER_CONFIG
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_all_platforms_trend_cached")
        return None

@st.cache_data(ttl=300)
def _create_single_platform_trend_cached(df_json, platform):
    """개별 방송사 시간대 추이 - 캐시"""
    try:
        df = json_to_df(df_json)
        platform_data = df[df['platform'] == platform]
        
        if len(platform_data) == 0:
            return None
        
        # 벡터화 집계
        hourly_trend = platform_data.groupby('hour').agg({
            'revenue': 'mean',
            'roi_calculated': 'mean'
        }).reindex(range(24), fill_value=0)
        
        fig = go.Figure()
        
        # 방송사별 색상 결정
        if platform in PLATFORM_COLORS:
            bar_color = PLATFORM_COLORS[platform]
            line_color = bar_color
        else:
            bar_color = '#00D9FF'  # 네온 시안
            line_color = '#FF0080'  # 네온 핑크
        
        # 매출 막대
        fig.add_trace(go.Bar(
            x=list(range(24)),
            y=hourly_trend['revenue'].values,
            name='평균 매출',
            marker_color=bar_color,
            opacity=0.7,
            hovertemplate=HoverTemplates.REVENUE_WITH_TIME
        ))
        
        # ROI 선
        fig.add_trace(go.Scatter(
            x=list(range(24)),
            y=hourly_trend['roi_calculated'].values,
            name='평균 ROI',
            mode='lines+markers',
            marker=dict(color=line_color, size=8),
            yaxis='y2',
            line=dict(width=3, color=line_color),
            hovertemplate=HoverTemplates.ROI
        ))
        
        fig.update_layout(
            title=f"{platform} 시간대별 성과",
            xaxis=dict(
                title="시간대",
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i}시" for i in range(24)],
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            yaxis=dict(
                title="평균 매출 (원)", 
                side='left',
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            yaxis2=dict(
                title="평균 ROI (%)", 
                overlaying='y', 
                side='right',
                color='#FF0080'
            ),
            height=400,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=DEFAULT_HOVER_CONFIG
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_single_platform_trend_cached")
        return None

def _create_platform_comparison_optimized(df, platform_colors, format_money):
    """방송사별 종합 성과 - Dark Mode 네온 테마"""
    try:
        # 필요한 데이터만 선택
        df_nonzero = df[df['revenue'] > 0]
        
        # 벡터화 집계
        platform_stats = df_nonzero.groupby('platform').agg({
            'revenue': ['sum', 'mean'],
            'roi_calculated': 'mean',
            'is_live': 'first'
        }).reset_index()
        
        platform_stats.columns = ['platform', 'revenue_sum', 'revenue_mean', 'roi_mean', 'is_live']
        platform_stats['channel_type'] = np.where(platform_stats['is_live'], '생방송', '비생방송')
        platform_stats = platform_stats.nlargest(20, 'revenue_sum')
        
        # 방송사별 네온 색상 적용
        colors_list = []
        for platform in platform_stats['platform']:
            if platform in platform_colors:
                colors_list.append(platform_colors[platform])
            else:
                # 기본 네온 색상
                default_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', 
                                '#FFD93D', '#FF6B35', '#00FFB9', '#FF3355']
                colors_list.append(default_colors[len(colors_list) % len(default_colors)])
        
        fig = go.Figure()
        
        # 막대 그래프 - 네온 색상
        fig.add_trace(go.Bar(
            x=platform_stats['platform'].values,
            y=platform_stats['revenue_sum'].values,
            name='총 매출',
            marker=dict(
                color=colors_list,
                line=dict(color='rgba(255, 255, 255, 0.2)', width=1)
            ),
            text=[f"{platform_stats.iloc[i]['channel_type']}<br>{format_money(v)}" 
                  for i, v in enumerate(platform_stats['revenue_sum'])],
            textposition='outside',
            textfont=dict(color='#FFFFFF'),
            hovertemplate=HoverTemplates.PLATFORM
        ))
        
        # ROI 선 - 네온 핑크
        fig.add_trace(go.Scatter(
            x=platform_stats['platform'].values,
            y=platform_stats['roi_mean'].values,
            mode='lines+markers+text',
            name='평균 실질 ROI (%)',
            marker=dict(
                color='#FF0080',
                size=10,
                line=dict(color='#FFFFFF', width=2)
            ),
            yaxis='y2',
            line=dict(color='#FF0080', width=3),
            text=[f"{v:.1f}%" for v in platform_stats['roi_mean']],
            textposition='top center',
            textfont=dict(color='#FF0080'),
            hovertemplate=HoverTemplates.ROI
        ))
        
        fig.update_layout(
            xaxis=dict(
                title="방송사", 
                tickangle=-45,
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            yaxis=dict(
                title="매출", 
                side='left',
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            yaxis2=dict(
                title="평균 실질 ROI (%)", 
                overlaying='y', 
                side='right',
                color='#FF0080'
            ),
            height=600,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=DEFAULT_HOVER_CONFIG
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_platform_comparison_optimized")
        return None

# ============================================================================
# 시간대 분석 탭 - 통합 호버 설정 적용
# ============================================================================

def create_time_tab(df_filtered, df_with_cost, chart_generator, 
                   data_formatter, colors, category_colors, weekday_colors, platform_colors):
    """시간대 분석 탭 - 통합 호버 설정 적용"""
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">⏰ 시간대별 분석</h2>', unsafe_allow_html=True)
    
    # 시간대별 방송사 매출 추이
    st.subheader("🌟 시간대별 방송사 매출 추이")
    
    col1, col2 = st.columns(2)
    
    with col1:
        day_filter = st.selectbox(
            "요일 선택",
            ["전체", "월", "화", "수", "목", "금", "토", "일"],
            key="time_platform_day_filter_v20"
        )
    
    with col2:
        revenue_type = st.radio(
            "매출 표시 방식",
            ["평균매출", "총매출"],
            horizontal=True,
            key="time_platform_revenue_type_v20"
        )
    
    # 캐시된 그래프 생성
    df_json = safe_to_json(df_filtered)
    platform_colors_json = json.dumps(PLATFORM_COLORS)
    fig_platform_time = _create_platform_hourly_lines_cached(
        df_json,
        day_filter,
        revenue_type,
        platform_colors_json
    )
    
    if fig_platform_time:
        # 기본 호버 설정 적용
        fig_platform_time.update_layout(hoverlabel=DEFAULT_HOVER_CONFIG)
        st.plotly_chart(fig_platform_time, use_container_width=True)
    
    # 시간대별 매출과 실질 ROI
    st.subheader("📊 시간대별 매출 및 실질 ROI")
    
    revenue_type_bar = st.radio(
        "매출 표시 방식",
        ["평균 매출", "총 매출"],
        horizontal=True,
        key="time_revenue_type_bar_v20"
    )
    
    # 최적화된 차트 생성
    fig_bar = _create_hourly_revenue_bar_optimized(
        df_filtered,
        revenue_type_bar,
        data_formatter.format_money
    )
    if fig_bar:
        # 기본 호버 설정 적용
        fig_bar.update_layout(hoverlabel=DEFAULT_HOVER_CONFIG)
        st.plotly_chart(fig_bar, use_container_width=True)
    

    # 카테고리별 매출 분포 추가 (카테고리 탭에서 이동)
    st.markdown("---")
    st.subheader("🏷️ 카테고리별 매출 분포")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 파이 차트
        category_revenue = df_filtered.groupby('category')['revenue'].sum().reset_index()
        category_revenue = category_revenue.sort_values('revenue', ascending=False)
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=category_revenue['category'],
            values=category_revenue['revenue'],
            hole=0.3,
            marker=dict(colors=[CATEGORY_COLORS.get(cat, '#808080') 
                              for cat in category_revenue['category']])
        )])
        
        fig_pie.update_layout(
            title="카테고리별 매출 비중",
            height=440,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='#FFFFFF')
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 바 차트
        fig_bar = go.Figure(data=[go.Bar(
            x=category_revenue['revenue'],
            y=category_revenue['category'],
            orientation='h',
            marker=dict(color=[CATEGORY_COLORS.get(cat, '#808080') 
                             for cat in category_revenue['category']]),
            text=[format_korean_number(v) for v in category_revenue['revenue']],
            textposition='outside'
        )])
        
        fig_bar.update_layout(
            title="카테고리별 매출액",
            height=440,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            xaxis=dict(title="매출액"),
            yaxis=dict(title="")
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def _create_platform_hourly_lines_cached(df_json, day_filter, revenue_type, platform_colors_json):
    """시간대별 방송사 매출 추이 - 캐시"""
    try:
        df = json_to_df(df_json)
        
        # platform_colors_json이 이미 dict인지 확인
        if isinstance(platform_colors_json, dict):
            platform_colors = platform_colors_json
        else:
            platform_colors = json.loads(platform_colors_json)
        
        # 요일 필터링
        if day_filter != "전체":
            weekday_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
            if day_filter in weekday_map:
                df = df[df['weekday'] == weekday_map[day_filter]]
        
        # 집계 방식
        agg_func = 'mean' if revenue_type == "평균매출" else 'sum'
        
        # 상위 16개 방송사
        top_platforms = df.groupby('platform')['revenue'].sum().nlargest(16).index.tolist()
        
        fig = go.Figure()
        
        # 네온 색상 리스트
        neon_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', '#FFD93D', 
                      '#FF6B35', '#00FFB9', '#FF3355']
        
        for idx, platform in enumerate(top_platforms):
            platform_data = df[df['platform'] == platform]
            
            # 벡터화 집계
            hourly_data = platform_data.groupby('hour')['revenue'].agg(agg_func).reindex(
                range(24), fill_value=0
            )
            
            # 색상 결정 - 방송사별 고정 색상 우선
            if platform in platform_colors:
                color = platform_colors[platform]
                line_width = 3
            else:
                color = neon_colors[idx % len(neon_colors)]
                line_width = 2
            
            # NS홈쇼핑 강조
            if 'NS' in platform or 'ns' in platform:
                line_width = 4
            
            fig.add_trace(go.Scatter(
                x=list(range(24)),
                y=hourly_data.values / 1e8,  # 억원 단위
                mode='lines+markers',
                name=platform,
                line=dict(color=color, width=line_width),
                marker=dict(size=10 if line_width >= 3 else 6),
                hovertemplate='%{x}시<br>%{y:.1f}억원<extra></extra>'
            ))
        
        fig.update_layout(
            xaxis=dict(
                title="시간대",
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i}시" for i in range(24)],
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            yaxis=dict(
                title=f"{revenue_type} (억원)",
                gridcolor='rgba(255, 255, 255, 0.06)',
                color='#FFFFFF'
            ),
            height=500,
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=DEFAULT_HOVER_CONFIG
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_platform_hourly_lines_cached")
        return None

def _create_hourly_revenue_bar_optimized(df, revenue_type, format_money):
    """시간대별 매출 막대 차트 - Dark Mode 네온"""
    try:
        # 벡터화 필터링
        df_nonzero = df[df['revenue'] > 0]
        
        # 집계 타입
        if revenue_type == "평균 매출":
            hourly_stats = df_nonzero.groupby('hour')['revenue'].mean()
            hourly_roi = df_nonzero.groupby('hour')['roi_calculated'].mean()
        else:
            hourly_stats = df.groupby('hour')['revenue'].sum()
            hourly_roi = df.groupby('hour')['roi_calculated'].mean()
        
        # ROI 값이 있는 시간대만 필터링
        valid_hours = hourly_roi[hourly_roi != 0].index
        
        # 0-23시 데이터 준비 (ROI가 있는 시간대만)
        hourly_data = pd.DataFrame({
            'hour': valid_hours,
            'revenue': hourly_stats.reindex(valid_hours, fill_value=0).values,
            'roi': hourly_roi.reindex(valid_hours, fill_value=0).values
        })
        
        # 데이터가 없는 경우 처리
        if len(hourly_data) == 0:
            hourly_data = pd.DataFrame({
                'hour': range(24),
                'revenue': hourly_stats.reindex(range(24), fill_value=0).values,
                'roi': hourly_roi.reindex(range(24), fill_value=0).values
            })
        
        # 네온 그라디언트 색상 (네모박스 스타일)
        max_revenue = hourly_data['revenue'].max() if len(hourly_data) > 0 else 1
        bar_colors = []
        for v in hourly_data['revenue']:
            if v > max_revenue * 0.8:
                bar_colors.append('rgba(16, 249, 129, 0.85)')  # 네온 그린 + 투명도
            elif v > max_revenue * 0.6:
                bar_colors.append('rgba(0, 217, 255, 0.85)')  # 네온 시안 + 투명도
            elif v > max_revenue * 0.4:
                bar_colors.append('rgba(124, 58, 237, 0.85)')  # 네온 퍼플 + 투명도
            elif v > max_revenue * 0.2:
                bar_colors.append('rgba(255, 217, 61, 0.85)')  # 네온 옐로우 + 투명도
            else:
                bar_colors.append('rgba(255, 107, 53, 0.85)')  # 네온 오렌지 + 투명도
        
        fig = go.Figure()
        
        # 막대 그래프 (네모박스 스타일)
        fig.add_trace(go.Bar(
            x=hourly_data['hour'],
            y=hourly_data['revenue'],
            name='매출',
            marker=dict(
                color=bar_colors,
                line=dict(color='rgba(255, 255, 255, 0.4)', width=2),
                pattern=dict(shape="")  # 패턴 제거로 깔끔한 박스
            ),
            text=[format_money(v) for v in hourly_data['revenue']],
            textposition='outside',
            textfont=dict(size=11, color='#FFFFFF', family='Inter'),
            hovertemplate=HoverTemplates.REVENUE_WITH_TIME
        ))
        
        # ROI 선 그래프 (부드러운 선)
        fig.add_trace(go.Scatter(
            x=hourly_data['hour'],
            y=hourly_data['roi'],
            name='ROI (%)',
            yaxis='y2',
            mode='lines+markers',
            line=dict(
                color='#FF3355', 
                width=3,
                shape='spline',  # 부드러운 곡선
                smoothing=1.2
            ),
            marker=dict(
                size=10, 
                color='#FF3355', 
                symbol='diamond',
                line=dict(color='rgba(255, 255, 255, 0.8)', width=2)
            ),
            hovertemplate=HoverTemplates.ROI
        ))
        
        # X축 라벨 설정
        ticktext = [f"{int(h)}시" for h in hourly_data['hour']]
        
        fig.update_layout(
            xaxis=dict(
                title="시간대",
                tickmode='array',
                ticktext=ticktext,
                tickvals=list(hourly_data['hour']),
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.08)',
                showgrid=True
            ),
            yaxis=dict(
                title="매출액",
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.08)',
                showgrid=True
            ),
            yaxis2=dict(
                title="ROI (%)",
                overlaying='y',
                side='right',
                color='#FF3355',
                gridcolor='rgba(255, 51, 85, 0.15)',
                showgrid=True
            ),
            height=500,
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(20, 20, 40, 0.4)',  # 배경색 추가
            font=dict(color='#FFFFFF', family='Inter, sans-serif'),
            hoverlabel=dict(
                bgcolor='rgba(10, 11, 30, 0.95)',
                bordercolor='#00D9FF',
                font=dict(size=14, color='#FFFFFF')
            ),
            # 네모박스 스타일 추가
            margin=dict(l=60, r=60, t=40, b=60),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(20, 20, 40, 0.6)',
                bordercolor='rgba(255, 255, 255, 0.2)',
                borderwidth=1
            )
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_hourly_revenue_bar_optimized")
        return None