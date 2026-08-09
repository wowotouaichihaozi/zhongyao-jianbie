<template>
  <div class="profile-page">
    <div class="profile-card">
      <h1>个人中心</h1>

      <div class="profile-layout">
        <!-- 左列：头像 -->
        <div class="avatar-section">
          <div class="avatar-display">
            <img :src="avatarPreview || avatarSrc || DEFAULT_AVATAR" alt="头像" />
          </div>
          <label class="upload-trigger">
            <input type="file" accept="image/*" ref="fileInput" @change="onFileChange" hidden />
            <span>更换头像</span>
          </label>
          <p class="upload-hint">支持 JPG、PNG，建议 200x200</p>
        </div>

        <!-- 右列：表单 -->
        <form id="profile-form" class="form-section" @submit.prevent="handleSave">
          <!-- 用户名 -->
          <div class="field-group">
            <label class="field-label">用户名</label>
            <input v-model="form.displayName" type="text" class="field-input" placeholder="输入新用户名" autocomplete="username" />
          </div>

          <!-- 账号（只读） -->
          <div class="field-group">
            <label class="field-label">账号</label>
            <input :value="userAccount" type="text" class="field-input readonly" disabled autocomplete="username" />
          </div>

          <div class="divider"></div>
          <p class="section-title">修改密码</p>

          <!-- 旧密码 -->
          <div class="field-group">
            <label class="field-label">当前密码</label>
            <input v-model="form.oldPassword" type="password" class="field-input" placeholder="输入当前密码" autocomplete="current-password" />
          </div>

          <!-- 新密码 -->
          <div class="field-group">
            <label class="field-label">新密码</label>
            <input v-model="form.newPassword" type="password" class="field-input" placeholder="输入新密码" autocomplete="new-password" />
          </div>

          <!-- 确认密码 -->
          <div class="field-group">
            <label class="field-label">确认新密码</label>
            <input v-model="form.confirmPassword" type="password" class="field-input" placeholder="再次输入新密码" autocomplete="new-password" />
          </div>
        </form>
      </div>

      <!-- 保存按钮 -->
      <div class="save-row">
        <button type="submit" form="profile-form" class="save-btn" :disabled="saving">
          {{ saving ? '保存中...' : '保存修改' }}
        </button>
      </div>

      <!-- 提示 -->
      <transition name="fade">
        <div v-if="toast.show" :class="['toast', toast.type]">{{ toast.message }}</div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { changePassword } from '../services/api'

const DEFAULT_AVATAR = '/userlogo.png'

const fileInput = ref(null)
const avatarSrc = ref('')
const avatarPreview = ref('')
const avatarFile = ref(null)
const userAccount = ref('')
const userInitial = ref('U')
const saving = ref(false)

const form = reactive({
  displayName: '',
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const toast = reactive({ show: false, message: '', type: 'success' })

function normalizeAvatar(avatar) {
  if (!avatar || String(avatar).startsWith('data:image/svg+xml')) return DEFAULT_AVATAR
  return avatar
}

function showToast(message, type = 'success') {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 2500)
}

onMounted(() => {
  try {
    const user = JSON.parse(localStorage.getItem('currentUser') || '{}')
    const raw = user.avatar || user.avatarUrl || ''
    avatarSrc.value = normalizeAvatar(raw)
    form.displayName = user.displayName || user.username || ''
    userAccount.value = user.username || ''
    userInitial.value = (user.displayName || user.username || 'U').charAt(0)
    localStorage.removeItem('userPassword')
  } catch {
    // ignore
  }
})

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  avatarFile.value = file
  const reader = new FileReader()
  reader.onload = (ev) => { avatarPreview.value = ev.target.result }
  reader.readAsDataURL(file)
}

