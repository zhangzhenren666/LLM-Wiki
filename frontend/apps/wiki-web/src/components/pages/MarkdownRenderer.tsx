'use client';

import { useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import type { Components } from 'react-markdown';
import { transformInternalLinks, parseWikiHref } from '@/lib/wikiLinks';

interface MarkdownRendererProps {
  /** Markdown 源文本 */
  content: string;
  /** 追加的 className */
  className?: string;
  /** 页面标题 → ID 映射（用于解析 [[内部链接]]） */
  pageLookup?: Map<string, number>;
  /** 内部链接点击回调 */
  onInternalLinkClick?: (targetPageId: number) => void;
}

const MISSING_RE = /\[\[WIKI_MISSING:(.+?)\]\]/g;

/**
 * 安全 Markdown 渲染组件
 *
 * - 使用 react-markdown 渲染为 React 元素（不直接使用 innerHTML）
 * - 通过 rehype-sanitize 进行 HTML 白名单消毒，防止 XSS / 脚本注入
 * - remark-gfm 支持表格、删除线、任务列表等 GFM 语法
 * - 支持 [[页面标题]] 内部链接解析与跳转
 * - 查看模式与编辑预览模式共用此组件。
 */
export function MarkdownRenderer({
  content,
  className,
  pageLookup,
  onInternalLinkClick,
}: MarkdownRendererProps) {
  // 预处理：将 [[title]] 转换为标准 Markdown 链接
  const processedContent = useMemo(() => {
    if (!pageLookup || pageLookup.size === 0) return content;
    const { markdown } = transformInternalLinks(content, pageLookup);
    // 将 WIKI_MISSING 占位符替换为可读文本（粗体 + 不存在提示）
    return markdown.replace(
      MISSING_RE,
      (_, label: string) => `**${label}**（页面不存在）`
    );
  }, [content, pageLookup]);

  // 内部链接点击处理
  const handleInternalClick = useCallback(
    (href: string, e: React.MouseEvent) => {
      const wikiId = parseWikiHref(href);
      if (wikiId !== null && onInternalLinkClick) {
        e.preventDefault();
        onInternalLinkClick(wikiId);
      }
    },
    [onInternalLinkClick]
  );

  const components: Partial<Components> = useMemo(
    () => ({
      a({ href, children, ...props }) {
        if (!href) return <a {...props}>{children}</a>;
        const wikiId = parseWikiHref(href);
        if (wikiId !== null) {
          return (
            <a
              href="#"
              onClick={(e) => handleInternalClick(href, e)}
              className="wiki-internal-link"
              title="跳转到对应页面"
              {...props}
            >
              {children}
            </a>
          );
        }
        return (
          <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
            {children}
          </a>
        );
      },
    }),
    [handleInternalClick]
  );

  return (
    <div className={`markdown-body ${className ?? ''}`}>
      {processedContent ? (
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeSanitize]}
          components={components}
        >
          {processedContent}
        </ReactMarkdown>
      ) : (
        <p className="text-gray-400">（暂无内容）</p>
      )}
    </div>
  );
}
