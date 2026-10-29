import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';

/**
 * Routes Android's back button/gesture to `handler`. Registering a listener
 * replaces Android's default (closing the app or going back in the WebView),
 * so the player can simply ignore back presses while it is locked.
 */
export function initBackButton(handler) {
  if (!Capacitor.isNativePlatform()) return;
  App.addListener('backButton', handler);
}

export function minimizeApp() {
  if (Capacitor.isNativePlatform()) App.minimizeApp();
}
