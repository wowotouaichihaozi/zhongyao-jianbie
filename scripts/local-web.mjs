import http from 'node:http'
import https from 'node:https'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const logRoot = path.join(project, '.local-web')
fs.mkdirSync(logRoot, { recursive: true })
function logError(label, error) {
  const line = `${new Date().toISOString()} ${label} ${error?.code || ''} ${error?.message || error}\n`
  try { fs.appendFileSync(path.join(logRoot, 'errors.log'), line) } catch { /* Logging must not crash the gateway. */ }
  console.error(line.trim())
}
process.on('uncaughtExceptionMonitor', error => logError('uncaught', error))
const config = JSON.parse(fs.readFileSync(path.join(project, 'remote-backend.json'), 'utf8'))
const localMode = Boolean(process.env.LOCAL_BACKEND_URL)
const upstream = new URL(process.env.LOCAL_BACKEND_URL || process.env.REMOTE_BACKEND_URL || config.backend)
if (upstream.username || upstream.password || upstream.pathname !== '/' || upstream.search || upstream.hash || (localMode ? upstream.protocol !== 'http:' || upstream.hostname !== '127.0.0.1' : upstream.protocol !== 'https:')) throw new Error('Use HTTPS for the remote backend, or an explicit loopback HTTP backend for local mode.')
const mode = localMode ? 'local-full-stack' : 'remote-backend'
const remoteAssetRoots = (config.remoteAssetRoots || []).filter(value => typeof value === 'string' && /^\/[A-Za-z0-9_-]+$/.test(value))
let port = Number(process.env.PORT || config.port || 5088)
if (!Number.isInteger(port) || port < 1024 || port > 65515) throw new Error('Choose a port between 1024 and 65515.')
let portRetries = 0
const root = path.resolve(project, 'frontend/dist')
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.mjs': 'application/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.gif': 'image/gif', '.ico': 'image/x-icon', '.wasm': 'application/wasm', '.mp4': 'video/mp4', '.mp3': 'audio/mpeg', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.gltf': 'model/gltf+json', '.glb': 'model/gltf-binary', '.pdf': 'application/pdf' }
const hop = new Set(['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade'])

function proxy(req, res) {
  req.on('error', error => logError('client-request', error))
  res.on('error', error => logError('client-response', error))
  const headers = Object.fromEntries(Object.entries(req.headers).filter(([key]) => !hop.has(key) && !['host', 'origin', 'referer'].includes(key)))
  headers.host = upstream.host
  if (localMode && headers.cookie) {
    // Remote and local modes share a loopback host; keep their login cookies independent.
    headers.cookie = headers.cookie.split(';').map(value => value.trim()).filter(value => !value.startsWith('fswy_session=')).map(value => value.startsWith(`bc_local_session_${port}=`) ? 'fswy_session=' + value.slice(value.indexOf('=') + 1) : value).join('; ')
  }
  // The local proxy is a same-origin gateway; preserve authentication and stream bodies.
  if (req.headers.origin) headers.origin = upstream.origin
  if (req.headers.referer) headers.referer = upstream.origin + '/'
  const remote = (localMode ? http : https).request(upstream, { method: req.method, path: req.url, headers }, response => {
    const outgoing = Object.fromEntries(Object.entries(response.headers).filter(([key]) => !hop.has(key)))
    if (outgoing['set-cookie']) outgoing['set-cookie'] = outgoing['set-cookie'].map(cookie => {
      const scoped = cookie.replace(/;\s*Domain=[^;]+/ig, '')
      return localMode ? scoped.replace(/^fswy_session=/, `bc_local_session_${port}=`) : scoped
    })
    if (outgoing.location?.startsWith(upstream.origin + '/')) outgoing.location = outgoing.location.slice(upstream.origin.length)
    res.writeHead(response.statusCode, outgoing)
    response.pipe(res)
    response.on('error', error => { logError('upstream-response ' + new URL(req.url, 'http://localhost').pathname, error); res.destroy() })
    response.on('aborted', () => { logError('upstream-aborted', 'response ended before completion'); res.destroy() })
  })
  remote.setTimeout(660000, () => remote.destroy(new Error('Remote backend timed out')))
  const requestPath = new URL(req.url, 'http://localhost').pathname
  if (req.method === 'GET' && ['/api/xiaozhi/history', '/api/personalized-resources/generated-videos'].includes(requestPath)) {
    // Bound history synchronisation without shortening model-generation requests.
    const limit = requestPath === '/api/xiaozhi/history' ? 60000 : 20000
    const deadline = setTimeout(() => remote.destroy(Object.assign(new Error('资源历史同步超时，请稍后重试'), { code: 'ETIMEDOUT' })), limit)
    res.once('close', () => clearTimeout(deadline))
  }
  remote.on('error', error => {
    logError('upstream-request ' + new URL(req.url, 'http://localhost').pathname, error)
    if (res.destroyed) return
    if (res.headersSent) return res.destroy()
    const status = error.code === 'ETIMEDOUT' ? 504 : 502
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ code: status, msg: error.code === 'ETIMEDOUT' ? error.message : '无法连接远程后端，请检查网络或远程服务状态。', detail: error.code || error.message }))
  })
  req.on('aborted', () => remote.destroy())
  res.on('close', () => { if (!res.writableFinished) remote.destroy() })
  req.pipe(remote)
}

