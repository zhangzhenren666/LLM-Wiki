'use client';

import { useMemo, useState } from 'react';
import type { Page } from '@wiki/types';
import { Button } from '@wiki/ui';

interface MovePageDialogProps {
  /** 待移动的页面 */
  page: Page;
  /** 知识库下全部页面（扁平列表），用于选择目标父节点 */
  allPages: Page[];
  /** 移动中 */
  moving: boolean;
  errorMessage: string | null;
  onConfirm: (targetParentId: number | null) => void;
  onCancel: () => void;
}

/**
 * 页面移动对话框：选择新的父节点或将页面置为顶层。
 * 自动排除该页自身及其整棵子树，避免产生循环引用。
 */
export function MovePageDialog({
  page,
  allPages,
  moving,
  errorMessage,
  onConfirm,
  onCancel,
}: MovePageDialogProps) {
  // 计算该页的子树集合，作为不可选目标
  const excludedIds = useMemo(() => {
    const ids = new Set<number>([page.id]);
    const byParent = new Map<number, number[]>();
    for (const p of allPages) {
      if (p.parent_id == null) continue;
      const list = byParent.get(p.parent_id) ?? [];
      list.push(p.id);
      byParent.set(p.parent_id, list);
    }
    const queue = [page.id];
    while (queue.length) {
      const cur = queue.pop()!;
      for (const child of byParent.get(cur) ?? []) {
        if (!ids.has(child)) {
          ids.add(child);
          queue.push(child);
        }
      }
    }
    return ids;
  }, [allPages, page.id]);

  // 可选父节点：排除自身子树，同时自身已挂在某父下时，该父不重复（本身无意义但无害）
  const candidates = useMemo(() => {
    return allPages.filter((p) => !excludedIds.has(p.id));
  }, [allPages, excludedIds]);

  // 目标父 id；null 表示顶层
  const [target, setTarget] = useState<number | null>(null);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900">
          移动「{page.title}」
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          选择新的父节点（或将页面置为顶层）。不可选择其自身所在子树。
        </p>

        <div className="mt-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            目标位置
          </label>
          <select
            value={target ?? ''}
            disabled={moving}
            onChange={(e) =>
              setTarget(e.target.value === '' ? null : Number(e.target.value))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-400 disabled:opacity-50"
          >
            <option value="">（顶层）</option>
            {candidates.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id === page.parent_id ? '（当前父节点）' : ''}
                {p.title}
              </option>
            ))}
          </select>
        </div>

        {errorMessage && (
          <p className="mt-3 text-sm text-red-600">{errorMessage}</p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel} disabled={moving}>
            取消
          </Button>
          <Button
            onClick={() => onConfirm(target)}
            disabled={moving}
            data-testid="confirm-move"
          >
            {moving ? '移动中…' : '确认移动'}
          </Button>
        </div>
      </div>
    </div>
  );
}
