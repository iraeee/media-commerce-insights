"""
기존 DB의 모든 레코드에 대해 평일/주말 구분하여 cost와 ROI를 재계산하는 스크립트
엑셀 구조 확정:
- 평일: 3~18행 (현대홈쇼핑부터 롯데원티비까지)
- 주말: 23~38행 (현대홈쇼핑부터 롯데원티비까지)
- 시간: B~Y열 (0~23시, B=0시, M=11시)
"""

import sqlite3
import pandas as pd
from datetime import datetime

# 전환율 및 마진율 설정 - ROI 계산법 변경 (2025-02-03)
CONVERSION_RATE = 0.75      # 전환률 75%
PRODUCT_COST_RATE = 0.13    # 제품 원가율 13%
COMMISSION_RATE = 0.10      # 판매 수수료율 10%
REAL_MARGIN_RATE = (1 - COMMISSION_RATE - PRODUCT_COST_RATE) * CONVERSION_RATE  # 0.5775 (57.75%)

# 생방송 채널 정의 (모델비 계산용)
LIVE_CHANNELS = {
    '현대홈쇼핑', 'GS홈쇼핑', '롯데홈쇼핑', 'CJ온스타일', 
    '홈앤쇼핑', 'NS홈쇼핑', '공영쇼핑'
}

# 모델비 설정
MODEL_COST_LIVE = 10400000
MODEL_COST_NON_LIVE = 2000000

