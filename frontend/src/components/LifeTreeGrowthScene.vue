<template>
  <div
    ref="container"
    class="life-tree-growth-scene"
    aria-label="画像驱动的六周学习成长果树三维画布"
    data-fruit-model="/models/life-tree/apple08.fbx"
    :data-fruit-count="model.fruits?.length || 0"
  ></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js'

const props = defineProps({
  model: { type: Object, required: true },
  selectedId: { type: String, default: '' },
  resetToken: { type: Number, default: 0 },
  growthFrom: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['select', 'ready', 'error'])
const container = ref(null)

const FRUIT_MODEL_URL = '/models/life-tree/apple08.fbx'
const TRANSPARENT_PIXEL = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+Xh5Z4wAAAABJRU5ErkJggg=='
const FRUIT_POSITIONS = [
  new THREE.Vector3(-3.25, 3.85, 1.34),
  new THREE.Vector3(2.95, 4.58, 1.48),
  new THREE.Vector3(-3.28, 5.48, 1.18),
  new THREE.Vector3(3.15, 6.25, 1.34),
  new THREE.Vector3(-2.18, 7.18, 1.2),
  new THREE.Vector3(1.68, 8.05, 1.32),
]
const LEAF_COLORS = ['#214f39', '#2e6444', '#39734c', '#496f45', '#557b49', '#2d5945']

let scene
let camera
let renderer
let controls
let raycaster
let pointer
let resizeObserver
let animationFrame = 0
let treeGroup
let fruitTemplate
let templateMaterial
let pointerStart = null
let hasSized = false
let hasEmittedReady = false
let sceneGeneration = 0
let fruitGroups = []
let clickableMeshes = []
let labelSprites = []
let renderedFruitStates = new Map()
const disposableMaterials = new Set()
const disposableGeometries = new Set()
const disposableTextures = new Set()
const templateGeometries = new Set()

function trackMaterial(material) {
  disposableMaterials.add(material)
  return material
}

function trackGeometry(geometry) {
  disposableGeometries.add(geometry)
  return geometry
}

function resetCamera() {
  if (!camera || !controls) return
  const aspect = container.value?.clientWidth / Math.max(1, container.value?.clientHeight || 1)
  const distance = aspect < 0.7 ? 27 : aspect < 1 ? 22 : 18.5
  camera.position.set(0, 6.6, distance)
  controls.target.set(0, 4.75, 0)
  controls.update()
}

function cylinderBetween(start, end, radiusStart, radiusEnd, material, radialSegments = 10) {
  const direction = new THREE.Vector3().subVectors(end, start)
  const length = direction.length()
  const geometry = trackGeometry(new THREE.CylinderGeometry(radiusEnd, radiusStart, length, radialSegments, 1, false))
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.copy(start).add(end).multiplyScalar(0.5)
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize())
  mesh.castShadow = true
  mesh.receiveShadow = true
  treeGroup.add(mesh)
  return mesh
}

function fruitColor(progress) {
  const normalized = THREE.MathUtils.clamp(Number(progress || 0) / 100, 0, 1)
  const green = new THREE.Color('#61b99b')
  const turning = new THREE.Color('#c79a3b')
  const red = new THREE.Color('#c43d34')
  return normalized < 0.58
    ? green.lerp(turning, normalized / 0.58)
    : turning.lerp(red, (normalized - 0.58) / 0.42)
}

