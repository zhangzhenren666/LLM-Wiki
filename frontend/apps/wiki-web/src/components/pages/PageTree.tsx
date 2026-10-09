'use client';

import { useMemo, useState } from 'react';
import type { Page } from '@wiki/types';
import { Button } from '@wiki/ui';

/** 树节点状态的展示映射 */
const STATUS_TAG: Record<string, { label: string; className: string }> = {
  published: { label: '已发布', className: 'bg-green-100 text-green-700' },
  draft: { label: '草稿', className: 'bg-gray-100 text-gray-600' },
  archived: { label: '已归档', className: 'bg-amber-100 text-amber-700' },
};

interface PageTreeProps {
  /** 某个知识库下的全部页面（扁平列表） */
  pages: Page[];
  /** 当前选中页面 id */
  selectedId: number | null;
  /** 刷新数据（用于空态重试） */
  onReload: () => void;
  onSelect: (page: Page) => void;
  onCreateChild: (parent: Page) => void;
  onDelete: (page: Page) => void;
}

/** 递归按标题过滤页面树，保留匹配节点所在完整路径 */
function filterPages(pages: Page[], keyword: string): Page[] {
  const lower = keyword.toLowerCase();
  const matchIds = new Set<number>();

  // 标记匹配的节点
  for (const page of pages) {
    if (page.title.toLowerCase().includes(lower)) {
      matchIds.add(page.id);
    }
  }

  // 向上追溯：将匹配节点的所有祖先也加入集合
  const parentMap = new Map<number, number | null>();
  for (const page of pages) {
    parentMap.set(page.id, page.parent_id ?? null);
  }
  let changed = true;
  while (changed) {
    changed = false;
    for (const id of [...matchIds]) {
      const parentId = parentMap.get(id);
      if (parentId != null && !matchIds.has(parentId)) {
        matchIds.add(parentId);
        changed = true;
      }
    }
  }

  // 只保留匹配路径上的页面
  return pages.filter((p) => matchIds.has(p.id));
}

interface TreeNodeProps {
  page: Page;
  childPages: Page[];
  depth: number;
  expanded: boolean;
  selectedId: number | null;
  expandedIds: Set<number>;
  childrenMap: Map<number, Page[]>;
  onToggle: (id: number) => void;
  onSelect: (page: Page) => void;
  onCreateChild: (parent: Page) => void;
  onDelete: (page: Page) => void;
}

