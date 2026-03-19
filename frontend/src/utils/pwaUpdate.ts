/**
 * Store for PWA update callback. Used when registerType is 'prompt'.
 * The PWAUpdatePrompt component listens for the custom event and shows a banner.
 */
let updateSWFn: (() => void) | null = null;

export const PWA_NEED_REFRESH_EVENT = 'pwa-need-refresh';

export function setUpdateSW(fn: () => void) {
  updateSWFn = fn;
}

export function getUpdateSW() {
  return updateSWFn;
}

export function notifyNeedRefresh() {
  window.dispatchEvent(new CustomEvent(PWA_NEED_REFRESH_EVENT));
}
