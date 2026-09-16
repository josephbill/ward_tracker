import React, { useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppProvider, useAppState } from "./src/state/AppContext";
import { startAutoSync, syncNow } from "./src/offline/syncManager";
import { initAnalytics } from "./src/services/analytics";

import LanguageSelectScreen from "./src/screens/LanguageSelectScreen";
import CountySelectScreen from "./src/screens/CountySelectScreen";
import WardSelectScreen from "./src/screens/WardSelectScreen";
import WardProjectsScreen from "./src/screens/WardProjectsScreen";
import ProjectDetailScreen from "./src/screens/ProjectDetailScreen";
import ReportScreen from "./src/screens/ReportScreen";
import PhoneVerifyScreen from "./src/screens/PhoneVerifyScreen";
import AuditTrailScreen from "./src/screens/AuditTrailScreen";
import MyReportsScreen from "./src/screens/MyReportsScreen";
import IssuesListScreen from "./src/screens/IssuesListScreen";
import ReportIssueScreen from "./src/screens/ReportIssueScreen";
import MenuButton from "./src/components/NavMenu";

const Stack = createNativeStackNavigator();

// Journey per the product brief: language -> county -> ward -> browse/report.
// Each step is skipped on relaunch once its choice is persisted (AppContext
// loads all of them from AsyncStorage before `loaded` flips true), so a
// returning resident lands straight on their ward's project list.
function initialRoute(lang: unknown, county: unknown, ward: unknown): string {
  if (!lang) return "LanguageSelect";
  if (!county) return "CountySelect";
  if (!ward) return "WardSelect";
  return "WardProjects";
}

function RootNavigator() {
  const { lang, county, ward, loaded } = useAppState();

  useEffect(() => {
    const stop = startAutoSync();
    syncNow(); // catch up on anything queued from a previous offline session
    initAnalytics();
    return stop;
  }, []);

  if (!loaded) return null;

  return (
    <Stack.Navigator
      initialRouteName={initialRoute(lang, county, ward)}
      screenOptions={({ navigation }) => ({
        // Every screen gets a real header (with React Navigation's automatic
        // back button whenever there's somewhere to go back to) and this
        // menu button, so no screen is ever a dead end and every feature is
        // reachable from anywhere — see NavMenu.tsx.
        headerRight: () => <MenuButton navigation={navigation} />,
      })}
    >
      <Stack.Screen name="LanguageSelect" component={LanguageSelectScreen} options={{ title: "" }} />
      <Stack.Screen name="CountySelect" component={CountySelectScreen} options={{ title: "" }} />
      <Stack.Screen name="WardSelect" component={WardSelectScreen} options={{ title: "" }} />
      <Stack.Screen name="WardProjects" component={WardProjectsScreen} options={{ title: "Projects" }} />
      <Stack.Screen name="ProjectDetail" component={ProjectDetailScreen} options={{ title: "Project" }} />
      <Stack.Screen name="Report" component={ReportScreen} options={{ title: "Report" }} />
      <Stack.Screen name="PhoneVerify" component={PhoneVerifyScreen} options={{ title: "Verify your number" }} />
      <Stack.Screen name="AuditTrail" component={AuditTrailScreen} options={{ title: "Audit Trail" }} />
      <Stack.Screen name="MyReports" component={MyReportsScreen} options={{ title: "My Reports" }} />
      <Stack.Screen name="IssuesList" component={IssuesListScreen} options={{ title: "Local Issues" }} />
      <Stack.Screen name="ReportIssue" component={ReportIssueScreen} options={{ title: "Report an Issue" }} />
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AppProvider>
        <NavigationContainer>
          <StatusBar style="auto" />
          <RootNavigator />
        </NavigationContainer>
      </AppProvider>
    </SafeAreaProvider>
  );
}
