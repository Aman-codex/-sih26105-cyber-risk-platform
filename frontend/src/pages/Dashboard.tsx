import { NavLink, Outlet } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { ROLE_LABELS } from "@/types/auth";

const TABS = [
  { to: "/dashboard/risk", label: "Risk Overview" },
  { to: "/dashboard/assets", label: "Assets" },
  { to: "/dashboard/vulnerabilities", label: "Vulnerabilities" },
  { to: "/dashboard/threats", label: "Threats" },
  { to: "/dashboard/controls", label: "Controls" },
  { to: "/dashboard/compliance", label: "Compliance" },
  { to: "/dashboard/investments", label: "Investments" },
  { to: "/dashboard/what-if", label: "What-If" },
  { to: "/dashboard/ml", label: "ML Prediction" },
  { to: "/dashboard/assistant", label: "Assistant" },
];

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-primary" size={22} />
          <span className="font-semibold">RISK BREAK</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm">{user?.full_name ?? user?.email}</p>
            <p className="text-xs text-muted-foreground">
              {user ? ROLE_LABELS[user.role] : ""}
            </p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </header>

      <nav className="flex gap-1 border-b border-border px-6">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `px-3 py-2 text-sm border-b-2 -mb-px ${
                isActive ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
