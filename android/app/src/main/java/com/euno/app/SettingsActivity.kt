package com.euno.app

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebStorage
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.euno.app.service.NotificationService
import com.euno.app.utils.PreferencesManager
import com.google.android.material.switchmaterial.SwitchMaterial

class SettingsActivity : AppCompatActivity() {

    private lateinit var prefs: PreferencesManager
    private lateinit var serverIpInput: EditText
    private lateinit var serverPortInput: EditText
    private lateinit var notificationsSwitch: SwitchMaterial
    private lateinit var saveButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        prefs = PreferencesManager(this)

        serverIpInput = findViewById(R.id.settingsServerIp)
        serverPortInput = findViewById(R.id.settingsServerPort)
        notificationsSwitch = findViewById(R.id.notificationsSwitch)
        saveButton = findViewById(R.id.saveButton)

        // Load current values
        serverIpInput.setText(prefs.getServerIp() ?: "")
        serverPortInput.setText(prefs.getServerPort().toString())
        notificationsSwitch.isChecked = prefs.isNotificationServiceEnabled()

        // Back button
        findViewById<ImageButton>(R.id.backButton).setOnClickListener {
            finish()
        }

        // Clear data button
        findViewById<android.widget.LinearLayout>(R.id.clearDataButton).setOnClickListener {
            showClearDataDialog()
        }

        // Save button
        saveButton.setOnClickListener {
            saveSettings()
        }

        // Handle notification switch changes
        notificationsSwitch.setOnCheckedChangeListener { _, isChecked ->
            prefs.setNotificationServiceEnabled(isChecked)
            if (isChecked) {
                startNotificationService()
            } else {
                stopNotificationService()
            }
        }
    }

    private fun saveSettings() {
        val ip = serverIpInput.text.toString().trim()
        val portStr = serverPortInput.text.toString().trim()
        val port = if (portStr.isEmpty()) 80 else (portStr.toIntOrNull() ?: 80)

        if (ip.isEmpty()) {
            serverIpInput.error = getString(R.string.setup_error_empty_ip)
            return
        }

        val currentIp = prefs.getServerIp()
        val currentPort = prefs.getServerPort()

        // Save new settings
        prefs.setServerAddress(ip, port)

        // If server changed, restart app
        if (ip != currentIp || port != currentPort) {
            Toast.makeText(this, "Settings saved. Reconnecting...", Toast.LENGTH_SHORT).show()

            // Restart to main activity
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        } else {
            Toast.makeText(this, "Settings saved", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    private fun showClearDataDialog() {
        AlertDialog.Builder(this)
            .setTitle(R.string.dialog_clear_data_title)
            .setMessage(R.string.dialog_clear_data_message)
            .setPositiveButton(R.string.dialog_clear) { _, _ ->
                clearAllData()
            }
            .setNegativeButton(R.string.dialog_cancel, null)
            .show()
    }

    private fun clearAllData() {
        // Stop notification service
        stopNotificationService()

        // Clear preferences
        prefs.clearAll()

        // Clear WebView data
        WebStorage.getInstance().deleteAllData()
        CookieManager.getInstance().removeAllCookies(null)
        CookieManager.getInstance().flush()

        // Go to setup
        val intent = Intent(this, SetupActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    private fun startNotificationService() {
        val intent = Intent(this, NotificationService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopNotificationService() {
        val intent = Intent(this, NotificationService::class.java)
        stopService(intent)
    }
}
