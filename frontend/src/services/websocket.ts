import { io, Socket } from 'socket.io-client'
import type { WSEvent } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL || ''

type EventHandler = (event: WSEvent) => void

class WebSocketService {
  private socket: Socket | null = null
  private handlers: Map<string, Set<EventHandler>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10

  connect() {
    if (this.socket?.connected) return

    this.socket = io(WS_URL, {
      path: '/ws',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
    })

    this.socket.on('connect', () => {
      console.log('[WS] Connected')
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason)
    })

    this.socket.on('event', (event: WSEvent) => {
      this.dispatch(event.type, event)
      this.dispatch('*', event)
    })

    this.socket.on('connect_error', () => {
      this.reconnectAttempts++
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.warn('[WS] Max reconnect attempts reached')
      }
    })
  }

  disconnect() {
    this.socket?.disconnect()
    this.socket = null
  }

  on(eventType: string, handler: EventHandler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set())
    }
    this.handlers.get(eventType)!.add(handler)
    return () => this.off(eventType, handler)
  }

  off(eventType: string, handler: EventHandler) {
    this.handlers.get(eventType)?.delete(handler)
  }

  private dispatch(eventType: string, event: WSEvent) {
    this.handlers.get(eventType)?.forEach((handler) => handler(event))
  }

  get connected() {
    return this.socket?.connected ?? false
  }
}

export const wsService = new WebSocketService()
