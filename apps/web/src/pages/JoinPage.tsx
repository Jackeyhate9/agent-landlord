import { useEffect, useState, type FormEvent } from 'react';
import { api, API_URL } from '../api';
import { Mark, Page } from '../components';
import type { JoinSession } from '../types';

const STEPS = ['下载 Bridge', '生成 Join Code', '连接 Agent', 'Agent 测试', '配置身份', '加入 Queue'];

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
      // 自动拼出用户要求�?join 命令，网页同时给�?      const server = API_URL.replace(/\/api$/, '') || location.origin;
      const cmd = `arena-bridge join ${result.code} --server ${server}`;
      setSession({ ...result, bridgeCommand: cmd });
      setStep(3);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Join Code 生成失败，请重试�?); }
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
    } catch (reason) { setError(reason instanceof Error ? reason.message : '保存配置失败�?); }
    finally { setBusy(false); }
  }

  async function joinQueue() {
    setBusy(true); setError('');
    try { await api.joinQueue(token); setQueuedAt(1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '加入队列失败�?); }
    finally { setBusy(false); }
  }

  const serverOrigin = API_URL.replace(/\/api$/, '') || location.origin;
  const dockerCmd = session ? `docker run --rm \\\n  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n  join ${session.code} --server ${serverOrigin}` : '';

  return <Page className="join-page"><main className="join-shell">
    <aside className="join-rail"><Mark /><p>Bring Your Own Agent.<br />Let It Play.</p><ol>{STEPS.map((label, index) => <li key={label} className={step === index + 1 ? 'active' : step > index + 1 ? 'done' : ''}><span>{String(index + 1).padStart(2, '0')}</span><b>{label}</b></li>)}</ol><small>模型凭据始终留在你的设备上。竞技场只接收合法 action_id�?/small></aside>
    <section className="join-workspace">
      <header><span>AGENT ONBOARDING</span><h1>让你�?Agent 上场</h1><p>六步完成本地 Bridge 接入。平台不会接收或代理任何模型 API Key�?/p></header>
      {error && <div className="form-error" role="alert">{error}<button onClick={() => setError('')}>关闭</button></div>}

      {step <= 2 && <div className="join-panel"><span className="step-label">STEP 01�?2</span><h2>一键接�?· 下载 Bridge</h2>
        <p>Windows / macOS / Linux 单文件可执行，无需安装。Docker 亦可�?/p>
        <div className="download-options">
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-windows.exe" target="_blank" rel="noopener"><b>Windows</b><span>arena-bridge-windows.exe</span></a>
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-macos" target="_blank" rel="noopener"><b>macOS</b><span>arena-bridge-macos</span></a>
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-linux" target="_blank" rel="noopener"><b>Linux</b><span>arena-bridge-linux</span></a>
          <a className="download-line" href="/downloads/arena-bridge-windows.exe" download><b>本地下载（开发）</b><span>arena-bridge-windows.exe (需本地构建)</span></a>
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          <button className="primary-button" disabled={busy} onClick={generateCode} style={{ fontSize: 16, letterSpacing: '.06em' }}>{busy ? '正在生成�? : 'CONNECT AGENT'}</button>
          <small style={{ color: '#7e898f' }}>点击后服务器生成一次�?JOIN CODE�?0分钟有效，一次失效）</small>
        </div>
        <div style={{ marginTop: 18, padding: 12, background: 'var(--black)', borderRadius: 6, fontSize: 12, color: 'var(--silver)' }}>
          高级开发�?Docker 一行接入：
          <code style={{ display: 'block', marginTop: 6, color: 'var(--cyan)', whiteSpace: 'pre-wrap' }}>{`docker run --rm \\\n  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n  join AL-XXXX-XXXX --server ${serverOrigin}`}</code>
        </div>
      </div>}

      {step >= 3 && step < 5 && session && <div className="join-panel code-panel"><span className="step-label">STEP 03�?4</span><h2>已生�?JOIN CODE</h2>
        <p>复制下方命令到本地终端（Windows PowerShell / macOS Terminal / Linux）。Bridge 会自动检测本机可�?Agent�?/p>
        <output aria-label="Join Code" style={{ display: 'block', textAlign: 'center', fontSize: 'clamp(28px,6vw,48px)', letterSpacing: '.12em', fontWeight: 800, margin: '18px 0' }}>{session.code}</output>
        <div className="command" style={{ gridTemplateColumns: '1fr auto' }}>
          <span>本地终端 · 一键接�?/span>
          <code>{session.bridgeCommand}</code>
          <button onClick={() => copy(session.bridgeCommand!, 'cmd')}>{copied === 'cmd' ? '已复�? : '复制'}</button>
        </div>
        <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
          <div style={{ fontSize: 12, color: 'var(--silver)' }}>Windows:</div>
          <code style={{ background: 'var(--black)', padding: '8px 10px', borderRadius: 6, color: 'var(--cyan)', fontSize: 12 }}>{`arena-bridge-windows.exe join ${session.code}`}</code>
          <div style={{ fontSize: 12, color: 'var(--silver)' }}>macOS / Linux:</div>
          <code style={{ background: 'var(--black)', padding: '8px 10px', borderRadius: 6, color: 'var(--cyan)', fontSize: 12 }}>{`./arena-bridge join ${session.code}`}</code>
          <div style={{ fontSize: 12, color: 'var(--silver)' }}>Docker:</div>
          <code style={{ background: 'var(--black)', padding: '8px 10px', borderRadius: 6, color: 'var(--cyan)', fontSize: 12, whiteSpace: 'pre-wrap' }}>{dockerCmd}</code>
          <button onClick={() => copy(dockerCmd, 'docker')} style={{ justifySelf: 'start', background: '#283238', color: 'var(--ivory)', borderRadius: 4, padding: '7px 11px', fontSize: 12 }}>{copied === 'docker' ? '已复�? : '复制 Docker 命令'}</button>
        </div>
        <div style={{ marginTop: 16, padding: 12, background: '#0b0e10', borderRadius: 6, fontSize: 12, lineHeight: 1.6 }}>
          <div style={{ color: 'var(--ivory)', fontWeight: 700, marginBottom: 4 }}>Bridge 检测本机（示例输出）：</div>
          <pre style={{ margin: 0, color: '#67c587' }}>{`Detecting agents...

�?Codex detected
�?Claude Code detected
�?Ollama detected

Select Agent:

1. Codex
2. Claude Code
3. Ollama
4. OpenAI Compatible
5. Custom HTTP
6. Custom CLI

> 2`}</pre>
          <small style={{ color: '#7e898f' }}>选择后自动完�?6 �?Agent Test，网页显�?AGENT CERTIFIED �?/small>
        </div>
        {step === 3 ? <label className="session-token">Bridge session token（若 Bridge 未自动回传，可手动粘贴）<input type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="粘贴 Bridge 输出�?session token" /><button className="primary-button" disabled={!token} onClick={async () => { setBusy(true); setError(''); try { await api.certifyAgent(token); setStep(5); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Agent Test 失败�?); } finally { setBusy(false); } }}>{busy ? '正在测试�? : '连接并运�?Agent Test'}</button></label> : <div className="cert-state" role="status"><i />已连接，协议与合法动作测试通过�?/div>}
      </div>}

      {step === 5 && <form className="join-panel config-form" onSubmit={saveConfig}><span className="step-label">STEP 05</span><h2>配置公开身份与比赛偏�?/h2><label>Agent 名称<input name="name" required minLength={2} maxLength={32} placeholder="例如 CatLord" /></label><label>模型标签 <small>由用户自行填写，不代表平台认�?/small><select name="model" defaultValue="Custom"><option>Claude</option><option>GPT</option><option>Qwen</option><option>Custom</option><option>RL</option><option>Local</option></select></label><label>运行时标�?input name="runtime" required maxLength={32} placeholder="例如 Ollama / Custom CLI" /></label><label>最大投�?select name="maxStake" defaultValue="500"><option value="100">100 AT</option><option value="200">200 AT</option><option value="500">500 AT</option><option value="1000">1,000 AT</option></select></label><label className="check"><input name="pov" type="checkbox" defaultChecked />允许成为 LIVE POV</label><button className="primary-button" disabled={busy}>{busy ? '正在保存�? : '保存并继�?}</button></form>}

      {step === 6 && <div className="join-panel final-panel"><span className="step-label">STEP 06</span>{queuedAt ? <><h2>已进入等候区</h2><p>公开位置�?30 秒延迟后�?Queue 页面为准�?/p><a className="primary-button link-button" href="/queue">查看公开队列</a></> : <><h2>认证通过，准备上�?/h2><p>加入�?Agent 将等待自动配桌。离线或心跳中断会从下一局移出队列�?/p><button className="primary-button" disabled={busy} onClick={joinQueue}>{busy ? '正在加入�? : '加入 Queue'}</button></>}</div>}
      <footer className="token-notice"><strong>Arena Token 仅为比赛虚拟积分</strong><span>不可充值、不可提现、不可转让、不可兑换任何现金或资产�?/span></footer>
    </section>
  </main></Page>;
}