def load_cost_from_excel(path="방송사별 방송정액비.xlsx"):
    """엑셀에서 방송사별 시간대별 비용 로드 (평일/주말 구분)"""
    try:
        # 엑셀 파일 읽기 - 헤더 없이
        df = pd.read_excel(path, header=None)
        
        print(f"엑셀 크기: {df.shape}")
        
        weekday_costs = {}
        weekend_costs = {}
        
        # 평일 방송사 리스트 (Excel 3~18행 = pandas index 2~17)
        weekday_platforms = [
            (2, "현대홈쇼핑"),
            (3, "GS홈쇼핑"),      # gs홈쇼핑을 GS홈쇼핑으로 통일
            (4, "롯데홈쇼핑"),
            (5, "CJ온스타일"),
            (6, "홈앤쇼핑"),
            (7, "NS홈쇼핑"),      # ns홈쇼핑을 NS홈쇼핑으로 통일
            (8, "공영쇼핑"),
            (9, "GS홈쇼핑 마이샵"), # gs홈쇼핑 마이샵을 GS홈쇼핑 마이샵으로 통일
            (10, "CJ온스타일 플러스"),
            (11, "현대홈쇼핑 플러스샵"),
            (12, "SK스토아"),      # sk스토아를 SK스토아로 통일
            (13, "신세계쇼핑"),
            (14, "KT알파쇼핑"),    # kt알파쇼핑을 KT알파쇼핑으로 통일
            (15, "NS홈쇼핑 샵플러스"),
            (16, "쇼핑엔티"),
            (17, "롯데원티비")
        ]
        
        # 주말 방송사 리스트 (Excel 23~38행 = pandas index 22~37)
        weekend_platforms = [
            (22, "현대홈쇼핑"),
            (23, "GS홈쇼핑"),
            (24, "롯데홈쇼핑"),
            (25, "CJ온스타일"),
            (26, "홈앤쇼핑"),
            (27, "NS홈쇼핑"),
            (28, "공영쇼핑"),
            (29, "GS홈쇼핑 마이샵"),
            (30, "CJ온스타일 플러스"),
            (31, "현대홈쇼핑 플러스샵"),
            (32, "SK스토아"),
            (33, "신세계쇼핑"),
            (34, "KT알파쇼핑"),
            (35, "NS홈쇼핑 샵플러스"),
            (36, "쇼핑엔티"),
            (37, "롯데원티비")
        ]
        
        print("\n[평일 데이터 로드]")
        for idx, platform in weekday_platforms:
            # 엑셀에서 실제 방송사명 읽기
            excel_platform = str(df.iloc[idx, 0]).strip() if pd.notna(df.iloc[idx, 0]) else ""
            
            weekday_hourly = {}
            for hour in range(24):
                try:
                    col_idx = hour + 1  # B열(index 1)이 0시, M열(index 12)이 11시
                    val = df.iloc[idx, col_idx]
                    
                    if pd.notnull(val):
                        if isinstance(val, (int, float)):
                            cost = int(val)
                        else:
                            val_str = str(val).replace(',', '').replace('원', '').strip()
                            if val_str.isdigit():
                                cost = int(val_str)
                            else:
                                cost = 0
                    else:
                        cost = 0
                except:
                    cost = 0
                weekday_hourly[hour] = cost
            
            # 통일된 이름으로 저장
            weekday_costs[platform] = weekday_hourly
            
            # 원본 이름(소문자)으로도 저장
            if excel_platform:
                weekday_costs[excel_platform] = weekday_hourly
                weekday_costs[excel_platform.lower()] = weekday_hourly
                weekday_costs[excel_platform.upper()] = weekday_hourly
            
            # 추가 변형 처리
            if "GS홈쇼핑" in platform and "마이샵" not in platform:
                weekday_costs["gs홈쇼핑"] = weekday_hourly
                weekday_costs["Gs홈쇼핑"] = weekday_hourly
            elif "GS홈쇼핑 마이샵" in platform:
                weekday_costs["gs홈쇼핑 마이샵"] = weekday_hourly
                weekday_costs["GS홈쇼핑마이샵"] = weekday_hourly
                weekday_costs["gs홈쇼핑마이샵"] = weekday_hourly
            
            if hour == 11:  # 11시 값만 출력
                print(f"  평일 [{idx:2d}행] {platform:20s}: 11시={weekday_hourly[11]:,}원")
        
        print("\n[주말 데이터 로드]")
        for idx, platform in weekend_platforms:
            # 엑셀에서 실제 방송사명 읽기
            excel_platform = str(df.iloc[idx, 0]).strip() if pd.notna(df.iloc[idx, 0]) else ""
            
            weekend_hourly = {}
            for hour in range(24):
                try:
                    col_idx = hour + 1  # B열(index 1)이 0시, M열(index 12)이 11시
                    val = df.iloc[idx, col_idx]
                    
                    if pd.notnull(val):
                        if isinstance(val, (int, float)):
                            cost = int(val)
                        else:
                            val_str = str(val).replace(',', '').replace('원', '').strip()
                            if val_str.isdigit():
                                cost = int(val_str)
                            else:
                                cost = 0
                    else:
                        cost = 0
                except:
                    cost = 0
                weekend_hourly[hour] = cost
            
            # 통일된 이름으로 저장
            weekend_costs[platform] = weekend_hourly
            
            # 원본 이름(소문자)으로도 저장
            if excel_platform:
                weekend_costs[excel_platform] = weekend_hourly
                weekend_costs[excel_platform.lower()] = weekend_hourly
                weekend_costs[excel_platform.upper()] = weekend_hourly
            
            # 추가 변형 처리
            if "GS홈쇼핑" in platform and "마이샵" not in platform:
                weekend_costs["gs홈쇼핑"] = weekend_hourly
                weekend_costs["Gs홈쇼핑"] = weekend_hourly
            elif "GS홈쇼핑 마이샵" in platform:
                weekend_costs["gs홈쇼핑 마이샵"] = weekend_hourly
                weekend_costs["GS홈쇼핑마이샵"] = weekend_hourly
                weekend_costs["gs홈쇼핑마이샵"] = weekend_hourly
            
            if hour == 11:  # 11시 값만 출력
                print(f"  주말 [{idx:2d}행] {platform:20s}: 11시={weekend_hourly[11]:,}원")
        
        print(f"\n✅ 평일 {len(weekday_platforms)}개, 주말 {len(weekend_platforms)}개 방송사 비용 로드 완료")
        
        # 검증 출력
        print("\n[검증] 11시 비용 확인:")
        print(f"  평일 GS홈쇼핑: {weekday_costs.get('GS홈쇼핑', {}).get(11, 0):,}원 (45,000,000원이어야 함)")
        print(f"  평일 GS홈쇼핑 마이샵: {weekday_costs.get('GS홈쇼핑 마이샵', {}).get(11, 0):,}원 (20,000,000원이어야 함)")
        print(f"  주말 GS홈쇼핑: {weekend_costs.get('GS홈쇼핑', {}).get(11, 0):,}원 (60,000,000원이어야 함)")
        print(f"  주말 GS홈쇼핑 마이샵: {weekend_costs.get('GS홈쇼핑 마이샵', {}).get(11, 0):,}원 (20,000,000원이어야 함)")
        
        return {
            'weekday': weekday_costs,
            'weekend': weekend_costs
        }
    except Exception as e:
        print(f"❌ 엑셀 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_cost_for_platform(platform_name, hour, cost_table):
    """방송사와 시간대로 비용 찾기 (대소문자 무시)"""
    if not cost_table:
        return 0
    
    # 1. 정확한 매칭
    if platform_name in cost_table:
        return cost_table[platform_name].get(hour, 0)
    
    # 2. 대소문자 변형 시도
    variations = [
        platform_name,
        platform_name.lower(),
        platform_name.upper(),
        platform_name.replace(" ", ""),
        platform_name.replace(" ", "").lower(),
    ]
    
    for variant in variations:
        if variant in cost_table:
            return cost_table[variant].get(hour, 0)
    
    # 3. 부분 매칭 (GS, NS 등)
    platform_lower = platform_name.lower()
    for key in cost_table.keys():
        if key.lower() == platform_lower:
            return cost_table[key].get(hour, 0)
    
    return 0

def calculate_roi(revenue, cost, platform):
    """실질 ROI 계산 - 새로운 계산법"""
    if cost <= 0:
        return 0
    
    # 모델비 계산
    is_live = platform in LIVE_CHANNELS
    model_cost = MODEL_COST_LIVE if is_live else MODEL_COST_NON_LIVE
    total_cost = cost + model_cost
    
    # 실질 수익 계산 - 새로운 계산법
    real_profit = (revenue * REAL_MARGIN_RATE) - total_cost
    
    # ROI 계산 (%)
    roi = (real_profit / total_cost) * 100
    
    return roi

def update_all_costs(db_path="schedule.db"):
    """모든 레코드의 cost와 ROI 업데이트 (평일/주말 구분, 새로운 ROI 계산법 적용)"""
    
    # 엑셀에서 비용 정보 로드
    cost_table = load_cost_from_excel()
    
    if not cost_table:
        print("❌ 비용 테이블 로드 실패")
        return
    
    # DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 모든 레코드 가져오기
    cursor.execute("""
        SELECT id, date, platform, time, revenue 
        FROM schedule
        ORDER BY date DESC, time
    """)
    
    records = cursor.fetchall()
    print(f"\n📊 총 {len(records)}개 레코드 업데이트 시작...")
    print(f"ℹ️ 실질 마진율: {REAL_MARGIN_RATE:.2%} 적용")
    
    updated_count = 0
    gs_samples = []  # GS 관련 샘플만 저장
    weekday_count = 0
    weekend_count = 0
    zero_cost_count = 0
    
    for record in records:
        record_id, date_str, platform, time_str, revenue = record
        
        # 날짜를 datetime으로 변환
        try:
            date_obj = pd.to_datetime(date_str)
            weekday = date_obj.weekday()  # 0=월, 1=화, ... 5=토, 6=일
            is_weekend = weekday >= 5  # 토(5), 일(6)은 주말
            
            if is_weekend:
                weekend_count += 1
            else:
                weekday_count += 1
        except:
            is_weekend = False
        
        # 시간 추출
        try:
            hour = int(time_str.split(':')[0])
        except:
            continue
        
        # 비용 계산 (평일/주말 구분)
        cost = 0
        if cost_table:
            if is_weekend:
                cost = get_cost_for_platform(platform, hour, cost_table.get('weekend', {}))
            else:
                cost = get_cost_for_platform(platform, hour, cost_table.get('weekday', {}))
        
        if cost == 0:
            zero_cost_count += 1
        
        # ROI 계산 - 새로운 계산법 적용
        roi = calculate_roi(revenue, cost, platform)
        
        # DB 업데이트
        cursor.execute("""
            UPDATE schedule 
            SET cost = ?, roi = ?
            WHERE id = ?
        """, (cost, roi, record_id))
        
        updated_count += 1
        
        # GS 관련 샘플 저장
        if ('GS' in platform.upper() or 'gs' in platform.lower()) and len(gs_samples) < 20:
            weekday_str = "주말" if is_weekend else "평일"
            gs_samples.append({
                'date': date_str,
                'weekday': weekday_str,
                'platform': platform,
                'time': time_str,
                'hour': hour,
                'cost': cost,
                'roi': roi,
                'revenue': revenue
            })
    
    # 커밋
    conn.commit()
    
    print(f"\n✅ {updated_count}개 레코드 업데이트 완료!")
    print(f"  - 평일 레코드: {weekday_count:,}개")
    print(f"  - 주말 레코드: {weekend_count:,}개")
    print(f"  - 비용 0원 레코드: {zero_cost_count:,}개 ({zero_cost_count/len(records)*100:.1f}%)")
    
    # GS홈쇼핑 관련 샘플 출력
    print("\n📋 GS홈쇼핑 관련 업데이트 샘플 (새로운 ROI 계산법):")
    for sample in gs_samples[:15]:
        print(f"  {sample['date']}({sample['weekday']}) {sample['platform']:20s} {sample['hour']:2d}시 - "
              f"비용: {sample['cost']:11,}원, 매출: {sample['revenue']:11,}원, ROI: {sample['roi']:6.2f}%")
    
    # 특정 날짜 GS홈쇼핑 11시 확인
    cursor.execute("""
        SELECT date, platform, time, cost, revenue, roi
        FROM schedule
        WHERE date = '2025-08-18' 
        AND platform LIKE '%GS%'
        AND time LIKE '11:%'
    """)
    
    print("\n[8월 18일 월요일 GS 관련 11시 데이터]")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]:20s} {row[2]} - 비용: {row[3]:,}원, 매출: {row[4]:,}원, ROI: {row[5]:.2f}%")
    
    # ROI 통계 출력
    cursor.execute("""
        SELECT 
            AVG(roi) as avg_roi,
            MIN(roi) as min_roi,
            MAX(roi) as max_roi,
            COUNT(CASE WHEN roi > 0 THEN 1 END) as positive_count,
            COUNT(CASE WHEN roi < 0 THEN 1 END) as negative_count,
            COUNT(*) as total_count
        FROM schedule
        WHERE cost > 0
    """)
    
    stats = cursor.fetchone()
    if stats:
        print("\n📊 ROI 통계 (새로운 계산법):")
        print(f"  - 평균 ROI: {stats[0]:.2f}%")
        print(f"  - 최소 ROI: {stats[1]:.2f}%")
        print(f"  - 최대 ROI: {stats[2]:.2f}%")
        print(f"  - 양수 ROI: {stats[3]:,}개 ({stats[3]/stats[5]*100:.1f}%)")
        print(f"  - 음수 ROI: {stats[4]:,}개 ({stats[4]/stats[5]*100:.1f}%)")
    
    conn.close()

if __name__ == "__main__":
    print("🔄 기존 DB의 모든 cost/ROI 업데이트 시작...")
    print("=" * 60)
    print(f"📢 새로운 ROI 계산법 적용")
    print(f"   - 전환률: {CONVERSION_RATE:.0%}")
    print(f"   - 제품 원가율: {PRODUCT_COST_RATE:.0%}")
    print(f"   - 판매 수수료율: {COMMISSION_RATE:.0%}")
    print(f"   - 실질 마진율: {REAL_MARGIN_RATE:.2%}")
    print("=" * 60)
    
    # 백업 먼저
    import shutil
    from datetime import datetime
    
    backup_name = f"schedule_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2("schedule.db", backup_name)
    print(f"💾 백업 생성: {backup_name}")
    
    # 업데이트 실행
    update_all_costs()
    
    print("\n✨ 완료! 이제 dashboard_app.py를 실행하세요.")