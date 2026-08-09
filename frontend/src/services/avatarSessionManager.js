const START_EVENT = 'digital-human-avatar:start'
const RELEASE_EVENT = 'digital-human-avatar:release'
const CHANNEL_NAME = 'digital-human-avatar-session'

let broadcastChannel = null

function getBroadcastChannel() {
  if (typeof window === 'undefined' || typeof BroadcastChannel === 'undefined') {
    return null
  }
  if (!broadcastChannel) {
    broadcastChannel = new BroadcastChannel(CHANNEL_NAME)
  }
  return broadcastChannel
}

function emitSessionEvent(type, detail) {
  if (typeof window === 'undefined') return

  window.dispatchEvent(new CustomEvent(type, { detail }))
  getBroadcastChannel()?.postMessage({ type, detail })
}

export function createAvatarSessionController(ownerId, onTakeover) {
  let active = true
  const channel = getBroadcastChannel()

  function handleSessionEvent(type, detail = {}) {
    if (!active || detail.ownerId === ownerId) return
    if (type === START_EVENT) {
      onTakeover?.(detail)
    }
  }

  function handleWindowStart(event) {
    handleSessionEvent(START_EVENT, event.detail)
  }

  function handleBroadcast(event) {
    handleSessionEvent(event.data?.type, event.data?.detail)
  }

  if (typeof window !== 'undefined') {
    window.addEventListener(START_EVENT, handleWindowStart)
  }
  channel?.addEventListener('message', handleBroadcast)

  return {
    ownerId,
    claim() {
      emitSessionEvent(START_EVENT, { ownerId, at: Date.now() })
    },
    release() {
      emitSessionEvent(RELEASE_EVENT, { ownerId, at: Date.now() })
    },
    dispose() {
      active = false
      if (typeof window !== 'undefined') {
        window.removeEventListener(START_EVENT, handleWindowStart)
      }
      channel?.removeEventListener('message', handleBroadcast)
    },
  }
}
