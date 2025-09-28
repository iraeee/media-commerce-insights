"""
dashboard_tabs_2_v8_integrated.py - 보조 탭 (트렌드, 카테고리) - 수정 버전 v20.3.2
Version: 20.3.2
Updated: 2025-01-XX

주요 수정사항:
1. 일일트렌드탭 - 전체 기간 표시, Y축 간격 조정, 성능 최적화
2. 카테고리분석탭 - 효율성 분석 그래프 삭제
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

# dashboard_config에서 통합 호버 설정 및 색상 import
from dashboard_config import (
    COLORS,
    PLATFORM_COLORS,
    WEEKDAY_COLORS,
    HEATMAP_COLORSCALE_REVENUE,
    HEATMAP_COLORSCALE_ROI,
    # 통합 호버 설정들
    DEFAULT_HOVER_CONFIG,
    HEATMAP_HOVER_CONFIG,
    SIMPLE_HOVER_CONFIG,
    # 호버 템플릿
    HoverTemplates,
    # 유틸리티 함수들
    ROI_COLORSCALE_OPTIMIZED,
    normalize_heatmap_data,
    optimize_roi_heatmap_colors,
    emergency_hover_fix,
    fix_heatmap_data,
    get_standard_hover_template,
    # ROI 계산 관련 상수들
    CONVERSION_RATE,
    REAL_MARGIN_RATE
)

# 생방송 채널 정의 (모델비 계산용)
LIVE_CHANNELS = {
    '현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', 
    '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑'
}

# 모델비 설정
MODEL_COST_LIVE = 10400000
MODEL_COST_NON_LIVE = 2000000

# 카테고리별 고유 색상 매핑 (중복 방지)
CATEGORY_COLORS_UNIQUE = {
    '디지털/가전': '#00D9FF',      # 밝은 시안
    '화장품/미용': '#FF0080',      # 네온 핑크 (변경됨)
    '패션/의류': '#10F981',        # 네온 그린
    '식품': '#FFD93D',             # 골드
    '생활용품': '#7C3AED',         # 보라
    '스포츠/레저': '#FF6B35',      # 오렌지
    '가구/인테리어': '#00FFB9',    # 민트
    '주방용품': '#FF3355',         # 레드
    '건강식품': '#4ECDC4',         # 틸
    '유아용품': '#95E1D3',         # 라이트민트
    '도서/문구': '#F38181',        # 코랄
    '반려동물': '#AA96DA',         # 라벤더
    '자동차용품': '#8B5CF6',       # 바이올렛
    '원예/화훼': '#84CC16',        # 라임
    '보석/시계': '#F59E0B',        # 앰버
}

# 기존 CATEGORY_COLORS 대체
CATEGORY_COLORS = CATEGORY_COLORS_UNIQUE

# 한국식 숫자 포맷 함수
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

def get_category_color(category, default='#808080'):
    """카테고리에 맞는 색상 반환"""
    return CATEGORY_COLORS_UNIQUE.get(category, default)

def get_category_colors_list(categories):
    """카테고리 리스트에 대한 색상 리스트 반환"""
    default_colors = ['#00D9FF', '#FF0080', '#10F981', '#FFD93D', '#7C3AED',
                     '#FF6B35', '#00FFB9', '#FF3355', '#4ECDC4', '#95E1D3']
    
    colors = []
    for idx, cat in enumerate(categories):
        if cat in CATEGORY_COLORS_UNIQUE:
            colors.append(CATEGORY_COLORS_UNIQUE[cat])
        else:
            colors.append(default_colors[idx % len(default_colors)])
    
    return colors

# ============================================================================
# 트렌드 분석 탭 - 수정된 버전
# ============================================================================

def create_daily_tab(df_filtered, chart_generator, data_formatter, weekday_colors, colors):
    """트렌드 분석 탭 - 수정 버전"""
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">📊 일일 트렌드</h2>', unsafe_allow_html=True)
    
    # 사이드바에서 필터 값 가져오기 (session_state 활용)
    weekday_filter = st.session_state.get('weekday_filter', '전체')
    period_filter = st.session_state.get('period_filter', '전체')
    
    # 기간 대비 성과 비교 - 수정됨
    st.subheader("📈 기간 대비 성과 비교")
    
    comparison_type = st.radio(
        "비교 기간 선택",
        ["일간 비교", "주간 비교"],
        horizontal=True,
        key="comparison_period_modified"
    )
    
    today = df_filtered['date'].max()
    
    try:
        if comparison_type == "일간 비교":
            # 요일 필터 적용
            comparison_fig = _create_daily_comparison_with_filter(
                df_filtered,
                today,
                weekday_filter
            )
        else:  # 주간 비교
            comparison_fig = _create_weekly_comparison_with_filter(
                df_filtered,
                weekday_filter,
                period_filter
            )
        
        if comparison_fig:
            st.plotly_chart(comparison_fig['fig'], use_container_width=True)
            
            # 메트릭 표시
            if 'metrics' in comparison_fig:
                cols = st.columns(len(comparison_fig['metrics']))
                for col, (key, value) in zip(cols, comparison_fig['metrics'].items()):
                    with col:
                        st.metric(key, value)
    except Exception as e:
        log_error(e, "create_daily_tab - comparison")
        st.error("비교 차트 생성 중 오류가 발생했습니다.")
    
    st.markdown("---")
    
    # 요일별 실적 분석 (유지)
    st.subheader("📅 요일별 실적 분석")
    
    try:
        weekday_fig = _create_weekday_analysis_fixed(df_filtered, weekday_colors)
        if weekday_fig:
            st.plotly_chart(weekday_fig, use_container_width=True)
        else:
            st.info("요일별 분석 데이터가 부족합니다.")
    except Exception as e:
        log_error(e, "create_daily_tab - weekday analysis")
        st.error("요일별 분석 차트 생성 중 오류가 발생했습니다.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def _create_daily_comparison_improved(df, today):
    """개선된 일일 비교 - 평일만 필터링 옵션 추가"""
    try:
        # 오늘의 요일 확인
        today_weekday = today.weekday()
        
        # 요일별 비교 대상 설정
        if today_weekday == 0:  # 월요일
            comparison_dates = {
                '오늘(월)': today,
                '금요일': today - timedelta(days=3),
                '목요일': today - timedelta(days=4)
            }
        elif today_weekday == 1:  # 화요일
            comparison_dates = {
                '오늘(화)': today,
                '어제(월)': today - timedelta(days=1),
                '금요일': today - timedelta(days=4)
            }
        else:
            # 기본: 오늘, 어제, 그제
            comparison_dates = {
                '오늘': today,
                '어제': today - timedelta(days=1),
                '그제': today - timedelta(days=2)
            }
        
        # 주말 제외 필터링
        filtered_dates = {}
        for label, date in comparison_dates.items():
            if date.weekday() not in [5, 6]:  # 토, 일 제외
                filtered_dates[label] = date
        
        fig = go.Figure()
        
        # 네온 색상 팔레트
        neon_colors = ['#00D9FF', '#7C3AED', '#10F981']
        
        for idx, (label, date) in enumerate(filtered_dates.items()):
            day_data = df[df['date'].dt.date == date.date()]
            if len(day_data) > 0:
                hourly_revenue = day_data.groupby('hour')['revenue'].sum().reindex(range(24), fill_value=0)
                
                fig.add_trace(go.Scatter(
                    x=list(range(24)),
                    y=hourly_revenue.values,
                    mode='lines+markers',
                    name=f'{label} ({date.strftime("%m/%d")})',
                    line=dict(color=neon_colors[idx % len(neon_colors)], width=2),
                    marker=dict(size=6, color=neon_colors[idx % len(neon_colors)]),
                    hovertemplate='%{x}시<br>매출: %{y:,.0f}원<extra></extra>'
                ))
        
        fig.update_layout(
            title="일간 시간대별 매출 비교 (평일)",
            xaxis=dict(
                title="시간대",
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i}시" for i in range(24)],
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)'
            ),
            yaxis=dict(
                title="매출액",
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)'
            ),
            height=600,
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        # 메트릭 계산
        total_revenues = {}
        for label, date in filtered_dates.items():
            day_data = df[df['date'].dt.date == date.date()]
            total_revenues[label] = day_data['revenue'].sum()
        
        return {
            'fig': fig,
            'metrics': {f"{label}": f"{revenue:,.0f}원" for label, revenue in total_revenues.items()}
        }
    except Exception as e:
        log_error(e, "_create_daily_comparison_improved")
        return None



def _create_daily_comparison_with_filter(df, today, weekday_filter):
    """요일 필터가 적용된 일간 비교 - 개선된 버전"""
    # format_korean_number는 이미 이 파일에 정의되어 있음
    
    # 오늘을 제외하고 어제까지만 표시
    yesterday = today - timedelta(days=1)
    
    # 요일 필터에 따른 표시 요일 결정
    if weekday_filter == "평일":
        weekdays_to_show = [0, 1, 2, 3, 4]  # 월-금
    elif weekday_filter == "주말":
        weekdays_to_show = [5, 6]  # 토-일
    else:  # 전체
        weekdays_to_show = list(range(7))
    
    # 데이터에서 사용 가능한 날짜 범위 확인
    min_date = df['date'].min()
    max_date = min(df['date'].max(), pd.Timestamp(yesterday))
    
    # 사이드바 필터 기간 고려 (session_state에서 가져오기)
    import streamlit as st
    # session_state의 실제 키 사용
    date_from = st.session_state.get('start_date', min_date)
    date_to = st.session_state.get('end_date', max_date)
    
    # 날짜 타입 변환
    if not isinstance(date_from, pd.Timestamp):
        date_from = pd.Timestamp(date_from)
    if not isinstance(date_to, pd.Timestamp):
        date_to = pd.Timestamp(date_to)
    
    # 날짜 범위 설정 (오늘 제외)
    if date_to >= pd.Timestamp(today):
        date_to = yesterday
    
    # 필터링된 데이터
    df_filtered = df[(df['date'] >= date_from) & 
                     (df['date'] <= date_to)]
    
    fig = go.Figure()
    
    revenues = []
    dates = []
    colors = []
    
    # 날짜별 데이터 집계
    date_range = pd.date_range(start=date_from, end=date_to)
    
    prev_revenue = None
    for date in date_range:
        if weekday_filter == "전체" or date.weekday() in weekdays_to_show:
            day_data = df_filtered[df_filtered['date'].dt.date == date.date()]
            if not day_data.empty:
                revenue = day_data['revenue'].sum()
                revenues.append(revenue)
                dates.append(date.strftime('%m/%d'))
                
                # 전일대비 색상 결정
                if prev_revenue is not None:
                    if revenue > prev_revenue:
                        colors.append('#10F981')  # 연두색 (상승)
                    else:
                        colors.append('#FF4444')  # 빨간색 (하락)
                else:
                    colors.append('#00D9FF')  # 첫날은 기본 색상
                
                prev_revenue = revenue
    
    # 최대 60개 데이터만 표시 (가독성을 위해)
    if len(revenues) > 60:
        revenues = revenues[-60:]
        dates = dates[-60:]
        colors = colors[-60:]
    
    # 막대 그래프 추가
    fig.add_trace(go.Bar(
        x=dates,
        y=revenues,
        name='일일 매출',
        marker_color=colors,
        text=[format_korean_number(r) for r in revenues],
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>" +
                      "매출: %{text}<br>" +
                      "<extra></extra>"
    ))
    
    # 7일 이동평균선 추가
    if len(revenues) >= 2:
        # 7일 이동평균 계산
        moving_avg = []
        for i in range(len(revenues)):
            # 7일 이전까지의 데이터 평균 계산
            start_idx = max(0, i - 6)
            end_idx = i + 1
            window_data = revenues[start_idx:end_idx]
            moving_avg.append(sum(window_data) / len(window_data))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=moving_avg,
            mode='lines+markers',
            name='7일 이동평균',
            line=dict(color='#FFD700', width=2, dash='dash'),
            marker=dict(size=6, color='#FFD700'),
            hovertemplate="<b>%{x}</b><br>" +
                          "이동평균: %{y:,.0f}<br>" +
                          "<extra></extra>"
        ))
    
    # Y축 범위 계산 (15% 증가)
    if revenues:
        max_revenue = max(revenues)
        y_range = [0, max_revenue * 1.15]
    else:
        y_range = None
    
    # 레이아웃 설정
    fig.update_layout(
        title=f"일간 비교 ({weekday_filter} 기준) - {len(revenues)}일 표시",
        showlegend=True,
        height=460,  # 기존 400에서 15% 증가
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(color='#FFFFFF'),
        xaxis=dict(
            title="날짜",
            tickangle=-45 if len(dates) > 15 else 0
        ),
        yaxis=dict(
            title="매출액", 
            tickformat=',.0f',
            range=y_range
        ),
        hoverlabel=dict(
            bgcolor='rgba(10, 11, 30, 0.95)',
            bordercolor='#00D9FF',
            font=dict(color='#FFFFFF', size=14)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 메트릭 계산
    total_revenue = sum(revenues) if revenues else 0
    avg_revenue = total_revenue / len(revenues) if revenues else 0
    
    # 전일대비 증감률 계산
    if len(revenues) >= 2:
        change_rate = ((revenues[-1] - revenues[-2]) / revenues[-2] * 100) if revenues[-2] != 0 else 0
        change_text = f"{change_rate:+.1f}%"
    else:
        change_text = "N/A"
    
    return {
        'fig': fig,
        'metrics': {
            '평균 매출': format_korean_number(avg_revenue),
            '총 매출': format_korean_number(total_revenue),
            '전일대비': change_text,
            '표시 일수': f"{len(revenues)}일"
        }
    }


def _create_weekly_comparison_with_filter(df, weekday_filter, period_filter):
    """요일 및 기간 필터가 적용된 주간 비교"""
    # format_korean_number는 이미 이 파일에 정의되어 있음
    
    # 요일 필터 적용
    if weekday_filter == "평일":
        df = df[df['date'].dt.weekday < 5]
    elif weekday_filter == "주말":
        df = df[df['date'].dt.weekday >= 5]
    
    # 기간 필터 적용
    if period_filter != "전체":
        # session_state에서 날짜 범위 가져오기
        date_from = st.session_state.get('date_from')
        date_to = st.session_state.get('date_to')
        if date_from and date_to:
            df = df[(df['date'] >= pd.to_datetime(date_from)) & 
                   (df['date'] <= pd.to_datetime(date_to))]
    
    # 주별 집계
    df['year_week'] = df['date'].dt.strftime('%Y-W%U')
    weekly_data = df.groupby('year_week').agg({
        'revenue': 'sum',
        'roi': 'mean',
        'date': 'min'  # 주의 시작일
    }).reset_index()
    weekly_data = weekly_data.sort_values('date')
    
    # 막대그래프 생성
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=weekly_data['year_week'],
        y=weekly_data['revenue'],
        name='주간 매출',
        marker_color='#00D9FF',
        text=[format_korean_number(v) for v in weekly_data['revenue']],
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>" +
                      "매출: %{text}<br>" +
                      f"평균 ROI: %{{customdata:.1f}}%<br>" +
                      "<extra></extra>",
        customdata=weekly_data['roi']
    ))
    
    # 레이아웃 설정
    fig.update_layout(
        title=f"주간 비교 ({weekday_filter}, {period_filter})",
        showlegend=False,
        height=400,
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(color='#FFFFFF'),
        xaxis=dict(title="주차"),
        yaxis=dict(title="매출액", tickformat=',.0f'),
        hoverlabel=dict(
            bgcolor='rgba(10, 11, 30, 0.95)',
            bordercolor='#00D9FF',
            font=dict(color='#FFFFFF', size=14)
        )
    )
    
    return {
        'fig': fig,
        'metrics': {
            '평균 주간 매출': format_korean_number(weekly_data['revenue'].mean()),
            '최고 주간 매출': format_korean_number(weekly_data['revenue'].max()),
            '표시 주차 수': f"{len(weekly_data)}주"
        }
    }

def _create_weekly_comparison_full_period(df):
    """전체 기간 주간 비교"""
    try:
        df_weekly = df.copy()
        df_weekly['date'] = pd.to_datetime(df_weekly['date'])
        df_weekly['week'] = df_weekly['date'].dt.strftime('%Y-W%U')
        
        weekly_stats = df_weekly.groupby('week').agg({
            'revenue': 'sum',
            'roi_calculated': 'mean',
            'units_sold': 'sum'
        }).reset_index()
        
        # 색상 리스트 (순환)
        week_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', '#FFD93D']
        
        fig = go.Figure()
        
        for idx, (_, week_data) in enumerate(weekly_stats.iterrows()):
            color_idx = idx % len(week_colors)
            fig.add_trace(go.Bar(
                x=[week_data['week']],
                y=[week_data['revenue']],
                name=week_data['week'],
                marker_color=week_colors[color_idx],
                hovertemplate='%{x}<br>매출: %{y:,.0f}원<extra></extra>'
            ))
        
        fig.update_layout(
            title="전체 기간 주별 매출 비교",
            xaxis=dict(title="주차", color='#FFFFFF'),
            yaxis=dict(title="매출액", color='#FFFFFF'),
            height=600,
            showlegend=False,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF')
        )
        
        return {'fig': fig, 'metrics': {}}
    except Exception as e:
        log_error(e, "_create_weekly_comparison_full_period")
        return None

def _create_monthly_comparison_full_period(df):
    """전체 기간 월별 비교"""
    try:
        df_monthly = df.copy()
        df_monthly['date'] = pd.to_datetime(df_monthly['date'])
        df_monthly['month'] = df_monthly['date'].dt.strftime('%Y-%m')
        
        monthly_stats = df_monthly.groupby('month').agg({
            'revenue': 'sum',
            'roi_calculated': 'mean',
            'units_sold': 'sum'
        }).reset_index()
        
        # 색상 리스트
        month_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', '#FFD93D']
        
        fig = go.Figure()
        
        for idx, (_, month_data) in enumerate(monthly_stats.iterrows()):
            color_idx = idx % len(month_colors)
            fig.add_trace(go.Bar(
                x=[month_data['month']],
                y=[month_data['revenue']],
                name=month_data['month'],
                marker_color=month_colors[color_idx],
                hovertemplate='%{x}<br>매출: %{y:,.0f}원<extra></extra>'
            ))
        
        fig.update_layout(
            title="전체 기간 월별 매출 비교",
            xaxis=dict(title="월", color='#FFFFFF'),
            yaxis=dict(title="매출액", color='#FFFFFF'),
            height=600,
            showlegend=False,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF')
        )
        
        return {'fig': fig, 'metrics': {}}
    except Exception as e:
        log_error(e, "_create_monthly_comparison_full_period")
        return None

def _create_period_trend_optimized(df, period_type):
    """최적화된 기간별 성과 추이 - Y축 간격 개선"""
    try:
        fig = go.Figure()
        
        if period_type == "일별":
            # 일별 처리 (기존 로직 유지하되 최적화)
            daily_stats = df.groupby('date').agg({
                'revenue': 'sum',
                'roi_calculated': 'mean',
                'units_sold': 'sum'
            }).reset_index()
            
            # 7일 이동평균 - 최적화
            if len(daily_stats) > 7:
                daily_stats['ma7'] = daily_stats['revenue'].rolling(7, min_periods=1, center=False).mean()
            else:
                daily_stats['ma7'] = daily_stats['revenue']
            
            # 데이터 포인트 제한 (너무 많으면 브라우저 렉)
            if len(daily_stats) > 365:
                # 1년 이상 데이터는 주별 평균으로 표시
                daily_stats = daily_stats.set_index('date').resample('W').agg({
                    'revenue': 'sum',
                    'ma7': 'mean',
                    'roi_calculated': 'mean',
                    'units_sold': 'sum'
                }).reset_index()
                st.warning("1년 이상의 데이터는 주별로 집계하여 표시합니다.")
            
            # 일별 매출
            fig.add_trace(go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['revenue'],
                mode='markers',
                name='일별 매출',
                marker=dict(size=8, color='#00D9FF', opacity=0.7),
                hovertemplate='%{x|%Y-%m-%d}<br>매출: %{y:,.0f}원<extra></extra>'
            ))
            
            # 이동평균선
            fig.add_trace(go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['ma7'],
                mode='lines',
                name='7일 이동평균',
                line=dict(color='#7C3AED', width=3),
                hovertemplate='%{x|%Y-%m-%d}<br>7일 평균: %{y:,.0f}원<extra></extra>'
            ))
            
            max_revenue = daily_stats['revenue'].max()
            
        elif period_type == "주별":
            # 주별 처리 최적화
            df_weekly = df.copy()
            df_weekly['week'] = pd.to_datetime(df_weekly['date']).dt.strftime('%Y-W%U')
            
            weekly_stats = df_weekly.groupby('week').agg({
                'revenue': 'sum',
                'roi_calculated': 'mean',
                'units_sold': 'sum'
            }).reset_index()
            
            # 최대 52주(1년)만 표시
            if len(weekly_stats) > 52:
                weekly_stats = weekly_stats.tail(52)
                st.info("최근 1년(52주) 데이터만 표시합니다.")
            
            fig.add_trace(go.Bar(
                x=weekly_stats['week'],
                y=weekly_stats['revenue'],
                name='주별 매출',
                marker_color='#10F981',
                hovertemplate='%{x}<br>매출: %{y:,.0f}원<extra></extra>'
            ))
            
            max_revenue = weekly_stats['revenue'].max()
            
        else:  # 월별
            # 월별 처리 최적화
            df_monthly = df.copy()
            df_monthly['month_str'] = pd.to_datetime(df_monthly['date']).dt.strftime('%Y-%m')
            
            monthly_stats = df_monthly.groupby('month_str').agg({
                'revenue': 'sum',
                'roi_calculated': 'mean',
                'units_sold': 'sum'
            }).reset_index()
            
            # 최대 24개월만 표시
            if len(monthly_stats) > 24:
                monthly_stats = monthly_stats.tail(24)
                st.info("최근 2년(24개월) 데이터만 표시합니다.")
            
            fig.add_trace(go.Bar(
                x=monthly_stats['month_str'],
                y=monthly_stats['revenue'],
                name='월별 매출',
                marker_color='#00D9FF',
                hovertemplate='%{x}<br>매출: %{y:,.0f}원<extra></extra>'
            ))
            
            max_revenue = monthly_stats['revenue'].max()
        
        # Y축 틱 생성 - 더 넓은 간격으로 조정
        if max_revenue > 1000000000:  # 10억 이상
            tick_interval = 200000000  # 2억 단위
        elif max_revenue > 500000000:  # 5억 이상
            tick_interval = 100000000  # 1억 단위
        else:
            tick_interval = 50000000  # 5천만 단위
        
        # 최대 8개의 틱만 생성
        tick_values = []
        current = 0
        while current <= max_revenue * 1.1 and len(tick_values) < 8:
            tick_values.append(current)
            current += tick_interval
        
        tick_texts = [format_korean_number(val) for val in tick_values]
        
        # Y축 설정 업데이트
        fig.update_yaxes(
            title="매출액",
            tickmode='array',
            tickvals=tick_values,
            ticktext=tick_texts,
            gridcolor='rgba(255, 255, 255, 0.1)',
            zeroline=True,
            zerolinecolor='rgba(255, 255, 255, 0.2)',
            color='#FFFFFF',
            tickfont=dict(size=11)  # 폰트 크기 조정
        )
        
        fig.update_xaxes(
            title="기간",
            color='#FFFFFF',
            gridcolor='rgba(255, 255, 255, 0.06)'
        )
        
        fig.update_layout(
            title=f"{period_type} 매출 추이",
            height=700,  # 600 → 700 (높이 증가)
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        return fig
        
    except Exception as e:
        log_error(e, "_create_period_trend_optimized")
        st.error(f"차트 생성 중 오류: {str(e)}")
        return None

def _create_category_trend_fixed(df):
    """카테고리별 트렌드 - 색상 중복 해결"""
    try:
        top_categories = df.groupby('category')['revenue'].sum().nlargest(5).index.tolist()
        
        if len(top_categories) == 0:
            return None
        
        daily_category = df[df['category'].isin(top_categories)].groupby(
            ['date', 'category']
        )['revenue'].sum().reset_index()
        
        if len(daily_category) == 0:
            return None
        
        fig = go.Figure()
        
        # 카테고리별 고유 색상 적용
        for idx, category in enumerate(top_categories):
            cat_data = daily_category[daily_category['category'] == category]
            
            if len(cat_data) > 0:
                # 카테고리별 고유 색상 사용
                color = get_category_color(category)
                
                fig.add_trace(go.Scatter(
                    x=cat_data['date'],
                    y=cat_data['revenue'],
                    mode='lines+markers',
                    name=category,
                    line=dict(color=color, width=2),
                    marker=dict(size=6, color=color),
                    hovertemplate='%{x|%Y-%m-%d}<br>%{fullData.name}<br>매출: %{y:,.0f}원<extra></extra>'
                ))
        
        fig.update_layout(
            title="상위 5개 카테고리 일별 매출 트렌드",
            xaxis=dict(title="날짜", color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)'),
            yaxis=dict(title="매출액", color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)'),
            height=600,
            hovermode='x unified',
            showlegend=True,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            legend=dict(font=dict(color='#FFFFFF')),
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_category_trend_fixed")
        return None

def _create_weekday_analysis_fixed(df, weekday_colors):
    """요일별 분석 - ROI 계산 시 00~05시, 12~16시 제외"""
    try:
        weekday_names_kr = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
        
        if 'weekday' not in df.columns:
            return None
        
        # ROI 계산용 필터링된 데이터 (00~05시, 12~16시 제외)
        df_roi_filtered = df[~((df['hour'] >= 0) & (df['hour'] <= 5)) & 
                              ~((df['hour'] >= 12) & (df['hour'] <= 16))]
        
        # 매출 등은 전체 데이터 사용
        weekday_stats = df.groupby('weekday').agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'broadcast': 'count'
        }).reset_index()
        
        # ROI는 필터링된 데이터에서 계산
        weekday_roi = df_roi_filtered.groupby('weekday')['roi_calculated'].mean().reset_index()
        weekday_roi.columns = ['weekday', 'roi_filtered']
        
        # 두 데이터프레임 병합
        weekday_stats = weekday_stats.merge(weekday_roi, on='weekday', how='left')
        
        if len(weekday_stats) == 0:
            return None
        
        weekday_stats['weekday_name'] = weekday_stats['weekday'].map(weekday_names_kr)
        weekday_stats = weekday_stats.sort_values('weekday')
        
        fig = make_subplots(
            rows=1, cols=1,
            specs=[[{"secondary_y": True}]]
        )
        
        bar_colors = [weekday_colors.get(w, '#00D9FF') for w in weekday_stats['weekday']]
        
        fig.add_trace(
            go.Bar(
                x=weekday_stats['weekday_name'],
                y=weekday_stats['revenue'],
                name='총 매출',
                marker_color=bar_colors,
                hovertemplate='%{x}요일<br>매출: %{y:,.0f}원<extra></extra>'
            ),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(
                x=weekday_stats['weekday_name'],
                y=weekday_stats['roi_filtered'],
                name='평균 ROI (특정시간 제외)',
                mode='lines+markers+text',
                line=dict(color='#FF0080', width=3),
                marker=dict(size=12, color='#FF0080'),
                text=[f"{v:.1f}%" for v in weekday_stats['roi_filtered']],
                textposition='top center',
                textfont=dict(color='#FF0080'),
                hovertemplate='%{x}요일<br>ROI: %{y:.1f}%<br>(00~05시, 12~16시 제외)<extra></extra>'
            ),
            secondary_y=True,
        )
        
        fig.update_xaxes(title_text="요일", color='#FFFFFF')
        fig.update_yaxes(title_text="매출액", secondary_y=False, color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)')
        fig.update_yaxes(title_text="평균 ROI (%) - 특정시간 제외", secondary_y=True, color='#FF0080')
        
        fig.update_layout(
            title="요일별 매출 및 ROI 추이 (ROI: 00~05시, 12~16시 제외)",
            height=600,
            hovermode='x unified',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            legend=dict(font=dict(color='#FFFFFF')),
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_weekday_analysis_fixed")
        return None

# ============================================================================
# 카테고리 분석 탭 - 수정된 버전 (효율성 분석 삭제)
# ============================================================================

def create_category_tab(df_filtered, chart_generator, data_formatter, 
                       category_colors, platform_colors, colors):
    """카테고리 분석 탭 - 효율성 분석 그래프 삭제"""
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-title">📦 카테고리 분석</h2>', unsafe_allow_html=True)
    
    # 카테고리별 상품 성과 분석
    st.subheader("🎯 카테고리별 TOP 10 상품")
    
    category_list = sorted(df_filtered['category'].unique())
    
    if len(category_list) == 0:
        st.warning("카테고리 데이터가 없습니다.")
    else:
        default_category = "화장품/미용" if "화장품/미용" in category_list else category_list[0]
        
        selected_category = st.selectbox(
            "분석할 카테고리 선택",
            options=category_list,
            index=category_list.index(default_category) if default_category in category_list else 0,
            key="category_select_v20_3_2"
        )
        
        try:
            # TOP 10 상품 차트 - 높이 800px로 조정
            fig_products = _create_category_top10_chart(
                df_filtered,
                selected_category,
                data_formatter
            )
            if fig_products:
                st.plotly_chart(fig_products, use_container_width=True)
            
            # 상품 상세정보 - 판매단가, 방송시간대 추가
            _render_product_details(df_filtered, selected_category, data_formatter)
            
        except Exception as e:
            log_error(e, "create_category_tab - product analysis")
            st.error("상품 분석 중 오류가 발생했습니다.")
    
    st.markdown("---")
    
    # 카테고리별 매출 분포
    st.subheader("📊 카테고리별 매출 분포")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        try:
            # 막대 그래프와 원형 그래프 색상 통일
            bar_fig = _create_category_bar_chart(df_filtered)
            if bar_fig:
                st.plotly_chart(bar_fig, use_container_width=True)
        except Exception as e:
            log_error(e, "create_category_tab - bar chart")
            st.error("막대 차트 생성 중 오류가 발생했습니다.")
    
    with col2:
        try:
            pie_fig = _create_category_pie_chart_fixed(df_filtered)
            if pie_fig:
                st.plotly_chart(pie_fig, use_container_width=True)
        except Exception as e:
            log_error(e, "create_category_tab - pie chart")
            # 대체 표시 - 테이블
            st.error("파이차트 생성 중 오류가 발생했습니다.")
            cat_revenue = df_filtered.groupby('category')['revenue'].sum().nlargest(10)
            st.dataframe(
                cat_revenue.reset_index().rename(columns={'index': '카테고리', 'revenue': '매출'}),
                use_container_width=True
            )
    
    # 효율성 분석 섹션 삭제됨
    # st.subheader("📈 카테고리별 효율성 분석") - 삭제
    # 관련 코드 블록 전체 삭제
    
    st.markdown('</div>', unsafe_allow_html=True)

def _create_category_top10_chart(df, category, data_formatter):
    """카테고리 TOP10 상품 그래프 - 높이 800px"""
    try:
        cat_data = df[df['category'] == category]
        
        if len(cat_data) == 0:
            return None
        
        # 상품별 집계
        product_stats = cat_data.groupby('broadcast').agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean'
        }).reset_index()
        
        # TOP 10
        top_products = product_stats.nlargest(10, 'revenue')
        
        fig = go.Figure()
        
        # 고유 색상 리스트
        colors = get_category_colors_list(['dummy'] * 10)
        
        fig.add_trace(go.Bar(
            x=top_products['revenue'],
            y=top_products['broadcast'].str[:30],
            orientation='h',
            marker=dict(
                color=colors[:len(top_products)],
                line=dict(color='rgba(255, 255, 255, 0.2)', width=1)
            ),
            text=[data_formatter.format_money(v) for v in top_products['revenue']],
            textposition='outside',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{y}<br>매출: %{x:,.0f}원<extra></extra>'
        ))
        
        fig.update_xaxes(
            title="매출액",
            color='#FFFFFF',
            gridcolor='rgba(255, 255, 255, 0.06)'
        )
        
        fig.update_yaxes(
            title="상품명",
            color='#FFFFFF',
            automargin=True,
            tickfont=dict(size=11)
        )
        
        fig.update_layout(
            title=f"{category} 카테고리 TOP 10 상품",
            height=800,  # 600 → 800 (적절한 세로 크기)
            margin=dict(l=200, r=50, t=50, b=50),  # 왼쪽 마진 증가
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            showlegend=False,
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_category_top10_chart")
        return None

def _render_product_details(df, category, data_formatter):
    """상품 상세정보 렌더링 - 판매단가, 방송시간대 추가"""
    try:
        cat_data = df[df['category'] == category]
        
        if len(cat_data) == 0:
            return
        
        # 상품별 집계
        product_stats = cat_data.groupby('broadcast').agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'platform': lambda x: x.value_counts().index[0] if len(x) > 0 else '',
            'hour': lambda x: list(x.value_counts().index[:3]) if len(x) > 0 else [],  # 주요 방송시간대
            'date': 'count'
        }).reset_index()
        
        # TOP 5 상품만
        top_products = product_stats.nlargest(5, 'revenue')
        
        st.markdown("#### 📋 상품 상세 정보")
        
        cols = st.columns(len(top_products))
        
        for idx, (_, product) in enumerate(top_products.iterrows()):
            # 판매단가 계산
            unit_price = product['revenue'] / product['units_sold'] if product['units_sold'] > 0 else 0
            
            # 방송시간대 문자열
            if isinstance(product['hour'], list) and len(product['hour']) > 0:
                time_str = ", ".join([f"{h}시" for h in product['hour']])
            else:
                time_str = "정보 없음"
            
            with cols[idx]:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.05); 
                            padding: 15px; 
                            border-radius: 10px;
                            border: 1px solid rgba(255, 255, 255, 0.2);">
                    <h5 style="color: #00D9FF; margin: 0 0 10px 0;">
                        {product['broadcast'][:30]}...
                    </h5>
                    <p style="color: #FFFFFF; margin: 5px 0;">
                        총 매출: <strong>{data_formatter.format_money(product['revenue'])}</strong>
                    </p>
                    <p style="color: #FFFFFF; margin: 5px 0;">
                        판매수량: <strong>{product['units_sold']:,}개</strong>
                    </p>
                    <p style="color: #10F981; margin: 5px 0;">
                        <strong>판매단가: {data_formatter.format_money(unit_price)}</strong>
                    </p>
                    <p style="color: #FFD93D; margin: 5px 0;">
                        <strong>방송시간: {time_str}</strong>
                    </p>
                    <p style="color: #FFFFFF; margin: 5px 0;">
                        평균 ROI: <strong>{product['roi_calculated']:.1f}%</strong>
                    </p>
                    <p style="color: rgba(255, 255, 255, 0.6); font-size: 12px;">
                        주요 방송사: {product['platform']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        log_error(e, "_render_product_details")

def _create_category_bar_chart(df):
    """카테고리별 막대 그래프"""
    try:
        # 카테고리별 집계
        cat_revenue = df.groupby('category')['revenue'].sum().sort_values(ascending=False).head(10)
        
        # 색상 매핑
        colors = get_category_colors_list(cat_revenue.index.tolist())
        
        # 막대 그래프
        fig = go.Figure(data=[
            go.Bar(
                x=cat_revenue.index,
                y=cat_revenue.values,
                marker_color=colors,
                text=[format_korean_number(v) for v in cat_revenue.values],
                textposition='outside',
                hovertemplate='%{x}<br>매출: %{y:,.0f}원<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="카테고리별 매출 TOP 10",
            xaxis=dict(title="카테고리", tickangle=-45, color='#FFFFFF'),
            yaxis=dict(title="매출액", color='#FFFFFF', gridcolor='rgba(255, 255, 255, 0.06)'),
            height=500,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        return fig
    except Exception as e:
        log_error(e, "_create_category_bar_chart")
        return None

def _create_category_pie_chart_fixed(df):
    """카테고리별 파이차트 - 오류 처리 개선"""
    try:
        # 데이터 검증
        cat_revenue = df.groupby('category')['revenue'].sum()
        cat_revenue = cat_revenue[cat_revenue > 0].nlargest(10)  # 상위 10개만, 0원 제외
        
        if len(cat_revenue) == 0:
            st.warning("📊 표시할 매출 데이터가 없습니다.")
            return None
        
        # 색상 리스트 생성
        colors = get_category_colors_list(cat_revenue.index.tolist())
        
        # 원형 그래프
        fig = go.Figure(data=[
            go.Pie(
                labels=cat_revenue.index,
                values=cat_revenue.values,
                hole=0.3,
                marker=dict(
                    colors=colors,
                    line=dict(color='rgba(255, 255, 255, 0.2)', width=2)
                ),
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(color='#FFFFFF'),
                hovertemplate='<b>%{label}</b><br>매출: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="카테고리별 매출 비중",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(color='#FFFFFF')
            ),
            margin=dict(l=0, r=150, t=50, b=50),
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='#FFFFFF'),
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor='#00D9FF',
                font=dict(color='#FFFFFF')
            )
        )
        
        return fig
        
    except Exception as e:
        log_error(e, "_create_category_pie_chart_fixed")
        st.error(f"파이차트 생성 중 오류: {str(e)}")
        return None

# ============================================================================
# 최적화 전략 탭 - 삭제
# ============================================================================

def create_optimization_tab(df_filtered, chart_generator, data_formatter, colors):
    """최적화 전략 탭 - 삭제됨"""
    st.info("이 탭은 더 이상 사용되지 않습니다.")
    return