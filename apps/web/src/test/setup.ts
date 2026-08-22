import '@testing-library/jest-dom/vitest';

class AudioContextStub {
  currentTime = 0;
  state = 'running';
  destination = {};
  createOscillator() { return { type: 'sine', frequency: { setValueAtTime() {} }, connect() { return this; }, start() {}, stop() {} }; }
  createGain() { return { gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() { return this; } }; }
  resume() { return Promise.resolve(); }
}

Object.defineProperty(window, 'AudioContext', { writable: true, value: AudioContextStub });

class WebSocketStub {
  static OPEN = 1;
  readyState = 0;
  addEventListener() {}
  send() {}
  close() {}
}

Object.defineProperty(window, 'WebSocket', { writable: true, value: WebSocketStub });
