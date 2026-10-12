import React from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  GaugeIcon,
  TruckIcon,
  ClockCounterClockwiseIcon,
  MoneyIcon,
  WrenchIcon,
  UsersThreeIcon,
  HardHatIcon,
  ChartBarIcon,
  SignOutIcon,
  BankIcon,
  WhatsappLogoIcon,
 LifebuoyIcon,
  TrophyIcon,
} from "@phosphor-icons/react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { BrandLockup, BrandMark } from "@/components/Brand";

const navItems = [
  { to: "/", label: "Dashboard", icon: GaugeIcon, testid: "nav-dashboard" },
  { to: "/units", label: "Unit Registry", icon: TruckIcon, testid: "nav-units", adminOnly: false },
  { to: "/operations", label: "Ops Report", icon: ClockCounterClockwiseIcon, testid: "nav-operations" },
  { to: "/payroll", label: "Payroll", icon: MoneyIcon, testid: "nav-payroll" },
  { to: "/spareparts", label: "Sparepart", icon: WrenchIcon, testid: "nav-spareparts" },
  { to: "/reports", label: "Laporan", icon: ChartBarIcon, testid: "nav-reports" },
  { to: "/finance", label: "Keuangan", icon: BankIcon, testid: "nav-finance", adminOnly: true },
  { to: "/bonus-admin", label: "Bonus Admin", icon: TrophyIcon, testid: "nav-bonus-admin", adminOnly: true },
  { to: "/wa-inbox", label: "Kotak Masuk WA", icon: WhatsappLogoIcon, testid: "nav-wa-inbox", adminOnly: true },
  { to: "/pengurus", label: "Pengurus", icon: HardHatIcon, testid: "nav-pengurus" },
  { to: "/users", label: "Operators", icon: UsersThreeIcon, testid: "nav-users", adminOnly: true },
  { to: "/bantuan", label: "Bantuan & Backup", icon: LifebuoyIcon, testid: "nav-help", adminOnly: true },
];

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const initials = (user?.name || "??").split(" ").map(s => s[0]).slice(0, 2).join("").toUpperCase();
  const items = navItems.filter(n => !n.adminOnly || user?.role === "admin");
  const current = items.find(i => i.to === location.pathname);

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 border-r border-border flex-col bg-card sticky top-0 h-screen">
        <div className="h-1 brand-rail" />
        <div className="px-5 py-5 border-b border-border" data-testid="app-sidebar-brand">
          <BrandLockup size={34} testid="app-sidebar-brand" />
          <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.2em] text-primary">Heavy Equipment Reporting</p>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          <p className="px-2 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">// Navigasi</p>
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              data-testid={item.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 text-sm font-medium border-l-2 ${
                  isActive
                    ? "bg-primary/10 border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`
              }
            >
              <item.icon size={18} weight="bold" />
              <span className="tracking-tight">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-border space-y-3">
          <div className="flex items-center gap-3 px-2">
            <Avatar className="h-9 w-9 rounded-sm">
              <AvatarImage src={user?.picture} />
              <AvatarFallback className="rounded-sm bg-secondary text-xs font-mono">{initials}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate" data-testid="current-user-name">{user?.name}</p>
              <Badge
                data-testid="current-user-role"
                className={`rounded-sm text-[9px] font-mono uppercase tracking-widest px-1.5 py-0 ${
                  user?.role === "admin" ? "bg-primary text-primary-foreground hover:bg-primary" : "bg-secondary text-foreground hover:bg-secondary"
                }`}
              >
                {user?.role}
              </Badge>
            </div>
          </div>
          <button
            onClick={logout}
            data-testid="logout-button"
            className="w-full flex items-center gap-2 px-3 py-2 text-xs font-mono uppercase tracking-widest text-muted-foreground hover:text-accent border border-border hover:border-accent"
          >
            <SignOutIcon size={14} weight="bold" />
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile top nav */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-card border-b border-border">
        <div className="h-0.5 brand-rail" />
        <div className="flex items-center justify-between px-4 h-14">
          <button className="flex items-center gap-2" onClick={() => navigate("/")} data-testid="app-mobile-header-logo">
            <BrandMark size={26} />
            <div className="text-left leading-none">
              <p className="font-display font-black text-sm tracking-tight">TRIRARA</p>
              <p className="font-mono text-[8px] uppercase tracking-[0.3em] text-muted-foreground mt-0.5">Tunggal Putra</p>
            </div>
          </button>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary" data-testid="app-mobile-header-title">{current?.label || ""}</p>
          <button onClick={logout} data-testid="logout-button-mobile" className="p-2 border border-border hover:border-accent hover:text-accent">
            <SignOutIcon size={16} weight="bold" />
          </button>
        </div>
      </div>

      {/* Mobile bottom nav */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-card border-t border-border grid grid-cols-5">
        {items.slice(0, 5).map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            data-testid={`${item.testid}-mobile`}
            className={({ isActive }) => `flex flex-col items-center justify-center py-2 text-[10px] gap-1 ${isActive ? "text-primary" : "text-muted-foreground"}`}
          >
            <item.icon size={18} weight="bold" />
            <span className="tracking-tight">{item.label.split(" ")[0]}</span>
          </NavLink>
        ))}
      </div>

      <main className="flex-1 min-w-0 pt-16 lg:pt-0 pb-20 lg:pb-0 relative grid-bg">
        <div className="p-6 lg:p-10 max-w-[1600px] animate-fade-up" key={location.pathname}>{children}</div>
      </main>
    </div>
  );
}
