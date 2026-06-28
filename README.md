# gaokao-cn-scraper

Scrape major-specific admission scores, rankings, and enrollment counts from [gaokao.cn](https://www.gaokao.cn) (掌上高考). Covers **2707 schools**, **142,719 records** across **32 provinces** for **2025**.

## Features

- **Full coverage** — 2707 schools: 1398 undergraduate (普通本科) + 1309 vocational (专科/高职)
- **WAF bypass** — Playwright `page.goto()` executes the JS challenge to obtain `acw_tc` cookies
- **Dual endpoint** — Both `province_score` (批次线) and `special_score` (专业分数线) APIs
- **Checkpoint resume** — Auto-saves per school, supports interrupted recovery
- **30 concurrent API** — aiohttp + asyncio semaphore for high throughput

## Usage

```bash
pip install aiohttp
npm install playwright
npx playwright install chromium
python3 gaokao_crawler.py
```

## Architecture

```
gaokao_crawler.py   — Main crawler (Python aiohttp)
waf-bypass.js       — WAF cookie acquisition (Playwright)
gaokao_data/        — Output directory
  ├── {id}_{name}.json    — Per-school data
  └── _all_data.csv       — Aggregated CSV (26 MB)
```

The crawler uses a hybrid approach:
1. **`waf-bypass.js`** opens headless Chromium → `page.goto(API_URL)` triggers WAF JS challenge → solves it → obtains `acw_tc` + `aliyungf_tc` + `alicfw`
2. Cookies passed to **Python aiohttp** for high-concurrency API calls
3. Cookies refreshed every 15 min via background task

## Data

Each school saved as individual JSON; aggregated into `_all_data.csv`.

| Field | Description |
|-------|------------|
| 学校ID / 学校名称 | School ID / Name |
| 学校层次 | Level (本科/专科) |
| 年份 | Year |
| 省份 | Province |
| 科类 | Subject type (理科/文科/综合) |
| 专业名称 | Major name |
| 最低分 / 最低位次 | Min score / Rank |
| 平均分 / 录取人数 | Avg score / Enrollment |
| 批次线 / 分差 | Batch line / Score diff |
| 选科要求 | Subject requirement |

## License

MIT
