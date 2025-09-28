"""
dashboard_config.py - Dark Mode + Glassmorphism 테마 설정 (통합 호버 개선)
Version: 25.1.0
Last Updated: 2025-02-03

주요 수정사항:
1. Plotly hoverlabel 속성 오류 수정
   - font_size, font_family를 font 딕셔너리 안으로 이동
   - borderwidth 속성 제거 (지원되지 않음)
2. 모든 HOVER_CONFIG 설정 수정 완료
3. colorbar borderwidth도 제거
4. ROI 계산법 변경 (2025-02-03)
   - 전환율: 43.5% → 75%
   - 제품 원가율: 13% 추가
   - 판매 수수료율: 10% 추가
   - 실질 마진율: 57.75%
5. 카테고리별 고유 색상 매핑 추가 (중복 방지)
"""

import streamlit as st
from datetime import datetime
import numpy as np

# ============================================================================
# 버전 관리
# ============================================================================
VERSION = "25.1.1"
LAST_UPDATED = "2025-02-03"

# ============================================================================
# 페이지 설정
# ============================================================================
PAGE_CONFIG = {
    "layout": "wide",
    "page_title": "홈쇼핑 방송 분석 대시보드",
    "page_icon": "🌌",
    "initial_sidebar_state": "expanded"
}

# ============================================================================
# 비즈니스 로직 상수 - ROI 계산법 변경
# ============================================================================
LIVE_CHANNELS = {
    '현대홈쇼핑', 'GS홈쇼핑', 'gs홈쇼핑', '롯데홈쇼핑', 
    'CJ온스타일', 'cj온스타일', '홈앤쇼핑', 'NS홈쇼핑', 
    'ns홈쇼핑', '공영쇼핑', '공영홈쇼핑'
}

MODEL_COST_LIVE = 10400000
MODEL_COST_NON_LIVE = 2000000

# 새로운 ROI 계산법 상수들
CONVERSION_RATE = 0.75      # 전환율 75% (기존 43.5%에서 변경)
PRODUCT_COST_RATE = 0.13    # 제품 원가율 13%
COMMISSION_RATE = 0.10      # 판매 수수료율 10%
REAL_MARGIN_RATE = (1 - COMMISSION_RATE - PRODUCT_COST_RATE) * CONVERSION_RATE
# REAL_MARGIN_RATE = 0.5775 (57.75%)

# ============================================================================
# Dark Mode + Glassmorphism 색상 팔레트
# ============================================================================

# 메인 색상 팔레트
COLORS = {
    # 배경색 - 깊은 우주 느낌
    'bg_base': '#050511',          # 가장 깊은 배경
    'bg_primary': '#0A0B1E',       # 메인 배경
    'bg_secondary': '#101332',     # 섹션 배경
    'bg_card': 'rgba(255, 255, 255, 0.05)',  # 글래스 카드
    'bg_hover': 'rgba(255, 255, 255, 0.08)',  # 호버 상태
    
    # 텍스트 색상 - 모두 흰색 계열로 통일
    'text_primary': '#FFFFFF',     # 100% - 제목
    'text_secondary': '#FFFFFF',   # 본문도 흰색으로
    'text_muted': '#B8BCC8',       # 보조 텍스트는 밝은 회색
    'text_disabled': 'rgba(255, 255, 255, 0.5)',   # 비활성
    
    # 테두리 - 글래스 효과
    'border': 'rgba(255, 255, 255, 0.12)',
    'border_focus': 'rgba(0, 217, 255, 0.5)',
    'border_light': 'rgba(255, 255, 255, 0.06)',
    
    # 네온 액센트 색상
    'accent_primary': '#00D9FF',   # 시안 (메인)
    'accent_secondary': '#7C3AED', # 퍼플
    'accent_tertiary': '#FF0080',  # 핑크
    'accent_light': '#10F981',     # 그린
    'accent_hover': '#FFD93D',     # 옐로우
    
    # 차트용 네온 색상
    'chart_primary': '#00D9FF',    # 시안
    'chart_secondary': '#7C3AED',  # 퍼플
    'chart_tertiary': '#10F981',   # 그린
    'chart_quaternary': '#FF6B35', # 오렌지
    
    # 상태 색상
    'success': '#10F981',           # 네온 그린
    'warning': '#FFD93D',           # 네온 옐로우
    'danger': '#FF3355',            # 네온 레드
    'info': '#00D9FF',              # 네온 시안
}

# 별칭
ENHANCED_PASTEL_COLORS = COLORS

# ============================================================================
# 통합 호버 툴팁 설정 (중앙 집중식 관리) - PLOTLY 오류 수정
# ============================================================================

# 기본 호버 설정 (모든 차트 공통)
DEFAULT_HOVER_CONFIG = {
    'bgcolor': 'rgba(10, 11, 30, 0.95)',
    'bordercolor': '#00D9FF',
    'font': {
        'color': '#FFFFFF',
        'size': 14,
        'family': "'Inter', 'Pretendard', sans-serif"
    },
    'align': 'left',
    'namelength': -1
}

