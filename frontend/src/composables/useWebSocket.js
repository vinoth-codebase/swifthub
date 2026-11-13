import { ref } from 'vue'
import { getWsUrl } from '../api/client'

export function useWebSocket(onMessage) {
  const status = ref('disconnected')
  let socket = null
  let reconnectTimer = null
  let retries = 0
  let closedManually = false

  function connect() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return
    }
    closedManually = false
    status.value = retries > 0 ? 'reconnecting' : 'connecting'

    try {
      socket = new WebSocket(getWsUrl())
    } catch {
      scheduleReconnect()
      return
    }

    socket.onopen = () => {
      retries = 0
      status.value = 'connected'
    }

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        if (onMessage) onMessage(parsed)
      } catch {
        // Ignore malformed messages
      }
    }

    socket.onclose = () => {
      status.value = 'disconnected'
      if (!closedManually) {
        scheduleReconnect()
      }
    }

    socket.onerror = () => {
      status.value = 'disconnected'
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    retries += 1
    const delay = Math.min(5000, 1000 * retries)
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  function disconnect() {
    closedManually = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (socket) {
      socket.close()
      socket = null
    }
    status.value = 'disconnected'
  }

  return {
    status,
    connect,
    disconnect,
  }
}
