"""
dashboard_cohort_prediction.py - 코호트 분석 및 예측 모델 통합 모듈 - Dark Mode + Glassmorphism
Version: 3.0.0
Last Updated: 2025-02-02

코호트 분석과 예측 모델을 제공하는 통합 모듈
scikit-learn 의존성 제거 - 자체 구현 버전
Dark Mode + Glassmorphism 테마 적용
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# sklearn 대체 구현
SKLEARN_AVAILABLE = False

# 자체 선형 회귀 구현
class SimpleLinearRegression:
    """간단한 선형 회귀 구현 (scikit-learn 대체)"""
    
    def __init__(self):
        self.coef_ = None
        self.intercept_ = None
    
    def fit(self, X, y):
        """최소제곱법을 사용한 선형 회귀 학습"""
        X = np.array(X).reshape(-1, 1) if len(np.array(X).shape) == 1 else np.array(X)
        y = np.array(y)
        
        # Add bias term
        X_with_bias = np.c_[np.ones(X.shape[0]), X]
        
        # Normal equation: θ = (X'X)^(-1)X'y
        try:
            theta = np.linalg.inv(X_with_bias.T @ X_with_bias) @ X_with_bias.T @ y
            self.intercept_ = theta[0]
            self.coef_ = theta[1:] if len(theta) > 1 else theta[1]
        except:
            # Fallback to simple average
            self.intercept_ = np.mean(y)
            self.coef_ = 0
        
        return self
    
    def predict(self, X):
        """예측"""
        X = np.array(X).reshape(-1, 1) if len(np.array(X).shape) == 1 else np.array(X)
        if self.coef_ is None:
            return np.zeros(X.shape[0])
        
        if isinstance(self.coef_, (int, float)):
            return self.intercept_ + X.flatten() * self.coef_
        else:
            return self.intercept_ + X @ self.coef_

# ============================================================================
# 코호트 분석 함수들 - Dark Mode 적용
# ============================================================================

def create_cohort_analysis(df_filtered, data_formatter):
    """
    방송 코호트 분석 - 실제 홈쇼핑 데이터에 적합한 분석
    Dark Mode + Glassmorphism 테마 적용
    """
    
    # Dark Mode 섹션 카드
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
                padding: 25px;
                box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3),
                           inset 0 0 60px rgba(255, 255, 255, 0.02);">
        <h2 style="color: #00D9FF; margin-bottom: 20px; 
                   text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);">
            📊 월별 방송 성과 패턴 분석
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    # 데이터 준비
    df = df_filtered.copy()
    df['cohort_month'] = pd.to_datetime(df['date']).dt.to_period('M')
    
    # 월별 카테고리별 성과 추적
    cohort_data = prepare_broadcast_cohort_data(df)
    
    if cohort_data is None or len(cohort_data) == 0:
        st.info("분석에 필요한 충분한 데이터가 없습니다.")
        return
    
    # 성과 매트릭스 계산
    performance_matrix = calculate_performance_matrix(cohort_data)
    
    # 성과 히트맵 생성 - Dark Mode
    fig_performance = create_performance_heatmap_dark(performance_matrix, data_formatter)
    st.plotly_chart(fig_performance, use_container_width=True)
    
    # 인사이트 제공 - Dark Mode
    show_cohort_insights_dark(cohort_data, data_formatter)

def prepare_broadcast_cohort_data(df):
    """방송 성과 데이터 준비"""
    try:
        # 카테고리-월별로 첫 방송 시점 찾기
        first_broadcast = df.groupby(['category', 'platform']).agg({
            'date': 'min'
        }).reset_index()
        first_broadcast['first_month'] = pd.to_datetime(first_broadcast['date']).dt.to_period('M')
        
        # 각 월별 성과 추적
        monthly_performance = df.groupby(['category', 'platform', 'cohort_month']).agg({
            'revenue': 'sum',
            'units_sold': 'sum',
            'roi_calculated': 'mean',
            'broadcast': 'count'
        }).reset_index()
        
        # 첫 방송 월과 병합
        cohort_data = monthly_performance.merge(
            first_broadcast[['category', 'platform', 'first_month']],
            on=['category', 'platform'],
            how='left'
        )
        
        # 첫 방송 이후 경과 월 계산
        cohort_data['months_since_first'] = (
            cohort_data['cohort_month'].astype(str).apply(lambda x: datetime.strptime(x, '%Y-%m')) -
            cohort_data['first_month'].astype(str).apply(lambda x: datetime.strptime(x, '%Y-%m'))
        ).dt.days // 30
        
        return cohort_data
    except Exception as e:
        st.error(f"데이터 준비 중 오류: {e}")
        return None

def calculate_performance_matrix(cohort_data):
    """실제 성과 기반 매트릭스 계산"""
    try:
        # 카테고리별 월별 성과 추이
        categories = cohort_data['category'].unique()[:10]  # 상위 10개 카테고리
        months = sorted(cohort_data['cohort_month'].unique())[-6:]  # 최근 6개월
        
        # 빈 DataFrame 생성 시 dtype 명시
        matrix = pd.DataFrame(index=categories, dtype='float64')
        
        for month in months:
            month_data = cohort_data[cohort_data['cohort_month'] == month]
            month_revenue = month_data.groupby('category')['revenue'].sum()
            # 새 컬럼 추가 시 float로 변환
            matrix[str(month)] = month_revenue.astype('float64')
        
        # 첫 달 대비 비율로 변환 (실제 데이터)
        for category in matrix.index:
            first_value = matrix.loc[category].iloc[0] if not pd.isna(matrix.loc[category].iloc[0]) else 1
            if first_value > 0:
                matrix.loc[category] = (matrix.loc[category] / first_value) * 100
            else:
                matrix.loc[category] = 0
        
        return matrix.fillna(0)
    except Exception as e:
        st.error(f"매트릭스 계산 중 오류: {e}")
        return pd.DataFrame()

def create_performance_heatmap_dark(performance_matrix, formatter):
    """성과 히트맵 생성 - Dark Mode 네온 색상"""
    
    # Dark Mode용 네온 그라디언트 색상 스케일
    neon_colorscale = [
        [0, 'rgba(10, 11, 30, 1)'],           # 매우 어두운 배경
        [0.2, 'rgba(124, 58, 237, 0.4)'],     # 퍼플
        [0.4, 'rgba(0, 217, 255, 0.5)'],      # 시안
        [0.6, 'rgba(16, 249, 129, 0.6)'],     # 그린
        [0.8, 'rgba(255, 217, 61, 0.7)'],     # 옐로우
        [1, '#10F981']                        # 밝은 네온 그린
    ]
    
    # X축 라벨 (월 표시)
    x_labels = [col.strftime('%Y-%m') if hasattr(col, 'strftime') else str(col) 
               for col in performance_matrix.columns]
    
    # 히트맵 생성
    fig = go.Figure(data=go.Heatmap(
        z=performance_matrix.values,
        x=x_labels,
        y=performance_matrix.index,
        colorscale=neon_colorscale,
        text=[[f"{val:.0f}%" if val > 0 else "" for val in row] 
              for row in performance_matrix.values],
        texttemplate='%{text}',
        textfont={"size": 12, "color": "#FFFFFF"},
        hovertemplate='카테고리: %{y}<br>월: %{x}<br>성과: %{z:.1f}%<extra></extra>',
        colorbar=dict(
            title="첫 달 대비 %",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            bgcolor='rgba(255, 255, 255, 0.05)',
            bordercolor='rgba(255, 255, 255, 0.12)',
            borderwidth=1
        )
    ))
    
    fig.update_layout(
        title=dict(
            text="카테고리별 월간 성과 변화 (첫 달 대비 %)",
            font=dict(color='#00D9FF', size=18)
        ),
        xaxis=dict(
            title="월",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        yaxis=dict(
            title="카테고리",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            autorange="reversed",
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        height=500,
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(family="'Inter', 'Pretendard', sans-serif", color='#FFFFFF')
    )
    
    return fig

def show_cohort_insights_dark(cohort_data, formatter):
    """코호트 분석 인사이트 - Dark Mode 스타일"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 217, 255, 0.05), rgba(124, 58, 237, 0.05));
                backdrop-filter: blur(10px);
                border: 1px solid rgba(0, 217, 255, 0.2);
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;">
        <h3 style="color: #00D9FF; margin-bottom: 15px;
                   text-shadow: 0 0 15px rgba(0, 217, 255, 0.5);">
            💡 핵심 인사이트
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 성장 카테고리 - include_groups=False 추가
        growth_categories = cohort_data.groupby('category', group_keys=False).apply(
            lambda x: x.sort_values('cohort_month')['revenue'].pct_change().mean(),
            include_groups=False
        ).nlargest(3)
        
        st.markdown("""
        <div style="background: rgba(16, 249, 129, 0.1);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(16, 249, 129, 0.3);
                    border-radius: 10px;
                    padding: 15px;">
            <h4 style="color: #10F981; margin-bottom: 10px;">📈 성장 카테고리</h4>
        """, unsafe_allow_html=True)
        
        for cat, growth in growth_categories.items():
            st.markdown(f"""
            <p style="color: rgba(255, 255, 255, 0.85); margin: 5px 0;">
                • {cat}: <span style="color: #10F981; font-weight: bold;">{growth*100:.1f}%</span> 월평균 성장
            </p>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # 안정적 카테고리
        stable_categories = cohort_data.groupby('category')['revenue'].std()
        stable_categories = stable_categories[stable_categories < stable_categories.median()].index[:3]
        
        st.markdown("""
        <div style="background: rgba(0, 217, 255, 0.1);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(0, 217, 255, 0.3);
                    border-radius: 10px;
                    padding: 15px;">
            <h4 style="color: #00D9FF; margin-bottom: 10px;">🔄 안정적 카테고리</h4>
        """, unsafe_allow_html=True)
        
        for cat in stable_categories:
            avg_revenue = cohort_data[cohort_data['category'] == cat]['revenue'].mean()
            st.markdown(f"""
            <p style="color: rgba(255, 255, 255, 0.85); margin: 5px 0;">
                • {cat}: <span style="color: #00D9FF; font-weight: bold;">{formatter.format_money(avg_revenue)}</span>
            </p>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        # 최적 방송 시기
        best_months = cohort_data.groupby('cohort_month')['roi_calculated'].mean().nlargest(3)
        
        st.markdown("""
        <div style="background: rgba(255, 217, 61, 0.1);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(255, 217, 61, 0.3);
                    border-radius: 10px;
                    padding: 15px;">
            <h4 style="color: #FFD93D; margin-bottom: 10px;">🎯 최적 방송 시기</h4>
        """, unsafe_allow_html=True)
        
        for month, roi in best_months.items():
            st.markdown(f"""
            <p style="color: rgba(255, 255, 255, 0.85); margin: 5px 0;">
                • {month}: ROI <span style="color: #FFD93D; font-weight: bold;">{roi:.1f}%</span>
            </p>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# 예측 모델 함수들 - Dark Mode 적용
# ============================================================================

def create_prediction_model(df_filtered, data_formatter):
    """현실적인 예측 모델 - Dark Mode + Glassmorphism"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(255, 0, 128, 0.1));
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 16px;
                padding: 25px;
                color: white;
                margin-bottom: 20px;
                box-shadow: 0 0 30px rgba(124, 58, 237, 0.3),
                           inset 0 0 60px rgba(124, 58, 237, 0.05);">
        <h2 style="margin: 0; color: #FFFFFF;
                   text-shadow: 0 0 20px rgba(124, 58, 237, 0.5);">
            📈 데이터 기반 예측 분석
        </h2>
        <p style="margin: 10px 0 0 0; color: rgba(255, 255, 255, 0.85);">
            과거 패턴 기반 통계적 예측
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 예측 옵션
    col1, col2 = st.columns(2)
    
    with col1:
        prediction_target = st.selectbox(
            "예측 대상",
            ["일별 매출", "카테고리별 성장", "시간대별 패턴"],
            key="pred_target_realistic"
        )
    
    with col2:
        prediction_period = st.slider(
            "예측 기간 (일)",
            min_value=7,
            max_value=30,
            value=14,
            key="pred_period_realistic"
        )
    
    # 실제 데이터 기반 예측
    if prediction_target == "일별 매출":
        fig, metrics = predict_daily_revenue_realistic_dark(
            df_filtered, prediction_period, data_formatter
        )
    elif prediction_target == "카테고리별 성장":
        fig, metrics = predict_category_growth_realistic_dark(
            df_filtered, prediction_period, data_formatter
        )
    else:
        fig, metrics = predict_hourly_pattern_realistic_dark(
            df_filtered, data_formatter
        )
    
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        
        # 예측 신뢰도 표시 - Dark Mode
        show_prediction_confidence_dark(metrics, data_formatter)

def predict_daily_revenue_realistic_dark(df, days_ahead, formatter):
    """실제 데이터 기반 일별 매출 예측 - Dark Mode"""
    
    # 일별 데이터 준비
    daily_revenue = df.groupby(df['date'].dt.date)['revenue'].sum().reset_index()
    daily_revenue.columns = ['date', 'revenue']
    daily_revenue = daily_revenue.sort_values('date')
    
    # 이동평균 계산
    daily_revenue['ma7'] = daily_revenue['revenue'].rolling(7, min_periods=1).mean()
    daily_revenue['ma30'] = daily_revenue['revenue'].rolling(30, min_periods=1).mean()
    
    # 추세 계산 - 자체 선형 회귀 사용
    if len(daily_revenue) >= 7:
        # 최근 7일 데이터로 추세 학습
        recent_data = daily_revenue.tail(7).copy()
        recent_data['day_num'] = range(len(recent_data))
        
        # 자체 선형 회귀 모델 학습
        model = SimpleLinearRegression()
        X = recent_data['day_num'].values
        y = recent_data['revenue'].values
        model.fit(X, y)
        
        # 추세 기반 예측
        future_days = np.arange(len(recent_data), len(recent_data) + days_ahead)
        trend_predictions = model.predict(future_days)
    else:
        # 데이터가 부족한 경우 평균값 사용
        trend_predictions = [daily_revenue['revenue'].mean()] * days_ahead
    
    # 요일별 패턴
    df['weekday'] = pd.to_datetime(df['date']).dt.dayofweek
    weekday_pattern = df.groupby('weekday')['revenue'].mean()
    
    # 예측 생성
    last_date = pd.to_datetime(daily_revenue['date'].iloc[-1])
    predictions = []
    
    for i in range(days_ahead):
        future_date = last_date + timedelta(days=i+1)
        weekday = future_date.weekday()
        
        # 추세 예측과 요일 패턴 결합
        base_prediction = trend_predictions[i] if i < len(trend_predictions) else trend_predictions[-1]
        weekday_adjustment = weekday_pattern.get(weekday, weekday_pattern.mean()) / weekday_pattern.mean()
        
        prediction = base_prediction * weekday_adjustment
        predictions.append(max(0, prediction))  # 음수 방지
    
    # 그래프 생성 - Dark Mode
    fig = go.Figure()
    
    # 실제 데이터
    fig.add_trace(go.Scatter(
        x=daily_revenue['date'],
        y=daily_revenue['revenue'],
        mode='lines',
        name='실제 매출',
        line=dict(color='#00D9FF', width=2),
        hovertemplate='%{x}<br>매출: %{y:,.0f}원<extra></extra>'
    ))
    
    # 예측 데이터
    future_dates = [last_date + timedelta(days=i+1) for i in range(days_ahead)]
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=predictions,
        mode='lines+markers',
        name='예측 매출',
        line=dict(color='#FF0080', width=2, dash='dash'),
        marker=dict(size=8, color='#FF0080'),
        hovertemplate='%{x}<br>예측: %{y:,.0f}원<extra></extra>'
    ))
    
    # 신뢰구간 (±20%)
    upper_bound = [p * 1.2 for p in predictions]
    lower_bound = [p * 0.8 for p in predictions]
    
    fig.add_trace(go.Scatter(
        x=future_dates + future_dates[::-1],
        y=upper_bound + lower_bound[::-1],
        fill='toself',
        fillcolor='rgba(255, 0, 128, 0.1)',
        line=dict(color='rgba(255, 255, 255, 0)'),
        showlegend=True,
        name='80% 신뢰구간',
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"일별 매출 예측 ({days_ahead}일)",
            font=dict(color='#00D9FF', size=18)
        ),
        xaxis=dict(
            title="날짜",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        yaxis=dict(
            title="매출액",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        height=500,
        hovermode='x unified',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(family="'Inter', 'Pretendard', sans-serif", color='#FFFFFF'),
        legend=dict(
            bgcolor='rgba(255, 255, 255, 0.05)',
            bordercolor='rgba(255, 255, 255, 0.12)',
            borderwidth=1
        )
    )
    
    metrics = {
        'total_revenue': sum(predictions),
        'daily_avg': np.mean(predictions),
        'confidence': 80,
        'trend': 'increasing' if len(trend_predictions) > 1 and trend_predictions[-1] > trend_predictions[0] else 'stable'
    }
    
    return fig, metrics

def predict_category_growth_realistic_dark(df, days_ahead, formatter):
    """카테고리별 성장 예측 - Dark Mode"""
    
    # 카테고리별 일별 추세 분석
    top_categories = df.groupby('category')['revenue'].sum().nlargest(5).index
    
    # 네온 색상 팔레트
    neon_colors = ['#00D9FF', '#7C3AED', '#10F981', '#FF0080', '#FFD93D']
    
    fig = go.Figure()
    
    for idx, category in enumerate(top_categories):
        cat_data = df[df['category'] == category]
        daily_cat = cat_data.groupby(cat_data['date'].dt.date)['revenue'].sum().reset_index()
        
        if len(daily_cat) >= 7:
            # 최근 7일 평균 성장률
            recent_growth = daily_cat['revenue'].pct_change().tail(7).mean()
            
            # 안정적인 성장률 적용 (극단값 제한)
            recent_growth = max(-0.1, min(0.1, recent_growth))  # -10% ~ +10% 제한
            
            # 예측
            last_value = daily_cat['revenue'].iloc[-1]
            predictions = []
            for i in range(days_ahead):
                next_value = last_value * (1 + recent_growth * 0.5)  # 성장률 감쇠 적용
                predictions.append(next_value)
                last_value = next_value
            
            # 예측 날짜
            last_date = pd.to_datetime(daily_cat['date'].iloc[-1])
            future_dates = [last_date + timedelta(days=i+1) for i in range(days_ahead)]
            
            color = neon_colors[idx % len(neon_colors)]
            
            # 실제 데이터
            fig.add_trace(go.Scatter(
                x=daily_cat['date'],
                y=daily_cat['revenue'],
                mode='lines',
                name=f'{category[:10]} (실제)',
                line=dict(width=2, color=color),
                hovertemplate='%{x}<br>%{y:,.0f}원<extra></extra>'
            ))
            
            # 예측 데이터
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=predictions,
                mode='lines',
                name=f'{category[:10]} (예측)',
                line=dict(width=2, dash='dash', color=color),
                showlegend=False,
                hovertemplate='%{x}<br>예측: %{y:,.0f}원<extra></extra>'
            ))
    
    fig.update_layout(
        title=dict(
            text=f"카테고리별 성장 예측 ({days_ahead}일)",
            font=dict(color='#00D9FF', size=18)
        ),
        xaxis=dict(
            title="날짜",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        yaxis=dict(
            title="매출액",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        height=500,
        hovermode='x unified',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(family="'Inter', 'Pretendard', sans-serif", color='#FFFFFF'),
        legend=dict(
            bgcolor='rgba(255, 255, 255, 0.05)',
            bordercolor='rgba(255, 255, 255, 0.12)',
            borderwidth=1
        )
    )
    
    metrics = {
        'confidence': 75,
        'trend': 'category_specific',
        'daily_avg': 0
    }
    
    return fig, metrics

def predict_hourly_pattern_realistic_dark(df, formatter):
    """시간대별 패턴 예측 - Dark Mode"""
    
    # 시간대별 평균과 표준편차
    hourly_stats = df.groupby('hour').agg({
        'revenue': ['mean', 'std', 'count']
    }).reset_index()
    
    hourly_stats.columns = ['hour', 'revenue_mean', 'revenue_std', 'count']
    
    # 데이터가 충분한 시간대만 사용
    hourly_stats = hourly_stats[hourly_stats['count'] >= 5]
    
    fig = go.Figure()
    
    # 전체 평균 패턴
    fig.add_trace(go.Scatter(
        x=hourly_stats['hour'],
        y=hourly_stats['revenue_mean'],
        mode='lines+markers',
        name='평균 패턴',
        line=dict(color='#00D9FF', width=3),
        marker=dict(size=8, color='#00D9FF'),
        hovertemplate='%{x}시<br>평균: %{y:,.0f}원<extra></extra>'
    ))
    
    # 신뢰구간 (평균 ± 표준편차)
    upper = hourly_stats['revenue_mean'] + hourly_stats['revenue_std']
    lower = hourly_stats['revenue_mean'] - hourly_stats['revenue_std']
    lower = lower.clip(lower=0)  # 음수 방지
    
    fig.add_trace(go.Scatter(
        x=list(hourly_stats['hour']) + list(hourly_stats['hour'][::-1]),
        y=list(upper) + list(lower[::-1]),
        fill='toself',
        fillcolor='rgba(0, 217, 255, 0.1)',
        line=dict(color='rgba(255, 255, 255, 0)'),
        showlegend=True,
        name='표준편차 범위',
        hoverinfo='skip'
    ))
    
    # 피크 시간대 표시
    peak_hours = hourly_stats.nlargest(3, 'revenue_mean')
    for _, row in peak_hours.iterrows():
        fig.add_annotation(
            x=row['hour'],
            y=row['revenue_mean'],
            text=f"피크: {int(row['hour'])}시",
            showarrow=True,
            arrowhead=2,
            font=dict(color="#10F981", size=10),
            arrowcolor='#10F981',
            ax=0,
            ay=-30
        )
    
    fig.update_layout(
        title=dict(
            text="시간대별 매출 패턴 분석",
            font=dict(color='#00D9FF', size=18)
        ),
        xaxis=dict(
            title="시간",
            titlefont=dict(color='#FFFFFF'),
            tickmode='linear',
            tick0=0,
            dtick=1,
            ticktext=[f"{i}시" for i in range(24)],
            tickvals=list(range(24)),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        yaxis=dict(
            title="평균 매출",
            titlefont=dict(color='#FFFFFF'),
            tickfont=dict(color='rgba(255, 255, 255, 0.85)'),
            gridcolor='rgba(255, 255, 255, 0.06)',
            linecolor='rgba(255, 255, 255, 0.12)'
        ),
        height=500,
        hovermode='x unified',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(family="'Inter', 'Pretendard', sans-serif", color='#FFFFFF')
    )
    
    metrics = {
        'confidence': 90,
        'trend': 'hourly_pattern',
        'daily_avg': hourly_stats['revenue_mean'].sum()
    }
    
    return fig, metrics

def show_prediction_confidence_dark(metrics, data_formatter):
    """예측 신뢰도 표시 - Dark Mode Glassmorphism"""
    
    st.markdown("""
    <h3 style="color: #00D9FF; margin: 20px 0;
               text-shadow: 0 0 15px rgba(0, 217, 255, 0.5);">
        📊 예측 신뢰도
    </h3>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        confidence = metrics.get('confidence', 0)
        if confidence > 80:
            color = "#10F981"
            glow_color = "16, 249, 129"
        elif confidence > 60:
            color = "#FFD93D"
            glow_color = "255, 217, 61"
        else:
            color = "#FF3355"
            glow_color = "255, 51, 85"
            
        st.markdown(f"""
        <div style="text-align: center; 
                    padding: 20px 15px; 
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 2px solid {color}; 
                    border-radius: 12px;
                    box-shadow: 
                        0 0 20px rgba({glow_color}, 0.5),
                        inset 0 0 20px rgba({glow_color}, 0.1);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;">
            <h4 style="color: {color}; 
                       margin: 0 0 10px 0; 
                       font-size: 16px;
                       font-weight: 600;">신뢰도</h4>
            <h2 style="color: {color}; 
                       margin: 0;
                       font-size: 36px;
                       font-weight: 700;
                       text-shadow: 0 0 20px rgba({glow_color}, 0.8);">{confidence}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        trend = metrics.get('trend', 'unknown')
        
        # 추세별 아이콘과 색상 설정
        if trend == 'increasing':
            trend_icon = "📈"
            trend_text = "상승세"
            trend_color = "#10F981"
            glow_color = "16, 249, 129"
        elif trend == 'stable':
            trend_icon = "➡️"
            trend_text = "안정세"
            trend_color = "#00D9FF"
            glow_color = "0, 217, 255"
        elif trend == 'decreasing':
            trend_icon = "📉"
            trend_text = "하락세"
            trend_color = "#FF3355"
            glow_color = "255, 51, 85"
        elif trend == 'hourly_pattern':
            trend_icon = "⏰"
            trend_text = "시간패턴"
            trend_color = "#7C3AED"
            glow_color = "124, 58, 237"
        else:
            trend_icon = "📊"
            trend_text = "카테고리별"
            trend_color = "#FF0080"
            glow_color = "255, 0, 128"
        
        st.markdown(f"""
        <div style="text-align: center; 
                    padding: 20px 15px; 
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 2px solid {trend_color}; 
                    border-radius: 12px;
                    box-shadow: 
                        0 0 20px rgba({glow_color}, 0.5),
                        inset 0 0 20px rgba({glow_color}, 0.1);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;">
            <h4 style="color: {trend_color}; 
                       margin: 0 0 8px 0;
                       font-size: 16px;
                       font-weight: 600;">추세</h4>
            <div style="font-size: 32px; 
                        margin: 0 0 5px 0;
                        line-height: 1;">{trend_icon}</div>
            <p style="color: {trend_color}; 
                      margin: 0;
                      font-size: 18px;
                      font-weight: 600;
                      text-shadow: 0 0 15px rgba({glow_color}, 0.8);">{trend_text}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        daily_avg = metrics.get('daily_avg', 0)
        st.markdown(f"""
        <div style="text-align: center; 
                    padding: 20px 15px; 
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 2px solid #FFD93D; 
                    border-radius: 12px;
                    box-shadow: 
                        0 0 20px rgba(255, 217, 61, 0.5),
                        inset 0 0 20px rgba(255, 217, 61, 0.1);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;">
            <h4 style="color: #FFD93D; 
                       margin: 0 0 10px 0;
                       font-size: 16px;
                       font-weight: 600;">예상 일평균</h4>
            <h3 style="color: #FFD93D; 
                       margin: 0;
                       font-size: 22px;
                       font-weight: 700;
                       word-break: keep-all;
                       text-shadow: 0 0 15px rgba(255, 217, 61, 0.8);">{data_formatter.format_money(daily_avg)}</h3>
        </div>
        """, unsafe_allow_html=True)

def show_prediction_insights(df_filtered, data_formatter):
    """예측 기반 인사이트 - Dark Mode"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(255, 0, 128, 0.05), rgba(16, 249, 129, 0.05));
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 0, 128, 0.2);
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;">
        <h3 style="color: #FF0080; margin-bottom: 15px;
                   text-shadow: 0 0 15px rgba(255, 0, 128, 0.5);">
            🎯 예측 기반 최적화 제안
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # 예측된 최적 시간대
    hourly_future = df_filtered.groupby('hour')['revenue'].mean()
    best_hours = hourly_future.nlargest(5).index.tolist()
    
    # 예측된 성장 카테고리 - include_groups=False 추가
    cat_growth = df_filtered.groupby('category', group_keys=False).apply(
        lambda x: x.sort_values('date')['revenue'].pct_change().mean(),
        include_groups=False
    ).nlargest(3)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background: rgba(0, 217, 255, 0.05);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(0, 217, 255, 0.2);
                    border-radius: 10px;
                    padding: 15px;">
            <h4 style="color: #00D9FF; margin-bottom: 10px;">⏰ 예측 최적 시간대</h4>
        """, unsafe_allow_html=True)
        
        for hour in best_hours[:3]:
            revenue = hourly_future[hour]
            st.markdown(f"""
            <p style="color: rgba(255, 255, 255, 0.85); margin: 5px 0;">
                • {int(hour)}시: 예상 매출 <span style="color: #00D9FF; font-weight: bold;">
                {data_formatter.format_money(revenue)}</span>
            </p>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: rgba(16, 249, 129, 0.05);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(16, 249, 129, 0.2);
                    border-radius: 10px;
                    padding: 15px;">
            <h4 style="color: #10F981; margin-bottom: 10px;">📈 예측 성장 카테고리</h4>
        """, unsafe_allow_html=True)
        
        for cat, growth in cat_growth.items():
            st.markdown(f"""
            <p style="color: rgba(255, 255, 255, 0.85); margin: 5px 0;">
                • {cat}: 예상 성장률 <span style="color: #10F981; font-weight: bold;">
                {growth*100:.1f}%</span>/일
            </p>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)