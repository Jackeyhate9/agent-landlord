import type { GameEventType } from './types';

export type SoundName = 'agent_join' | 'deal' | 'play_card' | 'pass' | 'landlord' | 'bomb' | 'rocket' | 'spring' | 'victory' | 'defeat' | 'elimination' | 'challenger_enter' | 'streak' | 'hall_of_fame' | 'suspense';

let context: AudioContext | null = null;

function ctx() {
  context ??= new AudioContext();
  if (context.state === 'suspended') void context.resume();
  return context;
}

function note(audio: AudioContext, frequency: number, start: number, duration: number, type: OscillatorType = 'sine', gainValue = 0.11) {
  const oscillator = audio.createOscillator();
  const gain = audio.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(gainValue, start + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain).connect(audio.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.02);
}

export function playSound(name: SoundName) {
  const audio = ctx();
  const now = audio.currentTime;
  const patterns: Record<SoundName, Array<[number, number, OscillatorType, number]>> = {
    agent_join: [[440, .12, 'sine', .08], [660, .22, 'sine', .1]],
    deal: [[190, .05, 'triangle', .06], [240, .05, 'triangle', .05], [300, .08, 'triangle', .05]],
    play_card: [[120, .06, 'square', .06], [230, .08, 'triangle', .05]],
    pass: [[240, .13, 'sine', .05]],
    landlord: [[220, .12, 'sawtooth', .08], [330, .2, 'triangle', .09]],
    bomb: [[90, .35, 'sawtooth', .18], [55, .48, 'square', .1]],
    rocket: [[70, .28, 'sawtooth', .2], [220, .34, 'square', .13], [880, .55, 'sine', .1]],
    spring: [[392, .12, 'sine', .08], [523, .12, 'sine', .09], [784, .28, 'triangle', .1]],
    victory: [[392, .14, 'triangle', .08], [523, .14, 'triangle', .09], [659, .34, 'triangle', .11]],
    defeat: [[220, .18, 'sine', .07], [174, .35, 'sine', .08]],
    elimination: [[180, .12, 'square', .09], [90, .42, 'sawtooth', .12]],
    challenger_enter: [[330, .1, 'triangle', .07], [440, .2, 'triangle', .09]],
    streak: [[523, .09, 'square', .06], [659, .09, 'square', .07], [784, .2, 'square', .08]],
    hall_of_fame: [[262, .2, 'triangle', .07], [392, .2, 'triangle', .08], [523, .45, 'sine', .1]],
    suspense: [[110, .7, 'sawtooth', .035], [116, .7, 'sine', .025]],
  };
  patterns[name].forEach(([frequency, duration, type, gain], index) => note(audio, frequency, now + index * .09, duration, type, gain));
}

export function soundForEvent(type: GameEventType): SoundName | undefined {
  return ({ DEAL: 'deal', PLAY: 'play_card', PASS: 'pass', BOMB: 'bomb', ROCKET: 'rocket', SPRING: 'spring', WIN: 'victory', LOSE: 'defeat', ELIMINATION: 'elimination', NEXT_CHALLENGER: 'challenger_enter', WIN_STREAK: 'streak', HALL_OF_FAME: 'hall_of_fame', LANDLORD: 'landlord' } as Partial<Record<GameEventType, SoundName>>)[type];
}
