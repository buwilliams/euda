package com.euno.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.euno.app.audio.VoiceInterface
import com.euno.app.service.NotificationService
import com.euno.app.utils.AppState
import com.euno.app.utils.PreferencesManager

class MainActivity : AppCompatActivity() {

    private lateinit var prefs: PreferencesManager
    private lateinit var webView: WebView
    private lateinit var loadingOverlay: FrameLayout
    private lateinit var errorView: LinearLayout
    private lateinit var errorMessage: TextView
    private lateinit var retryButton: Button

    private lateinit var webChromeClient: EunoWebChromeClient
    private var voiceInterface: VoiceInterface? = null

    companion object {
        private const val REQUEST_NOTIFICATION_PERMISSION = 1002
        private const val REQUEST_AUDIO_PERMISSION_NATIVE = 1003
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        prefs = PreferencesManager(this)

        // If setup not complete, redirect to setup
        if (!prefs.isSetupComplete()) {
            startSetupActivity()
            return
        }

        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        loadingOverlay = findViewById(R.id.loadingOverlay)
        errorView = findViewById(R.id.errorView)
        errorMessage = findViewById(R.id.errorMessage)
        retryButton = findViewById(R.id.retryButton)

        setupWebView()
        setupBackPressHandler()

        retryButton.setOnClickListener {
            loadWebPage()
        }

        // Request notification permission on Android 13+
        requestNotificationPermission()

        // Start notification service if enabled
        if (prefs.isNotificationServiceEnabled()) {
            startNotificationService()
        }

        loadWebPage()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webChromeClient = EunoWebChromeClient(this)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = false
            allowContentAccess = false
            cacheMode = WebSettings.LOAD_DEFAULT

            // Add custom user agent to identify Android app
            userAgentString = "$userAgentString EunoAndroid/1.0"
        }

        // Add native voice interface to bypass secure context restrictions
        val serverUrl = prefs.getServerUrl()
        if (serverUrl != null) {
            voiceInterface = VoiceInterface(this, webView, serverUrl)
            webView.addJavascriptInterface(voiceInterface!!, VoiceInterface.INTERFACE_NAME)
        }

        webView.webViewClient = EunoWebViewClient(
            onPageStarted = {
                runOnUiThread {
                    loadingOverlay.visibility = View.VISIBLE
                    errorView.visibility = View.GONE
                }
            },
            onPageFinished = {
                runOnUiThread {
                    loadingOverlay.visibility = View.GONE
                    // Inject native voice override script
                    injectNativeVoiceScript()
                }
            },
            onError = { _, description ->
                runOnUiThread {
                    showError(description)
                }
            }
        )

        webView.webChromeClient = webChromeClient

