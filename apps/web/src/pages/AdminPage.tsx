import { useState, type FormEvent } from 'react';
import { api } from '../api';
import { playSound, type SoundName } from '../audio';
import { Page } from '../components';
import { useBroadcast } from '../useBroadcast';

const CONTROLS = [['pause', 'PAUSE'], ['resume', 'RESUME'], ['force-next-turn', 'FORCE NEXT TURN'], ['restart-hand', 'RESTART HAND'], ['start-next-match', 'START NEXT MATCH'], ['house-in', 'HOUSE AGENT IN'], ['house-out', 'HOUSE AGENT OUT']] as const;
const SOUNDS: Array<[string, SoundName]> = [['Deal', 'deal'], ['Bomb', 'bomb'], ['Rocket', 'rocket'], ['Victory', 'victory'], ['Elimination', 'elimination'], ['Challenger', 'challenger_enter'], ['Suspense', 'suspense'], ['Hall of Fame', 'hall_of_fame']];

export function AdminPage() {
  const { state, socketState } = useBroadcast();
  const [token, setToken] = useState(() => sessionStorage.getItem('arena-admin-token') ?? '');
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy('login'); setError('');
    const password = String(new FormData(event.currentTarget).get('password'));
    try { const response = await api.adminLogin(password); sessionStorage.setItem('arena-admin-token', response.token); setToken(response.token); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '认证失败。'); }
    finally { setBusy(''); }
  }

  async function command(name: string, payload: Record<string, unknown> = {}) {
    setBusy(name); setError(''); setMessage('');
    try { await api.adminCommand(token, name, payload); setMessage(`指令 ${name} 已写入审计日志并执行。`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '操作失败。'); }
    finally { setBusy(''); }
  }

  async function adjustTokens(payload: Record<string, unknown>) {
    setBusy('adjust-token'); setError(''); setMessage('');
    try { await api.adjustTokens(token, payload); setMessage('竞技筹码已调整，Ledger 与 audit_logs 已写入。'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '竞技筹码调整失败。'); }
    finally { setBusy(''); }
  }

  async function triggerSound(label: string, sound: SoundName) {
    playSound(sound);
    const publicName = sound === 'challenger_enter' ? 'challenger' : sound;
    try { await api.triggerSound(token, publicName); setMessage(`${label} 已本地试听并广播到公共事件流。`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '音效广播失败。'); }
  }

  if (!token) return <Page className="admin-page"><main className="admin-login"><div className="lock-mark" aria-hidden="true">AL<span>ACCESS</span></div><form onSubmit={login}><span>DIRECTOR AUTHENTICATION</span><h1>导演台认证</h1><p>生产环境请在此入口外启用 Cloudflare Access。本地开发使用 ADMIN_PASSWORD。</p><label>管理员密码<input name="password" type="password" autoComplete="current-password" required autoFocus /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={busy === 'login'}>{busy ? '正在认证…' : '进入导演台'}</button></form></main></Page>;

  return <Page className="admin-page"><main className="admin-console">
    <header className="console-header"><div><span>DIRECTOR CONSOLE</span><h1>实时导演台</h1></div><div className="admin-live"><i className={socketState === 'open' ? 'online' : ''} /><b>{socketState === 'open' ? 'REALTIME' : socketState.toUpperCase()}</b><span>Admin 不经过广播延迟</span></div><button className="ghost-button" onClick={() => { sessionStorage.removeItem('arena-admin-token'); setToken(''); }}>退出</button></header>
    {(message || error) && <div className={error ? 'form-error' : 'form-success'} role="status">{error || message}</div>}
    <section className="live-strip"><div><span>Current Game</span><b>{state.table.gameId}</b></div><div><span>状态</span><b>{state.table.status}</b></div><div><span>Queue</span><b>{state.queue.length} WAITING</b></div><div><span>Public Delay</span><b>{state.table.delaySeconds}s</b></div><div><span>Sequence</span><b>{state.lastSequence}</b></div></section>
    <div className="console-grid">
      <section className="control-bank"><h2>比赛控制</h2><div className="button-bank">{CONTROLS.map(([name, label]) => <button key={name} className={name.includes('restart') ? 'danger-button' : ''} disabled={Boolean(busy)} onClick={() => command(name)}>{busy === name ? '执行中…' : label}</button>)}</div><h3>当前参赛 Agent</h3><ul className="admin-agent-list">{state.table.agents.map((agent) => <li key={agent.id}><div><b>{agent.name}</b><span>{agent.status} · {agent.model}</span></div><button disabled={Boolean(busy)} onClick={() => command('set-live-pov', { agent_id: agent.id })}>SET LIVE POV</button><button className="danger-button" disabled={Boolean(busy)} onClick={() => command('disqualify-agent', { agent_id: agent.id, reason: 'admin console' })}>DISQUALIFY</button></li>)}</ul></section>
      <section className="soundboard"><h2>Sound Test</h2><p>本地程序合成试听，同时发送 SOUND 公共事件供 OBS 牌桌触发。</p><div>{SOUNDS.map(([label, sound]) => <button key={sound} onClick={() => triggerSound(label, sound)}><i />{label}</button>)}</div></section>
      <section className="token-control"><h2>竞技筹码调整</h2><TokenForm busy={busy} onSubmit={adjustTokens} agents={state.table.agents.map(({ id, name }) => ({ id, name }))} /></section>
      <section className="queue-control"><h2>队列管理</h2><ul>{state.queue.slice(0, 5).map((entry) => <li key={entry.id}><span>#{entry.position}</span><b>{entry.name}</b><button className="danger-button" disabled={Boolean(busy)} onClick={() => command('remove-from-queue', { agent_id: entry.id, reason: 'admin console' })}>REMOVE</button></li>)}</ul></section>
    </div>
  </main></Page>;
}

function TokenForm({ busy, onSubmit, agents }: { busy: string; onSubmit: (payload: Record<string, unknown>) => void; agents: Array<{ id: string; name: string }> }) {
  const [reason, setReason] = useState('');
  const [agentId, setAgentId] = useState(agents[0]?.id ?? '');
  return <form onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); const delta = Number(data.get('delta')); onSubmit({ agent_id: agentId, operation: delta >= 0 ? 'add' : 'subtract', amount: Math.abs(delta), reason }); }}><label>Agent<select value={agentId} onChange={(event) => setAgentId(event.target.value)}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label><label>变更量<input name="delta" type="number" step="100" required placeholder="+500 / -500" /></label><label>原因<input value={reason} onChange={(event) => setReason(event.target.value)} required minLength={3} maxLength={240} placeholder="写入 audit_logs" /></label><div><button disabled={Boolean(busy)}>提交调整</button><button type="button" className="danger-button" disabled={Boolean(busy) || reason.length < 3} onClick={() => onSubmit({ agent_id: agentId, operation: 'reset', amount: 0, reason })}>RESET</button></div></form>;
}
