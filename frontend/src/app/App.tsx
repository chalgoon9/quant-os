import { Route, Routes } from "react-router-dom";

import { KillSwitchBanner } from "../components/KillSwitchBanner";
import { SidebarNav } from "../components/SidebarNav";
import { StatePanel } from "../components/StatePanel";
import { StatusBar } from "../components/StatusBar";
import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useRuntime } from "../hooks/useRuntime";
import { ControlsPage } from "../pages/ControlsPage";
import { OrdersPage } from "../pages/OrdersPage";
import { OverviewPage } from "../pages/OverviewPage";
import { ReportsPage } from "../pages/ReportsPage";
import { ResearchPage } from "../pages/ResearchPage";

export function App() {
  const runtime = useRuntime();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="app-shell">
      <SidebarNav />
      <div className="app-main">
        <header className="app-header">
          {runtime.isLoading ? (
            <div className="skeleton skeleton--status" />
          ) : runtime.isError ? (
            <StatePanel
              description="현재 모드, 시장, 데이터셋 정보를 표시하려면 백엔드의 런타임 메타데이터가 필요합니다."
              onAction={() => void runtime.refetch()}
              actionLabel="다시 시도"
              title="런타임 정보를 불러올 수 없음"
            />
          ) : runtime.data ? (
            <StatusBar runtime={runtime.data} />
          ) : null}
          {killSwitch.data ? <KillSwitchBanner events={killSwitch.data.items} /> : null}
        </header>
        <main className="app-content">
          <Routes>
            <Route element={<OverviewPage />} path="/" />
            <Route element={<OrdersPage />} path="/orders" />
            <Route element={<ResearchPage />} path="/research" />
            <Route element={<ReportsPage />} path="/reports" />
            <Route element={<ControlsPage />} path="/controls" />
          </Routes>
        </main>
      </div>
    </div>
  );
}
