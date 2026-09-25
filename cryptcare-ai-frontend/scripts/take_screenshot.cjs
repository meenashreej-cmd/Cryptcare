const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.setRequestInterception(true);
  page.on('request', request => {
    if (request.url().includes('/auth/me')) {
      request.respond({
        content: 'application/json',
        headers: {"Access-Control-Allow-Origin": "*"},
        body: JSON.stringify({
          user_id: "test-hospital-admin",
          email: "hospital@example.com",
          full_name: "Hospital Admin",
          role: "HOSPITAL_ADMIN",
          verified: true,
          created_at: new Date().toISOString()
        })
      });
    } else if (request.url().includes('/api/v1/')) {
      request.respond({
        content: 'application/json',
        headers: {"Access-Control-Allow-Origin": "*"},
        body: JSON.stringify([])
      });
    } else {
      request.continue();
    }
  });

  await page.setViewport({ width: 1280, height: 800 });
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' }).catch(e => console.log("Goto error:", e));
  
  // Set fake token
  await page.evaluate(() => {
    localStorage.setItem('access_token', 'fake-token');
  });
  
  console.log("Reloading...");
  await page.reload({ waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));
  
  await page.screenshot({ path: path.join(__dirname, 'screenshot_hospital.png') });
  console.log("Screenshot taken.");
  
  await browser.close();
})();
