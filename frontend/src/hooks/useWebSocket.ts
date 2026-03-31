import { useEffect, useRef } from 'react'
import { wsService } from '../services/websocket'
import { useAppStore } from '../stores/app'
import type { WSEvent } from '../types'

export function useWebSocket() {
  const handleWSEvent = useAppStore((s) => s.handleWSEvent)
  const setWsConnected = useAppStore((s) => s.setWsConnected)
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    wsService.connect()
    setWsConnected(true)

    const unsubAll = wsService.on('*', (event: WSEvent) => {
      handleWSEvent(event)
    })

    return () => {
      unsubAll()
      wsService.disconnect()
      setWsConnected(false)
    }
  }, [handleWSEvent, setWsConnected])

  return { connected: wsService.connected }
}
