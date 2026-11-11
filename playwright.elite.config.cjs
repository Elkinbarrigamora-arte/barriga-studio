const {defineConfig, devices}=require("@playwright/test");
module.exports=defineConfig({
 testDir:"./elite-browser-tests",
 timeout:25000,
 fullyParallel:false,
 workers:1,
 reporter:"list",
 use:{baseURL:"http://127.0.0.1:18866",trace:"retain-on-failure"},
 projects:[
  {name:"Chromium-ELITE",use:{...devices["Desktop Chrome"]}},
  {name:"WebKit-Safari-ELITE",use:{...devices["Desktop Safari"]}}
 ],
 webServer:{
  command:"python3 tests/bstudio_gateway_fixture.py",
  url:"http://127.0.0.1:18866/studio",
  timeout:15000,
  reuseExistingServer:false
 }
});