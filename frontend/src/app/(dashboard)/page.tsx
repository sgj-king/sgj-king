'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChartBar, FileText, Heart, Eye, TrendUp } from "@phosphor-icons/react";
import { analyticsApi, contentsApi } from '@/lib/api';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  trend?: "up" | "down" | "neutral";
  icon: React.ReactNode;
}

function StatCard({ title, value, change, trend = "neutral", icon }: StatCardProps) {
  const trendColors = {
    up: "text-emerald-500",
    down: "text-red-500",
    neutral: "text-slate-500"
  };
  
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
          {change && (
            <p className={`mt-1 text-sm font-medium ${trendColors[trend]}`}>
              {trend === "up" && "↑"} {change}
            </p>
          )}
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-50 text-sky-500">
          {icon}
        </div>
      </div>
    </div>
  );
}

interface Overview {
  total_notes: number;
  total_likes: number;
  total_collects: number;
  total_comments: number;
  total_shares: number;
  total_views: number;
  engagement_rate: number;
  popular_count: number;
  period_days: number;
}

interface ContentItem {
  id: string;
  title: string;
  status: string;
  published_at?: string | null;
  stats?: {
    likes: number;
    collects: number;
    comments: number;
    shares?: number;
    views?: number;
  };
}

interface TrendItem {
  date: string;
  likes: number;
  collects: number;
  comments: number;
  shares: number;
  views: number;
}

function formatNumber(num: number) {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}w`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num || 0);
}

export default function HomePage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [overviewRes, contentsRes, trendsRes] = await Promise.all([
          analyticsApi.overview(7),
          contentsApi.list({ status: 'published', per_page: 100 }),
          analyticsApi.trends(7, 'likes'),
        ]);

        if (!overviewRes.error) {
          setOverview(overviewRes.data?.overview || null);
        }
        if (!contentsRes.error) {
          setContents(contentsRes.data?.contents || []);
        }
        if (!trendsRes.error) {
          setTrends(trendsRes.data?.trends || []);
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const todayCount = useMemo(() => {
    const today = new Date();
    return contents.filter((c) => {
      if (!c.published_at) return false;
      const d = new Date(c.published_at);
      return d.toDateString() === today.toDateString();
    }).length;
  }, [contents]);

  const totalEngagement = useMemo(() => {
    if (!overview) return 0;
    return (
      overview.total_likes +
      overview.total_collects +
      overview.total_comments +
      overview.total_shares
    );
  }, [overview]);

  const hotRate = useMemo(() => {
    if (!overview || overview.total_notes === 0) return 0;
    return (overview.popular_count / overview.total_notes) * 100;
  }, [overview]);

  const topContents = useMemo(() => {
    return [...contents]
      .sort((a, b) => {
        const aEng = (a.stats?.likes || 0) + (a.stats?.collects || 0) + (a.stats?.comments || 0);
        const bEng = (b.stats?.likes || 0) + (b.stats?.collects || 0) + (b.stats?.comments || 0);
        return bEng - aEng;
      })
      .slice(0, 3);
  }, [contents]);

  const trendPoints = useMemo(() => {
    if (!trends.length) return '';
    const values = trends.map((t) => t.likes || 0);
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = Math.max(max - min, 1);
    const width = 320;
    const height = 160;
    const step = trends.length > 1 ? width / (trends.length - 1) : width;

    return values
      .map((v, i) => {
        const x = i * step;
        const y = height - ((v - min) / range) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }, [trends]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">数据概览</h1>
        <p className="mt-1 text-slate-500">查看您的运营数据汇总（近 7 天）</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="今日发布" 
          value={loading ? '-' : todayCount}
          icon={<FileText size={24} weight="bold" />}
        />
        <StatCard 
          title="总互动" 
          value={loading ? '-' : formatNumber(totalEngagement)}
          icon={<Heart size={24} weight="bold" />}
        />
        <StatCard 
          title="总浏览" 
          value={loading ? '-' : formatNumber(overview?.total_views || 0)}
          icon={<Eye size={24} weight="bold" />}
        />
        <StatCard 
          title="爆款率" 
          value={loading ? '-' : `${hotRate.toFixed(1)}%`}
          icon={<TrendUp size={24} weight="bold" />}
        />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-slate-900">数据趋势（点赞）</h2>
          <div className="mt-4 h-64 flex items-center justify-center">
            {trends.length === 0 ? (
              <div className="text-slate-400 flex items-center">
                <ChartBar size={48} />
                <span className="ml-2">暂无趋势数据</span>
              </div>
            ) : (
              <div className="w-full">
                <svg viewBox="0 0 320 160" className="w-full h-40">
                  <polyline
                    fill="none"
                    stroke="#0ea5e9"
                    strokeWidth="3"
                    points={trendPoints}
                  />
                </svg>
                <div className="mt-2 flex justify-between text-xs text-slate-400">
                  <span>{trends[0]?.date}</span>
                  <span>{trends[trends.length - 1]?.date}</span>
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-slate-900">热门内容</h2>
          <div className="mt-4 space-y-4">
            {topContents.length === 0 ? (
              <div className="text-slate-400">暂无已发布内容</div>
            ) : (
              topContents.map((item) => (
                <div key={item.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-50">
                  <div className="h-12 w-12 rounded-lg bg-slate-200" />
                  <div className="flex-1">
                    <p className="font-medium text-slate-900 truncate">{item.title}</p>
                    <p className="text-sm text-slate-500">
                      点赞 {item.stats?.likes || 0} · 收藏 {item.stats?.collects || 0} · 评论 {item.stats?.comments || 0}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
