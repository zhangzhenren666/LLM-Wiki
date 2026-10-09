import Link from 'next/link';
import { Button } from '@wiki/ui';
import { APP_NAME, APP_VERSION } from '@wiki/config';

export default function HomePage() {
  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col">
      <main className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">
          欢迎使用 {APP_NAME}
        </h1>
        <p className="mt-4 max-w-xl text-lg text-gray-600">
          基于 LLM-Wiki 理念的 Markdown
          知识库管理系统，用于管理知识页面、目录、标签、页面关系与知识图谱。
        </p>
        <div className="mt-8 flex gap-3">
          <Link href="/knowledge-bases">
            <Button>进入知识库</Button>
          </Link>
          <Link href="/search">
            <Button variant="secondary">搜索页面</Button>
          </Link>
        </div>
        <p className="mt-6 text-sm text-gray-400">
          版本 {APP_VERSION}
        </p>
      </main>
    </div>
  );
}
