package com.euno.app.audio

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.JavascriptInterface
import android.webkit.WebView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * JavaScript interface for native voice recording.
 * This bypasses WebView's secure context restrictions for getUserMedia.
 */
class VoiceInterface(
    private val context: Context,
    private val webView: WebView,
    private val serverUrl: String
) {
    companion object {
        private const val TAG = "VoiceInterface"
        const val INTERFACE_NAME = "EunoNativeVoice"
    }

    private val recorder = AudioRecorder(context)
    private val scope = CoroutineScope(Dispatchers.Main)
    private val mainHandler = Handler(Looper.getMainLooper())

    @Volatile
    private var isProcessingStop = false

    init {
        // Set up VAD callback for auto-stop when silence is detected
        recorder.setOnSilenceDetected {
            Log.d(TAG, "VAD silence detected - auto-stopping recording")
            mainHandler.post {
                handleAutoStop()
            }
        }
    }

    private fun handleAutoStop() {
        if (isProcessingStop) {
            Log.d(TAG, "Already processing stop, ignoring")
            return
        }
        isProcessingStop = true

        Log.d(TAG, "Auto-stopping due to VAD silence detection")

        // Notify JS that we're now transcribing
        runOnWebView("window.eunoNativeTranscribing && window.eunoNativeTranscribing()")

        scope.launch {
            try {
                val audioFile = recorder.saveToTempFile()
                if (audioFile != null) {
                    Log.d(TAG, "Audio file created: ${audioFile.absolutePath}, size: ${audioFile.length()}")
                    transcribeAudio(audioFile)
                } else {
                    Log.e(TAG, "No audio file created on auto-stop")
                    runOnWebView("window.eunoNativeRecordingError && window.eunoNativeRecordingError('No audio recorded')")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error in auto-stop", e)
                runOnWebView("window.eunoNativeRecordingError && window.eunoNativeRecordingError('${e.message}')")
            } finally {
                isProcessingStop = false
            }
        }
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    @JavascriptInterface
    fun hasPermission(): Boolean {
        val result = recorder.hasPermission()
        Log.d(TAG, "hasPermission: $result")
        return result
    }

    @JavascriptInterface
    fun isRecording(): Boolean {
        val result = recorder.isRecording()
        Log.d(TAG, "isRecording: $result")
        return result
    }

    @JavascriptInterface
    fun startRecording(): Boolean {
        Log.d(TAG, "startRecording called on thread: ${Thread.currentThread().name}")

        return try {
            val result = recorder.startRecording()
            Log.d(TAG, "startRecording result: $result")

            if (result) {
                // Notify web that recording started (must be on main thread)
                mainHandler.post {
                    Log.d(TAG, "Calling eunoNativeRecordingStarted")
                    runOnWebView("window.eunoNativeRecordingStarted && window.eunoNativeRecordingStarted()")
                }
            } else {
                Log.e(TAG, "Failed to start recording")
                mainHandler.post {
                    runOnWebView("window.eunoNativeRecordingError && window.eunoNativeRecordingError('Failed to start recording')")
                }
            }
            result
        } catch (e: Exception) {
            Log.e(TAG, "Exception in startRecording", e)
            mainHandler.post {
                runOnWebView("window.eunoNativeRecordingError && window.eunoNativeRecordingError('${e.message}')")
            }
            false
        }
    }

    @JavascriptInterface
    fun stopRecording() {
        Log.d(TAG, "stopRecording called on thread: ${Thread.currentThread().name}")

        // Prevent duplicate processing if VAD already triggered stop
        if (isProcessingStop) {
            Log.d(TAG, "Already processing stop from VAD, ignoring manual stop")
            return
        }

        // Run on main thread to ensure proper coroutine context
        mainHandler.post {
            handleAutoStop()  // Reuse the same stop logic
        }
    }

    private suspend fun transcribeAudio(audioFile: File) {
        withContext(Dispatchers.IO) {
            try {
                Log.d(TAG, "Uploading audio to $serverUrl/api/transcribe")

                val requestBody = MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart(
                        "audio",
                        "recording.wav",
                        audioFile.asRequestBody("audio/wav".toMediaType())
                    )
                    .build()

                val request = Request.Builder()
                    .url("$serverUrl/api/transcribe")
                    .post(requestBody)
                    .build()

                val response = client.newCall(request).execute()
                val responseBody = response.body?.string()

                Log.d(TAG, "Transcribe response: ${response.code}, body: $responseBody")

                audioFile.delete()

                if (response.isSuccessful && responseBody != null) {
                    val json = JSONObject(responseBody)
                    val text = json.optString("text", "")
                    Log.d(TAG, "Transcription text: $text")

                    withContext(Dispatchers.Main) {
                        // Escape the text for JavaScript
                        val escapedText = text
                            .replace("\\", "\\\\")
                            .replace("'", "\\'")
                            .replace("\"", "\\\"")
                            .replace("\n", "\\n")
                            .replace("\r", "")

                        runOnWebView("window.eunoNativeTranscription && window.eunoNativeTranscription('$escapedText')")
                    }
                } else {
                    Log.e(TAG, "Transcription failed: ${response.code}")
                    withContext(Dispatchers.Main) {
                        runOnWebView("window.eunoNativeRecordingError && window.eunoNativeRecordingError('Transcription failed: ${response.code}')")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Transcription error", e)
                withContext(Dispatchers.Main) {
                    val errorMsg = e.message?.replace("'", "\\'") ?: "Unknown error"
                    runOnWebView("window.eunoNativeRecordingError && window.eunoNativeRecordingError('$errorMsg')")
                }
            }
        }
    }

    private fun runOnWebView(js: String) {
        Log.d(TAG, "Executing JS: $js")
        webView.post {
            webView.evaluateJavascript(js, null)
        }
    }
}
