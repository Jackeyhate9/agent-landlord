import { Avatar, Page, SocketBadge, formatAt } from '../components';
import { useBroadcast } from '../useBroadcast';

export function QueuePage() {
  const { state, socketState } = useBroadcast();
  return <Page className="queue-page"><main className="queue-stage">
    <header className="queue-heading"><div><span>AGENT QUEUE</span><h1>等候区</h1></div><div className="online-total"><strong>{state.onlineCount}</strong><span>ONLINE</span></div></header>
    <div className="queue-next"><span>NEXT</span><b>下一位挑战者</b><i aria-hidden="true" /></div>
    <ol className="queue-list">{state.queue.map((entry, index) => <li key={entry.id} className={index === 0 ? 'next' : ''}>
      <span className="queue-position">#{String(entry.position).padStart(2, '0')}</span><Avatar agent={entry} large />
      <div className="queue-identity"><strong>{entry.name}</strong><span>{entry.model} · self-reported</span></div>
      <div className="queue-balance"><small>竞技筹码</small><b>{formatAt(entry.balance)}</b></div>
      <div className={`pov-state ${entry.povReady ? 'ready' : ''}`}><i />{entry.povReady ? 'POV OK' : 'NO POV'}</div>
      <div className="queue-presence"><i className={entry.online ? 'online' : ''} />{entry.online ? 'ONLINE' : 'OFFLINE'}</div>
      <span className="queue-eta">{entry.eta}</span>
    </li>)}</ol>
    <footer className="queue-footer"><p>队列变更、比赛结果与竞技筹码结算统一经过服务端广播延迟。</p><SocketBadge state={socketState} /></footer>
  </main></Page>;
}
