const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  let errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
      console.log('CONSOLE ERROR:', msg.text());
    }
  });
  page.on('pageerror', err => {
    errors.push(err.toString());
    console.log('PAGE ERROR:', err.toString());
  });
  
  await page.setRequestInterception(true);
  page.on('request', request => {
    if (request.url().includes('/auth/me')) {
      request.respond({
        content: 'application/json',
        headers: {"Access-Control-Allow-Origin": "*"},
        body: JSON.stringify({
          user_id: "test-admin",
          email: "admin@cryptcare.local",
          full_name: "Admin User",
          role: "ADMIN",
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

  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' }).catch(e => console.log("Goto error:", e));
  
  // Set fake token
  await page.evaluate(() => {
    localStorage.setItem('access_token', 'fake-token');
  });
  
  console.log("Reloading with fake admin token to trigger app render...");
  await page.reload({ waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));
  
  if (errors.length > 0) {
    fs.writeFileSync('errors.txt', errors.join('\\n'));
  } else {
    fs.writeFileSync('errors.txt', 'NO ERRORS CAUGHT');
  }
  
  await browser.close();
})();
