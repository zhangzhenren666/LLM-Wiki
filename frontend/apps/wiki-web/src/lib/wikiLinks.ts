/**
 * Wiki 内部链接（[[页面标题]]）解析工具（纯函数，可独立测试）。
 *
 * 设计要点（与后端保持一致）：
 * - 仅当标题在知识库内精确命中且唯一时才可跳转，避免同名歧义与模糊匹配；
 * - 歧义或页面不存在时不产生跳转链接，仅以占位文本提示；
 * - 不修改普通 Markdown 链接，保证安全处理链路不受影响。
 */

const INTERNAL_LINK_RE = /\[\[([^[\]]+)\]\]/g;

export const WIKI_LINK_PREFIX = 'wiki://';

export function buildPageLookup(
  pages: { id: number; title: string }[]
): Map<string, number> {
  const map = new Map<string, number>();
  const counts = new Map<string, number>();
  for (const p of pages) {
    counts.set(p.title, (counts.get(p.title) ?? 0) + 1);
  }
  for (const p of pages) {
    if (counts.get(p.title) === 1) {
      map.set(p.title, p.id);
    }
  }
  return map;
}

export interface InternalLink {
  label: string;
  resolved: boolean;
  targetId?: number;
}

export function resolveInternalLinks(
  content: string,
  lookup: Map<string, number>
): InternalLink[] {
  const results: InternalLink[] = [];
  for (const match of content.matchAll(INTERNAL_LINK_RE)) {
    const label = match[1].trim();
    if (!label) continue;
    const targetId = lookup.get(label);
    results.push(
      targetId === undefined
        ? { label, resolved: false }
        : { label, resolved: true, targetId }
    );
  }
  return results;
}

export function transformInternalLinks(
  content: string,
  lookup: Map<string, number>
): { markdown: string; links: InternalLink[] } {
  const links = resolveInternalLinks(content, lookup);
  let index = 0;
  const markdown = content.replace(INTERNAL_LINK_RE, (raw) => {
    const label = raw.slice(2, -2).trim();
    if (!label) return raw;
    const link = links[index];
    index += 1;
    if (link && link.resolved && link.targetId !== undefined) {
      return `[${label}](${WIKI_LINK_PREFIX}${link.targetId})`;
    }
    return `[[WIKI_MISSING:${label}]]`;
  });
  return { markdown, links };
}

export function parseWikiHref(href: string): number | null {
  if (!href.startsWith(WIKI_LINK_PREFIX)) return null;
  const id = Number(href.slice(WIKI_LINK_PREFIX.length));
  return Number.isFinite(id) ? id : null;
}