function makeLabelTexture(label, accent, emphasized = false) {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  const compact = /^\d{2}$/.test(label)
  const fontSize = emphasized ? 29 : 25
  context.font = `700 ${fontSize}px "Microsoft YaHei", sans-serif`
  canvas.width = compact ? 64 : Math.min(440, Math.max(190, Math.ceil(context.measureText(label).width + 60)))
  canvas.height = compact ? 64 : emphasized ? 66 : 58
  context.font = `700 ${fontSize}px "Microsoft YaHei", sans-serif`
  if (compact) {
    context.beginPath()
    context.arc(32, 32, 25, 0, Math.PI * 2)
    context.fillStyle = 'rgba(7, 20, 15, 0.88)'
    context.fill()
    context.lineWidth = 2
    context.strokeStyle = accent
    context.stroke()
    context.fillStyle = '#edf4f1'
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.fillText(label, 32, 33)
    const texture = new THREE.CanvasTexture(canvas)
    texture.colorSpace = THREE.SRGBColorSpace
    texture.minFilter = THREE.LinearFilter
    disposableTextures.add(texture)
    return { texture, aspect: 1, compact: true }
  }
  context.fillStyle = 'rgba(7, 20, 15, 0.92)'
  context.strokeStyle = 'rgba(222, 238, 230, 0.18)'
  context.lineWidth = 2
  context.beginPath()
  context.roundRect(1, 1, canvas.width - 2, canvas.height - 2, 8)
  context.fill()
  context.stroke()
  context.fillStyle = accent
  context.fillRect(14, 14, 5, canvas.height - 28)
  context.fillStyle = '#f3f7f4'
  context.textBaseline = 'middle'
  context.fillText(label, 32, canvas.height / 2 + 1)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.minFilter = THREE.LinearFilter
  disposableTextures.add(texture)
  return { texture, aspect: canvas.width / canvas.height, compact: false }
}

function addLabel(node, position, label, emphasized = false) {
  const color = fruitColor(node.progress)
  const { texture, aspect, compact } = makeLabelTexture(label, `#${color.getHexString()}`, emphasized)
  const material = trackMaterial(new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
    depthTest: false,
  }))
  const sprite = new THREE.Sprite(material)
  sprite.position.copy(position)
  const narrow = container.value?.clientWidth / Math.max(1, container.value?.clientHeight || 1) < 0.7
  const height = (compact ? 0.34 : emphasized ? 0.54 : 0.43) * (narrow ? 0.78 : 1)
  sprite.scale.set(height * aspect, height, 1)
  sprite.userData.nodeId = node.id
  sprite.renderOrder = 20
  treeGroup.add(sprite)
  labelSprites.push(sprite)
}

function addLeafCluster(center, scale, colorIndex, rotation = 0) {
  const material = trackMaterial(new THREE.MeshStandardMaterial({
    color: LEAF_COLORS[colorIndex % LEAF_COLORS.length],
    roughness: 0.93,
    metalness: 0,
    flatShading: true,
  }))
  const geometry = trackGeometry(new THREE.IcosahedronGeometry(1, 1))
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.copy(center)
  mesh.rotation.set(rotation * 0.3, rotation, rotation * 0.18)
  mesh.scale.set(scale * 1.3, scale, scale * 0.8)
  mesh.castShadow = true
  treeGroup.add(mesh)
}

function addProfileMarker(profile, barkLight) {
  const discMaterial = trackMaterial(new THREE.MeshStandardMaterial({
    color: profile.status === 'unverified' ? '#597068' : '#d0aa5e',
    emissive: profile.status === 'unverified' ? '#1d2d28' : '#77511c',
    emissiveIntensity: 0.48,
    roughness: 0.62,
    metalness: 0.16,
  }))
  const ring = new THREE.Mesh(trackGeometry(new THREE.TorusGeometry(0.43, 0.07, 10, 42)), barkLight)
  ring.position.set(0, 2.72, 0.82)
  treeGroup.add(ring)
  const disc = new THREE.Mesh(trackGeometry(new THREE.CircleGeometry(0.34, 40)), discMaterial)
  disc.position.set(0, 2.72, 0.84)
  disc.userData.nodeId = profile.id
  treeGroup.add(disc)
  clickableMeshes.push(disc)
  addLabel(profile, new THREE.Vector3(0, 3.38, 0.9), profile.label, true)
}

