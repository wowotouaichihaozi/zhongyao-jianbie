import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const require = createRequire(path.resolve(process.env.PLAYWRIGHT_PACKAGE_ROOT || 'frontend', 'package.json'))
const { chromium } = require('playwright')
const out=process.env.TEST_OUTPUT || '.test-artifacts/login-one-screen';fs.mkdirSync(out,{recursive:true})
const browser=await chromium.launch({channel:'msedge',headless:true,ignoreDefaultArgs:['--hide-scrollbars']})
const results=[]
try{
 const p=await browser.newPage();await p.emulateMedia({reducedMotion:'reduce'});const errors=[];p.on('pageerror',e=>errors.push(e.message))
 for(const size of [{width:320,height:568},{width:360,height:640},{width:390,height:844},{width:500,height:820},{width:768,height:1024}]){
  await p.setViewportSize(size);await p.goto((process.env.TEST_BASE_URL || 'http://127.0.0.1:5088') + '/login',{waitUntil:'domcontentloaded'});const frame=p.frameLocator('iframe[title="项目介绍"]');await frame.locator('#hero-login').waitFor();await p.waitForTimeout(500)
  const dims=await frame.locator('body').evaluate(e=>({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,button:document.querySelector('#hero-login').getBoundingClientRect().toJSON(),proof:document.querySelector('.proof-main').getBoundingClientRect().toJSON()}))
  assert(dims.scrollWidth<=dims.width+1);if(size.height>580)assert(dims.scrollHeight<=dims.height+2,'Fits one screen');else assert(dims.scrollHeight>=dims.height)
  assert(dims.button.y+dims.button.height<=dims.height);assert(dims.proof.height>=210)
  await p.screenshot({path:out+'/'+size.width+'-login.png'});await frame.locator('#hero-login').click();await p.getByRole('dialog').waitFor();await p.getByRole('button',{name:'关闭登录窗口'}).click();results.push({...size,...dims,passed:true});console.log('Login one-screen passed:',size.width,size.height)
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify(results,null,2))
}finally{await browser.close()}
