document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('btn-summarize');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const userInput = document.getElementById('user-input').textContent || '';
        if (!userInput.trim()) {
            alert('요약할 텍스트가 없습니다.');
            return;
        }

        btn.disabled = true;
        btn.textContent = '요약 중...';

        try {
            const response = await fetch('/api/summarize/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ text: userInput }),
            });

            if (!response.ok) {
                throw new Error('요약 실패');
            }

            const data = await response.json();
            document.getElementById('ai-summary').textContent = data.summary;
        } catch (e) {
            alert('요약 중 오류가 발생했습니다.');
            console.error(e);
        } finally {
            btn.disabled = false;
            btn.textContent = '요약 다시 요청';
        }
    });

    // CSRF 토큰 읽기 함수 (Django 표준)
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

document.getElementById('refresh-summary').addEventListener('click', () => {
    fetch('/api/summarize/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),  // CSRF 토큰 필요
        },
        body: JSON.stringify({ /* 필요한 데이터, 예: 사용자 응답들 */ }),
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('summary-text').innerText = data.summary || '요약 결과가 없습니다.';
    })
    .catch(error => {
        console.error('Error:', error);
        alert('요약 요청 중 오류가 발생했습니다.');
    });
});

// CSRF 토큰 함수 예시 (Django 공식 문서 참고)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            const cookie = c.trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
