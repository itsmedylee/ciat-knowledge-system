---
title: 외부평가보고서 검토 및 관련 유의사항 — 외부 LLM 재구성본 (소스 요약)
type: source
created: 2026-08-10
updated: 2026-08-15
domain: Deal Advisory
tags: [가치평가, DCF, WACC, PPA, 시장접근법, 손상평가, LLM재구성, 소스요약]
sources: ["외부평가보고서검토및관련유의사항_GPT.txt"]
---

# 외부평가보고서 검토 및 관련 유의사항 — 외부 LLM 재구성본 (소스 요약)

> [!quote] 출처
> 원본: `raw/재무자문/외부평가보고서검토및관련유의사항_GPT.txt` (불변, 수정하지 않음)
> 성격: **[[외부평가보고서검토및관련유의사항]]을 외부 LLM(GPT)이 학습용으로 재구성한 2차 가공물.**
> ⚠️ 법령·기준서·수치의 근거로 삼지 않는다. 인용은 1차 소스로 소급한다.

## 강의 개요

2020년 외부평가보고서 검토 교재를 외부 LLM이 기준서 원칙·가치평가 이론·당시 실무관행의 세 층으로 재구성한 학습자료다. 검토 프레임은 활용하되 수치는 원자료와 현행 기준을 확인한다.

## 다룬 주제

- **자료 안에 3층이 섞여 있다는 진단**: ① 기준서에서 직접 나오는 원칙 ② 가치평가 이론 ③ 2020년 당시 Deloitte VS 실무지침·관행. → 정본 문서의 "출처 층위 분리" 규칙이 여기서 왔다.
- **5개 질문**: 무엇을 평가하는가 → 어떤 현금흐름인가 → 위험을 할인율과 일관되게 반영했나 → 미래추정이 현실적인가 → 다른 시장정보와 비교해 말이 되는가.
- **3-Level 검토 프레임**: Level 1 Mechanical(산식) / Level 2 Internal Consistency(모형 내부) / Level 3 External Consistency(외부 현실). "실무에서 중요한 건 Level 2와 3, Level 1은 Excel 검산으로 잡힌다."
- **10개 체크리스트**: Valuation object → standard → method → business plan → revenue → margin → reinvestment → WACC → TV → cross-check.
- **학습 순서 제안**: FCFF/FCFE → Revenue~FCF → CAPEX/WC → WACC/CAPM/Beta → TV → 시장접근법 → 손상 → PPA. **"PPA를 앞에서 배우면 오히려 복잡해진다."**
- **"반드시 외워야 할 12개"** 와 **"외우지 말아야 할 것"** 의 명시적 구분.
- **Carrying amount ↔ Recoverable amount 원칙의 압축 표현**: "Left side와 right side의 **boundary**가 같아야 한다."

## 이 재구성본이 명시적으로 교정한 원자료 표현

| 원자료 표현 | 재구성본의 교정 |
|---|---|
| 한국 영구성장률 0~2% | 시점·관행. 기준은 inflation·GDP·산업 장기성장률·회사 maturity·pricing power이고 `g < WACC`가 필수 |
| BBB- 회사채 수익률, Bloomberg ERP, 5년 Monthly beta | 영구불변의 K-IFRS 요구사항이 **아님** |
| WARA ↔ IRR ↔ WACC 1% 이내 | IFRS rule이 아니라 **당시 실무 guideline** |
| Control premium / DLOM 수치 | 2020년 수치를 그대로 외우면 위험. 개념(Listed minority → control → liquidity)만 잡을 것 |
| DCF = 자동으로 control value | 정해진 것이 아니라 **현금흐름 assumptions가 어떤 권리를 반영하는지**가 결정한다 |

## 고유하게 정리한 개념 설명

- **왜 unlever 하는가**: 관찰된 beta에는 Business risk + Financial leverage가 섞여 있고, 우리가 원하는 것은 Business risk의 분리다.
- **CAC의 직관**: 고객관계 혼자서는 돈을 못 번다. 운전자본·공장·노동력·브랜드를 빌려 쓰므로 그 "사용료"를 내는 것으로 가정한다.
- **VIU vs Fair Value**: 같은 Excel DCF라도 VIU는 entity-specific, FV는 market participant — **assumptions의 출발점이 다르다**.
- **g = ROIC × Reinvestment Rate**: ROIC 10%, g 3%면 재투자율 30%가 필요하다는 항등식으로 "성장에는 돈이 든다"를 정량화.
- **실무형 문제 1건**: 매출 100→280(2.8배), EBIT margin 5%→18%인데 CAPEX 3 고정·ΔNWC 0인 모델. 초보는 WACC 8%부터 보고, 숙련자는 재투자 부재부터 묻는다.

## 관련 교재

- [[DCF-가치평가-및-평가보고서-검토-실무]] (신규 정본)