# 히트맵 전용 호버 설정
HEATMAP_HOVER_CONFIG = {
    'bgcolor': 'rgba(0, 0, 0, 0.98)',
    'bordercolor': '#FFFFFF',
    'font': {
        'color': '#FFFFFF',
        'size': 16,
        'family': "'Inter', 'Pretendard', sans-serif"
    },
    'align': 'left',
    'namelength': -1
}

# 대량 데이터용 간소화 설정
SIMPLE_HOVER_CONFIG = {
    'bgcolor': 'rgba(30, 30, 40, 0.9)',
    'bordercolor': '#7C3AED',
    'font': {
        'color': '#FFFFFF',
        'size': 12,
        'family': 'Arial'
    },
    'align': 'auto'
}

# 특수 차트용 호버 설정
TREEMAP_HOVER_CONFIG = {
    'bgcolor': 'rgba(10, 11, 30, 0.95)',
    'bordercolor': '#10F981',
    'font': {
        'color': '#FFFFFF',
        'size': 13,
        'family': "'Inter', 'Pretendard', sans-serif"
    },
    'align': 'left',
    'namelength': -1
}

PIE_HOVER_CONFIG = {
    'bgcolor': 'rgba(10, 11, 30, 0.95)',
    'bordercolor': '#FF0080',
    'font': {
        'color': '#FFFFFF',
        'size': 13,
        'family': "'Inter', 'Pretendard', sans-serif"
    },
    'align': 'left',
    'namelength': -1
}

# 구버전 호환성을 위한 별칭
ENHANCED_HOVER_CONFIG = DEFAULT_HOVER_CONFIG
IMPROVED_HOVER_CONFIG = DEFAULT_HOVER_CONFIG

# ============================================================================
# 호버 템플릿 표준화 클래스
# ============================================================================

class HoverTemplates:
    """표준 호버 템플릿 모음"""
    
    # 기본 템플릿
    DEFAULT = '%{x}<br>%{y:,.0f}<extra></extra>'
    
    # 매출 관련
    REVENUE = '%{x}<br>매출: %{y:,.0f}원<extra></extra>'
    REVENUE_WITH_DATE = '%{x|%Y-%m-%d}<br>매출: %{y:,.0f}원<extra></extra>'
    REVENUE_WITH_TIME = '%{x}시<br>매출: %{y:,.0f}원<extra></extra>'
    
    # ROI 관련
    ROI = '%{x}<br>ROI: %{y:.1f}%<extra></extra>'
    ROI_WITH_VALUE = '%{x}<br>ROI: %{y:.1f}%<br>매출: %{customdata:,.0f}원<extra></extra>'
    
    # 히트맵
    HEATMAP_REVENUE = '%{y} %{x}<br>매출: %{z:,.0f}원<extra></extra>'
    HEATMAP_ROI = '%{y} %{x}<br>ROI: %{z:.1f}%<extra></extra>'
    HEATMAP_MEDIAN = '%{y} %{x}<br>중위 매출: %{z:,.0f}원<extra></extra>'
    
    # 플랫폼/카테고리
    PLATFORM = '<b>%{x}</b><br>매출: %{y:,.0f}원<br>점유율: %{percent}<extra></extra>'
    CATEGORY = '<b>%{label}</b><br>매출: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
    
    # 시계열
    TIMESERIES = '%{x|%H시}<br>평균: %{y:,.0f}원<extra></extra>'
    DAILY = '%{x|%m/%d}<br>매출: %{y:,.0f}원<extra></extra>'
    WEEKLY = '주차: %{x}<br>매출: %{y:,.0f}원<extra></extra>'
    MONTHLY = '%{x|%Y-%m}<br>매출: %{y:,.0f}원<extra></extra>'
    
    # 박스플롯
    BOXPLOT = '%{x}<br>중위값: %{median}<br>Q1: %{q1}<br>Q3: %{q3}<extra></extra>'
    
    # 트리맵
    TREEMAP = '<b>%{label}</b><br>매출: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
    
    @staticmethod
    def get_template(chart_type, metric='revenue'):
        """차트 타입과 메트릭에 따른 템플릿 반환"""
        templates = {
            ('bar', 'revenue'): HoverTemplates.REVENUE,
            ('bar', 'roi'): HoverTemplates.ROI,
            ('heatmap', 'revenue'): HoverTemplates.HEATMAP_REVENUE,
            ('heatmap', 'roi'): HoverTemplates.HEATMAP_ROI,
            ('heatmap', 'median'): HoverTemplates.HEATMAP_MEDIAN,
            ('pie', 'revenue'): HoverTemplates.CATEGORY,
            ('line', 'revenue'): HoverTemplates.REVENUE_WITH_DATE,
            ('scatter', 'revenue'): HoverTemplates.REVENUE,
            ('box', 'revenue'): HoverTemplates.BOXPLOT,
            ('treemap', 'revenue'): HoverTemplates.TREEMAP,
        }
        return templates.get((chart_type, metric), HoverTemplates.DEFAULT)

