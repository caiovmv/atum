import { useEffect, useRef, useCallback } from 'react';

/**
 * Activates Picture-in-Picture for a video element when the component unmounts
 * (e.g. user navigates away). Exits PiP when the component mounts again.
 */
export function usePiP(videoSelector = '.receiver-video-player') {
  const wasPlayingRef = useRef(false);

  const enterPiP = useCallback(async () => {
    if (!document.pictureInPictureEnabled) return;
    const video = document.querySelector<HTMLVideoElement>(videoSelector);
    if (!video || video.paused || document.pictureInPictureElement) return;
    if (!video.isConnected) return;
    try {
      wasPlayingRef.current = true;
      await video.requestPictureInPicture();
    } catch {
      // PiP not supported, permission denied, or element detached
    }
  }, [videoSelector]);

  const exitPiP = useCallback(async () => {
    if (document.pictureInPictureElement) {
      try {
        await document.exitPictureInPicture();
      } catch { /* ignore */ }
    }
  }, []);

  useEffect(() => {
    exitPiP();
    return () => { enterPiP(); };
  }, [enterPiP, exitPiP]);

  return { enterPiP, exitPiP };
}
