---
title: IFRS9 ECL 03 Final 실전문제·감사실무 (소스 요약)
type: source
created: 2026-08-09
updated: 2026-08-09
domain: 회계
tags: [IFRS9, ECL, 감사절차, 문제집, 소스요약]
---

# IFRS9-ECL-03-Final-실전문제-감사실무 (소스 요약)

> 원본: `raw/회계자문 및 회계감사/About ECL/IFRS9-ECL-03-Final-실전문제-감사실무.md` (불변, 수정하지 않음)
> 원본이 밝힌 근거: 2023 Deloitte Anjin IFRS 9 ECL 교재 + 강의 녹취 기반 2차 가공물.
> ⚠️ 원본이 스스로 명시: **"문제에 등장하는 차주명·금액·등급·확률은 학습용 가상수치"**. Stage 구조·RC·SICR·FLI·다중시나리오·Validation·Overlay의 논리만 교재·녹취를 따른다.

## 성격

3부작 중 **3편(실전)**. 읽는 자료가 아니라 **푸는 자료**. 문제 23개 + 종합문제 4개 + Final Walk-through + 체크리스트 + RED FLAGS + 30초 답변으로 구성된다. 위키에서는 문제 자체를 정본 지식으로 옮기지 않고, ① 문제가 검증하는 **개념**은 각 topic으로, ② 체크리스트·RED FLAGS·Walk-through는 **practice 레이어**로 분리했다.

## 문제 구성

| 문제 | 검증 개념 | 답 |
|---|---|---|
| 1 | 기본 ECL | 100 × 2% × 40% = 0.8억 |
| 2 | Stage 1 → 2 | 4.8억(6배 증가). ⚠️ 2편의 12배 사례와는 12M PD 전제가 다름 |
| 3 | Stage 3분류 판단 | A=Stage 1 / B=Stage 2(3 Notch 하락) / C=Stage 3(100일 연체·채무재조정) |
| 4 | Stage 3 ≠ 100% 충당금 | 100 × 100% × 35% = 35억 |
| 5~6 | CCF | EAD = 40 + 60×50% = 70억 / CCF는 결과 재계산이 아니라 Population·정의·관측기간 검증 |
| 7~9 | LGD | 단순 35% → EIR 5% 할인 PV 64.88억(35.12%) → 비용 PV 4억 반영 시 **39.12%** |
| 10 | 담보 LGD | 예적금 50 + 주식 24 + 신용 14.3 = 88.3 회수 → 손실률 11.7% + 간접비 2% = **13.7%** (1편·교재와 동일 구조) |
| 11~12 | 담보 Double Counting / 선후순위 | 동일 담보 100을 두 계좌에 각 100 반영 = 이중계상 → ECL 과소계상. 비례배분(60/60)이 항상 옳지 않음 |
| 13~15 | FLI | 2% × 1.25 = 2.5% / 음반판매량 vs 기업대출 연체율(경제적 설명가능성) / ECL이 가장 낮은 모형 선택 = Management Bias |
| 16~19 | 다중 시나리오 | 확률가중 149.5 ≈ 150 vs Base 100 / 평균변수 단일 투입 부적절 / Downside Weight 20%→30% 근거 / Stress Test 최악 시나리오 연계(20% 이상, `[2023 교재 기준]`) |
| 20~21 | Validation | 예측 1.2% vs 실제 3.8%가 3년 반복 = 지속적 과소추정 / "크게 이상하면 수정"은 Performance Standard 부재 |
| 22~23 | Overlay | 4대 질문 / 위험이 정상화됐는데 "보수적으로 유지"는 과대계상 — IFRS 추정은 보수주의가 목적이 아님 |
| 종합 1~4 | 계좌 끝까지 계산(4.4억) / Bridge 기준 감사자원 배분 / Stage Migration 원인별 절차 설계 / **가정들이 일제히 낙관적으로 이동하는 패턴** = Management Bias 신호 |

## 실무 산출물 (practice로 이관)

- **FINAL AUDIT WALK-THROUGH** 7단계(Architecture → Stage → Migration → RC → FLI → Validation → Overlay)
- **ECL 감사 체크리스트** 6영역(Stage/SICR·PD·LGD·EAD/CCF·FLI·Overlay)
- **RED FLAGS 15개**
- Partner/Manager 30초 답변, 자기점검 Level 1~10
- ECL 숫자의 3요소 프레임: **DATA → MODEL → JUDGMENT** (뒤로 갈수록 감사위험 증가)

→ 모두 [[ECL-감사절차와-체크리스트]]에 수록. 개념 근거는 각 topic 링크로 참조하고 법리를 복제하지 않는다.

## 이 소스가 만들거나 갱신한 위키 페이지

[[기대신용손실-ECL-계산구조]] · [[ECL-스테이지와-SICR]] · [[ECL-PD-부도확률]] · [[ECL-LGD-부도시손실률]] · [[ECL-EAD와-CCF]] · [[ECL-미래전망정보와-다중시나리오]] · [[ECL-모형검증과-오버레이]] · [[ECL-감사절차와-체크리스트]] · [[IFRS9-ECL-완전학습가이드]]
