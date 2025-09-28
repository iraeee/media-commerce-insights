# HTML 보고서 생성 함수 (dashboard_strategy_analysis.py 추가 부분)

def generate_enhanced_html_report(analysis_df, strategy_name, platform, weekday, 
                                  top_hours, top_prices, metrics):
    """향상된 HTML 보고서 생성"""
    
    # 차트를 HTML로 변환
    charts_html = ""
    
    if not top_hours.empty:
        # 시간대별 ROI 차트
        fig_hours = go.Figure()
        
        # 막대 그래프
        fig_hours.add_trace(go.Bar(
            name='평균 ROI',
            x=[f"{int(h)}시" for h in top_hours['hour']],
            y=top_hours['roi'],
            text=[f"{roi:.1f}%" for roi in top_hours['roi']],
            textposition='outside',
            marker_color='#667eea'
        ))
        
        # 선 그래프
        fig_hours.add_trace(go.Scatter(
            name='절사평균 ROI',
            x=[f"{int(h)}시" for h in top_hours['hour']],
            y=top_hours['trimmed_roi'],
            mode='lines+markers',
            line=dict(color='#FF0080', width=2),
            marker=dict(size=8)
        ))
        
        fig_hours.update_layout(
            title="시간대별 ROI 분석",
            height=450,
            paper_bgcolor='white',
            plot_bgcolor='#f8f9fa'
        )
        
        charts_html = pio.to_html(fig_hours, include_plotlyjs='cdn')
    
    # HTML 템플릿
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>홈쇼핑 전략 분석 보고서 - {strategy_name}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Noto Sans KR', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                text-align: center;
                color: white;
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                font-weight: 900;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            
            .header .subtitle {{
                font-size: 1.2rem;
                opacity: 0.95;
            }}
            
            .content {{
                padding: 40px;
            }}
            
            .section {{
                margin-bottom: 40px;
            }}
            
            .section-title {{
                font-size: 1.8rem;
                color: #2d3748;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .metric-card {{
                background: linear-gradient(135deg, #f7fafc 0%, #ffffff 100%);
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                transition: all 0.3s ease;
            }}
            
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
                border-color: #667eea;
            }}
            
            .metric-label {{
                font-size: 0.9rem;
                color: #718096;
                margin-bottom: 8px;
                font-weight: 600;
            }}
            
            .metric-value {{
                font-size: 2rem;
                font-weight: 900;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            
            .metric-sub {{
                font-size: 0.8rem;
                color: #a0aec0;
                margin-top: 5px;
            }}
            
            .insight-box {{
                background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
                border-left: 5px solid #667eea;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }}
            
            .insight-title {{
                font-size: 1.2rem;
                color: #667eea;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            
            .insight-content {{
                color: #4a5568;
                line-height: 1.8;
            }}
            
            .time-analysis {{
                background: #f8f9fa;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            
            .time-rank {{
                display: inline-block;
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 50%;
                text-align: center;
                line-height: 40px;
                font-weight: 900;
                margin-right: 15px;
            }}
            
            .time-details {{
                display: flex;
                align-items: center;
                margin-bottom: 15px;
                padding: 15px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            .time-info {{
                flex: 1;
            }}
            
            .time-hour {{
                font-size: 1.3rem;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            
            .time-stats {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-top: 10px;
            }}
            
            .time-stat {{
                text-align: center;
            }}
            
            .time-stat-label {{
                font-size: 0.8rem;
                color: #718096;
            }}
            
            .time-stat-value {{
                font-size: 1.1rem;
                font-weight: 700;
                color: #2d3748;
            }}
            
            .recommendation-card {{
                background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
                color: white;
                border-radius: 15px;
                padding: 30px;
                margin: 30px 0;
                text-align: center;
            }}
            
            .recommendation-title {{
                font-size: 1.5rem;
                font-weight: 900;
                margin-bottom: 15px;
            }}
            
            .recommendation-content {{
                font-size: 1.1rem;
                line-height: 1.8;
            }}
            
            .chart-container {{
                background: white;
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            .footer {{
                background: #2d3748;
                color: white;
                text-align: center;
                padding: 30px;
                font-size: 0.9rem;
            }}
            
            .footer a {{
                color: #667eea;
                text-decoration: none;
            }}
            
            @media print {{
                body {{
                    background: white;
                }}
                .container {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- 헤더 -->
            <div class="header">
                <h1>🎯 홈쇼핑 전략 분석 보고서</h1>
                <div class="subtitle">
                    {strategy_name} | {platform} | {weekday} | {datetime.now().strftime('%Y년 %m월 %d일')}
                </div>
            </div>
            
            <!-- 콘텐츠 -->
            <div class="content">
                <!-- 핵심 지표 섹션 -->
                <div class="section">
                    <h2 class="section-title">📊 핵심 성과 지표</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">총 매출</div>
                            <div class="metric-value">{metrics.get('total_revenue', 0):.1f}억</div>
                            <div class="metric-sub">전체 매출액</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">평균 ROI</div>
                            <div class="metric-value">{metrics.get('avg_roi', 0):.1f}%</div>
                            <div class="metric-sub">절사: {metrics.get('trimmed_roi', 0):.1f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">순이익</div>
                            <div class="metric-value">{metrics.get('total_profit', 0):.1f}억</div>
                            <div class="metric-sub">실질 수익</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">최적 시간</div>
                            <div class="metric-value">{metrics.get('best_hour', 0)}시</div>
                            <div class="metric-sub">최고 ROI 시간대</div>
                        </div>
                    </div>
                </div>
                
                <!-- ROI 계산법 설명 -->
                <div class="section">
                    <h2 class="section-title">💡 분석 기준 및 계산법</h2>
                    <div class="insight-box">
                        <div class="insight-title">ROI 계산 공식</div>
                        <div class="insight-content">
                            <strong>ROI(%) = [(매출 × 실질마진율) - 총비용] ÷ 총비용 × 100</strong><br><br>
                            • 실질마진율: 57.75% (전환율 75% × 마진율 77%)<br>
                            • 모델비용: 라이브 1,040만원 / 비라이브 200만원<br>
                            • 방송비용: 시간대별 정액 (주말 13-16시 포함)<br>
                            • 제외시간: 00~05시 (모델비용 미적용)
                        </div>
                    </div>
                </div>
                
                <!-- 시간대별 분석 -->
                <div class="section">
                    <h2 class="section-title">⏰ 시간대별 상세 분석</h2>
                    <div class="chart-container">
                        {charts_html}
                    </div>
                    """
    
    # 시간대별 상세 정보 추가
    for idx, row in top_hours.head(5).iterrows():
        roi_color = "#10b981" if row['roi'] > 0 else "#ef4444"
        html_content += f"""
                    <div class="time-analysis">
                        <div class="time-details">
                            <span class="time-rank">{idx + 1}</span>
                            <div class="time-info">
                                <div class="time-hour">{int(row['hour'])}시 방송</div>
                                <div class="time-stats">
                                    <div class="time-stat">
                                        <div class="time-stat-label">평균 ROI</div>
                                        <div class="time-stat-value" style="color: {roi_color};">
                                            {row['roi']:.1f}%
                                        </div>
                                    </div>
                                    <div class="time-stat">
                                        <div class="time-stat-label">절사 ROI</div>
                                        <div class="time-stat-value">
                                            {row.get('trimmed_roi', row['roi']):.1f}%
                                        </div>
                                    </div>
                                    <div class="time-stat">
                                        <div class="time-stat-label">순이익</div>
                                        <div class="time-stat-value">
                                            {row.get('net_profit', 0):.2f}억
                                        </div>
                                    </div>
                                </div>
                                <div style="margin-top: 10px; color: #718096; font-size: 0.9rem;">
                                    모델비용: {row.get('model_cost', 0):.3f}억 | 
                                    방송비용: {row.get('broadcast_cost', 0):.3f}억 | 
                                    방송횟수: {row.get('count', 0)}회
                                </div>
                            </div>
                        </div>
                    </div>
        """
    
    # 추가 분석 인사이트
    html_content += f"""
                </div>
                
                <!-- 전략적 제언 -->
                <div class="section">
                    <h2 class="section-title">🎯 전략적 제언</h2>
                    <div class="recommendation-card">
                        <div class="recommendation-title">최적 운영 전략</div>
                        <div class="recommendation-content">
                            {get_strategic_recommendations(top_hours, metrics)}
                        </div>
                    </div>
                    
                    <div class="insight-box">
                        <div class="insight-title">추가 고려사항</div>
                        <div class="insight-content">
                            {get_additional_insights(analysis_df, top_hours, top_prices)}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 푸터 -->
            <div class="footer">
                <p>© 2025 홈쇼핑 전략 분석 시스템 | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>본 보고서는 데이터 기반 분석 결과이며, 실제 운영 시 시장 상황을 고려하여 적용하시기 바랍니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def get_strategic_recommendations(top_hours, metrics):
    """전략적 제언 생성"""
    if top_hours.empty:
        return "데이터가 충분하지 않아 제언을 생성할 수 없습니다."
    
    best_hour = top_hours.iloc[0]['hour']
    best_roi = top_hours.iloc[0]['roi']
    
    recommendations = []
    
    # 시간대별 추천
    if best_hour in range(7, 12):
        recommendations.append("• 오전 시간대가 최적 성과를 보입니다. 주부/시니어 타겟 상품을 집중 편성하세요.")
    elif best_hour in range(17, 22):
        recommendations.append("• 저녁 시간대가 최적입니다. 가족 단위 구매가 가능한 고가 상품을 배치하세요.")
    
    # ROI 기반 추천
    if best_roi > 30:
        recommendations.append("• 높은 ROI를 유지하고 있습니다. 현재 전략을 유지하며 방송 횟수를 늘리세요.")
    elif best_roi > 10:
        recommendations.append("• 안정적인 ROI입니다. 비용 최적화를 통해 수익성을 개선하세요.")
    else:
        recommendations.append("• ROI 개선이 필요합니다. 상품 구성과 가격대를 재검토하세요.")
    
    # 비용 관련 추천
    avg_model_cost = top_hours['model_cost'].mean()
    if avg_model_cost > 0.08:  # 0.08억 = 800만원
        recommendations.append("• 모델비용이 높습니다. 비라이브 채널 활용을 검토하세요.")
    
    return "<br>".join(recommendations)

def get_additional_insights(analysis_df, top_hours, top_prices):
    """추가 인사이트 생성"""
    insights = []
    
    # 시간대 집중도
    if not top_hours.empty:
        top3_hours = top_hours.head(3)['hour'].tolist()
        insights.append(f"• 상위 3개 시간대({', '.join([f'{h}시' for h in top3_hours])})에 집중 운영을 권장합니다.")
    
    # 가격대 분석
    if not top_prices.empty:
        best_price = top_prices.iloc[0]['price_range']
        insights.append(f"• {best_price} 가격대가 최적 성과를 보입니다.")
    
    # 주말/평일 비교
    if 'is_weekend' in analysis_df.columns:
        weekend_roi = analysis_df[analysis_df['is_weekend']]['roi'].mean()
        weekday_roi = analysis_df[~analysis_df['is_weekend']]['roi'].mean()
        if weekend_roi > weekday_roi:
            insights.append(f"• 주말 ROI({weekend_roi:.1f}%)가 평일({weekday_roi:.1f}%)보다 높습니다.")
        else:
            insights.append(f"• 평일 ROI({weekday_roi:.1f}%)가 주말({weekend_roi:.1f}%)보다 높습니다.")
    
    # 비용 효율성
    total_cost = analysis_df['total_cost'].sum()
    total_profit = analysis_df['net_profit'].sum()
    efficiency = (total_profit / total_cost * 100) if total_cost > 0 else 0
    insights.append(f"• 비용 대비 수익 효율성: {efficiency:.1f}%")
    
    # 개선 포인트
    negative_roi_count = (analysis_df['roi'] < 0).sum()
    if negative_roi_count > 0:
        negative_ratio = negative_roi_count / len(analysis_df) * 100
        insights.append(f"• 음수 ROI 비율 {negative_ratio:.1f}% - 해당 시간대 상품 재검토 필요")
    
    return "<br>".join(insights)
