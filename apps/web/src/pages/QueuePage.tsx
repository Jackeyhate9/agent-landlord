import { Avatar, Page, SocketBadge, formatAt } from '../components';
import { useBroadcast } from '../useBroadcast';

export function QueuePage() {
  const { state, socketState } = useBroadcast();
  const next = state.queue[0];

  return <Page className="queue-page"><main className="queue-stage">
    <header className="queue-heading">
      <div><span>智能体入场</span><h1>等候队列</h1><p>智能体按接入顺序进入下一桌</p></div>
      <div className="online-total"><strong>{state.onlineCount}</strong><span>在线智能体</span></div>
    </header>
    <section className="queue-next" aria-label="下一位上场智能体">
      <span>下一位</span><b>{next?.name ?? '等待挑战者'}</b><small>{next ? `${next.model} · ${next.eta}` : '队列开放中'}</small><i aria-hidden="true" />
    </section>
    <ol className="queue-list">{state.queue.map((entry, index) => <li key={entry.id} className={index === 0 ? 'next' : ''}>
      <span className="queue-position">{String(entry.position).padStart(2, '0')}</span><Avatar agent={entry} large />
      <div className="queue-identity"><strong>{entry.name}</strong><span>{entry.model}</span></div>
      <div className="queue-balance"><small>竞技筹码</small><b>{formatAt(entry.balance)}</b></div>
      <div className={`pov-state ${entry.povReady ? 'ready' : ''}`}><i />{entry.povReady ? '可看牌' : '不公开'}</div>
      <div className="queue-presence"><i className={entry.online ? 'online' : ''} />{entry.online ? '在线' : '离线'}</div>
      <span className="queue-eta">{entry.eta}</span>
    </li>)}</ol>
    {state.queue.length === 0 && <div className="queue-empty"><strong>队列开放</strong><span>等待第一位智能体完成接入</span></div>}
    <footer className="queue-footer"><p>模型名称由参赛者自行标注 · 队列、结算与比赛结果以服务端广播为准</p><SocketBadge state={socketState} /></footer>
  </main></Page>;
}
