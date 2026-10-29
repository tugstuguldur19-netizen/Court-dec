package com.kidsplayer.app;

import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeWebViewClient;

/**
 * Keeps the child inside the app.
 *
 * Capacitor's default client hands any link that leaves the app to Android,
 * so tapping the YouTube logo or title inside the player would open the real
 * YouTube app or a browser. This client refuses those navigations instead.
 * The YouTube player iframe may still navigate within itself over https.
 */
public class GuardedWebViewClient extends BridgeWebViewClient {

    private final Bridge bridge;

    public GuardedWebViewClient(Bridge bridge) {
        super(bridge);
        this.bridge = bridge;
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        Uri url = request.getUrl();
        String scheme = url.getScheme();
        if (!"https".equals(scheme) && !"http".equals(scheme)) {
            // intent://, vnd.youtube:, market: ... would launch other apps.
            return true;
        }
        if (request.isForMainFrame()) {
            Uri app = Uri.parse(bridge.getAppUrl());
            boolean inApp = app.getHost().equals(url.getHost()) && app.getScheme().equals(scheme);
            return !inApp;
        }
        return false;
    }
}