async function handleSave() {
  // 验证用户名
  if (!form.displayName.trim()) {
    showToast('用户名不能为空', 'error')
    return
  }

  // 如果填写了密码字段，验证密码
  const hasPasswordChange = form.oldPassword || form.newPassword || form.confirmPassword
  if (hasPasswordChange) {
    if (!form.oldPassword) {
      showToast('请输入当前密码', 'error')
      return
    }
    if (!form.newPassword) {
      showToast('请输入新密码', 'error')
      return
    }
    if (form.newPassword !== form.confirmPassword) {
      showToast('两次输入的新密码不一致', 'error')
      return
    }
    if (form.newPassword.length < 8) {
      showToast('新密码至少 8 位', 'error')
      return
    }
  }

  saving.value = true

  try {
    if (hasPasswordChange) {
      await changePassword({
        currentPassword: form.oldPassword,
        newPassword: form.newPassword,
      })
    }

    const user = JSON.parse(localStorage.getItem('currentUser') || '{}')

    // 更新用户名
    user.displayName = form.displayName.trim()

    // 更新头像：有预览用预览，有头像URL用URL，否则用默认头像
    const newAvatar = avatarPreview.value || avatarSrc.value || DEFAULT_AVATAR
    user.avatar = newAvatar
    user.avatarUrl = newAvatar

    // 只在浏览器保存非敏感的界面资料
    localStorage.setItem('currentUser', JSON.stringify(user))

    if (hasPasswordChange) {
      form.oldPassword = ''
      form.newPassword = ''
      form.confirmPassword = ''
    }

    // 更新本地状态
    avatarSrc.value = newAvatar
    userInitial.value = form.displayName.charAt(0)

    // 通知顶部导航栏同步
    window.dispatchEvent(new Event('current-user-change'))

    showToast('保存成功')
  } catch (error) {
    showToast(error?.response?.data?.msg || '保存失败，请重试', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 24px;
  background: #f4faf9;
}

.profile-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  padding: 40px 48px 36px;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
  max-width: 640px;
  width: 100%;
}

.profile-card h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0 0 32px;
}

.profile-layout {
  display: flex;
  gap: 40px;
}

/* 头像区域 */
.avatar-section {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-display {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid rgba(31, 166, 112, 0.25);
}

.avatar-display img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-initial {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  font-weight: 700;
}

.upload-trigger {
  cursor: pointer;
  padding: 6px 16px;
  border-radius: 6px;
  background: rgba(31, 166, 112, 0.08);
  color: #117a51;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.2s;
}

.upload-trigger:hover {
  background: rgba(31, 166, 112, 0.16);
}

.upload-hint {
  font-size: 12px;
  color: #94a3b8;
  margin: 0;
  text-align: center;
}

/* 表单区域 */
.form-section {
  flex: 1;
  min-width: 0;
}

.field-group {
  margin-bottom: 18px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 6px;
}

.field-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  color: #1f3f3b;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: #21b978;
}

.field-input.readonly {
  background: #f1f5f9;
  color: #94a3b8;
  cursor: not-allowed;
}

.divider {
  height: 1px;
  background: #e2e8f0;
  margin: 24px 0 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0 0 18px;
}

/* 保存按钮 */
.save-row {
  margin-top: 32px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  padding: 10px 32px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Toast */
.toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  z-index: 9999;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

.toast.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.toast.error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* 响应式 */
@media (max-width: 560px) {
  .profile-page {
    min-height: 100vh;
    padding: 24px 14px calc(128px + env(safe-area-inset-bottom));
    align-items: stretch;
  }

  .profile-layout {
    flex-direction: column;
    align-items: center;
  }

  .profile-card {
    padding: 28px 20px 30px;
    border-radius: 22px;
  }

  .field-input {
    min-height: 46px;
    border-radius: 12px;
    font-size: 15px;
  }

  .upload-trigger,
  .save-btn {
    min-height: 46px;
    border-radius: 999px;
  }

  .save-row {
    position: sticky;
    bottom: calc(92px + env(safe-area-inset-bottom));
    z-index: 20;
    justify-content: stretch;
    margin-top: 24px;
  }

  .save-btn {
    width: 100%;
    box-shadow: 0 14px 28px rgba(17, 122, 81, 0.2);
  }
}
</style>