        // Request audio permission proactively
        requestAudioPermission()
    }

    private fun injectNativeVoiceScript() {
        // JavaScript that sets up native Android audio recording with VAD
        // Uses web app's auto-submission pattern and respects STT availability
        val script = """
            (function() {
                if (window.eunoNativeVoiceInjected) return;
                window.eunoNativeVoiceInjected = true;

                if (typeof EunoNativeVoice === 'undefined') {
                    console.log('EunoNativeVoice: interface not available');
                    return;
                }

                var isRecording = false;
                var isTranscribing = false;

                // Track voice input for TTS response (mirrors web app's voice.js)
                var nativeLastInputWasVoice = false;

                // Override the web app's wasLastInputVoice function to work with native voice
                window.wasLastInputVoice = function() {
                    var was = nativeLastInputWasVoice;
                    nativeLastInputWasVoice = false;
                    return was;
                };

                // Auto-send transcribed text using web app pattern (for TTS integration)
                function autoSendTranscribedText(text) {
                    // Mark that this message came from voice input (for TTS response)
                    nativeLastInputWasVoice = true;

                    // Send directly to chat without showing in input field
                    // Add user message to UI
                    if (typeof addInlineMessage === 'function') {
                        addInlineMessage(text, 'you');
                    }

                    // Queue and process the message
                    if (typeof messageQueue !== 'undefined' && typeof processMessageQueue === 'function') {
                        messageQueue.push(text);
                        processMessageQueue();
                    }
                }

                window.eunoNativeTranscription = function(text) {
                    console.log('EunoNativeVoice: Received transcription:', text);
                    isRecording = false;
                    isTranscribing = false;
                    updateVoiceButton('idle');

                    if (text && text.trim()) {
                        autoSendTranscribedText(text.trim());
                    }
                };

                window.eunoNativeRecordingStarted = function() {
                    console.log('EunoNativeVoice: Recording started');
                    isRecording = true;
                    isTranscribing = false;
                    updateVoiceButton('recording');
                };

                window.eunoNativeTranscribing = function() {
                    console.log('EunoNativeVoice: Transcribing...');
                    isRecording = false;
                    isTranscribing = true;
                    updateVoiceButton('transcribing');
                };

                window.eunoNativeRecordingError = function(error) {
                    console.error('EunoNativeVoice: Error:', error);
                    isRecording = false;
                    isTranscribing = false;
                    updateVoiceButton('idle');
                    // Show error in chat like web app does
                    if (typeof addInlineMessage === 'function') {
                        addInlineMessage(error || 'Voice recording failed', 'friend');
                    }
                };

                function updateVoiceButton(state) {
                    var btn = document.getElementById('voice-btn');
                    if (!btn) return;

                    btn.classList.remove('recording', 'transcribing');
                    btn.disabled = false;

                    if (state === 'recording') {
                        btn.classList.add('recording');
                        // Waveform with <span> elements to match web app CSS
                        btn.innerHTML = '<span class="voice-indicator"></span><div class="voice-waveform"><span></span><span></span><span></span><span></span><span></span></div>';
                    } else if (state === 'transcribing') {
                        btn.classList.add('transcribing');
                        btn.disabled = true;
                        btn.innerHTML = '<span class="voice-indicator"></span><svg viewBox="0 0 24 24" class="spinner"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="31.4 31.4" transform="rotate(-90 12 12)"><animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/></circle></svg>';
                    } else {
                        btn.innerHTML = '<span class="voice-indicator"></span><svg viewBox="0 0 24 24" id="voice-icon"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v1a7 7 0 0 1-14 0v-1m7 9v3m-4 0h8"/></svg>';
                    }
                }

                // Update voice button visibility based on STT availability
                function updateNativeVoiceButtonVisibility() {
                    var voiceBtn = document.getElementById('voice-btn');
                    var jobLabel = document.getElementById('job-context-label');
                    if (!voiceBtn) return;

                    // Check if current provider supports STT (from settingsData)
                    if (typeof settingsData !== 'undefined' && settingsData && settingsData.speech && settingsData.speech.stt_available) {
                        voiceBtn.classList.remove('hidden');
                        voiceBtn.style.display = 'flex';
                        // Reset @job label position when mic is visible
                        if (jobLabel) jobLabel.style.right = '';
                        console.log('EunoNativeVoice: STT available, showing button');
                    } else {
                        voiceBtn.classList.add('hidden');
                        voiceBtn.style.display = 'none';
                        // Adjust @job label position when mic is hidden
                        if (jobLabel) jobLabel.style.right = '12px';
                        console.log('EunoNativeVoice: STT not available, hiding button');
                    }
                }

                window.toggleVoiceRecording = function() {
                    if (isTranscribing) return;

                    if (isRecording) {
                        EunoNativeVoice.stopRecording();
                        isRecording = false;
                        isTranscribing = true;
                        updateVoiceButton('transcribing');
                    } else {
                        if (EunoNativeVoice.hasPermission()) {
                            if (EunoNativeVoice.startRecording()) {
                                console.log('EunoNativeVoice: Started');
                            }
                        } else {
                            alert('Please grant microphone permission in app settings');
                        }
                    }
                };

                // Override the web app's updateVoiceButtonVisibility to use our native version
                window.updateVoiceButtonVisibility = updateNativeVoiceButtonVisibility;

                // Initial visibility check
                var voiceBtn = document.getElementById('voice-btn');
                if (voiceBtn) {
                    updateNativeVoiceButtonVisibility();
                    updateVoiceButton('idle');
                }

                // Also check when settingsData changes (in case it loads after this script)
                var checkSettingsInterval = setInterval(function() {
                    if (typeof settingsData !== 'undefined' && settingsData) {
                        updateNativeVoiceButtonVisibility();
                        clearInterval(checkSettingsInterval);
                    }
                }, 500);

                // Clear interval after 10 seconds to avoid infinite polling
                setTimeout(function() {
                    clearInterval(checkSettingsInterval);
                }, 10000);

                console.log('EunoNativeVoice: Ready');
            })();
        """.trimIndent()

        webView.evaluateJavascript(script, null)
    }

    private fun requestAudioPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                REQUEST_AUDIO_PERMISSION_NATIVE
            )
        }
    }

    private fun setupBackPressHandler() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    // Show exit confirmation or minimize
                    finish()
                }
            }
        })
    }

    private fun loadWebPage() {
        val serverUrl = prefs.getServerUrl()
        if (serverUrl != null) {
            loadingOverlay.visibility = View.VISIBLE
            errorView.visibility = View.GONE
            webView.loadUrl(serverUrl)
        } else {
            startSetupActivity()
        }
    }

    private fun showError(description: String) {
        loadingOverlay.visibility = View.GONE
        errorView.visibility = View.VISIBLE
        errorMessage.text = description
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    REQUEST_NOTIFICATION_PERMISSION
                )
            }
        }
    }

    private fun startNotificationService() {
        val intent = Intent(this, NotificationService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun startSetupActivity() {
        val intent = Intent(this, SetupActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    fun openSettings() {
        val intent = Intent(this, SettingsActivity::class.java)
        startActivity(intent)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        when (requestCode) {
            EunoWebChromeClient.REQUEST_AUDIO_PERMISSION -> {
                val granted = grantResults.isNotEmpty() &&
                        grantResults[0] == PackageManager.PERMISSION_GRANTED
                webChromeClient.handlePermissionResult(granted)
            }
            REQUEST_AUDIO_PERMISSION_NATIVE -> {
                // Native audio permission granted, voice interface will work
            }
            REQUEST_NOTIFICATION_PERMISSION -> {
                // Notification permission handled, no action needed
            }
        }
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
        // Mark app as in foreground (suppress notifications)
        AppState.setForeground(true)
    }

    override fun onPause() {
        super.onPause()
        webView.onPause()
        // Mark app as in background (allow notifications)
        AppState.setForeground(false)
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
