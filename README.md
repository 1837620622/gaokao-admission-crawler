# Gaokao Admission Data Crawler

**2025 年全国高校专业录取分数线爬虫工具**

Crawl and aggregate major-specific admission scores, rankings, and enrollment counts from [gaokao.cn](https://www.gaokao.cn) (掌上高考). Covers **2707 schools**, **142,719 records** across **32 provinces** for **2025** admission season.

## Features

- ✅ **Full coverage** — 2707 schools: 1398 undergraduate (普通本科) + 1309 vocational college (专科/高职)
- ✅ **WAF bypass** — Uses Playwright `page.goto()` to execute JS challenge and obtain `acw_tc` cookies
- ✅ **Dual API** — Crawls both `province_score` (省控线) and `special_score` (专业分数线) endpoints
- ✅ **Checkpoint resume** — Auto-saves after each school, supports interrupted recovery
- ✅ **30 concurrent API calls** — High-speed crawling with aiohttp + asyncio semaphore

## Data Structure

Each school is saved as an individual JSON file and aggregated into `gaokao_data/_all_data.csv`.

### CSV Fields

| Field | Description |
|-------|------------|
| 学校ID | School ID |
| 学校名称 | School name |
| 学校层次 | Level (本科/专科) |
| 年份 | Year |
| 省份ID | Province ID |
| 省份 | Province name |
| 科类ID | Subject type ID |
| 科类 | Subject type (理科/文科/综合/...) |
| 专业名称 | Major name |
| 最低分 | Minimum admission score |
| 最低位次 | Minimum ranking |
| 平均分 | Average score |
| 录取人数 | Enrollment count |
| 批次线 | Provincial batch control score |
| 分差 | Score difference |
| 选科要求 | Subject selection requirement |

## Requirements

- Python 3.10+
- Node.js 18+

## Usage

```bash
# Install Python dependencies
pip install aiohttp

# Install Playwright
npm install playwright
npx playwright install chromium

# Run crawler
python3 gaokao_crawler_v6.py
```

## Architecture

```
gaokao_crawler_v6.py   — Main crawler (Python aiohttp)
get_cookies.js         — WAF cookie acquisition (Playwright)
gaokao_data/           — Output directory
  ├── {school_id}_{name}.json   — Per-school data
  └── _all_data.csv             — Aggregated CSV
```

The crawler uses a **hybrid approach**:
1. **`get_cookies.js`** opens a headless Chromium to `page.goto(API_URL)`, triggering the WAF JS challenge
2. Cookies (`acw_tc` + `aliyungf_tc` + `alicfw`) are passed to **Python aiohttp** for high-concurrency API calls
3. Cookies are refreshed every 15 minutes via a background task

## Output

- **142,719 records** from **2,707 schools** across **32 provinces**
- Single file `_all_data.csv` (~26 MB) ready for analysis
- Per-school JSON for granular inspection

## License

MIT
