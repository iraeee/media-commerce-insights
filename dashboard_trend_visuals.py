"""
dashboard_trend_visuals.py - 추세 시각화 모듈
Version: 1.1.1
Created: 2025-01-25
Updated: 2025-09-12 - 색상 딕셔너리 참조 오류 수정

추세 분석 결과를 시각화하는 Plotly 기반 차트 컴포넌트
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TrendVisualizer:
    """추세 시각화 클래스"""
    
    def __init__(self, colors=None):
        """
        초기화
        
        Parameters:
        -----------
        colors : dict
            색상 테마 딕셔너리
        """
        # 기본 색상 정의
        default_colors = {
            'primary': '#00D9FF',
            'secondary': '#FF6B6B',
            'success': '#10F981',
            'warning': '#FFB800',
            'danger': '#FF0080',
            'info': '#4ECDC4',
            'light': '#FFFFFF',
            'dark': '#000000',
            'text_primary': '#FFFFFF',
            'text_secondary': '#B8B8B8',
            'text_muted': '#808080',
            'background': 'rgba(0, 0, 0, 0)',
            'background_secondary': 'rgba(255, 255, 255, 0.02)',
            'border': 'rgba(255, 255, 255, 0.1)',
        }
        
        # 전달된 colors가 있으면 기본값과 병합
        if colors:
            # colors 딕셔너리의 모든 키를 체크하고 없으면 기본값 사용
            self.colors = default_colors.copy()
            if isinstance(colors, dict):
                self.colors.update(colors)
        else:
            self.colors = default_colors
        
        self.chart_height = 720  # 600 -> 720 (20% 증가)
        self.chart_height_small = 480  # 400 -> 480 (20% 증가)
        
    def _validate_dataframe(self, df, required_columns=None):
        """
        데이터프레임 검증
        
        Parameters:
        -----------
        df : DataFrame
            검증할 데이터프레임
        required_columns : list
            필수 컬럼 리스트
            
        Returns:
        --------
        bool : 유효성 여부
        """
        if df is None or df.empty:
            return False
        
        if required_columns:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                print(f"⚠️ 누락된 컬럼: {missing_cols}")
                return False
        
        return True
    
    def _safe_numeric_conversion(self, series):
        """안전한 숫자 변환"""
        if series.dtype not in ['float64', 'int64']:
            return pd.to_numeric(series, errors='coerce').fillna(0)
        return series
    
    def _get_color(self, key, default='#808080'):
        """안전한 색상 키 접근"""
        return self.colors.get(key, default)
    
    def create_main_trend_chart(self, df, period='일별', show_forecast=False):
        """
        메인 추세 차트 생성
        - 매출 추이
        - 이동평균선
        - 볼린저 밴드
        - 이상치 표시
        - 성장률 차트
        
        Parameters:
        -----------
        df : DataFrame
            추세 데이터
        period : str
            기간 단위
        show_forecast : bool
            예측 표시 여부
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        # 데이터 검증
        if not self._validate_dataframe(df, ['date', 'revenue']):
            return self._create_empty_chart("데이터가 없습니다")
        
        # 숫자 컬럼 변환
        df = df.copy()
        df['revenue'] = self._safe_numeric_conversion(df['revenue'])
        
        # 서브플롯 생성
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=('매출 추세', '성장률'),
            vertical_spacing=0.1,
            shared_xaxes=True
        )
        
        # 매출 추이 (메인 차트)
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['revenue'],
                name='매출',
                mode='lines+markers',
                line=dict(color=self._get_color('primary'), width=2),
                marker=dict(size=4, color=self._get_color('primary')),
                hovertemplate='날짜: %{x}<br>매출: %{y:,.0f}원<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 7일 이동평균
        if 'ma_7' in df.columns:
            df['ma_7'] = self._safe_numeric_conversion(df['ma_7'])
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['ma_7'],
                    name='7일 평균',
                    mode='lines',
                    line=dict(color=self._get_color('secondary'), width=1.5, dash='dot'),
                    hovertemplate='7일 평균: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 30일 이동평균
        if 'ma_30' in df.columns:
            df['ma_30'] = self._safe_numeric_conversion(df['ma_30'])
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['ma_30'],
                    name='30일 평균',
                    mode='lines',
                    line=dict(color=self._get_color('info'), width=1.5, dash='dash'),
                    hovertemplate='30일 평균: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 볼린저 밴드 (신뢰구간)
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            df['bb_upper'] = self._safe_numeric_conversion(df['bb_upper'])
            df['bb_lower'] = self._safe_numeric_conversion(df['bb_lower'])
            
            # 밴드 영역 채우기
            fig.add_trace(
                go.Scatter(
                    x=df['date'].tolist() + df['date'].tolist()[::-1],
                    y=df['bb_upper'].tolist() + df['bb_lower'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(124, 58, 237, 0.1)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='신뢰구간',
                    showlegend=True,
                    hoverinfo='skip'
                ),
                row=1, col=1
            )
            
            # 상단 밴드 라인
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['bb_upper'],
                    name='상단 밴드',
                    mode='lines',
                    line=dict(color='rgba(124, 58, 237, 0.3)', width=1, dash='dash'),
                    showlegend=False,
                    hovertemplate='상단: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
            
            # 하단 밴드 라인
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['bb_lower'],
                    name='하단 밴드',
                    mode='lines',
                    line=dict(color='rgba(124, 58, 237, 0.3)', width=1, dash='dash'),
                    showlegend=False,
                    hovertemplate='하단: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 이상치 표시
        if 'is_anomaly' in df.columns:
            anomalies = df[df['is_anomaly'] == True]
            if not anomalies.empty:
                fig.add_trace(
                    go.Scatter(
                        x=anomalies['date'],
                        y=anomalies['revenue'],
                        mode='markers',
                        name='이상치',
                        marker=dict(
                            color=self._get_color('danger'),
                            size=12,
                            symbol='diamond',
                            line=dict(color='white', width=2)
                        ),
                        hovertemplate='⚠️ 이상치<br>날짜: %{x}<br>매출: %{y:,.0f}원<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # 예측 표시 (선택)
        if show_forecast and 'forecast_revenue' in df.columns:
            df['forecast_revenue'] = self._safe_numeric_conversion(df['forecast_revenue'])
            forecast_mask = df['forecast_revenue'].notna() & df['revenue'].isna()
            if forecast_mask.any():
                forecast_data = df[forecast_mask]
                fig.add_trace(
                    go.Scatter(
                        x=forecast_data['date'],
                        y=forecast_data['forecast_revenue'],
                        name='예측',
                        mode='lines+markers',
                        line=dict(color=self._get_color('warning'), width=2, dash='dash'),
                        marker=dict(size=6, color=self._get_color('warning')),
                        hovertemplate='예측<br>날짜: %{x}<br>예상 매출: %{y:,.0f}원<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # 성장률 차트 (하단)
        if 'revenue_dod' in df.columns:
            df['revenue_dod'] = self._safe_numeric_conversion(df['revenue_dod'])
            colors = [self._get_color('success') if x >= 0 else self._get_color('danger') 
                     for x in df['revenue_dod'].fillna(0)]
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['revenue_dod'],
                    name='전일 대비',
                    marker_color=colors,
                    hovertemplate='전일 대비: %{y:+.1f}%<extra></extra>'
                ),
                row=2, col=1
            )
        
        # Y축 범위 계산 (2.5b 단위)
        max_revenue = df['revenue'].max() if not df['revenue'].isna().all() else 5e9
        y_max = np.ceil(max_revenue / 2.5e9) * 2.5e9
        
        # 레이아웃 설정
        fig.update_layout(
            title={
                'text': f'📈 매출 추세 분석 ({period})',
                'font': {'size': 24, 'color': self._get_color('text_primary')},
                'x': 0.5,
                'xanchor': 'center'
            },
            height=self.chart_height,
            paper_bgcolor=self._get_color('background'),
            plot_bgcolor=self._get_color('background_secondary'),
            font=dict(color=self._get_color('text_primary')),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='rgba(0, 0, 0, 0.8)',
                bordercolor=self._get_color('primary'),
                font=dict(color=self._get_color('text_primary'))
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(0, 0, 0, 0.5)',
                bordercolor=self._get_color('primary'),
                borderwidth=1
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor=self._get_color('border'),
                zeroline=False
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=self._get_color('border'),
                zeroline=False,
                title='매출 (원)',
                title_font=dict(size=12),
                range=[0, y_max],
                dtick=2.5e9,  # 2.5b 단위
                tickformat=',.0f'
            ),
            xaxis2=dict(
                showgrid=True,
                gridcolor=self._get_color('border')
            ),
            yaxis2=dict(
                showgrid=True,
                gridcolor=self._get_color('border'),
                zeroline=True,
                zerolinecolor='rgba(255, 255, 255, 0.2)',
                title='성장률 (%)',
                title_font=dict(size=12)
            )
        )
        
        return fig
    
    def create_category_trend_heatmap(self, df_category):
        """
        카테고리별 추세 히트맵 (수정 버전)
        
        Parameters:
        -----------
        df_category : DataFrame
            카테고리별 데이터 (week, category, growth_rate 컬럼 필요)
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        if not self._validate_dataframe(df_category, ['week', 'category']):
            return self._create_empty_chart("카테고리 데이터가 없습니다")
        
        try:
            # growth_rate 컬럼이 없으면 revenue 사용
            if 'growth_rate' in df_category.columns:
                value_col = 'growth_rate'
                title_suffix = '주간 성장률 매트릭스'
                colorbar_title = '성장률 (%)'
            else:
                value_col = 'revenue'
                title_suffix = '주간 매출 매트릭스'
                colorbar_title = '매출 (억원)'
                df_category[value_col] = df_category[value_col] / 1e8  # 억원 단위
            
            # 피벗 테이블 생성 (NaN을 0으로 채움)
            pivot = df_category.pivot_table(
                index='category',
                columns='week',
                values=value_col,
                aggfunc='mean',
                fill_value=0  # NaN을 0으로 채움
            )
            
            # 히트맵 생성
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                colorscale=[
                    [0, self._get_color('danger')],      # 큰 하락
                    [0.25, self._get_color('secondary')], # 소폭 하락
                    [0.5, '#FFFFFF'],                 # 중립
                    [0.75, self._get_color('info')],      # 소폭 상승
                    [1, self._get_color('success')]       # 큰 상승
                ],
                zmid=0,
                text=pivot.values.round(1),
                texttemplate='%{text}%',
                textfont={"size": 10},
                colorbar=dict(
                    title=dict(
                        text=colorbar_title,
                        side="right",
                        font=dict(color=self._get_color('text_primary'))
                    ),
                    tickmode="linear",
                    tick0=-50,
                    dtick=25,
                    ticks="outside",
                    tickcolor=self._get_color('text_primary'),
                    tickfont=dict(color=self._get_color('text_primary'))
                ),
                hovertemplate='카테고리: %{y}<br>주차: %{x}<br>성장률: %{z:.1f}%<extra></extra>'
            ))
            
            fig.update_layout(
                title={
                    'text': '📦 카테고리별 주간 성장률 매트릭스',
                    'font': {'size': 20, 'color': self._get_color('text_primary')},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                height=500,
                paper_bgcolor=self._get_color('background'),
                plot_bgcolor=self._get_color('background_secondary'),
                font=dict(color=self._get_color('text_primary')),
                xaxis=dict(
                    title='주차',
                    side='bottom',
                    gridcolor=self._get_color('border')
                ),
                yaxis=dict(
                    title='카테고리',
                    gridcolor=self._get_color('border')
                )
            )
            
            return fig
            
        except Exception as e:
            print(f"⚠️ 히트맵 생성 실패: {e}")
            return self._create_empty_chart("히트맵 생성 실패")
    
    def create_seasonal_pattern_chart(self, df):
        """
        계절성 패턴 차트 (레이더 차트)
        
        Parameters:
        -----------
        df : DataFrame
            계절성 데이터
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        try:
            # 월별 집계
            if 'seasonal_index_month' in df.columns:
                monthly = df.groupby('month').agg({
                    'revenue': 'mean',
                    'seasonal_index_month': 'mean'
                }).reset_index()
            else:
                # 날짜에서 월 추출
                df_copy = df.copy()
                df_copy['month'] = pd.to_datetime(df_copy['date']).dt.month
                monthly = df_copy.groupby('month').agg({
                    'revenue': 'mean'
                }).reset_index()
                monthly_avg = monthly['revenue'].mean()
                monthly['seasonal_index_month'] = (monthly['revenue'] / monthly_avg) * 100
            
            month_names = ['1월', '2월', '3월', '4월', '5월', '6월',
                          '7월', '8월', '9월', '10월', '11월', '12월']
            monthly['month_name'] = monthly['month'].apply(lambda x: month_names[x-1] if x <= 12 else str(x))
            
            # 레이더 차트
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=monthly['seasonal_index_month'],
                theta=monthly['month_name'],
                fill='toself',
                fillcolor='rgba(0, 217, 255, 0.2)',
                line=dict(color=self._get_color('primary'), width=2),
                marker=dict(size=8, color=self._get_color('primary')),
                name='계절 지수',
                hovertemplate='%{theta}<br>지수: %{r:.1f}<extra></extra>'
            ))
            
            # 평균선 (100)
            fig.add_trace(go.Scatterpolar(
                r=[100] * len(monthly),
                theta=monthly['month_name'],
                mode='lines',
                line=dict(color='rgba(255, 255, 255, 0.3)', dash='dash'),
                name='평균',
                hoverinfo='skip'
            ))
            
            fig.update_layout(
                title={
                    'text': '🌸 월별 계절성 패턴',
                    'font': {'size': 20, 'color': self._get_color('text_primary')},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(150, monthly['seasonal_index_month'].max() * 1.1)],
                        tickcolor=self._get_color('text_primary'),
                        gridcolor=self._get_color('border')
                    ),
                    angularaxis=dict(
                        tickcolor=self._get_color('text_primary'),
                        gridcolor=self._get_color('border')
                    ),
                    bgcolor=self._get_color('background')
                ),
                height=self.chart_height_small,
                paper_bgcolor=self._get_color('background'),
                font=dict(color=self._get_color('text_primary')),
                showlegend=True,
                legend=dict(
                    bgcolor='rgba(0, 0, 0, 0.5)',
                    bordercolor=self._get_color('primary'),
                    borderwidth=1
                )
            )
            
            return fig
            
        except Exception as e:
            print(f"⚠️ 계절성 차트 생성 실패: {e}")
            return self._create_empty_chart("계절성 데이터 부족")
    
    def create_weekday_pattern_chart(self, df):
        """
        요일별 패턴 차트
        
        Parameters:
        -----------
        df : DataFrame
            요일별 데이터
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        try:
            # 요일별 집계
            if 'weekday' not in df.columns:
                df['weekday'] = pd.to_datetime(df['date']).dt.dayofweek
            
            weekday_revenue = df.groupby('weekday')['revenue'].mean().reset_index()
            weekday_names = ['월', '화', '수', '목', '금', '토', '일']
            weekday_revenue['weekday_name'] = weekday_revenue['weekday'].apply(lambda x: weekday_names[x])
            
            # 색상 설정 (평일/주말 구분)
            colors = [self._get_color('primary') if i < 5 else self._get_color('danger') 
                     for i in range(7)]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=weekday_revenue['weekday_name'],
                    y=weekday_revenue['revenue'],
                    marker_color=colors,
                    text=weekday_revenue['revenue'].apply(lambda x: f'{x/1e8:.1f}억'),
                    textposition='outside',
                    hovertemplate='%{x}요일<br>평균 매출: %{y:,.0f}원<extra></extra>'
                )
            ])
            
            # 평균선 추가
            avg_revenue = weekday_revenue['revenue'].mean()
            fig.add_hline(
                y=avg_revenue,
                line_dash="dash",
                line_color=self._get_color('warning'),
                annotation_text=f"평균: {avg_revenue/1e8:.1f}억",
                annotation_position="right"
            )
            
            fig.update_layout(
                title={
                    'text': '📅 요일별 평균 매출',
                    'font': {'size': 20, 'color': self._get_color('text_primary')},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                height=self.chart_height_small,
                paper_bgcolor=self._get_color('background'),
                plot_bgcolor=self._get_color('background_secondary'),
                font=dict(color=self._get_color('text_primary')),
                xaxis=dict(
                    title='요일',
                    gridcolor=self._get_color('border')
                ),
                yaxis=dict(
                    title='평균 매출',
                    showgrid=True,
                    gridcolor=self._get_color('border')
                ),
                bargap=0.2
            )
            
            return fig
            
        except Exception as e:
            print(f"⚠️ 요일별 차트 생성 실패: {e}")
            return self._create_empty_chart("요일별 데이터 부족")
    
    def create_volatility_chart(self, df):
        """
        변동성 차트
        
        Parameters:
        -----------
        df : DataFrame
            변동성 데이터
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        if not self._validate_dataframe(df, ['date', 'revenue']):
            return self._create_empty_chart("변동성 데이터가 없습니다")
        
        try:
            df = df.copy()
            df['revenue'] = self._safe_numeric_conversion(df['revenue'])
            
            fig = make_subplots(
                rows=2, cols=1,
                row_heights=[0.6, 0.4],
                subplot_titles=('매출 및 변동성', '변동계수 (CV)'),
                vertical_spacing=0.12,
                shared_xaxes=True
            )
            
            # 매출 및 변동성
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['revenue'],
                    name='매출',
                    mode='lines',
                    line=dict(color=self._get_color('primary'), width=2),
                    yaxis='y',
                    hovertemplate='매출: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
            
            if 'volatility_30' in df.columns:
                df['volatility_30'] = self._safe_numeric_conversion(df['volatility_30'])
                # 변동성을 2차 y축으로
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['volatility_30'],
                        name='변동성 (30일)',
                        mode='lines',
                        line=dict(color=self._get_color('warning'), width=1.5, dash='dot'),
                        yaxis='y2',
                        hovertemplate='변동성: %{y:,.0f}<extra></extra>'
                    ),
                    row=1, col=1
                )
            
            # 변동계수
            if 'cv_30' in df.columns:
                df['cv_30'] = self._safe_numeric_conversion(df['cv_30'])
                # 색상 설정 (임계값 기준)
                colors = []
                for cv in df['cv_30'].fillna(0):
                    if cv > 0.3:
                        colors.append(self._get_color('danger'))
                    elif cv > 0.15:
                        colors.append(self._get_color('warning'))
                    else:
                        colors.append(self._get_color('success'))
                
                fig.add_trace(
                    go.Bar(
                        x=df['date'],
                        y=df['cv_30'],
                        name='변동계수',
                        marker_color=colors,
                        hovertemplate='CV: %{y:.2f}<extra></extra>'
                    ),
                    row=2, col=1
                )
                
                # 임계선
                fig.add_hline(
                    y=0.3, row=2, col=1,
                    line_dash="dash",
                    line_color=self._get_color('danger'),
                    annotation_text="높은 변동성",
                    annotation_position="right"
                )
                fig.add_hline(
                    y=0.15, row=2, col=1,
                    line_dash="dash",
                    line_color=self._get_color('warning'),
                    annotation_text="보통",
                    annotation_position="right"
                )
            
            # Y축 범위 계산 (5b 단위)
            max_revenue = df['revenue'].max() if not df['revenue'].isna().all() else 5e9
            y_max = np.ceil(max_revenue / 5e9) * 5e9
            
            # 레이아웃 설정
            fig.update_layout(
                title={
                    'text': '📊 매출 변동성 분석',
                    'font': {'size': 20, 'color': self._get_color('text_primary')},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                height=self.chart_height,  # 720px로 증가
                paper_bgcolor=self._get_color('background'),
                plot_bgcolor=self._get_color('background_secondary'),
                font=dict(color=self._get_color('text_primary')),
                hovermode='x unified',
                xaxis=dict(
                    showgrid=True,
                    gridcolor=self._get_color('border')
                ),
                yaxis=dict(
                    title='매출 (원)',
                    showgrid=True,
                    gridcolor=self._get_color('border'),
                    range=[0, y_max],
                    dtick=5e9,  # 5b 단위
                    tickformat=',.0f'
                ),
                yaxis2=dict(
                    title='변동성',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                xaxis2=dict(
                    showgrid=True,
                    gridcolor=self._get_color('border')
                ),
                yaxis3=dict(
                    title='변동계수',
                    showgrid=True,
                    gridcolor=self._get_color('border')
                ),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(0, 0, 0, 0.5)',
                    bordercolor=self._get_color('primary'),
                    borderwidth=1
                )
            )
            
            return fig
            
        except Exception as e:
            print(f"⚠️ 변동성 차트 생성 실패: {e}")
            return self._create_empty_chart("변동성 차트 생성 실패")
    
    def create_growth_comparison_chart(self, df, periods=['revenue_dod', 'revenue_wow', 'revenue_mom']):
        """
        성장률 비교 차트 (색상 구분 개선)
        
        Parameters:
        -----------
        df : DataFrame
            성장률 데이터
        periods : list
            비교할 기간 리스트
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        period_names = {
            'revenue_dod': '전일 대비',
            'revenue_wow': '전주 대비',
            'revenue_mom': '전월 대비',
            'revenue_yoy': '전년 대비'
        }
        
        # 각 기간별로 명확히 다른 색상 사용
        period_colors = {
            'revenue_dod': self._get_color('primary'),    # 파란색
            'revenue_wow': self._get_color('success'),    # 초록색
            'revenue_mom': '#B794F4',                     # 보라색 (명확히 구분)
            'revenue_yoy': self._get_color('warning')     # 주황색
        }
        
        fig = go.Figure()
        
        has_data = False
        for period in periods:
            if period in df.columns:
                df[period] = self._safe_numeric_conversion(df[period])
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df[period],
                    name=period_names.get(period, period),
                    mode='lines',
                    line=dict(
                        color=period_colors.get(period, self._get_color('primary')),
                        width=2
                    ),
                    hovertemplate=f'{period_names.get(period, period)}: %{{y:.1f}}%<extra></extra>'
                ))
                has_data = True
        
        if not has_data:
            return self._create_empty_chart("성장률 데이터가 없습니다")
        
        # 0 기준선
        fig.add_hline(
            y=0,
            line_dash="solid",
            line_color='rgba(255, 255, 255, 0.3)',
            line_width=1
        )
        
        fig.update_layout(
            title={
                'text': '📈 성장률 비교',
                'font': {'size': 20, 'color': self._get_color('text_primary')},
                'x': 0.5,
                'xanchor': 'center'
            },
            height=self.chart_height_small,
            paper_bgcolor=self._get_color('background'),
            plot_bgcolor=self._get_color('background_secondary'),
            font=dict(color=self._get_color('text_primary')),
            xaxis=dict(
                title='날짜',
                showgrid=True,
                gridcolor=self._get_color('border')
            ),
            yaxis=dict(
                title='성장률 (%)',
                showgrid=True,
                gridcolor=self._get_color('border'),
                zeroline=True,
                zerolinecolor='rgba(255, 255, 255, 0.3)'
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                bgcolor='rgba(0, 0, 0, 0.5)',
                bordercolor=self._get_color('primary'),
                borderwidth=1
            )
        )
        
        return fig
    
    def create_momentum_indicator(self, df):
        """
        모멘텀 지표 차트 (RSI 등)
        
        Parameters:
        -----------
        df : DataFrame
            모멘텀 데이터
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        fig = go.Figure()
        
        if 'rsi_14' in df.columns:
            df['rsi_14'] = self._safe_numeric_conversion(df['rsi_14'])
            
            # RSI 라인
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['rsi_14'],
                name='RSI(14)',
                mode='lines',
                line=dict(color=self._get_color('primary'), width=2),
                hovertemplate='RSI: %{y:.1f}<extra></extra>'
            ))
            
            # 과매수/과매도 구간
            fig.add_hrect(
                y0=70, y1=100,
                fillcolor=self._get_color('danger'),
                opacity=0.1,
                line_width=0,
                annotation_text="과매수",
                annotation_position="top left"
            )
            
            fig.add_hrect(
                y0=0, y1=30,
                fillcolor=self._get_color('success'),
                opacity=0.1,
                line_width=0,
                annotation_text="과매도",
                annotation_position="bottom left"
            )
            
            # 중립선
            fig.add_hline(
                y=50,
                line_dash="dash",
                line_color='rgba(255, 255, 255, 0.3)',
                annotation_text="중립",
                annotation_position="right"
            )
        else:
            return self._create_empty_chart("RSI 데이터가 없습니다")
        
        fig.update_layout(
            title={
                'text': '📊 모멘텀 지표 (RSI)',
                'font': {'size': 20, 'color': self._get_color('text_primary')},
                'x': 0.5,
                'xanchor': 'center'
            },
            height=300,
            paper_bgcolor=self._get_color('background'),
            plot_bgcolor=self._get_color('background_secondary'),
            font=dict(color=self._get_color('text_primary')),
            xaxis=dict(
                title='날짜',
                showgrid=True,
                gridcolor=self._get_color('border')
            ),
            yaxis=dict(
                title='RSI',
                range=[0, 100],
                showgrid=True,
                gridcolor=self._get_color('border')
            ),
            hovermode='x unified'
        )
        
        return fig
    
    def create_forecast_chart(self, df, forecast_data=None):
        """
        예측 차트
        
        Parameters:
        -----------
        df : DataFrame
            실제 데이터
        forecast_data : DataFrame
            예측 데이터
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        fig = go.Figure()
        
        # 실제 데이터
        df['revenue'] = self._safe_numeric_conversion(df['revenue'])
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['revenue'],
            name='실제',
            mode='lines+markers',
            line=dict(color=self._get_color('primary'), width=2),
            marker=dict(size=4)
        ))
        
        # 예측 데이터
        if forecast_data is not None and not forecast_data.empty:
            forecast_data['forecast'] = self._safe_numeric_conversion(forecast_data['forecast'])
            fig.add_trace(go.Scatter(
                x=forecast_data['date'],
                y=forecast_data['forecast'],
                name='예측',
                mode='lines+markers',
                line=dict(color=self._get_color('warning'), width=2, dash='dash'),
                marker=dict(size=6)
            ))
            
            # 신뢰구간
            if 'lower_bound' in forecast_data.columns and 'upper_bound' in forecast_data.columns:
                forecast_data['lower_bound'] = self._safe_numeric_conversion(forecast_data['lower_bound'])
                forecast_data['upper_bound'] = self._safe_numeric_conversion(forecast_data['upper_bound'])
                
                fig.add_trace(go.Scatter(
                    x=forecast_data['date'].tolist() + forecast_data['date'].tolist()[::-1],
                    y=forecast_data['upper_bound'].tolist() + forecast_data['lower_bound'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(255, 184, 0, 0.1)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='신뢰구간',
                    hoverinfo='skip'
                ))
        
        fig.update_layout(
            title={
                'text': '🔮 매출 예측',
                'font': {'size': 20, 'color': self._get_color('text_primary')},
                'x': 0.5,
                'xanchor': 'center'
            },
            height=self.chart_height_small,
            paper_bgcolor=self._get_color('background'),
            plot_bgcolor=self._get_color('background_secondary'),
            font=dict(color=self._get_color('text_primary')),
            xaxis=dict(
                title='날짜',
                showgrid=True,
                gridcolor=self._get_color('border')
            ),
            yaxis=dict(
                title='매출',
                showgrid=True,
                gridcolor=self._get_color('border')
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                bgcolor='rgba(0, 0, 0, 0.5)',
                bordercolor=self._get_color('primary'),
                borderwidth=1
            )
        )
        
        return fig
    
    def create_trend_summary_table(self, summary_stats):
        """
        추세 요약 테이블
        
        Parameters:
        -----------
        summary_stats : dict
            요약 통계
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        if not summary_stats:
            return self._create_empty_chart("요약 통계가 없습니다")
        
        # 딕셔너리를 테이블 형식으로 변환
        headers = ['지표', '값']
        values = [
            list(summary_stats.keys()),
            [str(v) for v in summary_stats.values()]
        ]
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=headers,
                fill_color='rgba(0, 217, 255, 0.2)',
                align='left',
                font=dict(color=self._get_color('text_primary'), size=14)
            ),
            cells=dict(
                values=values,
                fill_color='rgba(255, 255, 255, 0.02)',
                align='left',
                font=dict(color=self._get_color('text_primary'), size=12),
                height=30
            )
        )])
        
        fig.update_layout(
            title={
                'text': '📊 추세 분석 요약',
                'font': {'size': 18, 'color': self._get_color('text_primary')},
                'x': 0.5,
                'xanchor': 'center'
            },
            height=400,
            paper_bgcolor=self._get_color('background'),
            font=dict(color=self._get_color('text_primary'))
        )
        
        return fig
    
    def _create_empty_chart(self, message="데이터가 없습니다"):
        """
        빈 차트 생성 (에러 처리용)
        
        Parameters:
        -----------
        message : str
            표시할 메시지
            
        Returns:
        --------
        Figure : Plotly Figure 객체
        """
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=self._get_color('text_muted'))
        )
        
        fig.update_layout(
            height=400,
            paper_bgcolor=self._get_color('background'),
            plot_bgcolor=self._get_color('background_secondary'),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        
        return fig


# 유틸리티 함수들
def create_trend_charts(df, colors=None):
    """
    모든 추세 차트를 한 번에 생성하는 헬퍼 함수
    
    Parameters:
    -----------
    df : DataFrame
        추세 데이터
    colors : dict
        색상 테마
        
    Returns:
    --------
    dict : 차트 딕셔너리
    """
    visualizer = TrendVisualizer(colors)
    
    charts = {}
    
    try:
        # 메인 추세 차트
        charts['main_trend'] = visualizer.create_main_trend_chart(df)
        
        # 계절성 차트
        charts['seasonal'] = visualizer.create_seasonal_pattern_chart(df)
        
        # 요일별 차트
        charts['weekday'] = visualizer.create_weekday_pattern_chart(df)
        
        # 변동성 차트
        charts['volatility'] = visualizer.create_volatility_chart(df)
        
        # 성장률 비교
        charts['growth'] = visualizer.create_growth_comparison_chart(df)
        
        # RSI
        if 'rsi_14' in df.columns:
            charts['rsi'] = visualizer.create_momentum_indicator(df)
        
    except Exception as e:
        print(f"차트 생성 중 오류: {e}")
    
    return charts


if __name__ == "__main__":
    """테스트 실행"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # 테스트 데이터 생성
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    df = pd.DataFrame({
        'date': dates,
        'revenue': np.random.normal(100000000, 20000000, len(dates)),
        'units_sold': np.random.normal(1000, 200, len(dates)),
        'roi_calculated': np.random.normal(50, 10, len(dates))
    })
    
    # 추가 지표 계산
    df['revenue_dod'] = df['revenue'].pct_change() * 100
    df['ma_7'] = df['revenue'].rolling(7).mean()
    df['ma_30'] = df['revenue'].rolling(30).mean()
    df['volatility_30'] = df['revenue'].rolling(30).std()
    df['cv_30'] = df['volatility_30'] / df['ma_30']
    df['bb_upper'] = df['ma_30'] + 2 * df['volatility_30']
    df['bb_lower'] = df['ma_30'] - 2 * df['volatility_30']
    df['is_anomaly'] = np.abs((df['revenue'] - df['ma_30']) / df['volatility_30']) > 3
    df['rsi_14'] = 50 + np.random.normal(0, 20, len(dates))
    df['month'] = df['date'].dt.month
    df['weekday'] = df['date'].dt.dayofweek
    
    # 시각화 테스트
    visualizer = TrendVisualizer()
    
    print("📊 추세 시각화 모듈 테스트")
    print("=" * 60)
    
    # 각 차트 테스트
    charts = create_trend_charts(df)
    
    for name, chart in charts.items():
        if chart:
            print(f"✅ {name} 차트 생성 성공")
        else:
            print(f"❌ {name} 차트 생성 실패")
    
    print("\n✨ 테스트 완료!")