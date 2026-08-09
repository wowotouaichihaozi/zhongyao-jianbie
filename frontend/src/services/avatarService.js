import { pingLegacyAvatar, speakLegacyAvatar, startLegacyAvatar, stopLegacyAvatar } from './api.js'

let sdkModulePromise = null
let playerModulePromise = null

export async function loadAvatarSdk() {
  if (typeof window === 'undefined') {
    throw new Error('数字人 SDK 只能在浏览器环境中初始化')
  }
  if (!sdkModulePromise) {
    sdkModulePromise = import('../vendor/avatar-sdk-web_3.2.3.1002/esm/index.js')
  }
  return sdkModulePromise
}

async function loadAvatarPlayer() {
  if (typeof window === 'undefined') {
    throw new Error('数字人播放器只能在浏览器环境中初始化')
  }
  if (!playerModulePromise) {
    playerModulePromise = import('../vendor/avatar-sdk-web_3.2.3.1002/esm/player.js')
  }
  return playerModulePromise
}

function normalizeNumber(value, fallback) {
  const next = Number(value)
  return Number.isFinite(next) ? next : fallback
}

function createRequestId() {
  const random = Math.random().toString(16).slice(2, 10)
  return `avatar_${Date.now()}_${random}`
}

export function validateAvatarConfig(config = {}) {
  const missing = []
  if (!config.appId) missing.push('appId')
  if (!config.sceneId) missing.push('sceneId')
  if (!config.avatarId) missing.push('avatarId')
  if (!config.signedUrl && !(config.apiKey && config.apiSecret)) {
    missing.push('signedUrl 或 apiKey/apiSecret')
  }
  return missing
}

function buildApiInfo(config = {}) {
  const signedUrl = String(config.signedUrl || '').trim()
  return {
    serverUrl: config.serverUrl || '',
    appId: config.appId || '',
    sceneId: config.sceneId || '',
    sceneVersion: config.sceneVersion || '',
    // The backend signs the short-lived websocket URL so long-lived
    // API credentials never enter the browser runtime.
    signedUrl,
  }
}

function buildGlobalParams(config = {}) {
  const avatar = config.avatar || {}
  const stream = config.stream || {}
  const tts = config.tts || {}

  return {
    stream: {
      protocol: stream.protocol || 'xrtc',
      fps: normalizeNumber(stream.fps, 25),
      bitrate: normalizeNumber(stream.bitrate, 1000000),
      alpha: normalizeNumber(stream.alpha, 1),
    },
    avatar: {
      avatar_id: config.avatarId || '',
      width: normalizeNumber(avatar.width, 720),
      height: normalizeNumber(avatar.height, 1280),
      audio_format: normalizeNumber(avatar.audio_format, 1),
    },
    tts: {
      vcn: config.vcn || 'x4_yezi',
      speed: normalizeNumber(tts.speed, 50),
      pitch: normalizeNumber(tts.pitch, 50),
      volume: normalizeNumber(tts.volume, 100),
    },
    avatar_dispatch: {
      interactive_mode: 1,
      enable_action_status: 1,
      content_analysis: 0,
    },
    subtitle: {
      subtitle: 1,
      font_color: '#FFFFFF',
    },
    air: {
      air: 0,
      add_nonsemantic: 0,
    },
    header: {
      request_id: createRequestId(),
    },
  }
}

function isAutoplayError(error) {
  const raw = error?.message || error?.name || String(error || '')
  return /play\(\) failed|NotAllowedError|not-allowed|autoplay|gesture|interact|NotAllowedWithoutGesture/i.test(raw)
}

function isAvatarAuthError(error) {
  const raw = error?.message || error?.name || String(error || '')
  return /authentication|auth|11200|11203|1006|鉴权|授权/i.test(raw)
}

