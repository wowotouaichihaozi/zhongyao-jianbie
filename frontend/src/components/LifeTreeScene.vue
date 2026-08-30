<template>
  <div ref="container" class="life-tree-scene" aria-label="交互式中医学习生命树三维画布"></div>
</template>

<script setup>
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const props = defineProps({
  model: { type: Object, required: true },
  selectedId: { type: String, default: '' },
  autoRotate: { type: Boolean, default: true },
  resetToken: { type: Number, default: 0 },
})

const emit = defineEmits(['select', 'ready', 'error'])
const container = ref(null)

const STATUS_COLORS = {
  mastered: '#55d28a',
  developing: '#5aa9ff',
  weak: '#ef756d',
  recommended: '#f2bd52',
  unverified: '#9ca8a3',
}

let scene
let camera
let renderer
let controls
let animationFrame = 0
let resizeObserver
let treeGroup
let nodeMeshes = []
let labelSprites = []
let raycaster
let pointer
let pointerStart = null
let hasEmittedReady = false
let hasSized = false

const disposableMaterials = new Set()
const disposableGeometries = new Set()
const disposableTextures = new Set()

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
  const distance = aspect < 0.7 ? 28 : (aspect < 1 ? 20 : 17)
  camera.position.set(0, 6.8, distance)
  controls.target.set(0, 4.7, 0)
  controls.update()
}

function cylinderBetween(start, end, radiusStart, radiusEnd, material) {
  const direction = new THREE.Vector3().subVectors(end, start)
  const length = direction.length()
  const geometry = trackGeometry(new THREE.CylinderGeometry(radiusEnd, radiusStart, length, 9, 1, false))
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.copy(start).add(end).multiplyScalar(0.5)
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize())
  mesh.castShadow = true
  mesh.receiveShadow = true
  treeGroup.add(mesh)
  return mesh
}

function makeLabelTexture(label, accent, emphasized = false) {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  const fontSize = emphasized ? 34 : 28
  context.font = `700 ${fontSize}px "Microsoft YaHei", sans-serif`
  const width = Math.min(520, Math.max(180, Math.ceil(context.measureText(label).width + 56)))
  canvas.width = width
  canvas.height = emphasized ? 72 : 62
  context.font = `700 ${fontSize}px "Microsoft YaHei", sans-serif`
  context.fillStyle = 'rgba(7, 17, 14, 0.90)'
  context.strokeStyle = 'rgba(255, 255, 255, 0.18)'
  context.lineWidth = 2
  context.beginPath()
  context.roundRect(1, 1, canvas.width - 2, canvas.height - 2, 9)
  context.fill()
  context.stroke()
  context.fillStyle = accent
  context.fillRect(15, 16, 5, canvas.height - 32)
  context.fillStyle = '#f4f7f5'
  context.textBaseline = 'middle'
  context.fillText(label, 34, canvas.height / 2 + 1)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.minFilter = THREE.LinearFilter
  disposableTextures.add(texture)
  return { texture, aspect: canvas.width / canvas.height }
}

function addLabel(node, position, emphasized = false) {
  const status = node.recommended ? 'recommended' : node.status
  const color = STATUS_COLORS[status] || STATUS_COLORS.unverified
  const { texture, aspect } = makeLabelTexture(node.label, color, emphasized)
  const material = trackMaterial(new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
    depthTest: false,
  }))
  const sprite = new THREE.Sprite(material)
  sprite.position.copy(position)
  const narrowScale = container.value?.clientWidth / Math.max(1, container.value?.clientHeight || 1) < 0.7 ? 0.78 : 1
  const height = (emphasized ? 0.58 : 0.43) * narrowScale
  sprite.scale.set(height * aspect, height, 1)
  sprite.userData.nodeId = node.id
  sprite.renderOrder = 20
  treeGroup.add(sprite)
  labelSprites.push(sprite)
  return sprite
}

