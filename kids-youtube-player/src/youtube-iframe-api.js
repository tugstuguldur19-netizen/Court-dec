const API_URL = 'https://www.youtube.com/iframe_api';
let loading = null;

/** Loads the YouTube IFrame Player API once and resolves with `window.YT`. */
export function loadIframeApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  loading ??= new Promise((resolve, reject) => {
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previous?.();
      resolve(window.YT);
    };
    const script = document.createElement('script');
    script.src = API_URL;
    script.async = true;
    script.onerror = () => {
      loading = null;
      script.remove();
      reject(new Error("Couldn't load the video player. Check the internet connection."));
    };
    document.head.append(script);
  });
  return loading;
}