function parseXrtcStream(streamUrl) {
  const match = String(streamUrl || '').trim().match(/^xrtc(s?):\/\/([^/]+)\/([^/?#]+)/i)
  if (!match) return null
  const [, secureSuffix, host, roomId] = match
  return {
    server: `http${secureSuffix ? 's' : ''}://${host}`,
    roomId,
  }
}

function buildLegacyStartError(legacy, originalError) {
  const attempts = Array.isArray(legacy?.attempts) ? legacy.attempts : []
  const lastAttempt = attempts[attempts.length - 1] || {}
  const code = lastAttempt.code || legacy?.code || ''
  const message = lastAttempt.message || legacy?.error || originalError?.message || ''
  if (/1120\d|20015|authentication|auth|avatar_id|invalid/i.test(`${code} ${message}`)) {
    return new Error(`数字人服务鉴权或形象授权失败（讯飞返回 ${code || '未知错误'}），请确认 APPID、接口服务 ID 和形象 ID 属于同一数字人服务`)
  }
  return new Error(message || '数字人备用通道启动失败')
}

export function normalizeAvatarDom(wrapper) {
  if (!wrapper) return
  const hasCanvas = !!wrapper.querySelector('canvas')
  wrapper.classList.toggle('has-avatar-canvas', hasCanvas)

  const nodes = wrapper.querySelectorAll(':scope > #xvideo, :scope > [id*="xvideo"], :scope > iframe')
  nodes.forEach((node) => {
    node.style.width = '100%'
    node.style.height = '100%'
    node.style.maxWidth = '100%'
    node.style.maxHeight = '100%'
    node.style.background = node.tagName === 'IFRAME' ? '#ffffff' : 'transparent'
    node.style.border = '0'
    node.style.display = 'block'
    node.style.overflow = 'hidden'
  })

  Array.from(wrapper.children).forEach((child) => {
    child.style.background = 'transparent'
    child.style.overflow = 'hidden'
  })

  wrapper.querySelectorAll('canvas').forEach((media) => {
    media.style.display = 'block'
    media.style.width = '100%'
    media.style.height = '100%'
    media.style.maxWidth = '100%'
    media.style.maxHeight = '100%'
    media.style.opacity = '1'
    media.style.objectFit = 'contain'
    media.style.objectPosition = 'center bottom'
    media.style.pointerEvents = 'none'
  })

  wrapper.querySelectorAll('video').forEach((video) => {
    if (hasCanvas) {
      video.style.position = 'absolute'
      video.style.width = '0'
      video.style.height = '0'
      video.style.maxWidth = '0'
      video.style.maxHeight = '0'
      video.style.opacity = '0'
      video.style.pointerEvents = 'none'
      return
    }
    video.style.width = '100%'
    video.style.height = '100%'
    video.style.maxWidth = '100%'
    video.style.maxHeight = '100%'
    video.style.opacity = '1'
    video.style.objectFit = 'contain'
    video.style.objectPosition = 'center bottom'
    video.style.pointerEvents = 'none'
  })
}

export function clearAvatarStage(wrapper) {
  if (!wrapper) return
  wrapper.replaceChildren()
  wrapper.classList.remove('has-avatar-canvas')
}

function withTimeout(promise, ms, message) {
  let timer = 0
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = window.setTimeout(() => reject(new Error(message)), ms)
    }),
  ]).finally(() => {
    if (timer) window.clearTimeout(timer)
  })
}

export class AvatarService {
  constructor(options = {}) {
    this.avatar = null
    this.sdk = null
    this.playerEventsBound = false
    this.globalParams = null
    this.config = null
    this.legacyPlayer = null
    this.legacySession = ''
    this.legacyPingTimer = 0
    this.legacyMode = false
    this.audioEnabled = false
    this.wrapper = null
    this.onStatus = options.onStatus || (() => {})
    this.onError = options.onError || (() => {})
    this.onEvent = options.onEvent || (() => {})
  }

  async init(config) {
    const missing = validateAvatarConfig(config)
    if (missing.length) {
      throw new Error(`数字人配置不完整：缺少 ${missing.join(', ')}`)
    }

    this.sdk = await loadAvatarSdk()
    this.config = config
    const AvatarPlatform = this.sdk.default
    this.avatar = new AvatarPlatform({
      useInlinePlayer: true,
      logLevel: 2,
      binaryData: false,
    })
    this.bindSdkEvents()
    this.avatar.setApiInfo(buildApiInfo(config))
    this.globalParams = buildGlobalParams(config)
    this.avatar.setGlobalParams(this.globalParams)
    if (this.avatar.player) {
      this.avatar.player.renderAlign = 'bottom'
      this.avatar.player.defaultMuted = true
      this.avatar.player.muted = true
      this.avatar.player.volume = 0
    }
    this.bindPlayerEvents()
    this.onStatus('ready')
    return this
  }

