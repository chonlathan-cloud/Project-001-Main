const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
  
  try {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    const content = await page.content();
    console.log('PAGE CONTENT LENGTH:', content.length);
  } catch (err) {
    console.log('GOTO ERROR:', err.message);
  } finally {
    await browser.close();
  }
})();
