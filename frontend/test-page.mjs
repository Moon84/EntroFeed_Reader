import { chromium } from 'playwright';

async function checkPage() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', err => {
    errors.push(`Page error: ${err.message}`);
  });

  try {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(2000);

    console.log('Console errors:', errors);
    console.log('Page title:', await page.title());

    const rootContent = await page.locator('#root').innerHTML();
    console.log('Root content length:', rootContent.length);
    console.log('Root content preview:', rootContent.substring(0, 200));

  } catch (e) {
    console.log('Error:', e.message);
  }

  await browser.close();
}

checkPage();