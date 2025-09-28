"""
dashboard_utils.py - 대시보드 공통 유틸리티 함수 (개선 버전)
Version: 3.0.0
Created: 2025-02-03

모든 대시보드 모듈에서 공통으로 사용하는 유틸리티 함수들
Period 타입 처리 강화, 포맷팅 함수 추가, DataFormatter 클래스 추가
"""

import pandas as pd
import numpy as np
import streamlit as st
import hashlib
import json
import os
import traceback
from datetime import datetime, timedelta
import contextlib
from typing import Any, Dict, List, Optional, Tuple, Union

# ============================================================================
# DataFormatter 클래스 추가 (dashboard_precision_analysis.py 호환용)
# ============================================================================

class DataFormatter:
    """데이터 포맷팅 클래스"""
    
    def __init__(self):
        self.currency_unit = "원"
    
    def format_money(self, value: Union[int, float, str, None], unit: str = "원") -> str:
        """
        금액을 포맷팅 (억, 천만, 만 단위)
        
        Parameters:
        -----------
        value : int, float, str, or None
            포맷팅할 금액 (문자열인 경우 %{y} 같은 plotly 변수 처리)
        unit : str
            단위 (기본값: "원", "억" 지정 가능)
            
        Returns:
        --------
        str : 포맷팅된 금액 문자열
        """
        # Plotly 변수 처리
        if isinstance(value, str) and '%{' in value:
            return value  # Plotly가 나중에 처리하도록 그대로 반환
        
        if value is None or pd.isna(value):
            return "0원"
        
        try:
            value = float(value)
            if unit == "억":
                # 모든 값을 억 단위로 표시 (소수점 3자리)
                return f"{value/1e8:.3f}억"
            else:  # 기본 원 단위
                if value >= 1e8:
                    return f"{value/1e8:.1f}억원"
                elif value >= 1e7:
                    return f"{value/1e7:.0f}천만원"
                elif value >= 1e4:
                    return f"{value/1e4:.0f}만원"
                else:
                    return f"{int(value):,}원"
        except (ValueError, TypeError):
            return "0원"
    
    def format_money_short(self, value: Union[int, float, None]) -> str:
        """
        금액을 짧게 포맷팅 (억, 천만, 만)
        
        Parameters:
        -----------
        value : int or float or None
            포맷팅할 금액
            
        Returns:
        --------
        str : 포맷팅된 짧은 금액 문자열
        """
        if value is None or pd.isna(value):
            return "0"
        
        try:
            value = float(value)
            if value >= 1e8:
                return f"{value/1e8:.1f}억"
            elif value >= 1e7:
                return f"{value/1e7:.0f}천만"
            elif value >= 1e4:
                return f"{value/1e4:.0f}만"
            else:
                return f"{int(value):,}"
        except (ValueError, TypeError):
            return "0"
    
    def format_number(self, value: Union[int, float, None], decimal: int = 0) -> str:
        """
        숫자를 포맷팅
        
        Parameters:
        -----------
        value : int or float or None
            포맷팅할 숫자
        decimal : int
            소수점 자리수
            
        Returns:
        --------
        str : 포맷팅된 숫자 문자열
        """
        if value is None or pd.isna(value):
            return "0"
        
        try:
            if decimal == 0:
                return f"{int(value):,}"
            else:
                return f"{value:,.{decimal}f}"
        except (ValueError, TypeError):
            return "0"
    
    def format_percent(self, value: Union[int, float, None], decimal: int = 1) -> str:
        """
        퍼센트 포맷팅
        
        Parameters:
        -----------
        value : int or float or None
            포맷팅할 퍼센트 값
        decimal : int
            소수점 자리수
            
        Returns:
        --------
        str : 포맷팅된 퍼센트 문자열
        """
        if value is None or pd.isna(value):
            return "0%"
        
        try:
            return f"{value:.{decimal}f}%"
        except (ValueError, TypeError):
            return "0%"

# ============================================================================
# DataFrame JSON 변환 유틸리티 (Period 타입 처리 강화)
# ============================================================================

