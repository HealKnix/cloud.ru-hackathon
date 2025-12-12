export type AguiStreamEvent =
  | { type: 'text'; delta: string }
  | { type: 'state'; state: Record<string, unknown> }
  | { type: 'done' }
  | { type: 'unknown'; raw: unknown };

const TEXT_KEYS = ['delta', 'text', 'content', 'message', 'output_text'];

export async function* parseAguiStream(
  stream?: ReadableStream<Uint8Array> | null,
): AsyncGenerator<AguiStreamEvent, void, unknown> {
  if (!stream) return;

  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: true });

      let newlineIndex = buffer.indexOf('\n');
      while (newlineIndex !== -1) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        const normalized = normalizeAguiLine(line);
        if (normalized) yield normalized;
        newlineIndex = buffer.indexOf('\n');
      }
    }

    const rest = buffer.trim();
    const normalized = normalizeAguiLine(rest);
    if (normalized) yield normalized;
  } finally {
    reader.releaseLock();
  }
}

function normalizeAguiLine(line: string): AguiStreamEvent | null {
  if (!line) return null;

  const raw = line.startsWith('data:') ? line.slice(5).trim() : line.trim();
  if (!raw) return null;
  if (raw === '[DONE]') return { type: 'done' };

  let parsed: unknown = raw;
  try {
    parsed = JSON.parse(raw);
  } catch {
    /* keep raw value */
  }

  return normalizeAguiEvent(parsed);
}

function normalizeAguiEvent(parsed: unknown): AguiStreamEvent {
  if (typeof parsed === 'string') {
    if (parsed.trim() === '[DONE]') return { type: 'done' };
    return { type: 'text', delta: parsed };
  }

  if (parsed && typeof parsed === 'object') {
    const obj = parsed as Record<string, unknown>;
    const state = extractState(obj);
    if (state) return { type: 'state', state };

    const text = extractText(obj);
    if (text) return { type: 'text', delta: text };

    return { type: 'unknown', raw: parsed };
  }

  return { type: 'unknown', raw: parsed };
}

function extractState(
  obj: Record<string, unknown>,
): Record<string, unknown> | null {
  const candidates = [
    obj.state,
    obj.data && typeof obj.data === 'object'
      ? (obj.data as Record<string, unknown>).state
      : null,
    obj.payload && typeof obj.payload === 'object'
      ? (obj.payload as Record<string, unknown>).state
      : null,
    obj.shared_state,
    obj.data && typeof obj.data === 'object'
      ? (obj.data as Record<string, unknown>).shared_state
      : null,
  ];

  for (const candidate of candidates) {
    if (
      candidate &&
      typeof candidate === 'object' &&
      !Array.isArray(candidate)
    ) {
      return candidate as Record<string, unknown>;
    }
  }

  return null;
}

function extractText(obj: Record<string, unknown>): string | null {
  const queue: unknown[] = [obj];

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || typeof current !== 'object') continue;

    const record = current as Record<string, unknown>;
    for (const key of TEXT_KEYS) {
      const value = record[key];
      if (typeof value === 'string' && value.trim()) {
        return value;
      }
    }

    for (const value of Object.values(record)) {
      if (value && typeof value === 'object') {
        queue.push(value);
      }
    }
  }

  return null;
}
