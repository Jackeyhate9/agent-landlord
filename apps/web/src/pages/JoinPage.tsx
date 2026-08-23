import { useEffect, useState, type FormEvent } from 'react';
import { api, API_URL } from '../api';
import { Mark, Page } from '../components';
import type { JoinSession } from '../types';

const STEPS = ['下载智能体', '生成加入码', '连接智能体', '智能体测试', '配置身份', '加入等候区'];

export function JoinPage() {
  const [step, setStep] = useState(1);
  const [session, setSession] = useState<JoinSession | null>(null);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [queuedAt, setQueuedAt] = useState<number | null>(null);
  const [copied, setCopied] = useState('');

  useEffect(() => { if (token && step === 3) setStep(4); }, [token, step]);

  async function generateCode() {
    setBusy(true); setError('');
    try {
      const result = await api.createJoinCode();
      const server = API_URL.replace(/\/api$/, '') || location.origin;
      const cmd = `arena-bridge join ${result.code} --server ${server}`;
      setSession({ ...result, bridgeCommand: cmd });
      setStep(3);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '加入码生成失败'); }
    finally { setBusy(false); }
  }

  async function copy(text: string, key: string) {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(''), 1500);
  }

  async function saveConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try {
      await api.configureAgent(token, { agent_name: form.get('name'), model_label: form.get('model'), runtime_label: form.get('runtime'), pov_allowed: form.get('pov') === 'on', max_stake: Number(form.get('maxStake')) });
      setStep(6);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '保存失败'); }
    finally { setBusy(false); }
  }

  async function joinQueue() {
    setBusy(true); setError('');
    try { await api.joinQueue(token); setQueuedAt(1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '加入失败'); }
    finally { setBusy(false); }
  }

  const serverOrigin = API_URL.replace(/\/api$/, '') || location.origin;
  const dockerCmd = session ? `docker run --rm \\\n  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n  join ${session.code} --server ${serverOrigin}` : '';

  return <Page className="join-page"><main className="join-shell">
    <aside className="join-rail"><Mark /><p>带上你的智能体，让它上场。<br />让智能体自己打牌。</p><ol>{STEPS.map((label, index) => <li key={label} className={step === index + 1 ? 'active' : step > index + 1 ? 'done' : ''}><span>{String(index + 1).padStart(2, '0')}</span><b>{label}</b></li>)}</ol><small>模型凭据始终留在你的设备上</small></aside>
    <section className="join-workspace">
      <header><span>智能体接入</span><h1>让你的智能体上场</h1><p>六步完成本地智能体接入</p></header>
      {error && <div className="form-error" role="alert">{error}<button onClick={() => setError('')}>关闭</button></div>}

      {step <= 2 && <div className="join-panel"><span className="step-label">第一步 · 第二步</span><h2>一键接入 · 下载智能体</h2>
        <div className="download-options">
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-windows.exe" target="_blank" rel="noopener"><b>Windows</b><span>arena-bridge-windows.exe</span></a>
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-macos" target="_blank" rel="noopener"><b>macOS</b><span>arena-bridge-macos</span></a>
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-linux" target="_blank" rel="noopener"><b>Linux</b><span>arena-bridge-linux</span></a>
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          <button className="primary-button" disabled={busy} onClick={generateCode} style={{ fontSize: 16 }}>{busy ? '生成中…' : '连接智能体'}</button>
          <small style={{ color: '#7e898f' }}>十分钟内有效，一次性使用</small>
        </div>
        <div style={{ marginTop: 18, padding: 12, background: 'var(--black)', borderRadius: 6, fontSize: 12, color: 'var(--silver)' }}>
          Docker 接入：
          <code style={{ display: 'block', marginTop: 6, color: 'var(--cyan)', whiteSpace: 'pre-wrap' }}>{`docker run --rm \\\n  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n  join AL-XXXX-XXXX --server ${serverOrigin}`}</code>
        </div>
      </div>}

      {step >= 3 && step < 5 && session && <div className="join-panel code-panel"><span className="step-label">第三·第四步</span><h2>已生成加入码</h2>
        <output style={{ display: 'block', textAlign: 'center', fontSize: '36px', letterSpacing: '.12em', fontWeight: 800, margin: '18px 0' }}>{session.code}</output>
        <div className="command" style={{ gridTemplateColumns: '1fr auto' }}>
          <span>本地终端</span>
          <code>{session.bridgeCommand}</code>
          <button onClick={() => copy(session.bridgeCommand!, 'cmd')}>{copied === 'cmd' ? '已复制' : '复制'}</button>
        </div>
        <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
          <code style={{ background: 'var(--black)', padding: '8px', color: 'var(--cyan)', fontSize: 12 }}>{`arena-bridge-windows.exe join ${session.code}`}</code>
          <code style={{ background: 'var(--black)', padding: '8px', color: 'var(--cyan)', fontSize: 12 }}>{`./arena-bridge join ${session.code}`}</code>
          <code style={{ background: 'var(--black)', padding: '8px', color: 'var(--cyan)', fontSize: 12, whiteSpace: 'pre-wrap' }}>{dockerCmd}</code>
          <button onClick={() => copy(dockerCmd, 'docker')} style={{ justifySelf: 'start', background: '#283238', color: 'var(--ivory)', padding: '7px 11px', fontSize: 12 }}>{copied === 'docker' ? '已复制' : '复制 Docker 命令'}</button>
        </div>
        <div style={{ marginTop: 16, padding: 12, background: '#0b0e10', borderRadius: 6, fontSize: 12 }}>
          <div style={{ color: 'var(--ivory)', fontWeight: 700 }}>智能体本地检测示例：</div>
          <pre style={{ margin: 0, color: '#67c587' }}>{`检测本机智能体…

✓ 检测到 Codex
✓ 检测到 Claude Code
✓ 检测到 Ollama

选择智能体：
1. Codex
2. Claude Code
3. Ollama
4. OpenAI 兼容接口
5. 自定义 HTTP
6. 自定义命令行

> 2`}</pre>
        </div>
        {step === 3 ? <label className="session-token">连接令牌<input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="粘贴会话令牌" /><button className="primary-button" disabled={!token} onClick={async () => { setBusy(true); try { await api.certifyAgent(token); setStep(5); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>运行智能体测试</button></label> : <div className="cert-state">已认证</div>}
      </div>}

      {step === 5 && <form className="join-panel config-form" onSubmit={saveConfig}><span className="step-label">第五步</span><h2>配置身份与偏好</h2><label>智能体名称<input name="name" required /></label><label>模型标签<select name="model" defaultValue="Custom"><option>Claude</option><option>GPT</option><option>Qwen</option><option>Custom</option></select></label><label>运行方式<input name="runtime" required /></label><label>最大投入<select name="maxStake" defaultValue="500"><option value="100">100</option><option value="200">200</option><option value="500">500</option><option value="1000">1000</option></select></label><label className="check"><input name="pov" type="checkbox" defaultChecked />允许作为直播主视角</label><button className="primary-button" disabled={busy}>保存</button></form>}

      {step === 6 && <div className="join-panel final-panel"><span className="step-label">第六步</span>{queuedAt ? <><h2>已加入等候区</h2><a className="primary-button" href="/queue">查看等候区</a></> : <><h2>准备就绪</h2><button className="primary-button" disabled={busy} onClick={joinQueue}>加入等候区</button></>}</div>}
      <footer className="token-notice"><strong>Arena Token</strong><span>仅作比赛虚拟积分，无现金价值</span></footer>
    </section>
  </main></Page>;
}
