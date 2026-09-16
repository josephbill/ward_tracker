# Bluetooth relay — running it for real

`bleHub.ts` and `bleReporter.ts` are complete, but `react-native-ble-plx` is
a native module: it cannot run inside Expo Go, and isn't installed in this
PoC's `package.json` to keep the default `npx expo start --web` demo path
dependency-light. To actually run the Bluetooth relay on two phones:

1. `npx expo install react-native-ble-plx`
2. `npx expo prebuild` (generates native `ios`/`android` projects)
3. Build a **dev client** — `npx expo run:android` (needs Android
   Studio/SDK) or use [EAS Build](https://docs.expo.dev/build/introduction/)
   for a cloud build if you don't have the Android SDK locally.
4. Install the dev client on two Android phones. One runs hub mode
   (`bleHub.startAdvertisingAsHub()`), the other queues a report while
   offline and calls `bleReporter.scanForHubs()` /
   `handOffQueueToHub()` once it finds the hub.
5. iOS: background BLE scanning is restricted, so both the hub and the
   reporter app need to stay in the foreground during the handshake — fine
   for a staged demo, not for production background relay.

For the hackathon demo itself, `scripts/simulate_bluetooth_relay.py` plays
out the identical store-and-forward sequence against the real backend
without needing a native build or two physical devices — see
`docs/DEMO_SCRIPT.md` step 5.
