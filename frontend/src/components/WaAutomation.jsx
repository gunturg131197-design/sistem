import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { formatIDR } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  RobotIcon, ShieldCheckIcon, ClockCounterClockwiseIcon, FloppyDiskIcon, PaperPlaneTiltIcon, EyeIcon, CopySimpleIcon,
  CalendarIcon, WarningIcon, CheckCircleIcon, ArrowClockwiseIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
export const AUDIT_LABEL = {
  received: "Diterima", ai_processed: "Dibaca AI", ai_error: "AI gagal", auto_approved: "Disimpan otomatis", auto_blocked: "Masuk verifikasi manual",
  approved: "Disetujui manual", rejected: "Ditolak", reprocessed: "Dibaca ulang", deleted: "Dihapus", edited: "Draft diubah",
  reply_sent: "Balasan WA terkirim", reply_failed: "Balasan WA gagal", settings_changed: "Pengaturan diubah", summary_run: "Ringkasan harian",
};
const AUDIT_TONE = { auto_approved: "text-emerald-400", approved: "text-emerald-400", auto_blocked: "text-primary", rejected: "text-accent", ai_error: "text-accent", reply_failed: "text-accent", deleted: "text-accent" };
const fmt = (s) => (s ? new Date(s).toLocaleString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "-");

