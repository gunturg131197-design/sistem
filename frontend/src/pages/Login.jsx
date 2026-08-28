import React from "react";
import { GoogleLogoIcon, BulldozerIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function Login() {
  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
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
              <p className="font-display font-black text-sm tracking-tighter">EXCAVA<span className="text-primary">.OPS</span></p>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Heavy Equipment Reporting</p>
            </div>
          </header>

          <div className="max-w-lg space-y-8">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-primary mb-4">// System 01 / Field Command</p>
              <h1 className="font-display font-black text-4xl sm:text-5xl lg:text-6xl tracking-tighter leading-[0.95]">
                Laporan Alat Berat.<br />
                <span className="text-primary text-glow-yellow">Presisi Militer.</span>
              </h1>
              <p className="mt-6 text-base text-muted-foreground max-w-md">
                Sistem pelaporan operasional excavator — hour meter, produksi cars, gaji operator, dan penggantian sparepart dalam satu cockpit terpadu.
              </p>
            </div>

            <div className="space-y-3">
              <Button
                data-testid="google-login-button"
                onClick={handleGoogleLogin}
                className="w-full h-14 rounded-sm bg-primary text-black font-display font-black tracking-tight text-base hover:bg-primary/90 hover:text-black flex items-center justify-center gap-3"
              >
                <GoogleLogoIcon size={22} weight="bold" />
                LOGIN DENGAN GOOGLE
              </Button>
              <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                Access granted via Emergent SSO · Role-based · Encrypted session
              </p>
            </div>

            <div className="grid grid-cols-3 gap-0 border border-border">
              {[
                { k: "01", v: "Unit Registry" },
                { k: "02", v: "Ops Reports" },
                { k: "03", v: "Payroll & Parts" },
              ].map((it) => (
                <div key={it.k} className="p-4 border-r border-border last:border-r-0">
                  <p className="font-mono text-[10px] text-primary">{it.k}</p>
                  <p className="font-display font-black text-sm mt-1 tracking-tight">{it.v}</p>
                </div>
              ))}
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
