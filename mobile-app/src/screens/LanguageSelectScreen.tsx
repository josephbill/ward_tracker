import React from "react";
import { useAppState } from "../state/AppContext";
import { Lang } from "../i18n/i18n";
import SearchableSelectList, { SelectOption } from "../components/SearchableSelectList";
import { trackEvent } from "../services/analytics";

// The instructional prompt itself is kept to Kiswahili + English only (the
// two languages a first-time visitor to this screen is overwhelmingly
// likely to read something in) — a resident who only reads Kikamba can
// still recognize "Kĩkamba" as a list option below. All 3 languages remain
// fully selectable; only the *instruction copy* is simplified. Kiswahili is
// the app's primary/default language (see Config.DEFAULT_LANGUAGE on the
// backend and SUPPORTED_LANGUAGES in i18n.ts) so it leads both the heading
// and the option list; English remains a fully supported translation.
//
// Labels are shown in each language's own script so a resident can
// recognize their language even before anything else on screen is in a
// language they read — a search box on top of 3 languages looks like
// overkill today, but the list is built to scale to many more without a
// redesign (Section 4's "ask before assuming beyond these" 3 languages).
const LANGUAGE_OPTIONS: SelectOption[] = [
  { value: "sw", label: "Kiswahili" },
  { value: "en", label: "English" },
  { value: "kam", label: "Kĩkamba" },
];

export default function LanguageSelectScreen({ navigation }: any) {
  const { setLang, onboardingSeen } = useAppState();

  const choose = (value: string) => {
    setLang(value as Lang);
    trackEvent("language_selected", { lang: value });
    // Only a genuine first-time pick goes through the onboarding story.
    // This screen is also reached later as "Badilisha lugha" from the menu
    // (NavMenu.tsx) for a resident who's already set up and browsing —
    // routing that case through Onboarding too (as this used to,
    // unconditionally) forced them through the whole story again and then
    // dumped them back on CountySelect, discarding their place in the app
    // even though their county/ward choice was still saved underneath.
    if (onboardingSeen && navigation.canGoBack()) {
      navigation.goBack();
    } else if (onboardingSeen) {
      // Reached with nothing to go back to (e.g. a deep link straight to
      // this screen) — land somewhere useful rather than a no-op goBack().
      navigation.replace("WardProjects");
    } else {
      navigation.replace("Onboarding");
    }
  };

  return (
    <SearchableSelectList
      icon="🌍"
      title="Chagua lugha yako"
      subtitle="Choose your language"
      searchPlaceholder="Search / Tafuta"
      options={LANGUAGE_OPTIONS}
      onSelect={choose}
      footer="Your reports are anonymous and your GPS is only kept to neighbourhood-level precision — see Kenya's Data Protection Act 2019 (ODPC). / Taarifa zako ni za siri na eneo lako halihifadhiwi kwa usahihi kamili."
    />
  );
}