function addSemanticNode(node, position, radius, showLabel = false) {
  const status = node.recommended ? 'recommended' : node.status
  const color = new THREE.Color(STATUS_COLORS[status] || STATUS_COLORS.unverified)
  const geometry = trackGeometry(new THREE.IcosahedronGeometry(radius, 2))
  const material = trackMaterial(new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: node.recommended ? 1.3 : 0.72,
    metalness: 0.18,
    roughness: 0.34,
  }))
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.copy(position)
  mesh.userData = { nodeId: node.id, baseScale: 1, node }
  mesh.castShadow = true
  treeGroup.add(mesh)
  nodeMeshes.push(mesh)

  const haloGeometry = trackGeometry(new THREE.TorusGeometry(radius * 1.55, radius * 0.08, 8, 32))
  const haloMaterial = trackMaterial(new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: node.recommended ? 0.92 : 0.35,
    depthWrite: false,
  }))
  const halo = new THREE.Mesh(haloGeometry, haloMaterial)
  halo.rotation.x = Math.PI / 2
  halo.userData.nodeHaloFor = node.id
  mesh.add(halo)

  if (showLabel) {
    addLabel(node, position.clone().add(new THREE.Vector3(0, radius + 0.42, 0)), radius > 0.25)
  }
  return mesh
}

function addLeafCluster(center, scale, colorIndex) {
  const colors = ['#1f5a41', '#2d7450', '#3d8055', '#496f48', '#2c6655', '#68794a']
  const material = trackMaterial(new THREE.MeshStandardMaterial({
    color: colors[colorIndex % colors.length],
    roughness: 0.9,
    metalness: 0,
    flatShading: true,
  }))
  const geometry = trackGeometry(new THREE.IcosahedronGeometry(1, 1))
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.copy(center)
  mesh.scale.set(scale * 1.18, scale, scale * 0.88)
  mesh.castShadow = true
  treeGroup.add(mesh)
}

function clearTree() {
  if (!scene || !treeGroup) return
  scene.remove(treeGroup)
  disposableTextures.forEach((texture) => texture.dispose())
  disposableMaterials.forEach((material) => material.dispose())
  disposableGeometries.forEach((geometry) => geometry.dispose())
  disposableTextures.clear()
  disposableMaterials.clear()
  disposableGeometries.clear()
  nodeMeshes = []
  labelSprites = []
}

