'use client';

import { useCallback, useRef, useState } from 'react';
import { Button } from '@wiki/ui';
import { getPage, uploadDocument } from '@/lib/api';
import { getErrorMessage } from '@/hooks/useKnowledgeBases';

const ALLOWED_EXTENSIONS = ['.md', '.txt', '.docx'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface DocumentUploaderProps {
  kbId: number;
  kbName?: string;
  onClose: () => void;
  onSuccess?: (pageId: number) => void | Promise<void>;
}

/**
 * 文档导入上传面板。
 *
 * 支持 .md / .txt / .docx，校验文件类型和大小，
 * 上传后展示结果并提供"跳转到导入页面"入口。
 */
export function DocumentUploader({
  kbId,
  kbName,
  onClose,
  onSuccess,
}: DocumentUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    pageId: number;
    pageTitle: string;
  } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((f: File | null) => {
    if (!f) {
      setValidation(null);
      setFile(null);
      return;
    }
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setValidation(`不支持的文件类型: ${ext}，仅支持 ${ALLOWED_EXTENSIONS.join(', ')}`);
      setFile(null);
      return;
    }
    if (f.size > MAX_FILE_SIZE) {
      setValidation(
        `文件过大（${(f.size / (1024 * 1024)).toFixed(1)} MB），最大 ${MAX_FILE_SIZE / (1024 * 1024)} MB`
      );
      setFile(null);
      return;
    }
    setValidation(null);
    setFile(f);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await uploadDocument(kbId, file);
      if (res.data && res.data.page_id) {
        // 获取实际页面标题
        let pageTitle: string;
        try {
          const pageRes = await getPage(res.data.page_id);
          pageTitle = pageRes.data?.title ?? file.name.replace(/\.[^.]+$/, '');
        } catch {
          pageTitle = file.name.replace(/\.[^.]+$/, '');
        }
        setResult({ pageId: res.data.page_id, pageTitle });
      } else {
        throw new Error('导入成功但未生成页面');
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setValidation(null);
    setError(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            导入文档
          </h3>
          <Button variant="ghost" onClick={onClose}>
            ✕
          </Button>
        </div>

        {kbName && (
          <p className="mb-4 text-sm text-gray-500">
            导入到「{kbName}」
          </p>
        )}

        {!result ? (
          <>
            {/* 文件选择 */}
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">
                选择文件
              </label>
              <input
                ref={inputRef}
                type="file"
                accept=".md,.txt,.docx"
                onChange={(e) => validate(e.target.files?.[0] ?? null)}
                disabled={uploading}
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1 file:text-xs file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
              />
              {validation && (
                <p className="mt-1 text-xs text-red-500">{validation}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">
                支持 .md / .txt / .docx，最大 10 MB
              </p>
            </div>

            {/* 错误信息 */}
            {error && (
              <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={onClose} disabled={uploading}>
                取消
              </Button>
              <Button
                onClick={() => void handleUpload()}
                disabled={!file || uploading}
              >
                {uploading ? (
                  <>
                    <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    导入中…
                  </>
                ) : (
                  '开始导入'
                )}
              </Button>
            </div>
          </>
        ) : (
          /* 成功结果 */
          <div className="space-y-4">
            <div className="rounded-md bg-green-50 p-4 text-center">
              <p className="text-sm font-medium text-green-800">
                导入成功
              </p>
              <p className="mt-1 text-xs text-green-600">
                已生成 Wiki 页面「{result.pageTitle}」
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={reset}>
                导入更多
              </Button>
              <Button
                onClick={() => {
                  void onSuccess?.(result.pageId);
                  onClose();
                }}
              >
                查看页面
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}