function addFruit(fruit, position, branchEnd, index, bark) {
  const targetColor = fruitColor(fruit.progress)
  const snapshotState = props.growthFrom?.[fruit.id]
  const previousState = renderedFruitStates.get(fruit.id) || (snapshotState ? {
    scale: Number(snapshotState.growthScale || 0.46),
    color: fruitColor(snapshotState.progress),
  } : null)
  const startColor = previousState?.color?.clone?.() || targetColor.clone()
  const material = trackMaterial(new THREE.MeshStandardMaterial({
    color: startColor,
    emissive: startColor.clone().multiplyScalar(fruit.recommended ? 0.24 : 0.09),
    emissiveIntensity: fruit.recommended ? 0.62 : 0.25,
    roughness: 0.48,
    metalness: 0.03,
  }))
  const fruitGroup = fruitTemplate.clone(true)
  const baseScale = Number(fruit.growthScale || 0.46)
  const startScale = Number(previousState?.scale ?? baseScale)
  const shouldAnimate = Boolean(previousState) && (
    Math.abs(startScale - baseScale) > 0.001
    || Math.abs(startColor.r - targetColor.r) + Math.abs(startColor.g - targetColor.g) + Math.abs(startColor.b - targetColor.b) > 0.001
  )
  fruitGroup.position.copy(position)
  fruitGroup.rotation.y = index * 0.83 - 0.34
  fruitGroup.scale.setScalar(startScale)
  fruitGroup.userData = {
    nodeId: fruit.id,
    node: fruit,
    baseScale,
    visualScale: startScale,
    startScale,
    targetScale: baseScale,
    startColor,
    targetColor,
    material,
    growthStartedAt: shouldAnimate ? performance.now() : 0,
  }
  fruitGroup.traverse((child) => {
    if (!child.isMesh) return
    child.material = material
    child.castShadow = true
    child.receiveShadow = true
    child.userData.nodeId = fruit.id
    clickableMeshes.push(child)
  })
  treeGroup.add(fruitGroup)
  fruitGroups.push(fruitGroup)

  const stemStart = branchEnd.clone()
  const stemEnd = position.clone().add(new THREE.Vector3(0, baseScale * 0.48, 0))
  cylinderBetween(stemStart, stemEnd, 0.045, 0.022, bark, 7)

  if (fruit.recommended) {
    const haloMaterial = trackMaterial(new THREE.MeshBasicMaterial({
      color: '#e3bc64',
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
    }))
    const halo = new THREE.Mesh(trackGeometry(new THREE.TorusGeometry(baseScale * 0.78, 0.035, 8, 40)), haloMaterial)
    halo.rotation.x = Math.PI / 2
    halo.position.y = -baseScale * 0.58
    halo.userData.fruitHalo = true
    fruitGroup.add(halo)
  }

  addLabel(
    fruit,
    position.clone().add(new THREE.Vector3(0, baseScale * 0.72 + 0.38, 0)),
    String(index + 1).padStart(2, '0'),
    fruit.recommended,
  )
}

function clearTree(preserveFruitState = false) {
  if (preserveFruitState) {
    renderedFruitStates = new Map(fruitGroups.map((group) => [
      group.userData.nodeId,
      {
        scale: Number(group.userData.visualScale ?? group.userData.baseScale ?? 0.46),
        color: group.userData.material?.color?.clone?.() || fruitColor(group.userData.node?.progress),
      },
    ]))
  } else {
    renderedFruitStates.clear()
  }
  if (scene && treeGroup) scene.remove(treeGroup)
  disposableTextures.forEach((texture) => texture.dispose())
  disposableMaterials.forEach((material) => material.dispose())
  disposableGeometries.forEach((geometry) => geometry.dispose())
  disposableTextures.clear()
  disposableMaterials.clear()
  disposableGeometries.clear()
  fruitGroups = []
  clickableMeshes = []
  labelSprites = []
  treeGroup = null
}

