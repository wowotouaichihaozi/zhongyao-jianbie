const API_BASE = 'https://lzhan.xyz'

function redirectToLogin() {
  wx.removeStorageSync('authToken')
  wx.removeStorageSync('currentUser')
  const pages = getCurrentPages()
  if (pages[pages.length - 1]?.route !== 'pages/login/login') {
    wx.reLaunch({ url: '/pages/login/login' })
  }
}

function request({ url, method = 'GET', data, header = {}, timeout = 120000 }) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('authToken')
    wx.request({
      url: /^https:\/\//.test(url) ? url : `${API_BASE}${url}`,
      method,
      data,
      timeout,
      header: {
        'content-type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...header,
      },
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data)
          return
        }
        if (response.statusCode === 401) redirectToLogin()
        const details = response.data || {}
        const error = new Error(details.msg || details.message || `请求失败 (${response.statusCode})`)
        error.statusCode = response.statusCode
        error.details = details
        reject(error)
      },
      fail(error) {
        reject(new Error(error.errMsg || '网络请求失败，请检查远程服务和合法域名配置'))
      },
    })
  })
}

function absoluteApiUrl(value) {
  const url = String(value || '')
  if (/^https:\/\//.test(url)) return url
  return url.startsWith('/api/') ? `${API_BASE}${url}` : ''
}

module.exports = { API_BASE, request, absoluteApiUrl }
