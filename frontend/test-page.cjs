const { chromium } = require('@playwright/test');

async function checkPage() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const consoleMessages = [];
  const errors = [];
  const failedRequests = [];

  page.on('console', msg => {
    consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', err => {
    errors.push(`Page error: ${err.message}`);
  });

  page.on('requestfailed', request => {
    failedRequests.push(`${request.url()} - ${request.failure().errorText}`);
  });

  page.on('response', response => {
    if (response.status() >= 400) {
      failedRequests.push(`${response.url()} - ${response.status()}`);
    }
  });

  try {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(3000);

    console.log('=== Console messages ===');
    consoleMessages.forEach(m => console.log(m));

    console.log('\n=== Errors ===');
    errors.forEach(e => console.log(e));

    console.log('\n=== Failed requests ===');
    failedRequests.forEach(r => console.log(r));

    console.log('\n=== Page info ===');
    console.log('Page title:', await page.title());

    const rootContent = await page.locator('#root').innerHTML();
    console.log('Root content length:', rootContent.length);
    if (rootContent.length > 0) {
      console.log('Root content preview:', rootContent.substring(0, 500));
    } else {
      console.log('Root is EMPTY - React failed to render');
    }

  } catch (e) {
    console.log('Error:', e.message);
  }

  await browser.close();
}

checkPage();