/**
 * Cross-platform "show the user a message" helper.
 *
 * react-native-web's Alert.alert() doesn't reliably render a dialog at all
 * on web (no polyfill ships with Expo's web target) — its onPress callback
 * never fires either, which is what left residents stuck on a screen after
 * a successful report/issue submit (see ReportScreen/ReportIssueScreen's
 * submit(), fixed by navigating directly instead of waiting on an Alert
 * button press). For every OTHER Alert.alert call in the app — permission
 * explainers, OTP errors, generic error messages — there's no navigation to
 * decouple; the fix here is simpler: use the browser's own window.alert()
 * on web (synchronous, always renders, needs no callback) and the real
 * native Alert.alert() everywhere else.
 */
import { Alert, Platform } from "react-native";

export function showAlert(title: string, message?: string): void {
  if (Platform.OS === "web") {
    // eslint-disable-next-line no-alert
    window.alert(message ? `${title}\n\n${message}` : title);
    return;
  }
  Alert.alert(title, message);
}
