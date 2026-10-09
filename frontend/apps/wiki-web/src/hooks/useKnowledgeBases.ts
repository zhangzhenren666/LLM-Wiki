'use client';

import { useCallback, useEffect, useState } from 'react';
import type { KnowledgeBase, KnowledgeBaseInput } from '@wiki/types';
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
} from '@/lib/api';
import { ApiError } from '@/lib/http';

/** 从未知错误中提取可读信息 */
export function getErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return '操作失败，请稍后重试';
}

interface UseKnowledgeBasesResult {
  items: KnowledgeBase[];
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
  create: (input: KnowledgeBaseInput) => Promise<void>;
  update: (id: number, input: KnowledgeBaseInput) => Promise<void>;
  remove: (id: number) => Promise<void>;
}

/**
 * 知识库数据管理 Hook：封装列表加载与增删改操作。
 */
export function useKnowledgeBases(): UseKnowledgeBasesResult {
  const [items, setItems] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listKnowledgeBases();
      setItems(res.data ?? []);
    } catch (err) {
      setItems([]);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (input: KnowledgeBaseInput) => {
      await createKnowledgeBase(input);
      await load();
    },
    [load]
  );

  const update = useCallback(
    async (id: number, input: KnowledgeBaseInput) => {
      await updateKnowledgeBase(id, input);
      await load();
    },
    [load]
  );

  const remove = useCallback(
    async (id: number) => {
      await deleteKnowledgeBase(id);
      await load();
    },
    [load]
  );

  return { items, loading, error, load, create, update, remove };
}
