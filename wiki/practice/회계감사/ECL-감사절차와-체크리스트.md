---
title: ECL 감사절차와 체크리스트
type: workflow
created: 2026-08-09
updated: 2026-08-09
domain: 회계
tags: [IFRS9, ECL, 감사절차, 체크리스트, PBC, RedFlag]
sources: [IFRS9-ECL-01-기초-완벽마스터, IFRS9-ECL-02-심화-모형이해, IFRS9-ECL-03-Final-실전문제-감사실무]
---

# ECL 감사절차와 체크리스트

> **업무 문서(practice)다.** 개념·근거는 복제하지 않고 정본 topic을 링크로 참조한다.
> 개념 정본: [[기대신용손실-ECL-계산구조]] · [[ECL-스테이지와-SICR]] · [[ECL-PD-부도확률]] · [[ECL-LGD-부도시손실률]] · [[ECL-EAD와-CCF]] · [[ECL-미래전망정보와-다중시나리오]] · [[ECL-모형검증과-오버레이]]

## 0. 감사 지도 — 3축

복잡한 ECL 조서를 받아도 길을 잃지 않는 압축 프레임.

| 축 | 질문 | 핵심 | 정본 |
|---|---|---|---|
| **A. Stage** | 누구에게 12개월 ECL을, 누구에게 Lifetime ECL을 적용했는가 | SICR | [[ECL-스테이지와-SICR]] |
| **B. Risk Components** | PD·LGD·EAD가 제대로 계산됐는가 | 데이터·세그먼트·Default·Lifetime 변환·담보·CCF·할인·비용 | [[ECL-PD-부도확률]] 외 |
| **C. FLI** | 미래경제 전망이 적절히 반영됐는가 | 변수·모델·시나리오·확률·Validation·Overlay | [[ECL-미래전망정보와-다중시나리오]] |

## 1. 조서를 받았을 때 읽는 순서 (STEP 1~9)

⚠️ **PD 파일부터 열지 않는다.**

| STEP | 무엇을 | 왜 |
|---|---|---|
| **1** | **충당금 Bridge** — 전기말 ECL → Stage 변화 → Exposure 변화 → RC 변화 → FLI 변화 → Overlay → 당기말 ECL | 전체 흐름을 먼저 잡고 **위험지역을 특정**한다 |
| 2 | Stage Distribution — Stage 1/2/3 잔액, 전기 대비 migration | Stage 2 비율 변동 원인 |
| 3 | SICR Policy — 신용등급·연체·Watchlist·자산건전성·정성 Trigger | 정책 변경 여부 |
| 4 | PD — 12M / Lifetime / FLI Adjustment / Segment | |
| 5 | LGD — 담보·회수율·할인율·회수기간·비용·담보배분 | |
| 6 | EAD — 특히 한도성 자산의 한도·사용잔액·CCF | |
| 7 | FLI — 변수·선택근거·시나리오·확률·전기 대비 변동 | |
| 8 | Validation Report — 모델 성능 미달, Override | |
| 9 | Overlay — 모델 밖 조정 금액 | |

### 1-1. Bridge로 감사자원을 배분한다

`[교육용 가상수치]` 전기말 2,500 → 당기말 3,500억원:

| 원인 | 효과 | 우선순위 |
|---|---:|---|
| Stage Migration | +450 | **1순위** — SICR 정책·Stage 1→2 이동이 최대 원인 |
| FLI | +200 | **2순위** — 주관성·모델링 판단이 큼 |
| PD 변경 | +100 | 3순위 — 모형·데이터 변경 원인 분해 |
| LGD 변경 | +100 | 3순위 |
| Exposure 증가 | +100 | |
| Overlay | +50 | 금액은 작아도 **수기 Judgment**이므로 별도 위험평가 |

> 원칙: 우선순위는 **금액만이 아니라 판단 개입 정도**를 함께 본다.

## 2. FINAL AUDIT WALK-THROUGH (7단계)

1. **회사의 ECL Architecture를 그린다**
   `Source Systems(대출·등급·연체·담보·한도·부도·회수) → Risk System(PD·LGD·CCF/EAD) → IFRS Adjustment(EIR·비용·IFRS Segment·Lifetime PD·FLI) → ECL Engine(Stage·Scenario·Probability Weighting) → Manual Adjustment(Overlay) → GL/재무제표`
   이 그림이 없으면 세부 Testing을 해도 전체 위험을 놓친다.
2. **Stage부터 본다** — Stage가 ECL Horizon을 결정하므로 첫 질문은 "Stage가 맞습니까?"
3. **Stage Migration을 본다** — 1→2, 2→1, 2→3, 3→2 이동에서 이상 Movement 탐색
4. **Risk Component를 본다** — PD(데이터·Default·Segment·12M·Lifetime·FLI) / LGD(Recovery·Discount·Cost·Collateral·Allocation) / EAD(Balance·Limit·CCF)
5. **FLI를 본다** — 변수·Source·시나리오 값·확률·비선형성 반영
6. **Validation을 본다** — 정책·정량기준·정성 타당성·기준 미달 시 대응
7. **Overlay를 본다** — Trigger·측정근거·Double Counting·Governance·Release 기준

