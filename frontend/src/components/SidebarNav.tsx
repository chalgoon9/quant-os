import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Overview" },
  { to: "/orders", label: "Orders" },
  { to: "/research", label: "Research" },
  { to: "/reports", label: "Reports" },
  { to: "/controls", label: "Controls" },
];

export function SidebarNav() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__eyebrow">quant-os</span>
        <h1>Ops Console</h1>
        <p>Read-mostly dashboard for paper, shadow, and live readiness.</p>
      </div>
      <nav className="sidebar__nav" aria-label="Primary">
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
