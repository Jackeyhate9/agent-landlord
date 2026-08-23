import { useEffect, useMemo, useState, type PropsWithChildren } from 'react';
import { playSound, soundForEvent } from './audio';
import type { AgentView, GameEventType, SocketState } from './types';

export const formatAt = (value: number) => `${new Intl.NumberFormat('zh-CN').format(value)} AT`;

export function Mark({ compact = false }: { compact?: boolean }) {
  return <span className="brand-mark" aria-label="Agent Landlord"><svg viewBox="0 0 42 42" aria-hidden="true"><path d="M6 32 16 7h10l10 25h-8l-2-7H15l-2 7H6Zm11-14h7l-3-8-4 8Z"/><path d="M30 7h6v25h-6z"/></svg>{!compact && <span><b>AGENT LANDLORD</b><small>智能体斗地主竞技场</small></span>}</span>;
}

export function Nav() {
  const current = location.pathname;
  const links = [['/table', '牌桌'], ['/queue', '等候区'], ['/hall', '名人堂'], ['/join', '接入'], ['/admin', '导演台'], ['/demo', '演示']];
  return <header className="topbar"><Mark /><nav aria-label="主导航">{links.map(([href, label]) => <a key={href} href={href} aria-current={current === href ? 'page' : undefined}>{label}</a>)}</nav><span className="version">竞技场 / 第一季</span></header>;
}

export function Page({ children, className = '' }: PropsWithChildren<{ className?: string }>) {
  const obs = new URLSearchParams(location.search).get('obs') === '1';
  return <div className={`app-shell ${obs ? 'obs-mode' : ''} ${className}`}>{!obs && <Nav />}{children}</div>;
}

export function SocketBadge({ state, delay = true }: { state: SocketState; delay?: boolean }) {
  const label = { open: '公共频道已连接', connecting: '正在连接', reconnecting: '正在恢复', closed: '连接关闭' }[state];
  return <div className="connection-rail" role="status"><span className={`dot ${state}`} />{label}{delay && <><i />公共画面延迟 30 秒</>}</div>;
}

export function Avatar({ agent, large = false }: { agent: Pick<AgentView, 'name' | 'avatarUrl' | 'isHouse'>; large?: boolean }) {
  const initials = [...agent.name].slice(0, 2).join('').toUpperCase();
  return <span className={`avatar ${large ? 'large' : ''} ${agent.isHouse ? 'house' : ''}`} aria-hidden="true">{agent.avatarUrl ? <img src={agent.avatarUrl} alt="" /> : initials}</span>;
}

function parseCard(card: string) {
  if (card === 'BJ') return { rank: 'JOKER', suit: '小', red: false };
  if (card === 'RJ') return { rank: 'JOKER', suit: '大', red: true };
  const suit = card.slice(-1);
  return { rank: card.slice(0, -1), suit, red: suit === '♥' || suit === '♦' };
}

export function PlayingCard({ card, hidden = false, small = false }: { card: string; hidden?: boolean; small?: boolean }) {
  if (hidden) return <span className={`playing-card back ${small ? 'small' : ''}`} aria-label="暗牌"><svg viewBox="0 0 76 108" aria-hidden="true"><rect x="2" y="2" width="72" height="104" rx="7"/><path d="M18 31 30 15h16l12 16-20 35-20-35Z"/><text x="38" y="90">AL</text></svg></span>;
  const data = parseCard(card);
  return <span className={`playing-card ${data.red ? 'red' : ''} ${small ? 'small' : ''}`} aria-label={card}><svg viewBox="0 0 76 108" aria-hidden="true"><rect x="1" y="1" width="74" height="106" rx="8"/><text className="rank" x="9" y="24">{data.rank}</text><text className="suit" x="10" y="43">{data.suit}</text><text className="center" x="38" y="75">{data.suit}</text></svg></span>;
}

const EVENT_COPY: Record<GameEventType, string> = {
  DEAL: '发牌 / DEAL', PLAY: '出牌 / PLAY', PASS: '不出 / PASS', BOMB: '炸弹 / BOMB', ROCKET: '王炸 / ROCKET', SPRING: '春天 / SPRING', WIN: '胜利 / WIN', LOSE: '落败 / LOSE', ELIMINATION: '归零淘汰', NEXT_CHALLENGER: '下一位挑战者', WIN_STREAK: '连胜继续', HALL_OF_FAME: '进入名人堂', LANDLORD: '地主确认',
};

export function EventSlate({ type, nonce }: { type?: GameEventType; nonce?: string | number }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!type) return;
    setVisible(true);
    const sound = soundForEvent(type);
    if (sound) playSound(sound);
    const timer = window.setTimeout(() => setVisible(false), type === 'WIN' || type === 'ELIMINATION' ? 4200 : 2200);
    return () => window.clearTimeout(timer);
  }, [type, nonce]);
  if (!type || !visible) return null;
  return <div className={`event-slate event-${type.toLowerCase().replace('_', '-')}`} role="status" aria-live="assertive"><span>{EVENT_COPY[type]}</span><i aria-hidden="true" /></div>;
}

export function AgentPlate({ agent, active = false, orientation = 'horizontal' }: { agent: AgentView; active?: boolean; orientation?: 'horizontal' | 'vertical' }) {
  const role = agent.role === 'landlord' ? '地主' : '农民';
  return <article className={`agent-plate ${active ? 'active' : ''} ${orientation} ${agent.status.toLowerCase()}`} aria-label={`${agent.name}，${role}，${agent.status}`}>
    <Avatar agent={agent} large />
    <div className="agent-copy"><div className="agent-name">{agent.name}{agent.isHouse && <span className="house-tag">官方智能体</span>}</div><div className="model-badge">{agent.model}</div></div>
    <div className="agent-metrics"><span className={`role role-${agent.role}`}>{role}</span><strong>{formatAt(agent.balance)}</strong><small>{agent.remaining} 张</small></div>
    <div className="agent-status"><span>{agent.status}</span>{active && <b>当前回合</b>}</div>
  </article>;
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return <div className="empty-state"><Mark compact /><strong>{title}</strong><p>{body}</p></div>;
}

export function useEventKey(type?: string) {
  return useMemo(() => `${type ?? 'none'}-${Date.now()}`, [type]);
}
