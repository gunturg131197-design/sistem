import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { WA_GUIDE } from "@/lib/waGuide";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import {
  PlugsConnectedIcon, PlugsIcon, CopySimpleIcon, CheckCircleIcon, CircleIcon, WarningIcon, ArrowClockwiseIcon,
  PaperPlaneTiltIcon, ShieldCheckIcon, CircleNotchIcon, ReceiptIcon, GaugeIcon, PhoneIcon, LinkIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
const fmt = (s) => (s ? new Date(s).toLocaleString("id-ID", { timeZone: "Asia/Makassar", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) + " WITA" : "-");

export const LEVEL = {
  not_configured: { tone: "border-primary/60 text-primary", icon: PlugsIcon, short: "WhatsApp Belum Dikonfigurasi · mode upload" },
  unverified: { tone: "border-primary/60 text-primary", icon: PlugsIcon, short: "Kredensial Terisi · Belum Diuji" },
  partial: { tone: "border-sky-400/60 text-sky-300", icon: PlugsIcon, short: "WhatsApp Sebagian Terverifikasi" },
  connected: { tone: "border-emerald-500/60 text-emerald-400", icon: PlugsConnectedIcon, short: "WhatsApp Terhubung · Terverifikasi" },
};

function Check({ ok, label, sub, testid }) {
  return (
    <li className="flex items-start gap-2.5" data-testid={testid}>
      {ok ? <CheckCircleIcon size={18} weight="fill" className="text-emerald-400 shrink-0" /> : <CircleIcon size={18} className="text-muted-foreground shrink-0" />}
      <div><p className={`text-sm ${ok ? "text-foreground" : "text-muted-foreground"}`}>{label}</p>{sub && <p className="font-mono text-[10px] text-muted-foreground">{sub}</p>}</div>
    </li>
  );
}

export function ConnectionTab({ onChanged }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState("");
  const [check, setCheck] = useState(null);
  const [to, setTo] = useState("");
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("Pesan uji dari aplikasi TRIRARA TUNGGAL PUTRA.");
  const [pin, setPin] = useState("");
  const webhook = `${process.env.REACT_APP_BACKEND_URL}/api/whatsapp/webhook`;
  const privacy = `${window.location.origin}/kebijakan-privasi`;
  const load = async () => {
    try { const { data } = await api.get("/wa/connection"); setSt(data); setCheck(data.phone_check || null); onChanged && onChanged(data); }
    catch { toast.error("Gagal memuat status koneksi"); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);
  const copy = (t) => { navigator.clipboard?.writeText(t); toast.success("Disalin"); };
  const configured = st && st.level !== "not_configured";

  const run = async (kind) => {
    setBusy(kind);
    try {
      if (kind === "check") {
        const { data } = await api.post("/wa/cloud/check"); setCheck(data);
        data.ok ? toast.success(`Kredensial valid · ${data.display_phone_number || ""}`) : toast.error(`Tes koneksi gagal: ${data.error || data.http}`);
      } else if (kind === "send") {
        if (!to) { toast.error("Isi nomor tujuan"); setBusy(""); return; }
        const { data } = await api.post("/wa/cloud/send-test", { to, mode, text });
        if (data.deduped) toast.info("Pesan uji yang sama baru saja dikirim — tunggu 30 detik");
        else if (data.status === "sent") toast.success("Diterima Meta. Tunggu status Diterima (delivered) di tab Pesan Keluar.");
        else toast.error(`Gagal: ${data.error || data.status}`);
      } else if (kind === "register") {
        const { data } = await api.post("/wa/cloud/register", { pin }); setPin("");
        data.ok ? toast.success("Nomor terdaftar di Cloud API") : toast.error(`Gagal mendaftarkan: ${data.error}`);
      } else if (kind === "subscribe") {
        const { data } = await api.post("/wa/cloud/subscribe");
        data.ok ? toast.success("Aplikasi berlangganan webhook WABA") : toast.error(`Gagal: ${data.error}`);
      }
      await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal"); }
    finally { setBusy(""); }
  };

  if (!st) return <div className="grid xl:grid-cols-3 gap-4"><Skeleton className="h-72 rounded-sm" /><Skeleton className="h-72 rounded-sm xl:col-span-2" /></div>;
  const L = LEVEL[st.level] || LEVEL.not_configured;
  const Icon = L.icon;
  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4" data-testid="wa-settings-tab">
      <div className="space-y-4">
        <div className="border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between"><p className={lbl}>// Status Koneksi</p>
            <button data-testid="wa-conn-refresh" onClick={load} className="p-1.5 border border-border hover:border-primary hover:text-primary transition-colors duration-150" aria-label="Muat ulang status"><ArrowClockwiseIcon size={13} weight="bold" /></button>
          </div>
          <div className="flex items-center gap-3" data-testid="wa-connection-status">
            <Icon size={28} weight="bold" className={L.tone.split(" ").pop()} />
            <div>
              <p className="font-display font-black text-xl tracking-tighter" data-testid="wa-connection-label">{st.label}</p>
              <p className="font-mono text-[10px] text-muted-foreground">WhatsApp Business Cloud API (Meta) · {st.api_version}</p>
            </div>
          </div>
          <ul className="space-y-2.5 pt-1">
            <Check testid="wa-check-credentials" ok={configured} label="Kredensial terisi di server" sub={configured ? "Token & App Secret tersimpan aman (tidak ditampilkan)" : `Belum: ${st.missing.join(", ")}`} />
            <Check testid="wa-check-api" ok={!!check?.ok} label="Tes koneksi Graph API" sub={check ? (check.ok ? `${check.display_phone_number || ""} · ${check.verified_name || ""} · ${fmt(check.at)}` : `Gagal: ${check.error || check.http}`) : "Belum diuji"} />
            <Check testid="wa-check-inbound" ok={!!st.inbound_verified_at} label="Pesan masuk asli diterima" sub={st.inbound_verified_at ? `+${st.inbound_phone} · ${fmt(st.inbound_verified_at)}` : "Kirim pesan dari HP ke nomor perusahaan"} />
            <Check testid="wa-check-outbound" ok={!!st.outbound_verified_at} label="Pesan keluar sampai (delivered)" sub={st.outbound_verified_at ? `+${st.outbound_phone} · ${fmt(st.outbound_verified_at)}` : "Kirim Pesan Uji & tunggu status Diterima"} />
          </ul>
          <p className="text-[11px] text-muted-foreground border-t border-border pt-3">Status <b className="text-foreground">Terhubung</b> hanya tampil setelah pesan masuk DAN pesan keluar terkonfirmasi Meta. Mengganti nomor/token akan mereset status ini.</p>
        </div>

        <div className="border border-border bg-card p-5 space-y-3">
          <p className={lbl}>// Alat Uji</p>
          <Button data-testid="wa-cloud-check" disabled={!configured || !!busy} onClick={() => run("check")} variant="outline" className="w-full rounded-sm border-border hover:border-primary hover:text-primary">
            {busy === "check" ? <CircleNotchIcon size={14} className="mr-2 animate-spin" /> : <ShieldCheckIcon size={14} weight="bold" className="mr-2" />} Tes Koneksi
          </Button>
          <div className="space-y-2 pt-2 border-t border-border">
            <Label className={lbl}>Kirim Pesan Uji</Label>
            <Input data-testid="wa-test-to" className="rounded-sm font-mono" placeholder="Nomor tujuan, mis. 0812xxxx" value={to} onChange={(e) => setTo(e.target.value)} />
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger data-testid="wa-test-mode" className="rounded-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="text">Teks (penerima harus mengirim pesan dalam 24 jam terakhir)</SelectItem>
                <SelectItem value="template">Template hello_world (bawaan Meta)</SelectItem>
              </SelectContent>
            </Select>
            {mode === "text" && <Textarea data-testid="wa-test-text" className="rounded-sm text-sm" rows={2} value={text} onChange={(e) => setText(e.target.value)} />}
            <Button data-testid="wa-test-send" disabled={!configured || !!busy} onClick={() => run("send")} className="w-full rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">
              {busy === "send" ? <CircleNotchIcon size={14} className="mr-2 animate-spin" /> : <PaperPlaneTiltIcon size={14} weight="bold" className="mr-2" />} Kirim Pesan Uji
            </Button>
          </div>
          <div className="space-y-2 pt-2 border-t border-border">
            <Label className={lbl}>Daftarkan Nomor (PIN 2 langkah)</Label>
            <div className="flex gap-2">
              <Input data-testid="wa-register-pin" type="password" inputMode="numeric" maxLength={6} autoComplete="off" className="rounded-sm font-mono" placeholder="6 digit" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
              <Button data-testid="wa-register" disabled={!configured || !!busy || pin.length !== 6} onClick={() => run("register")} variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"><PhoneIcon size={14} weight="bold" className="mr-1.5" /> Daftar</Button>
            </div>
            <p className="font-mono text-[10px] text-muted-foreground">PIN tidak disimpan di server.</p>
            <Button data-testid="wa-subscribe" disabled={!configured || !!busy || !st.waba_id_set} onClick={() => run("subscribe")} variant="outline" className="w-full rounded-sm border-border hover:border-primary hover:text-primary"><LinkIcon size={14} weight="bold" className="mr-2" /> Langganan Webhook WABA</Button>
            {!st.waba_id_set && <p className="font-mono text-[10px] text-muted-foreground">Isi WHATSAPP_WABA_ID di Secrets untuk mengaktifkan.</p>}
          </div>
        </div>
      </div>

      <div className="xl:col-span-2 space-y-4">
        <div className="border border-border bg-card p-5 space-y-3">
          <p className={lbl}>// URL untuk Meta</p>
          <div><Label className="text-xs text-muted-foreground">Callback URL webhook</Label>
            <div className="flex gap-2 mt-1"><Input readOnly data-testid="wa-webhook-url" value={webhook} className="rounded-sm font-mono text-xs" />
              <Button data-testid="wa-webhook-copy" variant="outline" onClick={() => copy(webhook)} className="rounded-sm border-border hover:border-primary hover:text-primary"><CopySimpleIcon size={14} weight="bold" className="mr-1.5" /> Salin</Button></div>
          </div>
          <div><Label className="text-xs text-muted-foreground">Privacy Policy URL (wajib untuk mode Live)</Label>
            <div className="flex gap-2 mt-1"><Input readOnly data-testid="wa-privacy-url" value={privacy} className="rounded-sm font-mono text-xs" />
              <Button data-testid="wa-privacy-copy" variant="outline" onClick={() => copy(privacy)} className="rounded-sm border-border hover:border-primary hover:text-primary"><CopySimpleIcon size={14} weight="bold" className="mr-1.5" /> Salin</Button></div>
          </div>
          <p className="font-mono text-[10px] text-accent">Gunakan alamat aplikasi yang sudah di-deploy (bukan preview) agar webhook selalu aktif.</p>
        </div>

        <div className="border border-border bg-card p-5" data-testid="wa-guide">
          <p className={lbl}>// Panduan Konfigurasi Meta & Uji End-to-End</p>
          <Accordion type="single" collapsible className="mt-2">
            {WA_GUIDE.map((g, i) => (
              <AccordionItem key={g.id} value={g.id} className="border-border">
                <AccordionTrigger data-testid={`wa-guide-${g.id}`} className="text-sm hover:no-underline hover:text-primary">
                  <span className="flex gap-3 text-left"><span className="font-mono text-primary">{String(i + 1).padStart(2, "0")}</span>{g.title}</span>
                </AccordionTrigger>
                <AccordionContent>
                  {g.warn && <p className="text-xs border border-primary/50 bg-primary/10 p-2.5 mb-2 flex gap-2"><WarningIcon size={14} weight="bold" className="text-primary shrink-0 mt-0.5" />{g.warn}</p>}
                  <ul className="space-y-1.5">{g.items.map((t, j) => <li key={j} className="text-sm text-muted-foreground flex gap-2"><span className="text-primary">•</span><span>{t}</span></li>)}</ul>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        <div className="border border-border bg-card p-5">
          <p className={lbl}>// Format pesan untuk operator & pengurus</p>
          <div className="grid sm:grid-cols-2 gap-3 mt-2 text-sm">
            <div className="border border-border p-3"><ReceiptIcon size={16} weight="bold" className="text-primary mb-1" /><b>Bukti transfer</b><p className="text-muted-foreground text-xs mt-1">Kirim foto/screenshot bukti transfer dengan caption kode unit, contoh: <span className="font-mono text-foreground">Sdlg 10</span></p></div>
            <div className="border border-border p-3"><GaugeIcon size={16} weight="bold" className="text-primary mb-1" /><b>Laporan HM</b><p className="text-muted-foreground text-xs mt-1">Kirim foto layar monitor (angka HM terlihat jelas) dengan caption kode unit, contoh: <span className="font-mono text-foreground">Sdlg 230</span></p></div>
          </div>
        </div>
      </div>
    </div>
  );
}

const OB_STATUS = {
  sending: ["Mengirim", "border-sky-400/50 text-sky-300"],
  sent: ["Terkirim ke Meta", "border-primary/70 text-primary"],
  delivered: ["Diterima", "border-emerald-500/60 text-emerald-400"],
  read: ["Dibaca", "border-emerald-500/60 text-emerald-400"],
  failed: ["Gagal", "border-accent text-accent"],
  simulated: ["Simulasi", "border-border text-muted-foreground"],
};
const KIND = { reply: "Balasan konfirmasi", ack: "Tanda terima", help: "Panduan format", daily_summary: "Ringkasan harian", test: "Pesan uji", reminder: "Pengingat piutang", weekly_report: "Laporan mingguan" };
const OB_FILTERS = [["all", "Semua"], ["failed", "Gagal"], ["sent,delivered,read", "Terkirim"], ["sending", "Mengirim"], ["simulated", "Simulasi"]];

export function OutboxTab() {
  const [data, setData] = useState({ items: [], counts: {} });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState("");
  const load = async () => {
    setLoading(true);
    try { setData((await api.get("/wa/outbox", { params: { status: filter } })).data); } catch { toast.error("Gagal memuat pesan keluar"); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [filter]);
  const retry = async (r) => {
    if (r.uncertain && !window.confirm("Status pesan ini tidak pasti (mungkin sudah sampai). Pastikan di WhatsApp penerima bahwa pesan BELUM diterima. Kirim ulang?")) return;
    setBusy(r.id);
    try {
      const { data: d } = await api.post(`/wa/outbox/${r.id}/retry`);
      d.status === "sent" ? toast.success("Terkirim ulang") : toast.error(`Masih gagal: ${d.error || d.status}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal"); }
    finally { setBusy(""); }
  };
  const c = data.counts || {};
  return (
    <div data-testid="wa-outbox-tab" className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-5 border border-border bg-card">
        {[["Terkirim ke Meta", c.sent, "text-primary"], ["Diterima/Dibaca", (c.delivered || 0) + (c.read || 0), "text-emerald-400"], ["Gagal", c.failed, "text-accent"], ["Mengirim", c.sending, "text-sky-300"], ["Simulasi", c.simulated, "text-muted-foreground"]].map(([l, v, t], i) => (
          <div key={l} className={`p-3 ${i ? "border-l border-border" : ""}`}><p className={lbl}>{l}</p><p data-testid={`wa-outbox-count-${i}`} className={`font-display font-black text-2xl tracking-tighter ${t}`}>{v || 0}</p></div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap border border-border bg-card">
          {OB_FILTERS.map(([v, l]) => (
            <button key={v} data-testid={`wa-outbox-filter-${v.split(",")[0]}`} onClick={() => setFilter(v)}
              className={`px-3 py-2 text-xs font-mono uppercase tracking-wider transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${filter === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{l}</button>
          ))}
        </div>
        <Button data-testid="wa-outbox-refresh" variant="outline" onClick={load} className="ml-auto rounded-sm border-border hover:border-primary hover:text-primary"><ArrowClockwiseIcon size={16} weight="bold" className="mr-2" /> Muat Ulang</Button>
      </div>
      <p className="text-xs text-muted-foreground">Semua pesan keluar lewat antrean ini: tiap pesan punya kunci unik sehingga tidak terkirim ganda. Gagal sementara (429/5xx/koneksi) dicoba ulang otomatis tiap 30 menit; status tidak pasti tidak diulang otomatis.</p>
      <div className="border border-border bg-card overflow-x-auto">
        <table className="w-full text-sm" data-testid="wa-outbox-table">
          <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-3">Waktu (WITA)</th><th className="p-3">Jenis</th><th className="p-3">Tujuan</th><th className="p-3">Status</th><th className="p-3">Percobaan</th><th className="p-3">Keterangan</th><th className="p-3 text-right">Aksi</th></tr></thead>
          <tbody>
            {loading && <tr><td colSpan={7} className="p-3"><Skeleton className="h-5 w-full rounded-sm" /></td></tr>}
            {!loading && data.items.length === 0 && <tr><td colSpan={7} className="p-8 text-center text-xs font-mono text-muted-foreground" data-testid="wa-outbox-empty">// Belum ada pesan keluar</td></tr>}
            {!loading && data.items.map((r) => {
              const [l, t] = OB_STATUS[r.status] || [r.status, "border-border text-muted-foreground"];
              return (
                <tr key={r.id} className="border-t border-border hover:bg-secondary/60 align-top" data-testid={`wa-outbox-row-${r.id}`}>
                  <td className="p-3 font-mono text-[11px] whitespace-nowrap">{fmt(r.created_at)}</td>
                  <td className="p-3">{r.label || KIND[r.kind] || r.kind}</td>
                  <td className="p-3 font-mono text-primary">+{r.to}</td>
                  <td className="p-3"><span className={`inline-flex font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${t}`}>{l}</span>{r.uncertain && <span className="block font-mono text-[9px] text-primary mt-1">tidak pasti</span>}</td>
                  <td className="p-3 font-mono text-xs">{r.attempts || 0}{r.next_retry_at && r.status === "failed" ? <span className="block text-[10px] text-muted-foreground">ulang {fmt(r.next_retry_at)}</span> : null}</td>
                  <td className="p-3 text-xs text-muted-foreground max-w-sm break-words">{r.error || (r.delivery?.read_at ? `Dibaca ${fmt(r.delivery.read_at)}` : r.delivery?.delivered_at ? `Diterima ${fmt(r.delivery.delivered_at)}` : "")}</td>
                  <td className="p-3 text-right">{r.status === "failed" && <Button size="sm" data-testid={`wa-outbox-retry-${r.id}`} disabled={busy === r.id} onClick={() => retry(r)} variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary">{busy === r.id ? <CircleNotchIcon size={12} className="animate-spin" /> : "Kirim Ulang"}</Button>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
