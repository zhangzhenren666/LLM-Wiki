'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Button } from '@wiki/ui';
import type { KnowledgeBase, KnowledgeBaseInput } from '@wiki/types';
import { useKnowledgeBases, getErrorMessage } from '@/hooks/useKnowledgeBases';
import { KnowledgeBaseForm } from '@/components/knowledge-bases/KnowledgeBaseForm';
import { DeleteConfirmDialog } from '@/components/knowledge-bases/DeleteConfirmDialog';

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

type PanelState =
  { kind: 'none' } | { kind: 'create' } | { kind: 'edit'; kb: KnowledgeBase };

export default function KnowledgeBasesPage() {
  const { items, loading, error, load, create, update, remove } =
    useKnowledgeBases();

  const [panel, setPanel] = useState<PanelState>({ kind: 'none' });
  const [pendingDelete, setPendingDelete] = useState<KnowledgeBase | null>(
    null
  );
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleSubmit = async (input: KnowledgeBaseInput) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (panel.kind === 'edit') {
        await update(panel.kb.id, input);
      } else {
        await create(input);
      }
      setPanel({ kind: 'none' });
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setSubmitError(null);
    try {
      await remove(pendingDelete.id);
      setPendingDelete(null);
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">知识库管理</h1>
          <p className="mt-1 text-sm text-gray-500">
            管理你的知识库，点击进入对应工作区。
          </p>
        </div>
        <Button
          onClick={() => {
            setPanel({ kind: 'create' });
            setSubmitError(null);
          }}
        >
          + 新建知识库
        </Button>
      </div>

      {/* 创建/编辑面板 */}
      {panel.kind !== 'none' && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            {panel.kind === 'edit' ? '编辑知识库' : '新建知识库'}
          </h2>
          <KnowledgeBaseForm
            initialValue={
              panel.kind === 'edit'
                ? { name: panel.kb.name, description: panel.kb.description }
                : undefined
            }
            onSubmit={handleSubmit}
            onCancel={() => setPanel({ kind: 'none' })}
            submitLabel={panel.kind === 'edit' ? '保存修改' : '创建'}
            submitting={submitting}
            errorMessage={submitError}
          />
        </div>
      )}

      {/* 列表区域 */}
      <div className="mt-6">
        {loading ? (
          <div className="flex justify-center py-16 text-gray-500">
            <span className="animate-spin mr-2 inline-block h-5 w-5 border-2 border-gray-300 border-t-blue-600 rounded-full" />
            加载中…
          </div>
        ) : error ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <p className="text-gray-600">{error}</p>
            <Button variant="secondary" onClick={() => void load()}>
              重试
            </Button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-16 text-center text-gray-500">
            <p className="text-lg">还没有知识库</p>
            <p className="mt-1 text-sm">点击右上角「新建知识库」开始创建。</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {items.map((kb) => (
              <li
                key={kb.id}
                className="group flex items-center justify-between px-4 py-4 transition hover:bg-gray-50"
              >
                <Link
                  href={`/knowledge-bases/${kb.id}`}
                  className="min-w-0 flex-1"
                >
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium text-gray-900">
                      {kb.name}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-sm text-gray-500">
                    {kb.description || '（暂无描述）'}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    创建于 {formatDate(kb.created_at)}
                  </p>
                </Link>
                <div className="ml-4 flex shrink-0 items-center gap-2">
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setPanel({ kind: 'edit', kb });
                      setSubmitError(null);
                    }}
                  >
                    编辑
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setPendingDelete(kb);
                      setSubmitError(null);
                    }}
                    className="text-red-600 hover:bg-red-50"
                  >
                    删除
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 删除确认弹窗 */}
      {pendingDelete && (
        <DeleteConfirmDialog
          name={pendingDelete.name}
          deleting={deleting}
          errorMessage={submitError}
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}
