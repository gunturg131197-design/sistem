import React, { useState } from "react";
import { GoogleLogoIcon, BulldozerIcon, UserIcon, LockIcon, ArrowRightIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

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
      <div className="grid lg:grid-cols-2 min-h-screen">
        {/* Left panel */}
        <div className="relative flex flex-col justify-between p-8 lg:p-14 border-r border-border">
          <header className="flex items-center gap-3">
            <div className="h-10 w-10 bg-primary flex items-center justify-center">
              <BulldozerIcon size={22} weight="fill" className="text-black" />
            </div>
            <div>
              <p className="font-display font-black text-sm tracking-tighter">CV.TTP<span className="text-primary">.OPS</span></p>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Heavy Equipment Reporting</p>
            </div>
          </header>

          <div className="max-w-lg space-y-8">
            <div>
              <h1 className="font-display font-black text-4xl sm:text-5xl lg:text-6xl tracking-tighter leading-[0.95]">
                Laporan Alat Berat.<br />
                <span className="text-primary text-glow-yellow">TRIRARA TUNGGAL PUTRA</span>
              </h1>
              <p className="mt-6 text-base text-muted-foreground max-w-md">
                Sistem pelaporan operasional excavator — hour meter, produksi cars, gaji operator, dan penggantian sparepart dalam satu cockpit terpadu.
              </p>
            </div>

            {/* Username/password login */}
            <form onSubmit={handlePasswordLogin} className="space-y-3 border border-border p-5 bg-muted/20">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Login Operator (Akun Manual)</p>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Username</Label>
                <div className="relative mt-1.5">
                  <UserIcon size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    data-testid="login-username-input"
                    className="rounded-sm pl-9"
                    autoComplete="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="username_operator"
                  />
                </div>
              </div>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Password</Label>
                <div className="relative mt-1.5">
                  <LockIcon size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    data-testid="login-password-input"
                    className="rounded-sm pl-9"
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
                className="w-full h-11 rounded-sm bg-primary text-black font-display font-black tracking-tight hover:bg-primary/90 hover:text-black flex items-center justify-center gap-2"
              >
                {loading ? "MEMPROSES…" : (<><ArrowRightIcon size={16} weight="bold" /> LOGIN</>)}
              </Button>
            </form>

            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-border" />
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">atau</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            <div className="space-y-3">
              <Button
                data-testid="google-login-button"
                onClick={handleGoogleLogin}
                className="w-full h-12 rounded-sm bg-secondary text-foreground font-display font-black tracking-tight text-sm hover:bg-primary hover:text-black flex items-center justify-center gap-3 border border-border"
              >
                <GoogleLogoIcon size={20} weight="bold" />
                LOGIN DENGAN GOOGLE
              </Button>
              <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                Untuk admin / owner · access via Emergent SSO
              </p>
            </div>
          </div>

          <footer className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            v1.0 · industrial edition · shanchidean ops
          </footer>
        </div>

        {/* Right panel - image */}
        <div className="hidden lg:block relative">
          <img
            src="https://images.pexels.com/photos/38735193/pexels-photo-38735193.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=1200"
            alt="Excavator"
            className="absolute inset-0 h-full w-full object-cover grayscale-[15%]"
          />
          <div className="absolute inset-0 bg-gradient-to-l from-transparent via-background/40 to-background" />
          <div className="absolute top-8 right-8 border border-primary/40 bg-background/80 px-3 py-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">● LIVE FIELD FEED</p>
          </div>
          <div className="absolute bottom-8 left-8 right-8 border-l-2 border-primary pl-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">SITE READING</p>
            <p className="font-display font-black text-2xl tracking-tighter mt-1">DIG · HAUL · REPORT</p>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-3 diagonal-stripes opacity-60" />
        </div>
      </div>
    </div>
  );
}
