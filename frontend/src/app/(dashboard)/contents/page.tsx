'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash, Calendar, Play, Clock } from '@phosphor-icons/react';
import { accountsApi, contentsApi } from '@/lib/api';

interface Account {
  id: string;
  nickname: string;
}

interface Content {
  id: string;
  title: string;
  status: string;
  scheduled_at: string;
  published_at: string;
  stats: {
    likes: number;
    collects: number;
    comments: number;
  };
  created_at: string;
}

export default function ContentsPage() {
  const [contents, setContents] = useState<Content[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [showEditor, setShowEditor] = useState(false);

  const loadContents = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter !== 'all' ? { status: filter } : {};
      const res = await contentsApi.list(params as any);
      setContents(res.data?.contents || []);
    } catch (err) {
      console.error('Failed to load contents:', err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadContents();
  }, [loadContents]);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    const res = await accountsApi.list();
    setAccounts((res.data?.accounts || []).map((a: any) => ({ id: a.id, nickname: a.nickname })));
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除该内容吗？')) return;
    const res = await contentsApi.delete(id);
    if (res.error) {
      alert(res.error);
      return;
    }
    loadContents();
  };

  const PUBLISH_URL = 'https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image';

  const handlePublish = async (id: string) => {
    const res = await contentsApi.publish(id);
    if (res.error) {
      alert(res.error);
      return;
    }
    loadContents();
  };

  const handleManualPublish = async (id: string) => {
    const res = await contentsApi.get(id);
    if (res.error) {
      alert(res.error);
      return;
    }

    const content = res.data?.content;
    if (!content) {
      alert('内容不存在');
      return;
    }

    const tags = (content.tags || []).map((t: string) => `#${t}`).join(' ');
    const text = `${content.title}\n\n${content.body}\n\n${tags}`.trim();

    try {
      await navigator.clipboard.writeText(text);
      window.open(PUBLISH_URL, '_blank');
      alert('已复制内容到剪贴板，并打开发布页，请手动上传图片并点击发布。');
    } catch (err) {
      console.error(err);
      alert('复制失败，请检查浏览器权限');
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'bg-slate-100 text-slate-600',
      scheduled: 'bg-amber-100 text-amber-600',
      publishing: 'bg-blue-100 text-blue-600',
      published: 'bg-emerald-100 text-emerald-600',
      failed: 'bg-red-100 text-red-600',
      manual: 'bg-purple-100 text-purple-600',
    };
    const labels: Record<string, string> = {
      draft: '草稿',
      scheduled: '定时',
      publishing: '发布中',
      published: '已发布',
      failed: '失败',
      manual: '待手动发布',
    };
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || styles.draft}`}>
        {labels[status] || status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">内容管理</h1>
          <p className="mt-1 text-slate-500">创建和管理小红书笔记</p>
        </div>
        <button
          onClick={() => setShowEditor(true)}
          className="flex items-center gap-2 px-4 py-2 bg-sky-500 text-white rounded-lg hover:bg-sky-600 transition-colors"
        >
          <Plus size={20} weight="bold" />
          <span>新建内容</span>
        </button>
      </div>

      <div className="flex gap-2">
        {[
          { value: 'all', label: '全部' },
          { value: 'draft', label: '草稿' },
          { value: 'scheduled', label: '定时' },
          { value: 'published', label: '已发布' },
          { value: 'manual', label: '待手动发布' },
          { value: 'failed', label: '失败' },
        ].map((item) => (
          <button
            key={item.value}
            onClick={() => setFilter(item.value)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === item.value
                ? 'bg-sky-500 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-500">标题</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-500">状态</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-500">数据</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-500">时间</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-slate-500">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-slate-400">加载中...</td>
              </tr>
            ) : contents.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-slate-400">暂无内容</td>
              </tr>
            ) : (
              contents.map((content) => (
                <tr key={content.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <p className="font-medium text-slate-900 truncate max-w-md">{content.title}</p>
                  </td>
                  <td className="px-6 py-4">{getStatusBadge(content.status)}</td>
                  <td className="px-6 py-4">
                    {content.status === 'published' ? (
                      <div className="flex gap-3 text-sm text-slate-500">
                        <span>❤️ {content.stats?.likes || 0}</span>
                        <span>⭐ {content.stats?.collects || 0}</span>
                        <span>💬 {content.stats?.comments || 0}</span>
                      </div>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500">
                    {content.status === 'scheduled' ? (
                      <div className="flex items-center gap-1">
                        <Clock size={14} />
                        <span>{new Date(content.scheduled_at).toLocaleString('zh-CN')}</span>
                      </div>
                    ) : content.published_at ? (
                      <div className="flex items-center gap-1">
                        <Calendar size={14} />
                        <span>{new Date(content.published_at).toLocaleDateString('zh-CN')}</span>
                      </div>
                    ) : (
                      <span>创建 {new Date(content.created_at).toLocaleDateString('zh-CN')}</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {content.status === 'draft' && (
                        <button
                          className="p-2 text-sky-500 hover:bg-sky-50 rounded"
                          title="发布"
                          onClick={() => handlePublish(content.id)}
                        >
                          <Play size={18} />
                        </button>
                      )}
                      {content.status === 'manual' && (
                        <button
                          className="px-3 py-2 text-purple-600 hover:bg-purple-50 rounded text-sm border border-purple-200"
                          title="一键打开发布页并复制内容"
                          onClick={() => handleManualPublish(content.id)}
                        >
                          一键发布
                        </button>
                      )}
                      {content.status === 'draft' && (
                        <button className="p-2 text-slate-400 cursor-not-allowed" title="编辑（待实现）">
                          <Pencil size={18} />
                        </button>
                      )}
                      <button
                        className="p-2 text-red-500 hover:bg-red-50 rounded"
                        title="删除"
                        onClick={() => handleDelete(content.id)}
                      >
                        <Trash size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showEditor && (
        <ContentEditor
          accounts={accounts}
          onClose={() => setShowEditor(false)}
          onSave={() => {
            loadContents();
            setShowEditor(false);
          }}
        />
      )}
    </div>
  );
}

function ContentEditor({
  accounts,
  onClose,
  onSave,
}: {
  accounts: Account[];
  onClose: () => void;
  onSave: () => void;
}) {
  const [accountId, setAccountId] = useState(accounts[0]?.id || '');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [tags, setTags] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    if (!accountId) {
      setError('请先添加并选择账号');
      setSaving(false);
      return;
    }

    const res = await contentsApi.create({
      account_id: accountId,
      title,
      body,
      tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
    });

    if (res.error) {
      setError(res.error);
      setSaving(false);
      return;
    }

    onSave();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-xl font-semibold text-slate-900">新建内容</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">发布账号</label>
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              required
            >
              <option value="">请选择账号</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>{acc.nickname}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="吸引人的标题..."
              required
              maxLength={100}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">正文</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="分享你的内容..."
              required
              rows={8}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">标签（用逗号分隔）</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="种草，好物分享，必买"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-4 py-2 bg-sky-500 text-white rounded-lg hover:bg-sky-600 disabled:opacity-50"
            >
              {saving ? '保存中...' : '保存草稿'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