function buildTree() {
  if (!scene || !fruitTemplate) return
  hasEmittedReady = false
  clearTree(true)
  treeGroup = new THREE.Group()
  treeGroup.name = 'profile-growth-tree'
  scene.add(treeGroup)

  const bark = trackMaterial(new THREE.MeshStandardMaterial({ color: '#69472f', roughness: 0.96, flatShading: true }))
  const barkLight = trackMaterial(new THREE.MeshStandardMaterial({ color: '#8c6541', roughness: 0.9, flatShading: true }))
  const trunkPoints = [
    new THREE.Vector3(0, 0.12, 0),
    new THREE.Vector3(-0.18, 1.75, 0.04),
    new THREE.Vector3(0.18, 3.45, -0.03),
    new THREE.Vector3(-0.08, 5.18, 0.02),
    new THREE.Vector3(0.14, 6.76, -0.02),
    new THREE.Vector3(0.02, 8.55, 0),
  ]
  const radii = [0.82, 0.72, 0.6, 0.45, 0.28, 0.1]
  trunkPoints.slice(0, -1).forEach((point, index) => {
    cylinderBetween(point, trunkPoints[index + 1], radii[index], radii[index + 1], index % 2 ? barkLight : bark, 12)
  })

  const fruits = Array.isArray(props.model?.fruits) ? props.model.fruits.slice(0, 6) : []
  fruits.forEach((fruit, index) => {
    const position = FRUIT_POSITIONS[index]
    const side = Math.sign(position.x) || 1
    const trunkY = Math.max(2.9, position.y - 0.94)
    const start = new THREE.Vector3(side * 0.05, trunkY, 0)
    const elbow = new THREE.Vector3(position.x * 0.55, position.y - 0.54, 0.02)
    const branchEnd = new THREE.Vector3(position.x, position.y + Number(fruit.growthScale || 0.46) * 0.5, position.z - 0.08)
    cylinderBetween(start, elbow, 0.22 - index * 0.018, 0.12 - index * 0.009, index % 2 ? barkLight : bark)
    cylinderBetween(elbow, branchEnd, 0.12 - index * 0.009, 0.045, bark)
    addFruit(fruit, position, branchEnd, index, bark)

    const tangent = new THREE.Vector3(0, 0, side)
    for (let leafIndex = 0; leafIndex < 5; leafIndex += 1) {
      const progress = 0.18 + leafIndex * 0.17
      const center = start.clone().lerp(branchEnd, progress)
      center.add(tangent.clone().multiplyScalar((leafIndex % 2 ? 1 : -1) * (0.38 + leafIndex * 0.06)))
      center.y += 0.44 + (leafIndex % 3) * 0.18
      center.z -= 0.72 + (leafIndex % 2) * 0.2
      addLeafCluster(center, 0.68 + (leafIndex % 2) * 0.16, index + leafIndex, index * 0.6 + leafIndex)
    }
  })

  const canopyCenters = [
    [-4.25, 4.35, -1.2, 1.05], [-2.65, 4.75, -1.45, 1.0], [3.9, 4.95, -1.25, 1.08],
    [-4.1, 5.95, -1.4, 1.0], [-2.45, 6.28, -1.65, 1.12], [2.35, 5.55, -1.55, 1.1], [4.2, 6.2, -1.35, 0.98],
    [-3.15, 7.35, -1.5, 1.08], [-1.2, 7.65, -1.75, 1.18], [1.0, 7.35, -1.72, 1.16], [3.05, 7.35, -1.45, 1.08],
    [-1.75, 8.55, -1.55, 0.98], [0.15, 8.85, -1.72, 1.14], [1.95, 8.55, -1.48, 0.96],
  ]
  canopyCenters.forEach(([x, y, z, scale], index) => addLeafCluster(new THREE.Vector3(x, y, z), scale, index, index * 0.54))

  addProfileMarker(props.model.profile, barkLight)

  const ground = new THREE.Mesh(
    trackGeometry(new THREE.CircleGeometry(16, 96)),
    trackMaterial(new THREE.MeshStandardMaterial({ color: '#10251b', roughness: 1 })),
  )
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.02
  ground.receiveShadow = true
  treeGroup.add(ground)

  for (let index = 0; index < 9; index += 1) {
    const angle = index / 9 * Math.PI * 2
    const reach = 2.45 + index % 3 * 0.45
    const rootEnd = new THREE.Vector3(Math.cos(angle) * reach, 0.08, Math.sin(angle) * reach)
    cylinderBetween(new THREE.Vector3(0, 0.28, 0), rootEnd, 0.23, 0.035, index % 2 ? barkLight : bark)
  }
  updateSelection()
}

