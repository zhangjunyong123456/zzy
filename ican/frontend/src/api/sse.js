import { api, getToken } from './client'

/**
 * fetch 流式读取 SSE（POST + JSON body）。
 * 帧格式：`event: <type>\ndata: <json>\n\n`；无 event 名的 data 帧以 'message' 分发。
 */
export async function streamSSE({ url, body, onEvent, signal }) {
  const token = getToken()
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body),
    signal
  })
  if (!resp.ok) {
    let detail
    try {
      detail = (await resp.json()).detail
    } catch {
      /* ignore */
    }
    throw new (await import('./client')).ApiError(resp.status, detail)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let sep
    while ((sep = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, sep)
      buf = buf.slice(sep + 2)
      let event = 'message'
      const dataLines = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (dataLines.length) {
        try {
          onEvent(event, JSON.parse(dataLines.join('\n')))
        } catch {
          /* 非 JSON data 忽略 */
        }
      }
    }
  }
}

export { api }
