import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, formatIDR, CurrencyInput } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import {
  FileXlsIcon, FilePdfIcon, FileDocIcon, TruckIcon, ClockIcon, WrenchIcon, MoneyIcon, FunnelIcon, XIcon, ArchiveIcon,
  DownloadSimpleIcon, CaretDownIcon, NotePencilIcon, GasPumpIcon, CalendarCheckIcon, TimerIcon, MapPinIcon, ShieldCheckIcon, WarningIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcelMultiSheet, exportToPDF } from "@/lib/exporters";
import { exportHourMeterPDF, exportHourMeterExcel, exportHourMeterDocx, KONDISI_ITEMS } from "@/lib/hourMeter";

const BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const ITEM_CLS = "cursor-pointer focus:bg-secondary focus:text-foreground";

function Stat({ icon: Icon, label, children, className = "" }) {
  return (
    <div className={`p-4 border-r border-b border-border ${className}`}>
      <div className="flex items-center gap-1.5 text-muted-foreground"><Icon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">{label}</p></div>
      <div className="font-display font-black text-lg tracking-tighter mt-1.5">{children}</div>
    </div>
  );
}

export default function ReportsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [periode, setPeriode] = useState(""); // "" = semua, atau "YYYY-MM"
  const [archive, setArchive] = useState([]);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const [extrasFor, setExtrasFor] = useState(null);
  const [extras, setExtras] = useState({ pengembalian_jam: "", lain_lain: "", keterangan_tambahan: "" });

  const loadArchive = async () => {
    try { const { data } = await api.get("/reports/archive"); setArchive(data); }
    catch { toast.error("Gagal memuat arsip nomor"); }
  };

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/reports/units", { params: periode ? { periode } : {} });
      setReports(data);
    } catch { toast.error("Gagal memuat laporan"); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [periode]);

  const periodeLabel = () => {
    if (!periode) return "Semua Periode";
    const [y, m] = periode.split("-");
    return `${BULAN_ID[Number(m)]} ${y}`;
  };

  const issueNomor = async (ctx = {}) => {
    let month, year;
    if (periode) { const [y, m] = periode.split("-"); month = Number(m); year = Number(y); }
    else { const d = new Date(); month = d.getMonth() + 1; year = d.getFullYear(); }
    const { data } = await api.post("/reports/number", {
      month, year, jenis: ctx.jenis || "semua", unit_label: ctx.unit_label || "", periode_label: periodeLabel(),
    });
    loadArchive();
    return data.nomor;
  };

  const slug = (s) => String(s).replace(/[^\w-]+/g, "_");
  const periodSlug = periode || "semua-periode";

  // ---- Hour Meter (format resmi) ----
  const runHourMeter = async (list, fmt, ctx) => {
    if (!list.length) { toast.error("Tidak ada unit untuk diunduh"); return; }
    const key = `${ctx.key}-${fmt}`;
    setBusy(key);
    try {
      const nomor = await issueNomor(ctx);
      const meta = { nomor, periodeLabel: periodeLabel() };
      const fname = `HourMeter_${ctx.fileTag}_${periodSlug}`;
      if (fmt === "pdf") exportHourMeterPDF(list, meta, fname);
      else if (fmt === "xlsx") await exportHourMeterExcel(list, meta, fname);
      else await exportHourMeterDocx(list, meta, fname);
      toast.success(`${fmt === "pdf" ? "PDF" : fmt === "xlsx" ? "Excel" : "Word"} diunduh · ${nomor}`);
    } catch (e) {
      console.error(e);
      toast.error("Gagal membuat laporan. Coba lagi.");
    } finally { setBusy(""); }
  };

  const unitHM = (r, fmt) => runHourMeter([r], fmt, { key: r.unit_id, jenis: "unit", unit_label: r.unit_label, fileTag: slug(`${r.unit_name}-${r.nomor_lambung}`) });
  const allHM = (fmt) => runHourMeter(reports, fmt, { key: "all", jenis: "semua", fileTag: "Semua-Unit" });

  // ---- Rekap ringkas semua unit ----
  const rekapPDF = async () => {
    try {
      const nomor = await issueNomor({ jenis: "semua" });
      exportToPDF({
        title: "Rekap Semua Unit", nomor, periodeLabel: periodeLabel(),
        columns: ["Unit", "No Lambung", "Proyek", "Hari", "Total HM", "Downtime", "Solar (L)", "Total Gaji", "Sparepart"],
        rows: reports.map(r => [r.unit_name, r.nomor_lambung, r.nama_proyek || "-", r.hari_operasional, r.total_hm, r.total_downtime, r.total_solar, formatIDR(r.total_gaji), formatIDR(r.total_sparepart)]),
        filename: `Rekap_Semua-Unit_${periodSlug}`,
      });
      toast.success(`Rekap PDF diunduh · ${nomor}`);
    } catch { toast.error("Gagal mengunduh rekap"); }
  };
  const rekapExcel = async () => {
    try {
      const nomor = await issueNomor({ jenis: "semua" });
      exportToExcelMultiSheet([
        { name: "Info", rows: [{ "Nomor Laporan": nomor, Periode: periodeLabel(), Digenerate: new Date().toLocaleString("id-ID") }] },
        { name: "Rekap Unit", rows: reports.map(r => ({
          Unit: r.unit_name, "Merek / Type": r.merek_type || "-", "Nomor Lambung": r.nomor_lambung, Serial: r.serial_number || "-",
          Proyek: r.nama_proyek || "-", Lokasi: r.lokasi_proyek || "-", Operator: (r.operators || []).join(", ") || "-",
          "Hari Operasional": r.hari_operasional, "Total Cars": r.total_cars, "HM Awal": r.hm_awal, "HM Akhir": r.hm_akhir, "Total HM": r.total_hm,
          "Downtime (Jam)": r.total_downtime, "Solar (Liter)": r.total_solar, "Total Gaji": r.total_gaji, "Total Sparepart": r.total_sparepart,
        })) },
      ], `Rekap_Semua-Unit_${periodSlug}`);
      toast.success(`Rekap Excel diunduh · ${nomor}`);
    } catch { toast.error("Gagal mengunduh rekap"); }
  };

  // ---- Extras (biaya lain & keterangan tambahan) ----
  const openExtras = (r) => {
    setExtrasFor(r);
    setExtras({ pengembalian_jam: r.pengembalian_jam || "", lain_lain: r.lain_lain || "", keterangan_tambahan: r.keterangan_tambahan || "" });
  };
  const saveExtras = async () => {
    try {
      await api.put("/reports/extras", {
        unit_id: extrasFor.unit_id, periode: periode || "",
        pengembalian_jam: Number(extras.pengembalian_jam || 0), lain_lain: Number(extras.lain_lain || 0),
        keterangan_tambahan: extras.keterangan_tambahan || "",
      });
      toast.success("Data laporan tersimpan");
      setExtrasFor(null); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
  };

  const FormatMenu = ({ onPick, testid, busyKey, label = "Hour Meter", primary }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button data-testid={testid} size="sm" disabled={busy.startsWith(busyKey)}
          className={primary
            ? "rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground font-display tracking-tight"
            : "rounded-sm bg-background border border-border text-foreground hover:border-primary hover:text-primary hover:bg-background"}>
          <DownloadSimpleIcon size={14} weight="bold" className="mr-1.5" />
          {busy.startsWith(busyKey) ? "Membuat…" : label}
          <CaretDownIcon size={12} weight="bold" className="ml-1.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="rounded-sm border-border bg-popover w-56">
        <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Form Hour Meter</DropdownMenuLabel>
        <DropdownMenuItem data-testid={`${testid}-pdf`} className={ITEM_CLS} onClick={() => onPick("pdf")}><FilePdfIcon size={16} weight="bold" className="text-accent" /> PDF (.pdf)</DropdownMenuItem>
        <DropdownMenuItem data-testid={`${testid}-excel`} className={ITEM_CLS} onClick={() => onPick("xlsx")}><FileXlsIcon size={16} weight="bold" className="text-emerald-400" /> Excel (.xlsx)</DropdownMenuItem>
        <DropdownMenuItem data-testid={`${testid}-word`} className={ITEM_CLS} onClick={() => onPick("docx")}><FileDocIcon size={16} weight="bold" className="text-sky-400" /> Word (.docx)</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  return (
    <div>
      <PageHeader
        overline="// Reports / 05"
        title="Laporan Hour Meter"
        description="Form Hour Meter Operator & Alat Berat per unit — data umum, identitas alat, rekap bulanan HM, sparepart, total biaya, dan kondisi alat. Unduh dalam PDF, Excel, atau Word berkop resmi dengan nomor laporan otomatis."
        actions={
          <>
            <Dialog open={archiveOpen} onOpenChange={(v) => { setArchiveOpen(v); if (v) loadArchive(); }}>
              <DialogTrigger asChild>
                <Button data-testid="open-archive" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary">
                  <ArchiveIcon size={16} weight="bold" className="mr-2" /> Arsip Nomor
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-sm border-border bg-card max-w-3xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="font-display font-black tracking-tighter text-2xl">Arsip Nomor Laporan</DialogTitle>
                </DialogHeader>
                <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground -mt-2">Semua nomor laporan yang pernah diterbitkan · {archive.length} nomor</p>
                <div className="border border-border overflow-x-auto mt-2" data-testid="archive-table">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                        <th className="p-2.5">Nomor</th><th className="p-2.5">Jenis</th><th className="p-2.5">Unit</th><th className="p-2.5">Periode</th><th className="p-2.5">Diterbitkan</th><th className="p-2.5">Oleh</th>
                      </tr>
                    </thead>
                    <tbody>
                      {archive.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-muted-foreground text-xs font-mono">// Belum ada nomor diterbitkan</td></tr>}
                      {archive.map((a) => (
                        <tr key={a.id} className="border-t border-border hover:bg-secondary/60">
                          <td className="p-2.5 font-mono text-primary font-semibold whitespace-nowrap">{a.nomor}</td>
                          <td className="p-2.5">
                            <span className={`font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${a.jenis === "unit" ? "border-primary/50 text-primary" : "border-border text-muted-foreground"}`}>
                              {a.jenis === "unit" ? "Per Unit" : "Semua"}
                            </span>
                          </td>
                          <td className="p-2.5 text-muted-foreground">{a.unit_label || "—"}</td>
                          <td className="p-2.5 font-mono text-xs">{a.periode_label || "—"}</td>
                          <td className="p-2.5 font-mono text-xs text-muted-foreground whitespace-nowrap">{a.created_at ? new Date(a.created_at).toLocaleString("id-ID") : "—"}</td>
                          <td className="p-2.5 text-xs">{a.issued_by || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </DialogContent>
            </Dialog>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button data-testid="export-all-menu" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary">
                  <FileXlsIcon size={16} weight="bold" className="mr-2" /> Rekap Ringkas <CaretDownIcon size={12} weight="bold" className="ml-1.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="rounded-sm border-border bg-popover w-56">
                <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Tabel Rekap Semua Unit</DropdownMenuLabel>
                <DropdownMenuItem data-testid="export-pdf-all" className={ITEM_CLS} onClick={rekapPDF}><FilePdfIcon size={16} weight="bold" className="text-accent" /> Rekap PDF</DropdownMenuItem>
                <DropdownMenuItem data-testid="export-excel-all" className={ITEM_CLS} onClick={rekapExcel}><FileXlsIcon size={16} weight="bold" className="text-emerald-400" /> Rekap Excel</DropdownMenuItem>
                <DropdownMenuSeparator />
                <p className="px-2 py-1.5 text-[10px] font-mono text-muted-foreground">Untuk form Hour Meter semua unit gunakan tombol kuning.</p>
              </DropdownMenuContent>
            </DropdownMenu>

            <div className="[&_button]:h-10">
              <FormatMenu primary testid="hm-all" busyKey="all" label="Hour Meter Semua Unit" onPick={allHM} />
            </div>
          </>
        }
      />

      {/* Filter periode */}
      <div className="flex flex-wrap items-center gap-3 mb-6 border border-border p-3 bg-card" data-testid="report-filter">
        <div className="flex items-center gap-2 text-muted-foreground">
          <FunnelIcon size={16} weight="bold" />
          <span className="font-mono text-[10px] uppercase tracking-[0.2em]">Filter Periode</span>
        </div>
        <Input data-testid="filter-periode" type="month" value={periode} onChange={(e) => setPeriode(e.target.value)} className="rounded-sm w-auto bg-background" />
        {periode ? (
          <Button data-testid="clear-filter" variant="ghost" size="sm" className="rounded-sm text-muted-foreground hover:text-accent" onClick={() => setPeriode("")}>
            <XIcon size={14} weight="bold" className="mr-1" /> Semua Periode
          </Button>
        ) : null}
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Menampilkan: {periodeLabel()}</span>
      </div>

      {loading && <p className="font-mono text-xs text-muted-foreground">// Memuat laporan…</p>}
      {!loading && reports.length === 0 && <p className="font-mono text-xs text-muted-foreground border border-dashed border-border p-8 text-center">// Tidak ada data untuk periode ini</p>}

      <div className="space-y-6" data-testid="reports-list">
        {reports.map((r) => {
          const bad = KONDISI_ITEMS.filter(([k]) => r.kondisi_alat?.[k]?.status === "tidak").map(([, l]) => l);
          const checked = KONDISI_ITEMS.filter(([k]) => r.kondisi_alat?.[k]?.status).length;
          const totalBiaya = (r.total_sparepart || 0) + (r.total_gaji || 0) + (r.pengembalian_jam || 0) + (r.lain_lain || 0);
          return (
            <div key={r.unit_id} className="border border-border bg-card relative" data-testid={`report-unit-${r.unit_id}`}>
              <div className="absolute top-0 left-0 h-full w-0.5 bg-primary" />
              <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 p-4 border-b border-border bg-muted">
                <div className="flex items-center gap-3">
                  <div className="h-11 w-11 bg-primary/15 border border-primary/40 flex items-center justify-center shrink-0">
                    <TruckIcon size={20} weight="bold" className="text-primary" />
                  </div>
                  <div>
                    <p className="font-display font-black text-lg tracking-tighter">{r.unit_name} <span className="text-primary">· {r.nomor_lambung}</span>
                      {r.merek_type && <span className="ml-2 font-mono text-[10px] font-normal text-muted-foreground tracking-normal">{r.merek_type}</span>}
                    </p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground flex flex-wrap gap-x-3 gap-y-1 mt-0.5">
                      <span>SN {r.serial_number || "-"}</span>
                      <span>Operator: {(r.operators || []).join(", ") || r.operator_utama || "—"}</span>
                      {r.nama_proyek && <span className="flex items-center gap-1"><MapPinIcon size={11} weight="bold" />{r.nama_proyek}{r.lokasi_proyek ? ` · ${r.lokasi_proyek}` : ""}</span>}
                      {r.pengawas_lapangan && <span>Pengawas: {r.pengawas_lapangan}</span>}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {isAdmin && (
                    <Button data-testid={`unit-extras-${r.unit_id}`} size="sm" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => openExtras(r)}>
                      <NotePencilIcon size={14} weight="bold" className="mr-1.5" /> Biaya & Keterangan
                    </Button>
                  )}
                  <FormatMenu testid={`unit-hm-${r.unit_id}`} busyKey={r.unit_id} onPick={(fmt) => unitHM(r, fmt)} />
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-0">
                <Stat icon={CalendarCheckIcon} label="Hari Operasi">{r.hari_operasional}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">HARI</span></Stat>
                <Stat icon={ClockIcon} label="HM Awal → Akhir">{Number(r.hm_awal).toLocaleString("id-ID")} <span className="text-muted-foreground">→</span> {Number(r.hm_akhir).toLocaleString("id-ID")}</Stat>
                <Stat icon={ClockIcon} label="Total HM"><span className="text-primary text-2xl">{r.total_hm}</span><span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">JAM</span></Stat>
                <Stat icon={TimerIcon} label="Downtime">{r.total_downtime}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">JAM</span></Stat>
                <Stat icon={GasPumpIcon} label="Solar">{Number(r.total_solar).toLocaleString("id-ID")}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">L</span></Stat>
                <Stat icon={TruckIcon} label="Cars Baru">{r.total_cars}</Stat>
                <Stat icon={WrenchIcon} label="Sparepart"><span className="text-accent">{formatIDR(r.total_sparepart)}</span></Stat>
                <Stat icon={MoneyIcon} label="Total Biaya">{formatIDR(totalBiaya)}</Stat>
              </div>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 text-xs">
                <span className="flex items-center gap-1.5 text-muted-foreground"><MoneyIcon size={13} weight="bold" /> Gaji Operator <b className="text-foreground font-mono">{formatIDR(r.total_gaji)}</b></span>
                <span className="text-muted-foreground">Pengembalian Jam-Jaman <b className="text-foreground font-mono">{formatIDR(r.pengembalian_jam)}</b></span>
                <span className="text-muted-foreground">Lain-lain <b className="text-foreground font-mono">{formatIDR(r.lain_lain)}</b></span>
                <span className="flex items-center gap-1.5 ml-auto" data-testid={`unit-kondisi-${r.unit_id}`}>
                  {checked === 0 ? (
                    <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Kondisi alat belum diperiksa</span>
                  ) : bad.length ? (
                    <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 bg-accent text-accent-foreground flex items-center gap-1"><WarningIcon size={11} weight="bold" /> Perlu cek: {bad.join(", ")}</span>
                  ) : (
                    <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 border border-emerald-500/60 text-emerald-400 flex items-center gap-1"><ShieldCheckIcon size={11} weight="bold" /> Kondisi alat baik</span>
                  )}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Dialog biaya & keterangan */}
      <Dialog open={!!extrasFor} onOpenChange={(v) => { if (!v) setExtrasFor(null); }}>
        <DialogContent className="rounded-sm border-border bg-card max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl">Biaya & Keterangan Laporan</DialogTitle>
            <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">{extrasFor?.unit_label} · {periodeLabel()}</p>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Pengembalian Jam-Jaman</Label>
                <CurrencyInput data-testid="input-pengembalian-jam" className="rounded-sm mt-1.5" placeholder="Rp 0" value={extras.pengembalian_jam} onChange={(v) => setExtras({ ...extras, pengembalian_jam: v })} />
              </div>
              <div>
                <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Lain-lain</Label>
                <CurrencyInput data-testid="input-lain-lain" className="rounded-sm mt-1.5" placeholder="Rp 0" value={extras.lain_lain} onChange={(v) => setExtras({ ...extras, lain_lain: v })} />
              </div>
            </div>
            <div>
              <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Keterangan Tambahan</Label>
              <Textarea data-testid="input-keterangan-tambahan" rows={4} className="rounded-sm mt-1.5" placeholder="Contoh: Hujan 2 hari, unit standby menunggu material" value={extras.keterangan_tambahan} onChange={(e) => setExtras({ ...extras, keterangan_tambahan: e.target.value })} />
            </div>
            <p className="font-mono text-[10px] text-muted-foreground">Spare Part & Gaji Operator dihitung otomatis. Data ini disimpan per unit untuk periode <b className="text-primary">{periodeLabel()}</b>.</p>
          </div>
          <DialogFooter>
            <Button data-testid="save-extras-button" onClick={saveExtras} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
