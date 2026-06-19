# Sagepontus 핵심 기술 명세 — IP 가능성 분석 요청용

## 배경

전문가의 암묵적 사고 구조(tacit knowledge)를 AI가 즉시 이해할 수 있는 구조화된 컨텍스트로 변환하고, 세션을 거듭할수록 개인화되는 지식 자산으로 축적하는 시스템. 현재 물리치료사(PT) 도메인 vertical에 구현 중.

---

## 기술 1: CRA (Context Retention Algorithm) 파이프라인

### 구조
3단계 직렬 LLM 호출 파이프라인.

**Call 1 — 토크나이제이션**
- 입력: 사용자 원문 텍스트 + 도메인 KB + 이전 세션 컨텍스트(optional)
- 처리: KB label/synonym 기반 규칙 매칭 → 신뢰도 스코어 산출
- 출력: domain_hits 리스트 (kb_id, label, confidence, depth, category)

**AMBIGUITY_HALT 메커니즘**
- confidence < 0.70인 토큰 존재 시 파이프라인 중단
- 모호한 표현에 대한 재질문을 자동 생성하여 반환
- AI 호출 없이 규칙 기반으로 1차 처리, 미달 시에만 AI 2차 패스 실행

**Call 2 — 시맨틱 매핑 + 컨텍스트 재구성**
- 입력: Call 1 결과 (domain_hits, raw_tokens)
- 처리: 원문 표현 → KB 표준 용어 매핑, depth_score 기반 정렬, 컨텍스트 오케스트레이션
- 출력: refined_tokens, context (primary_focus, inferred_goal, constraint_cluster, expert_state), depth_summary

**Call 3 — 출력 생성**
- 전문가용 브리핑, 일반 사용자 요약, Before/After 비교 세 가지 형태로 출력

### 세션 연속성 메커니즘 (핵심)
- Call 2 결과를 `CRAAsset`으로 DB 저장
- 다음 세션 Call 1 프롬프트에 `previous_context`로 주입
- 결과: 사용자가 매 세션 상황을 처음부터 설명하지 않아도 AI가 이전 컨텍스트를 즉시 복원

### 하이브리드 처리 전략
- 규칙 기반(비용 없음) → 신뢰도 미달 시 AI 2차 패스
- 각 Call에 AI 폴백과 규칙 기반 폴백이 병행 존재

---

## 기술 2: BrainTree depth-weight 개인화 시스템

### 데이터 구조
```
BrainTree (사용자 지식 트리 루트)
└── BrainBlockNode (블록 단위, MPTT 계층 구조)
    ├── type: common / domain / ai_generated / brain_dump / user_custom
    ├── cached_cra: CRA 파이프라인 결과 JSON
    └── BrainNode (질문-답변 단위 노드)
        ├── question_text
        └── answer_text
```

### depth_score 개념
- KB 내 각 항목에 depth 값 부여 (표면적 개념 = 낮음, 전문가 수준 개념 = 높음)
- 사용자 입력에서 추출된 토큰의 depth_score 분포로 "전문성 깊이" 측정
- peak_score, avg_score로 세션 전문성 수준 수치화

### 4단계 개인화 로드맵
```
1단계 임의지정      현재 구현: KB 저자가 수동으로 depth 값 설정
2단계 의사결정함수  → Alarm 채택률 등 사용자 행동 데이터로 weight 재산출
3단계 강화학습      → 교정 피드백을 reward로 weight 반복 갱신
4단계 귀납적 개인화 → 사용자별 행동 패턴으로 BrainTree가 다르게 진화
```

---

## 기술 3: 전문가 지식 결정화 시스템 (전체 파이프라인)

```
전문가 도메인 Q&A Flow 설계
        ↓
사용자 답변 수집 → BrainNode 저장
        ↓
CRA 파이프라인 처리 (Call1 → 2 → 3)
        ↓
CRAAsset 누적 (도메인별, 사용자별)
        ↓
어떤 AI 도구에서도 즉시 통용되는 시스템 프롬프트 생성
```

목적: 전문가가 매번 AI에게 자신의 맥락을 설명하는 반복 비용 제거. Claude, Gemini, GPT 등 모델 무관하게 작동하는 재사용 가능 컨텍스트 자산.

---

## 기술 4: PT Vertical 적용 — 임상 감사 루프 (설계 중)

### 개념
AI 출력물에 대한 임상가의 교정 행위를 데이터로 수집하여 위 기술 2의 2~4단계를 구동하는 피드백 레이어.

### 수집 대상 paired data
- `(AI 생성 SOAP 초안, 치료사 수정본)` 쌍
- `(AI 생성 Red Flag 알람, 임상가 채택/기각 결정)` 쌍
- `(AI 생성 의뢰서, 치료사 수정본)` 쌍

### 활용
- 수집된 쌍 → Alarm 프로토콜 weight 갱신 (기술 2의 2단계)
- 충분한 데이터 축적 후 → fine-tuning 학습 데이터
- 클리닉/치료사별 개인화 (기술 2의 4단계)

---

## 분석 요청 사항 (Opus에게)

1. 위 기술들 중 특허 청구 가능성이 있는 것은 무엇이며, 예상되는 선행기술(prior art)은 무엇인가?
2. 각 기술의 novelty와 non-obviousness를 어떻게 판단하는가?
3. 단독 특허보다 조합(시스템 특허)으로 청구하는 것이 유리한가?
4. 특허보다 영업비밀(trade secret)로 보호하는 게 더 적합한 항목이 있는가?
5. 출원 우선순위를 어떻게 매기겠는가?
