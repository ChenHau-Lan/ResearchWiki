# 大氣期刊全文取得 Route Playbook

狀態：active operational reference
最後驗證：2026-07-16
適用範圍：GitHub issue #18 portable-core acquisition slice

這份 playbook 保存 14 個大氣期刊代表案例實際成功的 route，以及同一期刊新文章
應如何重試。它記錄的是「可重用的選路方法」，不是保證每篇文章都能下載，也不是
把代表案例的 article-specific URL 套到其他文章。

## 使用原則

1. 先正規化 DOI，依 DOI prefix 選 publisher profile。Profile 本身只提供最後的
   landing／routing hint；少數已驗證 DOI family／pattern 另會生成 bounded official
   或 TDM candidates。Prefix 不直接證明 access、artifact version 或 license。
2. 先用 Crossref／DataCite 建立 identity，再查看 OpenAlex、Semantic Scholar、
   Unpaywall（僅在設定真實 contact email 時）與明確 repository identifier。
3. DOI 若由 NCBI ID Converter 對應到 PMCID，才測 current PMC Open Data Cloud；
   必須通過 DOI、OA、retraction 與 current-version gate。
4. 只使用 publisher、authoritative metadata、官方 repository 或使用者明確提供的
   lawful artifact。遇到 `401`／`403`、SSO、CAPTCHA、robots 或 anti-bot surface
   時 detect + stop，不繞過。
5. 每個 PDF 都重新執行 magic/EOF、頁數、文字層、完整 DOI token 或 distinctive
   title identity、locator-readiness 與 checksum gate。
6. `research_ready_verified=true` 只表示 artifact 可讀且 identity 已驗證；它不等於
   Version of Record、license 已確認、Evidence 已審查或 Claim 已驗證。

## 期刊／Publisher Route Registry

| 期刊／DOI family | 2026-07-16 成功 route | 同期刊新文章的建議順序 | 不可過度泛化的邊界 |
|---|---|---|---|
| AGU Advances／AGU-Wiley `10.1029` | `openalex-landing.citation-meta`，取得 repository preprint | Crossref identity → OpenAlex/Unpaywall OA locations → AGU/Wiley official PDF → 已授權 Wiley TDM | 代表案例的 repository URL 不可套用到其他 DOI；preprint 不是 VOR。 |
| Quarterly Journal of the Royal Meteorological Society／Wiley `10.1002` | 明確 `NOAA:71054` → `noaa-ir-landing.citation-meta` | Crossref/OpenAlex 尋找 lawful repository PID → 若已取得 exact PID，優先試該 explicit alternate → Wiley official route／已授權 TDM／DOI landing | `NOAA:71054` 只屬於該篇代表文章；其他 QJRMS 文章不可猜 NOAA PID。 |
| Weather and Forecasting／AMS `10.1175` | `openalex-landing.citation-meta`：repository landing → HTTP Signposting PDF item → same-origin DSpace REST bitstream | Crossref identity／OA metadata → OpenAlex/Unpaywall repository → AMS DOI landing/citation metadata → Signposting PDF item → DSpace REST content | Core 沒有獨立 `ams-official-pdf` route；AMS publisher `403` 不是 unavailable，Digital Commons 舊 URL 遷移後不可硬編舊 `viewcontent.cgi`。 |
| Atmospheric Measurement Techniques／Copernicus `10.5194` | `copernicus-direct` DOI-derived publisher PDF | 驗證 DOI pattern → Copernicus direct PDF → official landing metadata → Crossref/OpenAlex | 只有符合 Copernicus DOI 結構時才組 direct URL；HTML/XML 目前只協助 discovery。 |
| Atmospheric Environment／Elsevier `10.1016` | current NCBI ID Converter → `ncbi-pmc-cloud` | Crossref/OpenAlex → current PMC Cloud（僅 OA subset）→ official landing → 已授權 Elsevier TDM | PMCID 與 PMC OA 必須逐篇確認；`is_manuscript=false` 不能推論為 VOR。 |
| Climate Dynamics／Springer `10.1007` | `springer-official-oa` publisher PDF | Springer official OA PDF → Crossref/OpenAlex OA → DOI landing | Direct publisher route 仍須 PDF/identity gate；不得因同 prefix 假設每篇 OA。 |
| Communications Earth & Environment／Nature `10.1038` | `crossref-link`，metadata 明確標示 `content-version=vor` | Crossref artifact link → Nature official PDF → OpenAlex/landing | License 只可套用到相同 content version 且已生效的 exact artifact。 |
| Environmental Research Letters／IOP `10.1088` | `crossref-link`，該檔案為 `accepted-manuscript` | Crossref link → IOP official PDF → OpenAlex/Unpaywall | 代表檔案不是 VOR；不可把 VOR-scoped license 複製到 accepted manuscript。 |
| ACS ES&T Air／ACS `10.1021` | current NCBI ID Converter → `ncbi-pmc-cloud` | Crossref/OpenAlex → current PMC Cloud（若存在）→ ACS official PDF/landing | PMC membership 是 article-specific；non-manuscript PDF 的版本保持 `unknown`。 |
| Science／AAAS `10.1126` | `openalex-landing.citation-meta`，取得 repository preprint | Crossref/OpenAlex repository → Unpaywall → publisher landing/manual resolver | 不假設 Science VOR 為 OA；repository preprint 必須保留 preprint provenance。 |
| Atmospheric and Oceanic Science Letters／Taylor & Francis `10.1080` | 使用明確 GEOMAR repository alternate → `direct-identifier` | OpenAlex/Unpaywall repository → official T&F landing → 使用者提供的明確 repository URL | GEOMAR URL 只屬於該篇代表文章；URL-only artifact 版本維持 `unknown`。 |
| Atmosphere／MDPI `10.3390` | bounded `mdpi-official-pdf` revision candidates | Crossref／OA metadata → bounded `-v3`／`-v2`／`-v1`／base PDF candidates → MDPI DOI landing metadata | revision suffix 是 discovery heuristic，不證明 current revision；版本與 license 預設 `unknown`／空值。 |
| Frontiers in Earth Science — Atmospheric Science／Frontiers `10.3389` | `openalex-pdf` publisher PDF | OpenAlex PDF → Frontiers official PDF/landing → Crossref | 只有 artifact metadata 支持時才標 VOR／CC license。 |
| Journal of the Meteorological Society of Japan／J-STAGE `10.2151` | `openalex-pdf` J-STAGE PDF | OpenAlex → J-STAGE official PDF/landing → Crossref | DOI resolver 或 HTML landing 本身不是成功；目前需取得並驗證 PDF。 |

