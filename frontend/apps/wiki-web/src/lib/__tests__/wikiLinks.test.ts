/**
 * wikiLinks 纯函数单元测试
 *
 * 运行方式（需要 Node.js 18+ 或 tsx）：npx tsx src/lib/__tests__/wikiLinks.test.ts
 */

import {
  buildPageLookup,
  resolveInternalLinks,
  transformInternalLinks,
  parseWikiHref,
  WIKI_LINK_PREFIX,
} from '../wikiLinks';

// --------------- buildPageLookup ---------------

function testBuildPageLookup_singlePage() {
  const pages = [{ id: 1, title: '首页' }];
  const map = buildPageLookup(pages);
  console.assert(map.get('首页') === 1, '单页面应可查找');
  console.assert(map.size === 1, '应只有 1 个条目');
}

function testBuildPageLookup_duplicateTitlesExcluded() {
  const pages = [
    { id: 1, title: '同名' },
    { id: 2, title: '同名' },
    { id: 3, title: '唯一' },
  ];
  const map = buildPageLookup(pages);
  console.assert(!map.has('同名'), '同名歧义页面不应进入映射');
  console.assert(map.get('唯一') === 3, '唯一页面应可查找');
  console.assert(map.size === 1, '应只有唯一标题');
}

function testBuildPageLookup_emptyArray() {
  const map = buildPageLookup([]);
  console.assert(map.size === 0, '空数组应返回空映射');
}

// --------------- resolveInternalLinks ---------------

function testResolveInternalLinks_basic() {
  const lookup = new Map([
    ['页面A', 10],
    ['页面B', 20],
  ]);
  const links = resolveInternalLinks('[[页面A]] 和 [[页面B]]', lookup);
  console.assert(links.length === 2, '应有 2 个链接');
  console.assert(
    links[0].resolved && links[0].targetId === 10,
    '页面A 应解析为 10'
  );
  console.assert(
    links[1].resolved && links[1].targetId === 20,
    '页面B 应解析为 20'
  );
}

function testResolveInternalLinks_missingPage() {
  const lookup = new Map([['页面A', 10]]);
  const links = resolveInternalLinks('[[不存在]]', lookup);
  console.assert(links.length === 1, '应有 1 个链接');
  console.assert(!links[0].resolved, '不存在的页面应为 unresolved');
  console.assert(links[0].label === '不存在', 'label 应保留');
}

function testResolveInternalLinks_emptyLabel() {
  const lookup = new Map([['a', 1]]);
  const links = resolveInternalLinks('[[]]', lookup);
  console.assert(links.length === 0, '空标签应跳过');
}

function testResolveInternalLinks_noLinks() {
  const lookup = new Map([['a', 1]]);
  const links = resolveInternalLinks('普通文本，没有链接', lookup);
  console.assert(links.length === 0, '无链接时应返回空数组');
}

function testResolveInternalLinks_ambigousTitle() {
  const lookup = new Map<string, number>();
  const links = resolveInternalLinks('[[歧义页面]]', lookup);
  console.assert(links.length === 1, '应有 1 个链接');
  console.assert(!links[0].resolved, '歧义/不存在页面应为 unresolved');
}

// --------------- transformInternalLinks ---------------

function testTransformInternalLinks_resolved() {
  const lookup = new Map([['目标页', 5]]);
  const { markdown, links } = transformInternalLinks('参见 [[目标页]]', lookup);
  console.assert(
    markdown === `参见 [目标页](${WIKI_LINK_PREFIX}5)`,
    '应转换为 wiki:// 链接'
  );
  console.assert(links.length === 1 && links[0].resolved, '应返回已解析链接');
}

function testTransformInternalLinks_missing() {
  const lookup = new Map<string, number>();
  const { markdown, links } = transformInternalLinks('参见 [[不存在]]', lookup);
  console.assert(
    markdown === '参见 [[WIKI_MISSING:不存在]]',
    '未解析应转为 MISSING 占位符'
  );
  console.assert(links.length === 1 && !links[0].resolved, '应返回未解析链接');
}

function testTransformInternalLinks_mixedResolvedAndMissing() {
  const lookup = new Map([['存在', 1]]);
  const { markdown, links } = transformInternalLinks(
    '[[存在]] 和 [[不存在]]',
    lookup
  );
  console.assert(
    markdown === `[存在](${WIKI_LINK_PREFIX}1) 和 [[WIKI_MISSING:不存在]]`,
    '混合情况'
  );
  console.assert(links.length === 2, '应有 2 个链接');
  console.assert(
    links[0].resolved && links[0].targetId === 1,
    '第一个应 resolved'
  );
  console.assert(!links[1].resolved, '第二个应 unresolved');
}

function testTransformInternalLinks_duplicateLinks() {
  const lookup = new Map([['重复', 7]]);
  const { markdown, links } = transformInternalLinks(
    '[[重复]] [[重复]]',
    lookup
  );
  console.assert(
    markdown === `[重复](${WIKI_LINK_PREFIX}7) [重复](${WIKI_LINK_PREFIX}7)`,
    '每个出现都应替换'
  );
  console.assert(links.length === 2, '应有 2 个链接');
}

function testTransformInternalLinks_noLookup() {
  const lookup = new Map<string, number>();
  const { markdown, links } = transformInternalLinks('普通内容', lookup);
  console.assert(markdown === '普通内容', '无链接内容应原样返回');
  console.assert(links.length === 0);
}

// --------------- parseWikiHref ---------------

function testParseWikiHref_valid() {
  console.assert(parseWikiHref('wiki://42') === 42, '应解析为 42');
  console.assert(parseWikiHref('wiki://1') === 1, '应解析为 1');
}

function testParseWikiHref_invalid() {
  console.assert(
    parseWikiHref('https://example.com') === null,
    '非 wiki:// 应返回 null'
  );
  console.assert(parseWikiHref('wiki://abc') === null, '非数字应返回 null');
  console.assert(parseWikiHref('') === null, '空字符串应返回 null');
}

// --------------- 运行全部测试 ---------------

let passed = 0;
let failed = 0;

function run(name: string, fn: () => void) {
  try {
    fn();
    passed += 1;
    console.log(`  PASS  ${name}`);
  } catch (err) {
    failed += 1;
    console.error(`  FAIL  ${name}`);
    console.error(`    ${err}`);
  }
}

console.log('wikiLinks 单元测试\n');

console.log('buildPageLookup:');
run('单页面', testBuildPageLookup_singlePage);
run('同名歧义排除', testBuildPageLookup_duplicateTitlesExcluded);
run('空数组', testBuildPageLookup_emptyArray);

console.log('\nresolveInternalLinks:');
run('基本解析', testResolveInternalLinks_basic);
run('页面不存在', testResolveInternalLinks_missingPage);
run('空标签跳过', testResolveInternalLinks_emptyLabel);
run('无链接内容', testResolveInternalLinks_noLinks);
run('歧义标题', testResolveInternalLinks_ambigousTitle);

console.log('\ntransformInternalLinks:');
run('已解析转换为 wiki://', testTransformInternalLinks_resolved);
run('未解析转为 MISSING', testTransformInternalLinks_missing);
run('混合解析', testTransformInternalLinks_mixedResolvedAndMissing);
run('重复链接', testTransformInternalLinks_duplicateLinks);
run('无链接原样返回', testTransformInternalLinks_noLookup);

console.log('\nparseWikiHref:');
run('有效 wiki:// 链接', testParseWikiHref_valid);
run('无效链接', testParseWikiHref_invalid);

console.log(`\n结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);

if (failed > 0) {
  process.exit(1);
}
