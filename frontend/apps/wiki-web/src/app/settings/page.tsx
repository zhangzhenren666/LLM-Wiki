'use client';

import { useState } from 'react';
import { Button } from '@wiki/ui';
import type { ModelConfig, ModelConfigInput } from '@wiki/types';
import { useModelConfigs, getErrorMessage } from '@/hooks/useModelConfigs';
import { ModelConfigForm } from '@/components/model-configs/ModelConfigForm';

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface TestState {
  configId: number;
  success: boolean;
  message: string;
}

type PanelState =
  { kind: 'none' } | { kind: 'create' } | { kind: 'edit'; config: ModelConfig };

export default function SettingsPage() {
  const { items, loading, error, load, create, update, remove, test } =
    useModelConfigs();

  const [panel, setPanel] = useState<PanelState>({ kind: 'none' });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testState, setTestState] = useState<TestState | null>(null);

  const handleSubmit = async (input: ModelConfigInput) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (panel.kind === 'edit') {
        await update(panel.config.id, input);
      } else {
        await create(input);
      }
      setPanel({ kind: 'none' });
      setTestState(null);
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleTest = async (config: ModelConfig) => {
    setTestingId(config.id);
    try {
      const result = await test(config.id);
      setTestState({ configId: config.id, ...result });
    } catch (err) {
      setTestState({
        configId: config.id,
        success: false,
        message: getErrorMessage(err),
      });
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (config: ModelConfig) => {
    if (!window.confirm(`确定要删除模型配置「${config.name}」吗？`)) {
      return;
    }
    setSubmitError(null);
    try {
      await remove(config.id);
      if (testState?.configId === config.id) {
        setTestState(null);
      }
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">模型配置</h1>
          <p className="mt-1 text-sm text-gray-500">
            配置 OpenAI Chat Completions
            兼容接口的大模型，用于后续文档分析等能力。
          </p>
        </div>
        <Button
          onClick={() => {
            setPanel({ kind: 'create' });
            setSubmitError(null);
          }}
        >
          + 新建模型配置
        </Button>
      </div>

      {/* 创建/编辑面板 */}
      {panel.kind !== 'none' && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            {panel.kind === 'edit' ? '编辑模型配置' : '新建模型配置'}
          </h2>
          <ModelConfigForm
            initialValue={panel.kind === 'edit' ? panel.config : undefined}
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
            <p className="text-lg">还没有模型配置</p>
            <p className="mt-1 text-sm">
              点击右上角「新建模型配置」添加一个可用的模型。
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {items.map((config) => (
              <li key={config.id} className="px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-gray-900">
                        {config.name}
                      </span>
                      {config.is_default && (
                        <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                          默认
                        </span>
                      )}
                      {!config.is_active && (
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                          停用
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 truncate text-sm text-gray-500">
                      {config.model_name} · {config.base_url}
                    </p>
                    <p className="mt-0.5 text-xs text-gray-400">
                      超时 {config.timeout_seconds}s ·{' '}
                      {config.api_key_configured
                        ? 'API Key 已配置'
                        : '未配置 API Key'}{' '}
                      · 更新于 {formatDate(config.updated_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      disabled={testingId === config.id}
                      onClick={() => void handleTest(config)}
                    >
                      {testingId === config.id ? '测试中…' : '测试连接'}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setPanel({ kind: 'edit', config });
                        setSubmitError(null);
                      }}
                    >
                      编辑
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => void handleDelete(config)}
                      className="text-red-600 hover:bg-red-50"
                    >
                      删除
                    </Button>
                  </div>
                </div>

                {/* 测试结果 */}
                {testState?.configId === config.id && (
                  <div
                    className={`mt-3 rounded-md px-3 py-2 text-sm ${
                      testState.success
                        ? 'bg-green-50 text-green-700'
                        : 'bg-red-50 text-red-700'
                    }`}
                  >
                    <span className="font-medium">
                      {testState.success ? '✔ ' : '✘ '}
                    </span>
                    {testState.message}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