## 3. Stage Migration 원인별 감사절차

Breakdown을 받아 Trigger별로 설계한다.

| Trigger | 절차 |
|---|---|
| 신용등급 하락 | 최초 등급 데이터 검증 · 현재 등급 검증 · Notch Mapping 검증 · SICR Threshold Reperformance (표본 계좌별 최초등급/당기말등급/Notch 변화/Stage 결과 재수행, 오류율 높으면 시스템 Logic 전체 검증) |
| 30일 연체 | 연체일수 Data Reconciliation · 기준일 Cut-off · 30일 초과 Logic 검증 · Rebuttal 존재 여부 |
| Watchlist | Watchlist Source 확인 · ECL 시스템 Interface 확인 · Population Completeness |
| 정성 Trigger | 적용사유 검토 · 경영진 Judgment · 승인근거 · Override 여부 |

## 4. 첫 PBC Request (4분류)

처음부터 수백 개를 요청하지 않고 구조적으로 요청한다.

| 분류 | 항목 |
|---|---|
| **1. Methodology** | ECL Methodology · SICR Policy · Default Policy · PD/LGD/EAD·CCF/FLI Methodology · Overlay Policy |
| **2. Results** | Stage별 Exposure · Stage Migration · PD Table · Lifetime PD Table · LGD Table · EAD/CCF · Scenario별 ECL · Overlay |
| **3. Validation** | PD/LGD/FLI Validation · Model Change History |
| **4. Data** | Loan Tape · Rating History · Delinquency · Collateral · Recovery · Default · Limit/Drawdown |

## 5. 영역별 체크리스트

### Stage / SICR → [[ECL-스테이지와-SICR]]
- [ ] 회사 SICR Policy 입수
- [ ] **최초인식 신용등급 관리(보관) 여부**
- [ ] 현재 신용등급 Tracking
- [ ] 연체 Trigger
- [ ] Watchlist Trigger
- [ ] 정성 Trigger
- [ ] **Stage Cure 기준**
- [ ] Override / Rebuttal
- [ ] Stage Migration 분석

### PD → [[ECL-PD-부도확률]]
- [ ] Default 정의
- [ ] Segment 정의
- [ ] 데이터 관측기간 (Credit Cycle 포괄성)
- [ ] 경험 PD
- [ ] Master Scale / 규제 PD 여부
- [ ] **IFRS Adjustment (보수적 마진 제거 등)**
- [ ] 12M PD
- [ ] Lifetime PD
- [ ] Lifetime 변환 Methodology
- [ ] FLI 반영 위치
- [ ] Validation

### LGD → [[ECL-LGD-부도시손실률]]
- [ ] 부도 Population
- [ ] Recovery Data
- [ ] Recovery Period (회수관찰기간 근거)
- [ ] Discount Rate / **EIR 사용 여부**
- [ ] 직접비 / 간접비 처리
- [ ] 담보가치 / 담보 Haircut
- [ ] 선후순위
- [ ] 1:N / N:1 / N:N 배분 로직
- [ ] **담보 Double Counting** (총 가용 회수액 vs 계좌별 배분액 합계 대사)
- [ ] Validation

### EAD / CCF → [[ECL-EAD와-CCF]]
- [ ] 현재잔액 / 한도 / 미사용한도
- [ ] CCF 산출 Population
- [ ] 관측기간 (Observation Window)
- [ ] 부도 직전 추가사용액 데이터
- [ ] Segment 일관성
- [ ] **난외(off-balance) Exposure**
- [ ] Negative CCF 처리방식
- [ ] Validation

### FLI → [[ECL-미래전망정보와-다중시나리오]]
- [ ] 거시경제변수 / 데이터 Source
- [ ] PD·LGD와의 방향성
- [ ] **정성적 타당성(경제적 설명가능성)**
- [ ] 후보모형 선정 과정 · Final Model Selection 근거
- [ ] Upside / Base / Downside 값의 Source
- [ ] Stress Scenario 연계
- [ ] **Probability Weight와 전기 대비 변경 근거**
- [ ] 비선형성 반영 (평균변수 단일 투입이 아닌지)
- [ ] Validation

### Overlay → [[ECL-모형검증과-오버레이]]
- [ ] Overlay 대상
- [ ] 기존 모형 미포착 근거
- [ ] 정량화 방식
- [ ] **FLI와 중복(Double Counting) 여부**
- [ ] 전기 대비 변경
- [ ] 분기별 재검토 여부
- [ ] 승인 (Governance)
- [ ] **Release(해제) 기준**

