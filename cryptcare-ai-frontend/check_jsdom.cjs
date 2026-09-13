const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const distDir = path.join(__dirname, 'dist', 'assets');
const files = fs.readdirSync(distDir);
const jsFile = files.find(f => f.endsWith('.js'));

const html = `
<!DOCTYPE html>
<html>
<head></head>
<body>
  <div id="root"></div>
  <script type="module">
    window.onerror = function(message, source, lineno, colno, error) {
      console.log('RUNTIME ERROR:', message);
    };
  </script>
  <script type="module" src="file://${path.join(distDir, jsFile)}"></script>
</body>
</html>
`;

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  resources: "usable",
  url: "file://" + distDir + "/"
});

dom.window.console.error = (...args) => console.log('CONSOLE ERROR:', ...args);
dom.window.console.warn = (...args) => console.log('CONSOLE WARN:', ...args);
dom.window.addEventListener("error", (event) => {
  console.log("JSDOM ERROR EVENT:", event.error ? event.error.message : event.message);
});

setTimeout(() => {
  console.log("Done checking.");
  process.exit(0);
}, 3000);
