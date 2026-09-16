import React, { useEffect, useState } from "react";
import { Pressable, Text, StyleSheet, ActivityIndicator } from "react-native";
import { Lang } from "../i18n/i18n";
import { t } from "../i18n/i18n";
import { speak, stopSpeaking, isTtsAvailableForLang } from "../services/tts";

interface Props {
  text: string;
  lang: Lang;
}

/** "Listen" button for accessibility — reads `text` aloud in `lang` via the
 * device's TTS engine. Disables itself with an explanatory note when the
 * device has no voice for that language (always true for Kikamba today —
 * see services/tts.ts). */
export default function ListenButton({ text, lang }: Props) {
  const [available, setAvailable] = useState<boolean | null>(null);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    isTtsAvailableForLang(lang).then((ok) => {
      if (!cancelled) setAvailable(ok);
    });
    return () => {
      cancelled = true;
      stopSpeaking();
    };
  }, [lang]);

  const toggle = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    speak(text, lang, () => setSpeaking(false));
  };

  if (available === null) {
    return <ActivityIndicator size="small" style={{ marginVertical: 8 }} />;
  }

  if (!available) {
    return <Text style={styles.unavailable}>{t(lang, "audioNotAvailableForLanguage")}</Text>;
  }

  return (
    <Pressable style={styles.button} onPress={toggle}>
      <Text style={styles.buttonText}>{speaking ? `⏹ ${t(lang, "stopListening")}` : `🔊 ${t(lang, "listenToProject")}`}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: { borderWidth: 1, borderColor: "#0b6e4f", borderRadius: 8, paddingVertical: 10, paddingHorizontal: 14, alignSelf: "flex-start", marginBottom: 12 },
  buttonText: { color: "#0b6e4f", fontWeight: "600", fontSize: 13 },
  unavailable: { fontSize: 11, color: "#999", marginBottom: 12, fontStyle: "italic" },
});
