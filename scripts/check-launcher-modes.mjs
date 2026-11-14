import assert from 'node:assert/strict'
import http from 'node:http'
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'

const script=fileURLToPath(new URL('local-web.mjs',import.meta.url))
let businessHits=0
const backend=http.createServer((req,res)=>{
  if(req.url==='/api/startup-test')businessHits++
  res.setHeader('content-type','application/json')
  res.setHeader('set-cookie','fswy_session=local-test; HttpOnly; Path=/')
  res.end(JSON.stringify({ok:true,cookie:req.headers.cookie||''}))
})
await new Promise(resolve=>backend.listen(0,'127.0.0.1',resolve))
const backendPort=backend.address().port
assert(backendPort<65515)
const env={...process.env,PORT:String(backendPort),LOCAL_BACKEND_URL:`http://127.0.0.1:${backendPort}`,BENCAO_NO_BROWSER:'1'}
const child=spawn(process.execPath,[script],{env,stdio:['ignore','pipe','pipe']})
let logs=''
child.stdout.on('data',b=>{logs+=b})
child.stderr.on('data',b=>{logs+=b})
try{
  let status,origin
  for(let attempt=0;attempt<60;attempt++){
    if(child.exitCode!==null)throw new Error('Gateway stopped: '+logs)
    for(let offset=1;offset<=20;offset++){
      try{
        origin=`http://127.0.0.1:${backendPort+offset}`
        status=await(await fetch(origin+'/__launcher/status',{signal:AbortSignal.timeout(100)})).json()
        if(status.mode==='local-full-stack')break
      }catch{}
    }
    if(status?.mode==='local-full-stack')break
    await new Promise(resolve=>setTimeout(resolve,50))
  }
  assert.equal(status?.localDatabase,true)
  assert.equal(status.backend,`http://127.0.0.1:${backendPort}`)
  const response=await fetch(origin+'/api/startup-test',{headers:{cookie:`fswy_session=remote-test; bc_local_session_${new URL(origin).port}=local-test`}})
  const data=await response.json()
  assert(data.ok)
  assert(data.cookie.includes('fswy_session=local-test')&&!data.cookie.includes('remote-test'))
  assert(response.headers.get('set-cookie').startsWith(`bc_local_session_${new URL(origin).port}=`))
  assert.equal(businessHits,1)
  const repeat=spawn(process.execPath,[script],{env:{...env,PORT:new URL(origin).port},stdio:'ignore'})
  const exit=await new Promise((resolve,reject)=>{
    const deadline=setTimeout(()=>{repeat.kill();reject(new Error('Repeat launch failed to reuse the same copy'))},5000)
    repeat.once('exit',code=>{clearTimeout(deadline);resolve(code)})
  })
  assert.equal(exit,0)
  console.log('Port collision, loopback backend routing, local DB mode and repeat launch passed.')
}finally{
  child.kill()
  await new Promise(resolve=>child.once('exit',resolve))
  await new Promise(resolve=>backend.close(resolve))
}
