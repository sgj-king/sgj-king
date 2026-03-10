'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/auth';

interface AuthGuardProps {
  children: React.ReactNode;
}

const publicPaths = ['/login', '/register'];

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { token } = useAuthStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // 如果是公开页面，直接放行
    if (publicPaths.includes(pathname)) {
      setChecking(false);
      return;
    }

    // 仅依赖 token 判断（避免刷新后 isAuthenticated 丢失）
    if (!token) {
      router.push('/login');
    } else {
      setChecking(false);
    }
  }, [pathname, token, router]);

  // 公开页面直接显示
  if (publicPaths.includes(pathname)) {
    return <>{children}</>;
  }

  // 检查中显示加载状态
  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-slate-500">加载中...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}