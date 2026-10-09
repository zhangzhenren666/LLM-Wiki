'use client';

import { useCallback, useEffect, useState } from 'react';
import { Button } from '@wiki/ui';
import type {
  DocumentTaskListItem,
  DocumentTaskRead,
  TaskStepRead,
} from '@wiki/types';
import {
  getDocumentTask,
  listDocumentTasks,
  retryDocumentTask,
} from '@/lib/api';
import { ApiError } from '@/lib/http';

type FilterStatus =
  | ''
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'needs_attention';

const STATUS_LABEL: Record<FilterStatus, string> = {
  '': '全部',
  pending: '待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  needs_attention: '需关注',
};

const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  needs_attention: 'bg-orange-100 text-orange-800',
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getErrMsg(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return '操作失败';
}

export default function DocumentsPage() {
  const [tasks, setTasks] = useState<DocumentTaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('');

  const [detailTask, setDetailTask] = useState<DocumentTaskRead | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [retryingId, setRetryingId] = useState<number | null>(null);

  const load = useCallback(async (status?: FilterStatus) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {};
      if (status) params.status = status;
      params.limit = 50;
      const res = await listDocumentTasks(params);
      setTasks(res.data ?? []);
    } catch (err) {
      setError(getErrMsg(err));
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(statusFilter ? statusFilter : undefined);
  }, [load, statusFilter]);

  const handleRetry = async (task: DocumentTaskListItem) => {
    setRetryingId(task.id);
    try {
      await retryDocumentTask(task.id);
      await load(statusFilter || undefined);
    } catch (err) {
      setError(getErrMsg(err));
    } finally {
      setRetryingId(null);
    }
  };

  const handleViewDetail = async (id: number) => {
    setDetailError(null);
    try {
      const res = await getDocumentTask(id);
      setDetailTask(res.data);
    } catch (err) {
      setDetailError(getErrMsg(err));
      setDetailTask(null);
    }
  };

  const canRetry = (t: DocumentTaskListItem) =>
    t.status === 'failed' || t.status === 'needs_attention';

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900">文档处理任务</h1>
      <p className="mt-1 text-sm text-gray-500">
        查看文档上传后的解析与 AI 处理状态。
      </p>

      {/* 状态过滤 */}
      <div className="mt-5 flex flex-wrap gap-2">
        {(
          [
            '',
            'pending',
            'processing',
            'completed',
            'failed',
            'needs_attention',
          ] as FilterStatus[]
        ).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 text-sm font-medium transition ${
              statusFilter === s
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      {/* 操作错误 */}
      {error && (
        <div className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
          <button
            type="button"
            onClick={() => setError(null)}
            className="ml-2 underline"
          >
            关闭
          </button>
        </div>
      )}

      {/* 列表 */}
      <div className="mt-4">
        {loading ? (
          <div className="flex justify-center py-16 text-gray-500">
            加载中…
          </div>
        ) : tasks.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-16 text-center text-gray-500">
            <p>暂无匹配的任务</p>
            <p className="mt-1 text-sm">
              上传文档后将自动创建处理任务。
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {tasks.map((task) => (
              <li key={task.id} className="px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-gray-900">
                        文档 #{task.document_id}
                      </span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_COLOR[task.status] ?? 'bg-gray-100 text-gray-500'}`}
                      >
                        {STATUS_LABEL[task.status] ?? task.status}
                      </span>
                      {task.progress > 0 && task.progress < 100 && (
                        <span className="text-xs text-gray-400">
                          {task.progress}%
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-gray-400">
                      知识库 #{task.knowledge_base_id} · 已尝试 {task.attempts}/{task.max_attempts} 次
                      {task.finished_at
                        ? ` · 结束于 ${formatDate(task.finished_at)}`
                        : task.started_at
                          ? ` · 开始于 ${formatDate(task.started_at)}`
                          : ''}
                    </p>
                    {task.error_message && (
                      <p className="mt-0.5 truncate text-xs text-red-500">
                        {task.error_message}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      variant="ghost"
                      onClick={() => void handleViewDetail(task.id)}
                    >
                      详情
                    </Button>
                    {canRetry(task) && (
                      <Button
                        variant="secondary"
                        disabled={retryingId === task.id}
                        onClick={() => void handleRetry(task)}
                      >
                        {retryingId === task.id ? '重试中…' : '重试'}
                      </Button>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 详情面板 */}
      {(detailTask || detailError) && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              任务详情 #{detailTask?.id ?? '-'}
            </h2>
            <Button
              variant="ghost"
              onClick={() => {
                setDetailTask(null);
                setDetailError(null);
              }}
            >
              关闭
            </Button>
          </div>
          {detailError && (
            <p className="mt-2 text-sm text-red-600">{detailError}</p>
          )}
          {detailTask && (
            <div className="mt-3 space-y-3">
              <div className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <span className="text-gray-500">状态：</span>
                  <span className="font-medium">
                    {STATUS_LABEL[detailTask.status as FilterStatus] ?? detailTask.status}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">进度：</span>
                  <span className="font-medium">{detailTask.progress}%</span>
                </div>
                <div>
                  <span className="text-gray-500">尝试次数：</span>
                  <span className="font-medium">
                    {detailTask.attempts}/{detailTask.max_attempts}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">文档 ID：</span>
                  <span className="font-medium">{detailTask.document_id}</span>
                </div>
                {detailTask.error_message && (
                  <div className="sm:col-span-2">
                    <span className="text-gray-500">错误：</span>
                    <span className="text-red-600">
                      {detailTask.error_message}
                    </span>
                  </div>
                )}
              </div>

              {/* 处理步骤 */}
              {detailTask.steps.length > 0 && (
                <div>
                  <h3 className="mt-4 text-sm font-semibold text-gray-700">
                    处理记录
                  </h3>
                  <div className="mt-2 space-y-2">
                    {detailTask.steps.map((step: TaskStepRead) => (
                      <div
                        key={step.id}
                        className={`rounded-md border px-3 py-2 text-sm ${
                          step.status === 'completed'
                            ? 'border-green-200 bg-green-50'
                            : step.status === 'failed'
                              ? 'border-red-200 bg-red-50'
                              : 'border-yellow-200 bg-yellow-50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{step.step_name}</span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs ${
                              step.status === 'completed'
                                ? 'bg-green-200 text-green-800'
                                : step.status === 'failed'
                                  ? 'bg-red-200 text-red-800'
                                  : 'bg-yellow-200 text-yellow-800'
                            }`}
                          >
                            {step.status}
                          </span>
                          {step.page_id && (
                            <span className="text-xs text-gray-400">
                              → 页面 #{step.page_id}
                            </span>
                          )}
                        </div>
                        {step.error_message && (
                          <p className="mt-1 text-red-600">
                            {step.error_message}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}