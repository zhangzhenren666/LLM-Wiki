'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { KnowledgeBase } from '@wiki/types';
import { listKnowledgeBases } from '@/lib/api';

interface KnowledgeBaseSwitcherProps {
  currentKbId: number;
  className?: string;
}

/**
 * 知识库快速切换下拉组件。
 * 在工作区顶部显示当前知识库名称，点击下拉快速切换到其他知识库。
 */
export function KnowledgeBaseSwitcher({
  currentKbId,
  className = '',
}: KnowledgeBaseSwitcherProps) {
  const router = useRouter();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    listKnowledgeBases()
      .then((res) => setKbs(res.data ?? []))
      .catch(() => setKbs([]))
      .finally(() => setLoading(false));
  }, []);

  const currentKb = kbs.find((k) => k.id === currentKbId);
  const otherKbs = kbs.filter((k) => k.id !== currentKbId);

  const handleSwitch = (kbId: number) => {
    setOpen(false);
    router.push(`/knowledge-bases/${kbId}`);
  };

  // 点击外部关闭下拉
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-kb-switcher]')) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className={`relative ${className}`} data-kb-switcher>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={loading}
        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 transition-colors disabled:opacity-50"
        title="切换知识库"
      >
        <span className="max-w-[140px] truncate font-medium text-gray-900">
          {currentKb?.name ?? '知识库'}
        </span>
        <svg
          className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && otherKbs.length > 0 && (
        <div className="absolute left-0 top-full mt-1 w-52 rounded-lg border border-gray-200 bg-white shadow-lg z-50 py-1 max-h-52 overflow-y-auto">
          <div className="px-3 py-1.5 text-[10px] font-medium text-gray-400 uppercase tracking-wide">
            切换知识库
          </div>
          {otherKbs.map((kb) => (
            <button
              key={kb.id}
              type="button"
              onClick={() => handleSwitch(kb.id)}
              className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-colors"
            >
              <span className="block truncate font-medium">{kb.name}</span>
              {kb.description && (
                <span className="block truncate text-xs text-gray-400 mt-0.5">
                  {kb.description}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {open && otherKbs.length === 0 && (
        <div className="absolute left-0 top-full mt-1 w-52 rounded-lg border border-gray-200 bg-white shadow-lg z-50 py-3 px-3 text-center text-xs text-gray-400">
          {loading ? '加载中…' : '暂无其他知识库'}
        </div>
      )}
    </div>
  );
}