package com.euno.app.utils

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import java.util.concurrent.TimeUnit

class SSEClient(
    private val serverUrl: String,
    private val onEvent: (type: String, data: String) -> Unit,
    private val onConnected: () -> Unit = {},
    private val onDisconnected: () -> Unit = {},
    private val onError: (Exception) -> Unit = {}
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.SECONDS)  // No timeout for SSE
        .connectTimeout(30, TimeUnit.SECONDS)
        .build()

    private var eventSource: EventSource? = null
    private var isConnected = false

    fun connect() {
        val request = Request.Builder()
            .url("$serverUrl/api/events")
            .header("Accept", "text/event-stream")
            .build()

        val factory = EventSources.createFactory(client)
        eventSource = factory.newEventSource(request, object : EventSourceListener() {
            override fun onOpen(eventSource: EventSource, response: Response) {
                isConnected = true
                onConnected()
            }

            override fun onEvent(
                eventSource: EventSource,
                id: String?,
                type: String?,
                data: String
            ) {
                onEvent(type ?: "message", data)
            }

            override fun onClosed(eventSource: EventSource) {
                isConnected = false
                onDisconnected()
            }

            override fun onFailure(
                eventSource: EventSource,
                t: Throwable?,
                response: Response?
            ) {
                isConnected = false
                onError(t as? Exception ?: Exception("SSE connection failed: ${response?.code}"))
            }
        })
    }

    fun disconnect() {
        eventSource?.cancel()
        eventSource = null
        isConnected = false
    }

    fun isConnected(): Boolean = isConnected
}
