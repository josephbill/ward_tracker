import React, { useEffect, useState } from "react";
import { Text } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchCounties } from "../api/client";
import SearchableSelectList, { SelectOption } from "../components/SearchableSelectList";
import { trackEvent } from "../services/analytics";

export default function CountySelectScreen({ navigation }: any) {
  const { lang, setCounty } = useAppState();
  const l = lang || "sw";
  const [options, setOptions] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchCounties()
      .then((data) => setOptions(data.counties.map((c) => ({ value: c, label: c }))))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const choose = (value: string) => {
    setCounty(value);
    trackEvent("county_selected", { county: value });
    navigation.replace("WardSelect");
  };

  if (error) {
    return <Text style={{ padding: 24, textAlign: "center", color: "#777" }}>{t(l, "connectionRequiredFirstLoad")}</Text>;
  }

  return (
    <SearchableSelectList
      icon="📍"
      title={t(l, "selectCounty")}
      searchPlaceholder={t(l, "searchCounty")}
      options={options}
      loading={loading}
      onSelect={choose}
      emptyText={t(l, "noCountiesFound")}
    />
  );
}