# ============================================================================
# 방송사별 색상 - 네온 버전
# ============================================================================
PLATFORM_COLORS = {
    # NS홈쇼핑 - 네온 레드
    'NS홈쇼핑': '#FF3355',
    'NSN홈쇼핑': '#FF3355',
    'ns홈쇼핑': '#FF3355',
    'NS홈쇼핑 샵플러스': '#FF5577',
    
    # GS홈쇼핑 - 네온 그린
    'GS홈쇼핑': '#10F981',
    'gs홈쇼핑': '#10F981',
    'GS홈쇼핑 마이샵': '#30FFA1',
    
    # 메이저 방송사 - 네온 색상
    '현대홈쇼핑': '#00D9FF',       # 네온 시안
    '현대홈쇼핑플러스샵': '#20E9FF',
    '현대홈쇼핑 플러스샵': '#20E9FF',
    '롯데홈쇼핑': '#FF6B35',       # 네온 오렌지
    'CJ온스타일': '#7C3AED',       # 네온 퍼플
    'cj온스타일': '#7C3AED',
    'CJ온스타일 플러스': '#9C5AFD',
    
    # 세미 메이저 - 네온 톤
    'K쇼핑': '#FF0080',            # 네온 핑크
    '홈앤쇼핑': '#FFD93D',         # 네온 옐로우
    'SK스토아': '#B24BF3',         # 밝은 퍼플
    '신세계라이브쇼핑': '#00FFB9', # 네온 민트
    '공영홈쇼핑': '#FFA500',       # 네온 골드
    '공영쇼핑': '#FFA500',
    
    # 기타 방송사
    '신라면세점': '#4ECDC4',       # 터코이즈
    'W쇼핑': '#FF6B9D',            # 로즈
    'Shopping&T': '#C44569',       # 딥로즈
    '더블유쇼핑': '#C44569',
    '쇼핑엔티': '#FEB692',         # 피치
    '롯데원티비': '#FF9FF3',       # 라이트핑크
    '하림쇼핑': '#54A0FF',         # 스카이블루
    'AK쇼핑': '#48DBFB',           # 라이트시안
    'KT알파쇼핑': '#A29BFE',       # 라벤더
    '홈앤톡': '#6C5CE7',           # 딥퍼플
    '신세계쇼핑': '#FD79A8',       # 핫핑크
    '기타': '#FFFFFF'              # 흰색
}

# 별칭
PLATFORM_FIXED_COLORS = PLATFORM_COLORS

# ============================================================================
# 카테고리별 고유 색상 매핑 (중복 방지) - 수정 및 확장
# ============================================================================
CATEGORY_COLORS_UNIQUE = {
    # 주요 카테고리 - 고유 색상 배정
    '디지털/가전': '#00D9FF',      # 시안 (변경됨)
    '가전/디지털': '#00D9FF',      # 시안 (변경됨)
    '화장품/미용': '#FF0080',      # 네온 핑크 (유지)
    '패션의류': '#10F981',         # 네온 그린
    '패션/의류': '#10F981',        # 네온 그린
    '식품': '#FFD93D',             # 골드
    '생활용품': '#7C3AED',         # 퍼플
    
    # 추가 카테고리 - 모두 다른 색상
    '스포츠/레저': '#FF6B35',      # 오렌지
    '가구/인테리어': '#00FFB9',    # 민트
    '침구/인테리어': '#00FFB9',    # 민트
    '주방용품': '#FF3355',         # 레드
    '건강식품': '#4ECDC4',         # 틸
    '유아동': '#95E1D3',           # 라이트 민트
    '유아용품': '#95E1D3',         # 라이트 민트
    '도서/문구': '#F38181',        # 코랄
    '도서/음반': '#F38181',        # 코랄
    '반려동물': '#AA96DA',         # 라벤더
    '애완용품': '#AA96DA',         # 라벤더
    '자동차용품': '#8B5CF6',       # 바이올렛
    '원예/화훼': '#84CC16',        # 라임
    '보석/시계': '#F59E0B',        # 앰버
    '주얼리/시계': '#F59E0B',      # 앰버
    '캠핑용품': '#06B6D4',         # 사이언
    '악기': '#EC4899',             # 핫핑크
    '완구': '#A855F7',             # 퍼플2
    '홈데코': '#14B8A6',           # 틸2
    '문구류': '#F97316',           # 오렌지2
    '속옷/잠옷': '#FF9FF3',        # 라이트 핑크
    '가구': '#48DBFB',             # 라이트 시안
    '패션잡화': '#B24BF3',         # 밝은 퍼플
    '농수산물': '#54A0FF',         # 스카이 블루
    '여행/상품권': '#7EFFF5',      # 아쿠아
    '기타': '#C0C0C0'              # 실버
}

