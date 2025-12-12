import { useEffect, useState } from 'react';

export const useClipboard = () => {
  const [copiedHandle, setCopiedHandle] = useState<string | null>(null);

  useEffect(() => {
    if (!copiedHandle) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setCopiedHandle(null);
    }, 2000);

    return () => window.clearTimeout(timeoutId);
  }, [copiedHandle]);

  const handleCopy = async (handle: string) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(handle);
        setCopiedHandle(handle);
        return;
      }

      throw new Error('Clipboard API unavailable');
    } catch (error) {
      console.warn('Failed to copy handle', handle, error);
      setCopiedHandle(null);
    }
  };

  return {
    copiedHandle,
    handleCopy,
  };
};
