'use client';

import { useCallback, useEffect, useState } from 'react';
import type {
  ModelConfig,
  ModelConfigInput,
  ModelConfigTestResult,
} from '@wiki/types';
import {
  createModelConfig,
  deleteModelConfig,
  listModelConfigs,
  testModelConfig,
  updateModelConfig,
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

interface UseModelConfigsResult {
  items: ModelConfig[];
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
  create: (input: ModelConfigInput) => Promise<void>;
  update: (id: number, input: Partial<ModelConfigInput>) => Promise<void>;
  remove: (id: number) => Promise<void>;
  test: (id: number) => Promise<ModelConfigTestResult>;
}

/**
 * 模型配置数据管理 Hook：封装列表加载与增删改、测试连接操作。
 */
export function useModelConfigs(): UseModelConfigsResult {
  const [items, setItems] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listModelConfigs();
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
    async (input: ModelConfigInput) => {
      await createModelConfig(input);
      await load();
    },
    [load]
  );

  const update = useCallback(
    async (id: number, input: Partial<ModelConfigInput>) => {
      await updateModelConfig(id, input);
      await load();
    },
    [load]
  );

  const remove = useCallback(
    async (id: number) => {
      await deleteModelConfig(id);
      await load();
    },
    [load]
  );

  const test = useCallback(async (id: number) => {
    const res = await testModelConfig(id);
    return res.data ?? { success: false, message: '未返回测试结果' };
  }, []);

  return { items, loading, error, load, create, update, remove, test };
}
