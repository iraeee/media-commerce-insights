"""
라방바 DB를 CSV로 변환하는 스크립트
각 폴더에서 독립적으로 실행 가능
"""

import sqlite3
import pandas as pd
import os
import sys
from datetime import datetime
from pathlib import Path

class DBToCSVConverter:
    """DB를 CSV로 변환하는 클래스"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.db_name = Path(db_path).stem
        self.stats = {}
        
    def analyze_db(self):
        """DB 구조 분석"""
        print(f"\n{'='*60}")
        print(f"📊 DB 분석: {self.db_path}")
        print(f"{'='*60}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 테이블 목록
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            print(f"✅ 테이블 목록: {', '.join(tables)}")
            
            # 메인 테이블 찾기
            main_table = None
            if 'schedule_data' in tables:
                main_table = 'schedule_data'
            elif 'schedule' in tables:
                main_table = 'schedule'
            else:
                print("⚠️ schedule 관련 테이블을 찾을 수 없습니다!")
                conn.close()
                return None
            
            print(f"✅ 사용할 테이블: {main_table}")
            
            # 컬럼 정보
            cursor.execute(f"PRAGMA table_info({main_table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"✅ 컬럼 수: {len(column_names)}개")
            print(f"   컬럼: {', '.join(column_names[:10])}")
            if len(column_names) > 10:
                print(f"   ... 외 {len(column_names)-10}개")
            
            # 레코드 수
            cursor.execute(f"SELECT COUNT(*) FROM {main_table}")
            record_count = cursor.fetchone()[0]
            print(f"✅ 총 레코드: {record_count:,}개")
            
            # 날짜 범위
            if 'date' in column_names:
                cursor.execute(f"SELECT MIN(date), MAX(date) FROM {main_table}")
                date_range = cursor.fetchone()
                print(f"✅ 날짜 범위: {date_range[0]} ~ {date_range[1]}")
            
            # 방송사 수
            if 'platform' in column_names:
                cursor.execute(f"SELECT COUNT(DISTINCT platform) FROM {main_table}")
                platform_count = cursor.fetchone()[0]
                print(f"✅ 방송사 수: {platform_count}개")
                
                # 상위 5개 방송사
                cursor.execute(f"""
                    SELECT platform, COUNT(*) as cnt 
                    FROM {main_table}
                    GROUP BY platform
                    ORDER BY cnt DESC
                    LIMIT 5
                """)
                top_platforms = cursor.fetchall()
                print(f"   상위 방송사:")
                for plat, cnt in top_platforms:
                    print(f"   - {plat}: {cnt:,}개")
            
            # 카테고리 수
            if 'category' in column_names:
                cursor.execute(f"SELECT COUNT(DISTINCT category) FROM {main_table}")
                category_count = cursor.fetchone()[0]
                print(f"✅ 카테고리 수: {category_count}개")
            
            # 매출 통계
            if 'revenue' in column_names:
                cursor.execute(f"""
                    SELECT 
                        SUM(revenue) as total,
                        AVG(revenue) as avg,
                        COUNT(CASE WHEN revenue = 0 THEN 1 END) as zero_count
                    FROM {main_table}
                """)
                revenue_stats = cursor.fetchone()
                if revenue_stats[0]:
                    print(f"✅ 매출 통계:")
                    print(f"   - 총 매출: {revenue_stats[0]:,.0f}원")
                    print(f"   - 평균 매출: {revenue_stats[1]:,.0f}원")
                    print(f"   - 0원 비율: {revenue_stats[2]/record_count*100:.1f}%")
            
            conn.close()
            
            self.stats = {
                'table': main_table,
                'columns': column_names,
                'record_count': record_count,
                'date_range': date_range if 'date' in column_names else None
            }
            
            return main_table
            
        except Exception as e:
            print(f"❌ DB 분석 실패: {e}")
            return None
    
    def convert_to_csv(self, output_dir=None):
        """DB를 CSV로 변환"""
        
        # 테이블 분석
        main_table = self.analyze_db()
        if not main_table:
            return None
        
        print(f"\n{'='*60}")
        print(f"🔄 CSV 변환 시작")
        print(f"{'='*60}")
        
        try:
            # DB 연결
            conn = sqlite3.connect(self.db_path)
            
            # 데이터 읽기
            print(f"📖 데이터 읽는 중...")
            query = f"SELECT * FROM {main_table}"
            df = pd.read_sql_query(query, conn)
            print(f"✅ {len(df):,}개 레코드 로드 완료")
            
            # 날짜 형식 정리 (있는 경우)
            if 'date' in df.columns:
                print(f"📅 날짜 형식 정리 중...")
                # YYYY.MM.DD를 YYYY-MM-DD로 변환
                df['date'] = df['date'].str.replace('.', '-', regex=False)
                # 날짜 유효성 검사
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # 방송사와 방송명 분리 체크
            if 'broadcast' in df.columns and 'platform' in df.columns:
                print(f"🔍 방송사/방송명 분리 확인 중...")
                # 샘플 출력
                sample = df[['broadcast', 'platform']].head(3)
                print("샘플 데이터:")
                for idx, row in sample.iterrows():
                    print(f"  방송명: {row['broadcast'][:50]}...")
                    print(f"  방송사: {row['platform']}")
                    print()
            
            # 출력 경로 설정
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{self.db_name}.csv")
            else:
                output_path = f"{self.db_name}.csv"
            
            # CSV 저장
            print(f"💾 CSV 저장 중...")
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            # 파일 크기
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ CSV 저장 완료: {output_path}")
            print(f"   파일 크기: {file_size:.2f} MB")
            
            # 통계 요약
            print(f"\n{'='*60}")
            print(f"📊 변환 결과 요약")
            print(f"{'='*60}")
            print(f"원본 DB: {self.db_path}")
            print(f"출력 CSV: {output_path}")
            print(f"레코드 수: {len(df):,}개")
            print(f"컬럼 수: {len(df.columns)}개")
            
            if 'date' in df.columns:
                print(f"날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
            
            if 'platform' in df.columns:
                print(f"방송사 종류: {df['platform'].nunique()}개")
            
            if 'category' in df.columns:
                print(f"카테고리 종류: {df['category'].nunique()}개")
            
            if 'revenue' in df.columns:
                print(f"총 매출: {df['revenue'].sum():,.0f}원")
                zero_ratio = (df['revenue'] == 0).sum() / len(df) * 100
                print(f"매출 0원 비율: {zero_ratio:.1f}%")
            
            conn.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ 변환 실패: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """메인 함수"""
    print("\n" + "="*60)
    print("🔄 라방바 DB → CSV 변환 도구")
    print("="*60)
    
    # 현재 폴더에서 DB 파일 찾기
    current_dir = os.getcwd()
    db_files = [f for f in os.listdir(current_dir) if f.endswith('.db')]
    
    if not db_files:
        print("❌ 현재 폴더에 .db 파일이 없습니다!")
        return
    
    print(f"\n📂 현재 폴더: {current_dir}")
    print(f"🔍 발견된 DB 파일:")
    for i, db_file in enumerate(db_files, 1):
        file_size = os.path.getsize(db_file) / (1024 * 1024)
        print(f"  {i}. {db_file} ({file_size:.2f} MB)")
    
    # DB 선택
    if len(db_files) == 1:
        selected_db = db_files[0]
        print(f"\n✅ 자동 선택: {selected_db}")
    else:
        print("\n변환할 DB 파일 번호를 선택하세요:")
        try:
            choice = int(input("번호 입력: ")) - 1
            if 0 <= choice < len(db_files):
                selected_db = db_files[choice]
            else:
                print("❌ 잘못된 번호입니다!")
                return
        except ValueError:
            print("❌ 숫자를 입력해주세요!")
            return
    
    # 변환 실행
    converter = DBToCSVConverter(selected_db)
    result = converter.convert_to_csv()
    
    if result:
        print(f"\n✅ 변환 성공!")
        print(f"✅ CSV 파일: {result}")
        print(f"\n이제 이 CSV 파일을 엑셀에서 열어 확인할 수 있습니다.")
    else:
        print(f"\n❌ 변환 실패!")


if __name__ == "__main__":
    main()