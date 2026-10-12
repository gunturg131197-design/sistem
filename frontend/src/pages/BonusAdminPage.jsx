import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { PageHeader, CurrencyInput, formatIDR } from "@/components/common";
import { exportToExcelMultiSheet, exportToPDF } from "@/lib/exporters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import {
  TrophyIcon, GearSixIcon, FilePdfIcon, FileXlsIcon, CaretRightIcon, CaretDownIcon, CheckCircleIcon, ClockIcon,
  WarningIcon, ArrowClockwiseIcon, CoinsIcon, HourglassMediumIcon, SealCheckIcon, XCircleIcon, ClockCounterClockwiseIcon,
  UserCircleIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const fmtJam = (v) => Number(v || 0).toLocaleString("id-ID", { maximumFractionDigits: 2 });
const today = () => new Date().toISOString().slice(0, 10);
const fmtDate = (d) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }) : "—");

export default function BonusAdminPage() {
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState("all");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [filter, setFilter] = useState("semua");
  const [admins, setAdmins] = useState([]);
  const [cfgOpen, setCfgOpen] = useState(false);
  const [cfg, setCfg] = useState(null);
  const [savingCfg, setSavingCfg] = useState(false);
  const [payItem, setPayItem] = useState(null); // {row, item}
  const [payForm, setPayForm] = useState({ tanggal: today(), admin: "" });
  const [paying, setPaying] = useState(false);
  const [unpayItem, setUnpayItem] = useState(null);
  const [histOpen, setHistOpen] = useState(false);
  const [hist, setHist] = useState([]);
  const [busy, setBusy] = useState("");

  const load = async () => {
    setLoading(true); setError(false);
    try {
      const { data: d } = await api.get("/bonus-admin", { params: year === "all" ? {} : { year } });
      setData(d);
    } catch { setError(true); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [year]);
  useEffect(() => {
    api.get("/users").then(({ data: u }) => setAdmins((u || []).filter((x) => x.role === "admin").map((x) => x.name).filter(Boolean))).catch(() => {});
  }, []);

  const s = data?.settings;
  const step = s?.jam_per_bonus || 300;
  const rows = useMemo(() => {
    const all = data?.rows || [];
    if (filter === "belum") return all.filter((r) => r.bonus_unpaid > 0);
    if (filter === "dekat") return all.filter((r) => r.kurang_jam > 0 && r.kurang_jam <= step * 0.1);
    return all;
  }, [data, filter, step]);
  const nearCount = (data?.rows || []).filter((r) => r.kurang_jam > 0 && r.kurang_jam <= step * 0.1).length;
  const unpaidCount = (data?.rows || []).filter((r) => r.bonus_unpaid > 0).length;

  const openCfg = () => {
    setCfg({ ...BONUS_FORM(s), unit_admins: { ...(s?.unit_admins || {}) } });
    setCfgOpen(true);
  };
  const saveCfg = async () => {
    const jam = Number(cfg.jam_per_bonus);
    if (!jam || jam < 1) { toast.error("Kelipatan jam minimal 1"); return; }
    setSavingCfg(true);
    try {
      await api.put("/bonus-admin/settings", { ...cfg, jam_per_bonus: jam, nominal: Number(cfg.nominal || 0) });
      toast.success("Pengaturan bonus disimpan");
      setCfgOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan pengaturan"); }
    finally { setSavingCfg(false); }
  };

  const openPay = (row, item) => {
    setPayItem({ row, item });
    setPayForm({ tanggal: today(), admin: item.admin || row.admin || s?.default_admin || "" });
  };
  const doPay = async () => {
    if (!payForm.admin.trim()) { toast.error("Isi nama admin penerima bonus"); return; }
    setPaying(true);
    try {
      const { data: r } = await api.post("/bonus-admin/pay", { unit_id: payItem.row.unit_id, milestone: payItem.item.milestone, tanggal: payForm.tanggal, admin: payForm.admin });
      toast.success(`Bonus ${formatIDR(r.nominal)} untuk ${r.admin} dibayar · ${r.no_bukti} tercatat di Kas Keluar`);
      setPayItem(null); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mencatat pembayaran"); }
    finally { setPaying(false); }
  };
  const doUnpay = async () => {
    setPaying(true);
    try {
      await api.delete(`/bonus-admin/pay/${unpayItem.item.bonus_id}`);
      toast.success(`Pembayaran dibatalkan · ${unpayItem.item.no_bukti} dihapus dari Kas Keluar`);
      setUnpayItem(null); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal membatalkan"); }
    finally { setPaying(false); }
  };

  const openHist = async () => {
    setHistOpen(true);
    try { const { data: h } = await api.get("/bonus-admin/history"); setHist(h); } catch { setHist([]); }
  };

  const periodeLabel = year === "all" ? "Semua Periode" : `Tahun ${year}`;
  const doExport = async (fmt) => {
    const all = data?.rows || [];
    if (!all.length) { toast.error("Belum ada data untuk diunduh"); return; }
    setBusy(fmt);
    try {
      const y = year === "all" ? thisYear : Number(year);
      const { data: n } = await api.post("/reports/number", { month: y === thisYear ? new Date().getMonth() + 1 : 12, year: y, jenis: "semua", unit_label: "Rekap Bonus Admin", periode_label: periodeLabel });
      const fname = `Rekap-Bonus-Admin_${year === "all" ? "Semua" : year}`;
      const detail = all.flatMap((r) => r.items.map((i) => [r.unit, i.milestone, fmtJam(i.jam_target), fmtDate(i.tanggal_tercapai), i.admin || "—", formatIDR(i.nominal), i.status === "dibayar" ? `Dibayar ${fmtDate(i.paid_at)}` : "Belum dibayar", i.no_bukti || "—"]));
      if (fmt === "pdf") {
        const summary = all.map((r) => [r.unit, r.pengurus || "—", r.admin || "—", fmtJam(r.total_jam), r.jumlah_bonus, formatIDR(r.bonus_earned), formatIDR(r.bonus_paid), formatIDR(r.bonus_unpaid), `${fmtJam(r.kurang_jam)} jam`]);
        summary.push(["TOTAL", "", "", fmtJam(data.total.jam), data.total.bonus, formatIDR(data.total.earned), formatIDR(data.total.paid), formatIDR(data.total.unpaid), ""]);
        exportToPDF({
          title: `REKAP BONUS ADMIN · ${fmtJam(step)} JAM = ${formatIDR(s?.nominal)}`,
          columns: ["Unit", "Pengurus", "Admin", "Total Jam", "Bonus", "Nominal", "Dibayar", "Belum", "Ke Bonus Brkt"],
          rows: detail.length ? [...summary, ["", "", "", "", "", "", "", "", ""], ["RINCIAN", "Ke-", "Target Jam", "Tercapai", "Admin", "Nominal", "Status", "No. Bukti", ""], ...detail.map((d) => [...d, ""])] : summary,
          filename: fname, nomor: n.nomor, periodeLabel,
        });
      } else {
        exportToExcelMultiSheet([
          { name: "Rekap per Unit", rows: all.map((r) => ({ Unit: r.unit, Pengurus: r.pengurus, Admin: r.admin, "Total Jam": r.total_jam, "Jumlah Bonus": r.jumlah_bonus, "Nominal Bonus": r.bonus_earned, Dibayar: r.bonus_paid, "Belum Dibayar": r.bonus_unpaid, "Sisa Jam": r.sisa_jam, "Kurang ke Bonus Berikutnya": r.kurang_jam })) },
          { name: "Rincian Bonus", rows: all.flatMap((r) => r.items.map((i) => ({ Unit: r.unit, "Bonus ke-": i.milestone, "Target Jam": i.jam_target, "Tanggal Tercapai": i.tanggal_tercapai, Admin: i.admin, Nominal: i.nominal, Status: i.status === "dibayar" ? "Dibayar" : "Belum", "Tanggal Bayar": i.paid_at || "", "No. Bukti": i.no_bukti || "" }))) },
        ], fname);
      }
      toast.success(`${fmt === "pdf" ? "PDF" : "Excel"} diunduh · ${n.nomor}`);
    } catch (e) { console.error(e); toast.error("Gagal membuat file rekap"); }
    finally { setBusy(""); }
  };

  return (
    <div data-testid="bonus-admin-page">
      <PageHeader
        overline="// Keuangan / Bonus"
        title="Bonus Admin"
        description={`Setiap unit yang mencapai kelipatan ${fmtJam(step)} jam kerja (HM dari Ops Report) memberi bonus ${formatIDR(s?.nominal ?? 500000)} kepada admin unit. Sisa jam dibawa ke bonus berikutnya.`}
        actions={
          <>
            <Select value={String(year)} onValueChange={setYear}>
              <SelectTrigger data-testid="bonus-year-select" className="rounded-sm w-36 bg-card"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Periode</SelectItem>
                {[0, 1, 2, 3, 4].map((d) => <SelectItem key={d} value={String(thisYear - d)}>{thisYear - d}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button data-testid="bonus-history-button" variant="outline" onClick={openHist} className="rounded-sm border-border hover:border-primary hover:text-primary">
              <ClockCounterClockwiseIcon size={16} weight="bold" className="mr-2" /> Riwayat
            </Button>
            <Button data-testid="bonus-settings-button" variant="outline" onClick={openCfg} disabled={!s} className="rounded-sm border-border hover:border-primary hover:text-primary">
              <GearSixIcon size={16} weight="bold" className="mr-2" /> Pengaturan
            </Button>
            <Button data-testid="bonus-export-excel" variant="outline" disabled={!!busy || loading} onClick={() => doExport("xlsx")} className="rounded-sm border-border hover:border-primary hover:text-primary">
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> {busy === "xlsx" ? "Membuat…" : "Excel"}
            </Button>
            <Button data-testid="bonus-export-pdf" disabled={!!busy || loading} onClick={() => doExport("pdf")} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground font-display tracking-tight">
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> {busy === "pdf" ? "Membuat…" : "PDF Berkop"}
            </Button>
          </>
        }
      />

      {/* Rule banner */}
      <div className="border border-primary/40 bg-card mb-6 flex flex-col md:flex-row md:items-center gap-4 p-4" data-testid="bonus-rule-banner">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 bg-primary text-primary-foreground flex items-center justify-center shrink-0"><TrophyIcon size={26} weight="fill" /></div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Aturan aktif</p>
            <p className="font-display font-black text-xl tracking-tight" data-testid="bonus-rule-text">
              Tiap <span className="text-primary">{fmtJam(step)} jam</span> = <span className="text-primary">{formatIDR(s?.nominal ?? 500000)}</span>
            </p>
          </div>
        </div>
        <div className="md:ml-auto flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-wider">
          <span className={`px-2 py-1 border ${s?.enabled === false ? "border-accent text-accent" : "border-emerald-500/60 text-emerald-400"}`} data-testid="bonus-status-badge">{s?.enabled === false ? "Nonaktif" : "Aktif"}</span>
          <span className="px-2 py-1 border border-border text-muted-foreground">Admin default: <b className="text-foreground normal-case">{s?.default_admin || "belum diisi"}</b></span>
          <span className="px-2 py-1 border border-border text-muted-foreground">Hitung sejak: <b className="text-foreground">{s?.start_date ? fmtDate(s.start_date) : "awal data"}</b></span>
        </div>
      </div>

      {s && !s.default_admin && (data?.rows || []).some((r) => !r.admin) && (
        <div data-testid="bonus-missing-admin" className="flex items-start gap-2 border border-primary/50 bg-primary/10 px-4 py-3 mb-6 text-xs">
          <WarningIcon size={16} weight="bold" className="text-primary shrink-0 mt-0.5" />
          <p><b className="text-primary">Admin penerima belum diatur.</b> Buka <b>Pengaturan</b> untuk mengisi admin default atau admin per unit, agar nama penerima otomatis terisi saat bonus dibayar.</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-4 border border-border bg-card mb-6">
        {[
          ["Bonus Tercapai", data?.total?.bonus, TrophyIcon, "text-primary", "bonus-stat-count", "x", `${data?.total?.unit_bonus ?? 0} unit`],
          ["Total Nominal Bonus", data?.total?.earned, CoinsIcon, "text-primary", "bonus-stat-earned", "rp"],
          ["Sudah Dibayar", data?.total?.paid, SealCheckIcon, "text-emerald-400", "bonus-stat-paid", "rp"],
          ["Belum Dibayar", data?.total?.unpaid, HourglassMediumIcon, (data?.total?.unpaid || 0) > 0 ? "text-accent" : "text-muted-foreground", "bonus-stat-unpaid", "rp", `${unpaidCount} unit`],
        ].map(([l, v, Icon, c, tid, kind, sub], i) => (
          <div key={l} className={`p-5 relative ${i < 3 ? "xl:border-r" : ""} ${i % 2 === 0 ? "border-r" : ""} ${i < 2 ? "border-b xl:border-b-0" : ""} border-border`}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5"><Icon size={12} weight="bold" /> {l}</p>
            {loading ? <Skeleton className="h-8 w-32 mt-2 rounded-sm" /> : (
              <p data-testid={tid} className={`font-display font-black text-2xl lg:text-3xl tracking-tighter mt-2 ${c}`}>
                {kind === "x" ? <>{v || 0}<span className="text-xs font-mono font-normal text-muted-foreground ml-1.5">BONUS</span></> : formatIDR(v)}
              </p>
            )}
            {sub && !loading && <p className="font-mono text-[10px] text-muted-foreground mt-1">{sub}</p>}
            <div className="absolute bottom-0 left-0 h-0.5 w-8 bg-primary" />
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex flex-wrap border border-border bg-card w-fit" role="tablist">
          {[["semua", `Semua Unit (${data?.rows?.length || 0})`], ["belum", `Belum Dibayar (${unpaidCount})`], ["dekat", `Hampir Tercapai (${nearCount})`]].map(([k, l]) => (
            <button key={k} role="tab" aria-selected={filter === k} data-testid={`bonus-filter-${k}`} onClick={() => setFilter(k)}
              className={`px-3 py-2 text-xs font-mono uppercase tracking-wider transition-colors duration-150 ${filter === k ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
              {l}
            </button>
          ))}
        </div>
        <p className="font-mono text-[10px] text-muted-foreground">Hampir tercapai = kurang ≤ {fmtJam(step * 0.1)} jam ke bonus berikutnya</p>
      </div>

      {/* Table */}
      <div className="border border-border bg-card overflow-x-auto" data-testid="bonus-table">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3 min-w-[220px]">Unit</th>
              <th className="p-3">Admin</th>
              <th className="p-3 text-right">Total Jam</th>
              <th className="p-3 min-w-[220px]">Progres ke Bonus Berikutnya</th>
              <th className="p-3 text-right">Bonus</th>
              <th className="p-3 text-right">Dibayar</th>
              <th className="p-3 text-right">Belum Dibayar</th>
            </tr>
          </thead>
          <tbody>
            {loading && [0, 1, 2].map((i) => <tr key={i} className="border-t border-border"><td colSpan={7} className="p-3"><Skeleton className="h-6 w-full rounded-sm" /></td></tr>)}
            {!loading && error && (
              <tr><td colSpan={7} className="p-8 text-center">
                <p className="text-xs font-mono text-muted-foreground mb-3">// Gagal memuat rekap bonus</p>
                <Button data-testid="bonus-retry" size="sm" variant="outline" onClick={load} className="rounded-sm"><ArrowClockwiseIcon size={14} weight="bold" className="mr-1.5" /> Coba lagi</Button>
              </td></tr>
            )}
            {!loading && !error && rows.length === 0 && (
              <tr><td colSpan={7} className="p-10 text-center text-xs font-mono text-muted-foreground" data-testid="bonus-empty">
                {(data?.rows || []).length === 0 ? "// Belum ada unit terdaftar. Tambahkan unit di Unit Registry & isi Ops Report." : "// Tidak ada unit pada filter ini"}
              </td></tr>
            )}
            {!loading && !error && rows.map((r) => {
              const open = !!expanded[r.unit_id];
              const near = r.kurang_jam > 0 && r.kurang_jam <= step * 0.1;
              return (
                <React.Fragment key={r.unit_id}>
                  <tr className="border-t border-border hover:bg-secondary/60 cursor-pointer" data-testid={`bonus-row-${r.unit_id}`} onClick={() => setExpanded({ ...expanded, [r.unit_id]: !open })}>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {open ? <CaretDownIcon size={12} weight="bold" className="text-primary" /> : <CaretRightIcon size={12} weight="bold" className="text-muted-foreground" />}
                        <div>
                          <p className="font-medium">{r.unit_name} <span className="font-mono text-primary">{r.nomor_lambung}</span></p>
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{r.pengurus || "tanpa pengurus"} · {r.jumlah_laporan} laporan</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-xs">
                      {r.admin ? <span className="inline-flex items-center gap-1"><UserCircleIcon size={14} weight="bold" className="text-muted-foreground" />{r.admin}{r.admin_khusus && <span className="font-mono text-[9px] text-primary ml-1">KHUSUS</span>}</span> : <span className="text-muted-foreground font-mono">—</span>}
                    </td>
                    <td className="p-3 text-right font-mono whitespace-nowrap" data-testid={`bonus-jam-${r.unit_id}`}>{fmtJam(r.total_jam)}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 flex-1 bg-muted overflow-hidden" title={`${fmtJam(r.sisa_jam)} / ${fmtJam(step)} jam`}>
                          <div className={`h-full ${near ? "bg-accent" : "bg-primary"} transition-all duration-500`} style={{ width: `${Math.min(100, r.progress)}%` }} />
                        </div>
                        <span className="font-mono text-[10px] text-muted-foreground w-10 text-right">{Math.round(r.progress)}%</span>
                      </div>
                      <p className={`font-mono text-[10px] mt-1 ${near ? "text-accent" : "text-muted-foreground"}`} data-testid={`bonus-kurang-${r.unit_id}`}>
                        {fmtJam(r.sisa_jam)} / {fmtJam(step)} jam · kurang <b>{fmtJam(r.kurang_jam)} jam</b> ke bonus ke-{r.jumlah_bonus_total + 1}
                      </p>
                    </td>
                    <td className="p-3 text-right font-display font-black text-primary whitespace-nowrap" data-testid={`bonus-count-${r.unit_id}`}>{r.jumlah_bonus}×</td>
                    <td className="p-3 text-right font-mono text-xs whitespace-nowrap text-emerald-400">{r.bonus_paid ? formatIDR(r.bonus_paid) : <span className="text-muted-foreground">—</span>}</td>
                    <td className="p-3 text-right font-mono text-xs whitespace-nowrap" data-testid={`bonus-unpaid-${r.unit_id}`}>{r.bonus_unpaid ? <span className="text-accent font-semibold">{formatIDR(r.bonus_unpaid)}</span> : <span className="text-muted-foreground">—</span>}</td>
                  </tr>
                  {open && (
                    <tr className="bg-background/60 border-t border-border/50">
                      <td colSpan={7} className="p-0">
                        {r.items.length === 0 ? (
                          <p className="py-4 pl-10 font-mono text-[11px] text-muted-foreground">// Belum ada kelipatan {fmtJam(step)} jam yang tercapai{year !== "all" ? ` pada ${year}` : ""}.</p>
                        ) : (
                          <table className="w-full text-xs" data-testid={`bonus-items-${r.unit_id}`}>
                            <thead>
                              <tr className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground text-left">
                                <th className="py-2 pl-10 pr-3">Bonus ke-</th><th className="py-2 px-3">Target Jam</th><th className="py-2 px-3">Tercapai</th>
                                <th className="py-2 px-3">Admin</th><th className="py-2 px-3 text-right">Nominal</th><th className="py-2 px-3">Status</th><th className="py-2 px-3 text-right">Aksi</th>
                              </tr>
                            </thead>
                            <tbody>
                              {r.items.map((i) => (
                                <tr key={i.milestone} className="border-t border-border/40" data-testid={`bonus-item-${r.unit_id}-${i.milestone}`}>
                                  <td className="py-2 pl-10 pr-3 font-display font-black text-primary">#{i.milestone}</td>
                                  <td className="py-2 px-3 font-mono">{fmtJam(i.jam_target)} jam</td>
                                  <td className="py-2 px-3 font-mono">{fmtDate(i.tanggal_tercapai)}</td>
                                  <td className="py-2 px-3">{i.admin || <span className="text-muted-foreground">—</span>}</td>
                                  <td className="py-2 px-3 text-right font-mono">{formatIDR(i.nominal)}</td>
                                  <td className="py-2 px-3">
                                    {i.status === "dibayar" ? (
                                      <span className="inline-flex items-center gap-1 text-emerald-400 font-mono text-[10px] uppercase"><CheckCircleIcon size={13} weight="fill" /> Dibayar {fmtDate(i.paid_at)} · {i.no_bukti}</span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-primary font-mono text-[10px] uppercase"><ClockIcon size={13} weight="bold" /> Belum dibayar</span>
                                    )}
                                    {i.jam_berkurang && <span className="ml-2 inline-flex items-center gap-1 text-accent font-mono text-[10px]" title="Jam unit berkurang setelah bonus dibayar"><WarningIcon size={12} weight="bold" /> Jam berkurang</span>}
                                  </td>
                                  <td className="py-2 px-3 text-right">
                                    {i.status === "dibayar" ? (
                                      <Button size="sm" variant="outline" data-testid={`bonus-unpay-${r.unit_id}-${i.milestone}`} onClick={(e) => { e.stopPropagation(); setUnpayItem({ row: r, item: i }); }} className="rounded-sm h-7 text-[11px] border-border hover:border-accent hover:text-accent">
                                        <XCircleIcon size={13} weight="bold" className="mr-1" /> Batalkan
                                      </Button>
                                    ) : (
                                      <Button size="sm" data-testid={`bonus-pay-${r.unit_id}-${i.milestone}`} disabled={s?.enabled === false} onClick={(e) => { e.stopPropagation(); openPay(r, i); }} className="rounded-sm h-7 text-[11px] bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">
                                        <CoinsIcon size={13} weight="bold" className="mr-1" /> Tandai Dibayar
                                      </Button>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
          {!loading && !error && (data?.rows || []).length > 0 && (
            <tfoot>
              <tr className="border-t-2 border-primary bg-muted">
                <td className="p-3 font-mono text-[10px] uppercase tracking-[0.2em] text-primary" colSpan={2}>Total · {data.rows.length} unit</td>
                <td className="p-3 text-right font-mono font-semibold">{fmtJam(data.total.jam)}</td>
                <td className="p-3" />
                <td className="p-3 text-right font-display font-black text-primary" data-testid="bonus-total-count">{data.total.bonus}×</td>
                <td className="p-3 text-right font-mono text-xs font-semibold text-emerald-400">{formatIDR(data.total.paid)}</td>
                <td className="p-3 text-right font-mono text-xs font-semibold text-accent">{formatIDR(data.total.unpaid)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      <p className="font-mono text-[10px] text-muted-foreground mt-2">Klik baris unit untuk melihat rincian tiap kelipatan. "Tandai Dibayar" otomatis membuat bukti Kas Keluar (KK-TTP); "Batalkan" menghapusnya. Semua tercatat di riwayat.</p>

      {(data?.legacy_paid || []).length > 0 && (
        <div className="mt-8" data-testid="bonus-legacy">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary mb-2">// Bonus dibayar dengan aturan lama</p>
          <div className="border border-border bg-card overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-muted"><tr className="text-left font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-2">Unit</th><th className="p-2">Aturan</th><th className="p-2">Ke-</th><th className="p-2">Admin</th><th className="p-2 text-right">Nominal</th><th className="p-2">Dibayar</th><th className="p-2 text-right">Aksi</th></tr></thead>
              <tbody>
                {data.legacy_paid.map((p) => (
                  <tr key={p.id} className="border-t border-border">
                    <td className="p-2">{p.unit}</td><td className="p-2 font-mono">{fmtJam(p.jam_per_bonus)} jam</td><td className="p-2 font-mono">#{p.milestone} ({fmtJam(p.jam_target)} jam)</td>
                    <td className="p-2">{p.admin}</td><td className="p-2 text-right font-mono">{formatIDR(p.nominal)}</td><td className="p-2 font-mono">{fmtDate(p.paid_at)} · {p.no_bukti}</td>
                    <td className="p-2 text-right"><Button size="sm" variant="outline" onClick={() => setUnpayItem({ row: { unit: p.unit }, item: { ...p, bonus_id: p.id } })} className="rounded-sm h-7 text-[11px] border-border hover:border-accent hover:text-accent">Batalkan</Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Settings dialog */}
      <Dialog open={cfgOpen} onOpenChange={setCfgOpen}>
        <DialogContent className="rounded-sm border-border bg-card max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="bonus-settings-dialog">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl flex items-center gap-2"><GearSixIcon size={22} weight="bold" className="text-primary" /> Pengaturan Bonus Admin</DialogTitle>
            <DialogDescription className="text-xs">Perubahan aturan tidak mengubah bonus yang sudah dibayar.</DialogDescription>
          </DialogHeader>
          {cfg && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border border-border p-3">
                <div><p className="text-sm font-medium">Fitur bonus aktif</p><p className="font-mono text-[10px] text-muted-foreground">Bila nonaktif, bonus tetap dihitung tetapi tidak bisa ditandai dibayar.</p></div>
                <Switch data-testid="bonus-cfg-enabled" checked={!!cfg.enabled} onCheckedChange={(v) => setCfg({ ...cfg, enabled: v })} />
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Kelipatan Jam</Label>
                  <Input data-testid="bonus-cfg-jam" type="number" min={1} className="rounded-sm mt-1.5 font-mono" value={cfg.jam_per_bonus} onChange={(e) => setCfg({ ...cfg, jam_per_bonus: e.target.value })} />
                </div>
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Nominal Bonus</Label>
                  <CurrencyInput data-testid="bonus-cfg-nominal" className="rounded-sm mt-1.5" value={cfg.nominal} onChange={(v) => setCfg({ ...cfg, nominal: v })} />
                </div>
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Admin Default (Penerima)</Label>
                  <Input data-testid="bonus-cfg-default-admin" list="bonus-admin-names" className="rounded-sm mt-1.5" placeholder="Nama admin" value={cfg.default_admin} onChange={(e) => setCfg({ ...cfg, default_admin: e.target.value })} />
                </div>
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Hitung Jam Sejak (Opsional)</Label>
                  <Input data-testid="bonus-cfg-start" type="date" className="rounded-sm mt-1.5 font-mono" value={cfg.start_date} onChange={(e) => setCfg({ ...cfg, start_date: e.target.value })} />
                </div>
              </div>
              <datalist id="bonus-admin-names">{admins.map((n) => <option key={n} value={n} />)}</datalist>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">Admin per Unit (kosongkan = admin default)</p>
                <div className="border border-border divide-y divide-border max-h-64 overflow-y-auto">
                  {(data?.rows || []).length === 0 && <p className="p-3 text-xs font-mono text-muted-foreground">// Belum ada unit</p>}
                  {(data?.rows || []).map((r) => (
                    <div key={r.unit_id} className="flex items-center gap-3 p-2">
                      <p className="text-xs flex-1 min-w-0 truncate">{r.unit_name} <span className="font-mono text-primary">{r.nomor_lambung}</span></p>
                      <Input data-testid={`bonus-cfg-unit-admin-${r.unit_id}`} list="bonus-admin-names" className="rounded-sm h-8 w-52 text-xs" placeholder={cfg.default_admin || "Admin default"}
                        value={cfg.unit_admins[r.unit_id] || ""} onChange={(e) => setCfg({ ...cfg, unit_admins: { ...cfg.unit_admins, [r.unit_id]: e.target.value } })} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button data-testid="bonus-cfg-save" disabled={savingCfg} onClick={saveCfg} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">{savingCfg ? "Menyimpan…" : "Simpan Pengaturan"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Pay dialog */}
      <Dialog open={!!payItem} onOpenChange={(v) => { if (!v) setPayItem(null); }}>
        <DialogContent className="rounded-sm border-border bg-card" data-testid="bonus-pay-dialog">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl">Bayar Bonus Admin</DialogTitle>
            <DialogDescription className="text-xs">Pembayaran akan dicatat sebagai Kas Keluar (KK-TTP) secara otomatis.</DialogDescription>
          </DialogHeader>
          {payItem && (
            <div className="space-y-4">
              <div className="border border-primary/40 bg-primary/5 p-4 grid grid-cols-2 gap-3 text-xs">
                <div><p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Unit</p><p className="font-medium">{payItem.row.unit}</p></div>
                <div><p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Kelipatan</p><p className="font-mono">#{payItem.item.milestone} · {fmtJam(payItem.item.jam_target)} jam</p></div>
                <div><p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Tercapai</p><p className="font-mono">{fmtDate(payItem.item.tanggal_tercapai)}</p></div>
                <div><p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Nominal</p><p className="font-display font-black text-xl text-primary" data-testid="bonus-pay-nominal">{formatIDR(payItem.item.nominal)}</p></div>
              </div>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Admin Penerima</Label>
                <Input data-testid="bonus-pay-admin" list="bonus-admin-names" className="rounded-sm mt-1.5" placeholder="Nama admin" value={payForm.admin} onChange={(e) => setPayForm({ ...payForm, admin: e.target.value })} />
                <datalist id="bonus-admin-names">{admins.map((n) => <option key={n} value={n} />)}</datalist>
              </div>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Tanggal Bayar</Label>
                <Input data-testid="bonus-pay-date" type="date" className="rounded-sm mt-1.5 font-mono" value={payForm.tanggal} onChange={(e) => setPayForm({ ...payForm, tanggal: e.target.value })} />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayItem(null)} className="rounded-sm">Batal</Button>
            <Button data-testid="bonus-pay-confirm" disabled={paying} onClick={doPay} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">
              <CoinsIcon size={16} weight="bold" className="mr-1.5" /> {paying ? "Menyimpan…" : "Konfirmasi Bayar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unpay confirm */}
      <Dialog open={!!unpayItem} onOpenChange={(v) => { if (!v) setUnpayItem(null); }}>
        <DialogContent className="rounded-sm border-border bg-card" data-testid="bonus-unpay-dialog">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl">Batalkan Pembayaran?</DialogTitle>
            <DialogDescription className="text-xs">
              Bonus #{unpayItem?.item?.milestone} {unpayItem?.row?.unit} ({formatIDR(unpayItem?.item?.nominal)}) akan kembali berstatus belum dibayar dan bukti <b>{unpayItem?.item?.no_bukti}</b> dihapus dari Kas Keluar.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUnpayItem(null)} className="rounded-sm">Tidak</Button>
            <Button data-testid="bonus-unpay-confirm" disabled={paying} onClick={doUnpay} className="rounded-sm bg-accent text-white hover:bg-accent/90">{paying ? "Memproses…" : "Ya, Batalkan"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History */}
      <Dialog open={histOpen} onOpenChange={setHistOpen}>
        <DialogContent className="rounded-sm border-border bg-card max-w-2xl" data-testid="bonus-history-dialog">
          <DialogHeader><DialogTitle className="font-display font-black tracking-tighter text-2xl">Riwayat Bonus Admin</DialogTitle></DialogHeader>
          <div className="border border-border max-h-[60vh] overflow-y-auto divide-y divide-border">
            {hist.length === 0 && <p className="p-4 text-xs font-mono text-muted-foreground">// Belum ada riwayat</p>}
            {hist.map((h) => (
              <div key={h.id} className="p-3 text-xs flex gap-3">
                <span className={`font-mono text-[9px] uppercase px-1.5 py-0.5 h-fit border ${h.action === "bonus_paid" ? "border-emerald-500/60 text-emerald-400" : h.action === "bonus_unpaid" ? "border-accent text-accent" : "border-border text-muted-foreground"}`}>
                  {h.action === "bonus_paid" ? "Dibayar" : h.action === "bonus_unpaid" ? "Dibatalkan" : "Pengaturan"}
                </span>
                <div className="flex-1"><p>{h.detail}</p><p className="font-mono text-[10px] text-muted-foreground mt-0.5">{new Date(h.at).toLocaleString("id-ID", { timeZone: "Asia/Makassar" })} WITA · {h.actor}</p></div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function BONUS_FORM(s) {
  return {
    enabled: s?.enabled ?? true,
    jam_per_bonus: s?.jam_per_bonus ?? 300,
    nominal: s?.nominal ?? 500000,
    default_admin: s?.default_admin || "",
    start_date: s?.start_date || "",
  };
}
