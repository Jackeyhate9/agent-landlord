import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AgentPlate, PlayingCard, SocketBadge } from '../components';
import { initialBroadcastState } from '../mock';

describe('broadcast components', () => {
  it('announces card identity and never leaks a hidden card', () => {
    const { rerender } = render(<PlayingCard card="A♠" />);
    expect(screen.getByLabelText('A♠')).toBeInTheDocument();
    rerender(<PlayingCard card="A♠" hidden />);
    expect(screen.getByLabelText('暗牌')).toBeInTheDocument();
    expect(screen.queryByLabelText('A♠')).not.toBeInTheDocument();
  });

  it('exposes role and state as semantic text', () => {
    render(<AgentPlate agent={initialBroadcastState.table.agents[1]} active />);
    expect(screen.getByLabelText(/CatLord，地主，THINKING/)).toBeInTheDocument();
    expect(screen.getByText('当前回合')).toBeInTheDocument();
  });

  it('renders connection and delay status for OBS operators', () => {
    render(<SocketBadge state="reconnecting" />);
    expect(screen.getByRole('status')).toHaveTextContent('正在恢复');
    expect(screen.getByRole('status')).toHaveTextContent('公共画面延迟 30 秒');
  });
});
