<template>
  <main class="herb-model-page">
    <header class="herb-model-toolbar">
      <button class="icon-button" type="button" title="返回个性化资源" aria-label="返回个性化资源" @click="router.push('/personalized-resources')">
        <ArrowLeft :size="20" aria-hidden="true" />
      </button>
      <div>
        <span>药材模型识别</span>
        <small>{{ catalog.length ? `${catalog.length} 味模型库` : '正在读取模型库' }}</small>
      </div>
      <span v-if="isLearningPathTask" class="task-source">学习路径任务</span>
    </header>

    <section class="recognition-workbench">
      <div ref="sceneHost" class="model-stage" aria-label="可旋转缩放的中药材三维模型">
        <div v-if="loading" class="stage-state" role="status">
          <LoaderCircle :size="30" class="spin" aria-hidden="true" />
          <strong>正在加载药材模型</strong>
        </div>
        <div v-else-if="errorMessage" class="stage-state error" role="alert">
          <TriangleAlert :size="30" aria-hidden="true" />
          <strong>模型暂时无法加载</strong>
          <span>{{ errorMessage }}</span>
          <button type="button" @click="loadSelectedModel">重试</button>
        </div>
        <div class="model-stage-label">
          <ScanSearch :size="17" aria-hidden="true" />
          {{ revealed ? selectedHerb?.name : '待辨识药材' }}
        </div>
        <div class="model-stage-actions">
          <button type="button" title="重置视角" aria-label="重置视角" @click="resetCamera">
            <RotateCcw :size="18" aria-hidden="true" />
          </button>
        </div>
      </div>

      <aside class="recognition-panel">
        <div class="challenge-heading">
          <span>观察任务</span>
          <strong>这味药材是什么？</strong>
          <p>旋转模型观察整体形态、表面纹理与切面结构，再选择答案。</p>
        </div>

        <div class="answer-options" role="group" aria-label="药材名称选项">
          <button
            v-for="option in answerOptions"
            :key="option.id"
            type="button"
            :class="answerOptionClass(option)"
            :disabled="revealed"
            @click="submitAnswer(option)"
          >
            <span>{{ option.name }}</span>
            <Check v-if="revealed && option.id === selectedHerb?.id" :size="18" aria-hidden="true" />
            <X v-else-if="revealed && option.id === chosenHerbId" :size="18" aria-hidden="true" />
          </button>
        </div>

        <div v-if="revealed && selectedHerb" class="answer-analysis" aria-live="polite">
          <div :class="['answer-result', answerCorrect ? 'correct' : 'incorrect']">
            <CircleCheck v-if="answerCorrect" :size="20" aria-hidden="true" />
            <CircleX v-else :size="20" aria-hidden="true" />
            <strong>{{ answerCorrect ? '辨识正确' : `正确答案：${selectedHerb.name}` }}</strong>
          </div>
          <dl>
            <div>
              <dt>药用部位</dt>
              <dd>{{ selectedHerb.medicinalPart }}</dd>
            </div>
            <div>
              <dt>类别</dt>
              <dd>{{ selectedHerb.category }}</dd>
            </div>
          </dl>
          <ul>
            <li v-for="feature in selectedHerb.features" :key="feature">{{ feature }}</li>
          </ul>
        </div>

        <div class="challenge-actions">
          <button v-if="!revealed" class="secondary-button" type="button" @click="revealAnswer">查看答案</button>
          <button v-else class="primary-button" type="button" @click="selectNextHerb">
            <Shuffle :size="17" aria-hidden="true" />
            再认一味
          </button>
        </div>

        <p class="usage-note">模型用于中药材性状学习，不替代实物检验、真伪鉴定或临床判断。</p>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as THREE from 'three'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import {
  ArrowLeft,
  Check,
  CircleCheck,
  CircleX,
  LoaderCircle,
  RotateCcw,
  ScanSearch,
  Shuffle,
  TriangleAlert,
  X,
} from 'lucide-vue-next'
import { getHerbModelCatalog, saveLearningPathNodeCache } from '../services/api.js'
import { buildHerbAnswerOptions } from '../utils/herbAnswerOptions.js'

const router = useRouter()
const route = useRoute()
const sceneHost = ref(null)
const catalog = ref([])
const selectedHerb = ref(null)
const answerOptions = ref([])
const chosenHerbId = ref('')
const revealed = ref(false)
const answerCorrect = ref(false)
const loading = ref(true)
const errorMessage = ref('')
const isLearningPathTask = computed(() => String(route.query.source || '') === 'learning-path')

