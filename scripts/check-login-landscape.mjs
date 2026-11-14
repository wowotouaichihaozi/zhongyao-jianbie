import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const require = createRequire(path.resolve(process.env.PLAYWRIGHT_PACKAGE_ROOT || 'frontend', 'package.json'))
const { chromium } = require('playwright')
const out=process.env.TEST_OUTPUT || '.test-artifacts/login-landscape';fs.mkdirSync(out,{recursive:true})
const browser=await chromium.launch({channel:'msedge',headless:true,ignoreDefaultArgs:['--hide-scrollbars']})
const results=[]
try{
 const p=await browser.newPage();await p.emulateMedia({reducedMotion:'reduce'});const errors=[];p.on('pageerror',e=>errors.push(e.message))
 for(const size of [{width:1920,height:1080},{width:1536,height:746},{width:1366,height:650},{width:1280,height:620},{width:1024,height:600},{width:900,height:500},{width:844,height:390},{width:640,height:360}]){
 await p.setViewportSize(size);await p.goto((process.env.TEST_BASE_URL || 'http://127.0.0.1:5088') + '/login');const frame=p.frameLocator('iframe[title="项目介绍"]');await frame.locator('#hero-login').waitFor();await p.waitForTimeout(250)
 const dims=await frame.locator('body').evaluate(e=>({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,button:document.querySelector('#hero-login').getBoundingClientRect().toJSON(),proof:document.querySelector('.proof-main').getBoundingClientRect().toJSON(),caption:document.querySelector('.proof-caption').getBoundingClientRect().toJSON(),overflow:getComputedStyle(e).overflowY}))
 console.log('Landscape bounds',size.width,size.height,dims.button.bottom,dims.proof.bottom,dims.caption.bottom);assert(dims.scrollWidth<=dims.width+1,'No horizontal overflow');assert(dims.button.bottom<=dims.height+1,'Login visible');assert(dims.proof.bottom<=dims.height+1,'Full diagram panel visible');assert(dims.caption.bottom<=dims.height+1,'Caption visible');assert.equal(dims.overflow,'auto');await frame.locator('body').evaluate(()=>{document.scrollingElement.scrollTop=document.scrollingElement.scrollHeight});assert(await frame.locator('body').evaluate(()=>document.scrollingElement.scrollTop>0),'Supplementary content scrolls');await frame.locator('body').evaluate(()=>document.scrollingElement.scrollTop=0);await p.screenshot({path:out+'/'+size.width+'-landscape.png'});await frame.locator('#hero-login').click();await p.getByRole('dialog').waitFor();await p.getByRole('button',{name:'关闭登录窗口'}).click();results.push({...size,...dims,passed:true})
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify(results,null,2))
}finally{await browser.close()}
