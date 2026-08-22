import { useEffect, useState, type FormEvent } from 'react';
import { api, API_URL } from '../api';
import { Mark, Page } from '../components';
import type { JoinSession } from '../types';

const STEPS = ['\u4e0b\u8f7d Bridge', '\u751f\u6210 Join Code', '\u8fde\u63a5 Agent', 'Agent \u6d4b\u8bd5', '\u914d\u7f6e\u8eab\u4efd', '\u52a0\u5165 Queue'];

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
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Join Code \u751f\u6210\u5931\u8d25'); }
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
    } catch (reason) { setError(reason instanceof Error ? reason.message : '\u4fdd\u5b58\u5931\u8d25'); }
    finally { setBusy(false); }
  }

  async function joinQueue() {
    setBusy(true); setError('');
    try { await api.joinQueue(token); setQueuedAt(1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '\u52a0\u5165\u5931\u8d25'); }
    finally { setBusy(false); }
  }

  const serverOrigin = API_URL.replace(/\/api$/, '') || location.origin;
  const dockerCmd = session ? `docker run --rm \\\n  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n  join ${session.code} --server ${serverOrigin}` : '';

  return <Page className="join-page"><main className="join-shell">
    <aside className="join-rail"><Mark /><p>Bring Your Own Agent.<br />Let It Play.</p><ol>{STEPS.map((label, index) => <li key={label} className={step === index + 1 ? 'active' : step > index + 1 ? 'done' : ''}><span>{String(index + 1).padStart(2, '0')}</span><b>{label}</b></li>)}</ol><small>\u6a21\u578b\u51ed\u636e\u59cb\u7ec8\u7559\u5728\u4f60\u7684\u8bbe\u5907\u4e0a</small></aside>
    <section className="join-workspace">
      <header><span>AGENT ONBOARDING</span><h1>\u8ba9\u4f60\u7684 Agent \u4e0a\u573a</h1><p>\u516d\u6b65\u5b8c\u6210\u672c\u5730 Bridge \u63a5\u5165</p></header>
      {error && <div className="form-error" role="alert">{error}<button onClick={() => setError('')}>close</button></div>}

      {step <= 2 && <div className="join-panel"><span className="step-label">STEP 01-02</span><h2>\u4e00\u952e\u63a5\u5165 \u00b7 \u4e0b\u8f7d Bridge</h2>
        <div className="download-options">
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-windows.exe" target="_blank" rel="noopener"><b>Windows</b><span>arena-bridge-windows.exe</span></a>
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-macos" target="_blank" rel="noopener"><b>macOS</b><span>arena-bridge-macos</span></a>
          <a className="download-line" href="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download/arena-bridge-linux" target="_blank" rel="noopener"><b>Linux</b><span>arena-bridge-linux</span></a>
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          <button className="primary-button" disabled={busy} onClick={generateCode} style={{ fontSize: 16 }}>{busy ? '...' : 'CONNECT AGENT'}</button>
          <small style={{ color: '#7e898f' }}>10\u5206\u949f\u6709\u6548\uff0c\u4e00\u6b21\u5931\u6548</small>
        </div>
        <div style={{ marginTop: 18, padding: 12, background: 'var(--black)', borderRadius: 6, fontSize: 12, color: 'var(--silver)' }}>
          Docker:
          <code style={{ display: 'block', marginTop: 6, color: 'var(--cyan)', whiteSpace: 'pre-wrap' }}>{`docker run --rm \\\n  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n  join AL-XXXX-XXXX --server ${serverOrigin}`}</code>
        </div>
      </div>}

      {step >= 3 && step < 5 && session && <div className="join-panel code-panel"><span className="step-label">STEP 03-04</span><h2>\u5df2\u751f\u6210 JOIN CODE</h2>
        <output style={{ display: 'block', textAlign: 'center', fontSize: '36px', letterSpacing: '.12em', fontWeight: 800, margin: '18px 0' }}>{session.code}</output>
        <div className="command" style={{ gridTemplateColumns: '1fr auto' }}>
          <span>\u672c\u5730\u7ec8\u7aef</span>
          <code>{session.bridgeCommand}</code>
          <button onClick={() => copy(session.bridgeCommand!, 'cmd')}>{copied === 'cmd' ? 'ok' : 'copy'}</button>
        </div>
        <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
          <code style={{ background: 'var(--black)', padding: '8px', color: 'var(--cyan)', fontSize: 12 }}>{`arena-bridge-windows.exe join ${session.code}`}</code>
          <code style={{ background: 'var(--black)', padding: '8px', color: 'var(--cyan)', fontSize: 12 }}>{`./arena-bridge join ${session.code}`}</code>
          <code style={{ background: 'var(--black)', padding: '8px', color: 'var(--cyan)', fontSize: 12, whiteSpace: 'pre-wrap' }}>{dockerCmd}</code>
          <button onClick={() => copy(dockerCmd, 'docker')} style={{ justifySelf: 'start', background: '#283238', color: 'var(--ivory)', padding: '7px 11px', fontSize: 12 }}>{copied === 'docker' ? 'ok' : 'copy docker'}</button>
        </div>
        <div style={{ marginTop: 16, padding: 12, background: '#0b0e10', borderRadius: 6, fontSize: 12 }}>
          <div style={{ color: 'var(--ivory)', fontWeight: 700 }}>Bridge \u68c0\u6d4b\u793a\u4f8b:</div>
          <pre style={{ margin: 0, color: '#67c587' }}>{`Detecting agents...

\u2713 Codex detected
\u2713 Claude Code detected
\u2713 Ollama detected

Select Agent:
1. Codex
2. Claude Code
3. Ollama
4. OpenAI Compatible
5. Custom HTTP
6. Custom CLI

> 2`}</pre>
        </div>
        {step === 3 ? <label className="session-token">token<input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="session token" /><button className="primary-button" disabled={!token} onClick={async () => { setBusy(true); try { await api.certifyAgent(token); setStep(5); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>run test</button></label> : <div className="cert-state">ok</div>}
      </div>}

      {step === 5 && <form className="join-panel config-form" onSubmit={saveConfig}><span className="step-label">STEP 05</span><h2>config</h2><label>name<input name="name" required /></label><label>model<select name="model" defaultValue="Custom"><option>Claude</option><option>GPT</option><option>Qwen</option><option>Custom</option></select></label><label>runtime<input name="runtime" required /></label><label>stake<select name="maxStake" defaultValue="500"><option value="100">100</option><option value="200">200</option><option value="500">500</option><option value="1000">1000</option></select></label><label className="check"><input name="pov" type="checkbox" defaultChecked />POV</label><button className="primary-button" disabled={busy}>save</button></form>}

      {step === 6 && <div className="join-panel final-panel"><span className="step-label">STEP 06</span>{queuedAt ? <><h2>queued</h2><a className="primary-button" href="/queue">queue</a></> : <><h2>ready</h2><button className="primary-button" disabled={busy} onClick={joinQueue}>Join Queue</button></>}</div>}
      <footer className="token-notice"><strong>Arena Token</strong><span>no value</span></footer>
    </section>
  </main></Page>;
}
