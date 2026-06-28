const { chromium } = require('playwright');

const CHROME_PATH = '/Users/chuankangkk/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const API_URL = 'https://api-gaokao.zjzw.cn/apidata/web';

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: CHROME_PATH });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  // Navigate to the full API URL — triggers WAF JS challenge
  const testUrl = API_URL + '?autosign=&local_province_id=61&local_type_id=2073&page=1&platform=2&school_id=123&size=5&uri=v1/school/province_score&year=2025&signsafe=x';
  try {
    await page.goto(testUrl, { waitUntil: 'networkidle', timeout: 20000 });
  } catch(e) {
    // navigation might fail if challenge redirects weirdly, that's ok
  }
  await page.waitForTimeout(2000);

  const cookies = await context.cookies('https://api-gaokao.zjzw.cn');
  const result = {};
  for (const c of cookies) result[c.name] = c.value;

  console.log(JSON.stringify(result));
  await browser.close();
})();
