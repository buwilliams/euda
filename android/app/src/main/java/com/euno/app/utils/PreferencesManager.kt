package com.euno.app.utils

import android.content.Context
import android.content.SharedPreferences

class PreferencesManager(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        PREFS_NAME, Context.MODE_PRIVATE
    )

    companion object {
        private const val PREFS_NAME = "euno_prefs"
        private const val KEY_SERVER_IP = "server_ip"
        private const val KEY_SERVER_PORT = "server_port"
        private const val KEY_SETUP_COMPLETE = "setup_complete"
        private const val KEY_NOTIFICATIONS_ENABLED = "notifications_enabled"
        private const val DEFAULT_PORT = 80
    }

    fun getServerUrl(): String? {
        val ip = prefs.getString(KEY_SERVER_IP, null) ?: return null
        val port = prefs.getInt(KEY_SERVER_PORT, DEFAULT_PORT)
        // Omit port for standard HTTP (80)
        return if (port == 80) "http://$ip" else "http://$ip:$port"
    }

    fun getServerIp(): String? {
        return prefs.getString(KEY_SERVER_IP, null)
    }

    fun getServerPort(): Int {
        return prefs.getInt(KEY_SERVER_PORT, DEFAULT_PORT)
    }

    fun setServerAddress(ip: String, port: Int = DEFAULT_PORT) {
        prefs.edit()
            .putString(KEY_SERVER_IP, ip)
            .putInt(KEY_SERVER_PORT, port)
            .putBoolean(KEY_SETUP_COMPLETE, true)
            .apply()
    }

    fun isSetupComplete(): Boolean {
        return prefs.getBoolean(KEY_SETUP_COMPLETE, false)
    }

    fun isNotificationServiceEnabled(): Boolean {
        return prefs.getBoolean(KEY_NOTIFICATIONS_ENABLED, true)
    }

    fun setNotificationServiceEnabled(enabled: Boolean) {
        prefs.edit()
            .putBoolean(KEY_NOTIFICATIONS_ENABLED, enabled)
            .apply()
    }

    fun clearAll() {
        prefs.edit().clear().apply()
    }
}
