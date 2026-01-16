package com.euno.app

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.euno.app.utils.PreferencesManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class SetupActivity : AppCompatActivity() {

    private lateinit var prefs: PreferencesManager
    private lateinit var serverIpInput: EditText
    private lateinit var serverPortInput: EditText
    private lateinit var connectButton: Button
    private lateinit var loadingIndicator: ProgressBar
    private lateinit var errorText: TextView

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        prefs = PreferencesManager(this)

        // If setup is already complete, go directly to main
        if (prefs.isSetupComplete()) {
            startMainActivity()
            return
        }

        setContentView(R.layout.activity_setup)

        serverIpInput = findViewById(R.id.serverIpInput)
        serverPortInput = findViewById(R.id.serverPortInput)
        connectButton = findViewById(R.id.connectButton)
        loadingIndicator = findViewById(R.id.loadingIndicator)
        errorText = findViewById(R.id.errorText)

        // Set default port (80 for standard HTTP)
        serverPortInput.setText("80")

        connectButton.setOnClickListener {
            attemptConnection()
        }
    }

    private fun attemptConnection() {
        val ip = serverIpInput.text.toString().trim()
        val portStr = serverPortInput.text.toString().trim()

        // Validate IP
        if (ip.isEmpty()) {
            showError(getString(R.string.setup_error_empty_ip))
            return
        }

        // Validate port (default to 80 for standard HTTP)
        val port = if (portStr.isEmpty()) 80 else (portStr.toIntOrNull() ?: 80)

        // Show loading state
        setLoading(true)
        hideError()

        // Build URL - omit port for standard HTTP (80) and HTTPS (443)
        val serverUrl = if (port == 80) "http://$ip" else "http://$ip:$port"

        // Test connection in background
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val request = Request.Builder()
                    .url("$serverUrl/api/agents")
                    .build()

                val response = client.newCall(request).execute()

                withContext(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        // Save settings and proceed
                        prefs.setServerAddress(ip, port)
                        // Enable notifications by default
                        prefs.setNotificationServiceEnabled(true)
                        startMainActivity()
                    } else {
                        setLoading(false)
                        showError("${getString(R.string.setup_error_connection_failed)} (${response.code})")
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    setLoading(false)
                    showError("${getString(R.string.setup_error_connection_failed)}: ${e.localizedMessage}")
                }
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        connectButton.isEnabled = !loading
        connectButton.text = if (loading) {
            getString(R.string.setup_connecting)
        } else {
            getString(R.string.setup_connect)
        }
        loadingIndicator.visibility = if (loading) View.VISIBLE else View.GONE
        serverIpInput.isEnabled = !loading
        serverPortInput.isEnabled = !loading
    }

    private fun showError(message: String) {
        errorText.text = message
        errorText.visibility = View.VISIBLE
    }

    private fun hideError() {
        errorText.visibility = View.GONE
    }

    private fun startMainActivity() {
        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}
