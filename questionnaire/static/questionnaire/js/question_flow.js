document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("question-form");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const formData = new FormData(form);

        try {
            const response = await fetch(window.location.href, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (response.ok) {
                window.location.reload(); // 다음 질문 로드
            } else {
                alert("답변 저장에 실패했습니다. 다시 시도해주세요.");
            }
        } catch (err) {
            console.error(err);
            alert("오류가 발생했습니다.");
        }
    });
});
