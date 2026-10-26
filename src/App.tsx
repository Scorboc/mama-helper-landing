import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Routes, Route, useSearchParams } from "react-router-dom";
import { Component, lazy, Suspense, type ReactNode } from "react";
import { Link } from "react-router-dom";
import PublicFirstAid from "./pages/PublicFirstAid";
import FirstAid from "@/components/FirstAid";
import RoomTransition from "@/components/RoomTransition";
import RoomSurface from "@/components/RoomSurface";
import RoomPageShell from "@/components/RoomPageShell";
import RoomMediaProvider from "@/components/RoomMediaProvider";
import "@/components/room-guest.css";
import PublicOverview from "./pages/PublicOverview";
const Index = lazy(() => import("./pages/Index"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Account = lazy(() => import("./pages/Account"));
const ParentWorkspace = lazy(() => import("./pages/ParentWorkspace"));
const Privacy = lazy(() => import("./pages/Privacy"));
const Legal = lazy(() => import("./pages/Legal"));
const Billing = lazy(() => import("./pages/Billing"));
const DataRights = lazy(() => import("./pages/DataRights"));
const PublicGuide = lazy(() => import("./pages/PublicGuide"));
const CampaignGames = lazy(() => import("./pages/CampaignGames"));

function EntryRoute() {
  const [params] = useSearchParams();
  return params.get("lang") === "en" ? <Navigate to="/en" replace /> : <Index />;
}

function OpeningPage() {
  return <RoomSurface><main className="public-page route-message" aria-busy="true">
    <p role="status">Открываем страницу…</p>
    <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
  </main></RoomSurface>;
}

class PageBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <RoomSurface><main className="public-page route-message">
      <h1>Не удалось открыть страницу</h1>
      <p role="alert">Проверьте соединение и попробуйте обновить страницу. Сохранённые записи остаются в аккаунте.</p>
      <button className="glass-btn px-5 py-3" onClick={() => window.location.reload()}>Обновить страницу</button>
      <a className="standalone-link" href="tel:112">Позвонить 112</a>
      <details className="route-urgent-help">
        <summary>Открыть памятку первой помощи</summary>
        <FirstAid />
      </details>
    </main></RoomSurface>;
  }
}

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <RoomMediaProvider><RoomTransition />
        <PageBoundary><Suspense fallback={<OpeningPage />}><Routes>
          <Route path="/" element={<EntryRoute />} />
          <Route path="/en" element={<PublicOverview english />} />
          <Route path="/about" element={<PublicOverview />} />
          <Route path="/games" element={<RoomSurface><CampaignGames /></RoomSurface>} />

          <Route path="/cabinet" element={<RoomSurface><ParentWorkspace key="account" /></RoomSurface>} />
          <Route path="/demo" element={<Navigate to="/account" replace />} />
          <Route
            path="/chat"
            element={<RoomSurface><ParentWorkspace key="chat" initialTab="chat" /></RoomSurface>}
          />
          <Route element={<RoomPageShell />}>
            <Route path="/account" element={<Account />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Legal kind="account" />} />
            <Route path="/offer" element={<Legal kind="offer" />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/data-rights" element={<DataRights />} />
            <Route path="/first-aid" element={<PublicFirstAid />} />
            <Route path="/guide" element={<PublicGuide />} />
            <Route path="/guide/:slug" element={<PublicGuide />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes></Suspense></PageBoundary></RoomMediaProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