  bindSdkEvents() {
    if (!this.avatar || !this.sdk?.SDKEvents) return
    const { SDKEvents } = this.sdk

    this.avatar
      .on(SDKEvents.connected, (payload) => {
        this.onStatus('connected', payload)
        this.onEvent(SDKEvents.connected, payload)
        this.bindPlayerEvents()
      })
      .on(SDKEvents.disconnected, (payload) => {
        this.onStatus('disconnected', payload)
        this.onEvent(SDKEvents.disconnected, payload)
      })
      .on(SDKEvents.frame_start, (payload) => {
        if (this.audioEnabled) {
          void this.resumeRenderedMedia()
        }
        this.onStatus('speaking', payload)
        this.onEvent(SDKEvents.frame_start, payload)
      })
      .on(SDKEvents.frame_stop, (payload) => {
        this.onStatus('waiting', payload)
        this.onEvent(SDKEvents.frame_stop, payload)
      })
      .on(SDKEvents.subtitle_info, (payload) => {
        this.onEvent(SDKEvents.subtitle_info, payload)
      })
      .on(SDKEvents.error, (error) => {
        if (isAutoplayError(error)) {
          this.onStatus('resume-required', error)
          this.onEvent(SDKEvents.error, error)
          return
        }
        this.onStatus('error', error)
        this.onError(error)
        this.onEvent(SDKEvents.error, error)
      })
  }

  bindPlayerEvents() {
    if (this.playerEventsBound || !this.avatar?.player || !this.sdk?.PlayerEvents) return
    const { PlayerEvents } = this.sdk
    this.avatar.player
      .on(PlayerEvents.playNotAllowed, (error) => {
        this.onStatus('resume-required', error)
        this.onEvent(PlayerEvents.playNotAllowed, error)
      })
      .on(PlayerEvents.error, (error) => {
        if (isAutoplayError(error)) {
          this.onStatus('resume-required', error)
          return
        }
        this.onStatus('error', error)
        this.onError(error)
      })
    this.playerEventsBound = true
  }

  async start(wrapper) {
    if (!this.avatar) {
      throw new Error('数字人 SDK 尚未初始化')
    }
    if (!wrapper) {
      throw new Error('数字人渲染容器不存在')
    }
    this.onStatus('connecting')
    this.wrapper = wrapper
    clearAvatarStage(wrapper)
    if (this.globalParams) {
      this.globalParams = {
        ...this.globalParams,
        header: {
          ...(this.globalParams.header || {}),
          request_id: createRequestId(),
        },
      }
      this.avatar.setGlobalParams(this.globalParams)
    }
    try {
      await this.avatar.start({ wrapper })
      normalizeAvatarDom(wrapper)
      this.bindPlayerEvents()
      this.onStatus('connected')
    } catch (error) {
      if (!isAvatarAuthError(error)) {
        throw error
      }
      try {
        await this.startLegacyFallback(wrapper, error)
      } catch (fallbackError) {
        clearAvatarStage(wrapper)
        throw fallbackError
      }
    }
  }

  async startLegacyFallback(wrapper, originalError) {
    await this.stopLegacyFallback()
    this.onStatus('connecting', { mode: 'legacy-vms', reason: originalError?.message || String(originalError || '') })

    const legacy = await startLegacyAvatar({
      protocol: 'xrtc',
      avatarId: this.config?.avatarId || '',
    })
    if (!legacy?.success || !legacy.streamUrl) {
      throw buildLegacyStartError(legacy, originalError)
    }

    const parsedStream = parseXrtcStream(legacy.streamUrl)
    if (!parsedStream) {
      await stopLegacyAvatar({ session: legacy.session }).catch(() => {})
      throw new Error('数字人备用通道返回了无法识别的 XRTC 流地址')
    }

    const xrtcAuth = String(legacy.xrtcUserSign || legacy.userSign || '').replace(/^Bearer\s+/i, '')
    const xrtcAppId = legacy.xrtcAppId || legacy.appid || legacy.appId || this.config?.appId || ''
    if (!xrtcAuth) {
      await stopLegacyAvatar({ session: legacy.session }).catch(() => {})
      throw new Error('数字人备用通道缺少 XRTC 播放鉴权，请检查该 APPID 是否已授权当前形象')
    }

    const { RTCPlayer } = await loadAvatarPlayer()
    this.legacyPlayer = new RTCPlayer()
    this.legacyPlayer.playerType = 'xrtc'
    this.legacyPlayer.renderAlign = 'bottom'
    this.legacyPlayer.defaultMuted = true
    this.legacyPlayer.muted = true
    this.legacyPlayer.volume = 0
    this.legacyPlayer.videoSize = {
      width: normalizeNumber(legacy.width, 1280),
      height: normalizeNumber(legacy.height, 720),
    }

    clearAvatarStage(wrapper)
    await withTimeout(this.legacyPlayer.playStream({
      sid: legacy.sid || legacy.session || '',
      server: parsedStream.server,
      auth: xrtcAuth,
      appid: xrtcAppId,
      timeStr: `${Date.now()}`,
      userId: `c${parsedStream.roomId}`,
      roomId: parsedStream.roomId,
    }), 15000, '数字人备用通道播放超时')
    normalizeAvatarDom(wrapper)
    this.legacySession = legacy.session || ''
    this.legacyMode = true
    if (this.legacySession) {
      this.legacyPingTimer = window.setInterval(() => {
        pingLegacyAvatar({ session: this.legacySession }).catch(() => {})
      }, 25000)
    }
    this.onStatus('connected', { mode: 'legacy-vms', fallbackFrom: originalError?.message || '' })
  }