function updateSelection() {
  fruitGroups.forEach((group) => {
    const selected = group.userData.nodeId === props.selectedId
    const scale = Number(group.userData.visualScale ?? group.userData.baseScale) * (selected ? 1.13 : 1)
    group.scale.setScalar(scale)
    group.traverse((child) => {
      if (!child.isMesh || child.userData.fruitHalo) return
      child.material.emissiveIntensity = selected ? 0.78 : (group.userData.node?.recommended ? 0.62 : 0.25)
    })
  })
  labelSprites.forEach((sprite) => {
    sprite.material.opacity = sprite.userData.nodeId === props.selectedId ? 1 : 0.9
  })
}

function resize() {
  if (!renderer || !camera || !container.value) return
  const width = Math.max(1, container.value.clientWidth)
  const height = Math.max(1, container.value.clientHeight)
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  if (!hasSized) {
    hasSized = true
    resetCamera()
  }
}

function pointerCoordinates(event) {
  const bounds = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1
  pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1
}

function hitAtPointer(event) {
  pointerCoordinates(event)
  raycaster.setFromCamera(pointer, camera)
  return raycaster.intersectObjects(clickableMeshes, false)[0]
}

function handlePointerDown(event) {
  pointerStart = { x: event.clientX, y: event.clientY }
}

function handlePointerMove(event) {
  if (!renderer) return
  renderer.domElement.style.cursor = hitAtPointer(event) ? 'pointer' : 'grab'
}

function handlePointerUp(event) {
  if (!pointerStart) return
  const moved = Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y)
  pointerStart = null
  if (moved > 7) return
  const hit = hitAtPointer(event)
  emit('select', hit?.object?.userData?.nodeId || '')
}

