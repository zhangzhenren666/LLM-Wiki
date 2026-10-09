'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { Button } from '@wiki/ui';
import type { ModelConfig, ModelConfigInput } from '@wiki/types';

interface ModelConfigFormProps {
  /** 编辑时的初始配置；为空则表示创建 */
  initialValue?: ModelConfig;
  /** 提交回调 */
  onSubmit: (input: ModelConfigInput) => Promise<void> | void;
  /** 取消回调 */
  onCancel?: () => void;
  /** 自定义提交按钮文案 */
  submitLabel?: string;
  /** 是否处于提交中 */
  submitting?: boolean;
  /** 提交失败时的错误信息 */
  errorMessage?: string | null;
}

interface FormErrors {
  name?: string;
  base_url?: string;
  model_name?: string;
}

const inputCls =
  'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500';
const labelCls = 'mb-1 block text-sm font-medium text-gray-700';

/**
 * 模型配置创建/编辑共享表单。
 * 密钥输入在编辑态下留空表示"保留原值"，不强制重新填写。
 */
export function ModelConfigForm({
  initialValue,
  onSubmit,
  onCancel,
  submitLabel = '保存',
  submitting = false,
  errorMessage,
}: ModelConfigFormProps) {
  const isEdit = Boolean(initialValue);
  const [name, setName] = useState(initialValue?.name ?? '');
  const [baseUrl, setBaseUrl] = useState(initialValue?.base_url ?? '');
  const [modelName, setModelName] = useState(initialValue?.model_name ?? '');
  const [timeoutSeconds, setTimeoutSeconds] = useState(
    initialValue ? String(initialValue.timeout_seconds) : ''
  );
  const [apiKey, setApiKey] = useState('');
  const [isActive, setIsActive] = useState(initialValue?.is_active ?? true);
  const [isDefault, setIsDefault] = useState(initialValue?.is_default ?? false);
  const [errors, setErrors] = useState<FormErrors>({});

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const nextErrors: FormErrors = {};
    if (!name.trim()) nextErrors.name = '配置名称不能为空';
    if (!baseUrl.trim() || !/^https?:\/\//.test(baseUrl.trim())) {
      nextErrors.base_url = '请输入合法的 http(s) API Base URL';
    }
    if (!modelName.trim()) nextErrors.model_name = '模型名称不能为空';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const input: ModelConfigInput = {
      name: name.trim(),
      base_url: baseUrl.trim().replace(/\/+$/, ''),
      model_name: modelName.trim(),
      // 编辑时留空表示不修改密钥；创建时留空表示不配置
      api_key: apiKey.trim() || undefined,
      is_active: isActive,
      is_default: isDefault,
    };
    if (timeoutSeconds.trim()) {
      input.timeout_seconds = Number(timeoutSeconds);
    }
    void onSubmit(input);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div>
        <label
          htmlFor={`mc-name-${isEdit ? 'edit' : 'create'}`}
          className={labelCls}
        >
          配置名称 <span className="text-red-500">*</span>
        </label>
        <input
          id={`mc-name-${isEdit ? 'edit' : 'create'}`}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如：生产 GPT 模型"
          className={inputCls}
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name}</p>
        )}
      </div>

      <div>
        <label
          htmlFor={`mc-url-${isEdit ? 'edit' : 'create'}`}
          className={labelCls}
        >
          API Base URL <span className="text-red-500">*</span>
        </label>
        <input
          id={`mc-url-${isEdit ? 'edit' : 'create'}`}
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api.example.com/v1"
          className={inputCls}
        />
        {errors.base_url && (
          <p className="mt-1 text-sm text-red-600">{errors.base_url}</p>
        )}
      </div>

      <div>
        <label
          htmlFor={`mc-model-${isEdit ? 'edit' : 'create'}`}
          className={labelCls}
        >
          模型名称 <span className="text-red-500">*</span>
        </label>
        <input
          id={`mc-model-${isEdit ? 'edit' : 'create'}`}
          type="text"
          value={modelName}
          onChange={(e) => setModelName(e.target.value)}
          placeholder="例如：gpt-4o-mini"
          className={inputCls}
        />
        {errors.model_name && (
          <p className="mt-1 text-sm text-red-600">{errors.model_name}</p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor={`mc-timeout-${isEdit ? 'edit' : 'create'}`}
            className={labelCls}
          >
            超时时间（秒）{' '}
            <span className="text-gray-400">（选填，默认 60）</span>
          </label>
          <input
            id={`mc-timeout-${isEdit ? 'edit' : 'create'}`}
            type="number"
            min={1}
            max={600}
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(e.target.value)}
            placeholder="60"
            className={inputCls}
          />
        </div>
        <div>
          <label
            htmlFor={`mc-key-${isEdit ? 'edit' : 'create'}`}
            className={labelCls}
          >
            API Key{' '}
            {isEdit && initialValue?.api_key_configured ? (
              <span className="text-gray-400">（已配置，留空保持不变）</span>
            ) : (
              <span className="text-gray-400">（选填）</span>
            )}
          </label>
          <input
            id={`mc-key-${isEdit ? 'edit' : 'create'}`}
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={
              isEdit && initialValue?.api_key_configured ? '••••••••' : 'sk-...'
            }
            autoComplete="off"
            className={inputCls}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-6">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          启用
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          设为默认
        </label>
      </div>

      {errorMessage && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            取消
          </Button>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? '提交中…' : submitLabel}
        </Button>
      </div>
    </form>
  );
}