function buildTree() {
  if (!scene) return
  hasEmittedReady = false
  clearTree()
  treeGroup = new THREE.Group()
  treeGroup.name = 'life-tree'
  scene.add(treeGroup)

  const bark = trackMaterial(new THREE.MeshStandardMaterial({
    color: '#76543b',
    roughness: 0.96,
    metalness: 0,
    flatShading: true,
  }))
  const barkLight = trackMaterial(new THREE.MeshStandardMaterial({
    color: '#926946',
    roughness: 0.9,
    flatShading: true,
  }))

  const trunkPoints = [
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(-0.1, 1.7, 0.08),
    new THREE.Vector3(0.14, 3.3, -0.06),
    new THREE.Vector3(0, 5.05, 0),
    new THREE.Vector3(0.08, 6.25, 0.03),
  ]
  const radii = [0.72, 0.6, 0.47, 0.3, 0.14]
  for (let index = 0; index < trunkPoints.length - 1; index += 1) {
    cylinderBetween(trunkPoints[index], trunkPoints[index + 1], radii[index], radii[index + 1], index % 2 ? barkLight : bark)
  }

  const root = props.model?.profile
  if (root) addSemanticNode(root, new THREE.Vector3(0, 3.15, 0.48), 0.34, true)

  const branches = Array.isArray(props.model?.branches) ? props.model.branches : []
  branches.forEach((branch, branchIndex) => {
    const angle = branchIndex / Math.max(1, branches.length) * Math.PI * 2 - Math.PI / 2
    const direction = new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle))
    const start = new THREE.Vector3(0, 4.0 + (branchIndex % 3) * 0.42, 0)
    const mid = direction.clone().multiplyScalar(2.15)
    mid.y = 5.15 + (branchIndex % 2) * 0.58
    const end = direction.clone().multiplyScalar(4.45)
    end.y = 6.15 + ((branchIndex + 1) % 3) * 0.48
    cylinderBetween(start, mid, 0.28, 0.18, branchIndex % 2 ? barkLight : bark)
    cylinderBetween(mid, end, 0.18, 0.085, bark)

    const tangent = new THREE.Vector3(-direction.z, 0, direction.x)
    for (let leafIndex = 0; leafIndex < 5; leafIndex += 1) {
      const progress = 0.42 + leafIndex * 0.13
      const center = start.clone().lerp(end, progress)
      center.add(tangent.clone().multiplyScalar(((leafIndex % 2) * 2 - 1) * (0.55 + leafIndex * 0.06)))
      center.y += 0.65 + (leafIndex % 3) * 0.28
      center.z += (leafIndex % 2 ? 0.18 : -0.14)
      addLeafCluster(center, 0.95 + (leafIndex % 2) * 0.18, branchIndex + leafIndex)
    }

    const branchPosition = end.clone().add(new THREE.Vector3(0, 0.44, 0))
    addSemanticNode(branch, branchPosition, 0.3, true)

    const children = Array.isArray(branch.children) ? branch.children : []
    children.forEach((node, nodeIndex) => {
      const spread = children.length <= 1 ? 0 : nodeIndex / (children.length - 1) - 0.5
      const reach = 0.95 + (nodeIndex % 3) * 0.36
      const twigStart = mid.clone().lerp(end, 0.58 + (nodeIndex % 3) * 0.14)
      const nodePosition = twigStart.clone()
        .add(direction.clone().multiplyScalar(0.55 + (nodeIndex % 2) * 0.36))
        .add(tangent.clone().multiplyScalar(spread * 3.5))
      nodePosition.y += 0.82 + (nodeIndex % 3) * 0.48
      nodePosition.z += Math.sin(nodeIndex * 1.7 + branchIndex) * reach * 0.24
      cylinderBetween(twigStart, nodePosition, 0.065, 0.022, bark)
      addSemanticNode(node, nodePosition, node.kind === 'path' ? 0.22 : 0.18, node.recommended || node.status === 'weak')
    })
  })

  const groundMaterial = trackMaterial(new THREE.MeshStandardMaterial({
    color: '#14281f',
    roughness: 1,
    metalness: 0,
  }))
  const groundGeometry = trackGeometry(new THREE.CircleGeometry(18, 96))
  const ground = new THREE.Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.02
  ground.receiveShadow = true
  treeGroup.add(ground)

  for (let index = 0; index < 8; index += 1) {
    const angle = index / 8 * Math.PI * 2
    const rootEnd = new THREE.Vector3(Math.cos(angle) * (2.2 + (index % 3) * 0.45), 0.08, Math.sin(angle) * (2.2 + (index % 3) * 0.45))
    cylinderBetween(new THREE.Vector3(0, 0.2, 0), rootEnd, 0.2, 0.035, bark)
  }
  updateSelection()
}

