import React, { useState } from "react";
import { UserIcon, LockIcon, ArrowRightIcon, ClockIcon, FileTextIcon, WrenchIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { BrandLockup, BrandMark } from "@/components/Brand";
import logoFull from "@/assets/logo-full.jpg";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    if (!username || !password) { toast.error("Username & password wajib diisi"); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { username, password });
      setUser(data);
      toast.success(`Selamat datang, ${data.name}`);
      navigate("/", { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Login gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-background relative overflow-hidden grid-bg">
      <div className="h-1 brand-rail" />
      <div className="grid lg:grid-cols-2 min-h-[calc(100vh-4px)]">
        {/* Left panel — login */}
        <div className="relative flex flex-col justify-between p-8 lg:p-14 border-r border-border">
          <header className="flex items-center justify-between">
            <BrandLockup size={38} testid="login-brand" />
            <span className="hidden sm:inline font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground border border-border px-2 py-1">Ops Console</span>
          </header>

          <div className="max-w-lg w-full space-y-8 my-10 animate-fade-up">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-primary mb-4">// Sistem Pelaporan Alat Berat</p>
              <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tighter leading-[0.95]">
                Hour Meter, Produksi<br />& Biaya Alat.
              </h1>
              <p className="mt-5 text-base text-muted-foreground max-w-md">
                Laporan harian operator, rekap bulanan hour meter, penggantian sparepart, dan gaji operator — tercetak otomatis dengan kop resmi <span className="text-foreground font-semibold">TRIRARA TUNGGAL PUTRA</span>.
              </p>
            </div>

            <form onSubmit={handlePasswordLogin} className="space-y-3 border border-border p-5 bg-card relative">
              <div className="absolute top-0 left-0 h-0.5 w-12 bg-primary" />
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Login Akun</p>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Username</Label>
                <div className="relative mt-1.5">
                  <UserIcon size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    data-testid="login-username-input"
                    className="rounded-sm pl-9 bg-background"
                    autoComplete="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="username"
                  />
                </div>
              </div>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Password</Label>
                <div className="relative mt-1.5">
                  <LockIcon size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    data-testid="login-password-input"
                    className="rounded-sm pl-9 bg-background"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <Button
                data-testid="login-submit-button"
                type="submit"
                disabled={loading}
                className="w-full h-11 rounded-sm bg-primary text-primary-foreground font-display font-black tracking-tight hover:bg-primary/90 hover:text-primary-foreground flex items-center justify-center gap-2"
              >
                {loading ? "MEMPROSES…" : (<><ArrowRightIcon size={16} weight="bold" /> LOGIN</>)}
              </Button>
            </form>

            <p data-testid="login-account-note" className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              Akun dibuat oleh admin. Lupa password? Hubungi admin.
            </p>
          </div>

          <footer className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            © {new Date().getFullYear()} CV. Trirara Tunggal Putra
          </footer>
        </div>

        {/* Right panel — brand hero */}
        <div className="hidden lg:flex relative flex-col overflow-hidden">
          <img
            src="https://images.pexels.com/photos/38735193/pexels-photo-38735193.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=1200"
            alt="Excavator"
            className="absolute inset-0 h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-[#022D42]/85" />
          <div className="relative flex-1 flex flex-col justify-center px-14">
            <div className="bg-white p-6 w-fit shadow-[8px_8px_0_0_#FEC202]" data-testid="login-full-logo">
              <img src={logoFull} alt="TRIRARA TUNGGAL PUTRA" className="h-24 w-auto" />
            </div>
            <div className="mt-12 grid grid-cols-3 gap-0 border border-white/15 max-w-xl bg-[#0B1E2D]">
              {[
                { icon: ClockIcon, k: "Hour Meter", v: "Harian & Bulanan" },
                { icon: WrenchIcon, k: "Sparepart", v: "Detail Penggantian" },
                { icon: FileTextIcon, k: "Laporan", v: "PDF · Excel · Word" },
              ].map((it, i) => (
                <div key={it.k} className={`p-4 ${i < 2 ? "border-r border-white/15" : ""}`}>
                  <it.icon size={18} weight="bold" className="text-primary" />
                  <p className="mt-3 font-display font-black tracking-tight text-sm">{it.k}</p>
                  <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground mt-1">{it.v}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="relative flex items-end justify-between px-14 pb-8">
            <div className="border-l-2 border-accent pl-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Field Operations</p>
              <p className="font-display font-black text-2xl tracking-tighter mt-1">DIG · HAUL · REPORT</p>
            </div>
            <BrandMark size={44} className="opacity-90" />
          </div>
          <div className="relative h-6 checkered opacity-90" />
          <div className="relative h-2 brand-rail" />
        </div>
      </div>
    </div>
  );
}
