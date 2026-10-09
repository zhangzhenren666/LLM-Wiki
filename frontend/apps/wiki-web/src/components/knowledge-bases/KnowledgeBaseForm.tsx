'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { Button } from '@wiki/ui';
import type { KnowledgeBaseInput } from '@wiki/types';

interface KnowledgeBaseFormProps {
  /** 编辑时的初始值；为空则表示创建 */
  initialValue?: KnowledgeBaseInput;
  /** 提交回调 */
  onSubmit: (input: KnowledgeBaseInput) => Promise<void> | void;
  /** 取消回调 */
  onCancel?: () => void;
  /** 自定义提交按钮文案 */
  submitLabel?: string;
  /** 是否处于提交中 */
  submitting?: boolean;
  /** 提交失败时的错误信息（来自后端） */
  errorMessage?: string | null;
}

/**
 * 知识库创建/编辑共享表单
 * 含客户端基础校验（名称必填）。
 */
export function KnowledgeBaseForm({
  initialValue,
  onSubmit,
  onCancel,
  submitLabel = '保存',
  submitting = false,
  errorMessage,
}: KnowledgeBaseFormProps) {
  const [name, setName] = useState(initialValue?.name ?? '');
  const [description, setDescription] = useState(
    initialValue?.description ?? ''
  );
  const [errors, setErrors] = useState<{ name?: string }>({});

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const nextErrors: { name?: string } = {};
    const trimmedName = name.trim();
    if (!trimmedName) {
      nextErrors.name = '知识库名称不能为空';
    }
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const input: KnowledgeBaseInput = {
      name: trimmedName,
      description: description.trim() || null,
    };
    void onSubmit(input);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div>
        <label
          htmlFor={`kb-name-${initialValue ? 'edit' : 'create'}`}
          className="mb-1 block text-sm font-medium text-gray-700"
        >
          名称 <span className="text-red-500">*</span>
        </label>
        <input
          id={`kb-name-${initialValue ? 'edit' : 'create'}`}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如：研发知识库"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name}</p>
        )}
      </div>

      <div>
        <label
          htmlFor={`kb-desc-${initialValue ? 'edit' : 'create'}`}
          className="mb-1 block text-sm font-medium text-gray-700"
        >
          描述 <span className="text-gray-400">（选填）</span>
        </label>
        <textarea
          id={`kb-desc-${initialValue ? 'edit' : 'create'}`}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          placeholder="知识库用途说明"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
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
