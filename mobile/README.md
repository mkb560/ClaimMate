# ClaimMate Android App

Expo React Native implementation of the ClaimMate mobile app for Android.

## Setup

```bash
cd mobile
npm install
```

The app points to the Railway backend by default:

```bash
https://claimmate-backend-production.up.railway.app
```

Override it for local testing:

```bash
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000 npm start
```

`10.0.2.2` is the Android emulator address for the host machine.

## Run In Development

```bash
npm start
```

Then open the project in an Android emulator or Expo Go.

## Checks

```bash
npm run lint
npm run typecheck
```

## Build APK

```bash
npm run build:android
```

The `preview` EAS profile is configured to produce an installable APK.
