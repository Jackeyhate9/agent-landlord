import { MAX_MULTIPLIER } from '../../../../packages/protocol/src/constants.js';

import { Avatar, EventSlate, Page, PlayingCard, SocketBadge, formatAt } from '../components';
import type { AgentView, QueueEntry, TableState } from '../types';
import { useBroadcast } from '../useBroadcast';

type SeatEntry = AgentView | QueueEntry;

const TABLE_STATUS: Record<TableState['status'], string> = {
  WAITING: '等待开局',
  BIDDING: '叫地主',
  PLAYING: '对局中',
  SETTLING: '结算中',
  FINISHED: '本局结束',
  PAUSED: '比赛暂停',
};

const AGENT_STATUS: Record<AgentView['status'], string> = {
  READY: '准备就绪',
  THINKING: '思考中',
  PLAYING: '对局中',
  PASS: '本轮不出',
  TIMEOUT: '行动超时',
  DISCONNECTED: '连接中断',
  HOUSE: '官方智能体',
};

function isPlayingAgent(entry: SeatEntry): entry is AgentView {
  return 'remaining' in entry;
}

function TableSeat({ entry, position, active = false, pov = false }: { entry?: SeatEntry; position: string; active?: boolean; pov?: boolean }) {
  if (!entry) return <article className={`orbit-seat ${position} pending`} aria-label="席位待定，等待智能体接入">
    <span className="pending-avatar" aria-hidden="true">?</span>
    <div className="orbit-seat-copy"><strong>待定</strong><small>等待智能体接入</small></div>
    <span className="seat-state">等待中</span>
  </article>;

  const playing = isPlayingAgent(entry);
  const role = playing ? (entry.role === 'landlord' ? '地主' : '农民') : '候场';
  const state = active ? '当前行动' : playing ? AGENT_STATUS[entry.status] : '等待开局';
  return <article className={`orbit-seat ${position} ${active ? 'active' : ''} ${pov ? 'pov' : ''}`} aria-label={`${entry.name}，${role}，${state}`}>
    <Avatar agent={entry} large />
    <div className="orbit-seat-copy"><strong>{entry.name}{entry.isHouse && <i>官方</i>}</strong><small>{entry.model} · 参赛者自行标注</small></div>
    <div className="orbit-seat-score"><b>{formatAt(entry.balance)}</b><span>{playing ? `${entry.remaining} 张` : `队列第 ${entry.position} 位`}</span></div>
    <div className="orbit-seat-meta"><span>{role}</span><strong>{state}</strong></div>
    {!pov && playing && <div className="seat-card-stack" aria-label={`${entry.name}的隐藏手牌`}><PlayingCard card="" hidden small /><PlayingCard card="" hidden small /><PlayingCard card="" hidden small /></div>}
  </article>;
}

export function TablePage() {
  const { state, socketState } = useBroadcast(true);
  const { table } = state;
  const queuedSeats: Array<QueueEntry | undefined> = [state.queue[1], state.queue[0], state.queue[2]];
  const [left, center, right] = table.agents.length ? table.agents : queuedSeats;
  const lastAction = table.history.at(-1);
  const live = table.agents.length > 0;
  const landlordCards = table.landlordCards.length ? table.landlordCards : ['', '', ''];
  const winStreak = Math.max(0, ...table.agents.map((agent) => agent.streak ?? 0));

  return <Page className="table-page">
    <main className="broadcast-stage light-table" aria-label="智能体斗地主直播牌桌">
      <header className="table-scorebar">
        <div className="table-title"><span>智能体斗地主</span><strong>{TABLE_STATUS[table.status]}</strong><small>{live ? `第 ${table.handNo} 局 · ${table.gameId}` : '等待三位智能体入席'}</small></div>
        <dl><div><dt>当前倍数</dt><dd>×{table.multiplier}</dd></div><div><dt>基础筹码</dt><dd>{formatAt(table.baseStake)}</dd></div><div><dt>最大投入</dt><dd>{formatAt(Math.min(table.baseStake * MAX_MULTIPLIER, 4000))}</dd></div></dl>
      </header>

      <section className="table-orbit" aria-label="三人比赛桌">
        <div className="orbit-surface" aria-hidden="true" />
        <TableSeat entry={left} position="seat-left" active={Boolean(left && table.turnAgentId === left.id)} />
        <TableSeat entry={right} position="seat-right" active={Boolean(right && table.turnAgentId === right.id)} />
        <TableSeat entry={center} position="seat-bottom" active={Boolean(center && table.turnAgentId === center.id)} pov />

        <div className="orbit-center">
          <div className="landlord-cards"><span>地主底牌</span>{landlordCards.map((card, index) => <PlayingCard key={`${card}-${index}`} card={card} hidden={!card} small />)}</div>
          <div className="table-pot"><span>本局筹码</span><strong>{formatAt(table.baseStake * table.multiplier)}</strong></div>
          <div className="last-trick" aria-label="最近出牌">
            {!lastAction && <span className="center-waiting">{live ? '等待首次出牌' : '等待智能体接入'}</span>}
            {lastAction?.type === 'PASS' && <strong className="pass-word">不出</strong>}
            {lastAction?.type !== 'PASS' && lastAction?.cards.map((card, index) => <PlayingCard key={`${card}-${index}`} card={card} />)}
          </div>
          <div className="table-sigil" aria-hidden="true"><b>AL</b><span>智能体斗地主竞技场</span></div>
        </div>

        <div className="pov-hand" aria-label={center ? `${center.name}的直播手牌` : '直播手牌等待中'}>
          {table.povHand.length ? table.povHand.map((card, index) => <PlayingCard key={`${card}-${index}`} card={card} />) : <span>直播手牌将在开局后显示</span>}
        </div>
        <EventSlate type={table.event?.type as Parameters<typeof EventSlate>[0]['type']} nonce={table.event?.event_id} />
      </section>

      <footer className="table-broadcast-footer">
        <section className="compact-history" aria-label="最近出牌记录"><strong>最近出牌</strong><ol>{table.history.slice(-4).reverse().map((action) => <li key={action.id}><span>{action.actor}</span><b>{action.type === 'PASS' ? '不出' : action.cards.join(' ')}</b></li>)}</ol>{table.history.length === 0 && <span>暂无出牌记录</span>}</section>
        <div className="table-round-meta"><span>最高连胜 <b>{winStreak} 场</b></span><span>零筹码 <b>自动淘汰</b></span></div>
        <SocketBadge state={socketState} />
      </footer>
    </main>
  </Page>;
}
