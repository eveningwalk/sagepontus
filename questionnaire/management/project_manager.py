import json
pm_questions = [
  {
    "order": 1,
    "question_text": "현재 프로젝트에서 가장 불확실한 요소는 무엇인가요?",
    "description": "예상치 못한 변수나 확신이 부족한 부분을 중심으로 서술해보세요.",
    "hint": "예: 외주 일정, 기술 구현 가능성, 이해관계자 요구 변화"
  },
  {
    "order": 2,
    "question_text": "팀원들이 명확하게 이해하고 있는 목표는 무엇이며, 혼란스러운 부분은 무엇인가요?",
    "description": "팀 내에서 공통적으로 인식되는 목표와 오해가 생기는 지점을 구분해서 작성해보세요.",
    "hint": "예: 일정, 역할, 우선순위"
  },
  {
    "order": 3,
    "question_text": "현재 진행 중인 작업 중 병목이 발생하고 있는 부분은 어디인가요?",
    "description": "작업 흐름이 지연되거나 반복되는 지점을 중심으로 구체적으로 설명해보세요.",
    "hint": "예: 승인 지연, 의사결정 미루기, 리소스 부족"
  },
  {
    "order": 4,
    "question_text": "이 프로젝트의 성공을 위해 가장 중요한 이해관계자는 누구이며, 그들과 어떻게 소통하고 있나요?",
    "description": "이해관계자의 역할과 현재 진행 중인 커뮤니케이션 방식에 대해 정리해보세요.",
    "hint": "예: 클라이언트, 경영진, 사용자"
  },
  {
    "order": 5,
    "question_text": "이번 주에 반드시 완료되어야 할 핵심 작업은 무엇인가요?",
    "description": "구체적인 작업 항목과 완료 기준을 함께 작성해보세요.",
    "hint": "예: 기능 테스트, 보고서 제출, 회의 준비"
  }
]

with open("project_manager.json", "w", encoding="utf-8") as f:
    json.dump(pm_questions, f, ensure_ascii=False, indent=2)
