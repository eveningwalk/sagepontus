# Sagepontus — 프로젝트 컨텍스트

## 한 줄 정의
PT(물리치료사) 전용 AI SOAP 노트 자동화 + Red Flag 알람 SaaS → Chrome Extension

---

## 사업 개요

### 타겟 시장
미국 물리치료(PT) 시장. Direct Access 확대로 PT/PTA가 1차 스크리닝 의무를 지게 되었으나,
구인난으로 PTA(보조 물리치료사) 고용 극대화 → 레드 플래그 누락 → 수백만 달러 규모 의료 소송 리스크.

### 제품 전략 (Hook + Killer)
- **Hook (PTA용)**: AI SOAP 노트 자동화 — 매일 반복되는 행정업무 1분 → 10초
- **Killer (센터장용)**: Red Flag 알람 + 의사 리퍼럴 레터 자동 생성 → 소송 방지

### 배포 형태
기존 EMR(WebPT 등) 화면에 올라타는 **Chrome Extension** — 이중입력 없음, 워크플로우 침투형

### 핵심 기술
- **VPPS** (Vertical Prompt Propagation): 비정형 SOAP 텍스트 → 증상 팩트 JSON 추출 (할루시네이션 배제, Goodman's 가이드라인 기반)
- **CRA** (Context Retention Algorithm): 환자 수개월 치 세션 시계열 누적 → 점진적 악화 패턴 포착 (`questionnaire/prompts/cra_engine.py` 기존 구현 존재)

---

## 개발 디렉토리 구조

```
sagepontus/
│
│  ── 기존 유지 ──────────────────────────────────
├── animamus_project/          # Django 설정, 메인 urls.py
├── animamus_common/           # 공통 유틸, AI 헬퍼
├── accounts/                  # 인증
├── questionnaire/             # 기존 공통 Q&A 엔진
│
│  ── 신규 Django App ─────────────────────────────
├── vertical_pt/               # PT vertical 전체
│   ├── apps.py
│   ├── models/
│   │   ├── patient_timeline.py    # CRA용 시계열 누적
│   │   ├── red_flag_alert.py      # 알람 이력
│   │   └── symptom_weight.py      # 가중치 매트릭스
│   │
│   ├── engine/                # 핵심 엔진
│   │   ├── vpps.py            # 비정형 텍스트 → 증상 팩트 추출
│   │   ├── cra.py             # 시계열 추론 (cra_engine.py 이전)
│   │   ├── scorer.py          # 가중치 연산 + 임계치 판단
│   │   └── referral.py        # 의사 리퍼럴 레터 PDF 생성
│   │
│   ├── api/                   # Chrome Extension용 REST API
│   │   ├── views_api.py       # /api/pt/analyze/
│   │   └── serializers.py
│   │
│   ├── prompts/
│   │   ├── kb_soap.json       # SOAP 생성 지식베이스
│   │   └── kb_red_flag.json   # Goodman's 기반 Red Flag 패턴
│   │
│   ├── views/
│   │   └── views_pt_alarm.py  # PT 전용 웹 플로우
│   │
│   ├── migrations/
│   └── management/commands/
│       └── seed_red_flag.py   # Phase 1 데이터 적재
│
│  ── 신규 Chrome Extension ───────────────────────
├── chrome_extension/          # 별도 프론트엔드 프로젝트
│   ├── manifest.json
│   ├── content_script.js      # EMR DOM 읽기 (WebPT 등)
│   ├── background.js
│   └── popup/
│       ├── popup.html         # SOAP 보조 + 알람 UI
│       └── popup.js
│
│  ── 랜딩 페이지 ────────────────────────────────
├── landingpage_source/
│   └── app/
│       ├── page.tsx           # 기존 메인 랜딩
│       └── pt-alarm/
│           └── page.tsx       # PT Red Flag 전용 랜딩
│
│  ── 데이터셋 ────────────────────────────────────
├── data/
│   └── red_flag_protocols/    # Phase 1 산출물 (Goodman's 기반)
│       ├── low_back_pain.json
│       ├── cauda_equina.json
│       ├── fracture.json
│       ├── malignancy.json
│       └── vascular.json
│
│  ── 스크립트 ───────────────────────────────────
└── scripts/
    ├── generate_b_prompt.py       # 기존 PT A/B test
    ├── token_compare.py           # 기존 토큰 비교
    └── red_flag/
        ├── extract_goodmans.py    # Phase 1: Claude로 JSON 추출
        └── validate_scenarios.py  # Phase 2: 100건 시나리오 검증
```

---

## 개발 Phase 순서

| Phase | 작업 | 산출물 |
|-------|------|--------|
| 1 | Goodman's → Red Flag JSON 트리 추출 | `data/red_flag_protocols/*.json` |
| 2 | 가상 시나리오 100건 알고리즘 검증 | 민감도/특이도 수치 |
| 3 | VPPS + CRA + scorer 백엔드 구현 | `vertical_pt/engine/` |
| 4 | Chrome Extension API 엔드포인트 | `vertical_pt/api/` |
| 5 | Chrome Extension UI | `chrome_extension/` |
| 6 | PT Red Flag 전용 랜딩 페이지 | `landingpage_source/app/pt-alarm/` |
| 7 | Audit Loop + Paired Data 수집 구조 | DB 스키마 + UI 3종 + 추출 파이프라인 |
| 8 | Temporal Red Flag — 시계열 알람 고도화 | CRA→scorer 연동, 연속 상승 선제 경보, 가성 호전 경보 |
| 9 | Treatment Response Tracking | 세션 간 VAS/ROM 추적, 정체 알람, Progress Note 자동화 |
| 10 | Clinic Analytics Dashboard | 치료사별 정확도, 회복 곡선, 소송 방지 ROI 시뮬레이션 |

### Phase 7 상세

**목적**: AI 출력물에 대한 임상가 교정 행위를 데이터로 축적 → copy cat 대비 데이터 해자 구축 + Alarm weight 개인화 기반 마련

| 작업 | 설명 |
|------|------|
| SOAP 수정 UI | AI 생성 SOAP를 치료사가 직접 편집, (원본, 수정본) 쌍 저장 |
| Alarm 채택 확인 workflow | 알람 발생 후 "채택/기각" 결정 스텝 추가, 결과 저장 |
| 문서 검토/수정 UI | 의뢰서 등 생성 문서를 치료사가 검토·수정, 변경분 저장 |
| Paired data 추출 파이프라인 | 위 3종 데이터를 (raw, improved) 형태로 export 가능한 구조 |

**다음 단계 연결**: 수집된 paired data → Alarm 프로토콜 weight 갱신(Phase 8) → 클리닉별 개인화(Phase 9)

### Phase 8 상세 — Temporal Red Flag (시계열 알람 고도화)

**목적**: 단일 세션 점수 임계치 초과 방식에서, 세션 간 추세 패턴을 scorer에 반영

| 작업 | 설명 |
|------|------|
| CRA → scorer 연동 | `scorer.py`에 `patient_context` 인자 추가, trend=escalating 시 score +0.2 보정 |
| 가성 호전 경보 | 이전 RED → 현재 NONE 패턴 → "주의: 갑작스러운 점수 하락" 경고 |
| 연속 상승 선제 경보 | 아직 YELLOW 미달이지만 N주 연속 소폭 상승 시 조기 YELLOW 발령 |

**핵심 원칙**: CRA는 이미 trend/peak_score를 계산하나 scorer에 전혀 반영 안 됨 → 연결만으로 즉시 차별화 가능

---

### Phase 9 상세 — Treatment Response Tracking (치료 목표 달성률)

**목적**: `clinical_context` JSON 세션 간 비교 → progress note 자동화 + 치료 플랜 재설정 알람

| 작업 | 설명 |
|------|------|
| 세션 간 VAS/ROM 추적 | clinical_context의 통증 점수·관절가동범위를 시계열로 비교 |
| 목표 달성률 자동 계산 | 초기 설정 목표 대비 현재 수치 → % 달성률 |
| 정체 알람 | N주 연속 개선 없음 → "치료 플랜 재검토 권장" 알람 |
| Progress Note 초안 | 세션 변화량 기반으로 SOAP A/P 섹션 자동 생성 |

**GeneratedDocument 연결**: Phase 7 flywheel 구조를 progress note에도 적용 (chosen 선택 → few-shot 주입)

---

### Phase 10 상세 — Clinic Analytics Dashboard (센터장 대시보드)

**목적**: 누적 시계열 데이터 → 센터장 의사결정 지원 + 소송 방지 ROI 가시화

| 작업 | 설명 |
|------|------|
| 치료사별 리퍼럴 정확도 | 알람 채택/기각 이력 → 치료사별 민감도/특이도 |
| 평균 회복 세션 수 | 환자군·조건별 회복 곡선 집계 |
| 조기 리퍼럴 판단 근거 | "X주 이상 치료 시 회복 확률 Y% 이하" 임계점 자동 산출 |
| 소송 방지 금액 시뮬레이션 | 리퍼럴 건수 × 소송 평균 합의금 → "이번 분기 Z달러 리스크 방지" |
| Alarm weight 개인화 | 클리닉별 환자군 패턴 → 해당 클리닉 최적 임계치 자동 갱신 |

**데이터 해자 연결**: 클리닉별 개인화 weight는 경쟁자가 복제 불가한 핵심 IP

---

## RAG 로드맵 (전문용어 사전 기반 지식 검색)

RAG 인프라는 pgvector(기존 PostgreSQL 활용) + Gemini Embedding으로 구성. 3개 use case가 같은 벡터 DB를 공유.

| # | 목적 | 지식 소스 | 연결 지점 |
|---|------|-----------|-----------|
| RAG-1 | MCID / Skilled Care 입증 → 보험 승인율 향상 | MCID 공개 테이블 (ODI, NPRS, PSFS 등) | `documents.py` — progress note / discharge summary 생성 시 주입 |
| RAG-2 | Audit Defense → 법적 방어력 / 감사 대응 | APTA Clinical Practice Guidelines (공개 PDF) | 리퍼럴 레터 + 생성 문서에 가이드라인 조항 인용 + 링크 |
| RAG-3 | Goodman's 원문 근거 retrieval → 알람 신뢰도 향상 | Goodman & Snyder 챕터 (저작권 처리 후) | `referral.py` — triggered_condition → 관련 챕터 검색 → 레터에 원문 인용 |

### MVP 포함 여부

| # | MVP? | 판단 근거 |
|---|------|-----------|
| RAG-1 | MVP 제외 (v1.1) | 첫 고객 확보에 필수는 아님. JSON KB로 빠르게 추가 가능하므로 MVP 직후 투입 |
| RAG-2 | **v1.1 우선순위** | 현재 코드에 책 이름만 하드코딩 → 실제 원문 인용으로 바꾸면 보험 감사·소송 대응력 압도적 향상. 의미 있는 업그레이드 |
| RAG-3 | v1.2 | 저작권 해결 후. RAG-2와 동일 인프라 공유하므로 RAG-2 완료 후 빠르게 추가 가능 |

> **RAG-2 주의**: 현재 `referral.py`의 `"guideline": "Goodman & Snyder Ch.14"`는 책 이름 한 줄뿐.
> RAG-2 적용 후에는 실제 APTA CPG 원문 발췌 + 섹션 번호 인용이 레터에 포함됨 — 의사/보험사 신뢰도가 다른 차원.

### 구현 순서

1. **RAG-1 먼저** — MCID 테이블은 작은 JSON KB로도 충분, 벡터 DB 없이 즉시 가능
2. **RAG-2** — APTA CPG PDF 수집 → pgvector 청킹 → 감사 대응 인용 삽입
3. **RAG-3** — Goodman's 저작권 처리(출판사 라이선스 or 공개 인용 범위) → 챕터별 임베딩

### 핵심 원칙

- RAG는 **할루시네이션 방지 도구가 아님** — VPPS KB 매칭이 그 역할. RAG는 "근거 제시" 용도
- 생성이 아닌 **검색 후 인용** — LLM이 내용을 만들지 않고 원문 발췌 후 출처 표기
- 저작권 우선 해결 — Goodman's는 공개 인용 범위 확인 전까지 APTA CPG로 대체

---

## 인프라

- Cloud Run 서비스: `sagepontus` (asia-northeast1)
- git push → 자동 배포 (수동 gcloud deploy 불필요)
- Django + Next.js 별도 서비스
- DB: PostgreSQL (Cloud SQL)
