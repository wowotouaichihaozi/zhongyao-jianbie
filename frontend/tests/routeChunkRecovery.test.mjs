import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const source = fs.readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')

test('lazy route chunk failures trigger one bounded full-page recovery', () => {
  assert.match(source, /router\.onError/)
  assert.match(source, /Failed to fetch dynamically imported module/)
  assert.match(source, /sessionStorage\.setItem\(ROUTE_CHUNK_RELOAD_KEY/)
  assert.match(source, /now - lastReload < 15000/)
  assert.match(source, /window\.location\.replace\(target\)/)
})
