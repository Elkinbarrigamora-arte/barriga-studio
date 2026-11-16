const { defineConfig, devices } = require("@playwright/test");
module.exports = defineConfig({
  testDir: "./bridge-browser-tests",
  timeout: 25000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {baseURL:"http://127.0.0.1:8767",trace:"retain-on-failure"},
  projects: [
    {name:"Chromium",use:{...devices["Desktop Chrome"]}},
    {name:"WebKit-Safari",use:{...devices["Desktop Safari"]}}
  ],
  webServer: {
    command: "python3 tools/bstudio_unified_bridge.py --studio . --media-dir /tmp/bstudio-qa-mp4-empty --port 8767 --no-browser",
    url: "http://127.0.0.1:8767",
    reuseExistingServer: false,
    timeout: 15000
  }
});
