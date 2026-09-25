const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('response', response => {
    if (!response.ok()) {
      console.log('FAILED RESOURCE:', response.url(), response.status());
    }
  });

  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('CONSOLE ERROR:', msg.text());
    }
  });
  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.toString());
  });
  
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' }).catch(e => console.log("Goto error:", e));
  
  await browser.close();
})();