# 기존 CATEGORY_COLORS를 CATEGORY_COLORS_UNIQUE로 대체
CATEGORY_COLORS = CATEGORY_COLORS_UNIQUE

# 별칭 (호환성 유지)
CATEGORY_UNIQUE_COLORS = CATEGORY_COLORS_UNIQUE

# ============================================================================
# 색상 선택 헬퍼 함수들
# ============================================================================

def get_category_color(category, default='#808080'):
    """카테고리에 맞는 색상 반환"""
    # 정확한 매칭 시도
    if category in CATEGORY_COLORS_UNIQUE:
        return CATEGORY_COLORS_UNIQUE[category]
    
    # 부분 매칭 시도 (키워드 기반)
    category_lower = str(category).lower()
    for key, color in CATEGORY_COLORS_UNIQUE.items():
        if key.lower() in category_lower or category_lower in key.lower():
            return color
    
    return default

def get_category_colors_list(categories, ensure_unique=True):
    """카테고리 리스트에 대한 색상 리스트 반환"""
    # 기본 색상 팔레트 (모두 다른 색상)
    default_colors = [
        '#00D9FF', '#FF0080', '#10F981', '#FFD93D', '#7C3AED',
        '#FF6B35', '#00FFB9', '#FF3355', '#4ECDC4', '#95E1D3',
        '#F38181', '#AA96DA', '#8B5CF6', '#84CC16', '#F59E0B'
    ]
    
    colors = []
    used_colors = set()
    
    for idx, cat in enumerate(categories):
        color = get_category_color(cat, None)
        
        # 색상이 없거나 이미 사용된 경우
        if color is None or (ensure_unique and color in used_colors):
            # 사용되지 않은 기본 색상 찾기
            for default_color in default_colors:
                if default_color not in used_colors:
                    color = default_color
                    break
            else:
                # 모든 색상이 사용된 경우, 인덱스 기반 색상 선택
                color = default_colors[idx % len(default_colors)]
        
        colors.append(color)
        used_colors.add(color)
    
    return colors

def get_platform_color(platform, default='#808080'):
    """방송사에 맞는 색상 반환"""
    return PLATFORM_COLORS.get(platform, default)

# ============================================================================
# 요일별 색상 - 네온 레인보우
# ============================================================================
WEEKDAY_COLORS = {
    0: '#FF3355',  # 월요일 - 네온 레드
    1: '#FF6B35',  # 화요일 - 네온 오렌지
    2: '#FFD93D',  # 수요일 - 네온 옐로우
    3: '#10F981',  # 목요일 - 네온 그린
    4: '#00D9FF',  # 금요일 - 네온 시안
    5: '#7C3AED',  # 토요일 - 네온 퍼플
    6: '#FF0080'   # 일요일 - 네온 핑크
}

# ============================================================================
# 기본 필터 설정
# ============================================================================
DEFAULT_FILTERS = {
    'revenue_limit': 1200000000,
    'price_limit': 400000,
    'weekday_filter': '전체',
    'items_per_page': 50,
    'default_platform': 'NS홈쇼핑',
    'default_category': '화장품/미용',
}

# ============================================================================
# 히트맵 색상 스케일 - 다크 테마용 (최적화)
# ============================================================================

# 매출용 히트맵 컬러스케일
HEATMAP_COLORSCALE_REVENUE = [
    [0, 'rgba(5, 5, 17, 1)'],
    [0.2, 'rgba(124, 58, 237, 0.5)'],
    [0.5, 'rgba(0, 217, 255, 0.6)'],
    [0.8, 'rgba(16, 249, 129, 0.7)'],
    [1, '#10F981']
]

# ROI용 최적화된 히트맵 컬러스케일
HEATMAP_COLORSCALE_ROI = [
    [0.0, 'rgba(30, 41, 59, 1)'],     # 어두운 슬레이트 (낮은 ROI)
    [0.2, 'rgba(239, 68, 68, 0.8)'],  # 빨강 (부정적 ROI)  
    [0.4, 'rgba(251, 191, 36, 0.8)'], # 노랑 (중간 ROI)
    [0.6, 'rgba(34, 211, 238, 0.8)'], # 시안 (좋은 ROI)
    [0.8, 'rgba(16, 185, 129, 0.9)'], # 그린 (높은 ROI)
    [1.0, '#10F981']                  # 네온 그린 (최고 ROI)
]

# ROI 전용 RdYlGn 스케일 (개선된 버전)
ROI_COLORSCALE_OPTIMIZED = [
    [0.0, '#dc2626'],    # 빨강 (낮은 ROI)
    [0.25, '#ea580c'],   # 오렌지-레드
    [0.5, '#eab308'],    # 노랑 (중간)
    [0.75, '#22d3ee'],   # 시안 (좋음)
    [1.0, '#10b981']     # 그린 (우수)
]

