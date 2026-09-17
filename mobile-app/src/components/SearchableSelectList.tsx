import React, { useMemo, useState } from "react";
import { View, Text, TextInput, FlatList, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export interface SelectOption {
  value: string;
  label: string;
  sublabel?: string;
}

interface Props {
  icon?: string; // single emoji shown in a badge above the title
  title: string;
  subtitle?: string;
  searchPlaceholder: string;
  options: SelectOption[];
  onSelect: (value: string) => void;
  loading?: boolean;
  emptyText?: string;
  footer?: string; // small print below the list, e.g. a privacy notice
}

/**
 * Shared scroll + search picker used for language, county, and ward
 * selection — one component so the journey (language -> county -> ward)
 * feels like one consistent pattern rather than three different UIs, and so
 * it scales to many more options than fit as buttons on screen (e.g. all 47
 * Kenyan counties, or a long county's ward list) without redesign.
 */
export default function SearchableSelectList({
  icon,
  title,
  subtitle,
  searchPlaceholder,
  options,
  onSelect,
  loading,
  emptyText,
  footer,
}: Props) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (o) => o.label.toLowerCase().includes(q) || o.sublabel?.toLowerCase().includes(q)
    );
  }, [options, query]);

  return (
    // "top" is deliberately excluded — these screens now render inside a
    // real native-stack header (see App.tsx), which already accounts for
    // the status bar/notch inset; adding it again here would just leave an
    // oversized gap between the header and this screen's own title.
    <SafeAreaView style={styles.container} edges={["left", "right", "bottom"]}>
      <View style={styles.header}>
        {icon ? (
          <View style={styles.iconBadge}>
            <Text style={styles.iconBadgeText}>{icon}</Text>
          </View>
        ) : null}
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>

      <TextInput
        style={styles.searchInput}
        placeholder={searchPlaceholder}
        placeholderTextColor="#9aa5a1"
        value={query}
        onChangeText={setQuery}
        autoCorrect={false}
        autoCapitalize="none"
        accessibilityLabel={searchPlaceholder}
      />
      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} color="#0b6e4f" />
      ) : filtered.length === 0 ? (
        <Text style={styles.empty}>{emptyText ?? "No matches"}</Text>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(o) => o.value}
          contentContainerStyle={{ paddingBottom: 24 }}
          keyboardShouldPersistTaps="handled"
          renderItem={({ item }) => (
            <Pressable
              style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
              onPress={() => onSelect(item.value)}
              accessibilityRole="button"
              accessibilityLabel={item.sublabel ? `${item.label}, ${item.sublabel}` : item.label}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.rowLabel}>{item.label}</Text>
                {item.sublabel ? <Text style={styles.rowSublabel}>{item.sublabel}</Text> : null}
              </View>
              <Text style={styles.chevron}>›</Text>
            </Pressable>
          )}
        />
      )}
      {footer ? <Text style={styles.footer}>{footer}</Text> : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f7f9f8", paddingHorizontal: 20 },
  header: { alignItems: "center", marginTop: 12, marginBottom: 20 },
  iconBadge: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: "#e6f4ef",
    alignItems: "center", justifyContent: "center", marginBottom: 12,
  },
  iconBadgeText: { fontSize: 28 },
  title: { fontSize: 21, fontWeight: "700", textAlign: "center", color: "#14231e" },
  subtitle: { fontSize: 14, color: "#5b6b66", textAlign: "center", marginTop: 6, lineHeight: 20 },
  searchInput: {
    backgroundColor: "#fff", borderWidth: 1, borderColor: "#dde5e2", borderRadius: 12,
    padding: 13, fontSize: 15, marginBottom: 14,
  },
  empty: { textAlign: "center", marginTop: 32, color: "#777" },
  row: {
    flexDirection: "row", alignItems: "center", backgroundColor: "#fff",
    borderRadius: 12, paddingVertical: 16, paddingHorizontal: 16, marginBottom: 10,
    borderWidth: 1, borderColor: "#e9efec",
  },
  rowPressed: { backgroundColor: "#eef6f3", borderColor: "#0b6e4f" },
  rowLabel: { fontSize: 16, fontWeight: "600", color: "#14231e" },
  rowSublabel: { fontSize: 13, color: "#777", marginTop: 2 },
  chevron: { fontSize: 22, color: "#0b6e4f", marginLeft: 8 },
  footer: { fontSize: 11, color: "#8a938f", textAlign: "center", marginTop: 8, marginBottom: 4, lineHeight: 16 },
});
