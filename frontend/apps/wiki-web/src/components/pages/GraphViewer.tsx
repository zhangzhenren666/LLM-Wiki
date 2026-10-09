'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { GraphData, GraphEdge, GraphNode } from '@wiki/types';
import { Button } from '@wiki/ui';
import cytoscape from 'cytoscape';

interface GraphViewerProps {
  graphData: GraphData | null;
  loading: boolean;
  error: string | null;
  height?: number;
  emptyMessage?: string;
  onNavigate?: (nodeId: number) => void;
  onRetry?: () => void;
  totalCount?: number;
}

/** 关系类型 → 中文标签 + 颜色 */
const RELATION_META: Record<string, { label: string; color: string }> = {
  link: { label: '内部链接', color: '#3b82f6' },
  reference: { label: '引用', color: '#8b5cf6' },
  related: { label: '相关知识', color: '#10b981' },
  references: { label: '参考资料', color: '#f59e0b' },
  depends_on: { label: '依赖关系', color: '#ef4444' },
  parent: { label: '上级知识', color: '#ec4899' },
};

const RELATION_TYPES = Object.keys(RELATION_META) as string[];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CYTOSCAPE_STYLES: any[] = [
  {
    selector: 'node',
    style: {
      'background-color': '#3b82f6',
      label: 'data(label)',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'font-size': '10px',
      color: '#374151',
      'text-margin-y': 6,
      'border-width': 2,
      'border-color': '#2563eb',
    },
  },
  {
    selector: 'edge',
    style: {
      width: 2,
      'curve-style': 'bezier',
      label: 'data(label)',
      'font-size': '9px',
      color: '#6b7280',
      'text-rotation': 'autorotate',
      'text-margin-y': -8,
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.7,
      'text-background-padding': '2px',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1.2,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'background-color': '#f59e0b',
      'border-color': '#d97706',
      'border-width': 4,
      width: 44,
      height: 44,
      'font-size': '13px',
      'font-weight': 'bold',
      'z-index': 10,
    },
  },
  {
    selector: 'edge:selected',
    style: {
      width: 4,
      'z-index': 9,
    },
  },
];

/**
 * 知识图谱可视化组件。
 *
 * 直接使用 cytoscape 原生 API 管理实例生命周期，避免
 * react-cytoscapejs 与手动控制的冲突。
 */
