import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Lang } from "../i18n/i18n";

interface AppState {
  lang: Lang | null;
  setLang: (lang: Lang) => void;
  county: string | null;
  setCounty: (county: string) => void;
  ward: string | null;
  setWard: (ward: string) => void;
  phone: string | null;
  phoneVerified: boolean;
  setPhone: (phone: string) => void;
  setPhoneVerified: (verified: boolean) => void;
  loaded: boolean;
}

const AppContext = createContext<AppState | null>(null);

const LANG_KEY = "@county-tracker/lang";
const COUNTY_KEY = "@county-tracker/county";
const WARD_KEY = "@county-tracker/ward";
const PHONE_KEY = "@county-tracker/phone";
const VERIFIED_KEY = "@county-tracker/phone_verified";

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang | null>(null);
  const [county, setCountyState] = useState<string | null>(null);
  const [ward, setWardState] = useState<string | null>(null);
  const [phone, setPhoneState] = useState<string | null>(null);
  const [phoneVerified, setPhoneVerifiedState] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    (async () => {
      const [storedLang, storedCounty, storedWard, storedPhone, storedVerified] = await Promise.all([
        AsyncStorage.getItem(LANG_KEY),
        AsyncStorage.getItem(COUNTY_KEY),
        AsyncStorage.getItem(WARD_KEY),
        AsyncStorage.getItem(PHONE_KEY),
        AsyncStorage.getItem(VERIFIED_KEY),
      ]);
      if (storedLang) setLangState(storedLang as Lang);
      if (storedCounty) setCountyState(storedCounty);
      if (storedWard) setWardState(storedWard);
      if (storedPhone) setPhoneState(storedPhone);
      setPhoneVerifiedState(storedVerified === "true");
      setLoaded(true);
    })();
  }, []);

  const setLang = (next: Lang) => {
    setLangState(next);
    AsyncStorage.setItem(LANG_KEY, next);
  };
  const setCounty = (next: string) => {
    setCountyState(next);
    AsyncStorage.setItem(COUNTY_KEY, next);
  };
  const setWard = (next: string) => {
    setWardState(next);
    AsyncStorage.setItem(WARD_KEY, next);
  };
  const setPhone = (next: string) => {
    setPhoneState(next);
    AsyncStorage.setItem(PHONE_KEY, next);
  };
  const setPhoneVerified = (verified: boolean) => {
    setPhoneVerifiedState(verified);
    AsyncStorage.setItem(VERIFIED_KEY, verified ? "true" : "false");
  };

  return (
    <AppContext.Provider
      value={{
        lang, setLang,
        county, setCounty,
        ward, setWard,
        phone, phoneVerified, setPhone, setPhoneVerified,
        loaded,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppState must be used within AppProvider");
  return ctx;
}
