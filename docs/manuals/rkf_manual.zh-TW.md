# RKF v1 研究者手冊

RKF 是 LLM Wiki-based research knowledge framework，核心路徑是 Paper →
locator-backed Evidence → human-reviewed Claim → Synthesis。

## Paper maturity

`access_state`：`metadata | abstract | partial | fulltext`。
`review_state`：`unread | skimmed | read | annotated | reproduced`。
Legacy reading label 只做保守 mapping；未知值成為 data-quality finding。

## 五條工作流

以下是 Codex app 的 Common Workflows：

- Add：保存 DOI、URL、PDF pointer、note 或 selected paper，不 promotion。
- Ask：先 deterministic retrieval；有 evidence claim 時必須附 locator。
- Read：記錄 annotation、correction 與 Evidence。
- Compare & Synthesize：保存 Claim/Synthesis 的 agreement、opposition 與 gap。
- Review：顯示可行動研究缺口與 connected-project lineage。

academic-research-suite 可搜尋、推理、寫作或 review，但輸出仍是 proposal，直到滿足
RKF evidence rules。

## Save rules

Candidate 與 LLM output 不是 evidence。Verified claim 必須有 human-verified、
locator-backed Evidence。PDF、article text、secret、private path 與 raw prompt 不進
public knowledge。
