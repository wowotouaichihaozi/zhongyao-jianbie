<template>
  <main class="knowledge-page">
    <header class="knowledge-header">
      <RouterLink class="back-link" to="/personalized-resources">
        <ArrowLeft :size="18" />
        <span>个性化资源</span>
      </RouterLink>
      <div class="title-row">
        <div>
          <p class="eyebrow">HYBRID KNOWLEDGE</p>
          <h1>混合知识库</h1>
        </div>
        <div class="header-actions">
          <RouterLink class="network-entry" to="/knowledge-network">
            <Share2 :size="18" />
            <span><strong>知识网络</strong><small>Obsidian 风格关系视图</small></span>
            <ArrowRight :size="16" />
          </RouterLink>
          <dl class="knowledge-stats" aria-label="知识库统计">
            <div><dt>知识库</dt><dd>{{ state.stats.collectionCount || 0 }}</dd></div>
            <div><dt>文档</dt><dd>{{ state.stats.documentCount || 0 }}</dd></div>
            <div><dt>片段</dt><dd>{{ state.stats.chunkCount || 0 }}</dd></div>
          </dl>
        </div>
      </div>
    </header>

    <section class="knowledge-shell" :aria-busy="loading">
      <aside class="collection-sidebar">
        <div class="sidebar-heading">
          <div>
            <span>知识库</span>
            <small>{{ state.collections.length }}</small>
          </div>
          <button class="icon-command" type="button" title="新建知识库" @click="showCreate = !showCreate">
            <FolderPlus :size="19" />
          </button>
        </div>

        <form v-if="showCreate" class="create-form" @submit.prevent="createCollection">
          <label>
            <span>名称</span>
            <input v-model.trim="newCollection.name" maxlength="80" autofocus required />
          </label>
          <label>
            <span>备注</span>
            <textarea v-model.trim="newCollection.description" maxlength="500" rows="2"></textarea>
          </label>
          <div class="form-actions">
            <button class="text-button secondary" type="button" @click="cancelCreate">取消</button>
            <button class="text-button primary" type="submit" :disabled="busyAction === 'create'">
              <LoaderCircle v-if="busyAction === 'create'" class="spin" :size="16" />
              <Check v-else :size="16" />
              创建
            </button>
          </div>
        </form>

        <div v-if="loading" class="sidebar-loading">
          <LoaderCircle class="spin" :size="22" />
        </div>
        <div v-else-if="!state.collections.length" class="sidebar-empty">
          <Database :size="28" />
          <span>暂无知识库</span>
        </div>
        <div v-else class="collection-list">
          <button
            v-for="collection in state.collections"
            :key="collection.id"
            class="collection-item"
            :class="{ selected: collection.id === selectedCollectionId }"
            type="button"
            @click="selectCollection(collection.id)"
          >
            <span class="collection-icon"><BookOpen :size="18" /></span>
            <span class="collection-copy">
              <strong>{{ collection.name }}</strong>
              <small>{{ collection.documentCount }} 个文档 · {{ collection.chunkCount }} 个片段</small>
            </span>
            <span v-if="collection.isActive" class="active-dot" title="当前使用"></span>
          </button>
        </div>
      </aside>

      <div class="knowledge-workspace">
        <div v-if="!activeCollection && !loading" class="workspace-empty">
          <Database :size="48" />
          <h2>新建第一个知识库</h2>
          <button class="text-button primary" type="button" @click="showCreate = true">
            <FolderPlus :size="17" />
            新建知识库
          </button>
        </div>

        <template v-else-if="activeCollection">
          <div class="workspace-heading">
            <div class="workspace-title">
              <div class="title-line">
                <h2>{{ activeCollection.name }}</h2>
                <span v-if="activeCollection.isActive" class="active-label">当前使用</span>
              </div>
              <p>{{ activeCollection.description || '暂无备注' }}</p>
            </div>
            <div class="workspace-actions">
              <button
                v-if="!activeCollection.isActive"
                class="text-button activate"
                type="button"
                :disabled="busyAction === 'activate'"
                @click="activateSelected"
              >
                <CheckCircle2 :size="17" />
                设为当前
              </button>
              <button class="icon-command" type="button" title="重命名" @click="beginEdit">
                <Pencil :size="18" />
              </button>
              <button class="icon-command danger" type="button" title="删除知识库" @click="removeCollection">
                <Trash2 :size="18" />
              </button>
            </div>
          </div>

          <form v-if="editing" class="edit-form" @submit.prevent="saveCollection">
            <input v-model.trim="editCollection.name" maxlength="80" required />
            <input v-model.trim="editCollection.description" maxlength="500" placeholder="备注" />
            <button class="icon-command success" type="submit" title="保存"><Check :size="18" /></button>
            <button class="icon-command" type="button" title="取消" @click="editing = false"><X :size="18" /></button>
          </form>

          <section class="document-section" aria-labelledby="document-title">
            <div class="section-heading">
              <div>
                <h3 id="document-title">资料文档</h3>
                <span>{{ activeCollection.documentCount }} 个</span>
              </div>
              <label class="upload-button" :class="{ disabled: uploading }">
                <LoaderCircle v-if="uploading" class="spin" :size="17" />
                <Upload v-else :size="17" />
                <span>{{ uploading ? '解析中' : '上传文件' }}</span>
                <input
                  type="file"
                  accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf"
                  :disabled="uploading"
                  @change="uploadFile"
                />
              </label>
            </div>

            <div v-if="uploading" class="upload-progress">
              <span></span>
            </div>

            <div v-if="!activeCollection.documents.length" class="document-empty">
              <FileText :size="32" />
              <span>暂无资料文档</span>
            </div>
            <div v-else class="document-list">
              <article v-for="document in activeCollection.documents" :key="document.id" class="document-row">
                <span class="file-icon"><FileText :size="20" /></span>
                <div class="document-copy">
                  <strong>{{ document.filename }}</strong>
                  <small>{{ formatBytes(document.byteSize) }} · {{ document.chunkCount }} 个片段</small>
                </div>
                <span class="ready-status"><CheckCircle2 :size="15" /> 已索引</span>
                <button class="icon-command danger" type="button" title="删除文档" @click="removeDocument(document)">
                  <Trash2 :size="17" />
                </button>
              </article>
            </div>
          </section>

          <section class="retrieval-section" aria-labelledby="retrieval-title">
            <div class="section-heading retrieval-heading">
              <div>
                <h3 id="retrieval-title">混合路由验证</h3>
                <span>QA 对 + 文档切块 + 知识图谱</span>
              </div>
            </div>
            <form class="search-form" @submit.prevent="searchKnowledge">
              <Search :size="19" />
              <input v-model.trim="searchQuery" placeholder="输入知识点" maxlength="300" required />
              <button type="submit" :disabled="searching">
                <LoaderCircle v-if="searching" class="spin" :size="17" />
                <span>{{ searching ? '检索中' : '检索' }}</span>
              </button>
            </form>

            <div v-if="searchResult" class="search-result">
              <div class="result-summary">
                <span>命中 {{ searchResult.hits?.length || 0 }} 条</span>
                <span v-if="searchResult.activePrivateCollection">
                  私有来源：{{ searchResult.activePrivateCollection.name }}
                </span>
              </div>
              <div v-if="searchResult.routing" class="routing-status">
                <div class="route-strip" aria-label="混合检索路由">
                  <span
                    v-for="route in searchResult.routing.routes"
                    :key="route.id"
                    class="route-chip"
                    :class="route.id"
                  >
                    {{ route.label }}
                    <strong>{{ route.matched }}</strong>
                  </span>
                </div>
                <div
                  class="verification-state"
                  :class="searchResult.routing.crossValidation?.status"
                >
                  <ShieldCheck
                    v-if="searchResult.routing.crossValidation?.status === 'corroborated'"
                    :size="17"
                  />
                  <ShieldAlert v-else :size="17" />
                  <span>{{ verificationLabel(searchResult.routing.crossValidation) }}</span>
                  <small>
                    证据一致度 {{ formatAgreement(searchResult.routing.crossValidation?.agreementScore) }}
                  </small>
                </div>
              </div>
              <div v-if="searchResult.hits?.length" class="hit-list">
                <article v-for="hit in searchResult.hits" :key="`${hit.citationId}-${hit.source}-${hit.section}`" class="hit-row">
                  <span class="citation" :class="[hit.route, { private: hit.scope === 'private' }]">{{ hit.citationId }}</span>
                  <div>
                    <strong>{{ hit.title }}</strong>
                    <small>{{ knowledgeSourceLabel(hit) }} · {{ hit.source }}</small>
                    <p>{{ hit.excerpt }}</p>
                  </div>
                </article>
              </div>
              <div v-else class="no-hit">未命中可追溯片段</div>
            </div>
          </section>
        </template>
      </div>
    </section>

    <div v-if="notice.message" class="notice" :class="notice.type" role="status">
      <CheckCircle2 v-if="notice.type === 'success'" :size="18" />
      <CircleAlert v-else :size="18" />
      <span>{{ notice.message }}</span>
      <button type="button" aria-label="关闭" @click="notice.message = ''"><X :size="16" /></button>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  CircleAlert,
  Database,
  FileText,
  FolderPlus,
  LoaderCircle,
  Pencil,
  Search,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import {
  activateKnowledgeCollection,
  createKnowledgeCollection,
  deleteKnowledgeCollection,
  deleteKnowledgeDocument,
  getKnowledgeCollections,
  retrieveKnowledge,
  updateKnowledgeCollection,
  uploadKnowledgeDocument,
} from '../services/api.js'

