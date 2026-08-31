import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { PageHeader, formatIDR } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { FileXlsIcon, FilePdfIcon, TruckIcon, ClockIcon, WrenchIcon, MoneyIcon, FunnelIcon, XIcon, ArchiveIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcelMultiSheet, exportToPDF, exportUnitReportPDF } from "@/lib/exporters";

const BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [periode, setPeriode] = useState(""); // "" = semua, atau "YYYY-MM"
  const [archive, setArchive] = useState([]);
  const [archiveOpen, setArchiveOpen] = useState(false);

  const loadArchive = async () => {
    try {
      const { data } = await api.get("/reports/archive");
      setArchive(data);
    } catch { toast.error("Gagal memuat arsip nomor"); }
  };

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/reports/units", { params: periode ? { periode } : {} });
      setReports(data);
    } catch { toast.error("Gagal memuat laporan"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [periode]);

  const periodeLabel = () => {
    if (!periode) return "Semua Periode";
    const [y, m] = periode.split("-");
    return `${BULAN_ID[Number(m)]} ${y}`;
  };

  // Terbitkan nomor laporan otomatis dari backend
  const issueNomor = async (ctx = {}) => {
    let month, year;
    if (periode) { const [y, m] = periode.split("-"); month = Number(m); year = Number(y); }
    else { const d = new Date(); month = d.getMonth() + 1; year = d.getFullYear(); }
    try {
      const { data } = await api.post("/reports/number", {
        month, year,
        jenis: ctx.jenis || "semua",
        unit_label: ctx.unit_label || "",
        periode_label: periodeLabel(),
      });
      loadArchive();
      return data.nomor;
    } catch { toast.error("Gagal menerbitkan nomor laporan"); return ""; }
  };

  // ---- Rekap semua unit ----
  const summaryRows = reports.map(r => ({
    Unit: r.unit_name,
    "Nomor Lambung": r.nomor_lambung,
    Serial: r.serial_number || "-",
    Operator: (r.operators || []).join(", ") || (r.operator_utama || "-"),
    "Total Cars": r.total_cars,
    "HM Awal": r.hm_awal,
    "HM Akhir": r.hm_akhir,
    "Total HM": r.total_hm,
    "Total Gaji": r.total_gaji,
    "Total Gaji Bersih": r.total_gaji_bersih,
    "Total Sparepart": r.total_sparepart,
  }));

  const downloadAllExcel = async () => {
    const nomor = await issueNomor({ jenis: "semua" });
    exportToExcelMultiSheet([
      { name: "Info", rows: [{ "Nomor Laporan": nomor, Periode: periodeLabel(), Digenerate: new Date().toLocaleString("id-ID") }] },
      { name: "Rekap Unit", rows: summaryRows },
    ], "laporan-semua-unit");
    toast.success(`Excel diunduh · ${nomor}`);
  };

  const downloadAllPDF = async () => {
    const nomor = await issueNomor({ jenis: "semua" });
    exportToPDF({
      title: "Laporan Rekap Semua Unit",
      nomor,
      periodeLabel: periodeLabel(),
      columns: ["Unit", "No Lambung", "Operator", "Total Cars", "HM Awal", "HM Akhir", "Total HM", "Total Gaji", "Total Sparepart"],
      rows: reports.map(r => [
        r.unit_name, r.nomor_lambung, (r.operators || []).join(", ") || "-",
        r.total_cars, r.hm_awal, r.hm_akhir, r.total_hm, formatIDR(r.total_gaji), formatIDR(r.total_sparepart),
      ]),
      filename: "laporan-semua-unit",
    });
    toast.success(`PDF diunduh · ${nomor}`);
  };

  // ---- Per unit ----
  const downloadUnitExcel = async (r) => {
    const nomor = await issueNomor({ jenis: "unit", unit_label: r.unit_label });
    const fname = `laporan-${r.unit_name}-${r.nomor_lambung}`.replace(/\s+/g, "_");
    exportToExcelMultiSheet([
      {
        name: "Ringkasan",
        rows: [
          { Keterangan: "Nomor Laporan", Nilai: nomor },
          { Keterangan: "Periode", Nilai: periodeLabel() },
          { Keterangan: "Unit", Nilai: r.unit_label },
          { Keterangan: "Serial Number", Nilai: r.serial_number || "-" },
          { Keterangan: "Operator", Nilai: (r.operators || []).join(", ") || "-" },
          { Keterangan: "Total Cars Baru", Nilai: r.total_cars },
          { Keterangan: "HM Awal", Nilai: r.hm_awal },
          { Keterangan: "HM Akhir", Nilai: r.hm_akhir },
          { Keterangan: "Total HM (Jam)", Nilai: r.total_hm },
          { Keterangan: "Total Gaji", Nilai: r.total_gaji },
          { Keterangan: "Total Kasbon", Nilai: r.total_kasbon },
          { Keterangan: "Total Gaji Bersih", Nilai: r.total_gaji_bersih },
          { Keterangan: "Total Penggantian Sparepart", Nilai: r.total_sparepart },
        ],
      },
      {
        name: "Operasional",
        rows: (r.operations || []).map(o => ({
          Tanggal: o.tanggal, Operator: o.operator_name, Pengurus: o.pengurus || "-",
          "HM Awal": o.hour_meter_awal, "HM Akhir": o.hour_meter_akhir, "Total Jam": o.total_jam, Cars: o.jumlah_cars,
        })),
      },
      {
        name: "Gaji",
        rows: (r.payroll || []).map(p => ({
          Periode: p.periode, Operator: p.operator_name, "Tarif/Jam": p.tarif_per_jam,
          "Jam Dibayar": p.jam_dibayar, Gaji: p.gaji, Kasbon: p.kasbon, "Gaji Bersih": p.gaji_bersih,
        })),
      },
      {
        name: "Sparepart",
        rows: (r.spareparts || []).flatMap(s =>
          (s.items && s.items.length ? s.items : [{ nama_sparepart: s.nama_sparepart, qty: 1, harga_satuan: s.biaya, total: s.biaya }]).map(it => ({
            Tanggal: s.tanggal, "No Nota": s.nomor_nota, "HM Service": s.hm_service ?? "-",
            Sparepart: it.nama_sparepart, Qty: it.qty, "Harga Satuan": it.harga_satuan, Total: it.total,
          }))
        ),
      },
    ], fname);
    toast.success(`Excel ${r.unit_name} diunduh · ${nomor}`);
  };

  const downloadUnitPDF = async (r) => {
    const nomor = await issueNomor({ jenis: "unit", unit_label: r.unit_label });
    const fname = `laporan-${r.unit_name}-${r.nomor_lambung}`.replace(/\s+/g, "_");
    exportUnitReportPDF(r, fname, { nomor, periodeLabel: periodeLabel() });
    toast.success(`PDF ${r.unit_name} diunduh · ${nomor}`);
  };

  return (
    <div>
      <PageHeader
        overline="// Reports / 05"
        title="Laporan per Unit"
        description="Rekap lengkap tiap unit: cars baru, operator, gaji operator, HM awal/akhir, total HM, dan penggantian sparepart. Setiap unduhan otomatis diberi nomor laporan resmi."
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
                    <thead className="bg-muted/50">
                      <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                        <th className="p-2.5">Nomor</th>
                        <th className="p-2.5">Jenis</th>
                        <th className="p-2.5">Unit</th>
                        <th className="p-2.5">Periode</th>
                        <th className="p-2.5">Diterbitkan</th>
                        <th className="p-2.5">Oleh</th>
                      </tr>
                    </thead>
                    <tbody>
                      {archive.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-muted-foreground text-xs font-mono">// Belum ada nomor diterbitkan</td></tr>}
                      {archive.map((a) => (
                        <tr key={a.id} className="border-t border-border hover:bg-secondary/30">
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
            <Button data-testid="export-excel-all" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={downloadAllExcel}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel Semua
            </Button>
            <Button data-testid="export-pdf-all" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={downloadAllPDF}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF Semua
            </Button>
          </>
        }
      />

      {/* Filter periode */}
      <div className="flex flex-wrap items-center gap-3 mb-6 border border-border p-3 bg-muted/30" data-testid="report-filter">
        <div className="flex items-center gap-2 text-muted-foreground">
          <FunnelIcon size={16} weight="bold" />
          <span className="font-mono text-[10px] uppercase tracking-[0.2em]">Filter Periode</span>
        </div>
        <Input
          data-testid="filter-periode"
          type="month"
          value={periode}
          onChange={(e) => setPeriode(e.target.value)}
          className="rounded-sm w-auto"
        />
        {periode ? (
          <Button data-testid="clear-filter" variant="ghost" size="sm" className="rounded-sm text-muted-foreground hover:text-accent" onClick={() => setPeriode("")}>
            <XIcon size={14} weight="bold" className="mr-1" /> Semua Periode
          </Button>
        ) : (
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Menampilkan: Semua Periode</span>
        )}
        {periode && <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Menampilkan: {periodeLabel()}</span>}
      </div>

      {loading && <p className="font-mono text-xs text-muted-foreground">// Memuat laporan…</p>}
      {!loading && reports.length === 0 && <p className="font-mono text-xs text-muted-foreground">// Tidak ada data untuk periode ini</p>}

      <div className="space-y-6" data-testid="reports-list">
        {reports.map((r) => (
          <div key={r.unit_id} className="border border-border" data-testid={`report-unit-${r.unit_id}`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border-b border-border bg-muted/40">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-primary/15 border border-primary/40 flex items-center justify-center">
                  <TruckIcon size={20} weight="bold" className="text-primary" />
                </div>
                <div>
                  <p className="font-display font-black text-lg tracking-tighter">{r.unit_name} <span className="text-primary">· {r.nomor_lambung}</span></p>
                  <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                    SN {r.serial_number || "-"} · Operator: {(r.operators || []).join(", ") || r.operator_utama || "—"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button data-testid={`unit-excel-${r.unit_id}`} size="sm" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => downloadUnitExcel(r)}>
                  <FileXlsIcon size={14} weight="bold" className="mr-1.5" /> Excel
                </Button>
                <Button data-testid={`unit-pdf-${r.unit_id}`} size="sm" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => downloadUnitPDF(r)}>
                  <FilePdfIcon size={14} weight="bold" className="mr-1.5" /> PDF
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-0">
              <div className="p-4 border-r border-b border-border">
                <div className="flex items-center gap-1.5 text-muted-foreground"><TruckIcon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">Cars Baru</p></div>
                <p className="font-display font-black text-2xl tracking-tighter mt-1.5">{r.total_cars}</p>
              </div>
              <div className="p-4 border-r border-b border-border">
                <div className="flex items-center gap-1.5 text-muted-foreground"><ClockIcon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">HM Awal → Akhir</p></div>
                <p className="font-display font-black text-lg tracking-tighter mt-1.5">{Number(r.hm_awal).toLocaleString("id-ID")} <span className="text-muted-foreground">→</span> {Number(r.hm_akhir).toLocaleString("id-ID")}</p>
              </div>
              <div className="p-4 border-r border-b border-border">
                <div className="flex items-center gap-1.5 text-muted-foreground"><ClockIcon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">Total HM</p></div>
                <p className="font-display font-black text-2xl tracking-tighter mt-1.5 text-primary">{r.total_hm}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">HRS</span></p>
              </div>
              <div className="p-4 border-r border-b border-border">
                <div className="flex items-center gap-1.5 text-muted-foreground"><MoneyIcon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">Total Gaji</p></div>
                <p className="font-display font-black text-lg tracking-tighter mt-1.5">{formatIDR(r.total_gaji)}</p>
              </div>
              <div className="p-4 border-r border-b border-border">
                <div className="flex items-center gap-1.5 text-muted-foreground"><MoneyIcon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">Gaji Bersih</p></div>
                <p className="font-display font-black text-lg tracking-tighter mt-1.5">{formatIDR(r.total_gaji_bersih)}</p>
              </div>
              <div className="p-4 border-b border-border">
                <div className="flex items-center gap-1.5 text-muted-foreground"><WrenchIcon size={13} weight="bold" /><p className="font-mono text-[9px] uppercase tracking-[0.15em]">Sparepart</p></div>
                <p className="font-display font-black text-lg tracking-tighter mt-1.5 text-accent">{formatIDR(r.total_sparepart)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