const server = http.createServer((req, res) => {
  req.on('error', error => logError('request', error))
  res.on('error', error => logError('response', error))
  let pathname
  try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname) } catch { res.writeHead(400); return res.end() }
  if (pathname === '/__launcher/status') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' })
    return res.end(JSON.stringify({ mode, backend: upstream.origin, localDatabase: localMode, remoteAssets: !localMode && remoteAssetRoots.length > 0, preferLocalStatic: Boolean(config.preferLocalStatic), projectRoot: project }))
  }
  if (!localMode && remoteAssetRoots.some(prefix => pathname === prefix || pathname.startsWith(prefix + '/'))) {
    if (!['GET', 'HEAD'].includes(req.method)) return proxy(req, res)
    let cached = path.resolve(root, '.' + pathname)
    if (cached !== root && !cached.startsWith(root + path.sep)) { res.writeHead(403); return res.end() }
    try {
      if (fs.statSync(cached).isDirectory()) {
        if (config.preferLocalStatic && !pathname.endsWith('/')) {
          const canonical = new URL(req.url, 'http://localhost')
          res.writeHead(302, { Location: canonical.pathname + '/' + canonical.search })
          return res.end()
        }
        cached = path.join(cached, 'index.html')
      }
      if (!config.preferLocalStatic || !fs.statSync(cached).isFile()) return proxy(req, res)
    } catch { return proxy(req, res) }
  }
  if (pathname === '/local-overrides.css') {
    const overridePath = path.join(project, 'frontend/local-overrides.css')
    if (!fs.existsSync(overridePath)) { res.writeHead(404); return res.end() }
    const css = fs.readFileSync(overridePath)
    res.writeHead(200, { 'Content-Type': 'text/css; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(css)
  }
  if (pathname === '/local-resource-history.mjs') {
    if (!fs.existsSync(path.join(project, 'frontend/local-resource-history.mjs'))) { res.writeHead(404); return res.end() }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(fs.readFileSync(path.join(project, 'frontend/local-resource-history.mjs')))
  }
  if (pathname === '/local-path-cache.mjs') {
    const module = path.join(project, 'frontend/local-path-cache.mjs')
    if (!fs.existsSync(module)) { res.writeHead(404); return res.end() }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(fs.readFileSync(module))
  }
  if (pathname === '/local-account-view.mjs') {
    const module = path.join(project, 'frontend/local-account-view.mjs')
    if (!fs.existsSync(module)) { res.writeHead(404); return res.end() }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(fs.readFileSync(module))
  }
  if (pathname === '/local-exam-evidence.mjs') {
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(fs.readFileSync(path.join(project, 'frontend/local-exam-evidence.mjs')))
  }
  if (pathname === '/admin/local-admin.css') {
    res.writeHead(200, { 'Content-Type': 'text/css; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(fs.readFileSync(path.join(project, 'admin/local-admin.css')))
  }
  if (pathname.startsWith('/admin/') && ['GET', 'HEAD'].includes(req.method)) {
    const adminRoot = path.join(project, 'admin/dist')
    let adminFile = path.resolve(adminRoot, '.' + pathname.slice('/admin'.length))
    if (!adminFile.startsWith(adminRoot + path.sep) && adminFile !== adminRoot) { res.writeHead(403); return res.end() }
    try { if (fs.statSync(adminFile).isDirectory()) adminFile = path.join(adminFile, 'index.html') } catch { if (!path.extname(pathname)) adminFile = path.join(adminRoot, 'index.html') }
    if (fs.existsSync(adminFile) && fs.statSync(adminFile).isFile()) {
      if (adminFile.endsWith('index.html')) {
        const html = fs.readFileSync(adminFile, 'utf8').replace('</head>', '<link rel="stylesheet" href="/admin/local-admin.css"></head>')
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' })
        return res.end(req.method === 'HEAD' ? undefined : html)
      }
      res.writeHead(200, { 'Content-Type': mime[path.extname(adminFile).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-cache' })
      if (req.method === 'HEAD') return res.end()
      const stream = fs.createReadStream(adminFile); stream.on('error', () => res.destroy()); res.on('close', () => stream.destroy()); return stream.pipe(res)
    }
  }
  if (/^\/(api(?:[/-]|$)|ppt-api(?:\/|$)|herb-api(?:\/|$)|admin(?:\/|$)|uploads(?:\/|$)|generated(?:\/|$))/.test(pathname) || !['GET', 'HEAD'].includes(req.method)) return proxy(req, res)
  let file = path.resolve(root, '.' + pathname)
  if (file !== root && !file.startsWith(root + path.sep)) { res.writeHead(403); return res.end() }
  try {
    if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html')
    if (!fs.statSync(file).isFile()) throw new Error('not a file')
  } catch {
    // Missing generated/static assets are served by the remote site, SPA routes locally.
    if (path.extname(pathname)) return proxy(req, res)
    file = path.join(root, 'index.html')
  }
  let stat
  try { stat = fs.statSync(file) } catch { res.writeHead(503); return res.end('Missing frontend/dist. Build the frontend first.') }
  if (pathname === '/assets/LifeTreeView-HbbrOj0I.js') {
    let code = fs.readFileSync(file, 'utf8')
    const begin = code.indexOf('function Jr(i){'), end = code.indexOf('function Zr(', begin)
    if (begin >= 0 && end > begin) {
      code = 'import{learningResourceCompleted as __learningDone}from"/local-exam-evidence.mjs";\n' + code.slice(0, begin) + 'function Jr(i){return __learningDone(i?.resourceType,i||{})}' + code.slice(end)
      code = code.replace('const A=qr(v),I=Yr(i,v,s),M=pn(I),T=Jr(I);', 'const I=Yr(i,v,s),A=__learningDone(v.resourceType,v),M=pn(I),T=__learningDone(v.resourceType||I?.resourceType,I||{});')
      code = code.replace('return It.has(n)?{progress:100,completedNodes:', 'return It.has(n)&&h===r.length&&r.length>0?{progress:100,completedNodes:')
    }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (['/assets/QuestionExamSessionView-nJA_fE5H.js', '/assets/QuestionGeneratorView-DE7HoBSX.js'].includes(pathname)) {
    let code = fs.readFileSync(file, 'utf8')
    code = 'import{examAnswerState as __answerState,examStats as __examStats}from"/local-exam-evidence.mjs";\n' + code
    code = code.replace(/\.filter\(([\w$]+)=>!\1\.correct\)/g, '.filter($1=>__answerState($1)==="incorrect")')
    code = code.replace(/([\w$]+\.value)\.question_count-\1\.correct_count/g, '__examStats($1).incorrect')
    code = code.replace('e.detail.forEach(r=>{var A;', 'e.detail.forEach(r=>{if(!["correct","incorrect"].includes(__answerState(r)))return;var A;')
    code = code.replace('e.forEach(d=>{var Z;const b=', 'e.forEach(d=>{if(!["correct","incorrect"].includes(__answerState(d)))return;var Z;const b=')
    code = code.replace('a.correct||t.add(l)', '__answerState(a)==="incorrect"&&t.add(l)')
    code = code.replace('const t={score:e.score,total:e.total_score,', 'const t={answerEvidenceVersion:1,score:e.score,total:e.total_score,')
    code = code.replace('const C={score:l,total:r,correct_count:a,', 'const C={answerEvidenceVersion:1,score:l,total:r,correct_count:a,')
    // Display unanswered separately rather than hiding it inside the wrong count.
    if (pathname.includes('QuestionExamSessionView')) code = code.replace('s[2]||(s[2]=n("span",null,"错误",-1))', 's[2]||(s[2]=n("span",null,"错误",-1)),n("small",{class:"unanswered-count"},"未作答 "+i(__examStats(l.value).unanswered),1)')
    else code = code.replace('e[81]||(e[81]=n("span",null,"错误",-1))', 'e[81]||(e[81]=n("span",null,"错误",-1)),n("small",{class:"unanswered-count"},"未作答 "+o(__examStats(m.value).unanswered),1)')
    code = code.replace('i(z.value?"考试通过":"考试未通过")', 'i(__examStats(l.value).answered?(z.value?"考试通过":"考试未通过"):"未作答")')
    code = code.replace('i(U.value)+"%"', '(__examStats(l.value).graded?i(__examStats(l.value).accuracy)+"%":"待测评")')
    code = code.replace('o(m.value.score/m.value.total_score>=.6?"考试通过":"继续加油")', 'o(__examStats(m.value).answered?(m.value.score/m.value.total_score>=.6?"考试通过":"继续加油"):"未作答")')
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (pathname === '/assets/UserProfileView-bfldUmgr.js' && fs.existsSync(path.join(project, 'frontend/local-account-view.mjs'))) {
    let code = fs.readFileSync(file, 'utf8')
    const setup = 'function U(t){', render = 'return(t,s)=>(h(),y("div",J,'
    if (code.includes(setup) && code.includes(render) && code.includes('async function x(){')) {
      code = 'import{mobileAccountState as __accountState,renderMobileAccount as __accountRender}from"/local-account-view.mjs";\n' + code
      code = code.replace('import{a as A,', 'import{a4 as __accountUnmount,a as A,')
      code = code.replace(setup, 'const __account=__accountState(i,V,__accountUnmount,a,n);' + setup)
      code = code.replace(render, 'return(t,s)=>__account.portrait.value?__accountRender({el:e,state:__account,form:a,account:v.value,avatar:m.value||u.value||w,fileChange:S,save:x,notify:n,saving:p.value,toast:r}):(h(),y("div",J,')
    }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (pathname === '/assets/index-BPhhYrvy.js' && fs.existsSync(path.join(project, 'frontend/local-path-cache.mjs'))) {
    let code = fs.readFileSync(file, 'utf8')
    const configReader = 'async function j_(e={}){const{data:t}=await ee.get("/api/learning-path/config",{params:{summary:e.summary===!0?1:0}});return(t==null?void 0:t.data)||t}'
    const stageReader = 'async function B_(e,t={}){const{data:n}=await ee.get(`/api/learning-path/stages/${encodeURIComponent(e)}`,{params:{includeConfig:t.includeConfig===!0?1:0}});return(n==null?void 0:n.data)||n}'
    if (code.includes(configReader) && code.includes(stageReader)) {
      code = 'import{readSavedPath as __savedPath,invalidatePathCache as __invalidatePath}from"/local-path-cache.mjs";\n' + code
      code = code.replace(configReader, 'ee.interceptors.response.use(r=>{if(!["get","head"].includes(String(r.config?.method||"get").toLowerCase()))__invalidatePath(String(r.config?.url||""));return r});async function j_(e={}){const load=async()=>{const{data:t}=await ee.get("/api/learning-path/config",{params:{summary:e.summary===!0?1:0},timeout:20000});return t?.data||t};return e.summary===!0?__savedPath("/api/learning-path/config?summary=1",load,e):load()}')
      code = code.replace(stageReader, 'async function B_(e,t={}){const url="/api/learning-path/stages/"+encodeURIComponent(e)+"?includeConfig="+(t.includeConfig===!0?1:0);return __savedPath(url,async()=>{const{data:n}=await ee.get(url,{timeout:20000});return n?.data||n},t)}')
      code = code.replace('fetch(Ht("/api/learning-path/generate-stream"),', 'fetch((__invalidatePath("/api/learning-path/generate-stream"),Ht("/api/learning-path/generate-stream")),')
    }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (pathname === '/assets/LearningPathView-Cb-ZCyyA.js') {
    let code = fs.readFileSync(file, 'utf8')
    code = code.replace('async function se(){', 'async function se(__force=false){')
    code = code.replace('function Ze(){q.value=null,se()}', 'function Ze(){q.value=null,se(!0)}')
    code = code.replace('const l=await yt({summary:!0});let n=ue(l);', 'const l=await yt({summary:!0,fresh:__force===!0,onFresh:fresh=>{u.value=ue(fresh);if(d.value){const saved=oe(String(f.params.stageId||""),u.value);if(saved)h.value=saved}}});let n=ue(l);')
    code = code.replace('const n=await kt(e);', 'const n=await kt(e,{onFresh:fresh=>{if(fresh?.config)u.value=ue(fresh.config);h.value=fresh?.stage||fresh}});')
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (pathname === '/assets/LearningPathStageDetailView-De5pET68.js') {
    let code = fs.readFileSync(file, 'utf8')
    code = code.replace('let a=U(await fa({summary:!0}));if(b.value=', 'let a=U(await fa({summary:!0,onFresh:fresh=>{const saved=U(fresh);b.value=saved.meta||{};ke(saved);m.value=F(saved)}}));if(b.value=')
    code = code.replaceAll('await fa({summary:!0})', 'await fa({summary:!0,fresh:!0})')
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (pathname === '/assets/PersonalizedResourcesView-XLkt8wIR.js' && fs.existsSync(path.join(project, 'frontend/local-resource-history.mjs'))) {
    let code = fs.readFileSync(file, 'utf8')
    const start = code.indexOf('async function V(){var n;k.value=!0,T.value="",E.value="";')
    const end = code.indexOf('async function ze()', start)
    if (start >= 0 && end > start && code.slice(start, end).includes('Promise.allSettled([Ge(100),ze()])')) {
      const replacement = 'async function V(){return __localHistory({owner:z,history:()=>Ge(100),videos:publish=>__videoPages(Oe,publish),extract:ke,sort:Pe,publish:value=>z.value=value,setLoading:value=>k.value=value,setError:value=>T.value=value,setWarning:value=>E.value=value})}'
      code = 'import {loadHistory as __localHistory,loadVideoPages as __videoPages} from "/local-resource-history.mjs";\n' + code.slice(0, start) + replacement + code.slice(end)
    }
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : code)
  }
  if (file === path.join(root, 'index.html')) {
    const html = fs.readFileSync(file, 'utf8')
    const page = fs.existsSync(path.join(project, 'frontend/local-overrides.css')) ? html.replace('</head>', '<link rel="stylesheet" href="/local-overrides.css"></head>') : html
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' })
    return res.end(req.method === 'HEAD' ? undefined : page)
  }
  let start = 0, end = stat.size - 1, status = 200
  const headers = { 'Content-Type': mime[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-cache', 'Accept-Ranges': 'bytes' }
  if (req.headers.range) {
    const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range)
    if (range) {
      start = range[1] ? Number(range[1]) : Math.max(0, stat.size - Number(range[2]))
      end = range[1] && range[2] ? Math.min(Number(range[2]), end) : end
      if (start > end || start >= stat.size) { res.writeHead(416, { 'Content-Range': `bytes */${stat.size}` }); return res.end() }
      status = 206
      headers['Content-Range'] = `bytes ${start}-${end}/${stat.size}`
    }
  }
  headers['Content-Length'] = Math.max(0, end - start + 1)
  res.writeHead(status, headers)
  if (req.method === 'HEAD' || stat.size === 0) return res.end()
  const stream = fs.createReadStream(file, { start, end })
  stream.on('error', () => res.destroy())
  res.on('close', () => stream.destroy())
  stream.pipe(res)
})
function openBrowser() {
  if (!process.argv.includes('--open') || process.platform !== 'win32') return
  const url = `http://127.0.0.1:${port}/login`
  // ShellExecute opens the URL in a normal browser window, independently of the hidden helper.
  const opener = spawn('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', path.join(project, 'scripts/open-browser.ps1'), '-Url', url], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] })
  let detail = ''
  opener.stderr.on('data', data => { detail = (detail + data.toString()).slice(-2000) })
  opener.on('error', error => { logError('open-browser', error); console.error(`Open this address manually: ${url}`) })
  opener.on('close', code => {
    if (code !== 0) { logError('open-browser', detail.trim() || `exit code ${code}`); console.error(`Open this address manually: ${url}`) }
    else console.log(`Default browser requested: ${url}`)
  })
}
server.on('error', async error => {
  if (error.code === 'EADDRINUSE') {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/__launcher/status`, { signal: AbortSignal.timeout(2000) })
      const running = await response.json()
      if (running.mode === mode && running.backend === upstream.origin && running.projectRoot === project) {
        console.log(`Local frontend is already running: http://127.0.0.1:${port}/login`)
        openBrowser()
        return
      }
    } catch { /* A different application may occupy the preferred port. */ }
    if (portRetries++ < 20) {
      port += 1
      console.log(`Preferred port occupied; trying http://127.0.0.1:${port}/login`)
      server.listen(port, '127.0.0.1')
      return
    }
  }
  console.error(error.code === 'EADDRINUSE' ? `Port ${port} is already in use. Close the other local server, or change remote-backend.json.` : error)
  process.exitCode = 1
})
server.listen(port, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${port}/login`
  console.log(`Local frontend: ${url}\n${localMode ? "Local" : "Remote"} backend: ${upstream.origin}\nDatabase / knowledge network: ${localMode ? "local independent database" : "accessed through remote backend"}.\nKeep this window open. Press Ctrl+C to stop.`)
  openBrowser()
})
