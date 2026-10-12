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
  BellRingingIcon, FloppyDiskIcon, PaperPlaneTiltIcon, EyeIcon, CopySimpleIcon, WarningIcon, CheckCircleIcon,
  ArrowClockwiseIcon, ChartBarIcon, PlusIcon, TrashIcon, CircleNotchIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
const fmt = (s) => (s ? new Date(s).toLocaleString("id-ID", { timeZone: "Asia/Makassar", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) + " WITA" : "-");
const ST = {
  sent: ["Terkirim", "border-emerald-500/60 text-emerald-400"], simulated: ["Simulasi", "border-sky-400/50 text-sky-300"],
  skipped: ["Dilewati", "border-border text-muted-foreground"], failed: ["Gagal", "border-accent text-accent"],
};
const HARI = [[1, "Sen"], [2, "Sel"], [3, "Rab"], [4, "Kam"], [5, "Jum"], [6, "Sab"], [7, "Min"]];
const Pill = ({ status, testid }) => { const [l, c] = ST[status] || [status, "border-border"]; return <span data-testid={testid} className={`font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${c}`}>{l}</span>; };
const copy = (t) => { navigator.clipboard?.writeText(t); toast.success("Disalin"); };

function SimNote({ configured }) {
  return (
    <p className="flex gap-2 text-xs">{configured ? <CheckCircleIcon size={14} className="text-emerald-400 shrink-0" /> : <WarningIcon size={14} className="text-primary shrink-0" />}
      {configured ? "WhatsApp dikonfigurasi — pesan dikirim sungguhan" : "Mode simulasi — pesan TIDAK dikirim, hanya dicatat di Pesan Keluar"}</p>
  );
}

function HistoryTable({ rows, cols, testid }) {
  return (
    <div className="border border-border bg-card overflow-x-auto">
      <p className="font-display font-black text-xl tracking-tighter p-4 border-b border-border">Riwayat Pengiriman</p>
      <table className="w-full text-sm" data-testid={testid}>
        <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">{cols.map(([h]) => <th key={h} className="p-3">{h}</th>)}</tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={cols.length} className="p-6 text-center text-xs font-mono text-muted-foreground">// Belum ada riwayat</td></tr>}
          {rows.map((r) => <tr key={r.id} className="border-t border-border">{cols.map(([h, f]) => <td key={h} className="p-3 text-xs">{f(r)}</td>)}</tr>)}
        </tbody>
      </table>
    </div>
  );
}

export function ReminderTab() {
  const [cfg, setCfg] = useState(null);
  const [aging, setAging] = useState(null);
  const [pv, setPv] = useState(null);
  const [hist, setHist] = useState([]);
  const [busy, setBusy] = useState("");
  const [excl, setExcl] = useState("");
  const load = async () => {
    try {
      const [c, a, h] = await Promise.all([api.get("/wa/reminder/settings"), api.get("/wa/piutang/aging"), api.get("/wa/reminder/history")]);
      setCfg(c.data); setExcl((c.data.exclude || []).join(", ")); setAging(a.data); setHist(h.data);
    } catch { toast.error("Gagal memuat pengingat piutang"); }
  };
  useEffect(() => { load(); }, []);
  const save = async () => {
    setBusy("save");
    try {
      const body = { ...cfg, send_hour: Number(cfg.send_hour), min_nominal: Number(cfg.min_nominal), min_age_days: Number(cfg.min_age_days), cooldown_days: Number(cfg.cooldown_days), exclude: excl.split(",").map((x) => x.trim()).filter(Boolean) };
      ["template_text", "whatsapp_configured", "cron_secret_set", "today"].forEach((k) => delete body[k]);
      setCfg((await api.put("/wa/reminder/settings", body)).data); toast.success("Pengaturan pengingat tersimpan");
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
    finally { setBusy(""); }
  };
  const preview = async () => { setBusy("pv"); try { setPv((await api.get("/wa/reminder/preview")).data.items); } catch { toast.error("Gagal membuat pratinjau"); } finally { setBusy(""); } };
  const run = async (force) => {
    if (!window.confirm(force ? "Kirim paksa mengabaikan masa jeda & batas nominal/umur (tetap tidak mengirim ke yang lunas / ada transfer menunggu verifikasi). Lanjutkan?" : "Jalankan pengingat sekarang sesuai aturan?")) return;
    setBusy(force ? "force" : "run");
    try { const { data } = await api.post("/wa/reminder/run", { force }); const c = data.counts; toast.success(`Selesai · terkirim ${c.sent}, simulasi ${c.simulated}, dilewati ${c.skipped}, gagal ${c.failed}`); load(); preview(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal"); }
    finally { setBusy(""); }
  };
  const toggleDay = (d) => setCfg((c) => ({ ...c, days: c.days.includes(d) ? c.days.filter((x) => x !== d) : [...c.days, d].sort() }));

  return (
    <div className="space-y-4" data-testid="wa-reminder-tab">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="border border-border bg-card p-5 space-y-4">
          <div className="flex items-center gap-2"><BellRingingIcon size={20} weight="bold" className="text-primary" /><p className="font-display font-black text-xl tracking-tighter">Pengingat Piutang</p></div>
          {!cfg ? <Skeleton className="h-72 rounded-sm" /> : (
            <>
              <div className="flex items-center justify-between border border-border p-3"><Label htmlFor="rem-en" className="text-sm cursor-pointer">Kirim otomatis terjadwal</Label><Switch id="rem-en" data-testid="wa-reminder-enabled" checked={!!cfg.enabled} onCheckedChange={(v) => setCfg({ ...cfg, enabled: v })} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className={lbl}>Jam kirim (WITA)</Label>
                  <Select value={String(cfg.send_hour)} onValueChange={(v) => setCfg({ ...cfg, send_hour: Number(v) })}>
                    <SelectTrigger data-testid="wa-reminder-hour" className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger>
                    <SelectContent>{Array.from({ length: 24 }, (_, h) => <SelectItem key={h} value={String(h)}>{String(h).padStart(2, "0")}:00</SelectItem>)}</SelectContent>
                  </Select></div>
                <div><Label className={lbl}>Masa jeda (hari)</Label><Input data-testid="wa-reminder-cooldown" type="number" min={1} max={60} className="rounded-sm mt-1.5 font-mono" value={cfg.cooldown_days} onChange={(e) => setCfg({ ...cfg, cooldown_days: e.target.value })} /></div>
                <div><Label className={lbl}>Batas nominal (Rp)</Label><Input data-testid="wa-reminder-min-nominal" type="number" min={0} step={100000} className="rounded-sm mt-1.5 font-mono" value={cfg.min_nominal} onChange={(e) => setCfg({ ...cfg, min_nominal: e.target.value })} /></div>
                <div><Label className={lbl}>Umur minimal (hari)</Label><Input data-testid="wa-reminder-min-age" type="number" min={0} className="rounded-sm mt-1.5 font-mono" value={cfg.min_age_days} onChange={(e) => setCfg({ ...cfg, min_age_days: e.target.value })} /></div>
              </div>
              <div><Label className={lbl}>Hari kirim</Label>
                <div className="flex flex-wrap gap-1 mt-1.5">{HARI.map(([d, l]) => (
                  <button key={d} type="button" data-testid={`wa-reminder-day-${d}`} onClick={() => toggleDay(d)} className={`px-2.5 py-1.5 text-xs font-mono border transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${cfg.days.includes(d) ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>{l}</button>
                ))}</div></div>
              <div className="flex items-center justify-between border border-border p-3"><Label htmlFor="rem-pend" className="text-sm cursor-pointer">Lewati bila ada transfer menunggu verifikasi</Label><Switch id="rem-pend" data-testid="wa-reminder-skip-pending" checked={!!cfg.skip_if_pending_transfer} onCheckedChange={(v) => setCfg({ ...cfg, skip_if_pending_transfer: v })} /></div>
              <div className="flex items-center justify-between border border-border p-3"><Label htmlFor="rem-cc" className="text-sm cursor-pointer">Tembusan ke pemilik</Label><Switch id="rem-cc" data-testid="wa-reminder-cc-owner" checked={!!cfg.cc_owner} onCheckedChange={(v) => setCfg({ ...cfg, cc_owner: v })} /></div>
              <div><Label className={lbl}>Kecualikan pengurus (pisahkan koma)</Label><Input data-testid="wa-reminder-exclude" className="rounded-sm mt-1.5" value={excl} onChange={(e) => setExcl(e.target.value)} placeholder="mis. Pak Rudi" /></div>
              <div className="grid grid-cols-3 gap-2"><div className="col-span-2"><Label className={lbl}>Template Utility (Meta)</Label><Input data-testid="wa-reminder-template" className="rounded-sm mt-1.5 font-mono" placeholder="pengingat_piutang" value={cfg.template_name} onChange={(e) => setCfg({ ...cfg, template_name: e.target.value })} /></div>
                <div><Label className={lbl}>Bahasa</Label><Input data-testid="wa-reminder-lang" className="rounded-sm mt-1.5 font-mono" value={cfg.template_lang} onChange={(e) => setCfg({ ...cfg, template_lang: e.target.value })} /></div></div>
              <Button data-testid="wa-reminder-save" disabled={busy === "save"} onClick={save} className="w-full rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><FloppyDiskIcon size={16} weight="bold" className="mr-2" /> Simpan Pengaturan</Button>
              <div className="pt-2 border-t border-border space-y-1"><SimNote configured={cfg.whatsapp_configured} /><p className="text-xs text-muted-foreground">Pengecekan tiap jam; dikirim maks. 1x per hari pada jam & hari terpilih. Lunas tidak pernah diingatkan.</p></div>
            </>
          )}
        </div>

        <div className="xl:col-span-2 border border-border bg-card">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border">
            <p className="font-display font-black text-xl tracking-tighter mr-auto">Umur Piutang per Pengurus</p>
            <span className="font-mono text-xs" data-testid="wa-aging-total">Total: <b className="text-accent">{formatIDR(aging?.total || 0)}</b> · per {aging?.as_of}</span>
            <Button data-testid="wa-aging-refresh" size="sm" variant="outline" onClick={load} className="rounded-sm border-border hover:border-primary hover:text-primary"><ArrowClockwiseIcon size={14} weight="bold" /></Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="wa-aging-table">
              <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-3">Pengurus</th><th className="p-3 text-right">Tagihan</th><th className="p-3 text-right">Dibayar</th><th className="p-3 text-right">Piutang</th><th className="p-3 text-right">0–30</th><th className="p-3 text-right">31–60</th><th className="p-3 text-right">61–90</th><th className="p-3 text-right">&gt;90</th><th className="p-3">Tertua</th></tr></thead>
              <tbody>
                {!aging && <tr><td colSpan={9} className="p-3"><Skeleton className="h-5 w-full rounded-sm" /></td></tr>}
                {aging && aging.items.length === 0 && <tr><td colSpan={9} className="p-6 text-center text-xs font-mono text-muted-foreground">// Belum ada pengurus</td></tr>}
                {aging?.items.map((a) => (
                  <tr key={a.pengurus} className="border-t border-border" data-testid={`wa-aging-row-${a.pengurus.replace(/\s+/g, "-")}`}>
                    <td className="p-3"><p className="font-semibold">{a.pengurus}</p><p className="font-mono text-[10px] text-muted-foreground">{a.phone ? `+${a.phone}` : "belum ada nomor WA"}{a.pending_transfer ? ` · ${a.pending_transfer} transfer menunggu` : ""}</p></td>
                    <td className="p-3 text-right font-mono text-xs">{formatIDR(a.total_tagihan)}</td><td className="p-3 text-right font-mono text-xs">{formatIDR(a.total_bayar)}</td>
                    <td className={`p-3 text-right font-mono text-xs font-bold ${a.piutang > 0 ? "text-accent" : "text-emerald-400"}`}>{a.piutang < 0 ? `Lebih ${formatIDR(-a.piutang)}` : formatIDR(a.piutang)}</td>
                    {["0_30", "31_60", "61_90", "90_plus"].map((k) => <td key={k} className="p-3 text-right font-mono text-[11px] text-muted-foreground">{a.buckets[k] ? formatIDR(a.buckets[k]) : "-"}</td>)}
                    <td className="p-3 font-mono text-[11px]">{a.oldest_unpaid ? `${a.oldest_unpaid} (${a.umur_hari} hr)` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="p-4 text-xs text-muted-foreground border-t border-border">Tagihan = jam kerja Ops Report × tarif sewa. Pembayaran = Kas Masuk tervalidasi (bukti WA dihitung setelah disetujui). Umur dihitung FIFO: pembayaran melunasi tagihan tertua lebih dulu.</p>
        </div>
      </div>

      <div className="border border-border bg-card">
        <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border">
          <p className="font-display font-black text-xl tracking-tighter mr-auto">Pratinjau & Uji Kirim</p>
          <Button data-testid="wa-reminder-preview" variant="outline" disabled={!!busy} onClick={preview} className="rounded-sm border-border hover:border-primary hover:text-primary"><EyeIcon size={16} weight="bold" className="mr-2" /> {busy === "pv" ? "Memuat…" : "Pratinjau"}</Button>
          <Button data-testid="wa-reminder-run" disabled={!!busy} onClick={() => run(false)} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><PaperPlaneTiltIcon size={16} weight="bold" className="mr-2" /> {busy === "run" ? "Menjalankan…" : "Jalankan Sekarang"}</Button>
          <Button data-testid="wa-reminder-force" variant="outline" disabled={!!busy} onClick={() => run(true)} className="rounded-sm border-accent/60 text-accent hover:bg-accent/10 hover:text-accent">Kirim Paksa</Button>
        </div>
        {pv === null ? <p className="p-6 text-xs font-mono text-muted-foreground">// Klik Pratinjau untuk melihat siapa yang akan diingatkan hari ini & alasannya</p> : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4" data-testid="wa-reminder-previews">
            {pv.length === 0 && <p className="text-xs font-mono text-muted-foreground">// Belum ada pengurus</p>}
            {pv.map((x) => (
              <div key={x.pengurus} className={`border ${x.eligible ? "border-primary" : "border-border"}`} data-testid={`wa-reminder-card-${x.pengurus.replace(/\s+/g, "-")}`}>
                <div className="flex items-center justify-between gap-2 p-3 bg-muted border-b border-border">
                  <div><p className="font-semibold">{x.pengurus}</p><p className="font-mono text-[10px] text-muted-foreground">{x.phone ? `+${x.phone}` : "Nomor WA belum terdaftar"}</p></div>
                  <span className={`font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${x.eligible ? "border-primary text-primary" : "border-border text-muted-foreground"}`}>{x.eligible ? "Akan diingatkan" : "Dilewati"}</span>
                </div>
                {!x.eligible && <p className="px-3 pt-2 text-xs text-muted-foreground" data-testid={`wa-reminder-reason-${x.pengurus.replace(/\s+/g, "-")}`}>Alasan: {x.reason}</p>}
                {x.piutang > 0 && <pre className="text-xs whitespace-pre-wrap p-3 font-mono max-h-64 overflow-y-auto">{x.text}</pre>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border border-border bg-card p-5 space-y-2">
        <div className="flex items-center justify-between"><p className={lbl}>// Teks template Utility untuk didaftarkan di Meta (nanti)</p>
          <Button data-testid="wa-reminder-template-copy" size="sm" variant="outline" onClick={() => copy(cfg?.template_text || "")} className="rounded-sm border-border hover:border-primary hover:text-primary"><CopySimpleIcon size={14} weight="bold" className="mr-1.5" /> Salin</Button></div>
        <pre className="text-xs font-mono whitespace-pre-wrap bg-background border border-border p-3">{cfg?.template_text}</pre>
      </div>

      <HistoryTable testid="wa-reminder-history" rows={hist} cols={[
        ["Waktu", (h) => <span className="font-mono whitespace-nowrap">{fmt(h.created_at)}</span>], ["Pengurus", (h) => h.pengurus],
        ["Piutang", (h) => <span className="font-mono">{formatIDR(h.piutang)}</span>], ["Umur", (h) => `${h.umur_hari} hr`],
        ["Pemicu", (h) => (h.trigger === "cron" ? "Terjadwal" : `Manual · ${h.actor}`)], ["Status", (h) => <Pill status={h.status} />], ["Keterangan", (h) => <span className="text-muted-foreground">{h.error || "-"}</span>],
      ]} />
    </div>
  );
}

export function WeeklyTab() {
  const [cfg, setCfg] = useState(null);
  const [week, setWeek] = useState("");
  const [rep, setRep] = useState(null);
  const [hist, setHist] = useState([]);
  const [busy, setBusy] = useState("");
  const load = async () => {
    try {
      const [c, h] = await Promise.all([api.get("/wa/weekly/settings"), api.get("/wa/weekly/history")]);
      setCfg(c.data); setHist(h.data); setWeek((w) => w || c.data.default_week_start);
    } catch { toast.error("Gagal memuat laporan mingguan"); }
  };
  useEffect(() => { load(); }, []);
  const preview = async () => { setBusy("pv"); try { const { data } = await api.get("/wa/weekly/preview", { params: { week_start: week } }); setRep(data); setWeek(data.week_start); } catch (e) { toast.error(e?.response?.data?.detail || "Gagal"); } finally { setBusy(""); } };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (week && !rep) preview(); }, [week]);
  const save = async () => {
    setBusy("save");
    try { setCfg((await api.put("/wa/weekly/settings", { enabled: cfg.enabled, recipients: cfg.recipients, template_name: cfg.template_name, template_lang: cfg.template_lang })).data); toast.success("Pengaturan laporan mingguan tersimpan"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
    finally { setBusy(""); }
  };
  const run = async (force) => {
    if (!window.confirm(`Kirim laporan minggu ${rep?.periode || week}${force ? " (kirim ulang paksa)" : ""}?`)) return;
    setBusy(force ? "force" : "run");
    try { const { data } = await api.post("/wa/weekly/run", { week_start: week, force }); const c = data.counts; toast.success(`Selesai · terkirim ${c.sent}, simulasi ${c.simulated}, dilewati ${c.skipped}, gagal ${c.failed}`); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal"); }
    finally { setBusy(""); }
  };
  const setRc = (i, k, v) => setCfg((c) => ({ ...c, recipients: c.recipients.map((r, j) => (j === i ? { ...r, [k]: v } : r)) }));

  return (
    <div className="space-y-4" data-testid="wa-weekly-tab">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="border border-border bg-card p-5 space-y-4">
          <div className="flex items-center gap-2"><ChartBarIcon size={20} weight="bold" className="text-primary" /><p className="font-display font-black text-xl tracking-tighter">Laporan Mingguan Pemilik</p></div>
          {!cfg ? <Skeleton className="h-60 rounded-sm" /> : (
            <>
              <p className="text-sm" data-testid="wa-weekly-schedule"><b>{cfg.schedule}</b></p>
              <div className="flex items-center justify-between border border-border p-3"><Label htmlFor="wk-en" className="text-sm cursor-pointer">Kirim otomatis setiap Senin</Label><Switch id="wk-en" data-testid="wa-weekly-enabled" checked={!!cfg.enabled} onCheckedChange={(v) => setCfg({ ...cfg, enabled: v })} /></div>
              <div className="space-y-2"><Label className={lbl}>Penerima</Label>
                {cfg.recipients.map((r, i) => (
                  <div key={i} className="flex gap-2">
                    <Input data-testid={`wa-weekly-rc-name-${i}`} className="rounded-sm w-28" value={r.nama} onChange={(e) => setRc(i, "nama", e.target.value)} />
                    <Input data-testid={`wa-weekly-rc-phone-${i}`} className="rounded-sm font-mono" value={r.phone} onChange={(e) => setRc(i, "phone", e.target.value)} />
                    <Button data-testid={`wa-weekly-rc-del-${i}`} size="icon" variant="outline" disabled={cfg.recipients.length <= 1} onClick={() => setCfg((c) => ({ ...c, recipients: c.recipients.filter((_, j) => j !== i) }))} className="rounded-sm border-border hover:border-accent hover:text-accent shrink-0" aria-label="Hapus penerima"><TrashIcon size={14} /></Button>
                  </div>
                ))}
                <Button data-testid="wa-weekly-rc-add" size="sm" variant="outline" onClick={() => setCfg((c) => ({ ...c, recipients: [...c.recipients, { nama: "", phone: "" }] }))} className="rounded-sm border-border hover:border-primary hover:text-primary"><PlusIcon size={14} className="mr-1.5" /> Tambah penerima</Button>
              </div>
              <div className="grid grid-cols-3 gap-2"><div className="col-span-2"><Label className={lbl}>Template Utility (Meta)</Label><Input data-testid="wa-weekly-template" className="rounded-sm mt-1.5 font-mono" placeholder="laporan_mingguan" value={cfg.template_name} onChange={(e) => setCfg({ ...cfg, template_name: e.target.value })} /></div>
                <div><Label className={lbl}>Bahasa</Label><Input data-testid="wa-weekly-lang" className="rounded-sm mt-1.5 font-mono" value={cfg.template_lang} onChange={(e) => setCfg({ ...cfg, template_lang: e.target.value })} /></div></div>
              <Button data-testid="wa-weekly-save" disabled={busy === "save"} onClick={save} className="w-full rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><FloppyDiskIcon size={16} weight="bold" className="mr-2" /> Simpan</Button>
              <div className="pt-2 border-t border-border"><SimNote configured={cfg.whatsapp_configured} /></div>
              <div className="space-y-1.5"><div className="flex items-center justify-between"><p className={lbl}>// Template Meta</p><Button data-testid="wa-weekly-template-copy" size="sm" variant="ghost" onClick={() => copy(cfg.template_text)} className="h-7 rounded-sm hover:text-primary"><CopySimpleIcon size={13} /></Button></div>
                <pre className="text-[11px] font-mono whitespace-pre-wrap bg-background border border-border p-2">{cfg.template_text}</pre></div>
            </>
          )}
        </div>
        <div className="xl:col-span-2 border border-border bg-card">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border">
            <p className="font-display font-black text-xl tracking-tighter mr-auto">Pratinjau {rep ? <span className="font-mono text-xs text-muted-foreground">{rep.periode}</span> : null}</p>
            <Input data-testid="wa-weekly-date" type="date" value={week} onChange={(e) => setWeek(e.target.value)} className="rounded-sm w-auto bg-background" />
            <Button data-testid="wa-weekly-preview" variant="outline" disabled={!!busy || !week} onClick={preview} className="rounded-sm border-border hover:border-primary hover:text-primary">{busy === "pv" ? <CircleNotchIcon size={16} className="mr-2 animate-spin" /> : <EyeIcon size={16} weight="bold" className="mr-2" />} Pratinjau</Button>
            <Button data-testid="wa-weekly-run" disabled={!!busy || !rep} onClick={() => run(false)} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><PaperPlaneTiltIcon size={16} weight="bold" className="mr-2" /> Kirim</Button>
            <Button data-testid="wa-weekly-force" variant="outline" disabled={!!busy || !rep} onClick={() => run(true)} className="rounded-sm border-accent/60 text-accent hover:bg-accent/10 hover:text-accent">Kirim Ulang Paksa</Button>
          </div>
          {!rep ? <div className="p-4"><Skeleton className="h-60 rounded-sm" /></div> : (
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 border border-border">
                {[["Total jam (HM)", `${rep.total_jam.toLocaleString("id-ID")} jam`, "text-primary"], ["Total pemasukan", formatIDR(rep.total_pemasukan), "text-emerald-400"], ["Pembayaran sewa", formatIDR(rep.total_bayar), "text-emerald-400"], ["Piutang berjalan", formatIDR(rep.total_piutang), "text-accent"]].map(([l, v, t], i) => (
                  <div key={l} className={`p-3 ${i ? "border-l border-border" : ""}`}><p className={lbl}>{l}</p><p data-testid={`wa-weekly-stat-${i}`} className={`font-display font-black text-xl tracking-tighter ${t}`}>{v}</p></div>
                ))}
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <table className="w-full text-xs border border-border" data-testid="wa-weekly-units">
                  <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-2">Unit</th><th className="p-2 text-right">HM Awal</th><th className="p-2 text-right">HM Akhir</th><th className="p-2 text-right">Jam</th><th className="p-2 text-right">Hari</th></tr></thead>
                  <tbody>{rep.units.length === 0 ? <tr><td colSpan={5} className="p-3 text-center text-muted-foreground font-mono">// Tidak ada laporan HM</td></tr> : rep.units.map((u) => (
                    <tr key={u.unit} className="border-t border-border"><td className="p-2">{u.unit}</td><td className="p-2 text-right font-mono">{u.hm_awal}</td><td className="p-2 text-right font-mono">{u.hm_akhir}</td><td className="p-2 text-right font-mono font-bold">{u.jam}</td><td className="p-2 text-right font-mono">{u.hari}</td></tr>))}</tbody>
                </table>
                <pre className="text-xs whitespace-pre-wrap p-3 font-mono max-h-80 overflow-y-auto bg-background border border-border" data-testid="wa-weekly-text">{rep.text}</pre>
              </div>
            </div>
          )}
        </div>
      </div>
      <HistoryTable testid="wa-weekly-history" rows={hist} cols={[
        ["Waktu", (h) => <span className="font-mono whitespace-nowrap">{fmt(h.created_at)}</span>], ["Periode", (h) => <span className="font-mono">{h.week_start} – {h.week_end}</span>],
        ["Penerima", (h) => `${h.nama} +${h.phone}`], ["Pemicu", (h) => (h.trigger === "cron" ? "Terjadwal" : `Manual · ${h.actor}`)],
        ["Status", (h) => <Pill status={h.status} />], ["Keterangan", (h) => <span className="text-muted-foreground">{h.error || "-"}</span>],
      ]} />
    </div>
  );
}
