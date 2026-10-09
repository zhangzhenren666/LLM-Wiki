'use client';

import { useState } from 'react';
import type { Page } from '@wiki/types';
import { addPageTags, removePageTags } from '@/lib/api';
import { getErrorMessage } from '@/hooks/useKnowledgeBases';

interface TagEditorProps {
  page: Page;
  /** 有可用的知识库标签建议列表（用于输入补全提示，可空） */
  suggestions?: string[];
  onTagsChanged: (page: Page) => void;
  onError: (message: string) => void;
  onSuccess?: (message: string) => void;
}

/**
 * 页面标签管理（查看态）：展示现有标签，支持添加（回车/逗号）与移除。
 * 每次变更后调用 onTagsChanged 将后端返回的最新页面同步到上层。
 */
export function TagEditor({
  page,
  suggestions = [],
  onTagsChanged,
  onError,
  onSuccess,
}: TagEditorProps) {
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);

  const tags = page.tags ?? [];

  const submitDraft = async () => {
    const trimmed = draft
      .trim()
      .replace(/[,，]+$/, '')
      .trim();
    if (!trimmed) return;
    const names = trimmed
      .split(/[,，]/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (names.length === 0) return;
    setBusy(true);
    try {
      const res = await addPageTags(page.id, names);
      onTagsChanged(res.data as unknown as Page);
      setDraft('');
      onSuccess?.(`已添加标签：${names.join(', ')}`);
    } catch (err) {
      onError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (name: string) => {
    setBusy(true);
    try {
      const res = await removePageTags(page.id, [name]);
      onTagsChanged(res.data as unknown as Page);
      onSuccess?.(`已移除标签 #${name}`);
    } catch (err) {
      onError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      void submitDraft();
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tags.length === 0 && (
        <span className="text-xs text-gray-400">暂无标签</span>
      )}
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700"
        >
          #{tag}
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleRemove(tag)}
            className="text-blue-400 hover:text-red-600 disabled:opacity-50"
            aria-label={`移除标签 ${tag}`}
            title={`移除标签 ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        value={draft}
        disabled={busy}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="+ 添加标签，用逗号分隔"
        className="min-w-32 rounded-full border border-gray-200 px-2.5 py-0.5 text-xs outline-none focus:border-blue-400 disabled:opacity-50"
        list="page-tag-suggestions"
      />
      <datalist id="page-tag-suggestions">
        {suggestions.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </div>
  );
}
