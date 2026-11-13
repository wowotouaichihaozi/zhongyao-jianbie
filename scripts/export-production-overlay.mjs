// Export the already verified local view; never rebuild the stale server src.
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
const project = path.resolve(import.meta.dirname, '..')
const output = path.resolve(process.argv[2] || path.join(project, 'release-output'))
const origin = process.env.LOCAL_PREVIEW_URL || 'http://127.0.0.1:5088'
const assets = [
  'assets/index-BPhhYrvy.js', 'assets/PersonalizedResourcesView-XLkt8wIR.js',
  'assets/LearningPathView-Cb-ZCyyA.js', 'assets/LearningPathStageDetailView-De5pET68.js',
  'assets/UserProfileView-bfldUmgr.js', 'assets/QuestionExamSessionView-nJA_fE5H.js',
  'assets/QuestionGeneratorView-DE7HoBSX.js', 'assets/LifeTreeView-HbbrOj0I.js',
]
const helpers = ['local-overrides.css', 'local-resource-history.mjs', 'local-path-cache.mjs', 'local-account-view.mjs', 'local-exam-evidence.mjs']
const files = {}, baseline = {}
baseline['index.html'] = crypto.createHash('sha256').update(fs.readFileSync(path.join(project, 'frontend/dist/index.html'))).digest('hex')
for (const name of assets) {
  const original = fs.readFileSync(path.join(project, 'frontend/dist', name))
  baseline[name] = crypto.createHash('sha256').update(original).digest('hex')
}
for (const name of [...assets, ...helpers]) {
  const response = await fetch(origin + '/' + name)
  if (!response.ok) throw new Error(`Export failed: ${name} HTTP ${response.status}`)
  const content = Buffer.from(await response.arrayBuffer())
  const target = path.join(output, name)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  fs.writeFileSync(target, content)
  files[name] = crypto.createHash('sha256').update(content).digest('hex')
}
for (const [file, marker] of [
  ['assets/index-BPhhYrvy.js', '__savedPath'], ['assets/PersonalizedResourcesView-XLkt8wIR.js', '__localHistory'],
  ['assets/UserProfileView-bfldUmgr.js', '__accountRender'], ['assets/LifeTreeView-HbbrOj0I.js', '__learningDone'],
]) if (!fs.readFileSync(path.join(output, file), 'utf8').includes(marker)) throw new Error('Missing verified overlay: ' + file)
const manifest = { format: 1, base: 'server-static-build', files, baseline, generatedAt: new Date().toISOString() }
fs.writeFileSync(path.join(output, 'overlay-manifest.json'), JSON.stringify(manifest, null, 2))
console.log(JSON.stringify({ exportedFiles: Object.keys(files).length, output }))
