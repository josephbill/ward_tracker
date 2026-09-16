import React from "react";
import { useAppState } from "../state/AppContext";
import { Lang } from "../i18n/i18n";
import SearchableSelectList, { SelectOption } from "../components/SearchableSelectList";
import { trackEvent } from "../services/analytics";

// The instructional prompt itself is kept to English + Swahili only (the
// two languages a first-time visitor to this screen is overwhelmingly
// likely to read something in) — a resident who only reads Kikamba can
// still recognize "Kĩkamba" as a list option below. All 3 languages remain
// fully selectable; only the *instruction copy* is simplified.
//
// Labels are shown in each language's own script so a resident can
// recognize their language even before anything else on screen is in a
// language they read — a search box on top of 3 languages looks like
// overkill today, but the list is built to scale to many more without a
// redesign (Section 4's "ask before assuming beyond these" 3 languages).
const LANGUAGE_OPTIONS: SelectOption[] = [
  { value: "en", label: "English" },
  { value: "sw", label: "Kiswahili" },
  { value: "kam", label: "Kĩkamba" },
];

export default function LanguageSelectScreen({ navigation }: any) {
  const { setLang } = useAppState();

  const choose = (value: string) => {
    setLang(value as Lang);
    trackEvent("language_selected", { lang: value });
    navigation.replace("CountySelect");
  };

  return (
    <SearchableSelectList
      icon="🌍"
      title="Choose your language"
      subtitle="Chagua lugha yako"
      searchPlaceholder="Search / Tafuta"
      options={LANGUAGE_OPTIONS}
      onSelect={choose}
    />
  );
}