export function GraphViewer({
  graphData,
  loading,
  error,
  height = 480,
  emptyMessage = '暂无图谱数据',
  onNavigate,
  onRetry,
  totalCount,
}: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const graphDataRef = useRef<GraphData | null>(null);
  const activeLayoutRef = useRef<cytoscape.Layouts | null>(null);

  const [visibleTypes, setVisibleTypes] = useState<Record<string, boolean>>(
    () => Object.fromEntries(RELATION_TYPES.map((t) => [t, true]))
  );
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [layoutReady, setLayoutReady] = useState(false);

  // 同步 graphData 到 ref（供事件回调读取最新值）
  graphDataRef.current = graphData;

  const toggleType = (type: string) => {
    setVisibleTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  // 转换为 cytoscape elements（含筛选）
  const elements = useMemo(() => {
    if (!graphData) return [];
    const filteredEdges = graphData.edges.filter(
      (e) => visibleTypes[e.relation_type] !== false
    );
    const connectedIds = new Set<number>();
    filteredEdges.forEach((e) => {
      connectedIds.add(e.source);
      connectedIds.add(e.target);
    });

    const activeNodes =
      filteredEdges.length > 0
        ? graphData.nodes.filter((n) => connectedIds.has(n.id))
        : graphData.nodes;

    const degreeMap = new Map<number, number>();
    filteredEdges.forEach((e) => {
      degreeMap.set(e.source, (degreeMap.get(e.source) ?? 0) + 1);
      degreeMap.set(e.target, (degreeMap.get(e.target) ?? 0) + 1);
    });
    const maxDegree = Math.max(2, ...degreeMap.values());

    const cyNodes = activeNodes.map((n: GraphNode) => {
      const degree = degreeMap.get(n.id) ?? 0;
      const size = Math.max(22, 10 + 22 * (degree / maxDegree));
      return {
        group: 'nodes' as const,
        data: { id: String(n.id), label: n.title.slice(0, 18), fullTitle: n.title, slug: n.slug, degree },
        style: { width: size, height: size },
      };
    });

    const cyEdges = filteredEdges.map((e: GraphEdge) => {
      const meta = RELATION_META[e.relation_type];
      return {
        group: 'edges' as const,
        data: {
          id: `e${e.id}`,
          source: String(e.source),
          target: String(e.target),
          label: e.label || meta?.label || e.relation_type,
          relationType: e.relation_type,
        },
        style: {
          'line-color': meta?.color ?? '#9ca3af',
          'target-arrow-color': meta?.color ?? '#9ca3af',
        },
      };
    });

    return [...cyNodes, ...cyEdges] as cytoscape.ElementDefinition[];
  }, [graphData, visibleTypes]);

  // 是否已就绪可渲染图谱
  const isDataReady = !loading && !error && graphData && graphData.nodes.length > 0;

  /**
   * 统一管理 cytoscape 实例生命周期：创建、更新元素、销毁。
   *
   * 将原来的两个独立 useEffect 合并为一个，避免以下竞态问题：
   *   - 初始化 effect 在 loading 态时因 containerRef 为空而跳过，
   *     数据就绪后 React 可能在同一次提交中同时触发初始化和元素更新，
   *     导致 cyRef.current 尚未赋值时 elements 更新 effect 就已执行。
   *   - 现在改为单一 effect，依赖 [isDataReady, elements]，
   *     「检查容器 → 创建实例 → 加载元素 → 跑布局」是同步链路，
   *     不再需要两个 effect 之间的时序协调。
   */
  useEffect(() => {
    // 辅助：安全销毁 cytoscape 实例（先停止运行中的布局，再销毁，避免回调 null 崩溃）
    const safeDestroy = () => {
      if (activeLayoutRef.current) {
        try { activeLayoutRef.current.stop(); } catch { /* 布局可能已完成 */ }
        activeLayoutRef.current = null;
      }
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      setLayoutReady(false);
    };

    if (!isDataReady) {
      safeDestroy();
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    // ---- 创建 cytoscape 实例（首次，或之前被销毁后重建） ----
    if (!cyRef.current) {
      const cy = cytoscape({
        container,
        elements: [],
        style: CYTOSCAPE_STYLES,
        layout: { name: 'preset' },
        zoomingEnabled: true,
        userZoomingEnabled: true,
        panningEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
        autoungrabify: false,
        autounselectify: false,
      });

      cyRef.current = cy;

      cy.on('tap', 'node', (evt) => {
        const nodeId = Number(evt.target.id());
        const data = graphDataRef.current;
        const node = data?.nodes.find((n) => n.id === nodeId);
        if (node) {
          setSelectedNode((prev) => (prev?.id === node.id ? null : node));
        }
      });

      cy.on('tap', (evt) => {
        if (evt.target === cy) setSelectedNode(null);
      });
    }

    // ---- 更新图谱元素 ----
    const cy = cyRef.current;

    // 先停掉当前运行的布局
    if (activeLayoutRef.current) {
      try { activeLayoutRef.current.stop(); } catch { /* 忽略 */ }
      activeLayoutRef.current = null;
    }

    if (elements.length === 0) {
      cy.elements().remove();
      setLayoutReady(true);
      return;
    }

    setLayoutReady(false);
    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });

    // concentric 布局：按节点度数分层排列，高连接度核心节点居中，
    // 低度数子节点环绕外层，天然避免力导向布局中密集边导致的聚合。
    const layout = cy.layout({
      name: 'concentric',
      animate: true,
      animationDuration: 600,
      concentric: function (node: cytoscape.NodeSingular) {
        return Math.max(1, node.data('degree') || 1);
      },
      levelWidth: function () {
        return 1;
      },
      minNodeSpacing: 180,
      fit: true,
      padding: 80,
    });
    activeLayoutRef.current = layout as cytoscape.Layouts;
    layout.one('layoutstop', () => {
      activeLayoutRef.current = null;
      setLayoutReady(true);
    });
    layout.run();

    // 不在 cleanup 中销毁 cy —— 筛选切换（elements 变化）时不应重建实例。
    // 销毁仅由上方 `!isDataReady` 分支或下方卸载 effect 负责。
  }, [isDataReady, elements]);

  // 组件卸载时销毁 cytoscape 实例
  useEffect(() => {
    return () => {
      if (activeLayoutRef.current) {
        try { activeLayoutRef.current.stop(); } catch { /* ignore */ }
        activeLayoutRef.current = null;
      }
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, []);

  // 加载态
  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50" style={{ height }}>
        <span className="mr-2 inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        <span className="text-gray-500">加载图谱中…</span>
      </div>
    );
  }

  // 错误态
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-gray-200 bg-gray-50" style={{ height }}>
        <p className="text-sm text-red-500">{error}</p>
        {onRetry && <Button variant="secondary" onClick={onRetry}>重试</Button>}
      </div>
    );
  }

  // 空数据
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50" style={{ height }}>
        <p className="text-sm text-gray-400">{emptyMessage}</p>
      </div>
    );
  }

  const displayedEdges = graphData.edges.filter(
    (e) => visibleTypes[e.relation_type] !== false
  ).length;

  return (
    <div>
      {/* 筛选栏 */}
      <div className="mb-3 flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-gray-400 mr-1">筛选:</span>
        {RELATION_TYPES.map((t) => {
          const meta = RELATION_META[t];
          const active = visibleTypes[t] !== false;
          return (
            <button
              key={t}
              type="button"
              onClick={() => toggleType(t)}
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs transition-all ${
                active ? 'bg-white shadow-sm' : 'opacity-40 grayscale'
              }`}
              style={{
                borderColor: active ? meta.color : '#d1d5db',
                color: active ? '#374151' : '#9ca3af',
              }}
            >
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: meta.color }} />
              {meta.label}
            </button>
          );
        })}
      </div>

      {/* 图谱容器 */}
      <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-gray-50/30" style={{ height }}>
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

        {/* 节点详情面板 */}
        {selectedNode && (
          <div className="absolute bottom-4 left-4 right-4 rounded-lg border border-blue-200 bg-white/95 p-4 shadow-lg backdrop-blur-sm max-w-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <h4 className="truncate text-sm font-semibold text-gray-900">{selectedNode.title}</h4>
                <p className="mt-0.5 text-xs text-gray-400">{selectedNode.slug}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    onNavigate?.(selectedNode.id);
                    setSelectedNode(null);
                  }}
                >
                  查看详情
                </Button>
                <Button variant="ghost" onClick={() => setSelectedNode(null)}>关闭</Button>
              </div>
            </div>
          </div>
        )}

        {/* 布局进行中 */}
        {!layoutReady && (
          <div className="pointer-events-none absolute right-3 top-3 rounded bg-white/80 px-2 py-1 text-xs text-gray-400 backdrop-blur">
            布局中…
          </div>
        )}
      </div>

      {/* 底部信息栏 */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <span>
          {elements.filter((el) => el.group === 'nodes').length} 个节点 · {displayedEdges} 条边
          {totalCount && totalCount > graphData.nodes.length ? `（共 ${totalCount} 页面）` : ''}
        </span>
        <span>拖拽节点 · 滚轮缩放 · 点击查看详情</span>
      </div>
    </div>
  );
}