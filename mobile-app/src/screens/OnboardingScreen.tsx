import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ScrollView,
  NativeSyntheticEvent,
  NativeScrollEvent,
  useWindowDimensions,
} from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { trackEvent } from "../services/analytics";

/**
 * Shown once, right after language selection, before county/ward pick
 * (Section 3's onboarding gap-fill — first-time residents landed straight
 * on a ward picker with no explanation of what the app is for or how the
 * pieces fit together). A short story arc, not a feature tour: promise ->
 * transparency -> your voice -> trust -> access-for-everyone -> "let's go".
 * Addressed directly to the reader ("you", "your ward") rather than through
 * an invented named character, so it stays personal without asking every
 * translation to carry a persona's gender/background along with it.
 *
 * Illustrations are deliberately abstract geometric color blocks (no photos
 * or drawn figures) in a warm earth-tone palette — terracotta, ochre, deep
 * green, indigo — evoking East African textile and landscape color without
 * attempting to depict specific people, which this app has no way to source
 * or generate responsibly. Icons are plain emoji, matching the rest of the
 * app's existing icon convention (see LanguageSelectScreen's 🌍).
 */
const CARDS: { key: string; icon: string; base: string; accent: string }[] = [
  { key: "onboarding1", icon: "📋", base: "#b6532c", accent: "#e2a63c" },
  { key: "onboarding2", icon: "🔍", base: "#0b6e4f", accent: "#5fae8c" },
  { key: "onboarding3", icon: "🗣️", base: "#c1502e", accent: "#f0b27a" },
  { key: "onboarding4", icon: "🔒", base: "#1e3a5f", accent: "#5a82ab" },
  { key: "onboarding5", icon: "📶", base: "#d99a2b", accent: "#f4d58d" },
];

export default function OnboardingScreen({ navigation }: any) {
  const { lang, setOnboardingSeen } = useAppState();
  const { width } = useWindowDimensions();
  const scrollRef = useRef<ScrollView>(null);
  const [index, setIndex] = useState(0);

  // Defensive guard, matching the pattern ReportScreen uses for
  // phoneVerified: initialRoute() in App.tsx already only routes here once
  // a language is chosen, but that's a one-time check at Stack.Navigator
  // mount, not a standing rule — this makes it impossible to actually
  // render the story in no particular language (which would otherwise
  // silently fall back to Swahili copy for a resident who never chose it)
  // however this screen ends up reached.
  useEffect(() => {
    if (!lang) navigation.replace("LanguageSelect");
  }, [lang]);
  if (!lang) return null;
  const l = lang;

  const finish = (via: "skip" | "complete") => {
    setOnboardingSeen(true);
    trackEvent("onboarding_finished", { via, last_card: index + 1 });
    navigation.replace("CountySelect");
  };

  const goToCard = (next: number) => {
    // animated: false — react-native-web's ScrollView doesn't reliably
    // complete an animated programmatic scrollTo across a full page width
    // (confirmed in the web preview: the scroll position advanced a few
    // pixels then stopped short of the next card, leaving the dots/index
    // state out of sync with what was actually on screen). An instant jump
    // is standard for a "Next" button anyway — swiping between cards still
    // gets the browser's native smooth momentum scroll.
    scrollRef.current?.scrollTo({ x: next * width, animated: false });
    setIndex(next);
  };

  const onMomentumScrollEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const next = Math.round(e.nativeEvent.contentOffset.x / width);
    setIndex(next);
  };

  const isLast = index === CARDS.length - 1;

  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <View style={styles.dots}>
          {CARDS.map((c, i) => (
            <View key={c.key} style={[styles.dot, i === index && styles.dotActive]} />
          ))}
        </View>
        <Pressable
          onPress={() => finish("skip")}
          accessibilityRole="button"
          accessibilityLabel={t(l, "onboardingSkip")}
          style={styles.skipButton}
        >
          <Text style={styles.skipText}>{t(l, "onboardingSkip")}</Text>
        </Pressable>
      </View>

      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onMomentumScrollEnd}
        accessibilityLabel={t(l, "onboardingProgress", { current: index + 1, total: CARDS.length })}
      >
        {CARDS.map((card) => (
          <View key={card.key} style={[styles.card, { width }]}>
            <View style={[styles.illustration, { backgroundColor: card.base }]}>
              <View style={[styles.shapeA, { backgroundColor: card.accent }]} />
              <View style={[styles.shapeB, { borderBottomColor: card.accent }]} />
              <View style={[styles.shapeC, { backgroundColor: card.accent }]} />
              <Text style={styles.illustrationIcon}>{card.icon}</Text>
            </View>
            <Text style={styles.cardTitle}>{t(l, `${card.key}Title`)}</Text>
            <Text style={styles.cardBody}>{t(l, `${card.key}Body`)}</Text>
          </View>
        ))}
      </ScrollView>

      <View style={styles.bottomRow}>
        <Pressable
          style={styles.primaryButton}
          onPress={() => (isLast ? finish("complete") : goToCard(index + 1))}
          accessibilityRole="button"
          accessibilityLabel={t(l, isLast ? "onboardingGetStarted" : "onboardingNext")}
        >
          <Text style={styles.primaryButtonText}>
            {t(l, isLast ? "onboardingGetStarted" : "onboardingNext")}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: 56,
    paddingHorizontal: 20,
    paddingBottom: 8,
  },
  dots: { flexDirection: "row", gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#ddd" },
  dotActive: { backgroundColor: "#0b6e4f", width: 20 },
  skipButton: { minHeight: 44, justifyContent: "center", paddingHorizontal: 4 },
  skipText: { color: "#888", fontSize: 14, fontWeight: "600" },
  card: { padding: 24, alignItems: "center" },
  illustration: {
    width: "100%",
    height: 220,
    borderRadius: 20,
    marginBottom: 28,
    marginTop: 12,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  shapeA: {
    position: "absolute",
    width: 140,
    height: 140,
    borderRadius: 24,
    opacity: 0.35,
    top: -40,
    left: -30,
    transform: [{ rotate: "20deg" }],
  },
  shapeB: {
    position: "absolute",
    width: 0,
    height: 0,
    borderLeftWidth: 90,
    borderRightWidth: 90,
    borderBottomWidth: 150,
    borderLeftColor: "transparent",
    borderRightColor: "transparent",
    opacity: 0.25,
    bottom: -60,
    right: -50,
    transform: [{ rotate: "12deg" }],
  },
  shapeC: {
    position: "absolute",
    width: 70,
    height: 70,
    borderRadius: 35,
    opacity: 0.3,
    bottom: -10,
    left: 30,
  },
  illustrationIcon: { fontSize: 56 },
  cardTitle: { fontSize: 21, fontWeight: "700", color: "#222", textAlign: "center", marginBottom: 14 },
  cardBody: { fontSize: 15, color: "#555", textAlign: "center", lineHeight: 22 },
  bottomRow: { padding: 20, paddingBottom: 32 },
  primaryButton: { backgroundColor: "#0b6e4f", padding: 16, borderRadius: 10 },
  primaryButtonText: { color: "#fff", textAlign: "center", fontWeight: "700", fontSize: 16 },
});
