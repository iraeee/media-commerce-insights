"""
strategy_report_generator.py - 전략 분석 HTML 리포트 생성 모듈
Version: 2.0.0
Created: 2025-02-16
Updated: 2025-09-16 - 밝은 파스텔톤 디자인 적용

전략 분석 결과를 밝은 파스텔톤 HTML 리포트로 생성
"""

def generate_strategy_html_report(analysis_data, broadcaster="NS홈쇼핑", date_range="최근 30일"):
    """전략 분석 결과를 HTML 리포트로 생성 - 밝은 파스텔톤 디자인"""
    
    # 데이터 추출
    summary = analysis_data.get('summary', {})
    top_hours = analysis_data.get('top_hours', [])
    top_prices = analysis_data.get('top_prices', [])
    weekday_optimization = analysis_data.get('weekday_optimization', {})
    challenge_hours = analysis_data.get('challenge_hours', [])
    avoid_hours = analysis_data.get('avoid_hours', [])
    recommendations = analysis_data.get('recommendations', [])
    
    # HTML 템플릿 - 밝은 파스텔톤 디자인
    html_template = f'''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{broadcaster} 전략 분석 리포트 - {date_range}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        body {{ 
            font-family: 'Pretendard', sans-serif;
            background: linear-gradient(135deg, #FFF5F7 0%, #F0F9FF 50%, #F5F3FF 100%);
        }}
        .gradient-bg {{ 
            background: linear-gradient(135deg, #C084FC 0%, #F472B6 50%, #60A5FA 100%);
        }}
        .card-shadow {{ 
            box-shadow: 0 10px 40px rgba(147, 51, 234, 0.08);
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.95);
        }}
        .hover-scale {{ 
            transition: all 0.3s ease;
        }}
        .hover-scale:hover {{ 
            transform: translateY(-4px);
            box-shadow: 0 15px 50px rgba(147, 51, 234, 0.15);
        }}
        .chart-container {{ 
            position: relative; 
            height: 350px; 
            width: 100%;
        }}
        .pastel-purple {{ background: linear-gradient(135deg, #F3E7FC 0%, #E9D5FF 100%); }}
        .pastel-pink {{ background: linear-gradient(135deg, #FCE7F3 0%, #FBCFE8 100%); }}
        .pastel-blue {{ background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%); }}
        .pastel-green {{ background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%); }}
        .pastel-yellow {{ background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); }}
        .pastel-red {{ background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); }}
        
        .metric-card {{
            background: white;
            border: 2px solid;
            border-image: linear-gradient(135deg, #C084FC 0%, #60A5FA 100%) 1;
            position: relative;
            overflow: hidden;
        }}
        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #C084FC, #F472B6, #60A5FA);
        }}
        
        .insight-card {{
            background: linear-gradient(135deg, rgba(196, 181, 253, 0.1) 0%, rgba(251, 207, 232, 0.1) 100%);
            border: 2px solid rgba(196, 181, 253, 0.3);
        }}
        
        @media print {{
            .no-print {{ display: none !important; }}
            .page-break {{ page-break-after: always; }}
        }}
    </style>
</head>
<body class="min-h-screen">
    <!-- Header -->
    <div class="gradient-bg text-white py-12 px-6 rounded-b-3xl shadow-2xl">
        <div class="max-w-7xl mx-auto">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-4xl font-bold mb-3 text-white drop-shadow-lg">{broadcaster} 전략 분석 리포트</h1>
                    <p class="text-purple-100 text-lg">ROI 기반 최적 판매 전략 분석 | {date_range}</p>
                </div>
                <div class="bg-white bg-opacity-25 backdrop-blur-sm rounded-2xl px-6 py-4">
                    <p class="text-sm font-semibold">분석 기준: 절사평균 (상하위 15% 제외)</p>
                    <p class="text-xs text-purple-100 mt-1">생성일: {analysis_data.get('generated_date', '')}</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-6 py-10">
        <!-- Summary Cards -->
        <div class="grid grid-cols-5 gap-5 mb-10">
            <div class="metric-card rounded-2xl p-6 hover-scale">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-purple-600 text-sm font-semibold">총 방송</span>
                    <div class="w-10 h-10 rounded-full pastel-purple flex items-center justify-center">
                        <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                        </svg>
                    </div>
                </div>
                <p class="text-3xl font-bold text-gray-800">{summary.get('total_count', 0):,}건</p>
                <p class="text-xs text-gray-500 mt-2">분석 기간 전체</p>
            </div>
            
            <div class="metric-card rounded-2xl p-6 hover-scale">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-green-600 text-sm font-semibold">절사평균 ROI</span>
                    <div class="w-10 h-10 rounded-full pastel-green flex items-center justify-center">
                        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                        </svg>
                    </div>
                </div>
                <p class="text-3xl font-bold {"text-green-600" if summary.get('avg_roi', 0) > 0 else "text-red-500"}">{summary.get('avg_roi', 0):.1f}%</p>
                <p class="text-xs text-gray-500 mt-2">상하위 15% 제외</p>
            </div>
            
            <div class="metric-card rounded-2xl p-6 hover-scale">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-blue-600 text-sm font-semibold">절사평균 매출</span>
                    <div class="w-10 h-10 rounded-full pastel-blue flex items-center justify-center">
                        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                </div>
                <p class="text-3xl font-bold text-gray-800">{summary.get('avg_revenue', 0):.2f}억</p>
                <p class="text-xs text-gray-500 mt-2">방송당 평균</p>
            </div>
            
            <div class="metric-card rounded-2xl p-6 hover-scale">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-pink-600 text-sm font-semibold">절사평균 수량</span>
                    <div class="w-10 h-10 rounded-full pastel-pink flex items-center justify-center">
                        <svg class="w-6 h-6 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
                        </svg>
                    </div>
                </div>
                <p class="text-3xl font-bold text-gray-800">{summary.get('avg_units', 0):.0f}개</p>
                <p class="text-xs text-gray-500 mt-2">방송당 평균</p>
            </div>
            
            <div class="metric-card rounded-2xl p-6 hover-scale">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-yellow-600 text-sm font-semibold">최적 시간</span>
                    <div class="w-10 h-10 rounded-full pastel-yellow flex items-center justify-center">
                        <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                </div>
                <p class="text-3xl font-bold text-gray-800">{summary.get('best_hour', {}).get('hour', 'N/A')}시</p>
                <p class="text-xs text-gray-500 mt-2">ROI 최고 (제외: 2-6시)</p>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-2 gap-8 mb-10">
            <!-- 시간대별 최적화 -->
            <div class="card-shadow rounded-2xl p-8">
                <h3 class="text-2xl font-bold mb-6 text-gray-800">
                    <span class="text-purple-500">⏰</span> 시간대별 최적화
                </h3>
                <div class="chart-container">
                    <canvas id="hourlyChart"></canvas>
                </div>
                <div class="mt-6 space-y-3">
                    <h4 class="font-semibold text-gray-700">💎 TOP 3 시간대</h4>
    '''
    
    # TOP 3 시간대 추가
    for idx, hour in enumerate(top_hours[:3]):
        medal = ["🥇", "🥈", "🥉"][idx]
        roi_color = "text-green-600" if hour['avg_roi'] > 0 else "text-red-600"
        html_template += f'''
                    <div class="flex justify-between items-center p-3 rounded-xl pastel-purple">
                        <span class="font-medium">{medal} {hour['hour']}시</span>
                        <span class="{roi_color} font-bold">ROI {hour['avg_roi']:.1f}%</span>
                    </div>
        '''
    
    html_template += '''
                </div>
            </div>

            <!-- 가격대별 최적화 -->
            <div class="card-shadow rounded-2xl p-8">
                <h3 class="text-2xl font-bold mb-6 text-gray-800">
                    <span class="text-blue-500">💰</span> 가격대별 최적화
                </h3>
                <div class="chart-container">
                    <canvas id="priceChart"></canvas>
                </div>
                <div class="mt-6 space-y-3">
                    <h4 class="font-semibold text-gray-700">💎 TOP 3 가격대</h4>
    '''
    
    # TOP 3 가격대 추가
    for idx, price in enumerate(top_prices[:3]):
        medal = ["🥇", "🥈", "🥉"][idx]
        roi_color = "text-green-600" if price['avg_roi'] > 0 else "text-red-600"
        html_template += f'''
                    <div class="flex justify-between items-center p-3 rounded-xl pastel-blue">
                        <span class="font-medium">{medal} {price['price_range']}</span>
                        <span class="{roi_color} font-bold">ROI {price['avg_roi']:.1f}%</span>
                    </div>
        '''
    
    html_template += '''
                </div>
            </div>
        </div>

        <!-- 요일별 최적화 -->
        <div class="card-shadow rounded-2xl p-8 mb-10">
            <h3 class="text-2xl font-bold mb-6 text-gray-800">
                <span class="text-green-500">📅</span> 요일별 최적 시간대 TOP 3
            </h3>
            <div class="grid grid-cols-7 gap-4">
    '''
    
    # 요일별 데이터 추가
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']
    for day in weekday_names:
        if day in weekday_optimization:
            data = weekday_optimization[day]
            html_template += f'''
                <div class="text-center p-4 rounded-xl pastel-green">
                    <h4 class="font-bold text-gray-700 mb-3">{day}요일</h4>
            '''
            if data['top_hours']:
                for idx, hour_data in enumerate(data['top_hours'][:3]):
                    emoji = ["🥇", "🥈", "🥉"][idx]
                    html_template += f'''
                    <p class="text-sm mb-1">{emoji} {hour_data['hour']}시 ({hour_data['roi']:.0f}%)</p>
                    '''
            else:
                html_template += '<p class="text-xs text-gray-500">데이터 부족</p>'
            
            html_template += f'''
                    <p class="text-xs text-gray-600 mt-2">평균: {data['avg_roi']:.0f}%</p>
                </div>
            '''
        else:
            html_template += f'''
                <div class="text-center p-4 rounded-xl bg-gray-50">
                    <h4 class="font-bold text-gray-400 mb-3">{day}요일</h4>
                    <p class="text-xs text-gray-400">데이터 없음</p>
                </div>
            '''
    
    html_template += '''
            </div>
        </div>

        <!-- 전략적 인사이트 -->
        <div class="grid grid-cols-2 gap-8 mb-10">
            <!-- 도전 시간대 -->
            <div class="insight-card rounded-2xl p-8">
                <h3 class="text-2xl font-bold mb-6 text-yellow-600">
                    🎯 도전해볼 시간대 (개선 가능)
                </h3>
                <div class="space-y-4">
    '''
    
    # 도전 시간대 추가
    if challenge_hours:
        for hour in challenge_hours[:3]:
            html_template += f'''
                    <div class="p-5 rounded-xl bg-yellow-50 border-2 border-yellow-200">
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-xl font-bold text-yellow-700">{hour['hour']}시</span>
                            <span class="text-yellow-600 font-semibold">ROI {hour['avg_roi']:.1f}%</span>
                        </div>
                        <p class="text-sm text-gray-600 mb-2">매출: {hour['avg_revenue']:.2f}억 | 수량: {hour.get('avg_units', 0):.0f}개</p>
                        <p class="text-xs text-gray-500 leading-relaxed">{hour.get('reason', '개선 가능성이 높은 시간대')}</p>
                    </div>
            '''
    else:
        html_template += '''
                    <p class="text-gray-500 text-center py-8">분석할 데이터가 충분하지 않습니다.</p>
        '''
    
    html_template += '''
                </div>
            </div>

            <!-- 피해야 할 시간대 -->
            <div class="insight-card rounded-2xl p-8">
                <h3 class="text-2xl font-bold mb-6 text-red-600">
                    ⚠️ 절대 피해야 할 시간대
                </h3>
                <div class="space-y-4">
    '''
    
    # 피해야 할 시간대 추가
    if avoid_hours:
        for hour in avoid_hours[:3]:
            html_template += f'''
                    <div class="p-5 rounded-xl bg-red-50 border-2 border-red-200">
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-xl font-bold text-red-700">{hour['hour']}시</span>
                            <span class="text-red-600 font-semibold">ROI {hour['avg_roi']:.1f}%</span>
                        </div>
                        <p class="text-sm text-gray-600 mb-2">매출: {hour['avg_revenue']:.2f}억 | 수량: {hour.get('avg_units', 0):.0f}개</p>
                        <p class="text-xs text-gray-500 leading-relaxed">{hour.get('reason', 'ROI가 낮아 수익성이 저조한 시간대')}</p>
                    </div>
            '''
    else:
        html_template += '''
                    <p class="text-gray-500 text-center py-8">분석할 데이터가 충분하지 않습니다.</p>
        '''
    
    html_template += '''
                </div>
            </div>
        </div>

        <!-- 전략적 제언 -->
        <div class="card-shadow rounded-2xl p-8">
            <h3 class="text-2xl font-bold mb-6 text-gray-800">
                <span class="text-purple-500">✨</span> 전략적 제언
            </h3>
            <div class="grid grid-cols-2 gap-6">
                <div class="p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200">
                    <h4 class="text-lg font-bold text-purple-700 mb-3">⏰ 시간대 최적화</h4>
                    <p class="text-sm text-gray-700 leading-relaxed">
                        오전 피크 시간대와 저녁 프라임 시간대에 주력 상품을 집중 배치하여 ROI를 극대화하세요.
                        새벽 2-6시는 제외하고 운영하는 것이 효율적입니다.
                    </p>
                </div>
                <div class="p-6 rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200">
                    <h4 class="text-lg font-bold text-blue-700 mb-3">💰 가격 전략</h4>
                    <p class="text-sm text-gray-700 leading-relaxed">
                        고객의 심리적 가격대를 고려한 가격 구성으로 구매 전환율을 향상시키고,
                        가격 경쟁력과 수익성의 균형점을 확보하세요.
                    </p>
                </div>
                <div class="p-6 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200">
                    <h4 class="text-lg font-bold text-green-700 mb-3">📅 요일별 차별화</h4>
                    <p class="text-sm text-gray-700 leading-relaxed">
                        요일별 고객 특성을 반영한 맞춤 전략을 수립하고,
                        주중과 주말의 구매 패턴 차이를 활용한 차별화된 운영을 실시하세요.
                    </p>
                </div>
                <div class="p-6 rounded-xl bg-gradient-to-br from-red-50 to-orange-50 border-2 border-red-200">
                    <h4 class="text-lg font-bold text-red-700 mb-3">🎯 리스크 관리</h4>
                    <p class="text-sm text-gray-700 leading-relaxed">
                        비효율 시간대를 회피하여 손실을 최소화하고,
                        투자 대비 수익률을 개선하여 전체적인 ROI를 상승시키세요.
                    </p>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="mt-16 py-8 px-6 bg-gradient-to-r from-purple-100 to-pink-100 rounded-t-3xl">
        <div class="max-w-7xl mx-auto text-center">
            <p class="text-gray-600 text-sm">
                이 리포트는 절사평균(상하위 15% 제외) 기준으로 분석되었습니다.
            </p>
            <p class="text-gray-500 text-xs mt-2">
                생성일시: {analysis_data.get('generated_date', '')} | {broadcaster} | {date_range}
            </p>
        </div>
    </div>

    <!-- Charts JavaScript -->
    <script>
        // 시간대별 차트
        const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
        const hourlyData = {json.dumps([h['hour'] for h in top_hours[:10]] if top_hours else [])};
        const hourlyROI = {json.dumps([h['avg_roi'] for h in top_hours[:10]] if top_hours else [])};
        
        new Chart(hourlyCtx, {{
            type: 'bar',
            data: {{
                labels: hourlyData.map(h => h + '시'),
                datasets: [{{
                    label: '절사평균 ROI (%)',
                    data: hourlyROI,
                    backgroundColor: hourlyROI.map(roi => roi > 0 
                        ? 'rgba(52, 211, 153, 0.5)' 
                        : 'rgba(248, 113, 113, 0.5)'),
                    borderColor: hourlyROI.map(roi => roi > 0 
                        ? 'rgba(16, 185, 129, 1)' 
                        : 'rgba(239, 68, 68, 1)'),
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(147, 51, 234, 0.5)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }}
                }},
                scales: {{
                    y: {{
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }},
                        ticks: {{
                            font: {{ size: 12 }},
                            color: '#6B7280'
                        }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{
                            font: {{ size: 12 }},
                            color: '#6B7280'
                        }}
                    }}
                }}
            }}
        }});
        
        // 가격대별 차트
        const priceCtx = document.getElementById('priceChart').getContext('2d');
        const priceData = {json.dumps([p['price_range'] for p in top_prices[:10]] if top_prices else [])};
        const priceROI = {json.dumps([p['avg_roi'] for p in top_prices[:10]] if top_prices else [])};
        
        new Chart(priceCtx, {{
            type: 'bar',
            data: {{
                labels: priceData,
                datasets: [{{
                    label: '절사평균 ROI (%)',
                    data: priceROI,
                    backgroundColor: 'rgba(147, 51, 234, 0.5)',
                    borderColor: 'rgba(124, 58, 237, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(96, 165, 250, 0.5)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }}
                }},
                scales: {{
                    y: {{
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }},
                        ticks: {{
                            font: {{ size: 12 }},
                            color: '#6B7280'
                        }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{
                            font: {{ size: 12 }},
                            color: '#6B7280'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
    '''
    
    # json 모듈 import
    import json
    
    # 템플릿 반환
    return html_template
