import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

import {
  buildLoginRedirectPath,
  internalRedirectFromLocation,
  safeInternalRedirect,
} from '../src/utils/authRedirect.js'

test('preserves an internal path with its query and hash', () => {
  const target = '/resource-detail?id=task%3Axz_1%3Ahandout&tab=evidence#quality-review'

  assert.equal(safeInternalRedirect(target), target)
  assert.equal(
    new URL(buildLoginRedirectPath(target), 'https://app.invalid').searchParams.get('redirect'),
    target,
  )
})

test('rejects external, ambiguous, malformed, and login-loop redirects', () => {
  const rejected = [
    'https://example.com/resource-detail',
    '//example.com/resource-detail',
    '/\\example.com/resource-detail',
    '/%5cexample.com/resource-detail',
    '/%255cexample.com/resource-detail',
    '/%2f%2fexample.com/resource-detail',
    '/%252f%252fexample.com/resource-detail',
    'javascript:alert(1)',
    '/',
    '/login',
    '/login/',
    '/LOGIN?redirect=%2Fresource-detail',
    '/%6cogin?redirect=%2Fresource-detail',
    '/login%2Fnested?redirect=%2Fresource-detail',
    '/%2Flogin?redirect=%2Fresource-detail',
    '/resource-detail\u0000?task=1',
    '',
    null,
  ]

  rejected.forEach((value) => assert.equal(safeInternalRedirect(value), ''))
  assert.equal(safeInternalRedirect('//example.com', '/learning-profile'), '/learning-profile')
  assert.equal(buildLoginRedirectPath('/login?redirect=%2Fresource-detail'), '/login')
})

test('captures the current local pathname, query, and hash for a 401 redirect', () => {
  assert.equal(internalRedirectFromLocation({
    pathname: '/personalized-resources',
    search: '?type=document&task=xz_1',
    hash: '#history',
  }), '/personalized-resources?type=document&task=xz_1#history')

  assert.equal(internalRedirectFromLocation({
    pathname: '/login',
    search: '?redirect=%2Flearning-path',
    hash: '',
  }), '')
})

test('wires the shared redirect contract into the guard, 401 handler, and active auth page', () => {
  const routerSource = fs.readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')
  const apiSource = fs.readFileSync(new URL('../src/services/api.js', import.meta.url), 'utf8')
  const authSource = fs.readFileSync(new URL('../src/views/HerbWiseLoginPage.vue', import.meta.url), 'utf8')

  assert.match(routerSource, /query:\s*\{ redirect: safeInternalRedirect\(to\.fullPath\) \}/)
  assert.match(apiSource, /internalRedirectFromLocation\(window\.location\)/)
  assert.match(apiSource, /window\.location\.href = buildLoginRedirectPath\(redirectTarget\)/)
  assert.match(authSource, /ref\(safeInternalRedirect\(route\.query\.redirect\)\)/)
  assert.match(authSource, /if \(pendingRoute\.value\) openAuth\('login'\)/)
  assert.match(authSource, /window\.location\.replace\(target\)/)
  assert.equal(
    authSource.match(/redirectAfterAuthentication\(pendingRoute\.value \|\| DEFAULT_AUTHENTICATED_PATH\)/g)?.length,
    2,
  )
  assert.doesNotMatch(authSource, /router\.replace\(pendingRoute\.value \|\| DEFAULT_AUTHENTICATED_PATH\)/)
})