function updateSelection() {
  nodeMeshes.forEach((mesh) => {
    const selected = mesh.userData.nodeId === props.selectedId
    mesh.scale.setScalar(selected ? 1.35 : 1)
    mesh.material.emissiveIntensity = selected ? 1.75 : (mesh.userData.node?.recommended ? 1.3 : 0.72)
    const halo = mesh.children.find((child) => child.userData.nodeHaloFor)
    if (halo) halo.material.opacity = selected ? 1 : (mesh.userData.node?.recommended ? 0.92 : 0.35)
  })
  labelSprites.forEach((sprite) => {
    const selected = sprite.userData.nodeId === props.selectedId
    sprite.material.opacity = selected ? 1 : 0.92
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

function handlePointerDown(event) {
  pointerStart = { x: event.clientX, y: event.clientY }
}

function handlePointerMove(event) {
  if (!renderer) return
  pointerCoordinates(event)
  raycaster.setFromCamera(pointer, camera)
  const hit = raycaster.intersectObjects(nodeMeshes, false)[0]
  renderer.domElement.style.cursor = hit ? 'pointer' : 'grab'
}

function handlePointerUp(event) {
  if (!pointerStart) return
  const moved = Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y)
  pointerStart = null
  if (moved > 7) return
  pointerCoordinates(event)
  raycaster.setFromCamera(pointer, camera)
  const hit = raycaster.intersectObjects(nodeMeshes, false)[0]
  emit('select', hit?.object?.userData?.nodeId || '')
}

function animate(time = 0) {
  animationFrame = window.requestAnimationFrame(animate)
  controls.autoRotate = props.autoRotate
  controls.autoRotateSpeed = 0.32
  controls.update()
  nodeMeshes.forEach((mesh, index) => {
    const halo = mesh.children.find((child) => child.userData.nodeHaloFor)
    if (halo) halo.rotation.z = time * 0.00035 * (index % 2 ? -1 : 1)
  })
  renderer.render(scene, camera)
  if (!hasEmittedReady) {
    hasEmittedReady = true
    emit('ready')
  }
}

function stopAnimation() {
  if (animationFrame) window.cancelAnimationFrame(animationFrame)
  animationFrame = 0
}

function init() {
  try {
    scene = new THREE.Scene()
    scene.background = new THREE.Color('#07130f')
    scene.fog = new THREE.FogExp2('#07130f', 0.032)
    camera = new THREE.PerspectiveCamera(42, 1, 0.1, 80)
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6))
    container.value.appendChild(renderer.domElement)

    const hemisphere = new THREE.HemisphereLight('#c9e7dc', '#3e2a1e', 1.9)
    scene.add(hemisphere)
    const keyLight = new THREE.DirectionalLight('#ffe4b8', 3.8)
    keyLight.position.set(7, 12, 8)
    keyLight.castShadow = true
    keyLight.shadow.mapSize.set(2048, 2048)
    keyLight.shadow.camera.left = -10
    keyLight.shadow.camera.right = 10
    keyLight.shadow.camera.top = 12
    keyLight.shadow.camera.bottom = -4
    scene.add(keyLight)
    const rimLight = new THREE.DirectionalLight('#79bfff', 2.2)
    rimLight.position.set(-9, 6, -8)
    scene.add(rimLight)

    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.055
    controls.enablePan = false
    controls.minDistance = 9
    controls.maxDistance = 25
    controls.minPolarAngle = Math.PI * 0.2
    controls.maxPolarAngle = Math.PI * 0.49
    resetCamera()

    raycaster = new THREE.Raycaster()
    pointer = new THREE.Vector2()
    renderer.domElement.addEventListener('pointerdown', handlePointerDown)
    renderer.domElement.addEventListener('pointermove', handlePointerMove)
    renderer.domElement.addEventListener('pointerup', handlePointerUp)
    renderer.domElement.addEventListener('pointerleave', () => { pointerStart = null })
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container.value)
    buildTree()
    resize()
    animate()
  } catch (error) {
    emit('error', error?.message || '三维生命树初始化失败')
  }
}

watch(() => props.model, buildTree, { deep: true })
watch(() => props.selectedId, updateSelection)
watch(() => props.resetToken, resetCamera)

onMounted(init)

onDeactivated(stopAnimation)

onActivated(() => {
  if (renderer && !animationFrame) animate()
})

onBeforeUnmount(() => {
  stopAnimation()
  resizeObserver?.disconnect()
  if (renderer?.domElement) {
    renderer.domElement.removeEventListener('pointerdown', handlePointerDown)
    renderer.domElement.removeEventListener('pointermove', handlePointerMove)
    renderer.domElement.removeEventListener('pointerup', handlePointerUp)
  }
  clearTree()
  controls?.dispose()
  renderer?.dispose()
  renderer?.domElement?.remove()
})
</script>

<style scoped>
.life-tree-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #07130f;
}

.life-tree-scene :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  outline: none;
  touch-action: none;
}
</style>
