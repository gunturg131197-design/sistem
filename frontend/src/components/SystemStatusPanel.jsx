import React, { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArrowClockwiseIcon, GitCommitIcon, DatabaseIcon, CpuIcon, WarningIcon, CheckCircleIcon, CircleNotchIcon, CopyIcon } from "@phosphor-icons/react";
import { toast } from "sonner";

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
const REFRESH_MS = 30000;

const fmtTime = (s) => (s ? new Date(s).toLocaleString("id-ID", { timeZone: "Asia/Makassar", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }) + " WITA" : "-");

export const fmtUptime = (sec) => {
  if (sec == null) return "-";
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
  if (d) return `${d} hari ${h} jam`;
  if (h) return `${h} jam ${m} menit`;
  if (m) return `${m} menit`;
  return `${sec} detik`;
};

function Row({ k, v, mono, testid }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5 border-b border-border/60 last:border-0">
      <span className="text-xs text-muted-foreground shrink-0">{k}</span>
      <span data-testid={testid} className={`text-sm text-right min-w-0 break-all ${mono ? "font-mono text-xs" : ""}`}>{v ?? "-"}</span>
    </div>
  );
}

function Card({ icon: Icon, title, children, testid, tone }) {
  return (
    <section data-testid={testid} className={`border bg-card p-5 ${tone === "bad" ? "border-accent/70" : "border-border"}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={18} weight="bold" className={tone === "bad" ? "text-accent" : "text-primary"} />
        <h3 className="font-display font-bold text-base tracking-tight">{title}</h3>
      </div>
      {children}
    </section>
  );
}

export const SystemStatusPanel = () => {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef(null);

  const load = useCallback(async (manual = false) => {
    setBusy(true);
    try {
      const res = await api.get("/admin/system-status");
      setData(res.data); setErr(null);
      if (manual) toast.success("Status sistem diperbarui");
    } catch (e) {
      const status = e?.response?.status;
      setErr(status === 503 ? "Server sedang menyiapkan database — status akan muncul otomatis." : "Gagal memuat status sistem.");
      if (manual) toast.error("Gagal memuat status sistem");
    } finally { setBusy(false); }
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(() => load(), REFRESH_MS);
    return () => clearInterval(timer.current);
  }, [load]);

  const copyCommit = async () => {
    try { await navigator.clipboard.writeText(data?.version?.commit || ""); toast.success("Hash commit disalin"); }
    catch { toast.error("Tidak bisa menyalin"); }
  };

  const v = data?.version, st = data?.startup, dbi = data?.database, rt = data?.runtime;
  const overall = !data ? null : !dbi?.ok ? "bad" : !st?.ready ? "warn" : "ok";
  const badge = {
    ok: { text: "Semua normal", cls: "border-emerald-500/60 text-emerald-400", Icon: CheckCircleIcon },
    warn: { text: "Menyiapkan", cls: "border-primary/60 text-primary", Icon: CircleNotchIcon },
    bad: { text: "Database bermasalah", cls: "border-accent/70 text-accent", Icon: WarningIcon },
  }[overall];

  return (
    <div className="mb-6" data-testid="system-status-panel">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <p className="font-display font-black text-xl tracking-tighter">Status Sistem</p>
        {badge && (
          <span data-testid="system-status-overall" className={`inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 border ${badge.cls}`}>
            <badge.Icon size={12} weight="bold" className={overall === "warn" ? "animate-spin" : ""} /> {badge.text}
          </span>
        )}
        <span className="mr-auto" />
        {data && <span className="font-mono text-[10px] text-muted-foreground" data-testid="system-status-checked-at">Dicek {fmtTime(data.checked_at)} · otomatis tiap 30 dtk</span>}
        <Button data-testid="system-status-refresh" size="sm" variant="outline" disabled={busy} onClick={() => load(true)}
          className="rounded-sm border-border hover:border-primary hover:text-primary focus-visible:ring-2 focus-visible:ring-primary">
          <ArrowClockwiseIcon size={14} weight="bold" className={busy ? "animate-spin" : ""} />
        </Button>
      </div>

      {err && !data && (
        <div data-testid="system-status-error" className="border border-accent/70 bg-card p-4 flex flex-wrap items-center gap-3 text-sm">
          <WarningIcon size={18} className="text-accent" /> <span className="mr-auto">{err}</span>
          <Button size="sm" variant="outline" onClick={() => load(true)} data-testid="system-status-retry" className="rounded-sm">Coba lagi</Button>
        </div>
      )}

      {!data && !err && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="system-status-loading">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-48 rounded-sm" />)}
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card icon={GitCommitIcon} title="Versi Tayang" testid="system-status-version">
            <div className="flex items-center gap-2 mb-2">
              {v?.commit_short ? (
                <a href={`${v.repo_url}/commit/${v.commit}`} target="_blank" rel="noreferrer" data-testid="system-status-commit"
                  className="font-mono text-2xl font-bold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{v.commit_short}</a>
              ) : <span data-testid="system-status-commit" className="font-mono text-sm text-accent">Commit tidak diketahui</span>}
              {v?.commit && (
                <TooltipProvider><Tooltip><TooltipTrigger asChild>
                  <Button size="icon" variant="ghost" onClick={copyCommit} data-testid="system-status-copy-commit" aria-label="Salin hash commit" className="h-7 w-7 rounded-sm hover:text-primary"><CopyIcon size={14} /></Button>
                </TooltipTrigger><TooltipContent>Salin hash lengkap</TooltipContent></Tooltip></TooltipProvider>
              )}
            </div>
            {v?.message && <p className="text-xs text-muted-foreground mb-2 line-clamp-2" data-testid="system-status-commit-message">{v.message}</p>}
            <Row k="Branch" v={v?.branch} mono testid="system-status-branch" />
            <Row k="Waktu build" v={v?.built_at ? fmtTime(v.built_at) : "-"} testid="system-status-built-at" />
            <Row k="Sumber versi" v={v?.commit_source} mono testid="system-status-commit-source" />
          </Card>

          <Card icon={DatabaseIcon} title="Database" testid="system-status-db" tone={dbi?.ok ? "ok" : "bad"}>
            <div className="flex items-center gap-2 mb-2">
              <span className={`h-2.5 w-2.5 rounded-full ${dbi?.ok ? "bg-emerald-400" : "bg-accent"}`} aria-hidden />
              <span data-testid="system-status-db-state" className={`font-display font-bold text-lg ${dbi?.ok ? "text-emerald-400" : "text-accent"}`}>{dbi?.ok ? "Tersambung" : "Tidak tersambung"}</span>
              {dbi?.latency_ms != null && <span className="font-mono text-xs text-muted-foreground" data-testid="system-status-db-latency">{dbi.latency_ms} ms</span>}
            </div>
            {!dbi?.ok && dbi?.error && (
              <p data-testid="system-status-db-error" className="font-mono text-[11px] text-accent bg-background border border-accent/40 p-2 mb-2 break-all">{dbi.error}{dbi.attempts ? ` · percobaan ${dbi.attempts}` : ""}</p>
            )}
            <Row k="Engine" v={dbi?.server_version || dbi?.engine} mono testid="system-status-db-version" />
            <Row k="Target" v={dbi?.target} mono testid="system-status-db-target" />
            <Row k="Jumlah tabel" v={dbi?.tables} testid="system-status-db-tables" />
          </Card>

          <Card icon={CpuIcon} title="Server" testid="system-status-server">
            <div className="mb-2">
              <p className={lbl}>Berjalan sejak</p>
              <p className="font-display font-bold text-lg" data-testid="system-status-uptime">{fmtUptime(st?.uptime_seconds)}</p>
            </div>
            <Row k="Waktu startup" v={fmtTime(st?.started_at)} testid="system-status-started-at" />
            <Row k="Siap dalam" v={st?.startup_seconds != null ? `${st.startup_seconds} detik` : st?.ready ? "-" : "Masih menyiapkan…"} testid="system-status-startup-seconds" />
            <Row k="Platform" v={rt?.platform} testid="system-status-platform" />
            <Row k="Domain" v={rt?.domain} mono testid="system-status-domain" />
            <Row k="Python · Port" v={`${rt?.python || "-"} · ${rt?.port || "-"}${rt?.extra_ports ? ` (+${rt.extra_ports})` : ""}`} mono testid="system-status-runtime" />
          </Card>
        </div>
      )}
    </div>
  );
};
