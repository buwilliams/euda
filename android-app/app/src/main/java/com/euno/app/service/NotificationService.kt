package com.euno.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import com.euno.app.MainActivity
import com.euno.app.R
import com.euno.app.utils.AppState
import com.euno.app.utils.PreferencesManager
import com.euno.app.utils.SSEClient
import org.json.JSONObject

class NotificationService : Service() {

    companion object {
        private const val TAG = "NotificationService"
        private const val FOREGROUND_NOTIFICATION_ID = 1
        private const val CHANNEL_FOREGROUND = "euno_service"
        private const val CHANNEL_MESSAGES = "euno_messages"

        private const val INITIAL_RECONNECT_DELAY = 1000L  // 1 second
        private const val MAX_RECONNECT_DELAY = 60000L    // 60 seconds
    }

    private var sseClient: SSEClient? = null
    private var reconnectDelay = INITIAL_RECONNECT_DELAY
    private val handler = Handler(Looper.getMainLooper())
    private var isRunning = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isRunning) {
            isRunning = true
            startForeground(FOREGROUND_NOTIFICATION_ID, buildForegroundNotification(false))
            connectSSE()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        isRunning = false
        handler.removeCallbacksAndMessages(null)
        sseClient?.disconnect()
        sseClient = null
        super.onDestroy()
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        super.onTaskRemoved(rootIntent)
        // App was swiped away from recents - restart service to maintain connection
        Log.d(TAG, "Task removed, restarting service")
        val restartIntent = Intent(applicationContext, NotificationService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(restartIntent)
        } else {
            startService(restartIntent)
        }
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)

            // Foreground service channel (low importance, silent)
            val serviceChannel = NotificationChannel(
                CHANNEL_FOREGROUND,
                getString(R.string.notification_channel_service),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.notification_channel_service_description)
                setShowBadge(false)
            }
            notificationManager.createNotificationChannel(serviceChannel)

            // Messages channel (default importance)
            val messagesChannel = NotificationChannel(
                CHANNEL_MESSAGES,
                getString(R.string.notification_channel_messages),
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = getString(R.string.notification_channel_messages_description)
            }
            notificationManager.createNotificationChannel(messagesChannel)
        }
    }

    private fun buildForegroundNotification(connected: Boolean): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val text = if (connected) {
            getString(R.string.notification_service_text)
        } else {
            getString(R.string.notification_service_connecting)
        }

        return NotificationCompat.Builder(this, CHANNEL_FOREGROUND)
            .setContentTitle(getString(R.string.notification_service_title))
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_notification)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateForegroundNotification(connected: Boolean) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(FOREGROUND_NOTIFICATION_ID, buildForegroundNotification(connected))
    }

    private fun connectSSE() {
        val serverUrl = PreferencesManager(this).getServerUrl()
        if (serverUrl == null) {
            Log.e(TAG, "No server URL configured")
            stopSelf()
            return
        }

        sseClient?.disconnect()
        sseClient = SSEClient(
            serverUrl = serverUrl,
            onEvent = { type, data -> handleEvent(type, data) },
            onConnected = {
                Log.d(TAG, "SSE connected")
                reconnectDelay = INITIAL_RECONNECT_DELAY
                handler.post {
                    updateForegroundNotification(true)
                }
            },
            onDisconnected = {
                Log.d(TAG, "SSE disconnected")
                handler.post {
                    updateForegroundNotification(false)
                    scheduleReconnect()
                }
            },
            onError = { e ->
                Log.e(TAG, "SSE error: ${e.message}")
                handler.post {
                    updateForegroundNotification(false)
                    scheduleReconnect()
                }
            }
        )
        sseClient?.connect()
    }

    private fun scheduleReconnect() {
        if (!isRunning) return

        Log.d(TAG, "Scheduling reconnect in ${reconnectDelay}ms")
        handler.postDelayed({
            if (isRunning) {
                connectSSE()
            }
        }, reconnectDelay)

        // Exponential backoff
        reconnectDelay = (reconnectDelay * 2).coerceAtMost(MAX_RECONNECT_DELAY)
    }

    private fun handleEvent(type: String, data: String) {
        Log.d(TAG, "Received event: $type")

        when (type) {
            "agent_message" -> {
                try {
                    val json = JSONObject(data)
                    val agent = json.optString("agent", "Euno")
                    val message = json.optString("message", "")
                    if (message.isNotEmpty()) {
                        showMessageNotification(agent, message)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse agent_message: ${e.message}")
                }
            }
            "ping" -> {
                // Keepalive, no action needed
            }
            // Could handle other event types like jobs_update, chat_update
        }
    }

    private fun showMessageNotification(title: String, body: String) {
        // Only show notification if app is NOT in foreground
        if (AppState.isInForeground()) {
            Log.d(TAG, "App in foreground, suppressing notification")
            return
        }

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, System.currentTimeMillis().toInt(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_MESSAGES)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
        Log.d(TAG, "Notification shown: $title")
    }
}
