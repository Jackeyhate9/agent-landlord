import type { GameEventType } from './types';

export type SoundName = 'agent_join' | 'deal' | 'play_card' | 'pass' | 'landlord' | 'bomb' | 'rocket' | 'spring' | 'victory' | 'defeat' | 'elimination' | 'challenger_enter' | 'streak' | 'hall_of_fame' | 'suspense';

let context: AudioContext | null = null;

function ctx() {
  context ??= new AudioContext();
  if (context.state === 'suspended') void context.resume();
  return context;
}

// 音符：频率 / 时长(秒) / 波形 / 音量。加长版：关键事件更饱满、拖尾更长。
function note(audio: AudioContext, frequency: number, start: number, duration: number, type: OscillatorType = 'sine', gainValue = 0.11) {
  const oscillator = audio.createOscillator();
  const gain = audio.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(gainValue, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain).connect(audio.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.05);
}

export function playSound(name: SoundName) {
  const audio = ctx();
  const now = audio.currentTime;
  // 每项: [频率, 时长, 波形, 音量]；音符间隔 index * .14，让每个音效更有层次、更长。
  const patterns: Record<SoundName, Array<[number, number, OscillatorType, number]>> = {
    agent_join: [[440, .35, 'sine', .1], [660, .5, 'sine', .12]],
    deal: [[190, .18, 'triangle', .09], [240, .22, 'triangle', .08], [300, .3, 'triangle', .08], [360, .4, 'triangle', .07]],
    play_card: [[140, .16, 'square', .09], [260, .22, 'triangle', .08], [320, .3, 'triangle', .07]],
    pass: [[240, .35, 'sine', .07]],
    landlord: [[220, .3, 'sawtooth', .09], [330, .45, 'triangle', .1], [440, .55, 'sine', .08]],
    bomb: [[90, .9, 'sawtooth', .2], [55, 1.1, 'square', .14], [48, 1.3, 'sawtooth', .1]],
    rocket: [[70, .8, 'sawtooth', .24], [220, .9, 'square', .16], [440, 1.0, 'square', .12], [880, 1.2, 'sine', .1]],
    spring: [[392, .35, 'sine', .1], [523, .4, 'sine', .11], [784, .65, 'triangle', .12], [1046, .8, 'sine', .08]],
    victory: [[392, .4, 'triangle', .1], [523, .45, 'triangle', .11], [659, .5, 'triangle', .11], [784, .9, 'sine', .12]],
    defeat: [[220, .5, 'sine', .09], [174, .7, 'sine', .1], [146, .9, 'sine', .08]],
    elimination: [[180, .4, 'square', .12], [90, 1.0, 'sawtooth', .16], [70, 1.2, 'sawtooth', .12]],
    challenger_enter: [[330, .3, 'triangle', .09], [440, .45, 'triangle', .11], [660, .55, 'sine', .09]],
    streak: [[523, .3, 'square', .09], [659, .35, 'square', .1], [784, .5, 'square', .11], [1046, .7, 'sine', .1]],
    hall_of_fame: [[262, .5, 'triangle', .09], [392, .55, 'triangle', .1], [523, .6, 'triangle', .11], [784, 1.0, 'sine', .12]],
    suspense: [[110, 1.4, 'sawtooth', .05], [116, 1.5, 'sine', .04], [110, 1.6, 'sawtooth', .04]],
  };
  patterns[name].forEach(([frequency, duration, type, gain], index) => note(audio, frequency, now + index * .14, duration, type, gain));
}

export function soundForEvent(type: GameEventType): SoundName | undefined {
  return ({ DEAL: 'deal', PLAY: 'play_card', PASS: 'pass', BOMB: 'bomb', ROCKET: 'rocket', SPRING: 'spring', WIN: 'victory', LOSE: 'defeat', ELIMINATION: 'elimination', NEXT_CHALLENGER: 'challenger_enter', WIN_STREAK: 'streak', HALL_OF_FAME: 'hall_of_fame', LANDLORD: 'landlord' } as Partial<Record<GameEventType, SoundName>>)[type];
}