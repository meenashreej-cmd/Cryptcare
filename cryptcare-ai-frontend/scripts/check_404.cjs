const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('response', response => {
    if (!response.ok()) {
      console.log('404 URL:', response.url());
    }
  });

  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' }).catch(e => console.log("Goto error:", e));
  
  await browser.close();
})();
