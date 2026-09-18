import React, { useRef, useState } from "react";
import { Pressable, Text, StyleSheet, Platform } from "react-native";
import * as audioRecorder from "../services/audioRecorder";
import { Lang } from "../i18n/i18n";
import { t } from "../i18n/i18n";
import { transcribeVoice } from "../api/client";
import { showAlert } from "../services/alert";

interface Props {
  lang: Lang;
  onTranscript: (text: string) => void;
}

// Maps our 3 app languages to BCP-47 tags the Web Speech API / native STT
// backend expect. Kikamba has no standard speech-recognition locale, same
// constraint as text-to-speech (see services/tts.ts) — voice input for
// Kikamba falls back to typing.
const RECOGNITION_LOCALE: Partial<Record<Lang, string>> = { en: "en-US", sw: "sw-KE" };

/**
 * Voice-to-text for reporting (Section 9 item 1).
 *
 * - Web: uses the browser's built-in Web Speech API (SpeechRecognition) —
 *   a real, working live-transcription experience, no server round trip.
 * - Native (Android/iOS via Expo Go): there's no on-device speech-to-text
 *   API available without a custom dev client, so this records audio with
 *   expo-av and uploads it to POST /api/voice/transcribe. That endpoint is
 *   real, tested plumbing, but returns an empty transcript by default (see
 *   backend/app/services/stt.py) until a real STT credential is configured
 *   — the resident always sees why nothing appeared and can type instead.
 */
export default function VoiceInputButton({ lang, onTranscript }: Props) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const recognitionRef = useRef<any>(null);

  const locale = RECOGNITION_LOCALE[lang];
  if (!locale) {
    return <Text style={styles.unavailable}>{t(lang, "voiceInputNotAvailableForLanguage")}</Text>;
  }

  const startWeb = () => {
    const SpeechRecognition = (globalThis as any).SpeechRecognition || (globalThis as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      showAlert(t(lang, "genericErrorTitle"), t(lang, "voiceInputNotAvailableOnDevice"));
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = locale;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event: any) => {
      const text = event.results?.[0]?.[0]?.transcript;
      if (text) onTranscript(text);
    };
    recognition.onerror = () => setRecording(false);
    recognition.onend = () => setRecording(false);
    recognitionRef.current = recognition;
    recognition.start();
    setRecording(true);
  };

  const stopWeb = () => {
    recognitionRef.current?.stop();
    setRecording(false);
  };

  const startNative = async () => {
    const granted = await audioRecorder.requestPermission();
    if (!granted) {
      showAlert(t(lang, "permissionNeededTitle"), t(lang, "microphonePermissionExplainer"));
      return;
    }
    await audioRecorder.startRecording();
    setRecording(true);
  };

  const stopNative = async () => {
    setRecording(false);
    setBusy(true);
    try {
      const uri = await audioRecorder.stopRecording();
      if (!uri) return;
      const { transcript } = await transcribeVoice(uri, lang);
      if (transcript) {
        onTranscript(transcript);
      } else {
        showAlert(t(lang, "voiceRecordedTitle"), t(lang, "voiceInputNotAvailableOnDevice"));
      }
    } catch (err: any) {
      showAlert(t(lang, "genericErrorTitle"), err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggle = () => {
    if (Platform.OS === "web") {
      recording ? stopWeb() : startWeb();
    } else {
      recording ? stopNative() : startNative();
    }
  };

  return (
    <Pressable style={[styles.button, recording && styles.buttonActive]} onPress={toggle} disabled={busy}>
      <Text style={[styles.buttonText, recording && styles.buttonTextActive]}>
        {busy ? t(lang, "transcribing") : recording ? `⏺ ${t(lang, "stopRecording")}` : `🎙 ${t(lang, "recordVoiceNote")}`}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: { borderWidth: 1, borderColor: "#0b6e4f", borderRadius: 8, paddingVertical: 10, paddingHorizontal: 14, alignSelf: "flex-start" },
  buttonActive: { backgroundColor: "#0b6e4f" },
  buttonText: { color: "#0b6e4f", fontWeight: "600", fontSize: 13 },
  buttonTextActive: { color: "#fff" },
  unavailable: { fontSize: 11, color: "#999", fontStyle: "italic" },
});
