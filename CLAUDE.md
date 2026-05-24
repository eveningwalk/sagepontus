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

### Phase 7 상세

**목적**: AI 출력물에 대한 임상가 교정 행위를 데이터로 축적 → copy cat 대비 데이터 해자 구축 + Alarm weight 개인화 기반 마련

| 작업 | 설명 |
|------|------|
| SOAP 수정 UI | AI 생성 SOAP를 치료사가 직접 편집, (원본, 수정본) 쌍 저장 |
| Alarm 채택 확인 workflow | 알람 발생 후 "채택/기각" 결정 스텝 추가, 결과 저장 |
| 문서 검토/수정 UI | 의뢰서 등 생성 문서를 치료사가 검토·수정, 변경분 저장 |
| Paired data 추출 파이프라인 | 위 3종 데이터를 (raw, improved) 형태로 export 가능한 구조 |

**다음 단계 연결**: 수집된 paired data → Alarm 프로토콜 weight 갱신(Phase 8) → 클리닉별 개인화(Phase 9)

---

## 인프라

- Cloud Run 서비스: `sagepontus` (asia-northeast1)
- git push → 자동 배포 (수동 gcloud deploy 불필요)
- Django + Next.js 별도 서비스
- DB: PostgreSQL (Cloud SQL)
