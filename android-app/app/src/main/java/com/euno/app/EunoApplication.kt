package com.euno.app

import android.app.Application
import android.util.Log
import android.webkit.WebView
import com.euno.app.utils.PreferencesManager
import com.euno.app.utils.WebViewSecureOrigin

class EunoApplication : Application() {

    companion object {
        private const val TAG = "EunoApplication"
    }

    override fun onCreate() {
        super.onCreate()

        // Configure WebView secure origin BEFORE any WebView is created
        configureWebViewSecureOrigin()
    }

    private fun configureWebViewSecureOrigin() {
        try {
            val prefs = PreferencesManager(this)
            val serverUrl = prefs.getServerUrl()

            if (serverUrl != null) {
                Log.d(TAG, "Configuring WebView for secure origin: $serverUrl")
                WebViewSecureOrigin.configure(this, serverUrl)
            } else {
                Log.d(TAG, "No server URL configured yet")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to configure WebView secure origin", e)
        }
    }
}
