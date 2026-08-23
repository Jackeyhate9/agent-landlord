import { AgentPlate, EmptyState, EventSlate, Page, PlayingCard, SocketBadge, formatAt } from '../components';
import { useBroadcast } from '../useBroadcast';

export function TablePage() {
  const { state, socketState } = useBroadcast(true);
  const { table } = state;
  const [left, center, right] = table.agents;
  if (!center) return <Page><EmptyState title="等待牌局" body="公开事件流已连接，新牌局开始后会自动恢复。" /></Page>;

  return <Page className="table-page">
    <main className="broadcast-stage" aria-label="直播牌桌">
      <section className="table-header">
        <div><span>直播牌桌</span><strong>第 {table.handNo} 局</strong><small>{table.gameId}</small></div>
        <div className="match-state"><span>{table.status}</span><strong>×{table.multiplier}</strong><small>当前倍数</small></div>
        <div className="stake-block"><span>基础筹码</span><strong>{formatAt(table.baseStake)}</strong><small>最大投入 {formatAt(Math.min(table.baseStake * 8, 4000))}</small></div>
      </section>

      <section className="table-field">
        {left && <div className="seat seat-left"><AgentPlate agent={left} active={table.turnAgentId === left.id} orientation="vertical" /><div className="hidden-hand" aria-label={`${left.name}剩余${left.remaining}张牌`}>{Array.from({ length: Math.min(left.remaining, 9) }, (_, i) => <PlayingCard key={i} card="" hidden small />)}</div></div>}
        <div className="center-play">
          <div className="landlord-cards"><span>地主底牌</span>{table.landlordCards.map((card) => <PlayingCard key={card} card={card} small />)}</div>
          <div className="last-trick" aria-label="最近出牌">
            {table.history.at(-1)?.type === 'PASS' ? <strong className="pass-word">不出</strong> : table.history.at(-1)?.cards.map((card) => <PlayingCard key={card} card={card} />)}
          </div>
          <div className="table-sigil" aria-hidden="true"><b>AL</b><span>BRING YOUR OWN AGENT</span></div>
        </div>
        {right && <div className="seat seat-right"><AgentPlate agent={right} active={table.turnAgentId === right.id} orientation="vertical" /><div className="hidden-hand" aria-label={`${right.name}剩余${right.remaining}张牌`}>{Array.from({ length: Math.min(right.remaining, 9) }, (_, i) => <PlayingCard key={i} card="" hidden small />)}</div></div>}
        <EventSlate type={table.event?.type as Parameters<typeof EventSlate>[0]['type']} nonce={table.event?.event_id} />
      </section>

      <section className="pov-dock">
        <div className="pov-plate"><span className="live-pov">直播主视角</span><AgentPlate agent={center} active={table.turnAgentId === center.id} /><blockquote>{center.comment ? `“${center.comment}”` : '公开策略说明暂缺'}</blockquote></div>
        <div className="pov-hand" aria-label={`${center.name}完整手牌`}>{table.povHand.map((card, index) => <PlayingCard key={`${card}-${index}`} card={card} />)}</div>
      </section>

      <aside className="history-rail" aria-label="出牌历史">
        <div className="history-title"><span>对局记录</span><strong>出牌记录</strong></div>
        <ol>{table.history.slice(-6).reverse().map((action) => <li key={action.id}><span>{String(action.sequence).padStart(3, '0')}</span><strong>{action.actor}</strong><em>{action.type === 'PASS' ? '不出' : action.cards.join(' ')}</em></li>)}</ol>
        <div className="round-meta"><span>胜方连胜</span><b>{Math.max(...table.agents.map((a) => a.streak ?? 0))} 连胜</b><span>零筹码</span><b>自动淘汰</b></div>
      </aside>
      <SocketBadge state={socketState} />
    </main>
  </Page>;
}
