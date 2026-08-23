import { useState } from 'react';
import { playSound, soundForEvent } from '../audio';
import { EventSlate, Page, PlayingCard } from '../components';
import type { GameEventType } from '../types';

const EVENTS: GameEventType[] = ['DEAL', 'PLAY', 'PASS', 'BOMB', 'ROCKET', 'SPRING', 'WIN', 'LOSE', 'ELIMINATION', 'NEXT_CHALLENGER', 'WIN_STREAK', 'HALL_OF_FAME'];
const EVENT_NAMES: Record<string, string> = {
  DEAL: '发牌', PLAY: '出牌', PASS: '不出', BOMB: '炸弹', ROCKET: '王炸', SPRING: '春天',
  WIN: '胜利', LOSE: '落败', ELIMINATION: '淘汰', NEXT_CHALLENGER: '下一位挑战者', WIN_STREAK: '连胜', HALL_OF_FAME: '名人堂',
};

export function DemoPage() {
  const [event, setEvent] = useState<GameEventType>('DEAL');
  const [nonce, setNonce] = useState(0);
  const trigger = (next: GameEventType) => { setEvent(next); setNonce((value) => value + 1); const sound = soundForEvent(next); if (sound) playSound(sound); };
  return <Page className="demo-page"><main className="demo-shell"><header><span>赛事事件演示</span><h1>赛事事件演示台</h1><p>不需要真实比赛即可检查动画、安全区域和浏览器音频捕获。</p></header><section className="demo-preview"><div className="demo-cards"><PlayingCard card="BJ" /><PlayingCard card="RJ" /><PlayingCard card="2♥" /></div><div className="safe-area"><span>16:9 安全区域</span></div><EventSlate type={event} nonce={nonce} /></section><section className="demo-controls"><h2>事件动画</h2><div>{EVENTS.map((type) => <button key={type} onClick={() => trigger(type)}>{EVENT_NAMES[type] ?? type.replace('_', ' ')}</button>)}</div><p>当前：<strong>{EVENT_NAMES[event] ?? event}</strong> · 动画 #{nonce}</p></section></main></Page>;
}
