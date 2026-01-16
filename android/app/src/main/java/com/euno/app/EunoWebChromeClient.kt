package com.euno.app

import android.Manifest
import android.content.pm.PackageManager
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.euno.app.utils.PreferencesManager

class EunoWebChromeClient(
    private val activity: MainActivity
) : WebChromeClient() {

    companion object {
        const val REQUEST_AUDIO_PERMISSION = 1001
    }

    private var pendingPermissionRequest: PermissionRequest? = null
    private val prefs = PreferencesManager(activity)

    override fun onPermissionRequest(request: PermissionRequest) {
        val origin = request.origin.toString()
        val serverUrl = prefs.getServerUrl()

        // Only auto-grant permissions for our trusted server
        if (serverUrl != null && isTrustedOrigin(origin, serverUrl)) {
            val resources = request.resources

            // Check if audio capture is requested
            if (resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) {
                // Check if Android permission is already granted
                if (ContextCompat.checkSelfPermission(
                        activity,
                        Manifest.permission.RECORD_AUDIO
                    ) == PackageManager.PERMISSION_GRANTED
                ) {
                    // Grant the WebView permission
                    activity.runOnUiThread {
                        request.grant(resources)
                    }
                } else {
                    // Need to request Android permission first
                    pendingPermissionRequest = request
                    ActivityCompat.requestPermissions(
                        activity,
                        arrayOf(Manifest.permission.RECORD_AUDIO),
                        REQUEST_AUDIO_PERMISSION
                    )
                }
            } else {
                // Grant other requested resources
                activity.runOnUiThread {
                    request.grant(resources)
                }
            }
        } else {
            // Deny requests from untrusted origins
            activity.runOnUiThread {
                request.deny()
            }
        }
    }

    override fun onPermissionRequestCanceled(request: PermissionRequest) {
        super.onPermissionRequestCanceled(request)
        if (pendingPermissionRequest == request) {
            pendingPermissionRequest = null
        }
    }

    override fun onProgressChanged(view: WebView?, newProgress: Int) {
        super.onProgressChanged(view, newProgress)
        // Could be used to show loading progress if needed
    }

    /**
     * Called from MainActivity when Android permission result is received
     */
    fun handlePermissionResult(granted: Boolean) {
        pendingPermissionRequest?.let { request ->
            if (granted) {
                activity.runOnUiThread {
                    request.grant(request.resources)
                }
            } else {
                activity.runOnUiThread {
                    request.deny()
                }
            }
            pendingPermissionRequest = null
        }
    }

    /**
     * Check if the origin matches our trusted server URL
     */
    private fun isTrustedOrigin(origin: String, serverUrl: String): Boolean {
        // Remove trailing slashes for comparison
        val normalizedOrigin = origin.trimEnd('/')
        val normalizedServer = serverUrl.trimEnd('/')

        return normalizedOrigin == normalizedServer ||
                normalizedOrigin.startsWith("$normalizedServer/")
    }
}
