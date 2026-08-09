App({
  globalData: {
    apiBase: 'https://lzhan.xyz',
    user: wx.getStorageSync('currentUser') || {},
  },
})
