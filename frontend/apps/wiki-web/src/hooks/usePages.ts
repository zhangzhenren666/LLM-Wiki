'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Page, PageStatus } from '@wiki/types';
import {
  createPage,
  deletePage,
  getPage,
  listPages,
  updatePage,
} from '@/lib/api';
import { getErrorMessage } from '@/hooks/useKnowledgeBases';

/** 页面列表状态：加载中 / 出错 / 就绪 */
export type PagesState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; pages: Page[] };

interface UsePagesResult {
  state: PagesState;
  reload: () => Promise<void>;
  /** 按标签筛选重载页面列表 */
  filterByTag: (tag: string | null) => Promise<void>;
  /** 获取单个页面详情 */
  fetchPage: (id: number) => Promise<Page>;
  /** 创建页面（可指定父页面） */
  addPage: (input: {
    title: string;
    parent_id?: number | null;
    content?: string;
    status?: PageStatus;
  }) => Promise<Page>;
  /** 更新页面字段 */
  savePage: (
    id: number,
    input: {
      title?: string;
      slug?: string | null;
      parent_id?: number | null;
      content?: string;
      status?: PageStatus;
    }
  ) => Promise<Page>;
  /** 删除页面 */
  removePage: (id: number) => Promise<void>;
}

/**
 * 页面数据管理 Hook：加载某个知识库下的全部页面并缓存，
 * 供页面树与内容区使用。树结构在组件内基于扁平列表构建。
 */
export function usePages(knowledgeBaseId: number): UsePagesResult {
  const [state, setState] = useState<PagesState>({ kind: 'loading' });

  const reload = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      const res = await listPages({ knowledge_base_id: knowledgeBaseId });
      setState({ kind: 'ready', pages: res.data ?? [] });
    } catch (err) {
      setState({ kind: 'error', message: getErrorMessage(err) });
    }
  }, [knowledgeBaseId]);

  const filterByTag = useCallback(
    async (tag: string | null) => {
      setState({ kind: 'loading' });
      try {
        const res = await listPages({
          knowledge_base_id: knowledgeBaseId,
          tag: tag ?? undefined,
        });
        setState({ kind: 'ready', pages: res.data ?? [] });
      } catch (err) {
        setState({ kind: 'error', message: getErrorMessage(err) });
      }
    },
    [knowledgeBaseId]
  );

  useEffect(() => {
    if (!Number.isNaN(knowledgeBaseId)) {
      void reload();
    }
  }, [reload, knowledgeBaseId]);

  const fetchPage = useCallback(async (id: number) => {
    const res = await getPage(id);
    if (!res.data) {
      throw new Error('页面不存在');
    }
    return res.data;
  }, []);

  const addPage = useCallback(
    async (input: {
      title: string;
      parent_id?: number | null;
      content?: string;
      status?: PageStatus;
    }) => {
      const res = await createPage({
        knowledge_base_id: knowledgeBaseId,
        title: input.title,
        parent_id: input.parent_id ?? null,
        content: input.content ?? '',
        status: input.status ?? 'draft',
      });
      await reload();
      if (!res.data) {
        throw new Error('创建页面失败');
      }
      return res.data;
    },
    [knowledgeBaseId, reload]
  );

  const savePage = useCallback(
    async (
      id: number,
      input: {
        title?: string;
        slug?: string | null;
        parent_id?: number | null;
        content?: string;
        status?: PageStatus;
      }
    ) => {
      const res = await updatePage(id, input);
      await reload();
      if (!res.data) {
        throw new Error('更新页面失败');
      }
      return res.data;
    },
    [reload]
  );

  const removePage = useCallback(
    async (id: number) => {
      await deletePage(id);
      await reload();
    },
    [reload]
  );

  return {
    state,
    reload,
    filterByTag,
    fetchPage,
    addPage,
    savePage,
    removePage,
  };
}
