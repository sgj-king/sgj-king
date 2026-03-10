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
  const { token, setToken } = useAuthStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // 如果是公开页面，直接放行
    if (publicPaths.includes(pathname)) {
      setChecking(false);
      return;
    }

    // 尝试从 localStorage 恢复 token
    let effectiveToken = token;
    if (!effectiveToken && typeof window !== 'undefined') {
      const direct = localStorage.getItem('token');
      if (direct) {
        effectiveToken = direct;
        setToken(direct);
      } else {
        const persisted = localStorage.getItem('redflow-auth');
        if (persisted) {
          try {
            const parsed = JSON.parse(persisted);
            const persistedToken = parsed?.state?.token;
            if (persistedToken) {
              effectiveToken = persistedToken;
              setToken(persistedToken);
            }
          } catch {}
        }
      }
    }

    if (!effectiveToken) {
      router.push('/login');
    } else {
      setChecking(false);
    }
  }, [pathname, token, router, setToken]);

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