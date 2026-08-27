import assert from 'node:assert/strict'
import test from 'node:test'

import { buildHerbAnswerOptions } from '../src/utils/herbAnswerOptions.js'

const herbs = [
  ['ginseng', 'root'], ['eucommia', 'bark'], ['angelica', 'root'], ['forsythia', 'fruit'],
  ['gardenia', 'fruit'], ['scrophularia', 'root'], ['inula', 'flower'], ['amomum', 'fruit'],
  ['poria', 'fungus'], ['cinnamon', 'bark'], ['tangerine-peel', 'fruit'], ['chuanxiong', 'root'],
  ['red-sage', 'root'], ['notoginseng', 'root'], ['ox-gallstone', 'animal'], ['hawthorn', 'fruit'],
  ['pumpkin-seed', 'fruit'], ['dendrobium', 'stem'], ['pilose-antler', 'animal'], ['prunella', 'whole'],
].map(([id, category]) => ({ id, name: id, category }))

function seededRandom(seed) {
  let state = seed >>> 0
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0
    return state / 0x100000000
  }
}

test('every herb challenge includes one correct answer and three unique distractors', () => {
  herbs.forEach((herb, herbIndex) => {
    for (let run = 0; run < 50; run += 1) {
      const options = buildHerbAnswerOptions(herbs, herb, seededRandom(herbIndex * 100 + run + 1))
      assert.equal(options.length, 4)
      assert.equal(options.filter(option => option.id === herb.id).length, 1)
      assert.equal(new Set(options.map(option => option.id)).size, 4)
    }
  })
})

test('small catalogs still include the correct answer without duplicate options', () => {
  for (let size = 1; size <= 3; size += 1) {
    const catalog = herbs.slice(0, size)
    catalog.forEach((herb, index) => {
      const options = buildHerbAnswerOptions(catalog, herb, seededRandom(size * 10 + index))
      assert.equal(options.length, size)
      assert.equal(options.filter(option => option.id === herb.id).length, 1)
      assert.equal(new Set(options.map(option => option.id)).size, size)
    })
  }
})
