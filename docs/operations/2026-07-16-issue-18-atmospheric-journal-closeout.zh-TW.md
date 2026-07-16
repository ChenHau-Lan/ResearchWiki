# Issue #18 大氣期刊 Acquisition 對話與決策摘要

日期：2026-07-16
狀態：portable-core slice 完成並驗證；GitHub issue #18 尚未關閉
紀錄型態：使用者明確要求保存的 public-safe conversation/decision summary

## 保存邊界

本檔是本次 Codex 對話的決策與工作摘要，不是逐字 transcript。依 RKF public/private
邊界，未保存 raw prompts、PDF、article text、artifact hash、credentials、private
temporary path 或使用者機器細節。這份摘要不可單獨作為 Evidence 或 Claim support，
所有 acquisition 結果維持 `Promotion: none`。

## 使用者需求摘要

1. 參考 issue #18 identifier-adapter smoke 與 upstream `paper-fetch`，讓大氣研究常用
   期刊的代表 paper 能由 lawful publisher／OA／repository route 順利取得。
2. 不停在初步測試；持續處理 provider、repository migration、provenance 與安全問題，
   直到 bounded corpus 成功。
3. 將不同期刊的成功下載方法整理成可重用紀錄，讓未來同一期刊的新 DOI 優先嘗試
   相同 route ladder。
4. 將本次對話保存成 durable、public-safe 的專案紀錄。

## 共同決策

- 工作定位為 issue #18 的 **portable-core slice**，不新增第六個 user workflow；
  acquisition 仍是 Add 的 internal provider。
- 只使用 official publisher、authoritative metadata、current PMC Open Data Cloud 與
  authorized repository。SSO、CAPTCHA、paywall、robots 或 anti-bot surface 只做
  detect + stop，不繞過。
- 建立 11 個 P0 與 3 個 P1 大氣期刊代表案例；bounded result 只支持這 14 篇在該次
  run 的結果，不宣稱期刊所有文章都可下載。
- `research_ready_verified` 與 provenance review 分離。Unknown version、空 license、
  accepted manuscript 與 preprint 都保留原分類，不為了達成成功率而升格成 VOR。
- Raw PDF 與 private report 必須留在 repository 外的新 owner-only boundary，不能
  overwrite、commit 或發布。

## 執行與除錯摘要

1. 讀取 issue #18 benchmark、provider contract、upstream pinned `paper-fetch` 與既有
   RKF schema/lineage boundary。
2. 建立 portable acquisition provider、multi-identifier adapters、private artifact
   storage、smoke runner、public corpus 與 deterministic fixtures。
3. 增加 Crossref version-scoped license、current PMC version、conservative MDPI/PMC/
   generic landing classification，以及 exact DOI/title PDF identity gate。
4. 安全稽核後補上 connected-peer validation、IPv6 transition/NAT64 private-address
   rejection、HTTPS/same-origin secret handling、32-request shared budget、strict external
   route allowlist 與 concurrent no-replace checksum storage。
5. AMS 代表案例在 Iowa State repository migration 後出現舊 Digital Commons URL
   不穩定。最後以 OpenAlex repository landing 的 HTTP Signposting PDF item，轉到
   same-origin DSpace REST bitstream，通過 PDF 與 DOI identity gate。
6. 使用完全相同的最終程式執行 designated final run；14/14 `obtained`、14/14
   `research_ready_verified`，共觀察到 9 個 final route labels。

## 最終結果

- 14 個代表案例全部取得 PDF。
- 14 個 artifact 全部為 `readable`、identity `verified`，有頁數與 locator readiness。
- 5 個 artifact version 仍為 `unknown`。
- 8 個 artifact 沒有 machine-recorded license。
- IOP 代表檔案保守記為 `accepted-manuscript`。
- 所有結果為 `Promotion: none`；沒有建立或升格 Evidence、Claim 或 Synthesis。

## 交付物

- [期刊 route playbook](atmospheric-journal-acquisition-route-playbook.zh-TW.md)
- [14-case corpus](../benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json)
- [14-case public-safe live result](../benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md)
- [vNext acquisition reference](../references/vnext-acquisition.md)
- `rkf/acquisition.py`
- `tools/test_paper_acquisition.py`
- `tests/test_rkf_acquisition.py`
- `tests/test_paper_acquisition_tool.py`

## 驗證紀錄

- 492 unit tests passed。
- Python compilation passed。
- Canonical schema validation passed。
- RKF all/topic/graph lint passed。
- Public-safety scan passed。
- `git diff --check` passed。
- Designated final run 的 raw report 與 public corpus `live_outcome` 逐欄比較為
  14/14 exact match。

## 尚未完成／不應誤解

- Issue #18 仍保留 native institutional/browser adapters、獨立 HTML/JATS/XML artifact、
  broader multi-artifact relationship、wall-clock streaming deadline 與 external adapter
  stdout/stderr resource bounds 等工作。
- 代表案例成功不等於 provider 永久可用；repository migration、publisher policy、
  metadata index 與 access response 都可能改變。
- 未知 version／license 必須人工 review；不得用下載成功率取代 provenance 判斷。
- 在 2026-07-16 designated validation 階段尚未 commit、push 或 close issue；raw
  artifact 未發布。後續建立 commit／PR 仍不代表 issue #18 已全部完成。

## 後續重用指令

未來遇到同一期刊 DOI 時，先讀 route playbook，依 DOI family 使用相同 route ladder；
只有 metadata 或使用者明確提供時才能重用 article-specific alternate identifier。任何
新 live outcome 應寫入新 output directory，再更新 dated public-safe record，不能覆寫
這次 observation。
