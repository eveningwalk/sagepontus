# Sagepontus — 경쟁 전략 & 중장기 비전
> 작성일: 2026-05-30 | KAIST OverEdge AX-IV 지원서 참고용

---

## 1. 경쟁사 비교

| 기능 | WebPT | Prompt Sidekick | Prompt Insight | **Sagepontus** |
|------|-------|----------------|----------------|----------------|
| **포지셔닝** | EMR 플랫폼 | AI 문서화 | 코딩·컴플라이언스 | 임상 안전 특화 |
| EMR + 스케줄링 | ✅ | ❌ (WebPT에 올라탐) | ❌ | ❌ |
| AI SOAP 자동화 | ✅ | ✅ | ❌ | ✅ |
| 음성 → 텍스트 | ✅ | ✅ | ❌ | 구조만 |
| CPT 코딩 자동화 | ✅ | ❌ | ✅ | ❌ |
| 보험 청구 감사 방어 | ✅ | ❌ | ✅ | ❌ |
| **Red Flag 임상 스크리닝** | ❌ | ❌ | ❌ | ✅ |
| **의사 의뢰서 자동 생성** | ❌ | ❌ | ❌ | ✅ |
| **소송 방어 임상 문서** | ❌ | ❌ | ❌ | ✅ |
| **세션 간 악화 추이 감지** | ❌ | ❌ | ❌ | ✅ (CRA) |
| Chrome Extension (비침투형) | ❌ | ❌ | ❌ | ✅ |

### 포지셔닝 요약

- **WebPT**: PT 업계 EMR 점유율 ~40%. 청구·행정 효율화 중심. 업계 사실상 플랫폼(Salesforce 포지션).
- **Prompt**: 구 PredictionHealth (WebPT 공식 파트너 → rebranding). Sidekick=AI 문서화, Insight=코딩 컴플라이언스.
- **WebPT + Prompt 공백**: 두 제품 모두 *청구 컴플라이언스*에 집중. **임상 안전(Red Flag, 리퍼럴, 소송 방어)** 미포함.
- **Sagepontus**: 그 공백을 겨냥. 기존 EMR 위에 올라타므로 경쟁이 아닌 보완재 포지션.

### 컴플라이언스 유형 구분

| 구분 | 커버하는 제품 | 목적 |
|------|-------------|------|
| 보험 청구 컴플라이언스 | WebPT, Prompt Insight | 청구 거절(Denial) 방지, 감사 방어 |
| **임상 안전 컴플라이언스** | **Sagepontus** | Red Flag 누락 방지, 의료 소송 방어 |

---

## 2. WebPT 파트너 전략

### 기본 원칙
WebPT는 플랫폼. Sagepontus는 그 위의 임상 안전 레이어.  
Prompt가 파트너십으로 성장한 선례가 있으며, 동일 경로 활용 가능.

### 단계별 전략

| 단계 | 시점 | 내용 |
|------|------|------|
| **검증** | 지금 | Chrome Extension으로 WebPT 고객 대상 PMF 확인 |
| **파트너 등록** | 트랙션 확보 후 | WebPT 공식 마켓플레이스 입점 → 고객 발견 채널 확보 |
| **API 연동** | 파트너 확정 후 | WebPT FHIR API로 데이터 읽기 → DOM scraping 의존 탈피 |
| **Write-back** | 이후 | Sagepontus 결과 → WebPT에 역주입 → 워크플로우 완결 |

### Chrome Extension의 전략적 가치
- WebPT 고객이 별도 EMR 전환 없이 즉시 도입 가능
- 다른 EMR(Jane App, Clinicient 등)도 동시 커버 → WebPT 의존도 분산
- 트랙션 데이터로 WebPT 파트너 협상력 확보

---

## 3. 중장기 비전 — EMR 독립 임상 안전 레이어

### 비전 한 줄
> PT가 어떤 EMR을 쓰든, Sagepontus의 임상 안전 레이어 없이는 Direct Access 진료를 할 수 없는 세상.

### 3단계 로드맵

#### 1단계 — 파트너 (현재~2년)
- Chrome Extension으로 WebPT 위에서 임상 안전 검증
- 초기 고객 데이터(AuditPair) 축적 → 데이터 해자 형성 시작
- WebPT 파트너 마켓플레이스 입점

#### 2단계 — 레이어 (2~4년)
- EMR 종류 무관한 **임상 안전 미들웨어**로 포지셔닝
- FHIR(연방 표준 API) 클라이언트 구현 → EMR 독립

```
WebPT FHIR  ──┐
Jane App    ──┤  FHIR Client → Normalizer → VPPS 엔진 → Scorer
Clinicient  ──┘
```

- FHIR로 연결되는 SOAP 노트(`DocumentReference`), 환자 정보(`Patient`), VAS/ROM(`Observation`) 통합
- 어댑터 하나로 FHIR 지원 EMR 전부 커버

#### 3단계 — 스탠다드 (4년~)
임상 안전의 **사실상 규제 인프라**로 자리잡음

| 이해관계자 | Sagepontus에 원하는 것 |
|-----------|----------------------|
| 의료배상 보험사 | "이 솔루션 쓰면 보험료 할인" |
| 주(State) 면허 위원회 | Direct Access 확대 조건으로 Red Flag 도구 의무화 |
| 대형 PT 체인 | 전 지점 표준 임상 프로토콜로 도입 |
| EMR 벤더 | 임상 안전 커버 위해 Sagepontus 역으로 파트너 요청 |

### 데이터 해자가 스탠다드를 만드는 구조

```
AuditPair 누적 (치료사 교정 데이터)
    ↓
클리닉별 개인화 Weight 갱신
    ↓
경쟁사가 복제 불가한 임상 판단 정확도
    ↓
의료 소송 방어 실적 데이터 축적
    ↓
보험사·위원회가 Sagepontus를 기준으로 삼기 시작
```

PCI-DSS가 결제 업계 컴플라이언스 표준이 된 것처럼,  
Sagepontus가 PT 임상 안전의 컴플라이언스 레이어가 되는 것이 최종 목표.

---

## 4. 핵심 기술 차별화 요약

| 기술 | 설명 | 경쟁사 대비 |
|------|------|------------|
| **VPPS** | 비정형 SOAP → 임상 팩트 JSON 추출 (KB 매칭, 할루시네이션 배제) | WebPT/Prompt는 SOAP 생성에 집중, 임상 판단 없음 |
| **CRA** | 세션 간 시계열 누적 → 점진적 악화 패턴 감지 | 업계 어디도 세션 간 Red Flag 추적 없음 |
| **AuditPair** | 치료사 교정 행위 → paired data 축적 → 모델 개인화 | 데이터 해자, 복제 불가 |
| **Scorer** | Goodman's 가이드라인 기반 다중 프로토콜 채점 | 근거 기반 임상 로직, 법적 방어력 |
