// 브라우저 콘솔에서 실행할 쿠키 추출 스크립트
// 사용법: 
// 1. https://live.ecomm-data.com 접속
// 2. F12 개발자도구 열기
// 3. Console 탭에서 이 스크립트 붙여넣기
// 4. 엔터 실행

(function extractCookies() {
    // 현재 페이지의 모든 쿠키 가져오기
    const cookies = document.cookie;
    
    // 쿠키 정리
    const cookieObj = {};
    cookies.split(';').forEach(cookie => {
        const [key, value] = cookie.trim().split('=');
        if (key) cookieObj[key] = value;
    });
    
    // 필수 쿠키 확인
    const requiredCookies = ['_ga', '_gid'];
    const missingCookies = requiredCookies.filter(key => !cookieObj[key]);
    
    if (missingCookies.length > 0) {
        console.warn('⚠️ 누락된 필수 쿠키:', missingCookies.join(', '));
    }
    
    // 결과 출력
    console.log('%c📋 쿠키 추출 완료!', 'color: green; font-size: 16px; font-weight: bold');
    console.log('%c아래 쿠키 문자열을 복사해서 GitHub Secrets에 붙여넣으세요:', 'color: blue; font-size: 14px');
    console.log('');
    
    // 쿠키 문자열
    const cookieString = cookies.trim();
    console.log('%c' + cookieString, 'background: #f0f0f0; padding: 10px; font-family: monospace; font-size: 12px');
    
    // 클립보드에 복사
    if (navigator.clipboard) {
        navigator.clipboard.writeText(cookieString).then(() => {
            console.log('%c✅ 클립보드에 복사되었습니다!', 'color: green; font-size: 14px; font-weight: bold');
        }).catch(() => {
            console.log('클립보드 복사 실패. 위의 문자열을 수동으로 복사하세요.');
        });
    }
    
    // API 테스트 함수
    window.testAPI = async function() {
        console.log('🔄 API 테스트 중...');
        
        const today = new Date();
        const dateStr = today.toISOString().slice(2, 10).replace(/-/g, '');
        
        try {
            const response = await fetch('https://live.ecomm-data.com/schedule/list_hs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                },
                body: JSON.stringify({
                    code: "0",
                    date: dateStr
                }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data && data.data && data.data.length > 0) {
                console.log('%c✅ API 정상 작동!', 'color: green; font-size: 14px; font-weight: bold');
                console.log(`오늘 데이터: ${data.data.length}개`);
                
                // 0원 매출 체크
                const zeroRevenue = data.data.filter(item => 
                    item.revenue === 0 || item.revenue === "0"
                ).length;
                
                if (zeroRevenue > data.data.length * 0.5) {
                    console.warn(`⚠️ 경고: 0원 매출이 ${zeroRevenue}개 (${(zeroRevenue/data.data.length*100).toFixed(1)}%)`);
                }
            } else {
                console.error('❌ API 응답에 데이터가 없습니다');
            }
            
            return data;
        } catch (error) {
            console.error('❌ API 테스트 실패:', error);
            return null;
        }
    };
    
    // 사용 안내
    console.log('');
    console.log('%c💡 API 테스트를 실행하려면: testAPI()', 'color: #666; font-size: 12px');
    console.log('');
    console.log('%c다음 단계:', 'font-size: 14px; font-weight: bold');
    console.log('1. GitHub 저장소 → Settings → Secrets');
    console.log('2. LABANGBA_COOKIE 수정');
    console.log('3. 복사한 쿠키 값 붙여넣기');
    console.log('4. Actions → Run workflow로 테스트');
})();