## 6. RED FLAGS — 보이면 바로 파고든다

| # | 신호 |
|---|---|
| 1 | 경기악화에도 **Stage 2 비율이 급감** |
| 2 | SICR 기준이 당기에 **완화** |
| 3 | Stage 2 **Cure가 급증** |
| 4 | Lifetime PD가 12M PD와 거의 차이 없음 |
| 5 | PD는 상승하는데 ECL은 크게 감소 |
| 6 | 담보평가액이 모두 EAD에 100% 적용 |
| 7 | 동일 담보가 여러 계좌에 중복 사용 |
| 8 | Downside Weight가 특별한 근거 없이 감소 |
| 9 | 통계적으로 좋은 모델만 설명하고 경제적 근거가 없음 |
| 10 | Validation 기준 미달인데 조치 없음 |
| 11 | Overlay가 매년 같은 금액 |
| 12 | Overlay 해제기준이 없음 |
| 13 | Risk PD를 IFRS에서 아무 조정 없이 사용 |
| 14 | FLI가 사실상 Base Case 하나 |
| 15 | 모형 변경 결과 충당금이 크게 감소했는데 변경근거가 빈약 |

### 6-1. 개별 항목보다 "방향성"을 본다

다음이 동시에 나타났다고 하자 — Stage 2 비율 급감 / 경제전망은 악화 / Downside Weight 감소 / 일부 Segment Validation 기준 미달 / Overlay 축소.

각각을 개별적으로 틀렸다고 단정할 수는 없다. 그러나 **전체가 일관되게 충당금 감소 방향으로 움직이는 것 자체가 Risk Signal**이다. Possible Management Bias를 염두에 두고 SICR Policy 변경 · Stage Cure 기준 · Scenario Weight · FLI Model 변경 · Validation 미달 대응 · Overlay Release 근거 · 경영진 승인자료를 **연결해서** 본다.

## 7. Partner/Manager 30초 답변

| 질문 | 답변 |
|---|---|
| "Stage 2가 왜 중요해?" | Stage 1은 12개월 ECL이지만 SICR이 발생해 Stage 2로 가면 Lifetime ECL을 측정하므로 충당금이 크게 증가할 수 있습니다. 그래서 Stage 2 판단기준과 Migration이 ECL 감사 핵심입니다. |
| "PD 검토 핵심은?" | Default 정의, Segment, 산출 데이터, 12M→Lifetime 변환, FLI 반영, Validation입니다. 특히 리스크 목적 PD를 IFRS 목적에 맞게 어떻게 조정했는지가 중요합니다. |
| "LGD에서 제일 위험한 게?" | 회수율 산출도 어렵지만 **실제 계좌에 담보를 배분하는 과정**이 더 복잡합니다. 1:N, N:1, N:N 담보와 선후순위, 담보 중복배분이 핵심 위험입니다. |
| "FLI는 뭘 보는 거야?" | 어떤 거시변수를 왜 선택했는지, 시나리오 값과 발생확률의 근거, 복수 시나리오와 비선형성이 적절히 반영됐는지를 봅니다. |
| "Overlay가 뭐야?" | 기존 모델이 포착하지 못하는 추가위험을 모델 밖에서 보정하는 것입니다. 필요성, 금액 산정근거, FLI와의 중복, 해제기준이 중요합니다. |

## 8. 사고방식 — 숫자가 맞는 것과 추정이 맞는 것

ECL 감사는 **Arithmetic Audit이 아니라 Estimation Audit**이다. 조서의 한 행을 볼 때 초보자는 `11% × 42% × 100`을 계산하지만, 숙련자는 먼저 묻는다 — Stage는 왜 2인가 / PD 11%는 12M인가 Lifetime인가 / LGD 42%는 어떤 회수·담보·할인 가정인가 / EAD 100은 현재잔액인가 부도시 노출액인가 / FLI는 PD에 들어갔나 LGD에도 들어갔나 / 이 수치는 단일 시나리오인가 확률가중인가 / Validation 결과는 정상인가 / Overlay가 포함되어 있나.

배경 프레임은 [[기대신용손실-ECL-계산구조]] 5-2 (**DATA → MODEL → JUDGMENT**).

## 9. 출처

[[IFRS9-ECL-01-기초-완벽마스터]] (PART 19·20·23·24), [[IFRS9-ECL-02-심화-모형이해]] (PART K·L·M), [[IFRS9-ECL-03-Final-실전문제-감사실무]] (종합문제 2~4, FINAL WALK-THROUGH, 체크리스트, RED FLAGS)

> ⚠️ 이 체크리스트는 2023년 교재·강의 기반 2차 가공물에서 도출한 것이다. 실제 감사 적용 시 소속 법인의 감사방법론·현행 감독지침을 우선한다 `[현행 기준 확인 필요]`.