const state = reactive({
  collections: [],
  activeCollectionId: null,
  stats: { collectionCount: 0, documentCount: 0, chunkCount: 0 },
})
const selectedCollectionId = ref(null)
const loading = ref(true)
const uploading = ref(false)
const searching = ref(false)
const busyAction = ref('')
const showCreate = ref(false)
const editing = ref(false)
const searchQuery = ref('')
const searchResult = ref(null)
const newCollection = reactive({ name: '', description: '' })
const editCollection = reactive({ name: '', description: '' })
const notice = reactive({ type: 'success', message: '' })

const activeCollection = computed(() => {
  return state.collections.find(item => item.id === selectedCollectionId.value) || null
})

function setNotice(message, type = 'success') {
  notice.message = message
  notice.type = type
}

function errorMessage(error) {
  return error?.response?.data?.msg || error?.message || '操作失败'
}

function applyState(data, preferredId = null) {
  state.collections = Array.isArray(data?.collections) ? data.collections : []
  state.activeCollectionId = data?.activeCollectionId || null
  state.stats = data?.stats || { collectionCount: 0, documentCount: 0, chunkCount: 0 }
  const currentExists = state.collections.some(item => item.id === selectedCollectionId.value)
  const preferredExists = state.collections.some(item => item.id === preferredId)
  if (preferredExists) selectedCollectionId.value = preferredId
  else if (!currentExists) selectedCollectionId.value = state.activeCollectionId || state.collections[0]?.id || null
}

