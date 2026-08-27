function randomFraction() {
  return globalThis.crypto?.getRandomValues
    ? globalThis.crypto.getRandomValues(new Uint32Array(1))[0] / 0x100000000
    : Math.random()
}

function shuffled(items, random = randomFraction) {
  const copy = [...items]
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const target = Math.floor(random() * (index + 1))
    ;[copy[index], copy[target]] = [copy[target], copy[index]]
  }
  return copy
}

export function buildHerbAnswerOptions(catalog, herb, random = randomFraction) {
  if (!herb) return []

  const candidates = [...new Map(
    (Array.isArray(catalog) ? catalog : [])
      .filter(item => item?.id && item.id !== herb.id)
      .map(item => [item.id, item]),
  ).values()]
  const sameCategory = candidates.filter(item => item.category === herb.category)
  const otherCategories = candidates.filter(item => item.category !== herb.category)
  const distractors = shuffled(sameCategory, random).slice(0, 3)

  if (distractors.length < 3) {
    distractors.push(...shuffled(otherCategories, random).slice(0, 3 - distractors.length))
  }

  return shuffled([herb, ...distractors], random)
}
