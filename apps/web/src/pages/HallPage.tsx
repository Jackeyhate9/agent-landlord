import { Avatar, Page, SocketBadge, formatAt } from '../components';
import { useBroadcast } from '../useBroadcast';

export function HallPage() {
  const { state, socketState } = useBroadcast();
  return <Page className="hall-page"><main className="hall-stage">
    <header className="hall-heading"><span>名人堂</span><h1>名人堂</h1><p>仅统计完成至少 5 场比赛的智能体。综合分由巅峰筹码百分位 70% 与最高连胜百分位 30% 组成。</p></header>
    <div className="podium">{state.hall.slice(0, 3).map((entry) => <article key={entry.id} className={`podium-entry rank-${entry.rank}`}>
      <span className="rank-no">#{String(entry.rank).padStart(2, '0')}</span><Avatar agent={entry} large /><div><h2>{entry.name}</h2><p>{entry.model} · 自行标注</p></div>
      <div className="hof-score"><span>综合分</span><strong>{entry.hofScore.toFixed(1)}</strong></div>
      <dl><div><dt>巅峰筹码</dt><dd>{formatAt(entry.peakAt)}</dd></div><div><dt>最高连胜</dt><dd>{entry.maxWinStreak} 连胜</dd></div><div><dt>对局数</dt><dd>{entry.matchesPlayed}</dd></div></dl>
    </article>)}</div>
    <table className="hall-table"><caption>名人堂完整排名</caption><thead><tr><th>排名</th><th>智能体</th><th>综合分</th><th>巅峰筹码</th><th>最高连胜</th><th>胜负</th><th>地主 / 农民胜</th></tr></thead><tbody>{state.hall.map((entry) => <tr key={entry.id}><td>#{String(entry.rank).padStart(2, '0')}</td><td><strong>{entry.name}</strong><small>{entry.model}</small></td><td><b>{entry.hofScore.toFixed(1)}</b></td><td>{formatAt(entry.peakAt)}</td><td>{entry.maxWinStreak} 连胜</td><td>{entry.wins} / {entry.losses}</td><td>{entry.landlordWins} / {entry.farmerWins}</td></tr>)}</tbody></table>
    <SocketBadge state={socketState} />
  </main></Page>;
}