async function loadCollections(preferredId = null) {
  loading.value = true
  try {
    const response = await getKnowledgeCollections()
    applyState(response.data, preferredId)
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  } finally {
    loading.value = false
  }
}

function selectCollection(collectionId) {
  selectedCollectionId.value = collectionId
  editing.value = false
  searchResult.value = null
}

function cancelCreate() {
  showCreate.value = false
  newCollection.name = ''
  newCollection.description = ''
}

async function createCollection() {
  if (!newCollection.name) return
  busyAction.value = 'create'
  try {
    const response = await createKnowledgeCollection({
      name: newCollection.name,
      description: newCollection.description,
      activate: true,
    })
    const collectionId = response.data.id
    cancelCreate()
    await loadCollections(collectionId)
    setNotice('知识库已创建')
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  } finally {
    busyAction.value = ''
  }
}

function beginEdit() {
  if (!activeCollection.value) return
  editCollection.name = activeCollection.value.name
  editCollection.description = activeCollection.value.description || ''
  editing.value = true
}

async function saveCollection() {
  if (!activeCollection.value || !editCollection.name) return
  busyAction.value = 'edit'
  try {
    await updateKnowledgeCollection(activeCollection.value.id, {
      name: editCollection.name,
      description: editCollection.description,
    })
    editing.value = false
    await loadCollections(activeCollection.value.id)
    setNotice('知识库已更新')
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  } finally {
    busyAction.value = ''
  }
}

