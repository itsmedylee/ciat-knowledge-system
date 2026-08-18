---
title: Deal VS 과거 이슈사항 및 평가사례 — 외부 LLM 재구성본 (소스 요약)
type: source
created: 2026-08-10
updated: 2026-08-15
domain: Deal Advisory
tags: [가치평가, DCF, WACC, PGR, TerminalValue, LLM재구성, 소스요약]
sources: ["Deal VS 과거 이슈사항 및 평가사례_GPT.txt"]
---

# Deal VS 과거 이슈사항 및 평가사례 — 외부 LLM 재구성본 (소스 요약)

> 원본: `raw/재무자문/Deal VS 과거 이슈사항 및 평가사례_GPT.txt` (불변, 수정하지 않음)
> 성격: **[[Deal VS 과거 이슈사항 및 평가사례]]를 외부 LLM(GPT)이 학습용으로 재구성한 2차 가공물.** 새로운 사실을 담고 있지 않으며, 원자료의 사례를 리뷰 논리로 재배열한 것이다.
> ⚠️ 이 문서 자체는 **법령·기준서·수치의 근거가 될 수 없다.** 인용은 항상 1차 소스로 소급한다.

## 강의 개요

2020년 Deal VS 사례집을 외부 LLM이 학습용 검토 순서와 Red Flag 체계로 재배열한 2차 자료다. 새로운 사실보다 반복 가능한 리뷰 프레임을 제공하는 데 가치가 있다.

## 다룬 주제

원자료가 "Issue 1~4 + 사례"의 나열이라면, 이 재구성본은 **하나의 반복 가능한 사고순서**를 뽑아냈다. 정본 문서의 STEP 구조와 Red Flag 분류는 상당 부분 여기에서 왔다.

- **5개 질문 프레임**: ① 시장과 맞나 → ② 과거 실적과 맞나 → ③ 서로 논리적으로 맞나 → ④ 실제 실행 가능한가 → ⑤ 영구히 지속 가능한가.
- **리뷰 순서의 재배치**: Forecast Accuracy → 매출 decomposition → Operating leverage → NWC → Terminal normalization → **WACC를 마지막에**. 근거: "DCF value를 크게 왜곡시키는 것은 WACC 0.3% 차이보다 비현실적인 매출·마진·TV인 경우가 훨씬 많다."
- **Red Flag를 매출/비용/CAPEX/NWC 4계열로 분류.**
- **Forecast Error를 3분해**: External factor / Company-specific factor / **Forecast bias**. 세 번째가 반복되면 경영진 forecast reliability 자체가 이슈.
- **Market Value Growth = Volume Growth + Price/Mix Effect** 항등식으로 Top-down 함정을 일반화.
- **6개 공식을 "질문 생성기"로 쓰라는 관점**: Volume↑→CAPA? / Price↑→경쟁력? / Share↑→경쟁사? / Margin↑→Cost driver? / CAPEX↓→성장 가능? / g↑→경제 전체보다 계속 빨리?
- **외워야 할 질문 15개** 리스트.

## 이 재구성본이 명시적으로 교정한 원자료 표현

정본 문서의 "과거 관행 vs 일반원칙" 분리는 이 지적을 반영한 것이다.

| 원자료 표현 | 재구성본의 교정 |
|---|---|
| PGR 1% 초과 시 검토 | 당시 내부 **review trigger**일 뿐. K-IFRS 1036의 요구는 "장기평균성장률 초과 시 정당화"이지 1%가 절대기준이 아니다 |
| Kd는 IFRS 16 증분차입이자율보다 높아야 한다 | 강한 실무 heuristic이지 IFRS상 일반 규칙이 아니다 |
| 특정 신용등급·만기 회사채를 써야 한다 | 절대규칙 아님 |
| 특정 Beta 기간이 정답 | 정답은 없고 **"왜 그 측정기간·빈도·평균방법인가"** 를 묻는 것이 검토논리 |
| 기능통화와 WACC 통화가 같아야 한다 | 정확히는 **현금흐름에 내재된 통화·인플레이션 가정과 할인율이 일치**해야 한다 |
| Terminal CAPEX = 마지막 연도 Dep | 기계적 적용 금지. 질문은 "현재 operating capacity를 영구 유지하는 maintenance CAPEX가 얼마인가" |

## 고유하게 강조한 감사 논리 하나

**VIU × CAPEX 결합 논증**: 매출 5배 → 판매량 5배 → 현재 CAPA로 불가 → 신규 CAPEX 필요 → 그런데 그 CAPEX가 K-IFRS 1036상 VIU에서 허용되지 않는 **성능향상 CAPEX**라면, **애초에 그 매출성장 추정 자체가 VIU에 들어올 수 없다.** 원자료에도 재료는 있으나 이 결합을 한 문장으로 세운 것은 재구성본이다.

## 관련 교재

- [[DCF-가치평가-및-평가보고서-검토-실무]] (신규 정본)
