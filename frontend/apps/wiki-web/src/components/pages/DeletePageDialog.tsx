'use client';

import { Button } from '@wiki/ui';

interface DeletePageDialogProps {
  /** 待删除页面标题 */
  title: string;
  /** 是否含有子页面（用于提示） */
  hasChildren: boolean;
  deleting?: boolean;
  errorMessage?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 页面删除二次确认弹窗
 */
export function DeletePageDialog({
  title,
  hasChildren,
  deleting = false,
  errorMessage,
  onConfirm,
  onCancel,
}: DeletePageDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900">删除页面</h3>
        <p className="mt-3 text-sm text-gray-600">
          确定要删除页面
          <span className="font-medium text-gray-900">「{title}」</span>吗？
          {hasChildren
            ? '其下的子页面将一并删除，此操作不可撤销。'
            : '此操作不可撤销。'}
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
