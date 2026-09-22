import { streamSSE } from './sse'

export function sendMessage({ sessionId, message, docIds = [], attachmentIds = [], memoryIds = [], category, onEvent, signal }) {
  return streamSSE({
    url: '/api/chat/stream',
    body: { session_id: sessionId, message, doc_ids: docIds, attachment_ids: attachmentIds, memory_ids: memoryIds, category },
    onEvent,
    signal
  })
}