function animate(time = 0) {
  animationFrame = window.requestAnimationFrame(animate)
  if (!renderer || !scene || !camera || !controls) return
  controls.update()
  fruitGroups.forEach((group, index) => {
    if (group.userData.growthStartedAt) {
      const elapsed = Math.max(0, time - group.userData.growthStartedAt)
      const progress = THREE.MathUtils.clamp(elapsed / 1_050, 0, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      group.userData.visualScale = THREE.MathUtils.lerp(
        group.userData.startScale,
        group.userData.targetScale,
        eased,
      )
      const animatedColor = group.userData.startColor.clone().lerp(group.userData.targetColor, eased)
      group.userData.material.color.copy(animatedColor)
      group.userData.material.emissive.copy(animatedColor).multiplyScalar(group.userData.node?.recommended ? 0.24 : 0.09)
      if (progress >= 1) group.userData.growthStartedAt = 0
      const selected = group.userData.nodeId === props.selectedId
      group.scale.setScalar(group.userData.visualScale * (selected ? 1.13 : 1))
    }
    const halo = group.children.find((child) => child.userData.fruitHalo)
    if (halo) halo.rotation.z = time * 0.0004 * (index % 2 ? -1 : 1)
  })
  renderer.render(scene, camera)
  if (treeGroup && fruitTemplate && !hasEmittedReady) {
    hasEmittedReady = true
    emit('ready')
  }
}

function loadFruitTemplate() {
  const loadGeneration = ++sceneGeneration
  const manager = new THREE.LoadingManager()
  manager.setURLModifier((url) => (/\.(png|jpe?g|tga|bmp)(\?.*)?$/i.test(url) ? TRANSPARENT_PIXEL : url))
  const loader = new FBXLoader(manager)
  loader.load(
    FRUIT_MODEL_URL,
    (object) => {
      if (loadGeneration !== sceneGeneration) return
      const box = new THREE.Box3().setFromObject(object)
      const size = box.getSize(new THREE.Vector3())
      const center = box.getCenter(new THREE.Vector3())
      if (!Number.isFinite(size.y) || size.y <= 0) {
        emit('error', '苹果 FBX 模型尺寸无效')
        return
      }
      templateMaterial = new THREE.MeshBasicMaterial({ color: '#ffffff' })
      object.traverse((child) => {
        if (!child.isMesh) return
        const originalMaterials = Array.isArray(child.material) ? child.material : [child.material]
        originalMaterials.filter(Boolean).forEach((material) => {
          material.map?.dispose()
          material.dispose()
        })
        child.material = templateMaterial
        templateGeometries.add(child.geometry)
      })
      const normalizationScale = 1 / size.y
      object.position.copy(center).multiplyScalar(-normalizationScale)
      object.scale.setScalar(normalizationScale)
      object.updateMatrixWorld(true)
      const normalizedTemplate = new THREE.Group()
      normalizedTemplate.name = 'normalized-apple08-template'
      normalizedTemplate.add(object)
      fruitTemplate = normalizedTemplate
      buildTree()
    },
    undefined,
    (error) => emit('error', error?.message || '苹果 FBX 模型加载失败'),
  )
}

function init() {
  try {
    scene = new THREE.Scene()
    scene.background = new THREE.Color('#07130f')
    scene.fog = new THREE.FogExp2('#07130f', 0.029)
    camera = new THREE.PerspectiveCamera(41, 1, 0.1, 80)
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.08
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6))
    container.value.appendChild(renderer.domElement)

    scene.add(new THREE.HemisphereLight('#c9e4d8', '#38261c', 1.8))
    const keyLight = new THREE.DirectionalLight('#ffe2ad', 4.1)
    keyLight.position.set(7, 13, 9)
    keyLight.castShadow = true
    keyLight.shadow.mapSize.set(2048, 2048)
    keyLight.shadow.camera.left = -11
    keyLight.shadow.camera.right = 11
    keyLight.shadow.camera.top = 13
    keyLight.shadow.camera.bottom = -4
    scene.add(keyLight)
    const rimLight = new THREE.DirectionalLight('#88bca7', 2.15)
    rimLight.position.set(-10, 8, -8)
    scene.add(rimLight)
    const fruitLight = new THREE.PointLight('#d9a85c', 1.7, 18)
    fruitLight.position.set(0, 6.8, 5)
    scene.add(fruitLight)

    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.055
    controls.enablePan = false
    controls.minDistance = 10
    controls.maxDistance = 29
    controls.minPolarAngle = Math.PI * 0.2
    controls.maxPolarAngle = Math.PI * 0.5
    resetCamera()

    raycaster = new THREE.Raycaster()
    pointer = new THREE.Vector2()
    renderer.domElement.addEventListener('pointerdown', handlePointerDown)
    renderer.domElement.addEventListener('pointermove', handlePointerMove)
    renderer.domElement.addEventListener('pointerup', handlePointerUp)
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container.value)
    resize()
    animate()
    loadFruitTemplate()
  } catch (error) {
    emit('error', error?.message || '三维成长果树初始化失败')
  }
}

watch(() => props.model, buildTree, { deep: true })
watch(() => props.selectedId, updateSelection)
watch(() => props.resetToken, resetCamera)

onMounted(init)

onBeforeUnmount(() => {
  sceneGeneration += 1
  window.cancelAnimationFrame(animationFrame)
  resizeObserver?.disconnect()
  if (renderer?.domElement) {
    renderer.domElement.removeEventListener('pointerdown', handlePointerDown)
    renderer.domElement.removeEventListener('pointermove', handlePointerMove)
    renderer.domElement.removeEventListener('pointerup', handlePointerUp)
  }
  clearTree(false)
  controls?.dispose()
  renderer?.dispose()
  renderer?.domElement?.remove()
  templateMaterial?.dispose()
  templateGeometries.forEach((geometry) => geometry.dispose())
  templateGeometries.clear()
})
</script>

<style scoped>
.life-tree-growth-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #07130f;
}

.life-tree-growth-scene :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  outline: none;
  touch-action: none;
}
</style>