export function AuditList({ rows, compact = false, testid = "wa-audit-list" }) {
  if (!rows.length) return <p className="text-xs font-mono text-muted-foreground p-4">// Belum ada riwayat</p>;
  return (
    <ol className="divide-y divide-border" data-testid={testid}>
      {rows.map((a) => (
        <li key={a.id} className={`flex gap-3 ${compact ? "py-2" : "p-3"}`}>
          <span className="font-mono text-[10px] text-muted-foreground w-36 shrink-0">{fmt(a.at)}</span>
          <div className="min-w-0">
            <p className={`text-xs font-semibold ${AUDIT_TONE[a.action] || ""}`}>{AUDIT_LABEL[a.action] || a.action} <span className="font-normal text-muted-foreground">· {a.actor}</span></p>
            <p className="text-xs text-muted-foreground break-words">{a.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function AutomationTab() {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [audit, setAudit] = useState([]);
  const [action, setAction] = useState("all");
  const [loadingAudit, setLoadingAudit] = useState(true);
  const load = async () => { try { setCfg((await api.get("/wa/auto-settings")).data); } catch { toast.error("Gagal memuat pengaturan"); } };
  const loadAudit = async () => {
    setLoadingAudit(true);
    try { setAudit((await api.get("/wa/audit", { params: { action } })).data); } catch { toast.error("Gagal memuat riwayat audit"); }
    finally { setLoadingAudit(false); }
  };
  useEffect(() => { load(); }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAudit(); }, [action]);
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/wa/auto-settings", { transfer_enabled: cfg.transfer_enabled, hm_enabled: cfg.hm_enabled, min_confidence: Number(cfg.min_confidence) });
      setCfg((c) => ({ ...c, ...data })); toast.success("Pengaturan otomatis tersimpan"); loadAudit();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
    finally { setSaving(false); }
  };
  const rules = ["Keyakinan AI ≥ batas yang diatur (minimal 90%)", "Unit alat berat dikenali dari keterangan / kontak", "Nominal transfer atau angka HM terbaca",
    "No. Ref transfer terbaca & belum pernah tercatat", "Tidak ada peringatan (HM mundur, operator tidak dikenali, dll.)"];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4" data-testid="wa-automation-tab">
      <div className="border border-border bg-card p-5 space-y-5">
        <div className="flex items-center gap-2"><RobotIcon size={20} weight="bold" className="text-primary" /><p className="font-display font-black text-xl tracking-tighter">Persetujuan Otomatis</p></div>
        {!cfg ? <Skeleton className="h-40 rounded-sm" /> : (
          <>
            {[["transfer_enabled", "Bukti transfer → Kas Masuk"], ["hm_enabled", "Foto HM → Ops Report"]].map(([k, l]) => (
              <div key={k} className="flex items-center justify-between gap-3 border border-border p-3">
                <Label htmlFor={k} className="text-sm cursor-pointer">{l}</Label>
                <Switch id={k} data-testid={`wa-auto-${k}`} checked={!!cfg[k]} onCheckedChange={(v) => setCfg({ ...cfg, [k]: v })} />
              </div>
            ))}
            <div>
              <Label className={lbl}>Batas keyakinan AI (%)</Label>
              <Input data-testid="wa-auto-threshold" type="number" min={90} max={100} step={1} className="rounded-sm mt-1.5 font-mono w-32"
                value={Math.round(Number(cfg.min_confidence) * 100)} onChange={(e) => setCfg({ ...cfg, min_confidence: Number(e.target.value) / 100 })} />
              <p className="font-mono text-[10px] text-muted-foreground mt-1">Minimal 90%. Di bawah batas → antrean verifikasi manual.</p>
            </div>
            <Button data-testid="wa-auto-save" disabled={saving} onClick={save} className="w-full rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><FloppyDiskIcon size={16} weight="bold" className="mr-2" /> {saving ? "Menyimpan…" : "Simpan Pengaturan"}</Button>
            <div className="grid grid-cols-2 border border-border">
              <div className="p-3 border-r border-border"><p className={lbl}>Tersimpan otomatis</p><p data-testid="wa-auto-count" className="font-display font-black text-2xl tracking-tighter text-emerald-400">{cfg.auto_count ?? 0}</p></div>
              <div className="p-3"><p className={lbl}>Antrean manual</p><p data-testid="wa-manual-queue" className="font-display font-black text-2xl tracking-tighter text-primary">{cfg.manual_queue ?? 0}</p></div>
            </div>
          </>
        )}
        <div className="pt-3 border-t border-border space-y-1.5">
          <p className={lbl}>// Syarat disimpan otomatis (semua harus terpenuhi)</p>
          {rules.map((r) => <p key={r} className="text-xs flex gap-2"><ShieldCheckIcon size={13} weight="bold" className="text-primary shrink-0 mt-0.5" />{r}</p>)}
        </div>
      </div>
      <div className="xl:col-span-2 border border-border bg-card">
        <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border">
          <ClockCounterClockwiseIcon size={18} weight="bold" className="text-primary" />
          <p className="font-display font-black text-xl tracking-tighter mr-auto">Riwayat Audit</p>
          <Select value={action} onValueChange={setAction}>
            <SelectTrigger data-testid="wa-audit-filter" className="rounded-sm w-56"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua aktivitas</SelectItem>
              <SelectItem value="auto_approved,approved">Disetujui (otomatis & manual)</SelectItem>
              <SelectItem value="auto_blocked">Masuk verifikasi manual</SelectItem>
              <SelectItem value="rejected,deleted">Ditolak / dihapus</SelectItem>
              <SelectItem value="ai_error,reply_failed">Error</SelectItem>
              <SelectItem value="summary_run">Ringkasan harian</SelectItem>
              <SelectItem value="settings_changed">Perubahan pengaturan</SelectItem>
            </SelectContent>
          </Select>
          <Button data-testid="wa-audit-refresh" size="sm" variant="outline" onClick={loadAudit} className="rounded-sm border-border hover:border-primary hover:text-primary"><ArrowClockwiseIcon size={14} weight="bold" /></Button>
        </div>
        <div className="max-h-[560px] overflow-y-auto">{loadingAudit ? <div className="p-4 space-y-2">{[0, 1, 2].map(i => <Skeleton key={i} className="h-8 rounded-sm" />)}</div> : <AuditList rows={audit} />}</div>
      </div>
    </div>
  );
}

const ST = { sent: ["Terkirim", "border-emerald-500/60 text-emerald-400"], preview: ["Simulasi", "border-sky-400/50 text-sky-300"], skipped: ["Dilewati", "border-border text-muted-foreground"], failed: ["Gagal", "border-accent text-accent"] };

export function SummaryTab() {
  const [cfg, setCfg] = useState(null);
  const [tanggal, setTanggal] = useState("");
  const [items, setItems] = useState(null);
  const [hist, setHist] = useState([]);
  const [busy, setBusy] = useState("");
  const load = async () => {
    try {
      const [{ data: c }, { data: h }] = await Promise.all([api.get("/wa/summary/settings"), api.get("/wa/summary/history")]);
      setCfg(c); setHist(h); setTanggal((t) => t || c.today);
    } catch { toast.error("Gagal memuat ringkasan harian"); }
  };
  useEffect(() => { load(); }, []);
  const preview = async () => {
    setBusy("preview");
    try { setItems((await api.get("/wa/summary/preview", { params: { tanggal } })).data.items); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal membuat pratinjau"); }
    finally { setBusy(""); }
  };
  const runNow = async () => {
    if (!window.confirm(`Jalankan ringkasan tanggal ${tanggal} sekarang?${cfg?.whatsapp_configured ? " Pesan akan dikirim ke WhatsApp pengurus." : " (WhatsApp belum terhubung — disimpan sebagai simulasi)"}`)) return;
    setBusy("run");
    try {
      const { data } = await api.post("/wa/summary/run", { tanggal, force: true });
      const c = data.counts; toast.success(`Selesai · terkirim ${c.sent}, simulasi ${c.preview}, dilewati ${c.skipped}, gagal ${c.failed}`); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menjalankan ringkasan"); }
    finally { setBusy(""); }
  };
  const saveCfg = async () => {
    setBusy("save");
    try { setCfg((await api.put("/wa/summary/settings", { enabled: cfg.enabled, template_name: cfg.template_name, template_lang: cfg.template_lang })).data); toast.success("Pengaturan ringkasan tersimpan"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
    finally { setBusy(""); }
  };
  const copy = (t) => { navigator.clipboard?.writeText(t); toast.success("Disalin"); };

  return (
    <div className="space-y-4" data-testid="wa-summary-tab">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="border border-border bg-card p-5 space-y-4">
          <div className="flex items-center gap-2"><CalendarIcon size={20} weight="bold" className="text-primary" /><p className="font-display font-black text-xl tracking-tighter">Jadwal & Template</p></div>
          {!cfg ? <Skeleton className="h-40 rounded-sm" /> : (
            <>
              <p className="text-sm" data-testid="wa-summary-schedule"><b>{cfg.schedule}</b></p>
              <div className="flex items-center justify-between border border-border p-3"><Label htmlFor="sum-en" className="text-sm cursor-pointer">Kirim otomatis setiap hari</Label><Switch id="sum-en" data-testid="wa-summary-enabled" checked={!!cfg.enabled} onCheckedChange={(v) => setCfg({ ...cfg, enabled: v })} /></div>
              <div><Label className={lbl}>Nama template Utility (Meta)</Label><Input data-testid="wa-summary-template" className="rounded-sm mt-1.5 font-mono" placeholder="ringkasan_harian" value={cfg.template_name} onChange={(e) => setCfg({ ...cfg, template_name: e.target.value })} /></div>
              <div><Label className={lbl}>Kode bahasa</Label><Input data-testid="wa-summary-lang" className="rounded-sm mt-1.5 font-mono w-24" value={cfg.template_lang} onChange={(e) => setCfg({ ...cfg, template_lang: e.target.value })} /></div>
              <Button data-testid="wa-summary-save" disabled={busy === "save"} onClick={saveCfg} className="w-full rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><FloppyDiskIcon size={16} weight="bold" className="mr-2" /> Simpan</Button>
              <div className="text-xs space-y-1 pt-2 border-t border-border">
                <p className="flex gap-2">{cfg.whatsapp_configured ? <CheckCircleIcon size={14} className="text-emerald-400" /> : <WarningIcon size={14} className="text-primary" />} WhatsApp {cfg.whatsapp_configured ? "terhubung" : "belum terhubung — hasil disimpan sebagai simulasi"}</p>
                <p className="flex gap-2">{cfg.cron_secret_set ? <CheckCircleIcon size={14} className="text-emerald-400" /> : <WarningIcon size={14} className="text-accent" />} Penjadwal {cfg.cron_secret_set ? "siap" : "belum memiliki WEBHOOK_CRON_SECRET"}</p>
                <p className="text-muted-foreground">Dalam 24 jam setelah pengurus chat → pesan teks lengkap. Di luar 24 jam → template Utility (wajib disetujui Meta).</p>
              </div>
            </>
          )}
        </div>
        <div className="xl:col-span-2 border border-border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between"><p className={lbl}>// Teks template untuk didaftarkan di Meta (kategori Utility, bahasa Indonesia)</p>
            <Button data-testid="wa-template-copy" size="sm" variant="outline" onClick={() => copy(cfg?.template_text || "")} className="rounded-sm border-border hover:border-primary hover:text-primary"><CopySimpleIcon size={14} weight="bold" className="mr-1.5" /> Salin</Button></div>
          <pre data-testid="wa-template-text" className="text-xs font-mono whitespace-pre-wrap bg-background border border-border p-3">{cfg?.template_text}</pre>
          <p className="text-xs text-muted-foreground">Contoh isi variabel saat pendaftaran: {"{{1}}"} Pak Rudi · {"{{2}}"} 3 Feb 2026 · {"{{3}}"} Sdlg 10 1.024-1.032 = 8 jam | Total 8 jam · {"{{4}}"} Rp5.000.000 Ref 2297984 | Total Rp5.000.000 · {"{{5}}"} Rp3.400.000 (tagihan Rp8.400.000, dibayar Rp5.000.000, saldo awal Rp0) · {"{{6}}"} 0 item</p>
        </div>
      </div>

      <div className="border border-border bg-card">
        <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border">
          <p className="font-display font-black text-xl tracking-tighter mr-auto">Pratinjau & Uji Kirim</p>
          <Input data-testid="wa-summary-date" type="date" value={tanggal} onChange={(e) => setTanggal(e.target.value)} className="rounded-sm w-auto bg-background" />
          <Button data-testid="wa-summary-preview" variant="outline" disabled={!!busy || !tanggal} onClick={preview} className="rounded-sm border-border hover:border-primary hover:text-primary"><EyeIcon size={16} weight="bold" className="mr-2" /> {busy === "preview" ? "Memuat…" : "Pratinjau"}</Button>
          <Button data-testid="wa-summary-run" disabled={!!busy || !tanggal} onClick={runNow} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><PaperPlaneTiltIcon size={16} weight="bold" className="mr-2" /> {busy === "run" ? "Menjalankan…" : "Jalankan Sekarang"}</Button>
        </div>
        {items === null ? <p className="p-6 text-xs font-mono text-muted-foreground">// Pilih tanggal lalu klik Pratinjau untuk melihat isi pesan setiap pengurus</p> :
          items.length === 0 ? <p className="p-6 text-xs font-mono text-muted-foreground" data-testid="wa-summary-empty">// Belum ada pengurus. Daftarkan pengurus & unit, lalu tambahkan nomor WA di tab Kontak WA (tipe Pengurus).</p> : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4" data-testid="wa-summary-previews">
              {items.map((it) => (
                <div key={it.pengurus} className="border border-border" data-testid={`wa-summary-card-${it.pengurus.replace(/\s+/g, "-")}`}>
                  <div className="flex items-center justify-between gap-2 p-3 bg-muted border-b border-border">
                    <div><p className="font-semibold">{it.pengurus}</p><p className="font-mono text-[10px] text-muted-foreground">{it.phone ? `+${it.phone}` : "Nomor WA belum terdaftar — tidak akan dikirim"}</p></div>
                    <div className="text-right font-mono text-[10px]"><p>{it.total_jam} jam · {formatIDR(it.total_transfer)}</p><p className={it.piutang.piutang > 0 ? "text-accent" : "text-emerald-400"}>Piutang {formatIDR(it.piutang.piutang)}</p></div>
                  </div>
                  <pre className="text-xs whitespace-pre-wrap p-3 font-mono max-h-80 overflow-y-auto">{it.text}</pre>
                </div>
              ))}
            </div>
          )}
      </div>

      <div className="border border-border bg-card overflow-x-auto">
        <p className="font-display font-black text-xl tracking-tighter p-4 border-b border-border">Riwayat Pengiriman</p>
        <table className="w-full text-sm" data-testid="wa-summary-history">
          <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-3">Waktu</th><th className="p-3">Tanggal Laporan</th><th className="p-3">Pengurus</th><th className="p-3">Pemicu</th><th className="p-3">Status</th><th className="p-3">Mode</th><th className="p-3">Keterangan</th></tr></thead>
          <tbody>
            {hist.length === 0 && <tr><td colSpan={7} className="p-6 text-center text-xs font-mono text-muted-foreground">// Belum ada riwayat</td></tr>}
            {hist.map((h) => {
              const [l, c] = ST[h.status] || [h.status, "border-border"];
              return (
                <tr key={h.id} className="border-t border-border">
                  <td className="p-3 font-mono text-xs whitespace-nowrap">{fmt(h.created_at)}</td><td className="p-3 font-mono text-xs">{h.tanggal}</td><td className="p-3">{h.pengurus}</td>
                  <td className="p-3 text-xs">{h.trigger === "cron" ? "Terjadwal" : `Manual · ${h.actor}`}</td>
                  <td className="p-3"><span className={`font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${c}`}>{l}</span></td>
                  <td className="p-3 font-mono text-xs">{h.mode || "-"}</td><td className="p-3 text-xs text-muted-foreground">{h.error || "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
