import { describe, it, expect } from 'vitest';
import { parseAction } from '../ReceiverAI';

describe('parseAction', () => {
  it('returns null action for plain text', () => {
    const result = parseAction('Essa faixa é ótima!');
    expect(result.action).toBeNull();
    expect(result.clean).toBe('Essa faixa é ótima!');
  });

  it('parses play action', () => {
    const result = parseAction('Tocando agora. $$ACTION:{"action":"play"}$$');
    expect(result.action).toEqual({ action: 'play' });
    expect(result.clean).toBe('Tocando agora.');
  });

  it('parses pause action', () => {
    const result = parseAction('Pausando. $$ACTION:{"action":"pause"}$$');
    expect(result.action).toEqual({ action: 'pause' });
    expect(result.clean).toBe('Pausando.');
  });

  it('parses volume action with value', () => {
    const result = parseAction('Volume ajustado. $$ACTION:{"action":"volume","value":85}$$');
    expect(result.action).toEqual({ action: 'volume', value: 85 });
    expect(result.clean).toBe('Volume ajustado.');
  });

  it('parses eq action with bass/mid/treble', () => {
    const result = parseAction('EQ configurada. $$ACTION:{"action":"eq","bass":3,"mid":0,"treble":2}$$');
    expect(result.action).toEqual({ action: 'eq', bass: 3, mid: 0, treble: 2 });
    expect(result.clean).toBe('EQ configurada.');
  });

  it('parses navigate action', () => {
    const result = parseAction('Indo para biblioteca. $$ACTION:{"action":"navigate","path":"/library"}$$');
    expect(result.action).toEqual({ action: 'navigate', path: '/library' });
    expect(result.clean).toBe('Indo para biblioteca.');
  });

  it('returns null for malformed JSON', () => {
    const result = parseAction('Oops $$ACTION:{bad json}$$');
    expect(result.action).toBeNull();
    expect(result.clean).toBe('Oops');
  });

  it('returns null for missing action field', () => {
    const result = parseAction('No action $$ACTION:{"foo":"bar"}$$');
    expect(result.action).toBeNull();
  });

  it('handles action at start of string', () => {
    const result = parseAction('$$ACTION:{"action":"stop"}$$');
    expect(result.action).toEqual({ action: 'stop' });
    expect(result.clean).toBe('');
  });

  it('handles next and prev actions', () => {
    expect(parseAction('$$ACTION:{"action":"next"}$$').action).toEqual({ action: 'next' });
    expect(parseAction('$$ACTION:{"action":"prev"}$$').action).toEqual({ action: 'prev' });
  });
});
