"""
dashboard_trend_tab.py - 추세분석 탭 UI
Version: 1.1.0
Created: 2025-01-25
Updated: 2025-09-12 - 에러 핸들링 강화 및 타입 안정성 개선

홈쇼핑 매출 추세분석 탭 구현
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

# 추세분석 모듈 import
try:
    from dashboard_trend_calculator import TrendCalculator
    from dashboard_trend_visuals import TrendVisualizer
    from dashboard_trend_pipeline import TrendDataPipeline
except ImportError as e:
    st.error(f"추세분석 모듈 로드 실패: {e}")
    st.stop()

def get_category_insight(stat):
    """카테고리별 인사이트 생성"""
    insights = []
    
    if stat['growth_rate'] > 20:
        insights.append("급격한 성장세")
    elif stat['growth_rate'] > 5:
        insights.append("꾸준한 상승 추세")
    elif stat['growth_rate'] < -20:
        insights.append("급격한 하락세")
    elif stat['growth_rate'] < -5:
        insights.append("하락 추세 주의")
    else:
        insights.append("안정적 유지")
    
    if stat['volatility'] < 30:
        insights.append("일관된 방송 패턴")
    elif stat['volatility'] > 60:
        insights.append("불규칙한 방송 패턴")
    
    if stat['avg_daily'] > 10:
        insights.append("고빈도 방송")
    elif stat['avg_daily'] < 3:
        insights.append("저빈도 방송")
    
    return " / ".join(insights)

def create_trend_analysis_tab(df_filtered, chart_generator, data_formatter, colors):
    """
    추세분석 탭 메인 함수
    
    Parameters:
    -----------
    df_filtered : DataFrame
        필터링된 데이터
    chart_generator : ChartGenerator
        차트 생성기 (기존 시스템)
    data_formatter : DataFormatter
        데이터 포맷터 (기존 시스템)
    colors : dict
        색상 테마
    """
    
    # Session state 초기화
    if 'trend_analysis_started' not in st.session_state:
        st.session_state.trend_analysis_started = False
    if 'trend_filters' not in st.session_state:
        st.session_state.trend_filters = {}
    
    # 스타일 적용
    st.markdown("""
    <style>
    .trend-header {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1));
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 30px;
        border: 1px solid rgba(0, 217, 255, 0.3);
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 15px;
        border: 1px solid rgba(0, 217, 255, 0.2);
        height: 100%;
    }
    .insight-box {
        background: linear-gradient(135deg, rgba(16, 249, 129, 0.1), rgba(0, 217, 255, 0.1));
        border-left: 4px solid #10F981;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
    }
    .warning-box {
        background: linear-gradient(135deg, rgba(255, 0, 128, 0.1), rgba(255, 107, 107, 0.1));
        border-left: 4px solid #FF0080;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 헤더 섹션
    st.markdown('<div class="trend-header">', unsafe_allow_html=True)
    st.markdown('# 📊 매출 추세 분석 대시보드')
    st.markdown('실시간 매출 추세 모니터링 및 예측 분석 시스템')
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ==================== 필터 섹션 ====================
    st.markdown("### 🎯 분석 조건 설정")
    
    filter_cols = st.columns([2, 2, 2, 2, 1])
    
    with filter_cols[0]:
        period_type = st.selectbox(
            "📅 기간 단위",
            ["일별", "주별", "월별"],
            index=0,  # 일별이 기본값
            help="분석할 시간 단위를 선택하세요"
        )
    
    with filter_cols[1]:
        comparison_type = st.selectbox(
            "📊 비교 기준",
            ["전일 대비", "전주 대비", "전월 대비"],
            index=0,  # 전일대비가 기본값
            help="비교 기준 기간을 선택하세요"
        )
    
    with filter_cols[2]:
        ma_period = st.selectbox(
            "📈 이동평균",
            ["7일", "14일", "30일"],
            index=0,  # 7일이 기본값
            help="이동평균 기간을 선택하세요"
        )
    
    with filter_cols[3]:
        categories = df_filtered['category'].unique().tolist()
        selected_categories = st.multiselect(
            "📦 카테고리",
            categories,
            default=categories,  # 전체 선택이 기본값
            help="분석할 카테고리를 선택하세요"
        )
    
    with filter_cols[4]:
        show_forecast = st.checkbox(
            "🔮 예측",
            value=False,
            help="미래 예측 표시"
        )
    
    # 분석 시작/재설정 버튼
    st.markdown("---")
    col1, col2 = st.columns([5, 1])
    with col1:
        if st.button(
            "🚀 **분석 시작**",
            use_container_width=True,
            type="primary",
            help="설정한 조건으로 추세 분석을 시작합니다"
        ):
            st.session_state.trend_analysis_started = True
            st.session_state.trend_filters = {
                'period_type': period_type,
                'comparison_type': comparison_type,
                'ma_period': ma_period,
                'selected_categories': selected_categories,
                'show_forecast': show_forecast
            }
    
    with col2:
        if st.button("🔄 재설정", use_container_width=True):
            st.session_state.trend_analysis_started = False
            st.session_state.trend_filters = {}
            st.rerun()
    
    # 분석 시작 버튼이 눌린 경우에만 분석 수행
    if not st.session_state.trend_analysis_started:
        st.info("📊 필터를 설정하고 '분석 시작' 버튼을 클릭하세요.")
        return
    
    # Session state에서 필터 값 가져오기
    period_type = st.session_state.trend_filters['period_type']
    comparison_type = st.session_state.trend_filters['comparison_type']
    ma_period = st.session_state.trend_filters['ma_period']
    selected_categories = st.session_state.trend_filters['selected_categories']
    show_forecast = st.session_state.trend_filters['show_forecast']
    
    st.markdown("---")
    
    # ==================== 데이터 처리 (에러 핸들링 강화) ====================
    try:
        # 필터 적용
        if selected_categories:
            df_trend = df_filtered[df_filtered['category'].isin(selected_categories)].copy()
        else:
            df_trend = df_filtered.copy()
        
        # 데이터가 없는 경우
        if df_trend.empty:
            st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
            return
        
        # 날짜 형식 변환
        df_trend['date'] = pd.to_datetime(df_trend['date'], errors='coerce')
        
        # 오늘 날짜 제외 (어제까지만 포함)
        today = pd.Timestamp.now().normalize()
        df_trend = df_trend[df_trend['date'] < today]
        
        # 데이터가 없는 경우 체크
        if df_trend.empty:
            st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
            return
        
        # 데이터 타입 검증 및 변환
        numeric_columns = ['revenue', 'units_sold', 'roi_calculated', 'cost', 'total_cost']
        for col in numeric_columns:
            if col in df_trend.columns:
                # 타입 검증 - 강제로 float로 변환하여 에러 방지
                df_trend[col] = pd.to_numeric(df_trend[col], errors='coerce').fillna(0).astype(float)
                
                # 음수 값 제거 (revenue만)
                if col == 'revenue':
                    df_trend = df_trend[df_trend[col] >= 0]
        
        # broadcast 컬럼 추가 (집계용)
        df_trend['broadcast'] = 1  # 각 행을 1개의 방송으로 간주
        
        # 추세 계산기 초기화
        calculator = TrendCalculator()
        
        # 기간별 집계
        if period_type == "일별":
            df_agg = df_trend.groupby('date').agg({
                'revenue': 'sum',
                'units_sold': 'sum',
                'roi_calculated': 'mean',
                'broadcast': 'count'
            }).reset_index()
        elif period_type == "주별":
            df_trend['week'] = df_trend['date'].dt.to_period('W')
            df_agg = df_trend.groupby('week').agg({
                'revenue': 'sum',
                'units_sold': 'sum',
                'roi_calculated': 'mean',
                'broadcast': 'count'
            }).reset_index()
            df_agg['date'] = df_agg['week'].dt.start_time
        else:  # 월별
            df_trend['month'] = df_trend['date'].dt.to_period('M')
            df_agg = df_trend.groupby('month').agg({
                'revenue': 'sum',
                'units_sold': 'sum',
                'roi_calculated': 'mean',
                'broadcast': 'count'
            }).reset_index()
            df_agg['date'] = df_agg['month'].dt.start_time
        
        # 집계 후 모든 숫자 컬럼 타입 강제 변환
        numeric_cols_agg = ['revenue', 'units_sold', 'roi_calculated', 'broadcast']
        for col in numeric_cols_agg:
            if col in df_agg.columns:
                df_agg[col] = pd.to_numeric(df_agg[col], errors='coerce').fillna(0).astype(float)
        
        # cost 컬럼 추가 (필요한 경우)
        if 'cost' not in df_agg.columns:
            # 간단한 cost 계산 (revenue의 일정 비율로 가정)
            df_agg['cost'] = df_agg['revenue'] * 0.7  # 예시: 매출의 70%를 비용으로 가정
        else:
            df_agg['cost'] = pd.to_numeric(df_agg['cost'], errors='coerce').fillna(0).astype(float)
        
        # 모든 컬럼 타입 최종 확인 (디버그용)
        for col in df_agg.columns:
            if df_agg[col].dtype == 'object':
                # date 관련 컬럼이 아닌 경우 경고
                if col not in ['date', 'week', 'month', 'category']:
                    print(f"⚠️ Warning: Column '{col}' has object dtype: {df_agg[col].dtype}")
                    # 숫자로 변환 시도
                    try:
                        df_agg[col] = pd.to_numeric(df_agg[col], errors='coerce').fillna(0).astype(float)
                    except:
                        pass
        
        # 추세 지표 계산 (안전한 계산)
        try:
            df_agg = calculator.calculate_growth_rates(df_agg)
        except Exception as e:
            st.warning(f"성장률 계산 스킵: {e}")
            # 기본값 설정
            df_agg['revenue_dod'] = 0
            
        try:
            df_agg = calculator.calculate_moving_averages(df_agg)
        except Exception as e:
            st.warning(f"이동평균 계산 스킵: {e}")
            # 기본값 설정
            df_agg['ma_7'] = df_agg['revenue']
            
        try:
            df_agg = calculator.calculate_volatility(df_agg)
        except Exception as e:
            st.warning(f"변동성 계산 스킵: {e}")
            # 기본값 설정
            df_agg['cv_7'] = 0
            df_agg['cv_30'] = 0
            
        try:
            # 추세 방향 계산 전 최종 타입 확인
            for col in ['revenue', 'units_sold', 'cost']:
                if col in df_agg.columns:
                    df_agg[col] = df_agg[col].astype(float)
            
            # 디버그 정보
            if st.session_state.get('debug_mode', False):
                st.write("df_agg dtypes before trend detection:")
                st.write(df_agg.dtypes)
            
            df_agg = calculator.detect_trend_direction(df_agg)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            st.warning(f"추세 방향 계산 스킵: {str(e)[:100]}")
            if st.session_state.get('debug_mode', False):
                st.code(error_detail)
            # 기본값 설정
            df_agg['trend_direction_7'] = 'stable'
            df_agg['trend_direction_30'] = 'stable'
            
        try:
            df_agg = calculator.detect_anomalies(df_agg)
        except Exception as e:
            st.warning(f"이상치 감지 스킵: {e}")
            # 기본값 설정
            df_agg['is_anomaly'] = 0
        
    except ValueError as ve:
        st.error(f"데이터 검증 실패: {ve}")
        st.info("💡 해결 방법: 데이터베이스 무결성 검사를 실행하거나 관리자에게 문의하세요.")
        
        # 자동 복구 시도 버튼
        if st.button("🔧 자동 데이터 복구 시도"):
            with st.spinner("데이터 복구 중..."):
                try:
                    from fix_data_types import fix_data_types
                    if fix_data_types():
                        st.success("✅ 데이터 복구 완료! 페이지를 새로고침 해주세요.")
                        st.rerun()
                    else:
                        st.error("자동 복구 실패. 관리자에게 문의하세요.")
                except Exception as fix_error:
                    st.error(f"복구 모듈 실행 실패: {fix_error}")
        return
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # 특정 에러 유형 처리
        if 'must be real number' in error_msg or 'not str' in error_msg:
            st.error("📊 데이터 타입 오류가 감지되었습니다.")
            st.warning("""
            **발생 원인:**
            - 데이터베이스의 숫자 컬럼에 문자열 값이 포함되어 있습니다.
            - cost, roi 등의 컬럼 타입이 일치하지 않습니다.
            
            **해결 방법:**
            1. 아래 '자동 복구' 버튼을 클릭하세요.
            2. 문제가 지속되면 관리자에게 문의하세요.
            """)
            
            # 자동 복구 버튼
            if st.button("🔧 자동 복구 시도", key="auto_fix"):
                with st.spinner("데이터 타입 복구 중..."):
                    try:
                        # 간단한 복구 시도
                        df_trend_fixed = df_filtered.copy()
                        for col in ['revenue', 'cost', 'units_sold']:
                            if col in df_trend_fixed.columns:
                                df_trend_fixed[col] = pd.to_numeric(df_trend_fixed[col], errors='coerce').fillna(0)
                        
                        st.success("✅ 임시 복구 완료! 다시 시도하세요.")
                        st.experimental_set_query_params(fixed="true")
                        st.rerun()
                    except Exception as fix_e:
                        st.error(f"복구 실패: {fix_e}")
        else:
            st.error(f"데이터 처리 중 오류가 발생했습니다.")
            
        # 디버그 정보 표시
        if st.session_state.get('debug_mode', False):
            st.error(f"에러 상세: {str(e)}")
            with st.expander("🔍 상세 디버그 정보"):
                st.code(traceback.format_exc())
                st.write("데이터 타입 정보:")
                if 'df_trend' in locals():
                    st.write(df_trend.dtypes)
        return
    
    # ==================== 핵심 지표 카드 ====================
    st.markdown("### 📈 핵심 성과 지표")
    
    metric_cols = st.columns(5)
    
    # 최근 매출
    latest_revenue = df_agg['revenue'].iloc[-1] if not df_agg.empty else 0
    prev_revenue = df_agg['revenue'].iloc[-2] if len(df_agg) > 1 else latest_revenue
    revenue_change = ((latest_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    
    with metric_cols[0]:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="최근 매출",
            value=f"{latest_revenue/1e8:.1f}억",
            delta=f"{revenue_change:+.1f}%",
            delta_color="normal"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 평균 성장률
    avg_growth = df_agg['revenue_dod'].mean() if 'revenue_dod' in df_agg.columns else 0
    
    with metric_cols[1]:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="평균 성장률",
            value=f"{avg_growth:.1f}%",
            delta="일별 평균",
            delta_color="off"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 추세 방향
    if 'trend_direction_7' in df_agg.columns:
        recent_trend = df_agg['trend_direction_7'].iloc[-1] if not pd.isna(df_agg['trend_direction_7'].iloc[-1]) else 'stable'
    else:
        recent_trend = 'stable'
    
    trend_emoji = {'up': '📈', 'down': '📉', 'stable': '➡️'}
    trend_text = {'up': '상승', 'down': '하락', 'stable': '보합'}
    
    with metric_cols[2]:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="추세 방향",
            value=f"{trend_emoji.get(recent_trend, '➡️')} {trend_text.get(recent_trend, '보합')}",
            delta="7일 기준",
            delta_color="off"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 변동성
    recent_volatility = df_agg['cv_30'].iloc[-1] if 'cv_30' in df_agg.columns and not pd.isna(df_agg['cv_30'].iloc[-1]) else 0
    volatility_level = "높음" if recent_volatility > 0.3 else "보통" if recent_volatility > 0.15 else "낮음"
    
    with metric_cols[3]:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="변동성",
            value=f"{recent_volatility:.2f}",
            delta=volatility_level,
            delta_color="inverse" if recent_volatility > 0.3 else "off"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 이상치 감지
    anomaly_count = df_agg['is_anomaly'].sum() if 'is_anomaly' in df_agg.columns else 0
    
    with metric_cols[4]:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="이상치",
            value=f"{anomaly_count}건",
            delta="감지됨" if anomaly_count > 0 else "정상",
            delta_color="inverse" if anomaly_count > 0 else "off"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== 메인 차트 섹션 ====================
    st.markdown("### 📊 매출 추세 시각화")
    
    try:
        # 메인 매출 추세 차트 생성
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # 서브플롯 생성 (2행 1열)
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=('매출 추세', '변동계수 (CV)')
        )
        
        # 1. 매출 추세 라인
        fig.add_trace(
            go.Scatter(
                x=df_agg['date'],
                y=df_agg['revenue'],
                mode='lines',
                name='일별 매출',
                line=dict(color='#00D9FF', width=2),
                hovertemplate='날짜: %{x}<br>매출: %{y:,.0f}원<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 이동평균 추가
        if 'ma_7' in df_agg.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_agg['date'],
                    y=df_agg['ma_7'],
                    mode='lines',
                    name='7일 이동평균',
                    line=dict(color='#10F981', width=2, dash='dash'),
                    hovertemplate='날짜: %{x}<br>7일 평균: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 2. 변동계수 막대 그래프
        if 'cv_7' in df_agg.columns:
            # 변동계수 색상 설정 (값에 따라 다른 색상)
            cv_colors = ['#10F981' if cv < 0.2 else '#FFD93D' if cv < 0.3 else '#FF0080' 
                        for cv in df_agg['cv_7'].fillna(0)]
            
            fig.add_trace(
                go.Bar(
                    x=df_agg['date'],
                    y=df_agg['cv_7'],
                    name='변동계수',
                    marker_color=cv_colors,
                    hovertemplate='날짜: %{x}<br>변동계수: %{y:.2f}<extra></extra>'
                ),
                row=2, col=1
            )
        
        # 레이아웃 업데이트
        fig.update_xaxes(title_text="날짜", row=2, col=1)
        fig.update_yaxes(
            title_text="매출액", 
            row=1, col=1,
            tickformat=',.0f',
            showticklabels=True,
            tickmode='auto'
        )
        fig.update_yaxes(
            title_text="CV",
            row=2, col=1,
            tickformat='.2f'
        )
        
        fig.update_layout(
            height=660,  # 10% 증가 (600 -> 660)
            showlegend=True,
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
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
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"차트 생성 중 오류: {e}")
        if st.session_state.get('debug_mode', False):
            st.code(traceback.format_exc())
    
    # ==================== 카테고리 분석 섹션 ====================
    st.markdown("### 📦 카테고리별 추세 분석")
    
    try:
        # 카테고리별 일별 방송 횟수 계산 (오늘 제외, 어제까지)
        df_category = df_trend.copy()
        
        # 타입 변환 보장
        df_category['date'] = pd.to_datetime(df_category['date'], errors='coerce')
        
        # 사이드바에서 선택한 기간 사용
        start_date = st.session_state.get('start_date', df_category['date'].min())
        end_date = st.session_state.get('end_date', df_category['date'].max())
        
        # 날짜 타입 변환
        if not isinstance(start_date, pd.Timestamp):
            start_date = pd.Timestamp(start_date)
        if not isinstance(end_date, pd.Timestamp):
            end_date = pd.Timestamp(end_date)
        
        # 오늘 날짜는 제외
        today = df_category['date'].max()
        if end_date >= today:
            end_date = today - pd.Timedelta(days=1)
        
        # 선택된 기간으로 필터링
        df_category = df_category[(df_category['date'] >= start_date) & 
                                 (df_category['date'] <= end_date)]
        
        # 일별 카테고리별 방송 횟수 집계
        df_category_daily = df_category.groupby(['date', 'category']).size().reset_index(name='broadcast_count')
        
        # 통일된 카테고리 색상
        category_colors = {
            '가구/인테리어': '#808080',    # 회색
            '디지털/가전': '#0000FF',      # 파랑
            '생활용품': '#00FF00',         # 연두
            '건강식품': '#00FF00',         # 연두
            '식품': '#FFFF00',             # 노랑
            '여가생활편의': '#87CEEB',     # 하늘색
            '패션/의류': '#FFB6C1',        # 연분홍
            '패션잡화': '#FF69B4',         # 진한분홍
            '화장품/미용': '#FF0000',      # 적색
            '스포츠/레저': '#FFA500',      # 주황
            '주방용품': '#9370DB',         # 보라
            '유아용품': '#98FB98',         # 연한 초록
            '도서/문구': '#DDA0DD',        # 연보라
            '반려동물': '#F0E68C',         # 카키
            '자동차용품': '#4682B4',       # 스틸 블루
        }
        
        if not df_category_daily.empty:
            # 카테고리별 일별 방송 횟수 라인 그래프 생성
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            # 각 카테고리별로 라인 추가
            for idx, category in enumerate(df_category_daily['category'].unique()):
                cat_data = df_category_daily[df_category_daily['category'] == category]
                cat_data = cat_data.sort_values('date')
                
                # 색상 설정
                if category in category_colors:
                    color = category_colors[category]
                else:
                    backup_colors = ['#3498DB', '#9B59B6', '#2ECC71', '#F39C12', '#E74C3C']
                    color = backup_colors[idx % len(backup_colors)]
                
                # 일별 방송 횟수 라인 그래프
                fig.add_trace(go.Scatter(
                    x=cat_data['date'],
                    y=cat_data['broadcast_count'],
                    mode='lines+markers',
                    name=category,
                    line=dict(width=2, color=color),
                    marker=dict(size=6, color=color),
                    hovertemplate="<b>%{text}</b><br>" +
                                 "날짜: %{x}<br>" +
                                 "방송횟수: %{y}회<br>" +
                                 "<extra></extra>",
                    text=[category] * len(cat_data)
                ))
            
            # 기간 계산
            days_count = (end_date - start_date).days + 1
            
            fig.update_layout(
                title=f"카테고리별 일별 방송 횟수 추이 ({days_count}일간)",
                xaxis_title="날짜",
                yaxis_title="방송 횟수",
                height=552,  # 20% 증가 (460 -> 552)
                width=None,
                paper_bgcolor='rgba(0, 0, 0, 0)',
                plot_bgcolor='rgba(255, 255, 255, 0.02)',
                font=dict(color='#FFFFFF'),
                xaxis=dict(tickangle=-45),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("카테고리별 데이터가 부족합니다.")
            
    except Exception as e:
        st.error(f"카테고리 분석 중 오류: {e}")

    
    # ==================== 카테고리별 매출 추세 시각화 ====================
    st.markdown("### 📊 카테고리별 일별 매출 추세")
    
    try:
        # 카테고리별 일별 매출 추세 그래프 생성
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # 카테고리별로 그룹화
        category_list = df_trend['category'].unique()[:15]  # 최대 15개 카테고리
        
        fig = go.Figure()
        
        # 카테고리별 색상 설정 (통일된 색상)
        category_colors = {
            '가구/인테리어': '#808080',    # 회색
            '디지털/가전': '#0000FF',      # 파랑
            '생활용품': '#00FF00',         # 연두
            '건강식품': '#00FF00',         # 연두
            '식품': '#FFFF00',             # 노랑
            '여가생활편의': '#87CEEB',     # 하늘색
            '패션/의류': '#FFB6C1',        # 연분홍
            '패션잡화': '#FF69B4',         # 진한분홍
            '화장품/미용': '#FF0000',      # 적색
            '스포츠/레저': '#FFA500',      # 주황
            '주방용품': '#9370DB',         # 보라
            '유아용품': '#98FB98',         # 연한 초록
            '도서/문구': '#DDA0DD',        # 연보라
            '반려동물': '#F0E68C',         # 카키
            '자동차용품': '#4682B4',       # 스틸 블루
        }
        
        # 카테고리별 일별 총 매출액 계산
        category_daily_totals = {}
        for category in category_list:
            cat_daily = df_trend[df_trend['category'] == category].groupby('date')['revenue'].sum().reset_index()
            cat_daily = cat_daily.sort_values('date')
            category_daily_totals[category] = cat_daily
        
        # 각 날짜별 카테고리 평균 계산 (그날의 카테고리 매출 합 / 카테고리 수)
        all_dates = pd.concat([df['date'] for df in category_daily_totals.values()]).unique()
        all_dates = pd.Series(all_dates).sort_values()
        
        daily_averages = []
        for date in all_dates:
            daily_sum = 0
            category_count = 0
            for cat_data in category_daily_totals.values():
                date_revenue = cat_data[cat_data['date'] == date]['revenue']
                if not date_revenue.empty:
                    daily_sum += date_revenue.values[0]
                    category_count += 1
            if category_count > 0:
                daily_averages.append(daily_sum / category_count)
            else:
                daily_averages.append(0)
        
        # 전체 평균선 추가 (점선)
        if daily_averages:
            fig.add_trace(go.Scatter(
                x=all_dates,
                y=daily_averages,
                mode='lines',
                name='일별 카테고리 평균',
                line=dict(color='#FFFFFF', width=2, dash='dot'),
                opacity=0.7,
                hovertemplate="<b>일별 카테고리 평균</b><br>날짜: %{x}<br>평균 매출: %{y:,.0f}<extra></extra>"
            ))
        
        # 카테고리별 일별 총 매출액 표시
        for idx, category in enumerate(category_list):
            cat_daily = category_daily_totals[category]
            
            # 이동평균 계산
            ma_days = int(ma_period.replace('일', ''))
            cat_daily[f'MA{ma_days}'] = cat_daily['revenue'].rolling(window=ma_days, min_periods=1).mean()
            
            # 색상 설정
            if category in category_colors:
                color = category_colors[category]
            else:
                # 백업 색상 리스트
                backup_colors = ['#3498DB', '#9B59B6', '#2ECC71', '#F39C12', '#E74C3C', 
                               '#1ABC9C', '#34495E', '#F1C40F', '#8E44AD', '#16A085']
                color = backup_colors[idx % len(backup_colors)]
            
            # 추세선 추가
            fig.add_trace(go.Scatter(
                x=cat_daily['date'],
                y=cat_daily[f'MA{ma_days}'],
                mode='lines',
                name=category,
                line=dict(width=2, color=color),
                hovertemplate=f"<b>{category}</b><br>날짜: %{{x}}<br>일별 매출: %{{y:,.0f}}<extra></extra>"
            ))
        
        fig.update_layout(
            title=f"카테고리별 일별 매출 추세 ({ma_period} 이동평균)",
            xaxis_title="날짜",
            yaxis_title="일별 매출액",
            height=550,  # 10% 증가 (500 -> 550)
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(255, 255, 255, 0.02)',
            font=dict(color='#FFFFFF'),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 카테고리별 추세 분석 그래프
        st.markdown("#### 📈 카테고리별 추세 변화율 분석")
        
        # 계산식 설명 추가
        with st.expander("📖 지표 계산 방법 및 의미"):
            st.markdown("""
            **변화율 계산식:**
            - 7일 변화율(%) = ((최근 7일 평균 - 이전 7일 평균) ÷ 이전 7일 평균) × 100
            - 14일 변화율(%) = ((최근 14일 평균 - 이전 14일 평균) ÷ 이전 14일 평균) × 100
            - 30일 변화율(%) = ((최근 30일 평균 - 이전 30일 평균) ÷ 이전 30일 평균) × 100
            - 45일 변화율(%) = ((최근 45일 평균 - 이전 45일 평균) ÷ 이전 45일 평균) × 100
            
            **의미 해석:**
            - **양수(+)**: 해당 기간 동안 매출이 증가 (상승 추세)
            - **음수(-)**: 해당 기간 동안 매출이 감소 (하락 추세)
            - **0에 가까움**: 매출이 비슷한 수준 유지 (보합)
            
            **활용 방법:**
            - 변화율 +10% 이상: 급성장 카테고리로 마케팅 집중
            - 변화율 -10% 이하: 원인 분석 및 개선 전략 필요
            - 변화율 ±5% 이내: 안정적 운영, 현재 전략 유지
            """)
        
        # 카테고리별 변화율 계산
        try:
            trend_data = []
            
            for category in category_list[:10]:  # 최대 10개 카테고리
                cat_data = df_trend[df_trend['category'] == category].groupby('date')['revenue'].sum().reset_index()
                cat_data = cat_data.sort_values('date')
                
                # 충분한 데이터가 있는 경우만 계산
                if len(cat_data) >= 90:
                    # 7일 변화율
                    recent_7 = cat_data.tail(7)['revenue'].mean()
                    prev_7 = cat_data.tail(14).head(7)['revenue'].mean()
                    change_7 = ((recent_7 - prev_7) / prev_7 * 100) if prev_7 > 0 else 0
                    
                    # 14일 변화율
                    recent_14 = cat_data.tail(14)['revenue'].mean()
                    prev_14 = cat_data.tail(28).head(14)['revenue'].mean()
                    change_14 = ((recent_14 - prev_14) / prev_14 * 100) if prev_14 > 0 else 0
                    
                    # 30일 변화율
                    recent_30 = cat_data.tail(30)['revenue'].mean()
                    prev_30 = cat_data.tail(60).head(30)['revenue'].mean()
                    change_30 = ((recent_30 - prev_30) / prev_30 * 100) if prev_30 > 0 else 0
                    
                    # 45일 변화율
                    recent_45 = cat_data.tail(45)['revenue'].mean()
                    prev_45 = cat_data.tail(90).head(45)['revenue'].mean()
                    change_45 = ((recent_45 - prev_45) / prev_45 * 100) if prev_45 > 0 else 0
                    
                    trend_data.append({
                        'category': category,
                        '7일 변화율': change_7,
                        '14일 변화율': change_14,
                        '30일 변화율': change_30,
                        '45일 변화율': change_45
                    })
                elif len(cat_data) >= 60:
                    # 7일, 14일, 30일만 계산
                    recent_7 = cat_data.tail(7)['revenue'].mean()
                    prev_7 = cat_data.tail(14).head(7)['revenue'].mean()
                    change_7 = ((recent_7 - prev_7) / prev_7 * 100) if prev_7 > 0 else 0
                    
                    recent_14 = cat_data.tail(14)['revenue'].mean()
                    prev_14 = cat_data.tail(28).head(14)['revenue'].mean()
                    change_14 = ((recent_14 - prev_14) / prev_14 * 100) if prev_14 > 0 else 0
                    
                    recent_30 = cat_data.tail(30)['revenue'].mean()
                    prev_30 = cat_data.tail(60).head(30)['revenue'].mean()
                    change_30 = ((recent_30 - prev_30) / prev_30 * 100) if prev_30 > 0 else 0
                    
                    trend_data.append({
                        'category': category,
                        '7일 변화율': change_7,
                        '14일 변화율': change_14,
                        '30일 변화율': change_30,
                        '45일 변화율': 0
                    })
                elif len(cat_data) >= 28:
                    # 7일, 14일만 계산
                    recent_7 = cat_data.tail(7)['revenue'].mean()
                    prev_7 = cat_data.tail(14).head(7)['revenue'].mean()
                    change_7 = ((recent_7 - prev_7) / prev_7 * 100) if prev_7 > 0 else 0
                    
                    recent_14 = cat_data.tail(14)['revenue'].mean()
                    prev_14 = cat_data.tail(28).head(14)['revenue'].mean()
                    change_14 = ((recent_14 - prev_14) / prev_14 * 100) if prev_14 > 0 else 0
                    
                    trend_data.append({
                        'category': category,
                        '7일 변화율': change_7,
                        '14일 변화율': change_14,
                        '30일 변화율': 0,
                        '45일 변화율': 0
                    })
                elif len(cat_data) >= 14:
                    # 7일만 계산
                    recent_7 = cat_data.tail(7)['revenue'].mean()
                    prev_7 = cat_data.tail(14).head(7)['revenue'].mean()
                    change_7 = ((recent_7 - prev_7) / prev_7 * 100) if prev_7 > 0 else 0
                    
                    trend_data.append({
                        'category': category,
                        '7일 변화율': change_7,
                        '14일 변화율': 0,
                        '30일 변화율': 0,
                        '45일 변화율': 0
                    })
            
            if trend_data:
                # 그룹형 막대 그래프 생성
                import plotly.graph_objects as go
                
                trend_df = pd.DataFrame(trend_data)
                
                # 7일 변화율 기준으로 정렬 (내림차순)
                trend_df = trend_df.sort_values('7일 변화율', ascending=False)
                
                fig = go.Figure()
                
                # 45일 변화율 (가장 먼저)
                if '45일 변화율' in trend_df.columns:
                    fig.add_trace(go.Bar(
                        name='45일 변화율',
                        x=trend_df['category'],
                        y=trend_df['45일 변화율'],
                        marker_color='#7C3AED',
                        text=[f"{v:.1f}%" for v in trend_df['45일 변화율']],
                        textposition='outside'
                    ))
                
                # 30일 변화율
                fig.add_trace(go.Bar(
                    name='30일 변화율',
                    x=trend_df['category'],
                    y=trend_df['30일 변화율'],
                    marker_color='#FF0080',
                    text=[f"{v:.1f}%" for v in trend_df['30일 변화율']],
                    textposition='outside'
                ))
                
                # 14일 변화율
                fig.add_trace(go.Bar(
                    name='14일 변화율',
                    x=trend_df['category'],
                    y=trend_df['14일 변화율'],
                    marker_color='#10F981',
                    text=[f"{v:.1f}%" for v in trend_df['14일 변화율']],
                    textposition='outside'
                ))
                
                # 7일 변화율 (마지막)
                fig.add_trace(go.Bar(
                    name='7일 변화율',
                    x=trend_df['category'],
                    y=trend_df['7일 변화율'],
                    marker_color='#00D9FF',
                    text=[f"{v:.1f}%" for v in trend_df['7일 변화율']],
                    textposition='outside'
                ))
                
                # 0 기준선 추가
                fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
                
                fig.update_layout(
                    title="카테고리별 기간별 매출 변화율 (7일 변화율 순)",
                    xaxis_title="카테고리",
                    yaxis_title="변화율 (%)",
                    barmode='group',
                    height=480,  # 20% 증가 (400 -> 480)
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    plot_bgcolor='rgba(255, 255, 255, 0.02)',
                    font=dict(color='#FFFFFF'),
                    xaxis=dict(tickangle=-45),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("추세 분석을 위한 충분한 데이터가 없습니다.")
                
        except Exception as e:
            st.error(f"카테고리별 추세 분석 중 오류: {e}")
        
    except Exception as e:
        st.error(f"카테고리별 매출 추세 차트 생성 중 오류: {e}")
    
    # ==================== 인사이트 섹션 ====================
    st.markdown("### 💡 자동 인사이트")
    
    insights = generate_trend_insights(df_agg, df_category_weekly if 'df_category_weekly' in locals() else pd.DataFrame())
    
    insight_cols = st.columns(2)
    
    with insight_cols[0]:
        st.markdown("#### 📈 긍정적 시그널")
        for insight in insights['positive'][:3]:
            st.markdown(f'<div class="insight-box">✅ {insight}</div>', unsafe_allow_html=True)
    
    with insight_cols[1]:
        st.markdown("#### ⚠️ 주의 필요")
        for warning in insights['warnings'][:3]:
            st.markdown(f'<div class="warning-box">⚠️ {warning}</div>', unsafe_allow_html=True)
    
    # ==================== 예측 섹션 (선택) ====================
    if show_forecast:
        st.markdown("### 🔮 매출 예측")
        
        try:
            # 간단한 예측 계산
            forecast_metrics = calculator.calculate_forecast_metrics(df_agg, forecast_days=7)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "7일 후 예상 매출",
                    f"{forecast_metrics['forecast_revenue']/1e8:.1f}억",
                    f"추세: {'+' if forecast_metrics['trend_slope'] > 0 else ''}{forecast_metrics['trend_slope']/1e6:.1f}M/일"
                )
            
            with col2:
                lower, upper = forecast_metrics['confidence_interval']
                st.metric(
                    "신뢰구간",
                    f"{lower/1e8:.1f}~{upper/1e8:.1f}억",
                    "95% 신뢰수준"
                )
            
            with col3:
                st.metric(
                    "예측 정확도",
                    f"{forecast_metrics['r_squared']*100:.1f}%",
                    "R² 값"
                )
                
        except Exception as e:
            st.error(f"예측 계산 중 오류: {e}")
    
    # ==================== 요약 통계 테이블 ====================


def generate_trend_insights(df_agg, df_category):
    """
    자동 인사이트 생성 (개선된 버전)
    
    Parameters:
    -----------
    df_agg : DataFrame
        집계 데이터
    df_category : DataFrame
        카테고리별 데이터
        
    Returns:
    --------
    dict : 인사이트 딕셔너리
    """
    insights = {'positive': [], 'warnings': []}
    
    try:
        # 1. 매출 성장률 분석 (더 상세한 분석)
        if not df_agg.empty and 'revenue_dod' in df_agg.columns:
            recent_growth = df_agg['revenue_dod'].iloc[-1]
            week_avg_growth = df_agg['revenue_dod'].tail(7).mean()
            month_avg_growth = df_agg['revenue_dod'].tail(30).mean() if len(df_agg) >= 30 else week_avg_growth
            
            if not pd.isna(recent_growth):
                if recent_growth > 10:
                    insights['positive'].append(
                        f"📈 매출이 전일 대비 {recent_growth:.1f}% 증가 (주간 평균: {week_avg_growth:.1f}%, 월간 평균: {month_avg_growth:.1f}%)"
                    )
                elif recent_growth < -10:
                    insights['warnings'].append(
                        f"📉 매출이 전일 대비 {abs(recent_growth):.1f}% 감소 (주간 평균: {week_avg_growth:.1f}%, 월간 평균: {month_avg_growth:.1f}%)"
                    )
                    
        # 2. 매출 규모 및 수준 분석
        if 'revenue' in df_agg.columns:
            recent_revenue = df_agg['revenue'].tail(7).mean()
            total_revenue = df_agg['revenue'].sum()
            max_revenue = df_agg['revenue'].max()
            min_revenue = df_agg['revenue'][df_agg['revenue'] > 0].min() if any(df_agg['revenue'] > 0) else 0
            
            insights['positive'].append(
                f"💰 최근 7일 평균 매출: {recent_revenue/1e8:.1f}억원 (누적: {total_revenue/1e8:.1f}억원)"
            )
            
            # 최고/최저 매출 대비 현재 수준
            current_level = (df_agg['revenue'].iloc[-1] / max_revenue * 100) if max_revenue > 0 else 0
            if current_level > 80:
                insights['positive'].append(f"🎯 현재 매출이 최고치의 {current_level:.0f}% 수준 (역대 최고: {max_revenue/1e8:.1f}억)")
            elif current_level < 50:
                insights['warnings'].append(f"⚠️ 현재 매출이 최고치의 {current_level:.0f}% 수준 (개선 여지: {(max_revenue - df_agg['revenue'].iloc[-1])/1e8:.1f}억)")
        
        # 3. 추세 패턴 분석
        if 'trend_direction_7' in df_agg.columns:
            recent_trends = df_agg.tail(14)['trend_direction_7'].dropna()
            if len(recent_trends) > 0:
                up_count = (recent_trends == 'up').sum()
                down_count = (recent_trends == 'down').sum()
                stable_count = (recent_trends == 'stable').sum()
                
                total_days = len(recent_trends)
                if up_count > total_days * 0.6:
                    insights['positive'].append(f"📊 최근 2주간 {up_count}일 상승 추세 ({up_count/total_days*100:.0f}%)")
                elif down_count > total_days * 0.6:
                    insights['warnings'].append(f"📊 최근 2주간 {down_count}일 하락 추세 ({down_count/total_days*100:.0f}%)")
                else:
                    insights['positive'].append(f"📊 최근 2주간 안정적 추세 (상승 {up_count}일, 하락 {down_count}일, 보합 {stable_count}일)")
        
        # 4. 주간 패턴 분석
        if 'revenue' in df_agg.columns and len(df_agg) >= 7:
            # 요일별 평균 계산
            df_agg_copy = df_agg.copy()
            df_agg_copy['weekday'] = pd.to_datetime(df_agg_copy['date']).dt.day_name()
            weekday_avg = df_agg_copy.groupby('weekday')['revenue'].mean()
            
            if not weekday_avg.empty:
                best_day = weekday_avg.idxmax()
                worst_day = weekday_avg.idxmin()
                insights['positive'].append(f"📅 최고 실적 요일: {best_day} (평균 {weekday_avg[best_day]/1e8:.1f}억)")
                if weekday_avg[worst_day] < weekday_avg.mean() * 0.7:
                    insights['warnings'].append(f"📅 {worst_day} 실적 개선 필요 (평균 {weekday_avg[worst_day]/1e8:.1f}억)")
        
        # 5. 이상치 패턴 분석
        if 'is_anomaly' in df_agg.columns:
            anomaly_count = df_agg.tail(30)['is_anomaly'].sum()
            if anomaly_count > 5:
                insights['warnings'].append(f"🔴 최근 30일간 이상치 {anomaly_count}건 감지 - 운영 안정성 점검 필요")
            elif anomaly_count > 0:
                insights['warnings'].append(f"🟡 최근 30일간 이상치 {anomaly_count}건 감지")
            else:
                insights['positive'].append("🟢 최근 30일간 이상치 없음 - 안정적 운영")
        
        # 6. 카테고리 다양성 분석
        if not df_category.empty and 'category' in df_category.columns:
            unique_categories = df_category['category'].nunique()
            top_category = df_category['category'].value_counts().head(1)
            if not top_category.empty:
                top_cat_name = top_category.index[0]
                top_cat_ratio = top_category.values[0] / len(df_category) * 100
                
                insights['positive'].append(f"🏆 주력 카테고리: {top_cat_name} ({top_cat_ratio:.1f}% 비중)")
                
                if unique_categories < 5:
                    insights['warnings'].append(f"📦 카테고리 다양성 부족 ({unique_categories}개) - 포트폴리오 확대 검토")
                elif unique_categories > 10:
                    insights['positive'].append(f"📦 다양한 카테고리 운영 중 ({unique_categories}개)")
        
        # 7. 성장 모멘텀 분석
        if 'revenue' in df_agg.columns and len(df_agg) >= 14:
            last_week = df_agg.tail(7)['revenue'].mean()
            prev_week = df_agg.tail(14).head(7)['revenue'].mean()
            
            if prev_week > 0:
                momentum = ((last_week - prev_week) / prev_week * 100)
                if momentum > 15:
                    insights['positive'].append(f"🚀 강한 성장 모멘텀 (주간 +{momentum:.1f}%)")
                elif momentum < -15:
                    insights['warnings'].append(f"⚠️ 성장 모멘텀 약화 (주간 {momentum:.1f}%)")
        
        # 8. 변동성 수준 평가
        if 'cv_30' in df_agg.columns:
            recent_volatility = df_agg['cv_30'].iloc[-1] if not pd.isna(df_agg['cv_30'].iloc[-1]) else 0
            if recent_volatility < 0.2:
                insights['positive'].append(f"✅ 매출 변동성 낮음 ({recent_volatility:.2f}) - 예측 가능한 수익 구조")
            elif recent_volatility > 0.4:
                insights['warnings'].append(f"⚠️ 매출 변동성 높음 ({recent_volatility:.2f}) - 안정화 전략 필요")
                
    except Exception as e:
        print(f"인사이트 생성 중 오류: {e}")
        insights['warnings'].append("일부 인사이트 생성 실패")
    
    # 인사이트가 없는 경우 기본 메시지 추가
    if not insights['positive']:
        insights['positive'].append("데이터 수집 중 - 추가 기간 필요")
    if not insights['warnings']:
        insights['warnings'].append("현재 특별한 주의사항 없음")
    
    return insights