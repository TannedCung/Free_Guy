/**
 * Vercel Edge Function — SSE stream for simulation movement updates.
 *
 * Polls the Django REST API for new MovementRecord rows and forwards them
 * as Server-Sent Events to subscribed frontend clients.
 *
 * Runtime: Vercel Edge (V8, no Node.js built-ins).
 * Path: /api/simulations/:id/stream
 *
 * Authentication: Reads the Authorization header from the incoming request
 * and forwards it to the Django REST API, so only authenticated users can
 * subscribe to a simulation stream.
 */

export const runtime = 'edge'

const POLL_INTERVAL_MS = 2000
// Maximum stream duration to prevent runaway edge functions (10 minutes).
const MAX_DURATION_MS = 10 * 60 * 1000

/** Fetch the latest MovementRecord for the simulation from the Django REST API. */
async function fetchLatestMovement(
  apiBase: string,
  simId: string,
  afterStep: number,
  authHeader: string | null,
): Promise<{ step: number; sim_curr_time: string | null; persona_movements: unknown } | null> {
  const url = `${apiBase}/api/v1/simulations/${encodeURIComponent(simId)}/movements/latest/?after_step=${afterStep}`
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (authHeader) headers['Authorization'] = authHeader

  try {
    const res = await fetch(url, { headers })
    if (!res.ok) return null
    const data = (await res.json()) as {
      step?: number
      sim_curr_time?: string | null
      persona_movements?: unknown
    }
    if (data.step == null) return null
    return {
      step: data.step,
      sim_curr_time: data.sim_curr_time ?? null,
      persona_movements: data.persona_movements,
    }
  } catch {
    return null
  }
}

export async function GET(req: Request, { params }: { params: { id: string } }): Promise<Response> {
  const { id: simId } = params

  // Forward the Authorization header so the Django API can authenticate the request.
  const authHeader = req.headers.get('Authorization')

  // Determine Django API base URL from environment (set in Vercel project settings).
  // Defaults to same origin (works when frontend + API share the same Vercel project).
  const apiBase = (process.env['DJANGO_API_BASE_URL'] ?? '').replace(/\/$/, '')

  const encoder = new TextEncoder()
  let lastStep = -1
  const startedAt = Date.now()

  const stream = new ReadableStream({
    async start(controller) {
      // Send an initial "connected" event so the client knows the stream is live.
      controller.enqueue(encoder.encode('event: connected\ndata: {}\n\n'))

      while (true) {
        // Stop the stream after MAX_DURATION_MS to free edge resources.
        if (Date.now() - startedAt > MAX_DURATION_MS) {
          controller.enqueue(encoder.encode('event: timeout\ndata: {}\n\n'))
          controller.close()
          return
        }

        const record = await fetchLatestMovement(apiBase, simId, lastStep, authHeader)
        if (record !== null) {
          lastStep = record.step
          const payload = JSON.stringify(record)
          controller.enqueue(encoder.encode(`data: ${payload}\n\n`))
        }

        // Poll every POLL_INTERVAL_MS milliseconds.
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'X-Accel-Buffering': 'no',
    },
  })
}
