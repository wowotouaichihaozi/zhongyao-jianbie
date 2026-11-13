export function mobileAccountState(ref, mounted, unmounted, form, notify) {
  const query = window.matchMedia('(orientation: portrait)')
  const portrait = ref(query.matches)
  const passwordPage = ref(query.matches && new URLSearchParams(location.search).get('section') === 'password')
  const loggingOut = ref(false)
  function sync() {
    portrait.value = query.matches
    passwordPage.value = query.matches && new URLSearchParams(location.search).get('section') === 'password'
    if (portrait.value && !passwordPage.value) form.oldPassword = form.newPassword = form.confirmPassword = ''
  }
  mounted(() => { sync(); query.addEventListener('change', sync) })
  unmounted(() => query.removeEventListener('change', sync))
  async function logout() {
    if (loggingOut.value) return
    loggingOut.value = true
    try {
      const token = localStorage.getItem('authToken') || ''
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'include', signal: AbortSignal.timeout(8000), headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } })
    } catch { /* A network outage must not prevent signing out on this device. */ }
    try {
      const user = JSON.parse(localStorage.getItem('currentUser') || '{}')
      if (user.username) localStorage.setItem('lastLoginAccount', user.username)
    } catch {}
    for (const key of ['authToken', 'currentUser', 'appMode', 'codexPreviewAuth', 'userPassword']) localStorage.removeItem(key)
    try { for (const key of Object.keys(sessionStorage)) if (/^(saved-path-v1:|resource-history-v1:)/.test(key)) sessionStorage.removeItem(key) } catch {}
    location.replace('/login')
  }
  return { portrait, passwordPage, loggingOut, logout }
}

export function renderMobileAccount(v) {
  const h = v.el, state = v.state, passwordPage = state.passwordPage.value
  const field = (label, key, placeholder, autocomplete, readonly = false) => h('div', { class: 'field-group' }, [
    h('label', { class: 'field-label', for: 'account-' + key }, label),
    h('input', { id: 'account-' + key, class: 'field-input' + (readonly ? ' readonly' : ''), type: key.toLowerCase().includes('password') ? 'password' : 'text', value: readonly ? v.account : v.form[key], placeholder, autocomplete, disabled: readonly, onInput: readonly ? undefined : event => { v.form[key] = event.target.value } }),
  ])
  const submit = event => {
    event.preventDefault()
    if (passwordPage && !v.form.oldPassword && !v.form.newPassword && !v.form.confirmPassword) return v.notify('请输入当前密码', 'error')
    return v.save()
  }
  const fields = passwordPage ? [
    field('当前密码', 'oldPassword', '输入当前密码', 'current-password'),
    field('新密码', 'newPassword', '输入新密码', 'new-password'),
    field('确认新密码', 'confirmPassword', '再次输入新密码', 'new-password'),
  ] : [field('用户名', 'displayName', '输入新用户名', 'username'), field('账号', 'username', '', 'username', true)]
  const avatar = passwordPage ? null : h('div', { class: 'avatar-section' }, [
    h('div', { class: 'avatar-display' }, [h('img', { src: v.avatar, alt: '头像' })]),
    h('label', { class: 'upload-trigger' }, [h('input', { type: 'file', accept: 'image/*', hidden: true, onChange: v.fileChange }), h('span', null, '更换头像')]),
    h('p', { class: 'upload-hint' }, '支持 JPG、PNG，建议 200x200'),
  ])
  return h('div', { class: 'profile-page', 'data-account-section': passwordPage ? 'password' : 'profile' }, [h('div', { class: 'profile-card' }, [
    passwordPage ? h('a', { class: 'local-account-back', href: '/user-profile' }, '← 返回个人中心') : null,
    h('h1', null, passwordPage ? '修改密码' : '个人中心'),
    h('div', { class: 'profile-layout' }, [avatar, h('form', { id: 'profile-form', class: 'form-section', onSubmit: submit }, fields)]),
    h('div', { class: 'save-row' }, [h('button', { type: 'submit', form: 'profile-form', class: 'save-btn', disabled: v.saving }, v.saving ? '保存中...' : passwordPage ? '确认修改密码' : '保存修改')]),
    passwordPage ? null : h('div', { class: 'local-account-actions' }, [
      h('a', { class: 'upload-trigger local-account-password', href: '/user-profile?section=password' }, '修改密码'),
      h('button', { type: 'button', class: 'local-account-logout', disabled: state.loggingOut.value, onClick: state.logout }, state.loggingOut.value ? '正在退出...' : '退出登录'),
    ]),
    v.toast.show ? h('div', { class: ['toast', v.toast.type], role: 'status' }, v.toast.message) : null,
  ])])
}