  async writeText(text, extend = {}) {
    if (!this.avatar && !this.legacyMode) {
      throw new Error('数字人 SDK 尚未初始化')
    }
    const content = String(text || '').trim()
    if (!content) return ''
    if (this.legacyMode) {
      return speakLegacyAvatar({ session: this.legacySession, text: content })
    }
    return this.avatar.writeText(content, {
      nlp: false,
      avatar_dispatch: {
        interactive_mode: 1,
      },
      ...extend,
    })
  }

  async interrupt() {
    if (this.legacyMode) return
    if (this.avatar) {
      await this.avatar.interrupt()
    }
  }

  async resumePlayer() {
    this.audioEnabled = true
    const renderedMediaPlayback = this.resumeRenderedMedia()
    if (this.legacyMode && this.legacyPlayer?.resume) {
      this.legacyPlayer.defaultMuted = false
      this.legacyPlayer.muted = false
      this.legacyPlayer.volume = 1
      await this.legacyPlayer.resume()
      await renderedMediaPlayback
      await this.resumeRenderedMedia()
      this.onStatus('connected', { mode: 'legacy-vms' })
      return
    }
    if (this.avatar?.player?.resume) {
      this.avatar.player.defaultMuted = false
      this.avatar.player.muted = false
      this.avatar.player.volume = 1
      await this.avatar.player.resume()
      await renderedMediaPlayback
      await this.resumeRenderedMedia()
      this.onStatus('connected')
    }
  }

  async resumeRenderedMedia() {
    const mediaElements = Array.from(this.wrapper?.querySelectorAll?.('video, audio') || [])
    const playback = mediaElements.map((media) => {
      media.defaultMuted = false
      media.muted = false
      if (typeof media.volume === 'number') {
        media.volume = 1
      }
      try {
        return Promise.resolve(media.play?.()).catch(() => false)
      } catch {
        return Promise.resolve(false)
      }
    })
    await Promise.allSettled(playback)
    return mediaElements.length > 0
  }

  async stop() {
    if (this.legacyMode) {
      await this.stopLegacyFallback()
      this.onStatus('disconnected')
      return
    }
    if (this.avatar) {
      try {
        await this.avatar.stop?.()
      } catch (error) {
        this.onError(error)
      }
      this.onStatus('disconnected')
    }
  }

  async stopLegacyFallback() {
    if (this.legacyPingTimer) {
      window.clearInterval(this.legacyPingTimer)
      this.legacyPingTimer = 0
    }
    if (this.legacyPlayer) {
      try {
        this.legacyPlayer.stop?.()
        this.legacyPlayer.destroy?.()
      } catch (error) {
        this.onError(error)
      }
      this.legacyPlayer = null
    }
    if (this.legacySession) {
      const session = this.legacySession
      this.legacySession = ''
      await stopLegacyAvatar({ session }).catch(() => {})
    }
    this.legacyMode = false
  }

  async destroy() {
    await this.stopLegacyFallback()
    if (this.avatar) {
      try {
        await this.avatar.stop?.()
      } catch {
        // stop is a best-effort resource release before destroying the SDK instance.
      }
      try {
        await this.avatar.destroy?.()
      } catch (error) {
        this.onError(error)
      }
      this.avatar = null
    }
    clearAvatarStage(this.wrapper)
    this.wrapper = null
    this.audioEnabled = false
    this.playerEventsBound = false
    this.onStatus('destroyed')
  }
}

export function createAvatarService(options) {
  return new AvatarService(options)
}
