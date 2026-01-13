# Euno Android App

Android WebView client for Euno personal intelligence.

## Features

- WebView-based interface to your Euno server
- Server IP configuration with persistence
- Auto-granted microphone permissions for voice input
- Background notifications via SSE foreground service
- Settings to change server and toggle notifications

## Requirements

- Android 8.0 (API 26) or higher
- Android Studio or command-line build tools
- Your Euno server running and accessible

## Building

### Command Line

```bash
# Debug build
./gradlew assembleDebug

# Release build
./gradlew assembleRelease

# Install on connected device
./gradlew installDebug
```

### Android Studio

1. Open the `android-app` folder in Android Studio
2. Sync Gradle files
3. Run on device or emulator

## Installation

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Usage

1. **First Launch**: Enter your Euno server IP and port (default: 8000)
2. **Connect**: App validates connection before saving
3. **Use Euno**: Full web interface with voice input support
4. **Settings**: Long-press back or access from app to change server or toggle notifications

## Architecture

```
com.euno.app/
├── MainActivity.kt          # WebView container
├── SetupActivity.kt         # Server IP entry
├── SettingsActivity.kt      # Settings screen
├── EunoWebViewClient.kt     # URL handling
├── EunoWebChromeClient.kt   # Mic permission grants
├── BootReceiver.kt          # Auto-start on boot
├── service/
│   └── NotificationService.kt  # SSE background service
└── utils/
    ├── PreferencesManager.kt   # SharedPreferences
    └── SSEClient.kt            # SSE connection
```

## Permissions

- `INTERNET` - Network access
- `RECORD_AUDIO` - Voice input
- `POST_NOTIFICATIONS` - Push notifications
- `FOREGROUND_SERVICE` - Background SSE connection
- `RECEIVE_BOOT_COMPLETED` - Auto-start service

## Notes

- The app uses cleartext HTTP for local network access
- Microphone permissions are auto-granted for the configured server
- Background notifications require the foreground service to be enabled in settings