def safe_to_json(df: pd.DataFrame) -> str:
    """
    DataFrame을 안전하게 JSON으로 변환 - Period 타입 처리 강화
    
    Parameters:
    -----------
    df : pandas.DataFrame
        변환할 데이터프레임
        
    Returns:
    --------
    str : JSON 문자열
    """
    if df is None or len(df) == 0:
        return pd.DataFrame().to_json()
    
    # DataFrame 복사본 생성
    df_copy = df.copy()
    
    # Period 타입 컬럼을 문자열로 변환
    for col in df_copy.columns:
        try:
            # Period 타입 체크 및 변환
            if pd.api.types.is_period_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].astype(str)
            # Period가 object로 저장된 경우도 처리
            elif df_copy[col].dtype == 'object':
                # 첫 번째 non-null 값 확인
                first_val = df_copy[col].dropna().iloc[0] if len(df_copy[col].dropna()) > 0 else None
                if first_val and hasattr(first_val, 'strftime'):
                    df_copy[col] = df_copy[col].apply(lambda x: str(x) if pd.notna(x) else None)
            # 특정 컬럼명 체크 (month, week 등)
            elif col in ['month', 'week', 'quarter', 'year_month']:
                try:
                    df_copy[col] = df_copy[col].astype(str)
                except:
                    pass
        except Exception as e:
            # 개별 컬럼 변환 실패 시 로깅
            if st.session_state.get('debug_mode', False):
                st.warning(f"컬럼 '{col}' 변환 경고: {str(e)}")
            # 강제 문자열 변환
            df_copy[col] = df_copy[col].astype(str)
    
    # datetime 컬럼도 문자열로 변환
    datetime_cols = df_copy.select_dtypes(include=['datetime64']).columns
    for col in datetime_cols:
        df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # JSON으로 변환
    try:
        return df_copy.to_json(date_format='iso', orient='records')
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.error(f"JSON 변환 오류: {str(e)}")
        # 최후의 수단: 모든 컬럼을 문자열로 변환
        for col in df_copy.columns:
            df_copy[col] = df_copy[col].astype(str)
        return df_copy.to_json(orient='records')


def json_to_df(json_str: str) -> pd.DataFrame:
    """
    JSON 문자열을 DataFrame으로 변환
    
    Parameters:
    -----------
    json_str : str
        JSON 문자열
        
    Returns:
    --------
    pandas.DataFrame
    """
    if not json_str:
        return pd.DataFrame()
    
    try:
        df = pd.read_json(json_str, orient='records')
        
        # date 컬럼이 있으면 datetime으로 변환
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.error(f"JSON 파싱 오류: {str(e)}")
        return pd.DataFrame()

# ============================================================================
# 캐시 키 생성 유틸리티
# ============================================================================

