'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Page, PageRelationItem, RelationType } from '@wiki/types';
import { Button } from '@wiki/ui';
import {
  createRelation,
  deleteRelation,
  getPageRelations,
  listPages,
} from '@/lib/api';
import { getErrorMessage } from '@/hooks/useKnowledgeBases';

interface RelationEditorProps {
  pageId: number;
  kbId: number;
  /** 点击关联页面时回调 */
  onRelationClick?: (targetPageId: number) => void;
  /** 操作错误回调 */
  onError?: (message: string) => void;
  /** 操作成功回调 */
  onSuccess?: (message: string) => void;
}

const RELATION_TYPE_LABELS: Record<RelationType, string> = {
  related: '相关知识',
  references: '参考资料',
  depends_on: '依赖关系',
  parent: '上级知识',
};

const RELATION_TYPES: RelationType[] = [
  'related',
  'references',
  'depends_on',
  'parent',
];

type PanelMode = { kind: 'view' } | { kind: 'create' };

/**
 * 页面关系管理组件：
 * - 查看当前页面的入向/出向关系
 * - 创建新关系（搜索目标页面 + 选择关系类型）
 * - 删除关系（需确认）
 */
export function RelationEditor({
  pageId,
  kbId,
  onRelationClick,
  onError,
  onSuccess,
}: RelationEditorProps) {
  const [relations, setRelations] = useState<{
    outgoing: PageRelationItem[];
    incoming: PageRelationItem[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [panel, setPanel] = useState<PanelMode>({ kind: 'view' });

  // 创建面板状态
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<Page[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [selectedType, setSelectedType] = useState<RelationType>('related');
  const [creating, setCreating] = useState(false);

  // 删除状态
  const [deletePending, setDeletePending] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadRelations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPageRelations(pageId);
      setRelations(res.data ?? { outgoing: [], incoming: [] });
    } catch (err) {
      setError(getErrorMessage(err));
      setRelations(null);
    } finally {
      setLoading(false);
    }
  }, [pageId]);

  useEffect(() => {
    void loadRelations();
  }, [loadRelations]);

  // 搜索目标页面（防抖 300ms）
  useEffect(() => {
    if (panel.kind !== 'create') return;
    const keyword = searchKeyword.trim();
    if (!keyword) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(() => {
      setSearching(true);
      listPages({ knowledge_base_id: kbId, keyword })
        .then((res) =>
          setSearchResults(
            (res.data ?? []).filter((p) => p.id !== pageId)
          )
        )
        .catch(() => setSearchResults([]))
        .finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchKeyword, kbId, pageId, panel.kind]);

  const handleCreate = async () => {
    if (selectedTargetId === null) return;
    setCreating(true);
    try {
      await createRelation({
        source_page_id: pageId,
        target_page_id: selectedTargetId,
        relation_type: selectedType,
      });
      setPanel({ kind: 'view' });
      setSearchKeyword('');
      setSearchResults([]);
      setSelectedTargetId(null);
      setSelectedType('related');
      onSuccess?.('关系创建成功');
      await loadRelations();
    } catch (err) {
      onError?.(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (deletePending === null) return;
    setDeleting(true);
    try {
      await deleteRelation(deletePending);
      setDeletePending(null);
      onSuccess?.('关系已删除');
      await loadRelations();
    } catch (err) {
      onError?.(getErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  const openCreatePanel = () => {
    setPanel({ kind: 'create' });
    setSearchKeyword('');
    setSearchResults([]);
    setSelectedTargetId(null);
    setSelectedType('related');
  };

  const closeCreatePanel = () => {
    setPanel({ kind: 'view' });
    setSearchKeyword('');
    setSearchResults([]);
    setSelectedTargetId(null);
  };

  const renderRelationItem = (item: PageRelationItem, isOutgoing: boolean) => {
    const label = RELATION_TYPE_LABELS[item.relation_type as RelationType];
    const relatedPage = item.related_page;
    return (
      <li
        key={item.id}
        className="flex items-center justify-between gap-2 py-1"
      >
        <div className="min-w-0 flex-1">
          {relatedPage ? (
            <button
              onClick={() => onRelationClick?.(relatedPage.id)}
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline text-left truncate max-w-full"
              title={relatedPage.title}
            >
              {relatedPage.title}
            </button>
          ) : (
            <span className="text-sm text-gray-400">（页面已删除）</span>
          )}
          <span className="ml-2 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500">
            {isOutgoing ? '出向' : '入向'}
          </span>
          {label && (
            <span className="ml-1 inline-block rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
              {label}
            </span>
          )}
        </div>
        {isOutgoing && (
          <Button
            variant="ghost"
            onClick={() => setDeletePending(item.id)}
            className="shrink-0 px-1.5 py-0.5 text-xs text-red-500 hover:bg-red-50"
          >
            删除
          </Button>
        )}
      </li>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-gray-400">
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        加载关系中…
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-2">
        <p className="text-sm text-red-500">{error}</p>
        <Button variant="secondary" onClick={() => void loadRelations()} className="mt-2">
          重试
        </Button>
      </div>
    );
  }

  const hasRelations =
    (relations?.outgoing.length ?? 0) > 0 ||
    (relations?.incoming.length ?? 0) > 0;

  return (
    <div>
      {panel.kind === 'create' && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50/30 p-4">
          <h4 className="mb-3 text-sm font-semibold text-gray-800">
            创建页面关系
          </h4>

          {/* 搜索目标页面 */}
          <div className="mb-3">
            <label className="mb-1 block text-xs text-gray-500">
              搜索目标页面
            </label>
            <input
              type="text"
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              placeholder="输入关键词搜索页面…"
              className="w-full rounded-md border border-gray-200 px-3 py-1.5 text-sm outline-none focus:border-blue-400"
              autoFocus
            />
            {searching && (
              <div className="mt-1 flex items-center gap-1 text-xs text-gray-400">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                搜索中…
              </div>
            )}
            {!searching && searchResults.length > 0 && (
              <ul className="mt-2 max-h-40 overflow-y-auto rounded border border-gray-100 bg-white">
                {searchResults.map((p) => (
                  <li key={p.id}>
                    <button
                      onClick={() => setSelectedTargetId(p.id)}
                      className={`w-full px-3 py-1.5 text-left text-sm hover:bg-blue-50 ${
                        selectedTargetId === p.id
                          ? 'bg-blue-100 text-blue-700'
                          : 'text-gray-700'
                      }`}
                    >
                      {p.title}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {!searching &&
              searchKeyword.trim() &&
              searchResults.length === 0 && (
                <p className="mt-1 text-xs text-gray-400">未找到匹配页面</p>
              )}
          </div>

          {/* 选择关系类型 */}
          <div className="mb-4">
            <label className="mb-1 block text-xs text-gray-500">
              关系类型
            </label>
            <select
              value={selectedType}
              onChange={(e) =>
                setSelectedType(e.target.value as RelationType)
              }
              className="w-full rounded-md border border-gray-200 px-3 py-1.5 text-sm outline-none focus:border-blue-400"
            >
              {RELATION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {RELATION_TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={() => void handleCreate()}
              disabled={selectedTargetId === null || creating}
            >
              {creating ? '创建中…' : '创建关系'}
            </Button>
            <Button variant="ghost" onClick={closeCreatePanel} disabled={creating}>
              取消
            </Button>
          </div>
        </div>
      )}

      {!hasRelations ? (
        <p className="text-sm text-gray-400">暂无手动关系</p>
      ) : (
        <div className="space-y-4">
          {relations && relations.outgoing.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-medium text-gray-500">
                出向关系
              </h4>
              <ul className="divide-y divide-gray-50">
                {relations.outgoing.map((r) => renderRelationItem(r, true))}
              </ul>
            </div>
          )}
          {relations && relations.incoming.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-medium text-gray-500">
                入向关系
              </h4>
              <ul className="divide-y divide-gray-50">
                {relations.incoming.map((r) => renderRelationItem(r, false))}
              </ul>
            </div>
          )}
        </div>
      )}

      {panel.kind === 'view' && (
        <div className="mt-3">
          <Button variant="ghost" onClick={openCreatePanel} className="text-sm">
            + 创建关系
          </Button>
        </div>
      )}

      {/* 删除确认弹窗 */}
      {deletePending !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-lg">
            <h4 className="mb-2 text-sm font-semibold text-gray-900">
              确认删除
            </h4>
            <p className="mb-4 text-sm text-gray-600">
              确定要删除这条关系吗？此操作不可撤销。
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setDeletePending(null)}
                disabled={deleting}
              >
                取消
              </Button>
              <Button
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="bg-red-600 hover:bg-red-700"
              >
                {deleting ? '删除中…' : '确认删除'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}