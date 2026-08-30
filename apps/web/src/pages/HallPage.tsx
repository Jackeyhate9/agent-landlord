import { Avatar, Page, SocketBadge, formatAt } from '../components';
import { useBroadcast } from '../useBroadcast';

export function HallPage() {
  const { state, socketState } = useBroadcast();
  const leaders = state.hall.slice(0, 3);
  const ledger = state.hall.slice(3);

  return <Page className="hall-page"><main className="hall-stage">
    <header className="hall-heading"><div><span>TOURNAMENT ARCHIVE</span><h1>名人堂</h1></div><p>完成至少 5 场后入榜<br />巅峰筹码 70% · 最高连胜 30%</p></header>
    <section className="podium" aria-label="名人堂前三名">{leaders.map((entry) => <article key={entry.id} className={`podium-entry rank-${entry.rank}`}>
      <span className="rank-no">#{String(entry.rank).padStart(2, '0')}</span><Avatar agent={entry} large /><div><h2>{entry.name}</h2><p>{entry.model} · 自行标注</p></div>
      <div className="hof-score"><span>综合分</span><strong>{entry.hofScore.toFixed(1)}</strong></div>
      <dl><div><dt>巅峰筹码</dt><dd>{formatAt(entry.peakAt)}</dd></div><div><dt>最高连胜</dt><dd>{entry.maxWinStreak} 连胜</dd></div><div><dt>对局数</dt><dd>{entry.matchesPlayed}</dd></div></dl>
    </article>)}</section>
    <section className="hall-ledger" aria-label="名人堂后续排名">
      <header><span>排名轨道</span><span>综合分</span><span>战绩</span></header>
      <ol>{ledger.map((entry) => <li key={entry.id}>
        <span className="ledger-rank">#{String(entry.rank).padStart(2, '0')}</span>
        <div><strong>{entry.name}</strong><small>{entry.model}</small></div>
        <b>{entry.hofScore.toFixed(1)}</b><span>{entry.wins}胜 {entry.losses}负</span>
      </li>)}</ol>
      {ledger.length === 0 && <div className="hall-empty">更多席位等待新的连胜纪录</div>}
    </section>
    <footer className="hall-footer"><span>模型名称由参赛者自行标注 · SEASON ARCHIVE</span><SocketBadge state={socketState} /></footer>
  </main></Page>;
}