# ============================================================================
# 차트 기본 설정 - 다크 테마 (호버 통합)
# ============================================================================
CHART_CONFIG = {
    'height': 500,
    'margin': dict(t=40, b=40, l=40, r=40),
    'paper_bgcolor': 'rgba(0, 0, 0, 0)',  # 완전 투명
    'plot_bgcolor': 'rgba(255, 255, 255, 0.02)',  # 거의 투명
    'font': dict(
        family="'Inter', 'Pretendard', system-ui, sans-serif",
        size=14,
        color='#FFFFFF'
    ),
    'hovermode': 'x unified',
    # 기본 호버 설정 적용
    'hoverlabel': DEFAULT_HOVER_CONFIG,
    'xaxis': dict(
        gridcolor='rgba(255, 255, 255, 0.06)',
        linecolor='rgba(255, 255, 255, 0.12)',
        linewidth=2,
        tickfont=dict(color='#FFFFFF', size=12),
        titlefont=dict(color='#FFFFFF', size=14)
    ),
    'yaxis': dict(
        gridcolor='rgba(255, 255, 255, 0.06)',
        linecolor='rgba(255, 255, 255, 0.12)',
        linewidth=2,
        tickfont=dict(color='#FFFFFF', size=12),
        titlefont=dict(color='#FFFFFF', size=14)
    )
}

# ============================================================================
# 개선된 호버 함수들
# ============================================================================

def get_hover_config(chart_type='default', custom_settings=None):
    """차트 타입별 최적 호버 설정 반환 (개선된 버전)"""
    hover_configs = {
        'default': DEFAULT_HOVER_CONFIG,
        'heatmap': HEATMAP_HOVER_CONFIG,
        'simple': SIMPLE_HOVER_CONFIG,
        'treemap': TREEMAP_HOVER_CONFIG,
        'pie': PIE_HOVER_CONFIG,
        'bar': DEFAULT_HOVER_CONFIG,
        'line': DEFAULT_HOVER_CONFIG,
        'scatter': DEFAULT_HOVER_CONFIG,
        'box': DEFAULT_HOVER_CONFIG
    }
    
    config = hover_configs.get(chart_type, DEFAULT_HOVER_CONFIG).copy()
    
    # 사용자 정의 설정 병합
    if custom_settings:
        # font 설정이 있으면 올바르게 병합
        if 'font' in custom_settings:
            config['font'] = {**config['font'], **custom_settings['font']}
            del custom_settings['font']
        # 나머지 설정 병합
        config.update(custom_settings)
    
    return config

def emergency_hover_fix(fig, chart_type='default'):
    """통합 호버 툴팁 수정 함수 - 개선된 버전"""
    config = get_hover_config(chart_type)
    fig.update_layout(hoverlabel=config)
    
    # 히트맵인 경우 추가 설정
    if chart_type == 'heatmap':
        for trace in fig.data:
            if hasattr(trace, 'type') and trace.type == 'heatmap':
                trace.update(
                    connectgaps=False,
                    hoverongaps=False,
                    xgap=0,
                    ygap=0
                )
    
    return fig

def create_heatmap_with_fix(z_data, x_labels, y_labels, 
                           colorscale=None, text_values=None,
                           hovertemplate=None, title=""):
    """히트맵 생성 헬퍼 - 모든 문제 해결 (수정됨)"""
    import plotly.graph_objects as go
    
    # 기본값 설정
    if colorscale is None:
        colorscale = HEATMAP_COLORSCALE_REVENUE
    if hovertemplate is None:
        hovertemplate = HoverTemplates.HEATMAP_REVENUE
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        text=text_values,
        texttemplate='%{text}' if text_values else None,
        textfont=dict(size=14, color='#FFFFFF'),
        hovertemplate=hovertemplate,
        # 히트맵 라인 문제 완전 해결
        connectgaps=False,
        hoverongaps=False,
        xgap=0,
        ygap=0,
        colorbar=dict(
            tickfont=dict(color='#FFFFFF'),
            title=dict(
                text=title,
                font=dict(color='#FFFFFF', size=14)
            ),
            bgcolor='rgba(0, 0, 0, 0)',
            bordercolor='#00D9FF',
            # borderwidth 제거됨 (지원 안됨)
            thickness=20,
            len=0.8
        )
    ))
    
    # 히트맵 전용 호버 설정 적용
    fig.update_layout(
        hoverlabel=HEATMAP_HOVER_CONFIG,
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(255, 255, 255, 0.02)',
        font=dict(color='#FFFFFF'),
        height=600
    )
    
    return fig

# ============================================================================
# 히트맵 데이터 정규화 함수
# ============================================================================

