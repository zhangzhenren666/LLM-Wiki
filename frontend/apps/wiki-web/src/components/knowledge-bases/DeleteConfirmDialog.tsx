'use client';

import { Button } from '@wiki/ui';

interface DeleteConfirmDialogProps {
  /** 待删除对象名称，用于提示 */
  name: string;
  /** 是否正在删除 */
  deleting?: boolean;
  /** 删除失败的错误信息 */
  errorMessage?: string | null;
  /** 确认删除回调 */
  onConfirm: () => void;
  /** 取消回调 */
  onCancel: () => void;
}

/**
 * 删除二次确认弹窗
 */
export function DeleteConfirmDialog({
  name,
  deleting = false,
  errorMessage,
  onConfirm,
  onCancel,
}: DeleteConfirmDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900">删除知识库</h3>
        <p className="mt-3 text-sm text-gray-600">
          确定要删除知识库
          <span className="font-medium text-gray-900">「{name}」</span>
          吗？其下的页面、标签和关系也会一并删除，此操作不可撤销。
        </p>

        {errorMessage && (
          <div className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMessage}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel} disabled={deleting}>
            取消
          </Button>
          <Button
            variant="secondary"
            onClick={onConfirm}
            disabled={deleting}
            className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
          >
            {deleting ? '删除中…' : '确认删除'}
          </Button>
        </div>
      </div>
    </div>
  );
}
