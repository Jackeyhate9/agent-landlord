import { useState, type FormEvent } from 'react';
import { api } from '../api';
import { playSound, type SoundName } from '../audio';
import { Page } from '../components';
import { useBroadcast } from '../useBroadcast';

const CONTROLS = [['pause', '暂停'], ['resume', '恢复'], ['force-next-turn', '强制下一回合'], ['restart-hand', '重开本局'], ['start-next-match', '开始下一局'], ['house-in', '接入官方智能体'], ['house-out', '撤下官方智能体']] as const;
const SOUNDS: Array<[string, SoundName]> = [['发牌', 'deal'], ['炸弹', 'bomb'], ['王炸', 'rocket'], ['胜利', 'victory'], ['淘汰', 'elimination'], ['挑战者', 'challenger_enter'], ['悬念', 'suspense'], ['名人堂', 'hall_of_fame']];

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

  if (!token) return <Page className="admin-page"><main className="admin-login"><div className="lock-mark" aria-hidden="true">AL<span>访问</span></div><form onSubmit={login}><span>导演台认证</span><h1>导演台认证</h1><p>生产环境请在此入口外启用 Cloudflare Access。本地开发使用 ADMIN_PASSWORD。</p><label>管理员密码<input name="password" type="password" autoComplete="current-password" required autoFocus /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={busy === 'login'}>{busy ? '正在认证…' : '进入导演台'}</button></form></main></Page>;

  return <Page className="admin-page"><main className="admin-console">
    <header className="console-header"><div><span>导演台</span><h1>实时导演台</h1></div><div className="admin-live"><i className={socketState === 'open' ? 'online' : ''} /><b>{socketState === 'open' ? '实时' : '连接中'}</b><span>导演台不经过广播延迟</span></div><button className="ghost-button" onClick={() => { sessionStorage.removeItem('arena-admin-token'); setToken(''); }}>退出</button></header>
    {(message || error) && <div className={error ? 'form-error' : 'form-success'} role="status">{error || message}</div>}
    <section className="live-strip"><div><span>当前对局</span><b>{state.table.gameId}</b></div><div><span>状态</span><b>{state.table.status}</b></div><div><span>等候人数</span><b>{state.queue.length} 人</b></div><div><span>公共延迟</span><b>{state.table.delaySeconds} 秒</b></div><div><span>事件序号</span><b>{state.lastSequence}</b></div></section>
    <div className="console-grid">
      <section className="control-bank"><h2>比赛控制</h2><div className="button-bank">{CONTROLS.map(([name, label]) => <button key={name} className={name.includes('restart') ? 'danger-button' : ''} disabled={Boolean(busy)} onClick={() => command(name)}>{busy === name ? '执行中…' : label}</button>)}</div><h3>当前参赛智能体</h3><ul className="admin-agent-list">{state.table.agents.map((agent) => <li key={agent.id}><div><b>{agent.name}</b><span>{agent.status} · {agent.model}</span></div><button disabled={Boolean(busy)} onClick={() => command('set-live-pov', { agent_id: agent.id })}>设为直播视角</button><button className="danger-button" disabled={Boolean(busy)} onClick={() => command('disqualify-agent', { agent_id: agent.id, reason: 'admin console' })}>取消资格</button></li>)}</ul></section>
      <section className="soundboard"><h2>音效测试</h2><p>本地程序合成试听，同时发送公共音效事件供 OBS 牌桌触发。</p><div>{SOUNDS.map(([label, sound]) => <button key={sound} onClick={() => triggerSound(label, sound)}><i />{label}</button>)}</div></section>
      <section className="token-control"><h2>竞技筹码调整</h2><TokenForm busy={busy} onSubmit={adjustTokens} agents={state.table.agents.map(({ id, name }) => ({ id, name }))} /></section>
      <section className="queue-control"><h2>队列管理</h2><ul>{state.queue.slice(0, 5).map((entry) => <li key={entry.id}><span>#{entry.position}</span><b>{entry.name}</b><button className="danger-button" disabled={Boolean(busy)} onClick={() => command('remove-from-queue', { agent_id: entry.id, reason: 'admin console' })}>移出队列</button></li>)}</ul></section>
    </div>
  </main></Page>;
}

function TokenForm({ busy, onSubmit, agents }: { busy: string; onSubmit: (payload: Record<string, unknown>) => void; agents: Array<{ id: string; name: string }> }) {
  const [reason, setReason] = useState('');
  const [agentId, setAgentId] = useState(agents[0]?.id ?? '');
  return <form onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); const delta = Number(data.get('delta')); onSubmit({ agent_id: agentId, operation: delta >= 0 ? 'add' : 'subtract', amount: Math.abs(delta), reason }); }}><label>智能体<select value={agentId} onChange={(event) => setAgentId(event.target.value)}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label><label>变更量<input name="delta" type="number" step="100" required placeholder="+500 / -500" /></label><label>原因<input value={reason} onChange={(event) => setReason(event.target.value)} required minLength={3} maxLength={240} placeholder="写入审计日志" /></label><div><button disabled={Boolean(busy)}>提交调整</button><button type="button" className="danger-button" disabled={Boolean(busy) || reason.length < 3} onClick={() => onSubmit({ agent_id: agentId, operation: 'reset', amount: 0, reason })}>重置</button></div></form>;
}
