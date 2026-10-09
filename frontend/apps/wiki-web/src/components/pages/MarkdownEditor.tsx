'use client';

import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Button } from '@wiki/ui';
import type { PageStatus } from '@wiki/types';
import { MarkdownRenderer } from '@/components/pages/MarkdownRenderer';

const STATUS_OPTIONS: { value: PageStatus; label: string }[] = [
  { value: 'draft', label: '草稿' },
  { value: 'published', label: '已发布' },
  { value: 'archived', label: '已归档' },
];

export interface MarkdownEditorValues {
  title: string;
  content: string;
  status: PageStatus;
}

interface MarkdownEditorProps {
  /** 编辑器上下文标题 */
  heading: string;
  initialTitle: string;
  initialContent: string;
  initialStatus?: PageStatus;
  /** 提交（保存）回调，抛出错误则由父级展示失败提示 */
  onSubmit: (values: MarkdownEditorValues) => Promise<void>;
  onCancel: () => void;
  /** 是否处于保存中 */
  submitting?: boolean;
  /** 保存失败的错误信息 */
  saveError?: string | null;
  /** 内容发生变化（未保存）时回调 */
  onDirtyChange?: (dirty: boolean) => void;
}

/**
 * Markdown 编辑组件
 *
 * - 标题编辑
 * - 左右分栏：左侧编辑区、右侧实时预览区（安全渲染）
 * - 保存 / 取消
 * - 脏状态跟踪（用于「未保存内容提醒」）
 * 独立封装，供页面创建/编辑与后续扩展复用。
 */
export function MarkdownEditor({
  heading,
  initialTitle,
  initialContent,
  initialStatus = 'draft',
  onSubmit,
  onCancel,
  submitting = false,
  saveError,
  onDirtyChange,
}: MarkdownEditorProps) {
  const [title, setTitle] = useState(initialTitle);
  const [content, setContent] = useState(initialContent);
  const [status, setStatus] = useState<PageStatus>(initialStatus);
  const [error, setError] = useState<{ title?: string }>({});

  const dirty = useMemo(
    () =>
      title !== initialTitle ||
      content !== initialContent ||
      status !== initialStatus,
    [title, content, status, initialTitle, initialContent, initialStatus]
  );

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const nextErrors: { title?: string } = {};
    const trimmed = title.trim();
    if (!trimmed) {
      nextErrors.title = '页面标题不能为空';
    }
    setError(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }
    void onSubmit({ title: trimmed, content, status });
  };

  return (
    <form onSubmit={handleSubmit} className="flex h-full flex-col" noValidate>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-gray-900">{heading}</h3>
          <span className="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
            编辑
          </span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as PageStatus)}
            aria-label="页面状态"
            className="rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={submitting}
          >
            取消
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? '保存中…' : '保存'}
          </Button>
        </div>
      </div>

      {dirty && (
        <div className="mb-3 rounded-md bg-amber-50 px-3 py-1.5 text-xs text-amber-700">
          有未保存的内容
        </div>
      )}
      {saveError && (
        <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {saveError}
        </div>
      )}

      <div>
        <label
          htmlFor="md-title"
          className="mb-1 block text-sm font-medium text-gray-700"
        >
          标题 <span className="text-red-500">*</span>
        </label>
        <input
          id="md-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="页面标题"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {error.title && (
          <p className="mt-1 text-sm text-red-600">{error.title}</p>
        )}
      </div>

      {/* 左右分栏：编辑 / 预览（小屏纵向堆叠） */}
      <div className="mt-4 grid min-h-0 flex-1 grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex min-h-0 flex-col">
          <div className="mb-1 text-xs font-medium text-gray-400">编辑</div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="在此输入 Markdown 内容…"
            spellCheck={false}
            className="min-h-0 flex-1 resize-none rounded-md border border-gray-300 p-3 font-mono text-sm leading-6 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex min-h-0 flex-col">
          <div className="mb-1 text-xs font-medium text-gray-400">预览</div>
          <div className="min-h-0 flex-1 overflow-auto rounded-md border border-gray-200 bg-gray-50 p-3">
            <MarkdownRenderer content={content} />
          </div>
        </div>
      </div>
    </form>
  );
}
