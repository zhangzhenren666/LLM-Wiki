'use client';

import { Button } from '@wiki/ui';

interface UnsavedChangesDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 未保存内容提醒弹窗
 * 当存在未保存修改且用户尝试取消/切换时弹出，确认放弃或返回继续编辑。
 */
export function UnsavedChangesDialog({
  onConfirm,
  onCancel,
}: UnsavedChangesDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900">放弃修改？</h3>
        <p className="mt-3 text-sm text-gray-600">
          当前页面有未保存的修改，确定要放弃并离开编辑吗？
        </p>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            继续编辑
          </Button>
          <Button
            variant="secondary"
            onClick={onConfirm}
            className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
          >
            放弃修改
          </Button>
        </div>
      </div>
    </div>
  );
}
