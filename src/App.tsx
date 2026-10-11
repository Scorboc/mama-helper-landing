import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import { Component, lazy, Suspense, type ReactNode } from "react";
import { Link } from "react-router-dom";
import PublicFirstAid from "./pages/PublicFirstAid";
import FirstAid from "@/components/FirstAid";
const Index = lazy(() => import("./pages/Index"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Account = lazy(() => import("./pages/Account"));
const ParentWorkspace = lazy(() => import("./pages/ParentWorkspace"));
const Privacy = lazy(() => import("./pages/Privacy"));

function OpeningPage() {
  return <main className="public-page route-message" aria-busy="true">
    <p role="status">Открываем страницу…</p>
    <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
  </main>;
}

class PageBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <main className="public-page route-message">
      <h1>Не удалось открыть страницу</h1>
      <p role="alert">Проверьте соединение и попробуйте обновить страницу. Сохранённые записи остаются в аккаунте.</p>
      <button className="glass-btn px-5 py-3" onClick={() => window.location.reload()}>Обновить страницу</button>
      <a className="standalone-link" href="tel:112">Позвонить 112</a>
      <details className="route-urgent-help">
        <summary>Открыть памятку первой помощи</summary>
        <FirstAid />
      </details>
    </main>;
  }
}

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <PageBoundary><Suspense fallback={<OpeningPage />}><Routes>
          <Route path="/" element={<Index />} />
          <Route path="/account" element={<Account />} />
          <Route path="/cabinet" element={<ParentWorkspace key="account" />} />
          <Route path="/demo" element={<Navigate to="/account" replace />} />
          <Route
            path="/chat"
            element={<ParentWorkspace key="chat" initialTab="chat" />}
          />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/first-aid" element={<PublicFirstAid />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes></Suspense></PageBoundary>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
