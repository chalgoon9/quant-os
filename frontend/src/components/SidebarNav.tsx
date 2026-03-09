import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "개요" },
  { to: "/backtests", label: "백테스트" },
  { to: "/orders", label: "주문" },
  { to: "/research", label: "리서치" },
  { to: "/reports", label: "리포트" },
  { to: "/controls", label: "제어" },
];

export function SidebarNav() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__eyebrow">quant-os</span>
        <h1>운영 대시보드</h1>
        <p>리서치에서 데이터를 불러오고, 백테스트로 전략 결과를 확인한 뒤 개요와 주문, 리포트에서 운영 상태를 검토하십시오.</p>
      </div>
      <nav className="sidebar__nav" aria-label="주요 화면">
        {NAV_ITEMS.map((item) => (
          <NavLink
            className={({ isActive }) =>
              `sidebar__link${isActive ? " sidebar__link--active" : ""}`
            }
            end={item.to === "/"}
            key={item.to}
            to={item.to}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
