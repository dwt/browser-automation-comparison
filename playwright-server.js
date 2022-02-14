const { chromium } = require('playwright');  // Or 'webkit' or 'firefox'.

(async () => {
  const browserServer = await chromium.launchServer({
      port: 2342
  });
  const wsEndpoint = browserServer.wsEndpoint();
  console.log(wsEndpoint);
})()