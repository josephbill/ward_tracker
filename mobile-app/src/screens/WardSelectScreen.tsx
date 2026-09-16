import React, { useEffect, useState } from "react";
import { Text } from "react-native";
import { useAppState } from "../state/AppContext";
import { t } from "../i18n/i18n";
import { fetchWards } from "../api/client";
import SearchableSelectList, { SelectOption } from "../components/SearchableSelectList";
import { trackEvent } from "../services/analytics";

export default function WardSelectScreen({ navigation }: any) {
  const { lang, county, setWard } = useAppState();
  const l = lang || "en";
  const [options, setOptions] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchWards(county || undefined)
      .then((data) => setOptions(data.wards.map((w) => ({ value: w, label: w, sublabel: county || undefined }))))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [county]);

  const choose = (value: string) => {
    setWard(value);
    trackEvent("ward_selected", { ward: value, county });
    navigation.replace("WardProjects");
  };

  if (error) {
    return <Text style={{ padding: 24, textAlign: "center", color: "#777" }}>{t(l, "connectionRequiredFirstLoad")}</Text>;
  }

  return (
    <SearchableSelectList
      icon="🏘️"
      title={t(l, "selectWard")}
      subtitle={county ?? undefined}
      searchPlaceholder={t(l, "searchWard")}
      options={options}
      loading={loading}
      onSelect={choose}
      emptyText={t(l, "noWardsFound")}
    />
  );
}
