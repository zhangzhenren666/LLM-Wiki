import type { Metadata } from 'next';
import { NavHeader } from '@/components/layout/NavHeader';
import './globals.css';

export const metadata: Metadata = {
  title: 'Wiki 知识库',
  description: '基于 LLM-Wiki 理念的 Markdown 知识库管理系统',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <NavHeader />
        <main className="min-h-[calc(100vh-3.5rem)]">{children}</main>
      </body>
    </html>
  );
}