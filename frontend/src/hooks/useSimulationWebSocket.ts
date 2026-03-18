/**
 * Hook for live WebSocket connection to a simulation.
 * Handles JWT authentication, reconnect with exponential backoff,
 * and close codes 4001 (invalid token) and 4003 (forbidden).
 */

import { useEffect, useRef, useState, useCallback, type MutableRefObject } from 'react'
import { getAccessToken } from '../api/client'

export interface StepUpdatePayload {
  step?: number
  sim_curr_time?: string
  agents?: Record<string, unknown>
}

interface UseSimulationWebSocketOptions {
  simId: string
  onStepUpdate: (payload: StepUpdatePayload) => void
  onForbidden: () => void
  onAuthError: () => void
}

export type WsStatus = 'connecting' | 'connected' | 'disconnected'

const BASE_URL = window.location.origin.replace(/^http/, 'ws')

export function useSimulationWebSocket({
  simId,
  onStepUpdate,
  onForbidden,
  onAuthError,
}: UseSimulationWebSocketOptions) {
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(1000)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)
  // Use a ref to allow the close handler to call connect without dependency cycle
  const connectRef: MutableRefObject<(() => void) | null> = useRef(null)

  const connect = useCallback(() => {
    if (unmountedRef.current) return
    const token = getAccessToken()
    if (!token) {
      onAuthError()
      return
    }
    setWsStatus('connecting')
    const url = `${BASE_URL}/ws/simulations/${encodeURIComponent(simId)}/?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (unmountedRef.current) return
      setWsStatus('connected')
      backoffRef.current = 1000
    }

    ws.onmessage = (event) => {
      if (unmountedRef.current) return
      try {
        const data = JSON.parse(event.data as string) as StepUpdatePayload
        onStepUpdate(data)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = (event) => {
      if (unmountedRef.current) return
      setWsStatus('disconnected')
      if (event.code === 4003) {
        onForbidden()
        return
      }
      if (event.code === 4001) {
        onAuthError()
        return
      }
      // Exponential backoff reconnect
      const delay = Math.min(backoffRef.current, 30000)
      backoffRef.current = Math.min(backoffRef.current * 2, 30000)
      reconnectTimerRef.current = setTimeout(() => connectRef.current?.(), delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [simId, onStepUpdate, onForbidden, onAuthError])

  useEffect(() => {
    connectRef.current = connect
  })

  useEffect(() => {
    unmountedRef.current = false
    // Defer to avoid calling setState synchronously in effect body
    const timer = setTimeout(connect, 0)
    return () => {
      unmountedRef.current = true
      clearTimeout(timer)
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { wsStatus }
}