async function activateSelected() {
  if (!activeCollection.value) return
  busyAction.value = 'activate'
  try {
    await activateKnowledgeCollection(activeCollection.value.id)
    await loadCollections(activeCollection.value.id)
    setNotice('已设为当前知识库')
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  } finally {
    busyAction.value = ''
  }
}

async function removeCollection() {
  if (!activeCollection.value) return
  const collection = activeCollection.value
  if (!window.confirm(`删除知识库“${collection.name}”及其中全部文档？`)) return
  try {
    const response = await deleteKnowledgeCollection(collection.id)
    applyState(response.data)
    searchResult.value = null
    setNotice('知识库已删除')
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  }
}

async function uploadFile(event) {
  const input = event.target
  const file = input.files?.[0]
  input.value = ''
  if (!file || !activeCollection.value) return
  uploading.value = true
  try {
    await uploadKnowledgeDocument(activeCollection.value.id, file)
    await loadCollections(activeCollection.value.id)
    setNotice('文件已解析并写入知识库')
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  } finally {
    uploading.value = false
  }
}

async function removeDocument(document) {
  if (!window.confirm(`删除文档“${document.filename}”？`)) return
  try {
    const response = await deleteKnowledgeDocument(document.id)
    applyState(response.data, activeCollection.value?.id)
    searchResult.value = null
    setNotice('文档已删除')
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  }
}

async function searchKnowledge() {
  if (!searchQuery.value) return
  searching.value = true
  try {
    const response = await retrieveKnowledge({ query: searchQuery.value, topK: 8 })
    searchResult.value = response.data
  } catch (error) {
    setNotice(errorMessage(error), 'error')
  } finally {
    searching.value = false
  }
}

