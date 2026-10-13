---
title: DCF·손상평가 외부평가보고서 리뷰 실무 — 외부 LLM 통합 초안 (소스 요약)
type: source
created: 2026-08-10
updated: 2026-08-15
domain: Deal Advisory
tags: [가치평가, DCF, 손상평가, 리뷰프레임워크, LLM재구성, 소스요약]
sources: ["DCF·손상평가 외부평가보고서 리뷰 실무.txt"]
---

# DCF·손상평가 외부평가보고서 리뷰 실무 — 외부 LLM 통합 초안 (소스 요약)

> [!quote] 출처
> 원본: `raw/재무자문/DCF·손상평가 외부평가보고서 리뷰 실무.txt` (불변, 수정하지 않음)
> 성격: **앞의 두 원자료를 외부 LLM이 하나로 통합해 만든 3차 가공물(통합 초안).** 원본 스스로 "실무 WIKI 정본에 가깝게 구성했다"고 밝히고 있으며, YAML frontmatter까지 붙어 있다.
> ⚠️ 그러나 이 저장소 기준으로는 **정본이 아니라 소스**다. 이유는 아래 참조.

## 강의 개요

외부평가보고서와 손상평가를 감사인 관점에서 검토하는 통합 초안이다. 앞선 원자료 2건을 외부 LLM이 재구성했으므로, 구조·질문 프레임은 활용하되 사실·수치의 근거는 1차 자료로 소급한다.

## 왜 이 문서를 그대로 정본으로 채택하지 않았는가

1. **frontmatter 스키마가 이 저장소 규약과 다르다.** `domain: 회계감사`, `topic:`, `subtopics:`, `status:` 를 쓰는데, CLAUDE.md 매핑표상 유효한 `domain` 값이 아니고 존재하지 않는 필드다.
2. **포지셔닝이 감사인 단일 관점이다.** 원본 0장이 "감사인이 검토할 때 필요한 판단체계"로 목적을 못박고 있어, **직접 가치평가를 수행하는 Valuation/Advisory 관점**이 구조적으로 빠져 있다. (매출을 "어떻게 추정하는가"가 아니라 "어떻게 검토하는가"만 있다.)
3. **1차 소스의 상당 부분이 소실됐다.** 시장접근법(GPC/GTC·EV multiple 일관성·경영권프리미엄·비유동성할인), PPA(MPEEM·RFRM·CAC·WARA), 금감원 외부평가업무 가이드라인, 별도 vs 연결 손상검사 구조, NWC 정상화 수치 예제, 추정기간 27년 vs 5년 비교, WACC 일반적 오류 11가지, Bottom-up 4개 사례의 세부 로직이 통합 과정에서 빠졌다.
4. **Source Index가 없다.** 어떤 결론이 어느 원자료 몇 페이지에서 나왔는지 추적 불가.

→ 따라서 정본 [[DCF-가치평가-및-평가보고서-검토-실무]]는 이 초안의 **좋은 골격을 흡수하되, 1차 소스로 되돌아가 누락분을 복원하고 Valuation 관점을 추가**해 다시 작성했다.

## 다룬 주제

- **STEP 1~10 리뷰 순서**: 평가대상·Carrying Amount → Forecast Accuracy → Revenue → Cost/Margin → CAPEX/Capacity/Dep → NWC → Terminal Value → WACC → Sensitivity → Disclosure Tie-out. "WACC부터 검토하는 것은 효율적이지 않다"는 원칙을 순서로 구현.
- **Matching Principle의 3자 확장**: Cash Flow ↔ Discount Rate ↔ **Carrying Amount**. (GPT 재구성본은 2자 또는 EV/CF/CA를 IFRS 16 맥락에서만 언급했는데, 이 초안이 문서 전체를 관통하는 원칙으로 승격시켰다.)
- **핵심 연결관계 체인**: Market → Share → Volume → Capacity → Headcount/CAPEX → Cost/Dep → NWC → FCFF → Terminal Normalization → WACC → Recoverable Amount → Carrying Amount. **정본이 이 체인을 문서의 중심 구조로 채택했다.**
- **Maintenance CAPEX vs Growth CAPEX 구분**을 Terminal 논의의 축으로 세운 것.
- **감사조서 작성 Framework 9단계**: Issue → Relevant Accounting Requirement → Management Position → Key Assumptions → Auditor Challenge → Audit Evidence → Recalculation/Cross-check → Sensitivity → Conclusion.
- **20개 질문 리스트**와 **Red Flag 체크리스트**(평가범위/Forecast/Revenue/Cost/CAPEX/NWC/Terminal/WACC/기타).
- **Headroom을 Materiality와 연결**하는 관점: "WACC +0.5%만으로 손상 발생"이면 감사위험이 높다.
- **2020년 자료 사용 시 3분류**: 현재도 유효한 일반원칙 / 당시 내부 실무관행 / 시점 의존 수치.
- **산업 사례 관점 정리**: 제약·바이오(질환별 시장·약가·계약만료·신약승인), 제조업(수주잔고·가동률·전가능력), 사양산업(산업 감소인데 매출 증가 시 요구되는 설명).

## 주의

이 초안에는 1차 소스에 없는 서술도 일부 있다(예: 경영자확인서의 증거력 한계, 외부평가인 활용 시 감사인의 책임 불이전). 감사기준 일반론으로 타당하나 **원자료에 근거 문장이 없으므로 정본에서는 `[LLM 해석]`으로 구분**했다.

## 관련 교재

- [[DCF-가치평가-및-평가보고서-검토-실무]] (신규 정본)
