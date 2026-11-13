import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
const require=createRequire(path.resolve(process.env.PLAYWRIGHT_PACKAGE_ROOT || 'frontend', 'package.json'))
const {chromium}=require('playwright')
const browser=await chromium.launch({channel:'msedge',headless:true,ignoreDefaultArgs:['--hide-scrollbars']})
const context=await browser.newContext()
const credentials={username:process.env.TEST_ADMIN_USERNAME,password:process.env.TEST_ADMIN_PASSWORD}
assert(credentials.username && credentials.password, 'Provide TEST_ADMIN_USERNAME and TEST_ADMIN_PASSWORD')
const out=process.env.TEST_OUTPUT || '.test-artifacts/admin-adaptation';fs.mkdirSync(out,{recursive:true})
const results=[];let token='',refresh=''
try{
 const r=await context.request.post((process.env.TEST_BASE_URL || 'http://127.0.0.1:5088')+'/api/admin-auth/login',{data:credentials});const data=await r.json();token=data.data?.token;refresh=data.data?.refreshToken||token;assert(token)
 await context.route('**/*',route=>{
  const r=route.request(),u=new URL(r.url());if(!['GET','HEAD','OPTIONS'].includes(r.method())&&!/\/api\/admin-auth\/(refresh|logout)$/.test(u.pathname))return route.fulfill({status:409,contentType:'application/json',body:'{}'});return route.continue()
 })
 const p=await context.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message))
 await p.goto((process.env.TEST_BASE_URL || 'http://127.0.0.1:5088')+'/admin/dashboard#'+new URLSearchParams({auth_token:token,refresh_token:refresh,redirect:'/dashboard'}),{waitUntil:'domcontentloaded'})
 await p.locator('.admin-dashboard').waitFor()
 for(const size of [{width:320,height:700},{width:390,height:844},{width:500,height:820},{width:768,height:1024},{width:900,height:500},{width:1440,height:900}]){
  await p.setViewportSize(size)
  for(const route of ['/dashboard','/manage/user','/manage/user-detail/1','/agents','/tasks','/logs','/digital-twin']){
   await p.goto((process.env.TEST_BASE_URL || 'http://127.0.0.1:5088')+'/admin'+route,{waitUntil:'domcontentloaded'});await p.locator('main').first().waitFor();await p.waitForTimeout(route==='/digital-twin'?1200:500)
   const metrics=await p.evaluate(()=>{const main=document.querySelector('main');return{width:innerWidth,scrollWidth:document.documentElement.scrollWidth,mainWidth:main.clientWidth,mainScrollWidth:main.scrollWidth}})
   assert(metrics.scrollWidth<=size.width+1,'No document overflow: '+route)
   if(size.width<=768)assert(metrics.mainScrollWidth<=metrics.mainWidth+2,'No main-area horizontal overflow: '+route)
   const key=size.width+'-'+route.replaceAll('/','_')
   await p.screenshot({path:out+'/after-'+key+'.png'})
   results.push({...size,route,...metrics,passed:true})
  }
  console.log('Admin routes passed:',size.width)
 }
 await p.setViewportSize({width:390,height:844});await p.goto((process.env.TEST_BASE_URL || 'http://127.0.0.1:5088')+'/admin/dashboard',{waitUntil:'domcontentloaded'});await p.locator('.admin-dashboard').waitFor();await p.waitForTimeout(1500)
 await p.locator('header[class*="_layout-header"] button').first().click();await p.waitForTimeout(350)
 const aside=p.locator('aside[class*="_layout-mobile-sider"]');console.log('DRAWER_STATE',await aside.evaluate(e=>({class:e.className,width:e.getBoundingClientRect().width})));assert((await aside.boundingBox()).width>0,'Drawer opens')
 await aside.locator('.n-menu-item-content').filter({hasText:'资源任务记录'}).first().click();await p.waitForURL(u=>u.pathname==='/admin/tasks',{waitUntil:'domcontentloaded'});results.push({drawerNavigation:true})
 assert.deepEqual(errors,[]);fs.writeFileSync(out+'/result.json',JSON.stringify({results,errors},null,2));console.log('All admin pages and mobile drawer navigation passed; business mutation requests blocked.')
}catch(e){console.log('ADMIN_TEST_ERROR',e.name,e.message.split('\n')[0].replaceAll(token||'__none__','[redacted]').replaceAll(refresh||'__none__','[redacted]'));process.exitCode=1}finally{await browser.close()}
