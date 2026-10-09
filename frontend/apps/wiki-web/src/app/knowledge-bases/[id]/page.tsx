'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { BacklinkRead, GraphData, KnowledgeBase, Page } from '@wiki/types';
import { Button } from '@wiki/ui';
import {
  getBacklinks,
  getKbGraph,
  getKnowledgeBase,
  getPageGraph,
  listKnowledgeBaseTags,
  movePage,
} from '@/lib/api';
import { getErrorMessage } from '@/hooks/useKnowledgeBases';
import { usePages } from '@/hooks/usePages';
import { buildPageLookup } from '@/lib/wikiLinks';
import { PageTree } from '@/components/pages/PageTree';
import { DeletePageDialog } from '@/components/pages/DeletePageDialog';
import { TagEditor } from '@/components/pages/TagEditor';
import { MovePageDialog } from '@/components/pages/MovePageDialog';
import { MarkdownRenderer } from '@/components/pages/MarkdownRenderer';
import {
  MarkdownEditor,
  type MarkdownEditorValues,
} from '@/components/pages/MarkdownEditor';
import { DocumentUploader } from '@/components/pages/DocumentUploader';
import { GraphViewer } from '@/components/pages/GraphViewer';
import { RelationEditor } from '@/components/pages/RelationEditor';
import { Toast, type ToastKind } from '@/components/pages/Toast';
import { UnsavedChangesDialog } from '@/components/pages/UnsavedChangesDialog';
import { KnowledgeBaseSwitcher } from '@/components/layout/KnowledgeBaseSwitcher';

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

type EditorMode =
  | { kind: 'closed' }
  | { kind: 'create'; parentId: number | null; heading: string }
  | { kind: 'edit'; page: Page; heading: string };

export default function KnowledgeBaseWorkspacePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [kbLoading, setKbLoading] = useState(true);
  const [kbError, setKbError] = useState<string | null>(null);

  const {
    state,
    reload,
    filterByTag,
    fetchPage,
    addPage,
    savePage,
    removePage,
  } = usePages(id);

  const [selected, setSelected] = useState<Page | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);
  const [editor, setEditor] = useState<EditorMode>({ kind: 'closed' });
  const [submitting, setSubmitting] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Page | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [pendingMove, setPendingMove] = useState<Page | null>(null);
  const [moving, setMoving] = useState(false);
  const [moveError, setMoveError] = useState<string | null>(null);

  // 文档导入
  const [uploaderOpen, setUploaderOpen] = useState(false);

  // 反向引用
  const [backlinks, setBacklinks] = useState<BacklinkRead[]>([]);
  const [backlinksLoading, setBacklinksLoading] = useState(false);

  // 视图模式：详情 / 图谱
  const [contentView, setContentView] = useState<'detail' | 'graph'>(
    'detail'
  );
  const [graphMode, setGraphMode] = useState<'page' | 'kb'>('page');
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  // 内部链接解析映射：标题 → 页面 ID（仅在同知识库内唯一的标题）
  const pageLookup = useMemo(() => {
    if (state.kind !== 'ready') return undefined;
    return buildPageLookup(
      state.pages.map((p) => ({ id: p.id, title: p.title }))
    );
  }, [state]);

  // 标签
  const [kbTags, setKbTags] = useState<string[]>([]);
  const [activeTag, setActiveTag] = useState<string | null>(null);

  // 未保存修改相关
  const [dirty, setDirty] = useState(false);
  const [unsavedOpen, setUnsavedOpen] = useState(false);
  const pendingActionRef = useRef<(() => void) | null>(null);

  // 保存成功 / 失败提示
  const [toast, setToast] = useState<{
    kind: ToastKind;
    message: string;
  } | null>(null);

  const loadKb = useCallback(async () => {
    setKbLoading(true);
    setKbError(null);
    try {
      const res = await getKnowledgeBase(id);
      setKb(res.data);
    } catch (err) {
      setKb(null);
      setKbError(getErrorMessage(err));
    } finally {
      setKbLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!Number.isNaN(id)) {
      void loadKb();
    }
  }, [loadKb, id]);

  // 加载该知识库下出现过的所有标签（用于建议与筛选）
  useEffect(() => {
    listKnowledgeBaseTags(id)
      .then((res) => setKbTags(res.data ?? []))
      .catch(() => setKbTags([]));
  }, [id]);

  // 有未保存修改时，阻止浏览器离开/刷新
  useEffect(() => {
    if (!dirty) return undefined;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  /** 在存在未保存修改时，先弹确认框再执行 action；否则直接执行 */
  const runActionGuarded = useCallback(
    (action: () => void) => {
      if (dirty) {
        pendingActionRef.current = action;
        setUnsavedOpen(true);
      } else {
        action();
      }
    },
    [dirty]
  );

  const traverseTo = useCallback(
    async (page: Page) => {
      pendingActionRef.current = null;
      setDirty(false);
      setEditor({ kind: 'closed' });
      setContentLoading(true);
      setContentError(null);
      setBacklinks([]);
      setBacklinksLoading(true);
      try {
        const detail = await fetchPage(page.id);
        setSelected(detail);
        // 同时加载反向引用
        getBacklinks(page.id)
          .then((res) => setBacklinks(res.data ?? []))
          .catch(() => setBacklinks([]))
          .finally(() => setBacklinksLoading(false));
      } catch (err) {
        setSelected(null);
        setContentError(getErrorMessage(err));
        setBacklinksLoading(false);
      } finally {
        setContentLoading(false);
      }
    },
    [fetchPage]
  );

  const handleSelect = useCallback(
    (page: Page) => {
      runActionGuarded(() => traverseTo(page));
    },
    [runActionGuarded, traverseTo]
  );

  const closeEditorGuarded = useCallback(() => {
    runActionGuarded(() => {
      pendingActionRef.current = null;
      setDirty(false);
      setEditor({ kind: 'closed' });
    });
  }, [runActionGuarded]);

  const handleCreateTop = () => {
    setContentError(null);
    setEditor({ kind: 'create', parentId: null, heading: '新建顶层页面' });
    setDirty(false);
  };

  const handleCreateChild = (parent: Page) => {
    setContentError(null);
    setEditor({
      kind: 'create',
      parentId: parent.id,
      heading: `在「${parent.title}」下新建子页面`,
    });
    setDirty(false);
  };

  const handleEdit = (page: Page) => {
    setContentError(null);
    setEditor({ kind: 'edit', page, heading: '编辑页面' });
    setDirty(false);
  };

  const handleEditorSubmit = async (values: MarkdownEditorValues) => {
    setSubmitting(true);
    try {
      if (editor.kind === 'edit') {
        await savePage(editor.page.id, values);
        const refreshed = await fetchPage(editor.page.id);
        setSelected(refreshed);
        setToast({ kind: 'success', message: '保存成功' });
      } else {
        const parentId = editor.kind === 'create' ? editor.parentId : null;
        const createdPage = await addPage({ ...values, parent_id: parentId });
        setSelected(createdPage);
        setToast({ kind: 'success', message: '页面创建成功' });
      }
      pendingActionRef.current = null;
      setDirty(false);
      setEditor({ kind: 'closed' });
    } catch (err) {
      setToast({ kind: 'error', message: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await removePage(pendingDelete.id);
      if (selected && selected.id === pendingDelete.id) {
        setSelected(null);
      }
      setPendingDelete(null);
      setToast({ kind: 'success', message: '删除成功' });
    } catch (err) {
      setToast({ kind: 'error', message: getErrorMessage(err) });
    } finally {
      setDeleting(false);
    }
  };

  const handleConfirmDiscard = () => {
    const action = pendingActionRef.current;
    pendingActionRef.current = null;
    setUnsavedOpen(false);
    setDirty(false);
    if (action) {
      action();
    }
  };

  const handleCancelDiscard = () => {
    pendingActionRef.current = null;
    setUnsavedOpen(false);
  };

  /** 标签变化后同步最新页面到选中态，并刷新知识库标签建议 */
  const handleTagChanged = (updated: Page) => {
    setSelected(updated);
    void listKnowledgeBaseTags(id)
      .then((res) => setKbTags(res.data ?? []))
      .catch(() => setKbTags([]));
  };

  /** 内部链接点击：在同知识库内导航到目标页面 */
  const handleInternalLinkClick = useCallback(
    (targetPageId: number) => {
      if (state.kind !== 'ready') return;
      const target = state.pages.find((p) => p.id === targetPageId);
      if (!target) {
        setToast({ kind: 'error', message: '目标页面不存在' });
        return;
      }
      runActionGuarded(() => traverseTo(target));
    },
    [state, runActionGuarded, traverseTo]
  );

  /** 加载图谱数据（传入当前模式和选中页面避免闭包陈旧） */
  const loadGraph = useCallback(
    async (mode: 'page' | 'kb', currentSelected: Page | null) => {
      setGraphLoading(true);
      setGraphError(null);
      try {
        let res;
        if (mode === 'page' && currentSelected) {
          res = await getPageGraph(currentSelected.id);
        } else {
          res = await getKbGraph(id, 100);
        }
        setGraphData(res.data);
      } catch (err) {
        setGraphError(getErrorMessage(err));
        setGraphData(null);
      } finally {
        setGraphLoading(false);
      }
    },
    [id]
  );

  /** 切换到图谱视图（加载由 useEffect 自动触发） */
  const openGraphView = useCallback(() => {
    setContentView('graph');
    if (selected) {
      setGraphMode('page');
    } else {
      setGraphMode('kb');
    }
  }, [selected]);

  // 图谱模式或选中页面变化时加载
  useEffect(() => {
    if (contentView === 'graph') {
      void loadGraph(graphMode, selected);
    }
  }, [contentView, graphMode, selected?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTagFilterChange = (tag: string) => {
    const next = tag === '' ? null : tag;
    setActiveTag(next);
    setSelected(null);
    setContentError(null);
    void filterByTag(next);
  };

  const handleConfirmMove = async (targetParentId: number | null) => {
    if (!pendingMove) return;
    setMoving(true);
    setMoveError(null);
    try {
      const updated = await movePage(pendingMove.id, targetParentId);
      await reload();
      if (selected && selected.id === pendingMove.id && updated.data) {
        setSelected(updated.data);
      }
      setPendingMove(null);
      setToast({ kind: 'success', message: '移动成功' });
    } catch (err) {
      setMoveError(getErrorMessage(err));
    } finally {
      setMoving(false);
    }
  };

  if (kbLoading) {
    return (
      <div className="flex justify-center py-16 text-gray-500">
        <span className="mr-2 inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        加载中…
      </div>
    );
  }

  if (kbError || !kb) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-gray-600">{kbError}</p>
        <Button variant="secondary" onClick={() => void loadKb()}>
          重试
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <Link
              href="/knowledge-bases"
              className="inline-flex shrink-0 items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors"
              title="返回知识库列表"
            >
              ← 列表
            </Link>
            <KnowledgeBaseSwitcher currentKbId={kb.id} />
          </div>
          <h1 className="mt-1 text-2xl font-bold text-gray-900 truncate">{kb.name}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {kb.description || '（暂无描述）'} · 创建于{' '}
            {formatDate(kb.created_at)}
          </p>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-6 lg:flex-row">
        {/* 左侧：页面树 */}
        <aside className="flex max-h-[calc(100vh-8rem)] flex-col w-full shrink-0 rounded-lg border border-gray-200 bg-white lg:sticky lg:top-20 lg:w-72">
          <div className="flex shrink-0 items-center justify-between border-b border-gray-100 px-4 py-3">
            <span className="text-sm font-semibold text-gray-900">页面</span>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                onClick={() => setUploaderOpen(true)}
                className="px-2 py-1 text-xs"
              >
                导入
              </Button>
              <Button
                variant="ghost"
                onClick={handleCreateTop}
                className="px-2 py-1"
              >
                + 新建
              </Button>
            </div>
          </div>

          {kbTags.length > 0 && (
            <div className="shrink-0 border-b border-gray-100 px-3 py-2">
              <select
                value={activeTag ?? ''}
                onChange={(e) => handleTagFilterChange(e.target.value)}
                className="w-full rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-700 outline-none focus:border-blue-400"
                aria-label="按标签筛选"
              >
                <option value="">全部标签</option>
                {kbTags.map((t) => (
                  <option key={t} value={t}>
                    #{t}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-2">
            {state.kind === 'loading' ? (
              <div className="flex justify-center py-12 text-gray-400">
                <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                加载中…
              </div>
            ) : state.kind === 'error' ? (
              <div className="flex flex-col items-center gap-3 py-12 text-center">
                <p className="px-4 text-sm text-red-600">{state.message}</p>
                <Button variant="secondary" onClick={() => void reload()}>
                  重试
                </Button>
              </div>
            ) : (
              <PageTree
                pages={state.pages}
                selectedId={selected?.id ?? null}
                onReload={() => void reload()}
                onSelect={handleSelect}
                onCreateChild={(p) => {
                  runActionGuarded(() => handleCreateChild(p));
                }}
                onDelete={(p) => {
                  runActionGuarded(() => {
                    setPendingDelete(p);
                  });
                }}
              />
            )}
          </div>
        </aside>

        {/* 右侧：内容区 */}
        <main className="min-h-[480px] flex-1 rounded-lg border border-gray-200 bg-white p-6">
          {contentView === 'graph' ? (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold text-gray-900">
                    知识图谱
                  </h3>
                  <div className="flex overflow-hidden rounded-md border border-gray-200 text-xs">
                    <button
                      onClick={() => setGraphMode('page')}
                      disabled={!selected}
                      className={`px-3 py-1 transition-colors ${
                        graphMode === 'page'
                          ? 'bg-blue-600 text-white'
                          : !selected
                          ? 'cursor-not-allowed bg-gray-50 text-gray-300'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      页面关联
                    </button>
                    <button
                      onClick={() => setGraphMode('kb')}
                      className={`px-3 py-1 transition-colors ${
                        graphMode === 'kb'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      知识库全貌
                    </button>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  onClick={() => setContentView('detail')}
                >
                  ← 返回详情
                </Button>
              </div>
              <GraphViewer
                graphData={graphData}
                loading={graphLoading}
                error={graphError}
                height={520}
                emptyMessage={
                  graphMode === 'page'
                    ? '当前页面暂无关联关系'
                    : '知识库暂无页面关系数据'
                }
                totalCount={
                  graphMode === 'kb' && state.kind === 'ready'
                    ? state.pages.length
                    : undefined
                }
                onNavigate={(nodeId) => {
                  if (state.kind !== 'ready') return;
                  const target = state.pages.find(
                    (p) => p.id === nodeId
                  );
                  if (target) {
                    setContentView('detail');
                    traverseTo(target);
                  }
                }}
                onRetry={() => void loadGraph(graphMode, selected)}
              />
            </div>
          ) : editor.kind === 'closed' &&
          !selected &&
          state.kind === 'ready' &&
          state.pages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 py-24 text-center">
              <p className="text-gray-500">该知识库还没有页面</p>
              <div className="flex gap-2">
                <Button onClick={handleCreateTop}>创建第一个页面</Button>
                <Button variant="ghost" onClick={() => { setContentView('graph'); setGraphMode('kb'); void loadGraph('kb', selected); }}>
                  查看图谱
                </Button>
              </div>
            </div>
          ) : editor.kind !== 'closed' ? (
            <MarkdownEditor
              key={
                editor.kind === 'edit'
                  ? `edit-${editor.page.id}`
                  : `create-${editor.parentId ?? 'top'}`
              }
              heading={editor.heading}
              initialTitle={editor.kind === 'edit' ? editor.page.title : ''}
              initialContent={editor.kind === 'edit' ? editor.page.content : ''}
              initialStatus={
                editor.kind === 'edit' ? editor.page.status : 'draft'
              }
              onSubmit={handleEditorSubmit}
              onCancel={closeEditorGuarded}
              submitting={submitting}
              saveError={toast?.kind === 'error' ? toast.message : null}
              onDirtyChange={setDirty}
            />
          ) : contentLoading ? (
            <div className="flex h-full items-center justify-center py-24">
              <span className="mr-2 inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
              <span className="text-gray-500">加载页面…</span>
            </div>
          ) : contentError ? (
            <div className="flex flex-col items-center gap-4 py-24 text-center">
              <p className="text-sm text-red-600">{contentError}</p>
              <Button variant="secondary" onClick={() => void reload()}>
                重新加载
              </Button>
            </div>
          ) : selected ? (
            <div>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="truncate text-2xl font-bold text-gray-900">
                      {selected.title}
                    </h2>
                    <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500">
                      查看
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">
                    更新于 {formatDate(selected.updated_at)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-1.5">
                  <Button
                    variant="secondary"
                    onClick={() => handleEdit(selected)}
                    className="text-sm"
                  >
                    编辑
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => handleCreateChild(selected)}
                    className="text-sm"
                  >
                    + 子页面
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setPendingMove(selected)}
                    className="text-sm"
                  >
                    移动
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => openGraphView()}
                    className="text-sm"
                  >
                    图谱
                  </Button>
                </div>
              </div>

              <div className="mt-3">
                <TagEditor
                  page={selected}
                  suggestions={kbTags}
                  onTagsChanged={handleTagChanged}
                  onError={(msg) => setToast({ kind: 'error', message: msg })}
                  onSuccess={(msg) => setToast({ kind: 'success', message: msg })}
                />
              </div>

              <div className="mt-6 border-t border-gray-100 pt-6">
                <MarkdownRenderer
                  content={selected.content}
                  pageLookup={pageLookup}
                  onInternalLinkClick={handleInternalLinkClick}
                />
              </div>

              {/* 反向引用 */}
              <div className="mt-6 border-t border-gray-100 pt-6">
                <h3 className="mb-3 text-sm font-semibold text-gray-700">
                  被以下页面引用
                </h3>
                {backlinksLoading ? (
                  <div className="flex items-center gap-2 py-4 text-sm text-gray-400">
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                    加载中…
                  </div>
                ) : backlinks.length === 0 ? (
                  <p className="text-sm text-gray-400">
                    暂无其他页面引用当前页面
                  </p>
                ) : (
                  <ul className="space-y-1">
                    {backlinks.map((bl) => (
                      <li key={bl.id}>
                        <button
                          onClick={() => handleInternalLinkClick(bl.id)}
                          className="text-sm text-blue-600 hover:text-blue-800 hover:underline text-left"
                        >
                          {bl.title}
                        </button>
                        <span className="ml-2 text-xs text-gray-400">
                          {bl.source === 'BACKLINK' ? '（内容引用）' : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 页面关系 */}
              <div className="mt-6 border-t border-gray-100 pt-6">
                <h3 className="mb-3 text-sm font-semibold text-gray-700">
                  页面关系
                </h3>
                <RelationEditor
                  pageId={selected.id}
                  kbId={selected.knowledge_base_id}
                  onRelationClick={(targetId) =>
                    handleInternalLinkClick(targetId)
                  }
                  onError={(msg) =>
                    setToast({ kind: 'error', message: msg })
                  }
                  onSuccess={(msg) =>
                    setToast({ kind: 'success', message: msg })
                  }
                />
              </div>
            </div>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-4 py-24 text-center">
              <p className="text-gray-500">
                从左侧选择一个页面，或新建一个页面开始编辑。
              </p>
              <div className="flex gap-2">
                <Button onClick={handleCreateTop}>新建顶层页面</Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setContentView('graph');
                    setGraphMode('kb');
                    void loadGraph('kb', selected);
                  }}
                >
                  查看图谱
                </Button>
              </div>
            </div>
          )}
        </main>
      </div>

      {pendingDelete && (
        <DeletePageDialog
          title={pendingDelete.title}
          hasChildren={
            state.kind === 'ready' &&
            state.pages.some((p) => p.parent_id === pendingDelete.id)
          }
          deleting={deleting}
          errorMessage={toast?.kind === 'error' ? toast.message : null}
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}

      {unsavedOpen && (
        <UnsavedChangesDialog
          onConfirm={handleConfirmDiscard}
          onCancel={handleCancelDiscard}
        />
      )}

      {pendingMove && (
        <MovePageDialog
          page={pendingMove}
          allPages={state.kind === 'ready' ? state.pages : []}
          moving={moving}
          errorMessage={moveError}
          onConfirm={(targetParentId) => {
            void handleConfirmMove(targetParentId);
          }}
          onCancel={() => {
            setPendingMove(null);
            setMoveError(null);
          }}
        />
      )}

      {uploaderOpen && (
        <DocumentUploader
          kbId={id}
          kbName={kb.name}
          onClose={() => setUploaderOpen(false)}
          onSuccess={async (pageId) => {
            setUploaderOpen(false);
            await reload();
            try {
              const fresh = await fetchPage(pageId);
              setSelected(fresh);
            } catch {
              setToast({ kind: 'error', message: '页面已导入但加载失败，请手动刷新' });
            }
          }}
        />
      )}

      {toast && (
        <Toast
          key={`${toast.kind}-${toast.message}-${Date.now()}`}
          kind={toast.kind}
          message={toast.message}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  );
}