let renderer = null
let scene = null
let camera = null
let controls = null
let resizeObserver = null
let animationFrame = 0
let currentObject = null
let loadGeneration = 0
const textureLoader = new THREE.TextureLoader()

function shuffled(items) {
  const copy = [...items]
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const random = globalThis.crypto?.getRandomValues
      ? globalThis.crypto.getRandomValues(new Uint32Array(1))[0] / 0x100000000
      : Math.random()
    const target = Math.floor(random * (index + 1))
    ;[copy[index], copy[target]] = [copy[target], copy[index]]
  }
  return copy
}

function chooseRandomHerb(excludedId = '') {
  const candidates = catalog.value.filter(item => item.id !== excludedId)
  return shuffled(candidates)[0] || catalog.value[0] || null
}

function buildAnswerOptions(herb) {
  return buildHerbAnswerOptions(catalog.value, herb)
}

function setSelectedHerb(herb, replaceRoute = true) {
  if (!herb) return
  selectedHerb.value = herb
  answerOptions.value = buildAnswerOptions(herb)
  chosenHerbId.value = ''
  revealed.value = false
  answerCorrect.value = false
  if (replaceRoute) {
    router.replace({ query: { ...route.query, herb: herb.id, mode: 'identify' } })
  }
}

async function loadCatalog() {
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getHerbModelCatalog()
    catalog.value = Array.isArray(payload?.items) ? payload.items : []
    if (!catalog.value.length) throw new Error('模型目录为空')
    const requested = String(route.query.herb || '')
    setSelectedHerb(catalog.value.find(item => item.id === requested) || chooseRandomHerb(), !requested)
  } catch (error) {
    errorMessage.value = error?.response?.data?.msg || error?.message || '药材模型目录读取失败'
    loading.value = false
  }
}

function disposeObject(object) {
  if (!object) return
  object.traverse(child => {
    child.geometry?.dispose?.()
    const materials = Array.isArray(child.material) ? child.material : [child.material]
    materials.filter(Boolean).forEach(material => {
      material.map?.dispose?.()
      material.dispose?.()
    })
  })
  object.parent?.remove(object)
}

function loadTexture(url) {
  return new Promise((resolve, reject) => {
    textureLoader.load(
      url,
      texture => {
        texture.colorSpace = THREE.SRGBColorSpace
        texture.anisotropy = Math.min(8, renderer?.capabilities?.getMaxAnisotropy?.() || 1)
        resolve(texture)
      },
      undefined,
      reject,
    )
  })
}

async function loadSelectedModel() {
  if (!selectedHerb.value || !scene) return
  const generation = ++loadGeneration
  loading.value = true
  errorMessage.value = ''
  disposeObject(currentObject)
  currentObject = null
  try {
    const herb = selectedHerb.value
    const textureEntries = await Promise.all(
      Object.entries(herb.materialTextures || {}).map(async ([material, url]) => [material, await loadTexture(url)]),
    )
    const textures = Object.fromEntries(textureEntries)
    const object = await new OBJLoader().loadAsync(herb.modelUrl)
    if (generation !== loadGeneration) {
      disposeObject(object)
      Object.values(textures).forEach(texture => texture.dispose())
      return
    }
    object.traverse(child => {
      if (!child.isMesh) return
      const sourceMaterials = Array.isArray(child.material) ? child.material : [child.material]
      const mapped = sourceMaterials.map(source => new THREE.MeshStandardMaterial({
        name: source?.name || '',
        map: textures[source?.name] || Object.values(textures)[0] || null,
        color: textures[source?.name] || Object.values(textures)[0] ? 0xffffff : 0xb8a27d,
        roughness: 0.72,
        metalness: 0,
        side: THREE.DoubleSide,
      }))
      child.material = Array.isArray(child.material) ? mapped : mapped[0]
      child.castShadow = true
      child.receiveShadow = true
    })
    const box = new THREE.Box3().setFromObject(object)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const scale = 3.1 / Math.max(size.x, size.y, size.z, 0.001)
    object.scale.setScalar(scale)
    object.position.set(-center.x * scale, -center.y * scale, -center.z * scale)
    scene.add(object)
    currentObject = object
    resetCamera()
  } catch (error) {
    errorMessage.value = error?.message || '模型文件或纹理加载失败'
  } finally {
    if (generation === loadGeneration) loading.value = false
  }
}

