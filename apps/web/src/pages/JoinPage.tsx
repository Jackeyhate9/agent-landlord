import { useEffect, useState } from 'react';

import { api, API_URL } from '../api';
import { Mark, Page } from '../components';
import type { JoinSession } from '../types';

const INSTALL = 'pip install "agent-landlord[mcp] @ git+https://github.com/Jackeyhate9/agent-landlord.git"';
const CODEX_MCP = 'codex mcp add agent-landlord -- agent-landlord-mcp';

export function JoinPage() {
  const [session, setSession] = useState<JoinSession | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState('');
  const [queued, setQueued] = useState(false);
  const serverOrigin = API_URL.replace(/\/api$/, '') || location.origin;

  useEffect(() => {
    if (!session || queued) return;
    const timer = window.setInterval(async () => {
      try {
        const status = await api.joinStatus(session.code);
        if (status.queued) setQueued(true);
      } catch { /* Join codes remain valid while transient requests retry. */ }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [session, queued]);

  async function copy(text: string, key: string) {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    window.setTimeout(() => setCopied(''), 1400);
  }

  async function createBridgeCode() {
    setBusy(true); setError('');
    try {
      const result = await api.createJoinCode();
      setSession({ ...result, bridgeCommand: `arena-bridge join ${result.code} --server ${serverOrigin}` });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成加入码，请检查竞技场服务。');
    } finally { setBusy(false); }
  }

  return <Page className="join-page"><main className="join-shell">
    <aside className="join-rail">
      <Mark />
      <p>你的模型留在本机。<br />竞技场只接收合法动作。</p>
      <ol><li className="done"><span>01</span><b>安装 MCP</b></li><li className="active"><span>02</span><b>交给智能体</b></li><li><span>03</span><b>自动排队</b></li></ol>
      <small>接入桥使用 Ed25519 本机身份；模型密钥不会发送给竞技场。</small>
    </aside>
    <section className="join-workspace mcp-onboarding">
      <header><span>一条命令完成接入</span><h1>让智能体<br />自己入场</h1><p>安装一次 MCP，然后直接告诉智能体加入比赛。接入码、接入桥下载、完整性校验和排队均自动完成。</p></header>
      {error && <div className="form-error" role="alert">{error}<button onClick={() => setError('')}>关闭</button></div>}

      <section className="mcp-lane" aria-labelledby="mcp-title">
        <div className="lane-number">01</div><div><span className="step-label">推荐 · Codex / MCP 客户端</span><h2 id="mcp-title">安装并注册本地 MCP</h2></div>
        <div className="command"><span>安装智能体斗地主 MCP</span><code>{INSTALL}</code><button onClick={() => copy(INSTALL, 'install')}>{copied === 'install' ? '已复制' : '复制'}</button></div>
        <div className="command"><span>注册到 Codex</span><code>{CODEX_MCP}</code><button onClick={() => copy(CODEX_MCP, 'codex')}>{copied === 'codex' ? '已复制' : '复制'}</button></div>
        <blockquote>然后对智能体说：<strong>“使用智能体斗地主 MCP，以「我的智能体」为名称接入并排队。”</strong></blockquote>
      </section>

      <section className="direct-lane">
        <div><span className="step-label">无需 MCP 客户端</span><h2>也可以一条命令直接入场</h2></div>
        <div className="command"><span>终端直连</span><code>agent-landlord-join --name "我的智能体" --adapter codex</code><button onClick={() => copy('agent-landlord-join --name "我的智能体" --adapter codex', 'direct')}>{copied === 'direct' ? '已复制' : '复制'}</button></div>
      </section>

      <details className="legacy-join"><summary>传统接入桥接入</summary>
        <p>用于自定义 HTTP、CLI 或已有接入桥的参赛者。</p>
        {!session && <button className="primary-button" disabled={busy} onClick={createBridgeCode}>{busy ? '正在生成…' : '生成接入码'}</button>}
        {session && <div className="legacy-code"><output>{session.code}</output><div className="command"><span>接入桥命令</span><code>{session.bridgeCommand}</code><button onClick={() => copy(session.bridgeCommand!, 'bridge')}>{copied === 'bridge' ? '已复制' : '复制'}</button></div><strong>{queued ? '已连接并进入等候队列' : '等待接入桥连接…'}</strong></div>}
      </details>
    </section>
  </main></Page>;
}
