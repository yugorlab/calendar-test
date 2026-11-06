# Kyodo Events — Android foundation

This is the first Android integration layer for the existing Kyodo Events website.
The website remains the source UI; the Android app packages a local copy of its
HTML and calendar data with Capacitor.

## Fixed project identity

- App name: Kyodo Events
- Application ID: `app.yugorlab.kyodoevents`
- Minimum Android: 10 (API 29)
- Capacitor major: 8
- Android compile/target SDK baseline: 36

## Requirements

- Node.js 22+
- Android Studio 2025.2.1 or newer
- Android SDK Platform 36
- JDK 21 (Android Studio's bundled JDK is suitable)

See the official Capacitor environment setup:
https://capacitorjs.com/docs/getting-started/environment-setup

## First local setup

Run these commands from the repository root:

```bash
npm install
npm run prepare:web
npm run cap:add:android
node scripts/configure-android.mjs
npm run cap:sync
```

Then open Android Studio:

```bash
npm run android:open
```

Or build a debug APK from a machine with the Android SDK installed:

```bash
npm run android:debug
```

The debug APK is generated at:

`android/app/build/outputs/apk/debug/app-debug.apk`

## Architecture decisions

- `index.html` remains the web interface; it is copied to `www/` for packaging.
- `events.json` is copied alongside the page. The current relative `fetch('./events.json')`
  therefore works from the Capacitor app's local web origin without changing the website.
- Calendar-data updates and APK updates remain separate operations.
- Local Notifications and Preferences are included as dependencies for the next phase.
  Notification scheduling, event-diff logic, update checks, and background refresh are
  deliberately not enabled in this foundation step.
- Android 10 is the minimum installation version. The SDK target is a separate
  compatibility setting and is set to API 36 for the Capacitor 8 baseline.

## Important release note

Do not distribute a release APK until a permanent signing key is configured and stored
securely outside the repository (for CI, use encrypted GitHub Actions secrets).
Keep the same application ID and signing certificate for every upgrade.

## Current limitations

The initial wrapper bundles the calendar snapshot available at build time. The next
implementation phase should add a runtime refresh from the published `events.json`,
persist the last known snapshot, and compare stable event identities before enabling
change notifications. Background checks on Android are periodic/best-effort, not
real-time push delivery.
