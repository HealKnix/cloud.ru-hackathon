export async function* decodeTextStream(stream?: ReadableStream<Uint8Array>) {
  if (!stream) return;
  const reader = stream.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) {
        yield decoder.decode(value, { stream: true });
      }
    }
  } finally {
    reader.releaseLock();
  }
}
