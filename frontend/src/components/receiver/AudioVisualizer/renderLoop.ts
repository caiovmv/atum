import type { AudioEnergy } from '../../../audio/audioEnergy';

/**
 * Cria um loop de renderização que chama draw(audio) a cada frame.
 * Retorna função de cleanup.
 */
export function createRenderLoop(
  getAudio: () => AudioEnergy,
  draw: (audio: AudioEnergy) => void
): () => void {
  let raf = 0;
  let running = true;

  const tick = () => {
    if (!running) return;
    const audio = getAudio();
    draw(audio);
    raf = requestAnimationFrame(tick);
  };

  raf = requestAnimationFrame(tick);

  return () => {
    running = false;
    cancelAnimationFrame(raf);
  };
}