def generate_cache_key(**kwargs) -> str:
    """
    캐시 키 생성 - 파라미터 조합의 고유 해시 생성
    
    Parameters:
    -----------
    **kwargs : dict
        캐시 키 생성에 사용할 파라미터들
        
    Returns:
    --------
    str : MD5 해시 문자열
    """
    # None 값 처리
    cleaned_kwargs = {k: str(v) if v is not None else 'None' for k, v in kwargs.items()}
    sorted_items = sorted(cleaned_kwargs.items())
    key_string = json.dumps(sorted_items, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()

# ============================================================================
# 숫자 포맷팅 유틸리티 (개선 버전)
# ============================================================================

def format_short_number(value: Union[int, float, None]) -> str:
    """
    숫자를 약자로 변환 (억, 천만, 만)
    
    Parameters:
    -----------
    value : int or float or None
        포맷팅할 숫자
        
    Returns:
    --------
    str : 포맷팅된 문자열
    """
    if value is None or pd.isna(value):
        return "N/A"
    
    try:
        value = float(value)
        if value >= 1e8:
            return f"{value/1e8:.1f}억"
        elif value >= 1e7:
            return f"{value/1e7:.1f}천만"
        elif value >= 1e4:
            return f"{value/1e4:.0f}만"
        else:
            return f"{int(value):,}"
    except (ValueError, TypeError):
        return "N/A"

def format_money(value: Union[int, float, str, None], unit: str = "원") -> str:
    """
    금액을 포맷팅 (억, 천만, 만 단위)
    
    Parameters:
    -----------
    value : int, float, str, or None
        포맷팅할 금액
    unit : str
        단위 (기본값: "원", "억" 지정 가능)
        
    Returns:
    --------
    str : 포맷팅된 금액 문자열
    """
    # Plotly 변수 처리
    if isinstance(value, str) and '%{' in value:
        return value  # Plotly가 나중에 처리하도록 그대로 반환
        
    if value is None or pd.isna(value):
        return "0원"
    
    try:
        value = float(value)
        if unit == "억":
            if value >= 1e8:
                return f"{value/1e8:.2f}억"
            elif value >= 1e7:
                return f"{value/1e7:.1f}천만"
            else:
                return f"{value/1e4:.0f}만"
        else:  # 기본 원 단위
            if value >= 1e8:
                return f"{value/1e8:.1f}억원"
            elif value >= 1e7:
                return f"{value/1e7:.0f}천만원"
            elif value >= 1e4:
                return f"{value/1e4:.0f}만원"
            else:
                return f"{int(value):,}원"
    except (ValueError, TypeError):
        return "0원"

def format_money_short(value: Union[int, float, None]) -> str:
    """
    금액을 짧게 포맷팅 (억, 천만, 만)
    
    Parameters:
    -----------
    value : int or float or None
        포맷팅할 금액
        
    Returns:
    --------
    str : 포맷팅된 짧은 금액 문자열
    """
    if value is None or pd.isna(value):
        return "0"
    
    try:
        value = float(value)
        if value >= 1e8:
            return f"{value/1e8:.1f}억"
        elif value >= 1e7:
            return f"{value/1e7:.0f}천만"
        elif value >= 1e4:
            return f"{value/1e4:.0f}만"
        else:
            return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"

# ============================================================================
# 날짜 관련 유틸리티
# ============================================================================

def get_date_range(df: pd.DataFrame) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    DataFrame에서 날짜 범위 추출
    
    Parameters:
    -----------
    df : pandas.DataFrame
        날짜 컬럼이 있는 데이터프레임
        
    Returns:
    --------
    tuple : (min_date, max_date)
    """
    if df is None or len(df) == 0 or 'date' not in df.columns:
        return None, None
    
    try:
        min_date = df['date'].min()
        max_date = df['date'].max()
        
        # datetime이면 date로 변환
        if hasattr(min_date, 'date'):
            min_date = min_date.date()
        if hasattr(max_date, 'date'):
            max_date = max_date.date()
        
        return min_date, max_date
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.warning(f"날짜 범위 추출 실패: {str(e)}")
        return None, None


def get_week_dates(date: Union[datetime, pd.Timestamp]) -> Tuple[datetime, datetime]:
    """
    주어진 날짜가 속한 주의 시작일과 종료일 반환
    
    Parameters:
    -----------
    date : datetime or pd.Timestamp
        기준 날짜
        
    Returns:
    --------
    tuple : (week_start, week_end)
    """
    if isinstance(date, datetime):
        date = date.date()
    elif isinstance(date, pd.Timestamp):
        date = date.date()
    
    # 월요일을 주의 시작으로
    week_start = date - timedelta(days=date.weekday())
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end

# ============================================================================
# 로딩 메시지 유틸리티 (contextmanager 추가)
# ============================================================================

from contextlib import contextmanager

@contextlib.contextmanager
def show_loading_message(message: str, type: str = "info"):
    """
    로딩 메시지 표시 (context manager)
    
    Parameters:
    -----------
    message : str
        표시할 메시지
    type : str
        메시지 타입 ('info', 'success', 'warning', 'error')
        
    Usage:
    ------
    with show_loading_message('데이터 로딩 중...'):
        # 작업 수행
        pass
    """
    
    # 중앙 로딩 스타일 주입
    style_placeholder = st.empty()
    style_placeholder.markdown("""
    <style>
    div.stSpinner {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 9999;
        background: rgba(10, 11, 30, 0.95);
        padding: 30px 50px;
        border-radius: 15px;
        border: 2px solid #00D9FF;
        backdrop-filter: blur(10px);
        box-shadow: 0 0 30px rgba(0, 217, 255, 0.5);
    }
    div.stSpinner > div {
        color: #00D9FF !important;
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # spinner context 사용
    with st.spinner(f"⏳ {message}"):
        yield
    
    # 스타일 정리
    style_placeholder.empty()

def show_loading_message_legacy(message: str, type: str = "info"):
    """
    로딩 메시지 표시 (context manager)
    
    Parameters:
    -----------
    message : str
        표시할 메시지
    type : str
        메시지 타입 ('info', 'success', 'warning', 'error')
        
    Usage:
    ------
    with show_loading_message('데이터 로딩 중...'):
        # 작업 수행
        pass
    """
    if type == "info":
        placeholder = st.info(f"⏳ {message}")
    elif type == "success":
        placeholder = st.success(f"✅ {message}")
    elif type == "warning":
        placeholder = st.warning(f"⚠️ {message}")
    elif type == "error":
        placeholder = st.error(f"❌ {message}")
    else:
        placeholder = st.empty()
        placeholder.markdown(f'<div class="loading-message">⏳ {message}</div>', 
                           unsafe_allow_html=True)
    
    try:
        yield placeholder
    finally:
        placeholder.empty()

# ============================================================================
# 데이터 검증 유틸리티 (개선)
# ============================================================================

def validate_dataframe(df: pd.DataFrame, required_columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    DataFrame 유효성 검사 (상세 검증)
    
    Parameters:
    -----------
    df : pandas.DataFrame
        검증할 데이터프레임
    required_columns : list
        필수 컬럼 리스트
        
    Returns:
    --------
    dict : 검증 결과
    """
    result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    # 빈 DataFrame 체크
    if df is None:
        result['is_valid'] = False
        result['errors'].append("DataFrame이 None입니다")
        return result
    
    if len(df) == 0:
        result['is_valid'] = False
        result['errors'].append("데이터가 비어있습니다")
        return result
    
    # 기본 정보 수집
    result['info']['rows'] = len(df)
    result['info']['columns'] = len(df.columns)
    
    # 필수 컬럼 체크
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            result['is_valid'] = False
            result['errors'].append(f"필수 컬럼 누락: {', '.join(missing_cols)}")
    
    # 데이터 크기 체크
    if len(df) < 10:
        result['warnings'].append(f"데이터가 너무 적습니다 ({len(df)}건)")
    
    # 날짜 범위 체크
    if 'date' in df.columns:
        try:
            date_range = (df['date'].max() - df['date'].min()).days
            result['info']['date_range'] = date_range
            if date_range < 7:
                result['warnings'].append(f"데이터 기간이 짧습니다 ({date_range}일)")
        except:
            result['warnings'].append("날짜 컬럼 처리 오류")
    
    # 매출 데이터 체크
    if 'revenue' in df.columns:
        zero_count = len(df[df['revenue'] == 0])
        zero_ratio = (zero_count / len(df)) * 100
        result['info']['zero_revenue_ratio'] = zero_ratio
        if zero_ratio > 50:
            result['warnings'].append(f"매출 0원 비율이 높습니다 ({zero_ratio:.1f}%)")
    
    return result

# ============================================================================
# 색상 관련 유틸리티
# ============================================================================

def get_gradient_colors(n: int, start_color: str = '#667EEA', end_color: str = '#764BA2') -> List[str]:
    """
    그라디언트 색상 리스트 생성
    
    Parameters:
    -----------
    n : int
        생성할 색상 개수
    start_color : str
        시작 색상 (hex)
    end_color : str
        종료 색상 (hex)
        
    Returns:
    --------
    list : 색상 리스트
    """
    if n <= 1:
        return [start_color]
    
    # Hex to RGB
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # RGB to Hex
    def rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    
    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)
    
    colors = []
    for i in range(n):
        ratio = i / (n - 1)
        r = start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio
        g = start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio
        b = start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio
        colors.append(rgb_to_hex((r, g, b)))
    
    return colors

# ============================================================================
# 세션 상태 관리 유틸리티 (개선)
# ============================================================================

def init_session_state(**defaults):
    """
    세션 상태 초기화 (디버그 모드 포함)
    
    Parameters:
    -----------
    **defaults : dict
        기본값 딕셔너리
    """
    # 디버그 모드 기본값 추가
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    
    # 에러 로그 초기화
    if 'error_log' not in st.session_state:
        st.session_state.error_log = []
    
    # 기존 기본값 설정
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_session_value(key: str, default: Any = None) -> Any:
    """
    세션 상태 값 가져오기
    
    Parameters:
    -----------
    key : str
        세션 키
    default : any
        기본값
        
    Returns:
    --------
    any : 세션 값 또는 기본값
    """
    return st.session_state.get(key, default)


def set_session_value(key: str, value: Any) -> None:
    """
    세션 상태 값 설정
    
    Parameters:
    -----------
    key : str
        세션 키
    value : any
        설정할 값
    """
    st.session_state[key] = value

# ============================================================================
# 파일 및 데이터베이스 체크 유틸리티 (개선)
# ============================================================================

def check_database_exists(db_path: str = "schedule.db") -> bool:
    """
    데이터베이스 파일 존재 여부 확인 (상세 정보 포함)
    
    Parameters:
    -----------
    db_path : str
        데이터베이스 파일 경로
        
    Returns:
    --------
    bool : 존재 여부
    """
    if not os.path.exists(db_path):
        return False
    
    # 파일 크기 체크
    file_size = os.path.getsize(db_path)
    if file_size == 0:
        if st.session_state.get('debug_mode', False):
            st.warning(f"데이터베이스 파일이 비어있습니다: {db_path}")
        return False
    
    # 데이터베이스 연결 테스트
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        
        if table_count == 0:
            if st.session_state.get('debug_mode', False):
                st.warning("데이터베이스에 테이블이 없습니다")
            return False
        
        return True
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.error(f"데이터베이스 연결 테스트 실패: {str(e)}")
        return False

# ============================================================================
# 텍스트 처리 유틸리티
# ============================================================================

def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    텍스트 잘라내기
    
    Parameters:
    -----------
    text : str
        원본 텍스트
    max_length : int
        최대 길이
    suffix : str
        잘린 부분 표시
        
    Returns:
    --------
    str : 처리된 텍스트
    """
    if not text:
        return ""
    
    text = str(text)  # 문자열로 변환
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + suffix


def safe_string(value: Any, default: str = "") -> str:
    """
    안전한 문자열 변환
    
    Parameters:
    -----------
    value : any
        변환할 값
    default : str
        기본값
        
    Returns:
    --------
    str : 문자열
    """
    if value is None or pd.isna(value):
        return default
    
    try:
        return str(value)
    except:
        return default

# ============================================================================
# 에러 처리 유틸리티 (신규)
# ============================================================================

def log_error(error: Exception, context: str = "") -> None:
    """
    에러 로깅 (세션 상태에 저장)
    
    Parameters:
    -----------
    error : Exception
        발생한 에러
    context : str
        에러 발생 컨텍스트
    """
    error_info = {
        'time': datetime.now().isoformat(),
        'context': context,
        'error': str(error),
        'traceback': traceback.format_exc()
    }
    
    if 'error_log' not in st.session_state:
        st.session_state.error_log = []
    
    st.session_state.error_log.append(error_info)
    
    # 디버그 모드일 때 상세 정보 표시
    if st.session_state.get('debug_mode', False):
        st.error(f"🐛 에러 발생: {context}")
        st.code(traceback.format_exc())


def show_debug_panel():
    """
    디버그 패널 표시 (사이드바에서 호출)
    """
    if st.sidebar.checkbox("🐛 디버그 모드", value=st.session_state.get('debug_mode', False)):
        st.session_state.debug_mode = True
        
        st.sidebar.markdown("### 📊 디버그 정보")
        
        # 세션 상태 정보
        with st.sidebar.expander("세션 상태", expanded=False):
            session_keys = list(st.session_state.keys())
            for key in sorted(session_keys):
                if key not in ['error_log', 'data']:  # 큰 데이터 제외
                    value = st.session_state[key]
                    st.write(f"**{key}**: {truncate_text(str(value), 50)}")
        
        # 에러 로그
        if 'error_log' in st.session_state and st.session_state.error_log:
            with st.sidebar.expander(f"에러 로그 ({len(st.session_state.error_log)})", expanded=False):
                for i, error in enumerate(reversed(st.session_state.error_log[-5:])):  # 최근 5개
                    st.write(f"**[{i+1}] {error['time']}**")
                    st.write(f"Context: {error['context']}")
                    st.write(f"Error: {error['error']}")
        
        # 클리어 버튼
        if st.sidebar.button("🗑️ 에러 로그 삭제"):
            st.session_state.error_log = []
            st.rerun()
    else:
        st.session_state.debug_mode = False

# ============================================================================
# 성능 모니터링 유틸리티 (신규)
# ============================================================================

import time
from functools import wraps

def measure_performance(func):
    """
    함수 실행 시간 측정 데코레이터
    
    Usage:
    ------
    @measure_performance
    def my_function():
        pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not st.session_state.get('debug_mode', False):
            return func(*args, **kwargs)
        
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        if elapsed_time > 1.0:  # 1초 이상 걸린 경우만 표시
            st.sidebar.warning(f"⚠️ {func.__name__}: {elapsed_time:.2f}초")
        
        return result
    return wrapper

# ============================================================================
# 데이터 샘플링 유틸리티 (신규)
# ============================================================================

def sample_dataframe(df: pd.DataFrame, max_rows: int = 1000, strategy: str = 'random') -> pd.DataFrame:
    """
    큰 DataFrame을 샘플링
    
    Parameters:
    -----------
    df : pd.DataFrame
        원본 데이터프레임
    max_rows : int
        최대 행 수
    strategy : str
        샘플링 전략 ('random', 'top', 'stratified')
        
    Returns:
    --------
    pd.DataFrame : 샘플링된 데이터프레임
    """
    if len(df) <= max_rows:
        return df
    
    if strategy == 'random':
        return df.sample(n=max_rows, random_state=42)
    elif strategy == 'top':
        return df.nlargest(max_rows, 'revenue' if 'revenue' in df.columns else df.columns[0])
    elif strategy == 'stratified' and 'platform' in df.columns:
        # 플랫폼별 비율 유지하며 샘플링
        sample_ratio = max_rows / len(df)
        return df.groupby('platform', group_keys=False).apply(
            lambda x: x.sample(n=max(1, int(len(x) * sample_ratio)), random_state=42)
        )
    else:
        return df.head(max_rows)

# ============================================================================
# 숫자 변환 관련 유틸리티 (신규 추가 - 2025-02-03)
# ============================================================================

def safe_numeric_conversion(df, columns=None):
    """
    안전한 숫자 변환 함수 - 모든 문자열/숫자 타입 혼재 문제 해결
    
    Parameters:
    -----------
    df : pd.DataFrame
        변환할 데이터프레임
    columns : list
        변환할 컬럼 리스트 (None이면 기본 컬럼 사용)
        
    Returns:
    --------
    pd.DataFrame : 숫자로 변환된 데이터프레임
    """
    if columns is None:
        columns = ['revenue', 'units_sold', 'cost', 'total_cost', 
                  'real_profit', 'model_cost', 'roi', 'roi_calculated', 
                  'product_count']
    
    df = df.copy()
    
    for col in columns:
        if col in df.columns:
            # 1. 문자열 정리
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '')
                df[col] = df[col].str.replace('원', '')
                df[col] = df[col].str.replace('₩', '')
                df[col] = df[col].str.replace('%', '')
                df[col] = df[col].str.replace('억', '')
                df[col] = df[col].str.replace('만', '')
                df[col] = df[col].str.replace('천', '')
                df[col] = df[col].str.strip()
            
            # 2. 숫자 변환
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 3. NaN 처리
            df[col] = df[col].fillna(0)
            
            # 4. 무한대 처리
            df[col] = df[col].replace([np.inf, -np.inf], 0)
    
    return df

def validate_numeric_columns(df):
    """
    숫자 컬럼 검증 및 변환
    
    Parameters:
    -----------
    df : pd.DataFrame
        검증할 데이터프레임
        
    Returns:
    --------
    pd.DataFrame : 검증 및 변환된 데이터프레임
    """
    numeric_cols = ['revenue', 'cost', 'units_sold', 'total_cost', 'model_cost', 
                   'real_profit', 'roi', 'roi_calculated', 'product_count']
    
    for col in numeric_cols:
        if col in df.columns:
            # 타입 체크
            if df[col].dtype not in ['int64', 'float64', 'float32', 'int32']:
                if st.session_state.get('debug_mode', False):
                    st.warning(f"Warning: {col} is {df[col].dtype}, converting to numeric")
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

# ============================================================================
# safe_abs 함수 추가 (dashboard_precision_analysis.py 호환용)
# ============================================================================

def safe_abs(value):
    """
    안전한 절대값 계산 함수
    
    Parameters:
    -----------
    value : any
        절대값을 계산할 값
        
    Returns:
    --------
    float or int : 절대값
    """
    if value is None or pd.isna(value):
        return 0
    
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0

# 기본 DataFormatter 인스턴스 생성 (전역 사용)
default_formatter = DataFormatter()