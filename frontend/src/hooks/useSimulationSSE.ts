/**
 * Hook for live Server-Sent Events connection to a simulation.
 *
 * Connects to the Vercel Edge Function SSE endpoint at
 * /api/simulations/:id/stream, which polls the DB for new MovementRecord rows
 * and forwards them as SSE events.
 *
 * Replaces useSimulationWebSocket.ts — same interface, different transport.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { getAccessToken } from '../api/client'

export interface StepUpdatePayload {
  step?: number
  sim_curr_time?: string
  persona_movements?: Record<string, unknown>
  // Legacy field names kept for backwards compatibility with existing consumers
  agents?: Record<string, unknown>
}

interface UseSimulationSSEOptions {
  simId: string
  onStepUpdate: (payload: StepUpdatePayload) => void
  onForbidden: () => void
  onAuthError: () => void
}

export type SseStatus = 'connecting' | 'connected' | 'disconnected'

export function useSimulationSSE({
  simId,
  onStepUpdate,
  onForbidden,
  onAuthError,
}: UseSimulationSSEOptions) {
  const [sseStatus, setSseStatus] = useState<SseStatus>('disconnected')
  const esRef = useRef<EventSource | null>(null)
  const backoffRef = useRef(1000)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  const connect = useCallback(() => {
    if (unmountedRef.current) return

    const token = getAccessToken()
    if (!token) {
      onAuthError()
      return
    }

    setSseStatus('connecting')

    // The SSE edge function is at /api/simulations/:id/stream.
    // We pass the JWT as a query parameter because EventSource does not support
    // custom headers. The edge function forwards it to the Django API.
    const url = `/api/simulations/${encodeURIComponent(simId)}/stream?token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('connected', () => {
      if (unmountedRef.current) return
      setSseStatus('connected')
      backoffRef.current = 1000
    })

    es.onmessage = (event) => {
      if (unmountedRef.current) return
      try {
        const data = JSON.parse(event.data as string) as StepUpdatePayload
        onStepUpdate(data)
      } catch {
        // ignore malformed messages
      }
    }

    es.addEventListener('timeout', () => {
      // Edge function stream expired — reconnect immediately.
      es.close()
      if (!unmountedRef.current) connect()
    })

    es.onerror = () => {
      if (unmountedRef.current) return
      es.close()
      setSseStatus('disconnected')
      const delay = Math.min(backoffRef.current, 30000)
      backoffRef.current = Math.min(backoffRef.current * 2, 30000)
      reconnectTimerRef.current = setTimeout(connect, delay)
    }
  }, [simId, onStepUpdate, onForbidden, onAuthError])

  useEffect(() => {
    unmountedRef.current = false
    const timer = setTimeout(connect, 0)
    return () => {
      unmountedRef.current = true
      clearTimeout(timer)
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      esRef.current?.close()
    }
  }, [connect])

  return { wsStatus: sseStatus }
}
