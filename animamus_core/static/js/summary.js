document.addEventListener("DOMContentLoaded", function() {
    const refreshBtn = document.getElementById("refresh-summary");
    const summaryBox = document.getElementById("summary-text");
    const statusBox = document.getElementById("summary-status");

    refreshBtn.addEventListener("click", function() {
        statusBox.textContent = "요약 중입니다. 잠시만 기다려 주세요...";
        summaryBox.textContent = "";

        fetch(window.location.href, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'refresh_summary' })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                summaryBox.textContent = data.summary_text;
                statusBox.textContent = "요약 완료!";
            } else {
                statusBox.textContent = "요약 실패: " + (data.error || "알 수 없는 오류");
            }
        })
        .catch(error => {
            statusBox.textContent = "요약 중 오류 발생: " + error.message;
        });
    });

    // CSRF 토큰 추출 함수
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
