import {fileURLToPath} from 'node:url'
import {spawnSync} from 'node:child_process'
for (const test of ['check-login-layout.mjs', ...(process.env.TEST_ADMIN_USERNAME ? ['check-admin-layout.mjs'] : [])]) {
 const result=spawnSync(process.execPath,[fileURLToPath(new URL(test,import.meta.url))],{stdio:'inherit',env:process.env})
 if(result.error)throw result.error
 if(result.status!==0)process.exit(result.status||1)
}
if(!process.env.TEST_ADMIN_USERNAME)console.log('Admin checks skipped: provide TEST_ADMIN_USERNAME and TEST_ADMIN_PASSWORD.')