function resetCamera() {
  if (!camera || !controls) return
  camera.position.set(0, 0.35, 4.4)
  controls.target.set(0, 0, 0)
  controls.update()
}

function initScene() {
  const host = sceneHost.value
  if (!host) return
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf2f5f1)
  camera = new THREE.PerspectiveCamera(38, 1, 0.05, 100)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  host.prepend(renderer.domElement)

  scene.add(new THREE.HemisphereLight(0xfaf7ef, 0x758478, 2.1))
  const keyLight = new THREE.DirectionalLight(0xffffff, 3.4)
  keyLight.position.set(4, 6, 5)
  keyLight.castShadow = true
  scene.add(keyLight)
  const fillLight = new THREE.DirectionalLight(0xd9b38c, 1.4)
  fillLight.position.set(-4, 1, -3)
  scene.add(fillLight)

  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(2.2, 72),
    new THREE.MeshStandardMaterial({ color: 0xdfe6df, roughness: 1, transparent: true, opacity: 0.72 }),
  )
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -1.62
  ground.receiveShadow = true
  scene.add(ground)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.minDistance = 2.4
  controls.maxDistance = 8
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.75
  resetCamera()

  const resize = () => {
    const width = Math.max(1, host.clientWidth)
    const height = Math.max(1, host.clientHeight)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
  }
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host)
  resize()

  const render = () => {
    animationFrame = window.requestAnimationFrame(render)
    controls.update()
    renderer.render(scene, camera)
  }
  render()
}

function answerOptionClass(option) {
  if (!revealed.value) return { selected: chosenHerbId.value === option.id }
  return {
    correct: option.id === selectedHerb.value?.id,
    incorrect: option.id === chosenHerbId.value && option.id !== selectedHerb.value?.id,
  }
}

async function persistAttempt(correct, answer = '') {
  if (!selectedHerb.value) return
  const attempt = {
    herbId: selectedHerb.value.id,
    herbName: selectedHerb.value.name,
    answer,
    correct,
    completedAt: new Date().toISOString(),
  }
  try {
    const history = JSON.parse(localStorage.getItem('herbModelRecognitionHistory') || '[]')
    localStorage.setItem('herbModelRecognitionHistory', JSON.stringify([attempt, ...history].slice(0, 100)))
  } catch {}
  const cacheKey = String(route.query.cacheKey || '')
  if (!cacheKey) return
  await saveLearningPathNodeCache(cacheKey, {
    status: 'complete',
    progress: 100,
    resourceType: 'herb-model',
    title: `${selectedHerb.value.name}药材模型辨识`,
    route: route.fullPath,
    result: attempt,
  })
}

function submitAnswer(option) {
  if (revealed.value || !selectedHerb.value) return
  chosenHerbId.value = option.id
  answerCorrect.value = option.id === selectedHerb.value.id
  revealed.value = true
  void persistAttempt(answerCorrect.value, option.name)
}

function revealAnswer() {
  if (!selectedHerb.value || revealed.value) return
  chosenHerbId.value = ''
  answerCorrect.value = false
  revealed.value = true
  void persistAttempt(false, '查看答案')
}

function selectNextHerb() {
  setSelectedHerb(chooseRandomHerb(selectedHerb.value?.id))
}

watch(
  () => selectedHerb.value?.id,
  async value => {
    if (!value || !scene) return
    await nextTick()
    await loadSelectedModel()
  },
)

onMounted(async () => {
  initScene()
  await loadCatalog()
})

onBeforeUnmount(() => {
  loadGeneration += 1
  window.cancelAnimationFrame(animationFrame)
  resizeObserver?.disconnect()
  controls?.dispose()
  disposeObject(currentObject)
  scene?.traverse(object => {
    object.geometry?.dispose?.()
    object.material?.dispose?.()
  })
  renderer?.dispose()
  renderer?.domElement?.remove()
})
</script>

<style scoped>
.herb-model-page {
  min-height: 100vh;
  height: 100vh;
  display: grid;
  grid-template-rows: 64px minmax(0, 1fr);
  overflow: hidden;
  color: #172522;
  background: #f7f8f7;
}

