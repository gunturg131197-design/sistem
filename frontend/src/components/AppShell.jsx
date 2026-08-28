import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  GaugeIcon,
  TruckIcon,
  ClockCounterClockwiseIcon,
  MoneyIcon,
  WrenchIcon,
  UsersThreeIcon,
  SignOutIcon,
  BulldozerIcon,
} from "@phosphor-icons/react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { to: "/", label: "Dashboard", icon: GaugeIcon, testid: "nav-dashboard" },
  { to: "/units", label: "Unit Registry", icon: TruckIcon, testid: "nav-units", adminOnly: false },
  { to: "/operations", label: "Ops Report", icon: ClockCounterClockwiseIcon, testid: "nav-operations" },
  { to: "/payroll", label: "Payroll", icon: MoneyIcon, testid: "nav-payroll" },
  { to: "/spareparts", label: "Sparepart", icon: WrenchIcon, testid: "nav-spareparts" },
  { to: "/users", label: "Operators", icon: UsersThreeIcon, testid: "nav-users", adminOnly: true },
];

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initials = (user?.name || "??").split(" ").map(s => s[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 border-r border-border flex-col bg-muted/40">
        <div className="p-5 border-b border-border flex items-center gap-3">
          <div className="h-9 w-9 bg-primary flex items-center justify-center">
            <BulldozerIcon size={20} weight="fill" className="text-black" />
          </div>
          <div>
            <p className="font-display font-black text-sm tracking-tighter">EXCAVA<span className="text-primary">.OPS</span></p>
            <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground">Field Command v1.0</p>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          <p className="px-2 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">// Navigation</p>
          {navItems.filter(n => !n.adminOnly || user?.role === "admin").map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              data-testid={item.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 text-sm font-medium border-l-2 ${
                  isActive
                    ? "bg-primary/10 border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/50"
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
                  user?.role === "admin" ? "bg-primary text-black" : "bg-secondary text-foreground"
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
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-background border-b border-border flex items-center justify-between px-4 h-14">
        <div className="flex items-center gap-2" onClick={() => navigate("/")}>
          <div className="h-7 w-7 bg-primary flex items-center justify-center">
            <BulldozerIcon size={16} weight="fill" className="text-black" />
          </div>
          <p className="font-display font-black text-sm">EXCAVA<span className="text-primary">.OPS</span></p>
        </div>
        <button onClick={logout} data-testid="logout-button-mobile" className="p-2 border border-border">
          <SignOutIcon size={16} weight="bold" />
        </button>
      </div>

      {/* Mobile bottom nav */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-background border-t border-border grid grid-cols-5">
        {navItems.filter(n => !n.adminOnly || user?.role === "admin").slice(0, 5).map(item => (
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

      <main className="flex-1 min-w-0 pt-14 lg:pt-0 pb-20 lg:pb-0 relative">
        <div className="p-6 lg:p-10 max-w-[1600px]">{children}</div>
      </main>
    </div>
  );
}