def normalize_heatmap_data(z_values):
    """히트맵 데이터 정규화 및 범위 최적화"""
    z_clean = np.nan_to_num(z_values, nan=0)
    
    if np.max(z_clean) == 0:
        return {'zmin': 0, 'zmax': 1, 'zmid': 0.5}
    
    # 극값 제거 (상위 5%, 하위 5%)
    non_zero_values = z_clean[z_clean > 0]
    if len(non_zero_values) > 0:
        z_min, z_max = np.percentile(non_zero_values, [5, 95])
        z_mid = np.median(non_zero_values)
    else:
        z_min, z_max, z_mid = 0, np.max(z_clean), np.max(z_clean) / 2
    
    return {
        'zmin': z_min,
        'zmax': z_max,
        'zmid': z_mid
    }

def optimize_roi_heatmap_colors(roi_data):
    """ROI 히트맵 색상 최적화"""
    roi_clean = np.nan_to_num(roi_data, nan=0)
    
    # ROI 특성에 맞는 범위 설정
    if len(roi_clean[roi_clean != 0]) > 0:
        q25, q75 = np.percentile(roi_clean[roi_clean != 0], [25, 75])
        roi_min = min(-50, np.min(roi_clean))  # 음수 ROI도 고려
        roi_max = max(100, np.max(roi_clean))  # 100% 이상도 고려
        
        return {
            'zmin': roi_min,
            'zmax': roi_max,
            'zmid': 0,  # ROI는 0을 기준으로
            'colorscale': ROI_COLORSCALE_OPTIMIZED
        }
    else:
        return {
            'zmin': -50,
            'zmax': 100,
            'zmid': 0,
            'colorscale': ROI_COLORSCALE_OPTIMIZED
        }

def fix_heatmap_data(z_data):
    """히트맵 데이터 수정 및 검증"""
    # NaN 값 처리
    z_clean = np.nan_to_num(z_data, nan=0)
    
    # 극값 제거 (99th percentile 캡핑)
    if np.max(z_clean) > 0:
        q99 = np.percentile(z_clean[z_clean > 0], 99)
        z_clean = np.clip(z_clean, 0, q99)
    
    return z_clean

# ============================================================================
# 함수들
# ============================================================================

def apply_page_config():
    """Streamlit 페이지 설정 적용"""
    st.set_page_config(**PAGE_CONFIG)

