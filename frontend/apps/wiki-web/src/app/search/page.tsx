'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@wiki/ui';
import type { SearchResult } from '@wiki/types';
import { searchPages } from '@/lib/api';
import { getErrorMessage } from '@/hooks/useKnowledgeBases';

const MATCH_LABELS: Record<string, { label: string; color: string }> = {
  title: { label: '标题', color: 'bg-blue-100 text-blue-700' },
  tag: { label: '标签', color: 'bg-purple-100 text-purple-700' },
  content: { label: '内容', color: 'bg-green-100 text-green-700' },
};

/** 将 snippet 中的 **text** 渲染为高亮 span */
function renderSnippet(snippet: string | null): React.ReactNode {
  if (!snippet) return null;
  const parts = snippet.split(/(\*\*[^*]+\*\*)/g);
  return (
    <span>
      {parts.map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? (
          <mark key={i} className="bg-yellow-200 px-0.5 text-gray-900">
            {part.slice(2, -2)}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
}

type PageState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | {
      kind: 'ready';
      items: SearchResult[];
      total: number;
      page: number;
      page_size: number;
    };

function SearchContent() {
  const router = useRouter();
  const sp = useSearchParams();
  const initialQuery = sp.get('q') ?? '';

  const [query, setQuery] = useState(initialQuery);
  const [state, setState] = useState<PageState>({ kind: 'idle' });

  const doSearch = useCallback(
    async (q: string, page = 1) => {
      const trimmed = q.trim();
      if (!trimmed) {
        setState({ kind: 'idle' });
        return;
      }
      setState({ kind: 'loading' });
      try {
        const res = await searchPages({ q: trimmed, page, page_size: 20 });
        if (res.data) {
          setState({
            kind: 'ready',
            items: res.data.items,
            total: res.data.total,
            page: res.data.page,
            page_size: res.data.page_size,
          });
        } else {
          setState({ kind: 'error', message: '搜索结果为空' });
        }
      } catch (err) {
        setState({ kind: 'error', message: getErrorMessage(err) });
      }
    },
    []
  );

  // 首屏若 URL 含 q 参数则自动搜索
  useEffect(() => {
    if (initialQuery.trim()) {
      void doSearch(initialQuery.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q) {
      router.replace(`/search?q=${encodeURIComponent(q)}`, { scroll: false });
      void doSearch(q);
    }
  };

  const totalPages = useMemo(() => {
    if (state.kind !== 'ready') return 0;
    return Math.ceil(state.total / state.page_size);
  }, [state]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6">
        <Link
          href="/knowledge-bases"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
        >
          ← 返回知识库管理
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">搜索页面</h1>
      </div>

      {/* 搜索输入 */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入关键词搜索标题、标签或正文…"
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
            autoFocus
          />
          <Button type="submit" disabled={!query.trim()}>
            搜索
          </Button>
        </div>
      </form>

      {/* 状态展示 */}
      {state.kind === 'idle' && (
        <div className="py-16 text-center text-sm text-gray-400">
          输入关键词开始搜索
        </div>
      )}

      {state.kind === 'loading' && (
        <div className="flex justify-center py-16 text-gray-500">
          <span className="mr-2 inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
          搜索中…
        </div>
      )}

      {state.kind === 'error' && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">
          {state.message}
        </div>
      )}

      {state.kind === 'ready' && (
        <>
          <p className="mb-4 text-sm text-gray-500">
            找到 <strong>{state.total}</strong> 个结果
            {state.total > 0 && (
              <>
                ，第 {state.page}/{totalPages} 页
              </>
            )}
          </p>

          {state.items.length === 0 ? (
            <div className="py-16 text-center text-sm text-gray-400">
              未找到匹配的页面
            </div>
          ) : (
            <ul className="space-y-4">
              {state.items.map((item) => (
                <li
                  key={item.page_id}
                  className="rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-blue-200"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/knowledge-bases/${item.knowledge_base_id}`}
                          className="truncate text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          {item.title}
                        </Link>
                        <span
                          className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                            MATCH_LABELS[item.match_type]?.color ?? 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {MATCH_LABELS[item.match_type]?.label ?? item.match_type}
                        </span>
                      </div>

                      {item.snippet && (
                        <p className="mt-1 text-xs leading-relaxed text-gray-500">
                          {renderSnippet(item.snippet)}
                        </p>
                      )}

                      <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                        {item.knowledge_base_name && (
                          <span>知识库：{item.knowledge_base_name}</span>
                        )}
                        {item.tags.length > 0 && (
                          <span className="flex items-center gap-1">
                            {item.tags.map((t) => (
                              <span
                                key={t}
                                className="rounded bg-gray-100 px-1 py-0.5 text-[10px]"
                              >
                                #{t}
                              </span>
                            ))}
                          </span>
                        )}
                      </div>
                    </div>

                    <Link
                      href={`/knowledge-bases/${item.knowledge_base_id}`}
                      className="shrink-0 text-xs text-gray-400 hover:text-blue-600"
                    >
                      查看 →
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="ghost"
                disabled={state.page <= 1}
                onClick={() => void doSearch(query.trim(), state.page - 1)}
              >
                上一页
              </Button>
              <span className="text-sm text-gray-500">
                {state.page} / {totalPages}
              </span>
              <Button
                variant="ghost"
                disabled={state.page >= totalPages}
                onClick={() => void doSearch(query.trim(), state.page + 1)}
              >
                下一页
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16 text-gray-500">
          <span className="mr-2 inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
          加载中…
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}