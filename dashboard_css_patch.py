"""
dashboard_css_patch.py - 메인 대시보드 CSS 충돌 해결
"""

def apply_dark_theme_patch():
    """다크 테마 CSS 패치 - 전략 분석과 충돌 방지"""
    return """
    <style>
    /* 메인 대시보드 다크 테마 유지 */
    .main-dashboard-card {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* 메트릭 카드 - 네임스페이스로 구분 */
    .main-metric-card {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #FFFFFF !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* 전략 분석 전용 스타일은 strategy- 프리픽스 사용 */
    .strategy-metric-card {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* 스트림릿 기본 컨테이너 다크 유지 */
    .stApp {
        background: #050511 !important;
    }
    
    /* 사이드바 다크 테마 */
    section[data-testid="stSidebar"] {
        background: rgba(10, 11, 30, 0.95) !important;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.02) !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #B8BCC8 !important;
        background: transparent !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(102, 126, 234, 0.2) !important;
        color: #00D9FF !important;
    }
    
    /* 텍스트 색상 */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
    }
    
    p, span, div {
        color: #B8BCC8 !important;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%) !important;
        color: white !important;
        border: 1px solid rgba(102, 126, 234, 0.5) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 1) 0%, rgba(118, 75, 162, 1) 100%) !important;
    }
    
    /* selectbox 스타일 */
    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #FFFFFF !important;
    }
    
    /* 입력 필드 */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #FFFFFF !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #00D9FF !important;
    }
    
    /* 데이터프레임 */
    .dataframe {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #B8BCC8 !important;
    }
    
    /* Plotly 차트 배경 */
    .js-plotly-plot .plotly {
        background: transparent !important;
    }
    </style>
    """
