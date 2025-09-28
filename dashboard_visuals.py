"""
dashboard_visuals.py - 차트 및 시각화 생성 (Dark Mode + Glassmorphism) - 수정 v20.3.1
Version: 12.0.0
Last Updated: 2025-02-03

주요 수정사항 (v20.3.1):
1. 모든 차트 높이 20% 증가 (500 → 600px)
2. 카테고리 색상 중복 문제 해결 (CATEGORY_COLORS_UNIQUE 사용)
3. 호버 툴팁 가시성 개선 유지
4. get_category_colors_list 헬퍼 함수 활용
5. ROI 히트맵 최적화 유지
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import json

# dashboard_config에서 개선된 설정 및 헬퍼 함수 가져오기
from dashboard_config import (
    COLORS, CHART_CONFIG, PLATFORM_COLORS, WEEKDAY_COLORS, 
    HEATMAP_COLORSCALE_REVENUE, HEATMAP_COLORSCALE_ROI,
    ENHANCED_HOVER_CONFIG, HEATMAP_HOVER_CONFIG, ROI_COLORSCALE_OPTIMIZED,
    normalize_heatmap_data, optimize_roi_heatmap_colors, 
    emergency_hover_fix, fix_heatmap_data, get_standard_hover_template,
    # 새로 추가된 카테고리 관련 imports
    CATEGORY_COLORS_UNIQUE, get_category_color, get_category_colors_list
)

# ============================================================================
# Dark Mode 차트 기본 설정 - 높이 수정 (500 → 600)
# ============================================================================

DARK_CHART_LAYOUT = {
    'height': 600,  # 수정: 500 → 600 (20% 증가)
    'margin': dict(t=40, b=40, l=40, r=40),
    'paper_bgcolor': 'rgba(0, 0, 0, 0)',  # 완전 투명
    'plot_bgcolor': 'rgba(255, 255, 255, 0.02)',  # 거의 투명
    'font': dict(
        family="'Inter', 'Pretendard', system-ui, sans-serif",
        size=14,
        color='#FFFFFF'
    ),
    'hovermode': 'x unified',
    # 개선된 호버 설정 적용
    'hoverlabel': {
        'bgcolor': 'rgba(0, 0, 0, 0.95)',     # 거의 불투명한 검정
        'bordercolor': '#FFFFFF',             # 흰색 테두리로 강조
        'font': {
            'color': '#FFFFFF',               # 완전한 흰색
            'size': 15,
            'family': "'Inter', sans-serif"
        },
        'align': 'left'
    },
    'xaxis': dict(
        gridcolor='rgba(255, 255, 255, 0.06)',
        linecolor='rgba(255, 255, 255, 0.12)',
        linewidth=2,
        tickfont=dict(color='#FFFFFF', size=12),
        title_font=dict(color='#FFFFFF', size=14)
    ),
    'yaxis': dict(
        gridcolor='rgba(255, 255, 255, 0.06)',
        linecolor='rgba(255, 255, 255, 0.12)',
        linewidth=2,
        tickfont=dict(color='#FFFFFF', size=12),
        title_font=dict(color='#FFFFFF', size=14)
    ),
    'dragmode': 'pan',
    'showlegend': True,
    'legend': dict(
        bgcolor='rgba(0, 0, 0, 0)',
        bordercolor='rgba(255, 255, 255, 0.1)',
        borderwidth=1,
        font=dict(color='#FFFFFF', size=12)
    )
}

# ============================================================================
# 캐시 키 생성 유틸리티
# ============================================================================

def generate_chart_key(chart_type: str, data_hash: str, **kwargs) -> str:
    """차트별 고유 캐시 키 생성"""
    params = {
        'type': chart_type,
        'data': data_hash,
        **kwargs
    }
    key_string = json.dumps(params, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()

# ============================================================================
# Dark Mode 차트 생성 클래스 - 수정된 버전
# ============================================================================

class ChartGenerator:
    """Dark Mode + Glassmorphism 테마가 적용된 차트 생성 클래스 (v20.3.1)"""
    
    def __init__(self, colors=None, chart_config=None):
        self.colors = colors or COLORS
        self.platform_colors = PLATFORM_COLORS
        self.category_colors = CATEGORY_COLORS_UNIQUE  # 수정: 고유 색상 사용
        self.weekday_colors = WEEKDAY_COLORS
        self.chart_config = chart_config or CHART_CONFIG
        self._chart_cache = {}
        self.default_layout = DARK_CHART_LAYOUT.copy()
    
    # ========================================================================
    # 히트맵 차트 - Dark Mode
    # ========================================================================
    
    @st.cache_data(ttl=300, show_spinner=False)
    def create_platform_heatmap(_self, df_json: str, platform_name: str):
        """방송사별 시간대 히트맵 - Dark Mode"""
        df = pd.read_json(df_json)
        platform_data = df[df['platform'] == platform_name]
        
        if len(platform_data) == 0:
            return None
        
        heatmap_data = platform_data.pivot_table(
            values='revenue',
            index='hour',
            columns='weekday',
            aggfunc='mean',
            fill_value=0
        )
        
        all_hours = list(range(24))
        heatmap_data = heatmap_data.reindex(all_hours, fill_value=0)
        
        fig = _self._create_heatmap_base(
            heatmap_data.values,
            x_labels=['월', '화', '수', '목', '금', '토', '일'],
            y_labels=[f"{i}시" for i in range(24)],
            title=f"{platform_name} 시간대별 매출 히트맵",
            colorscale='Viridis',
            chart_type='revenue'
        )
        
        return fig
    
    def _create_heatmap_base(self, z_values, x_labels, y_labels, title, colorscale, chart_type='revenue'):
        """히트맵 기본 생성 - Dark Mode (최적화)"""
        
        # 데이터 검증 및 정규화
        z_clean = fix_heatmap_data(z_values)
        
        # 차트 타입별 설정
        if chart_type == 'roi':
            # ROI 전용 설정
            color_config = optimize_roi_heatmap_colors(z_clean)
            text_values = [[f"{val:.1f}%" if val != 0 else "" for val in row] 
                          for row in z_clean]
            hover_template = get_standard_hover_template('heatmap_roi')
            colorbar_title = "ROI (%)"
        else:
            # 매출 전용 설정  
            norm_config = normalize_heatmap_data(z_clean)
            color_config = {
                'colorscale': colorscale,
                **norm_config
            }
            text_values = [[f"{val/1e6:.1f}M" if val > 0 else "" for val in row] 
                          for row in z_clean]
            hover_template = get_standard_hover_template('heatmap_revenue')
            colorbar_title = "매출 (원)"
        
        fig = go.Figure(data=go.Heatmap(
            z=z_clean,
            x=x_labels,
            y=y_labels,
            text=text_values,
            texttemplate='%{text}',
            textfont={"size": 14, "color": '#FFFFFF'},
            hovertemplate=hover_template,
            colorbar=dict(
                tickfont=dict(color='#FFFFFF', size=12),
                title=dict(
                    text=colorbar_title,
                    font=dict(color='#FFFFFF', size=14)
                ),
                bgcolor='rgba(0, 0, 0, 0)',
                bordercolor='#00D9FF',
                outlinecolor='rgba(255, 255, 255, 0.1)',
                outlinewidth=1
            ),
            **color_config
        ))
        
        layout_config = self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text=title,
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'height': 600,  # 수정: 400 → 600
            'showlegend': False,
            'hoverlabel': HEATMAP_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    # ========================================================================
    # 조건부 렌더링
    # ========================================================================
    
    def should_render_chart(self, chart_type: str, tab_index: int, current_tab: int) -> bool:
        """차트를 렌더링해야 하는지 판단"""
        if tab_index != current_tab:
            return False
        
        if chart_type == 'heatmap' and st.session_state.get('skip_heatmap', False):
            return False
        
        return True
    
    # ========================================================================
    # 데이터 샘플링
    # ========================================================================
    
    def sample_large_dataset(self, df, max_points=1000):
        """대용량 데이터셋 샘플링"""
        if len(df) <= max_points:
            return df
        
        df_sorted = df.sort_values('revenue', ascending=False)
        
        top_half = df_sorted.head(max_points // 2)
        random_half = df_sorted.tail(len(df_sorted) - max_points // 2).sample(
            n=max_points // 2, 
            random_state=42
        )
        
        return pd.concat([top_half, random_half])
    
    @st.cache_data(ttl=300, show_spinner=False)
    def create_category_roi_heatmap(_self, df_json: str, category_name: str):
        """카테고리별 방송사 ROI 히트맵 - Dark Mode"""
        df = pd.read_json(df_json)
        cat_data = df[df['category'] == category_name]
        
        if len(cat_data) == 0:
            return None
        
        platform_roi = cat_data.groupby('platform').agg({
            'real_profit': 'sum',
            'total_cost': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        platform_roi['roi_calculated'] = np.where(
            platform_roi['total_cost'] > 0,
            (platform_roi['real_profit'] / platform_roi['total_cost']) * 100,
            0
        )
        
        # 상위 15개 플랫폼 선택
        top_platforms = platform_roi.nlargest(15, 'revenue')
        roi_values = top_platforms['roi_calculated'].values.reshape(-1, 1)
        
        # ROI 데이터 검증 및 정규화
        roi_clean = fix_heatmap_data(roi_values)
        roi_config = optimize_roi_heatmap_colors(roi_clean)
        
        # 개선된 텍스트 표시
        text_values = [[f"{val:.1f}%" if abs(val) > 0.1 else "0%" for val in row] 
                      for row in roi_clean]
        
        fig = go.Figure(data=go.Heatmap(
            z=roi_clean,
            x=[category_name],
            y=top_platforms['platform'].tolist(),
            text=text_values,
            texttemplate='%{text}',
            textfont={"size": 16, "color": '#FFFFFF'},
            hovertemplate='<b>%{y}</b><br>카테고리: %{x}<br>ROI: %{z:.1f}%<extra></extra>',
            colorbar=dict(
                title=dict(
                    text="실질 ROI (%)",
                    font=dict(color='#FFFFFF', size=16)
                ),
                tickfont=dict(color='#FFFFFF', size=13),
                bgcolor='rgba(0, 0, 0, 0)',
                bordercolor='#00D9FF',
                thickness=25,
                len=0.8
            ),
            **roi_config
        ))
        
        layout_config = _self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text=f"{category_name} 카테고리 방송사별 실질 ROI",
                font=dict(size=20, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'height': 600,  # 유지
            'showlegend': False,
            'xaxis': dict(
                title="카테고리",
                tickfont=dict(color='#FFFFFF', size=14),
                color='#FFFFFF'
            ),
            'yaxis': dict(
                title="방송사",
                autorange="reversed",
                tickfont=dict(color='#FFFFFF', size=14),
                color='#FFFFFF'
            ),
            'hoverlabel': HEATMAP_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    # ========================================================================
    # 막대 차트 - Dark Mode
    # ========================================================================
    
    def create_platform_comparison_optimized(self, df, platform_colors=None, format_money=None):
        """방송사별 종합 성과 비교 - Dark Mode"""
        df_nonzero = df[df['revenue'] > 0]
        
        platform_stats = df_nonzero.groupby('platform').agg({
            'revenue': ['sum', 'mean'],
            'roi_calculated': 'mean',
            'is_live': 'first'
        }).reset_index()
        
        platform_stats.columns = ['platform', 'revenue_sum', 'revenue_mean', 
                                 'roi_mean', 'is_live']
        
        platform_stats['channel_type'] = np.where(
            platform_stats['is_live'], '생방송', '비생방송'
        )
        
        platform_stats = platform_stats.sort_values('revenue_sum', ascending=False).head(20)
        
        colors_list = []
        for platform in platform_stats['platform']:
            if platform in self.platform_colors:
                colors_list.append(self.platform_colors[platform])
            else:
                default_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', 
                                '#FFD93D', '#FF6B35', '#00FFB9', '#FF3355']
                colors_list.append(default_colors[len(colors_list) % len(default_colors)])
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=platform_stats['platform'],
            y=platform_stats['revenue_sum'],
            name='총 매출',
            marker=dict(
                color=colors_list,
                line=dict(color='rgba(255, 255, 255, 0.2)', width=1)
            ),
            text=[f"{row['channel_type']}<br>{format_money(row['revenue_sum']) if format_money else row['revenue_sum']}" 
                  for _, row in platform_stats.iterrows()],
            textposition='outside',
            textfont=dict(size=11, color='#FFFFFF'),
            hovertemplate='<b>%{x}</b><br>매출: %{y:,.0f}원<br>채널: %{customdata}<extra></extra>',
            customdata=platform_stats['channel_type']
        ))
        
        fig.add_trace(go.Scatter(
            x=platform_stats['platform'],
            y=platform_stats['roi_mean'],
            mode='lines+markers+text',
            name='평균 ROI (%)',
            marker=dict(
                color='#FF0080',
                size=12,
                line=dict(color='#FFFFFF', width=2),
                symbol='diamond'
            ),
            yaxis='y2',
            line=dict(color='#FF0080', width=3),
            text=[f"{v:.1f}%" for v in platform_stats['roi_mean']],
            textposition='top center',
            textfont=dict(size=10, color='#FF0080'),
            hovertemplate='<b>%{x}</b><br>평균 ROI: %{y:.1f}%<extra></extra>'
        ))
        
        layout_config = self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text="방송사별 종합 성과 비교",
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'xaxis': dict(
                title="방송사", 
                tickangle=-45,
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)',
                tickfont=dict(size=11, color='#FFFFFF')
            ),
            'yaxis': dict(
                title="매출", 
                side='left',
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)'
            ),
            'yaxis2': dict(
                title="평균 ROI (%)", 
                overlaying='y', 
                side='right',
                color='#FF0080',
                tickfont=dict(color='#FF0080')
            ),
            'height': 600,  # 유지
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    def create_hourly_revenue_bar_optimized(self, df, revenue_type="평균 매출", format_money=None):
        """시간대별 매출 막대 차트 - Dark Mode"""
        df_nonzero = df[df['revenue'] > 0]
        
        if revenue_type == "평균 매출":
            hourly_stats = df_nonzero.groupby('hour')['revenue'].mean()
            hourly_roi = df_nonzero.groupby('hour')['roi_calculated'].mean()
        else:
            hourly_stats = df.groupby('hour')['revenue'].sum()
            hourly_roi = df.groupby('hour')['roi_calculated'].mean()
        
        all_hours = pd.DataFrame({'hour': range(24)})
        hourly_data = pd.DataFrame({
            'hour': hourly_stats.index,
            'revenue': hourly_stats.values,
            'roi': hourly_roi.values
        })
        hourly_data = all_hours.merge(hourly_data, on='hour', how='left').fillna(0)
        
        max_revenue = hourly_data['revenue'].max()
        bar_colors = []
        for v in hourly_data['revenue']:
            if v > max_revenue * 0.8:
                bar_colors.append('#10F981')
            elif v > max_revenue * 0.6:
                bar_colors.append('#00D9FF')
            elif v > max_revenue * 0.4:
                bar_colors.append('#7C3AED')
            elif v > max_revenue * 0.2:
                bar_colors.append('#FFD93D')
            else:
                bar_colors.append('#FF6B35')
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=hourly_data['hour'],
            y=hourly_data['revenue'],
            name='매출',
            marker=dict(
                color=bar_colors,
                line=dict(color='rgba(255, 255, 255, 0.2)', width=1)
            ),
            text=[format_money(v) if format_money else f"{v:,.0f}" 
                  for v in hourly_data['revenue']],
            textposition='outside',
            textfont=dict(size=10, color='#FFFFFF'),
            hovertemplate='%{x}시<br>매출: %{y:,.0f}원<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=hourly_data['hour'],
            y=hourly_data['roi'],
            name='ROI (%)',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='#FF3355', width=3),
            marker=dict(size=8, color='#FF3355', symbol='star'),
            hovertemplate='%{x}시<br>ROI: %{y:.1f}%<extra></extra>'
        ))
        
        layout_config = self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text="시간대별 매출 및 ROI 분석",
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'xaxis': dict(
                title="시간대",
                tickmode='linear',
                tick0=0,
                dtick=1,
                ticktext=[f"{i}시" for i in range(24)],
                tickvals=list(range(24)),
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)',
                tickfont=dict(color='#FFFFFF')
            ),
            'yaxis': dict(
                title=f"{revenue_type} (원)", 
                side='left',
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)',
                tickfont=dict(color='#FFFFFF')
            ),
            'yaxis2': dict(
                title="ROI (%)", 
                overlaying='y', 
                side='right',
                color='#FF3355',
                tickfont=dict(color='#FF3355')
            ),
            'height': 600,  # 유지
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    # ========================================================================
    # 파이 차트 - Dark Mode (카테고리 색상 중복 해결)
    # ========================================================================
    
    @st.cache_data(ttl=300, show_spinner=False)
    def create_category_pie_cached(_self, df_json: str, category_colors_json: str, top_n=10):
        """카테고리별 매출 비중 파이 차트 - 캐시 버전 (색상 중복 해결)"""
        df = pd.read_json(df_json)
        
        cat_stats = df.groupby('category')['revenue'].sum().nlargest(top_n)
        
        # get_category_colors_list 헬퍼 함수 사용 (중복 방지)
        colors_list = get_category_colors_list(cat_stats.index.tolist())
        
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=[str(label) for label in cat_stats.index],
            values=[float(value) for value in cat_stats.values],
            hole=0.3,
            marker=dict(
                colors=colors_list,
                line=dict(color='rgba(255, 255, 255, 0.2)', width=2)
            ),
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=12, color='#FFFFFF'),
            hovertemplate='<b>%{label}</b><br>매출: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        ))
        
        layout_config = _self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text=f"카테고리별 매출 비중 (TOP {top_n})",
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'height': 600,  # 수정: 500 → 600
            'showlegend': False,
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    def create_category_pie(self, df, category_colors=None, top_n=10):
        """카테고리별 매출 비중 파이 차트 - 비캐시 버전 (색상 중복 해결)"""
        cat_stats = df.groupby('category')['revenue'].sum().nlargest(top_n)
        
        # get_category_colors_list 헬퍼 함수 사용 (중복 방지)
        colors_list = get_category_colors_list(cat_stats.index.tolist())
        
        fig = go.Figure(data=[go.Pie(
            labels=cat_stats.index,
            values=cat_stats.values,
            hole=0.3,
            marker=dict(
                colors=colors_list,
                line=dict(color='rgba(255, 255, 255, 0.2)', width=2)
            ),
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=12, color='#FFFFFF'),
            hovertemplate='<b>%{label}</b><br>매출: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        layout_config = self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text=f"카테고리별 매출 비중 (TOP {top_n})",
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'height': 600,  # 수정: 500 → 600
            'showlegend': False,
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    # ========================================================================
    # 트리맵 - Dark Mode
    # ========================================================================
    
    @st.cache_data(ttl=300, show_spinner=False)
    def create_revenue_treemap_cached(_self, df_json: str):
        """계층적 매출 구조 트리맵 - Dark Mode"""
        df = pd.read_json(df_json)
        
        top_categories = df.groupby('category')['revenue'].sum().nlargest(20).index
        df_filtered = df[df['category'].isin(top_categories)]
        
        treemap_data = df_filtered.groupby(['platform', 'category'])['revenue'].sum().reset_index()
        treemap_data = treemap_data[treemap_data['revenue'] > 0]
        
        fig = px.treemap(
            treemap_data,
            path=['platform', 'category'],
            values='revenue',
            color='revenue',
            color_continuous_scale=[
                [0, '#7C3AED'],
                [0.3, '#00D9FF'],
                [0.5, '#10F981'],
                [0.7, '#FFD93D'],
                [1, '#FF3355']
            ]
        )
        
        fig.update_traces(
            textfont=dict(color='#FFFFFF', size=12),
            hovertemplate='<b>%{label}</b><br>매출: %{value:,.0f}원<extra></extra>',
            marker=dict(line=dict(color='rgba(255, 255, 255, 0.2)', width=2))
        )
        
        layout_config = _self.default_layout.copy()
        layout_config.update({
            'height': 600,  # 유지
            'margin': dict(t=30, b=0, l=0, r=0),
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    # ========================================================================
    # 선 차트 - Dark Mode
    # ========================================================================
    
    def create_platform_time_trend_optimized(self, df, platform_name):
        """방송사별 시간대 매출 추이 - Dark Mode"""
        platform_data = df[df['platform'] == platform_name]
        
        if len(platform_data) == 0:
            return None
        
        hourly_trend = platform_data.groupby('hour').agg({
            'revenue': 'mean',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        all_hours = pd.DataFrame({'hour': range(24)})
        hourly_trend = all_hours.merge(hourly_trend, on='hour', how='left').fillna(0)
        
        platform_color = self.platform_colors.get(platform_name, '#00D9FF')
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=hourly_trend['hour'],
            y=hourly_trend['revenue'],
            name='평균 매출',
            marker=dict(
                color=platform_color,
                opacity=0.7,
                line=dict(color='rgba(255, 255, 255, 0.2)', width=1)
            ),
            yaxis='y',
            hovertemplate='%{x}시<br>평균 매출: %{y:,.0f}원<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=hourly_trend['hour'],
            y=hourly_trend['roi_calculated'],
            name='평균 ROI',
            mode='lines+markers',
            marker=dict(
                color='#FF0080',
                size=10,
                line=dict(color='#FFFFFF', width=2),
                symbol='diamond'
            ),
            yaxis='y2',
            line=dict(color='#FF0080', width=3),
            hovertemplate='%{x}시<br>평균 ROI: %{y:.1f}%<extra></extra>'
        ))
        
        layout_config = self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text=f"{platform_name} 시간대별 성과",
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'xaxis': dict(
                title="시간대",
                tickmode='linear',
                tick0=0,
                dtick=1,
                ticktext=[f"{i}시" for i in range(24)],
                tickvals=list(range(24)),
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)',
                tickfont=dict(color='#FFFFFF')
            ),
            'yaxis': dict(
                title="평균 매출 (원)", 
                side='left',
                color='#FFFFFF',
                gridcolor='rgba(255, 255, 255, 0.06)',
                tickfont=dict(color='#FFFFFF')
            ),
            'yaxis2': dict(
                title="평균 ROI (%)", 
                overlaying='y', 
                side='right',
                color='#FF0080',
                tickfont=dict(color='#FF0080')
            ),
            'height': 400,  # 유지 (작은 차트)
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig
    
    def create_channel_type_pie(self, df):
        """생방송 vs 비생방송 채널 비교 - Dark Mode"""
        channel_comparison = df.groupby('channel_type')['revenue'].sum()
        
        fig = go.Figure(data=[go.Pie(
            labels=channel_comparison.index,
            values=channel_comparison.values,
            hole=0.3,
            marker=dict(
                colors=['#00D9FF', '#7C3AED'],
                line=dict(color='rgba(255, 255, 255, 0.2)', width=2)
            ),
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=12, color='#FFFFFF'),
            hovertemplate='<b>%{label}</b><br>매출: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        layout_config = self.default_layout.copy()
        layout_config.update({
            'title': dict(
                text="채널 유형별 매출 비중",
                font=dict(size=18, color='#FFFFFF'),
                x=0.5,
                xanchor='center'
            ),
            'height': 400,  # 유지 (작은 차트)
            'showlegend': False,
            'hoverlabel': ENHANCED_HOVER_CONFIG
        })
        
        fig.update_layout(**layout_config)
        
        return fig

# ============================================================================
# 차트 래퍼 함수들
# ============================================================================

def create_cached_chart(chart_generator, chart_type, df, **kwargs):
    """캐시된 차트 생성 래퍼"""
    df_json = df.to_json(date_format='iso', orient='records')
    
    data_hash = hashlib.md5(df_json.encode()).hexdigest()[:8]
    cache_key = generate_chart_key(chart_type, data_hash, **kwargs)
    
    if 'chart_cache' not in st.session_state:
        st.session_state.chart_cache = {}
    
    if cache_key in st.session_state.chart_cache:
        cached_chart = st.session_state.chart_cache[cache_key]
        return emergency_hover_fix(cached_chart)
    
    if chart_type == 'platform_heatmap':
        chart = chart_generator.create_platform_heatmap(df_json, kwargs.get('platform_name'))
    elif chart_type == 'category_pie':
        category_colors_json = json.dumps(CATEGORY_COLORS_UNIQUE)  # 수정: 고유 색상 사용
        chart = chart_generator.create_category_pie_cached(
            df_json, 
            category_colors_json, 
            kwargs.get('top_n', 10)
        )
    elif chart_type == 'revenue_treemap':
        chart = chart_generator.create_revenue_treemap_cached(df_json)
    elif chart_type == 'roi_heatmap':
        chart = chart_generator.create_category_roi_heatmap(df_json, kwargs.get('category_name'))
    else:
        chart = None
    
    if chart:
        chart = emergency_hover_fix(chart)
        st.session_state.chart_cache[cache_key] = chart
    
    return chart

# ============================================================================
# 차트 테마 적용
# ============================================================================

def apply_chart_theme_optimized(fig, theme_config=None):
    """차트에 Dark Mode 테마 적용"""
    if not theme_config:
        theme_config = DARK_CHART_LAYOUT
    
    update_dict = {}
    
    if 'paper_bgcolor' in theme_config:
        update_dict['paper_bgcolor'] = theme_config['paper_bgcolor']
    if 'plot_bgcolor' in theme_config:
        update_dict['plot_bgcolor'] = theme_config['plot_bgcolor']
    if 'font' in theme_config:
        update_dict['font'] = theme_config['font']
    if 'height' in theme_config:
        update_dict['height'] = theme_config['height']
    
    # 호버라벨 설정 강제 적용
    update_dict['hoverlabel'] = ENHANCED_HOVER_CONFIG
    
    if update_dict:
        fig.update_layout(**update_dict)
    
    return fig

# ============================================================================
# 성능 모니터링
# ============================================================================

def monitor_chart_performance(chart_type: str, start_time: float):
    """차트 생성 성능 모니터링"""
    import time
    
    elapsed = time.time() - start_time
    
    if 'chart_timings' not in st.session_state:
        st.session_state.chart_timings = {}
    
    st.session_state.chart_timings[chart_type] = elapsed
    
    if elapsed > 1.0:
        st.warning(f"⚠️ {chart_type} 차트 생성이 느립니다 ({elapsed:.2f}초)")

# ============================================================================
# 배치 차트 생성
# ============================================================================

class BatchChartGenerator:
    """여러 차트를 효율적으로 생성"""
    
    def __init__(self, chart_generator):
        self.generator = chart_generator
        self.queue = []
    
    def add_to_queue(self, chart_type: str, df: pd.DataFrame, **kwargs):
        """차트를 큐에 추가"""
        self.queue.append({
            'type': chart_type,
            'df': df,
            'kwargs': kwargs
        })
    
    def generate_all(self):
        """큐의 모든 차트 생성"""
        charts = {}
        
        for item in self.queue:
            if item['type'] == 'platform_comparison':
                chart = self.generator.create_platform_comparison_optimized(
                    item['df'], 
                    **item['kwargs']
                )
            elif item['type'] == 'hourly_revenue':
                chart = self.generator.create_hourly_revenue_bar_optimized(
                    item['df'], 
                    **item['kwargs']
                )
            else:
                chart = None
            
            if chart:
                chart = emergency_hover_fix(chart)
                charts[item['type']] = chart
        
        self.queue.clear()
        
        return charts

# ============================================================================
# 히트맵 특화 함수들
# ============================================================================

def create_enhanced_roi_heatmap(df, category_name, platform_colors=None):
    """향상된 ROI 히트맵 생성"""
    cat_data = df[df['category'] == category_name]
    
    if len(cat_data) == 0:
        return None
    
    # 방송사별 ROI 계산
    platform_roi = cat_data.groupby('platform').agg({
        'real_profit': 'sum',
        'total_cost': 'sum',
        'revenue': 'sum',
        'broadcast': 'count'
    }).reset_index()
    
    # 최소 방송 수 필터링 (5회 이상)
    platform_roi = platform_roi[platform_roi['broadcast'] >= 5]
    
    platform_roi['roi_calculated'] = np.where(
        platform_roi['total_cost'] > 0,
        (platform_roi['real_profit'] / platform_roi['total_cost']) * 100,
        0
    )
    
    # 매출 기준으로 상위 15개 선택
    top_platforms = platform_roi.nlargest(15, 'revenue')
    
    if len(top_platforms) == 0:
        return None
    
    roi_values = top_platforms['roi_calculated'].values.reshape(-1, 1)
    
    # ROI 데이터 최적화
    roi_config = optimize_roi_heatmap_colors(roi_values)
    
    # 텍스트 값 생성 (소수점 1자리)
    text_values = [[f"{val:.1f}%" if abs(val) > 0.1 else "0%" for val in row] 
                  for row in roi_values]
    
    fig = go.Figure(data=go.Heatmap(
        z=roi_values,
        x=[category_name],
        y=top_platforms['platform'].tolist(),
        text=text_values,
        texttemplate='%{text}',
        textfont={"size": 16, "color": '#FFFFFF'},
        hovertemplate='<b>%{y}</b><br>카테고리: %{x}<br>실질 ROI: %{z:.1f}%<br>방송수: %{customdata}회<extra></extra>',
        customdata=top_platforms['broadcast'].values.reshape(-1, 1),
        colorbar=dict(
            title=dict(
                text="실질 ROI (%)",
                font=dict(color='#FFFFFF', size=16)
            ),
            tickfont=dict(color='#FFFFFF', size=13),
            bgcolor='rgba(0, 0, 0, 0)',
            bordercolor='#00D9FF',
            thickness=25,
            len=0.8
        ),
        **roi_config
    ))
    
    fig.update_layout(
        title=dict(
            text=f"{category_name} 카테고리 방송사별 실질 ROI",
            font=dict(size=20, color='#FFFFFF'),
            x=0.5,
            xanchor='center'
        ),
        height=600,  # 수정: 높이 증가
        xaxis=dict(
            title="카테고리",
            tickfont=dict(color='#FFFFFF', size=14),
            color='#FFFFFF'
        ),
        yaxis=dict(
            title="방송사",
            autorange="reversed",
            tickfont=dict(color='#FFFFFF', size=14),
            color='#FFFFFF'
        ),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(color='#FFFFFF'),
        hoverlabel=HEATMAP_HOVER_CONFIG
    )
    
    return fig

# ============================================================================
# Y축 포맷 함수 추가
# ============================================================================

def format_korean_number(value):
    """숫자를 한국식 단위로 포맷"""
    if value >= 100000000:  # 1억 이상
        return f"{value/100000000:.1f}억"
    elif value >= 10000000:  # 1천만 이상
        return f"{value/10000000:.0f}천만"
    else:
        return f"{value/1000000:.0f}백만"

# ============================================================================
# 호환성을 위한 별칭
# ============================================================================

OptimizedChartGenerator = ChartGenerator