function formatBytes(value) {
  const bytes = Number(value || 0)
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function knowledgeSourceLabel(hit) {
  if (hit?.scope === 'private') return '我的文档切块'
  if (hit?.route === 'qa') return 'QA 精确问答'
  if (hit?.route === 'graph') return '知识图谱节点'
  return '课程文档切块'
}

function verificationLabel(verification) {
  if (verification?.status === 'corroborated') return '已通过多源交叉验证'
  if (verification?.status === 'low_agreement') return '多源结论一致度不足，需核验'
  if (verification?.status === 'single_source') return '单源证据，需进一步核验'
  return '证据不足，禁止无依据生成'
}

function formatAgreement(value) {
  return `${Math.round(Math.max(0, Math.min(1, Number(value || 0))) * 100)}%`
}

onMounted(() => loadCollections())
</script>

<style scoped>
.knowledge-page {
  min-height: calc(100vh - 72px);
  padding: 30px 32px 56px;
  color: #173533;
  background: #f3f8f6;
  box-sizing: border-box;
}

.knowledge-header {
  width: min(1280px, 100%);
  margin: 0 auto 20px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 18px;
  color: #5d7470;
  font-size: 14px;
  text-decoration: none;
}

.back-link:hover { color: #0f9f69; }

.title-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.header-actions {
  display: flex;
  align-items: stretch;
  gap: 10px;
}

.network-entry {
  min-width: 210px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid #b9d9cf;
  border-radius: 6px;
  background: #173d35;
  color: #ffffff;
  text-decoration: none;
}

.network-entry > span { flex: 1; }
.network-entry strong,
.network-entry small { display: block; }
.network-entry strong { font-size: 13px; }
.network-entry small { margin-top: 2px; color: #a8d6c9; font-size: 9px; }

.eyebrow {
  margin: 0 0 5px;
  color: #b94862;
  font-size: 11px;
  font-weight: 800;
}

h1 {
  margin: 0;
  color: #173533;
  font-size: 30px;
  line-height: 1.2;
}

.knowledge-stats {
  display: flex;
  margin: 0;
  border: 1px solid #dce8e4;
  border-radius: 8px;
  background: #ffffff;
}

.knowledge-stats div {
  min-width: 92px;
  padding: 10px 16px;
  text-align: center;
  border-left: 1px solid #e3ece9;
}

.knowledge-stats div:first-child { border-left: 0; }
.knowledge-stats dt { color: #758a86; font-size: 11px; }
.knowledge-stats dd { margin: 2px 0 0; color: #173533; font-size: 19px; font-weight: 800; }

.knowledge-shell {
  width: min(1280px, 100%);
  min-height: 650px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  border: 1px solid #dce8e4;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
}

.collection-sidebar {
  min-width: 0;
  padding: 18px 14px;
  border-right: 1px solid #e2ebe8;
  background: #f8fbfa;
}

.sidebar-heading,
.section-heading,
.workspace-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.sidebar-heading { padding: 0 4px 12px; }
.sidebar-heading > div { display: flex; align-items: center; gap: 8px; font-weight: 800; }
.sidebar-heading small { color: #80928f; font-size: 12px; }

.icon-command {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dbe7e3;
  border-radius: 7px;
  color: #526d68;
  background: #ffffff;
  cursor: pointer;
}

.icon-command:hover { color: #0f9f69; border-color: #a9d9c8; }
.icon-command.danger:hover { color: #c13f55; border-color: #efbcc5; background: #fff6f7; }
.icon-command.success { color: #0f9f69; }

.create-form {
  margin-bottom: 12px;
  padding: 12px;
  display: grid;
  gap: 10px;
  border: 1px solid #cfe4dc;
  border-radius: 8px;
  background: #ffffff;
}

.create-form label { display: grid; gap: 5px; color: #607773; font-size: 12px; }
.create-form input,
.create-form textarea,
.edit-form input,
.search-form input {
  width: 100%;
  border: 1px solid #d7e4e0;
  border-radius: 6px;
  color: #173533;
  background: #ffffff;
  font: inherit;
  box-sizing: border-box;
  outline: none;
}

.create-form input,
.create-form textarea { padding: 9px 10px; font-size: 13px; resize: vertical; }
.create-form input:focus,
.create-form textarea:focus,
.edit-form input:focus,
.search-form:focus-within { border-color: #54bc95; }

.form-actions { display: flex; justify-content: flex-end; gap: 8px; }
.text-button {
  min-height: 36px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: 7px;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.text-button.primary { color: #ffffff; background: #119b67; }
.text-button.secondary { color: #5d7470; border-color: #dbe7e3; background: #ffffff; }
.text-button.activate { color: #0b8056; border-color: #b8dfd0; background: #edf9f4; }
.text-button:disabled { opacity: 0.55; cursor: not-allowed; }

.collection-list { display: grid; gap: 5px; }
.collection-item {
  width: 100%;
  min-height: 64px;
  padding: 10px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 10px;
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #2a4844;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.collection-item:hover { background: #eff7f4; }
.collection-item.selected { border-color: #b9dfd1; background: #eaf7f2; }
.collection-icon,
.file-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  color: #0f9665;
  background: #ddf3ea;
}

.collection-copy,
.document-copy { min-width: 0; display: grid; gap: 4px; }
.collection-copy strong,
.document-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.collection-copy small,
.document-copy small { color: #788d89; font-size: 11px; }
.active-dot { width: 8px; height: 8px; border-radius: 50%; background: #13a66f; }

.sidebar-loading,
.sidebar-empty {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #8a9b98;
  font-size: 13px;
}

.knowledge-workspace { min-width: 0; padding: 26px 30px 34px; }
.workspace-empty {
  min-height: 560px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #8a9b98;
}
.workspace-empty h2 { margin: 0; color: #294743; font-size: 20px; }

.workspace-heading { min-height: 60px; padding-bottom: 20px; border-bottom: 1px solid #e4ece9; }
.title-line { display: flex; align-items: center; gap: 10px; }
.workspace-title h2 { margin: 0; color: #173533; font-size: 22px; }
.workspace-title p { margin: 6px 0 0; color: #718783; font-size: 13px; }
.active-label,
.ready-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #0f8d60;
  font-size: 11px;
  font-weight: 700;
}
.active-label { padding: 4px 8px; border-radius: 4px; background: #e8f7f1; }
.workspace-actions { display: flex; align-items: center; gap: 8px; }

.edit-form {
  margin: 14px 0 0;
  padding: 10px;
  display: grid;
  grid-template-columns: minmax(140px, 0.7fr) minmax(180px, 1.3fr) 36px 36px;
  gap: 8px;
  border: 1px solid #dbe7e3;
  border-radius: 8px;
  background: #f8fbfa;
}
.edit-form input { min-height: 36px; padding: 0 10px; font-size: 13px; }

.document-section,
.retrieval-section { padding-top: 26px; }
.section-heading h3 { margin: 0; color: #294743; font-size: 16px; }
.section-heading > div { display: flex; align-items: baseline; gap: 8px; }
.section-heading span { color: #7c908c; font-size: 12px; }

.upload-button {
  min-height: 38px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #a9d9c8;
  border-radius: 7px;
  color: #0d875b;
  background: #edf9f4;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.upload-button input { display: none; }
.upload-button.disabled { opacity: 0.6; cursor: wait; }
.upload-progress { height: 3px; margin-top: 12px; overflow: hidden; background: #e3efeb; }
.upload-progress span { display: block; width: 40%; height: 100%; background: #13a66f; animation: upload 1.2s ease-in-out infinite; }

.document-list { margin-top: 14px; border-top: 1px solid #e4ece9; }
.document-row {
  min-height: 64px;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto 36px;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #e8efed;
}
.document-row .file-icon { color: #3f78bf; background: #eaf1fb; }
.document-empty,
.no-hit {
  min-height: 120px;
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px dashed #cfddd9;
  border-radius: 8px;
  color: #8a9b98;
  font-size: 13px;
  background: #fbfdfc;
}

.retrieval-heading { margin-bottom: 12px; }
.search-form {
  min-height: 46px;
  padding-left: 14px;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  border: 1px solid #d7e4e0;
  border-radius: 8px;
  color: #6e8581;
  overflow: hidden;
}
.search-form input { height: 44px; padding: 0; border: 0; font-size: 14px; }
.search-form button {
  height: 46px;
  min-width: 86px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  color: #ffffff;
  background: #119b67;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.search-form button:disabled { opacity: 0.65; cursor: wait; }

.search-result { margin-top: 14px; border-top: 1px solid #e4ece9; }
.result-summary { min-height: 44px; display: flex; align-items: center; gap: 18px; color: #677e79; font-size: 12px; }
.routing-status {
  padding: 12px 0 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border-top: 1px solid #edf2f0;
}
.route-strip { display: flex; flex-wrap: wrap; gap: 7px; }
.route-chip {
  min-height: 28px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #cdded9;
  border-radius: 5px;
  color: #48645f;
  background: #f5f9f8;
  font-size: 11px;
}
.route-chip strong { color: #173d35; font-size: 12px; }
.route-chip.qa { border-color: #c9d9ef; color: #315f96; background: #f1f6fc; }
.route-chip.graph { border-color: #d8cfec; color: #65459a; background: #f6f2fb; }
.verification-state {
  min-height: 32px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-left: 3px solid #bc4960;
  color: #8f3347;
  background: #fff5f6;
  font-size: 12px;
}
.verification-state.corroborated { border-left-color: #149264; color: #176c4d; background: #edf9f4; }
.verification-state small { color: inherit; opacity: 0.72; }
.hit-list { border-top: 1px solid #edf2f0; }
.hit-row {
  padding: 16px 0;
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr);
  gap: 12px;
  border-bottom: 1px solid #edf2f0;
}
.citation { align-self: start; padding: 5px 7px; border-radius: 4px; color: #346fae; background: #eaf1fa; font-size: 11px; font-weight: 800; text-align: center; }
.citation.private { color: #b13f59; background: #fff0f3; }
.citation.qa { color: #246ea4; background: #eaf4fb; }
.citation.graph { color: #6a499d; background: #f1ecf8; }
.hit-row strong { display: block; color: #294743; font-size: 14px; }
.hit-row small { display: block; margin-top: 3px; color: #7c908c; font-size: 11px; }
.hit-row p { margin: 8px 0 0; color: #536c67; font-size: 12px; line-height: 1.65; display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }

.notice {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 1400;
  max-width: min(420px, calc(100vw - 32px));
  min-height: 46px;
  padding: 0 12px 0 15px;
  display: flex;
  align-items: center;
  gap: 9px;
  border: 1px solid #b8dfd0;
  border-radius: 8px;
  color: #176c4d;
  background: #f0faf6;
  box-shadow: 0 14px 36px rgba(29, 69, 61, 0.16);
  font-size: 13px;
}
.notice.error { color: #9f354a; border-color: #efbcc5; background: #fff5f6; }
.notice button { margin-left: auto; display: inline-flex; border: 0; color: inherit; background: transparent; cursor: pointer; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes upload { 0% { transform: translateX(-100%); } 100% { transform: translateX(350%); } }

@media (max-width: 900px) {
  .knowledge-page { padding: 24px 18px 120px; }
  .knowledge-shell { grid-template-columns: 240px minmax(0, 1fr); }
  .knowledge-workspace { padding: 22px; }
  .knowledge-stats div { min-width: 72px; padding: 9px 10px; }
  .header-actions { flex-direction: column; }
  .network-entry { min-width: 0; }
}

@media (max-width: 700px) {
  .title-row { align-items: stretch; flex-direction: column; }
  .header-actions { align-items: stretch; }
  .knowledge-stats { align-self: stretch; }
  .knowledge-stats div { flex: 1; }
  .knowledge-shell { display: block; }
  .collection-sidebar { border-right: 0; border-bottom: 1px solid #e2ebe8; }
  .collection-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .workspace-heading { align-items: flex-start; }
  .workspace-actions { flex-wrap: wrap; justify-content: flex-end; }
  .edit-form { grid-template-columns: 1fr 36px 36px; }
  .edit-form input:nth-child(2) { grid-column: 1 / -1; grid-row: 2; }
  .document-row { grid-template-columns: 40px minmax(0, 1fr) 36px; }
  .ready-status { display: none; }
  .routing-status { align-items: stretch; flex-direction: column; }
  .verification-state { align-self: flex-start; }
}

@media (max-width: 480px) {
  .collection-list { grid-template-columns: 1fr; }
  .knowledge-workspace { padding: 18px 14px 26px; }
  .workspace-heading { display: grid; }
  .workspace-actions { justify-content: flex-start; }
  .section-heading { align-items: flex-start; }
  .result-summary { align-items: flex-start; flex-direction: column; gap: 4px; padding: 10px 0; }
  .verification-state { width: 100%; box-sizing: border-box; flex-wrap: wrap; }
}
</style>
