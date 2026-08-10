---
title: IFRS9 ECL 02 심화·모형이해 (소스 요약)
type: source
created: 2026-08-09
updated: 2026-08-09
domain: 회계
tags: [IFRS9, ECL, 신용리스크, 모형검증, 소스요약]
---

# IFRS9-ECL-02-심화-모형이해 (소스 요약)

> 원본: `raw/회계자문 및 회계감사/About ECL/IFRS9-ECL-02-심화-모형이해.md` (불변, 수정하지 않음)
> 원본이 밝힌 근거: 2023 Deloitte Anjin IFRS 9 ECL 교재 + 강의 녹취 기반 2차 가공물.
> ⚠️ 원본이 스스로 명시: **"아래 숫자 사례 중 강의에 직접 없는 숫자는 개념 이해를 위해 새로 만든 교육용 예시"**. 따라서 이 소스의 수치는 원칙적으로 `[교육용 가상수치]`이며, 실제 회사·감독 데이터가 아니다.

## 성격

3부작 중 **2편(심화)**. 1편이 "무엇인가"라면 2편은 **"숫자를 해체한다"**. ECL을 하나의 공장(원재료→1·2·3차 가공→사후조정→완제품)으로 보고, 각 공정에서 감사인이 무엇을 묻는지를 계산 예시와 함께 전개한다.

## 다룬 내용 (원본 PART 구성)

| 구간 | 내용 |
|---|---|
| 1~2 | "PD·LGD·EAD 세 숫자만 검증하면 된다"는 착각 버리기, ECL 공장 비유(원재료 → 세그먼트·Default·SICR·Stage → RC → FLI·Scenario → Overlay → 완제품) |
| PART A | 경험 PD 산출표(5개년, 단순평균 2.01%)와 그 즉시 나오는 감사질문 3개, 생존 기반 Lifetime PD(0.98⁵ → 5년 누적 9.61% vs 단순합 10%), Marginal PD / Cumulative PD 기간구조, Weibull은 정답이 아니라 "만기별 부도패턴을 설명하는 근거"가 핵심 |
| PART B | Stage 1(12M PD 1%) 0.4억 vs Stage 2(Lifetime PD 12%) 4.8억 = **12배** 사례, 두 효과 분해(Credit Quality Effect + Horizon Effect), SICR Test 실제 절차 5단계(정책·데이터·Notch Mapping·누락 Trigger·Rebuttal/Override) |
| PART C | LGD를 현금흐름으로: 명목회수 70억(단순 LGD 30%) → EIR 5% 할인 시 PV 64.88억(LGD 35.12%) → 회수비용 PV 3억 반영 시 **38.12%**. "늦게 받는 것도 손실" |
| PART D | 담보배분: 2계좌:1담보에서 비례배분(60/60) vs 선후순위(100/20)에 따라 계좌 LGD가 완전히 달라짐. 담보 중복사용·Haircut·회수기간이 실제 위험 |
| PART E | CCF 재확인(40 + 60×50% = 70)과 그 뒤에 숨은 데이터 정책(Population·Observation Window·Default Point·Negative CCF) |
| PART F | TTC/PIT 감각, FLI multiplier 예시(2%×1.20 = 2.4%, 0.9면 1.8%로 **감소도 가능**), 아이스크림 판매량 사례(Statistical significance ≠ Economic validity), 후보모형 100→30→10→3→1 축소 과정의 일관성과 Management Bias |
| PART G~H | 평균변수 단일 투입(ECL 100) vs 시나리오별 확률가중(≈150), Downside에서는 PD뿐 아니라 LGD도 함께 악화되어 곡선이 위로 휨. Stage 축과 FLI 축은 별개 |
| PART I~J | Validation: 예측 PD 1% vs 실제 3% 사례, Backtesting, **사전 Performance Standard가 없으면 Validation이 아니다**, Recalibration vs Redevelopment 구분. Overlay 4대 질문(왜 필요·왜 그 금액·Double Counting·해제기준) |
| PART K~Q | 가상 은행 Walk-through: 총 ECL 2,200 → 3,000 Bridge 분해(Stage Migration +400이 최대) → 감사자원 배분, Stage Migration Breakdown 검증, PD/LGD 증가 원인 분리, Downside Weight 20%→30% 근거, PBC Request 4분류(Methodology/Results/Validation/Data), ECL의 5층(Classification·Data·Model·Assumption·Governance), 자주 헷갈리는 질문 6개(48~53) |

## 이 소스가 만들거나 갱신한 위키 페이지

1편과 동일한 정본 페이지군에 **심화 계산·감사 절차 층**을 누적: [[기대신용손실-ECL-계산구조]](공장 비유·5층) · [[ECL-스테이지와-SICR]](12배 사례·SICR Test 5단계) · [[ECL-PD-부도확률]](생존기반 누적·Marginal/Cumulative) · [[ECL-LGD-부도시손실률]](현금흐름 할인·담보배분) · [[ECL-EAD와-CCF]](CCF 데이터 정책) · [[ECL-미래전망정보와-다중시나리오]](multiplier·후보모형 축소) · [[ECL-모형검증과-오버레이]](Performance Standard·Recalibration/Redevelopment) · [[ECL-감사절차와-체크리스트]](Bridge·PBC)

## 주의

- **12배(2편)와 6배(3편 문제2)는 모순이 아니다.** 2편은 12M PD 1% 전제, 3편은 12M PD 2% 전제로 Stage 1 ECL이 다르다. 두 예시 모두 Stage 2 ECL은 4.8억원으로 같다. → [[ECL-스테이지와-SICR]]에 전제와 함께 기록.
- 회수비용 반영 후 LGD도 2편은 38.12%(비용 PV 3억), 3편은 39.12%(비용 PV 4억)로 **전제가 다른 별개 예시**다.