## 特殊 Route 的重用規則

### PMC Open Data Cloud

- ID Converter 必須使用 `versions=yes`。
- 優先 current version；無 current flag 時才用最高列出版本，明示 non-live 即停止。
- Cloud metadata 的 DOI 必須與輸入 DOI 完全相等。
- `is_pmc_openaccess` 必須為 true，`is_retracted` 必須明確為 false。
- `is_manuscript=true` 可支持 accepted-manuscript；false 仍不足以證明 VOR。
- `license_code` 是待人工解釋的 metadata，不自動變成 reuse permission claim。

### Repository Signposting／DSpace

- Landing response 若有 HTTP `Link`，只接受明確
  `rel="item"; type="application/pdf"` 的 target。
- 標準 `/bitstreams/<uuid>/download` 可先改走同源
  `/server/api/core/bitstreams/<uuid>/content`，再保留 advertised URL fallback。
- 所有 inferred URL 仍通過 public-IP、redirect、byte-size、PDF 與 identity gate。
- 不以 repository 名稱或舊 Digital Commons path 猜 UUID。

### Article-specific alternate identifier

NOAA PID、GEOMAR PDF、repository handle 或其他 alternate identifier 只能在 metadata、
官方 landing 或使用者明確提供時加入。它們的成功可以證明「該篇」有 lawful route，
不能證明同一期刊其他 DOI 共用相同 identifier 或檔案 URL。

## 實際重跑方式

建立一個 UTF-8 `references.txt`，每行放一個 DOI；若有明確 repository／report ID，
放在同一行 DOI 後方。輸出必須使用 repository 外、尚未存在結果檔的新目錄：

```bash
python3 tools/test_paper_acquisition.py references.txt \
  --output-dir /path/outside/repository/rkf-journal-retry \
  --external-qc-tools \
  --workers 2 \
  --artifact-timeout 35 \
  --metadata-timeout 12
```

若只重跑公開 14-case corpus 的特定案例：

```bash
python3 tools/test_paper_acquisition.py \
  docs/benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json \
  --output-dir /path/outside/repository/rkf-journal-retry \
  --indices 3,5,9 \
  --external-qc-tools
```

輸出判讀：

- `obtained`：已取得並通過最低 PDF gate；再看 `research_ready_verified`。
- `retryable`：429、5xx、暫時 timeout 或 provider backoff；做有限度 serial retry。
- `manual-required`：缺 contact/token、SSO/CAPTCHA、401/403、resolver/ILL 或需使用者提供檔案。
- `identity-mismatch`／`invalid-artifact`：拒絕註冊該檔案，修正 route 後再試。
- `unknown` version 或空 license：artifact 可用，但 provenance 仍需人工 review。

## 維護規則

- 每次 provider URL、API schema、repository platform 或 publisher policy 改變時，新增
  deterministic fixture，並以新輸出目錄執行 bounded live check。
- 更新本 playbook 時，同步更新 public corpus 的 `live_outcome`、live smoke、
  `docs/PROJECT_MEMORY.md` 與 `docs/AI_USE_LOG.md`。
- 不覆寫舊 raw report；歷史 run 保持 dated observation。
- 不把 PDF、article text、artifact hash、secret、private path 或 raw conversation
  transcript 寫進 repository。

## 相關紀錄

- [14-case corpus](../benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json)
- [14-case public-safe live result](../benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md)
- [vNext acquisition contract](../references/vnext-acquisition.md)
- [本次 public-safe 對話／決策摘要](2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md)
