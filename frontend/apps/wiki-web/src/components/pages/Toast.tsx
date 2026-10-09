'use client';

import { useEffect } from 'react';

export type ToastKind = 'success' | 'error';

interface ToastProps {
  kind: ToastKind;
  message: string;
  onDismiss: () => void;
  /** 自动消失毫秒数，默认 3000 */
  duration?: number;
}

/**
 * 轻量顶部提示条
 * 用于保存成功 / 失败等即时反馈，可自动消失。
 */
export function Toast({
  kind,
  message,
  onDismiss,
  duration = 3000,
}: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
  }, [onDismiss, duration]);

  const isSuccess = kind === 'success';

  return (
    <div className="pointer-events-none fixed left-1/2 top-4 z-[60] -translate-x-1/2">
      <div
        className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm text-white shadow-lg ${
          isSuccess ? 'bg-green-600' : 'bg-red-600'
        }`}
      >
        <span>{isSuccess ? '✓' : '✕'}</span>
        <span>{message}</span>
      </div>
    </div>
  );
}
