package com.euno.app.utils

import android.content.Context
import android.os.Build
import android.util.Log
import android.webkit.WebView
import java.io.File

/**
 * Utility to enable insecure origins as secure for WebView.
 * This mirrors Chrome's --unsafely-treat-insecure-origin-as-secure flag.
 */
object WebViewSecureOrigin {

    private const val TAG = "WebViewSecureOrigin"

    /**
     * Attempt to configure WebView to treat the given origin as secure.
     * Must be called BEFORE any WebView is created.
     *
     * @param context Application context
     * @param origin The origin to treat as secure (e.g., "http://192.168.1.100")
     * @return true if configuration was attempted
     */
    fun configure(context: Context, origin: String): Boolean {
        return try {
            // Enable WebView debugging (required for command line to work)
            WebView.setWebContentsDebuggingEnabled(true)

            // Try multiple approaches
            val success = tryCommandLineFile(context, origin) ||
                    tryReflection(origin)

            Log.d(TAG, "Configuration attempted for origin: $origin, success: $success")
            success
        } catch (e: Exception) {
            Log.e(TAG, "Failed to configure secure origin", e)
            false
        }
    }

    /**
     * Try to write command line file that WebView reads on startup.
     */
    private fun tryCommandLineFile(context: Context, origin: String): Boolean {
        return try {
            // Try app-specific command line file location
            val cmdLine = "_ --unsafely-treat-insecure-origin-as-secure=$origin"

            // Try multiple possible locations
            val locations = listOf(
                File(context.applicationInfo.dataDir, "webview-command-line"),
                File("/data/local/tmp", "${context.packageName}-command-line"),
                File("/data/local/tmp", "webview-command-line")
            )

            var written = false
            for (file in locations) {
                try {
                    file.writeText(cmdLine)
                    file.setReadable(true, false)
                    Log.d(TAG, "Wrote command line to: ${file.absolutePath}")
                    written = true
                    break
                } catch (e: Exception) {
                    Log.d(TAG, "Could not write to ${file.absolutePath}: ${e.message}")
                }
            }

            written
        } catch (e: Exception) {
            Log.e(TAG, "Command line file approach failed", e)
            false
        }
    }

    /**
     * Try to use reflection to set command line flags directly.
     */
    private fun tryReflection(origin: String): Boolean {
        return try {
            // Try to access CommandLine class via reflection
            val commandLineClass = Class.forName("org.chromium.base.CommandLine")

            // Try getInstance
            val getInstance = commandLineClass.getMethod("getInstance")
            val instance = getInstance.invoke(null)

            // Try appendSwitch
            val appendSwitch = commandLineClass.getMethod(
                "appendSwitchWithValue",
                String::class.java,
                String::class.java
            )
            appendSwitch.invoke(
                instance,
                "unsafely-treat-insecure-origin-as-secure",
                origin
            )

            Log.d(TAG, "Reflection approach succeeded")
            true
        } catch (e: ClassNotFoundException) {
            Log.d(TAG, "CommandLine class not found (expected on most devices)")
            false
        } catch (e: Exception) {
            Log.d(TAG, "Reflection approach failed: ${e.message}")
            false
        }
    }
}
