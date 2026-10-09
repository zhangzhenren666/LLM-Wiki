import Link from 'next/link';
import { fetchHealth } from '@/lib/api';

export const revalidate = 5;

export default async function HealthPage() {
  let status = 'waiting';
  let message = '尚未连接';

  try {
    const health = await fetchHealth();
    status = health.data?.status ?? 'error';
    message = health.message ?? '';
  } catch {
    status = 'error';
    message = '后端服务不可用，请确认 FastAPI 已启动。';
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6">
      <header className="flex h-16 items-center justify-between border-b border-gray-200">
        <Link href="/" className="text-lg font-semibold">
          ← 返回首页
        </Link>
        <span className="text-sm text-gray-500">健康检查</span>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center text-center">
        <div
          className={`flex h-16 w-16 items-center justify-center rounded-full text-2xl font-bold ${
            status === 'ok'
              ? 'bg-green-100 text-green-600'
              : 'bg-red-100 text-red-600'
          }`}
        >
          {status === 'ok' ? 'OK' : '!'}
        </div>
        <h1 className="mt-4 text-2xl font-semibold">
          后端状态：{status === 'ok' ? '正常' : '异常'}
        </h1>
        <p className="mt-2 text-gray-600">{message}</p>
      </main>
    </div>
  );
}