.herb-model-toolbar {
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid #dfe5e2;
  background: #ffffff;
}

.icon-button,
.model-stage-actions button {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: 1px solid #d7dfdc;
  border-radius: 6px;
  color: #315c50;
  background: #ffffff;
  cursor: pointer;
}

.herb-model-toolbar > div {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.herb-model-toolbar span {
  font-size: 17px;
  font-weight: 700;
}

.herb-model-toolbar small {
  color: #76817e;
  font-size: 12px;
}

.task-source {
  margin-left: auto;
  padding: 5px 9px;
  border: 1px solid #d7b760;
  border-radius: 5px;
  color: #745713;
  background: #fff8e2;
  font-size: 12px !important;
  font-weight: 600 !important;
}

.recognition-workbench {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 390px);
}

.model-stage {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #f2f5f1;
}

.model-stage :deep(canvas) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.model-stage-label,
.model-stage-actions {
  position: absolute;
  z-index: 2;
  top: 16px;
}

.model-stage-label {
  left: 16px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 6px;
  color: #244a40;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(8px);
  font-size: 13px;
  font-weight: 650;
}

.model-stage-actions {
  right: 16px;
}

.stage-state {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #47615a;
  background: rgba(242, 245, 241, 0.9);
}

.stage-state.error {
  color: #8f382f;
}

.stage-state span {
  max-width: 360px;
  padding: 0 20px;
  text-align: center;
  font-size: 13px;
}

.stage-state button,
.secondary-button,
.primary-button {
  min-height: 38px;
  padding: 0 15px;
  border-radius: 6px;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}

.stage-state button,
.secondary-button {
  border: 1px solid #cfd8d5;
  color: #33564c;
  background: #ffffff;
}

.recognition-panel {
  min-height: 0;
  overflow-y: auto;
  padding: 28px 24px;
  border-left: 1px solid #dde4e1;
  background: #ffffff;
}

.challenge-heading > span {
  display: block;
  margin-bottom: 8px;
  color: #a04439;
  font-size: 12px;
  font-weight: 750;
}

.challenge-heading strong {
  display: block;
  font-size: 22px;
  line-height: 1.25;
}

.challenge-heading p,
.usage-note {
  color: #697572;
  font-size: 13px;
  line-height: 1.65;
}

.answer-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 24px;
}

.answer-options button {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 13px;
  border: 1px solid #dbe1df;
  border-radius: 6px;
  color: #263b36;
  background: #fafbfa;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}

.answer-options button:hover:not(:disabled) {
  border-color: #7da99a;
  background: #f0f7f4;
}

.answer-options button.correct {
  border-color: #37966f;
  color: #176443;
  background: #eaf7f0;
}

.answer-options button.incorrect {
  border-color: #cf796d;
  color: #8f382f;
  background: #fff0ed;
}

.answer-analysis {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid #e5e9e7;
}

.answer-result {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.answer-result.correct { color: #16704b; }
.answer-result.incorrect { color: #a33e35; }

.answer-analysis dl {
  display: grid;
  gap: 8px;
  margin: 0;
}

.answer-analysis dl > div {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  gap: 10px;
  font-size: 13px;
}

.answer-analysis dt { color: #77817f; }
.answer-analysis dd { margin: 0; color: #283b36; }

.answer-analysis ul {
  margin: 16px 0 0;
  padding-left: 20px;
  color: #3e514c;
  font-size: 13px;
  line-height: 1.7;
}

.challenge-actions {
  margin-top: 22px;
  display: flex;
  justify-content: flex-end;
}

.primary-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #17694d;
  color: #ffffff;
  background: #17694d;
}

.usage-note {
  margin: 22px 0 0;
  padding-top: 16px;
  border-top: 1px solid #e5e9e7;
  font-size: 12px;
}

.spin { animation: spin 0.9s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 760px) {
  .herb-model-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
    grid-template-rows: 58px auto;
  }

  .recognition-workbench {
    display: block;
  }

  .model-stage {
    height: 54vh;
    min-height: 390px;
  }

  .recognition-panel {
    overflow: visible;
    padding: 24px 18px 44px;
    border-top: 1px solid #dde4e1;
    border-left: 0;
  }

  .herb-model-toolbar {
    padding: 0 12px;
  }

  .herb-model-toolbar small,
  .task-source {
    display: none;
  }
}
</style>