def apply_custom_styles():
    """최적화된 Dark Mode + Glassmorphism 테마 (입력 필드 가시성 개선)"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        /* ===== 기본 설정 - GPU 가속 활용 ===== */
        * {
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        /* ===== CSS 변수 정의 ===== */
        :root {
            --neon-cyan: #00D9FF;
            --neon-purple: #7C3AED;
            --neon-green: #10F981;
            --neon-pink: #FF0080;
            --neon-yellow: #FFD93D;
            --neon-red: #FF3355;
            --text-primary: #FFFFFF;
            --text-secondary: #FFFFFF;
            --glow-intensity: 0.5;
        }
        
        /* ===== 전체 텍스트 기본 색상 - 강제 적용 ===== */
        .stApp * {
            color: var(--text-primary) !important;
        }
        
        /* ===== 입력 필드 텍스트 가시성 개선 (수정) ===== */
        .stTextInput input, 
        .stNumberInput input, 
        .stDateInput input,
        .stTimeInput input,
        .stTextArea textarea {
            color: #FFFFFF !important;
            background: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(0, 217, 255, 0.3) !important;
            padding: 8px 12px !important;
            border-radius: 8px !important;
        }
        
        /* 입력 필드 포커스 상태 */
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--neon-cyan) !important;
            box-shadow: 0 0 0 2px rgba(0, 217, 255, 0.2) !important;
            background: rgba(255, 255, 255, 0.1) !important;
        }
        
        /* 셀렉트박스 텍스트 가시성 (수정) */
        .stSelectbox label, 
        .stMultiSelect label,
        .stRadio label,
        .stCheckbox label {
            color: #FFFFFF !important;
        }
        
        .stSelectbox > div > div,
        .stMultiSelect > div > div {
            color: #FFFFFF !important;
            background: rgba(255, 255, 255, 0.08) !important;
        }
        
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(0, 217, 255, 0.3) !important;
        }
        
        /* 드롭다운 메뉴 스타일 */
        [data-baseweb="menu"] {
            background-color: rgba(10, 11, 30, 0.98) !important;
            border: 1px solid rgba(0, 217, 255, 0.3) !important;
        }
        
        [data-baseweb="menu"] [role="option"] {
            color: #FFFFFF !important;
            background-color: transparent !important;
        }
        
        [data-baseweb="menu"] [role="option"]:hover {
            background-color: rgba(0, 217, 255, 0.2) !important;
        }
        
        /* ===== 네온 글로우 애니메이션 ===== */
        @keyframes neonGlow {
            0%, 100% {
                text-shadow: 
                    0 0 10px rgba(0, 217, 255, 0.8),
                    0 0 20px rgba(0, 217, 255, 0.6),
                    0 0 30px rgba(0, 217, 255, 0.4);
            }
            50% {
                text-shadow: 
                    0 0 20px rgba(0, 217, 255, 1),
                    0 0 30px rgba(0, 217, 255, 0.8),
                    0 0 40px rgba(0, 217, 255, 0.6);
            }
        }
        
        /* ===== 펄스 애니메이션 ===== */
        @keyframes pulse {
            0% { 
                transform: scale(1);
                box-shadow: 0 0 0 0 rgba(0, 217, 255, 0.7);
            }
            70% {
                transform: scale(1.05);
                box-shadow: 0 0 0 10px rgba(0, 217, 255, 0);
            }
            100% {
                transform: scale(1);
                box-shadow: 0 0 0 0 rgba(0, 217, 255, 0);
            }
        }
        
        /* ===== 메인 배경 - 단순화된 그라디언트 ===== */
        .stApp {
            background: linear-gradient(135deg, #0A0B1E 0%, #1A1B3A 100%);
            min-height: 100vh;
            position: relative;
        }
        
        /* ===== 서브틀한 오버레이 효과 (성능 최적화) ===== */
        .stApp::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(
                ellipse at top left, 
                rgba(0, 217, 255, 0.08) 0%, 
                transparent 50%
            );
            pointer-events: none;
            z-index: 1;
            will-change: transform;
        }
        
        /* ===== 메인 타이틀 - 네온 애니메이션 적용 ===== */
        .main-title {
            font-size: 48px;
            font-weight: 700;
            background: linear-gradient(135deg, #00D9FF 0%, #7C3AED 50%, #FF0080 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: 30px;
            letter-spacing: -0.5px;
            position: relative;
            animation: neonGlow 2s ease-in-out infinite;
            transform: translateZ(0); /* GPU 가속 */
        }
        
        /* ===== 카드 스타일 - 경량 glassmorphism + 호버 효과 ===== */
        .section-card, .metric-card {
            background: rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 
                0 8px 32px rgba(0, 0, 0, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            will-change: transform;
            position: relative;
            overflow: hidden;
        }
        
        /* ===== 네온 보더 효과 ===== */
        .section-card::before, .metric-card::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(
                45deg,
                var(--neon-cyan),
                var(--neon-purple),
                var(--neon-pink),
                var(--neon-cyan)
            );
            border-radius: 16px;
            opacity: 0;
            z-index: -1;
            transition: opacity 0.3s ease;
            filter: blur(5px);
        }
        
        /* ===== 호버 효과 - 네온 글로우 ===== */
        .section-card:hover, .metric-card:hover {
            transform: translateY(-2px) translateZ(0);
            box-shadow: 
                0 12px 40px rgba(0, 217, 255, 0.15),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            border-color: rgba(0, 217, 255, 0.3);
        }
        
        .section-card:hover::before, .metric-card:hover::before {
            opacity: 0.3;
        }
        
        /* ===== 대시보드 카드 - 네온 액센트 ===== */
        .dashboard-card {
            background: linear-gradient(
                135deg,
                rgba(255, 255, 255, 0.05) 0%,
                rgba(255, 255, 255, 0.02) 100%
            );
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 217, 255, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
            overflow: hidden;
            transform: translateZ(0);
        }
        
        /* ===== 데이터테이블 Dark Mode 스타일링 강화 (수정) ===== */
        .dataframe,
        .stDataFrame > div > div > div > div {
            background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(0, 217, 255, 0.2) !important;
            overflow: hidden !important;
        }
        
        .dataframe thead th,
        .stDataFrame thead th {
            background: linear-gradient(135deg, rgba(0, 217, 255, 0.15), rgba(124, 58, 237, 0.15)) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(0, 217, 255, 0.3) !important;
            font-weight: 600 !important;
            text-shadow: 0 0 10px rgba(0, 217, 255, 0.5) !important;
            padding: 12px !important;
        }
        
        .dataframe tbody td,
        .stDataFrame tbody td {
            background: rgba(255, 255, 255, 0.03) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            transition: all 0.2s ease !important;
            padding: 10px !important;
        }
        
        .dataframe tbody tr:hover td,
        .stDataFrame tbody tr:hover td {
            background: rgba(0, 217, 255, 0.1) !important;
            transform: scale(1.01) !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 10px rgba(0, 217, 255, 0.3) !important;
        }
        
        /* 데이터프레임 인덱스 스타일 */
        .dataframe .blank {
            background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1)) !important;
            border: 1px solid rgba(0, 217, 255, 0.2) !important;
        }
        
        /* 데이터프레임 셀 텍스트 강제 색상 적용 */
        .dataframe td, .dataframe th, .dataframe .col_heading,
        .stDataFrame td, .stDataFrame th {
            color: #FFFFFF !important;
        }
        
        /* 데이터프레임 컨테이너 */
        .stDataFrame {
            background: rgba(255, 255, 255, 0.02) !important;
            border-radius: 15px !important;
            padding: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        
        /* ===== 히트맵 gap 제거 (수정) ===== */
        .js-plotly-plot .heatmap {
            gap: 0 !important;
        }
        
        .js-plotly-plot .heatmapgl {
            gap: 0 !important;
        }
        
        /* Plotly 히트맵 셀 간격 제거 */
        .plotly .heatmaplayer .hm {
            stroke-width: 0 !important;
        }
        
        /* ===== 버튼 스타일 - 네온 효과 + 펄스 ===== */
        .stButton > button {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-primary) !important;
            font-weight: 600;
            transition: all 0.2s ease;
            border-radius: 8px;
            padding: 8px 20px;
            position: relative;
            overflow: hidden;
            transform: translateZ(0);
        }
        
        .stButton > button:hover {
            background: rgba(0, 217, 255, 0.1);
            border-color: var(--neon-cyan);
            color: var(--neon-cyan) !important;
            transform: translateY(-1px) translateZ(0);
            box-shadow: 0 4px 15px rgba(0, 217, 255, 0.3);
            animation: pulse 1.5s infinite;
        }
        
        /* ===== 모든 그래프 텍스트 색상 강제 적용 ===== */
        .js-plotly-plot text {
            fill: var(--text-primary) !important;
        }
        
        .js-plotly-plot .xtick text,
        .js-plotly-plot .ytick text,
        .js-plotly-plot .gtitle {
            fill: var(--text-primary) !important;
        }
        
        /* ===== 탭 스타일 - 네온 언더라인 ===== */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 6px;
            gap: 8px;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(
                135deg, 
                rgba(0, 217, 255, 0.15) 0%, 
                rgba(124, 58, 237, 0.15) 100%
            ) !important;
            color: var(--text-primary) !important;
            border: 1px solid rgba(0, 217, 255, 0.3) !important;
            box-shadow: 0 0 15px rgba(0, 217, 255, 0.2) !important;
            position: relative;
        }
        
        .stTabs [aria-selected="true"]::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 10%;
            right: 10%;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { 
                left: 50%;
                right: 50%;
            }
            to {
                left: 10%;
                right: 10%;
            }
        }
        
        /* ===== 메트릭 카드 - 네온 글로우 ===== */
        .metric-value {
            font-size: 26px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--neon-cyan) 0%, var(--neon-purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 10px 0;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
            animation: neonGlow 3s ease-in-out infinite;
        }
        
        /* ===== 효율성 카드 - 네온 펄스 ===== */
        .efficiency-card {
            background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(124, 58, 237, 0.1));
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 217, 255, 0.3);
            color: var(--text-primary) !important;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            margin: 5px;
            box-shadow: 
                0 0 20px rgba(0, 217, 255, 0.3),
                inset 0 0 20px rgba(0, 217, 255, 0.05);
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .efficiency-card:hover {
            transform: scale(1.05);
            box-shadow: 
                0 0 30px rgba(0, 217, 255, 0.5),
                inset 0 0 30px rgba(0, 217, 255, 0.1);
        }
        
        /* ===== 사이드바 - 다크 테마 + 텍스트 색상 강제 ===== */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10, 11, 30, 0.98) 0%, rgba(16, 19, 50, 0.98) 100%);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        /* 사이드바 모든 텍스트 흰색 강제 */
        section[data-testid="stSidebar"] * {
            color: var(--text-primary) !important;
        }
        
        /* 사이드바 입력 필드 특별 처리 */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {
            background: rgba(255, 255, 255, 0.08) !important;
            color: #FFFFFF !important;
        }
        
        /* ===== 스크롤바 - 네온 스타일 ===== */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(
                180deg,
                rgba(0, 217, 255, 0.3) 0%,
                rgba(124, 58, 237, 0.3) 100%
            );
            border-radius: 4px;
            transition: all 0.3s ease;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(
                180deg,
                rgba(0, 217, 255, 0.5) 0%,
                rgba(124, 58, 237, 0.5) 100%
            );
            box-shadow: 0 0 5px rgba(0, 217, 255, 0.5);
        }
        
        /* ===== 성능 최적화 클래스 ===== */
        .gpu-accelerated {
            transform: translateZ(0);
            will-change: transform;
            backface-visibility: hidden;
        }
        
        /* ===== 반응형 조정 ===== */
        @media (max-width: 768px) {
            .main-title {
                font-size: 32px;
            }
            
            .section-card, .metric-card {
                padding: 15px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# 호버 템플릿 표준화
# ============================================================================

def get_standard_hover_template(chart_type='default'):
    """차트 타입별 표준 호버 템플릿"""
    return HoverTemplates.get_template(chart_type.lower())