/** 递归渲染树节点 */
function TreeNode({
  page,
  childPages,
  depth,
  expanded,
  selectedId,
  expandedIds,
  childrenMap,
  onToggle,
  onSelect,
  onCreateChild,
  onDelete,
}: TreeNodeProps) {
  const hasChildren = childPages.length > 0;
  const tag = STATUS_TAG[page.status] ?? STATUS_TAG.draft;
  const selected = selectedId === page.id;

  return (
    <li>
      <div
        className={`group flex items-center gap-1 rounded-md py-1 pr-1 ${
          selected ? 'bg-blue-50' : 'hover:bg-gray-50'
        }`}
        style={{ paddingLeft: `${depth * 14 + 6}px` }}
      >
        <button
          type="button"
          onClick={() => onToggle(page.id)}
          className="flex h-4 w-4 shrink-0 items-center justify-center text-gray-400 hover:text-gray-700"
          aria-label={hasChildren ? (expanded ? '收起' : '展开') : undefined}
          disabled={!hasChildren}
        >
          {hasChildren ? (
            <span
              className={`inline-block text-[10px] leading-none transition-transform ${expanded ? '' : '-rotate-90'}`}
            >
              ▶
            </span>
          ) : null}
        </button>

        <button
          type="button"
          onClick={() => onSelect(page)}
          className="min-w-0 flex-1 truncate text-left text-sm text-gray-800"
          title={page.title}
        >
          <span className={selected ? 'font-medium text-blue-700' : ''}>
            {page.title}
          </span>
          <span
            className={`ml-2 inline-block shrink-0 rounded px-1 text-[10px] leading-4 ${tag.className}`}
          >
            {tag.label}
          </span>
        </button>

        <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
          <button
            type="button"
            onClick={() => onCreateChild(page)}
            className="rounded px-1 text-gray-400 hover:text-blue-600"
            title="新建子页面"
          >
            ＋
          </button>
          <button
            type="button"
            onClick={() => onDelete(page)}
            className="rounded px-1 text-gray-400 hover:text-red-600"
            title="删除页面"
          >
            ×
          </button>
        </div>
      </div>

      {hasChildren && expanded && (
        <ul className="mt-0.5">
          {childPages.map((child) => (
            <TreeNode
              key={child.id}
              page={child}
              childPages={childrenMap.get(child.id) ?? []}
              depth={depth + 1}
              expanded={expandedIds.has(child.id)}
              selectedId={selectedId}
              expandedIds={expandedIds}
              childrenMap={childrenMap}
              onToggle={onToggle}
              onSelect={onSelect}
              onCreateChild={onCreateChild}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * 页面树组件
 *
 * 接收某个知识库的扁平页面列表，内部按 parent_id 构建树并递归渲染。
 * 支持展开/收起、选中状态、新建子页面与删除操作（通过回调上抛），
 * 可处理较深层级（递归）。
 */
export function PageTree({
  pages,
  selectedId,
  onReload,
  onSelect,
  onCreateChild,
  onDelete,
}: PageTreeProps) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [filterText, setFilterText] = useState('');

  // 按父 id 建立子页面映射，顶层父 id 记作 0
  const childrenMap = useMemo(() => {
    const map = new Map<number, Page[]>();
    for (const page of pages) {
      const parent = page.parent_id ?? 0;
      const list = map.get(parent) ?? [];
      list.push(page);
      map.set(parent, list);
    }
    return map;
  }, [pages]);

  // 过滤后的页面列表
  const filteredPages = useMemo(() => {
    const keyword = filterText.trim();
    if (!keyword) return pages;
    return filterPages(pages, keyword);
  }, [pages, filterText]);

  // 过滤后的顶层页面
  const topLevel = useMemo(() => {
    const filteredIds = new Set(filteredPages.map((p) => p.id));
    return (childrenMap.get(0) ?? []).filter((p) => filteredIds.has(p.id));
  }, [childrenMap, filteredPages]);

  const toggle = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div>
      {/* 搜索过滤 */}
      {pages.length > 0 && (
        <div className="mb-2 px-2">
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="搜索页面…"
            className="w-full rounded-md border border-gray-200 px-2.5 py-1.5 text-xs text-gray-700 outline-none placeholder:text-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors"
            aria-label="搜索页面"
          />
        </div>
      )}

      {pages.length === 0 ? (
        <div className="flex flex-col items-center gap-3 p-8 text-center">
          <p className="text-sm text-gray-500">还没有页面</p>
          <Button variant="secondary" onClick={() => onReload()}>
            刷新
          </Button>
        </div>
      ) : topLevel.length === 0 && filterText.trim() ? (
        <div className="flex flex-col items-center gap-3 p-8 text-center">
          <p className="text-sm text-gray-400">没有匹配「{filterText.trim()}」的页面</p>
          <button
            type="button"
            onClick={() => setFilterText('')}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            清除搜索
          </button>
        </div>
      ) : (
        <ul className="space-y-0.5">
          {topLevel.map((page) => (
            <TreeNode
              key={page.id}
              page={page}
              childPages={(childrenMap.get(page.id) ?? []).filter((p) =>
                filteredPages.some((fp) => fp.id === p.id)
              )}
              depth={0}
              expanded={expandedIds.has(page.id)}
              selectedId={selectedId}
              expandedIds={expandedIds}
              childrenMap={childrenMap}
              onToggle={toggle}
              onSelect={onSelect}
              onCreateChild={onCreateChild}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
