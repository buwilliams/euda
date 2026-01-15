package com.euno.app.utils

/**
 * Global app state tracker.
 * Used to determine if the app is in foreground to control notification behavior.
 */
object AppState {
    @Volatile
    private var isInForeground = false

    fun setForeground(inForeground: Boolean) {
        isInForeground = inForeground
    }

    fun isInForeground(): Boolean {
        return isInForeground
    }
}
