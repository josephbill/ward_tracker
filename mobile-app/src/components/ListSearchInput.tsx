import React from "react";
import { TextInput, StyleSheet } from "react-native";

interface Props {
  value: string;
  onChangeText: (text: string) => void;
  placeholder: string;
}

/**
 * Shared search box for in-app listing screens (ward projects, local
 * issues, my reports) — separate from SearchableSelectList, which is
 * purpose-built for the language/county/ward picker flow (full-screen,
 * icon header, footer notice) rather than a filter bar sitting above an
 * already-visible list.
 */
export default function ListSearchInput({ value, onChangeText, placeholder }: Props) {
  return (
    <TextInput
      style={styles.input}
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor="#9aa5a1"
      autoCorrect={false}
      autoCapitalize="none"
      accessibilityLabel={placeholder}
    />
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#dde5e2",
    borderRadius: 12,
    padding: 13,
    fontSize: 15,
    marginBottom: 14,
  },
});
