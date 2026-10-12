import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { PageHeader, StatBox, formatIDR, CurrencyInput } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  PlusIcon, TrashIcon, PencilSimpleIcon, FileXlsIcon, FilePdfIcon, ArrowDownLeftIcon, ArrowUpRightIcon, WalletIcon,
  ReceiptIcon, LockSimpleIcon, FunnelIcon, XIcon,
} from "@phosphor-icons/react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";
import { fmtDate } from "@/lib/hourMeter";

const today = () => new Date().toISOString().slice(0, 10);
const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
const SRC_LABEL = { sparepart: "Otomatis · Sparepart", payroll: "Otomatis · Payroll" };
const INV_STATUS = ["Belum Dibayar", "Sebagian", "Lunas"];

// ---------- Konfigurasi tiap form (mengikuti Sistem_Administrasi_Keuangan_Perusahaan.xlsx) ----------
const SECTIONS = {
  "kas-masuk": {
    title: "Kas Masuk", endpoint: "/finance/kas-masuk", periodeFilter: true, numberKey: "no_bukti", numberHint: "KM-TTP-xxx otomatis",
    fields: [
      { key: "tanggal", label: "Tanggal", type: "date", required: true },
      { key: "uraian", label: "Uraian", type: "text", required: true, full: true },
      { key: "tujuan_dana", label: "Tujuan Dana", type: "text" },
      { key: "pic", label: "PIC", type: "text" },
      { key: "debit", label: "Debit (Masuk)", type: "currency", required: true, full: true },
    ],
    columns: [
      { key: "tanggal", label: "Tanggal", type: "date" }, { key: "uraian", label: "Uraian" }, { key: "tujuan_dana", label: "Tujuan Dana" },
      { key: "no_bukti", label: "No Bukti", type: "mono" }, { key: "debit", label: "Debit (Masuk)", type: "idr" }, { key: "pic", label: "PIC" },
      { key: "_saldo", label: "Saldo", type: "idr" },
    ],
    sumKey: "debit",
  },
  "kas-keluar": {
    title: "Kas Keluar", endpoint: "/finance/kas-keluar", periodeFilter: true, numberKey: "no_bukti", numberHint: "BK/KK-TTP-xxx otomatis", jenisFilter: true,
    fields: [
      { key: "tanggal", label: "Tanggal", type: "date", required: true },
      { key: "jenis", label: "Jenis Bukti", type: "select", options: [["KK", "KK · Gaji / Kasbon / Biaya lain"], ["BK", "BK · Belanja Sparepart / Barang"]], lockOnEdit: true },
      { key: "uraian", label: "Uraian", type: "text", required: true, full: true },
      { key: "penerima", label: "Penerima", type: "text" },
      { key: "kredit", label: "Kredit (Keluar)", type: "currency", required: true },
      { key: "keterangan", label: "Keterangan", type: "text", full: true },
    ],
    columns: [
      { key: "tanggal", label: "Tanggal", type: "date" }, { key: "uraian", label: "Uraian" }, { key: "penerima", label: "Penerima" },
      { key: "no_bukti", label: "No Bukti", type: "mono" }, { key: "kredit", label: "Kredit (Keluar)", type: "idr" }, { key: "keterangan", label: "Keterangan", type: "ket" },
    ],
    sumKey: "kredit",
  },
  invoices: {
    title: "Invoice", endpoint: "/finance/invoices", numberKey: "no_invoice", numberHint: "INV/TTP/xxx/bulan/tahun otomatis",
    fields: [
      { key: "tanggal", label: "Tanggal", type: "date", required: true },
      { key: "status", label: "Status Pembayaran", type: "select", options: INV_STATUS.map(s => [s, s]) },
      { key: "nama_client", label: "Nama Client", type: "text", required: true, full: true },
      { key: "deskripsi", label: "Deskripsi", type: "textarea", full: true },
      { key: "jumlah", label: "Jumlah", type: "currency", required: true, full: true },
    ],
    columns: [
      { key: "no_invoice", label: "No Invoice", type: "mono" }, { key: "tanggal", label: "Tanggal", type: "date" }, { key: "nama_client", label: "Nama Client" },
      { key: "deskripsi", label: "Deskripsi" }, { key: "jumlah", label: "Jumlah", type: "idr" }, { key: "status", label: "Status Pembayaran", type: "inv" },
    ],
    sumKey: "jumlah",
  },
  "surat-masuk": {
    title: "Surat Masuk", endpoint: "/finance/surat-masuk",
    fields: [
      { key: "tanggal_surat", label: "Tanggal Surat", type: "date", required: true },
      { key: "tanggal_terima", label: "Tanggal Terima", type: "date" },
      { key: "nomor_surat", label: "Nomor Surat", type: "text", required: true, full: true },
      { key: "pengirim", label: "Pengirim", type: "text", required: true },
      { key: "perihal", label: "Perihal", type: "text", required: true },
      { key: "keterangan", label: "Keterangan", type: "text", full: true },
    ],
    columns: [
      { key: "tanggal_surat", label: "Tanggal Surat", type: "date" }, { key: "nomor_surat", label: "Nomor Surat", type: "mono" }, { key: "pengirim", label: "Pengirim" },
      { key: "perihal", label: "Perihal" }, { key: "tanggal_terima", label: "Tanggal Terima", type: "date" }, { key: "keterangan", label: "Keterangan" },
    ],
  },
  "surat-keluar": {
    title: "Surat Keluar", endpoint: "/finance/surat-keluar", numberKey: "nomor_surat", numberHint: "SP/TTP/xxx/bulan/tahun otomatis",
    fields: [
      { key: "tanggal_surat", label: "Tanggal Surat", type: "date", required: true },
      { key: "pengirim", label: "Pengirim", type: "text" },
      { key: "tujuan_surat", label: "Tujuan Surat", type: "text", required: true, full: true },
      { key: "perihal", label: "Perihal", type: "text", required: true, full: true },
      { key: "keterangan", label: "Keterangan", type: "text", full: true },
    ],
    columns: [
      { key: "tanggal_surat", label: "Tanggal Surat", type: "date" }, { key: "nomor_surat", label: "Nomor Surat", type: "mono" }, { key: "tujuan_surat", label: "Tujuan Surat" },
      { key: "perihal", label: "Perihal" }, { key: "pengirim", label: "Pengirim" }, { key: "keterangan", label: "Keterangan" },
    ],
  },
};

const fmtCell = (c, v) => {
  if (c.type === "date") return fmtDate(v);
  if (c.type === "idr") return formatIDR(v);
  return v === undefined || v === null || v === "" ? "-" : String(v);
};

function CrudSection({ id, onChanged }) {
  const cfg = SECTIONS[id];
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [periode, setPeriode] = useState("");
  const [jenis, setJenis] = useState("all");
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const blank = () => Object.fromEntries(cfg.fields.map(f => [f.key, f.type === "date" && f.required ? today() : f.type === "select" ? f.options[0][0] : ""]));
  const [form, setForm] = useState(blank());

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(cfg.endpoint, { params: cfg.periodeFilter && periode ? { periode } : {} });
      setRows(data);
    } catch { toast.error(`Gagal memuat ${cfg.title}`); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [periode]);

  const view = useMemo(() => {
    let list = jenis === "all" ? rows : rows.filter(r => r.jenis === jenis);
    if (id === "kas-masuk") { let s = 0; list = list.map(r => ({ ...r, _saldo: (s += Number(r.debit || 0)) })); }
    return list;
  }, [rows, jenis, id]);
  const total = cfg.sumKey ? view.reduce((a, r) => a + Number(r[cfg.sumKey] || 0), 0) : 0;

  const openNew = () => { setForm(blank()); setEditId(null); setOpen(true); };
  const openEdit = (r) => { setForm(Object.fromEntries(cfg.fields.map(f => [f.key, r[f.key] ?? ""]))); setEditId(r.id); setOpen(true); };

  const save = async () => {
    const miss = cfg.fields.find(f => f.required && (form[f.key] === "" || form[f.key] === null || form[f.key] === undefined));
    if (miss) { toast.error(`${miss.label} wajib diisi`); return; }
    const payload = { ...form };
    cfg.fields.filter(f => f.type === "currency").forEach(f => { payload[f.key] = Number(payload[f.key] || 0); });
    try {
      const { data } = editId ? await api.patch(`${cfg.endpoint}/${editId}`, payload) : await api.post(cfg.endpoint, payload);
      toast.success(editId ? "Perubahan tersimpan" : `Tersimpan${cfg.numberKey && data?.[cfg.numberKey] ? ` · ${data[cfg.numberKey]}` : ""}`);
      setOpen(false); load(); onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
  };

  const del = async (r) => {
    if (!window.confirm(`Hapus data ini${r[cfg.numberKey] ? ` (${r[cfg.numberKey]})` : ""}?`)) return;
    try { await api.delete(`${cfg.endpoint}/${r.id}`); toast.success("Terhapus"); load(); onChanged && onChanged(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menghapus"); }
  };

  const periodeLabel = periode ? new Date(`${periode}-01`).toLocaleDateString("id-ID", { month: "long", year: "numeric" }) : "Semua Periode";
  const exportCols = cfg.columns;
  const doExcel = () => exportToExcel(view.map((r, i) => ({ No: i + 1, ...Object.fromEntries(exportCols.map(c => [c.label, c.type === "idr" ? Number(r[c.key] || 0) : c.type === "date" ? fmtDate(r[c.key]) : (r[c.key] ?? "")])) })), `${cfg.title.replace(/\s+/g, "-")}_${periode || "semua"}`, cfg.title);
  const doPDF = () => exportToPDF({
    title: cfg.title, periodeLabel,
    columns: ["No", ...exportCols.map(c => c.label)],
    rows: [...view.map((r, i) => [i + 1, ...exportCols.map(c => fmtCell(c, r[c.key]))]),
      ...(cfg.sumKey ? [["", ...exportCols.map(c => c.key === cfg.sumKey ? formatIDR(total) : c === exportCols[0] ? "TOTAL" : "")]] : [])],
    filename: `${cfg.title.replace(/\s+/g, "-")}_${periode || "semua"}`,
  });

  return (
    <div data-testid={`fin-section-${id}`}>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {cfg.periodeFilter && (
          <div className="flex items-center gap-2 border border-border bg-card px-3 py-1.5">
            <FunnelIcon size={14} weight="bold" className="text-muted-foreground" />
            <Input data-testid={`fin-${id}-periode`} type="month" value={periode} onChange={e => setPeriode(e.target.value)} className="h-8 w-auto rounded-sm bg-background" />
            {periode && <button data-testid={`fin-${id}-clear`} onClick={() => setPeriode("")} className="text-muted-foreground hover:text-accent"><XIcon size={14} weight="bold" /></button>}
          </div>
        )}
        {cfg.jenisFilter && (
          <div className="flex border border-border bg-card">
            {[["all", "Semua"], ["BK", "BK · Belanja"], ["KK", "KK · Gaji/Kasbon/Lain"]].map(([v, l]) => (
              <button key={v} data-testid={`fin-jenis-${v}`} onClick={() => setJenis(v)} className={`px-3 py-2 text-xs font-mono uppercase tracking-wider ${jenis === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{l}</button>
            ))}
          </div>
        )}
        <div className="ml-auto flex gap-2">
          <Button data-testid={`fin-${id}-excel`} variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={doExcel}><FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel</Button>
          <Button data-testid={`fin-${id}-pdf`} variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={doPDF}><FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF</Button>
          <Button data-testid={`fin-${id}-add`} onClick={openNew} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground font-display tracking-tight"><PlusIcon size={16} weight="bold" className="mr-1.5" /> Tambah</Button>
        </div>
      </div>

      <div className="border border-border overflow-x-auto bg-card" data-testid={`fin-${id}-table`}>
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3 w-10">No</th>
              {cfg.columns.map(c => <th key={c.key} className={`p-3 whitespace-nowrap ${c.type === "idr" ? "text-right" : ""}`}>{c.label}</th>)}
              <th className="p-3 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={cfg.columns.length + 2} className="p-6 text-center text-xs font-mono text-muted-foreground">// Memuat…</td></tr>}
            {!loading && view.length === 0 && <tr><td colSpan={cfg.columns.length + 2} className="p-8 text-center text-xs font-mono text-muted-foreground">// Belum ada data {cfg.title.toLowerCase()}</td></tr>}
            {view.map((r, i) => {
              const auto = r.source && r.source !== "manual";
              return (
                <tr key={r.id} className="border-t border-border hover:bg-secondary/60" data-testid={`fin-${id}-row-${r.id}`}>
                  <td className="p-3 font-mono text-muted-foreground">{i + 1}</td>
                  {cfg.columns.map(c => (
                    <td key={c.key} className={`p-3 ${c.type === "idr" ? "text-right font-mono whitespace-nowrap" : ""} ${c.type === "mono" ? "font-mono text-primary whitespace-nowrap" : ""} ${c.type === "date" ? "font-mono whitespace-nowrap" : ""} ${c.key === "_saldo" ? "text-emerald-400" : ""}`}>
                      {c.type === "inv" ? (
                        <span className={`font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${r.status === "Lunas" ? "border-emerald-500/60 text-emerald-400" : r.status === "Sebagian" ? "border-primary/70 text-primary" : "border-accent text-accent"}`}>{r.status}</span>
                      ) : c.type === "ket" ? (
                        <div className="flex flex-col gap-1">
                          {auto && <span className="w-fit font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border border-sky-400/50 text-sky-300">{SRC_LABEL[r.source] || "Otomatis"}</span>}
                          <span className="text-muted-foreground">{r.keterangan || (auto ? "" : "-")}</span>
                        </div>
                      ) : fmtCell(c, r[c.key])}
                    </td>
                  ))}
                  <td className="p-3 text-right whitespace-nowrap">
                    {auto ? (
                      <span title="Transaksi otomatis — ubah dari menu Sparepart/Payroll" className="inline-flex p-1.5 border border-border text-muted-foreground"><LockSimpleIcon size={14} weight="bold" /></span>
                    ) : (
                      <div className="inline-flex gap-1">
                        <button data-testid={`fin-${id}-edit-${r.id}`} onClick={() => openEdit(r)} className="p-1.5 border border-border hover:border-primary hover:text-primary"><PencilSimpleIcon size={14} weight="bold" /></button>
                        <button data-testid={`fin-${id}-delete-${r.id}`} onClick={() => del(r)} className="p-1.5 border border-border hover:border-accent hover:text-accent"><TrashIcon size={14} weight="bold" /></button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {cfg.sumKey && view.length > 0 && (
            <tfoot>
              <tr className="border-t-2 border-primary bg-muted">
                <td className="p-3 font-mono text-[10px] uppercase tracking-[0.2em] text-primary" colSpan={cfg.columns.findIndex(c => c.key === cfg.sumKey) + 1}>Total · {view.length} transaksi</td>
                <td className="p-3 text-right font-display font-black text-primary whitespace-nowrap" data-testid={`fin-${id}-total`}>{formatIDR(total)}</td>
                <td colSpan={cfg.columns.length - cfg.columns.findIndex(c => c.key === cfg.sumKey)} />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="rounded-sm border-border bg-card max-w-xl">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl">{editId ? `Edit ${cfg.title}` : `Tambah ${cfg.title}`}</DialogTitle>
            {cfg.numberHint && <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Nomor: {cfg.numberHint}</p>}
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            {cfg.fields.map(f => (
              <div key={f.key} className={f.full ? "col-span-2" : "col-span-2 sm:col-span-1"}>
                <Label className={lbl}>{f.label}{f.required ? " *" : ""}</Label>
                {f.type === "currency" ? (
                  <CurrencyInput data-testid={`fin-input-${f.key}`} className="rounded-sm mt-1.5" placeholder="Rp 0" value={form[f.key]} onChange={v => setForm({ ...form, [f.key]: v })} />
                ) : f.type === "select" ? (
                  <Select value={form[f.key] || f.options[0][0]} disabled={f.lockOnEdit && !!editId} onValueChange={v => setForm({ ...form, [f.key]: v })}>
                    <SelectTrigger data-testid={`fin-input-${f.key}`} className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger>
                    <SelectContent>{f.options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
                  </Select>
                ) : f.type === "textarea" ? (
                  <Textarea data-testid={`fin-input-${f.key}`} rows={3} className="rounded-sm mt-1.5" value={form[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
                ) : (
                  <Input data-testid={`fin-input-${f.key}`} type={f.type === "date" ? "date" : "text"} className="rounded-sm mt-1.5" value={form[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
                )}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button data-testid={`fin-${id}-save`} onClick={save} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function RekapSection({ summary, year, setYear }) {
  const months = summary?.months || [];
  const doExcel = () => exportToExcel(months.map(m => ({ Bulan: m.bulan, "Total Masuk": m.total_masuk, "Total Keluar": m.total_keluar, Saldo: m.saldo })), `Rekap-Keuangan_${year}`, "Rekap Bulanan");
  const doPDF = () => exportToPDF({
    title: `Rekap Bulanan Keuangan ${year}`, periodeLabel: `Tahun ${year}`,
    columns: ["Bulan", "Total Masuk", "Total Keluar", "Saldo"],
    rows: [...months.map(m => [m.bulan, formatIDR(m.total_masuk), formatIDR(m.total_keluar), formatIDR(m.saldo)]),
      ["TOTAL", formatIDR(months.reduce((a, m) => a + m.total_masuk, 0)), formatIDR(months.reduce((a, m) => a + m.total_keluar, 0)), formatIDR(months[11]?.saldo || 0)]],
    filename: `Rekap-Keuangan_${year}`,
  });
  return (
    <div data-testid="fin-section-rekap">
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <Select value={String(year)} onValueChange={v => setYear(Number(v))}>
          <SelectTrigger data-testid="fin-rekap-year" className="rounded-sm w-32"><SelectValue /></SelectTrigger>
          <SelectContent>{[0, 1, 2, 3, 4].map(d => { const y = new Date().getFullYear() - d; return <SelectItem key={y} value={String(y)}>{y}</SelectItem>; })}</SelectContent>
        </Select>
        <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Saldo awal tahun: <b className="text-foreground">{formatIDR(summary?.saldo_awal_tahun)}</b></p>
        <div className="ml-auto flex gap-2">
          <Button data-testid="fin-rekap-excel" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={doExcel}><FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel</Button>
          <Button data-testid="fin-rekap-pdf" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={doPDF}><FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF</Button>
        </div>
      </div>
      <div className="border border-border overflow-x-auto bg-card" data-testid="fin-rekap-table">
        <table className="w-full text-sm">
          <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-3">Bulan</th><th className="p-3 text-right">Total Masuk</th><th className="p-3 text-right">Total Keluar</th><th className="p-3 text-right">Saldo</th></tr></thead>
          <tbody>
            {months.map(m => (
              <tr key={m.periode} className="border-t border-border hover:bg-secondary/60">
                <td className="p-3 font-medium">{m.bulan}</td>
                <td className="p-3 text-right font-mono text-emerald-400">{m.total_masuk ? formatIDR(m.total_masuk) : "—"}</td>
                <td className="p-3 text-right font-mono text-accent">{m.total_keluar ? formatIDR(m.total_keluar) : "—"}</td>
                <td className="p-3 text-right font-mono font-semibold">{formatIDR(m.saldo)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function FinancePage() {
  const [tab, setTab] = useState("dashboard");
  const [year, setYear] = useState(new Date().getFullYear());
  const [summary, setSummary] = useState(null);
  const loadSummary = async () => {
    try { const { data } = await api.get("/finance/summary", { params: { year } }); setSummary(data); }
    catch { toast.error("Gagal memuat ringkasan keuangan"); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadSummary(); }, [year]);

  const tabs = [["dashboard", "Dashboard"], ["kas-masuk", "Kas Masuk"], ["kas-keluar", "Kas Keluar"], ["invoices", "Invoice"], ["surat-masuk", "Surat Masuk"], ["surat-keluar", "Surat Keluar"], ["rekap", "Rekap Bulanan"]];

  return (
    <div>
      <PageHeader overline="// Finance / 07" title="Keuangan & Administrasi"
        description="Sistem administrasi keuangan perusahaan: kas masuk, kas keluar (nota sparepart & payroll tercatat otomatis), invoice, surat masuk/keluar, dan rekap bulanan. Nomor bukti & surat dibuat otomatis." />
      <Tabs value={tab} onValueChange={(v) => { setTab(v); if (v === "dashboard" || v === "rekap") loadSummary(); }}>
        <TabsList className="flex flex-wrap h-auto w-full justify-start rounded-sm bg-card border border-border p-1 mb-6 gap-1">
          {tabs.map(([v, l]) => (
            <TabsTrigger key={v} value={v} data-testid={`fin-tab-${v}`} className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">{l}</TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="dashboard">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            <StatBox testid="fin-stat-masuk" label="Total Kas Masuk" value={formatIDR(summary?.total_kas_masuk)} icon={ArrowDownLeftIcon} accent="foreground" />
            <StatBox testid="fin-stat-keluar" label="Total Kas Keluar" value={formatIDR(summary?.total_kas_keluar)} icon={ArrowUpRightIcon} accent="accent" />
            <StatBox testid="fin-stat-saldo" label="Saldo Akhir" value={formatIDR(summary?.saldo_akhir)} icon={WalletIcon} accent="primary" />
            <StatBox testid="fin-stat-invoice" label="Invoice Belum Lunas" value={formatIDR(summary?.invoice_outstanding)} icon={ReceiptIcon} accent="foreground" />
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className="xl:col-span-2 border border-border bg-card p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Arus Kas {year}</p>
              <h3 className="font-display font-black text-xl tracking-tighter mb-4">Masuk vs Keluar per Bulan</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={(summary?.months || []).map(m => ({ ...m, bulan: m.bulan.slice(0, 3) }))}>
                    <CartesianGrid stroke="#1E3A52" vertical={false} />
                    <XAxis dataKey="bulan" stroke="#8FA6B8" fontSize={10} tickLine={false} />
                    <YAxis stroke="#8FA6B8" fontSize={10} tickLine={false} tickFormatter={v => `${(v / 1e6).toFixed(0)}jt`} />
                    <Tooltip contentStyle={{ background: "#0F2D44", border: "1px solid #2A4A63", color: "#F3F7FB", borderRadius: 0, fontSize: 12 }} formatter={v => formatIDR(v)} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="total_masuk" name="Masuk" fill="#FEC202" />
                    <Bar dataKey="total_keluar" name="Keluar" fill="#EF3B2D" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="border border-border bg-card p-5 space-y-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Komposisi Kas Keluar</p>
              {[["BK · Belanja Sparepart/Barang", summary?.keluar_bk, "bg-primary"], ["KK · Gaji/Kasbon/Biaya Lain", summary?.keluar_kk, "bg-accent"]].map(([l, v, c]) => {
                const pct = summary?.total_kas_keluar ? Math.round(((v || 0) / summary.total_kas_keluar) * 100) : 0;
                return (
                  <div key={l}>
                    <div className="flex justify-between text-xs"><span className="text-muted-foreground">{l}</span><span className="font-mono">{pct}%</span></div>
                    <p className="font-display font-black text-lg tracking-tight mt-1">{formatIDR(v)}</p>
                    <div className="h-1.5 bg-background mt-2"><div className={`h-full ${c}`} style={{ width: `${pct}%` }} /></div>
                  </div>
                );
              })}
              <p className="font-mono text-[10px] text-muted-foreground pt-2 border-t border-border">Nota sparepart → BK otomatis · Payroll (gaji & kasbon) → KK otomatis.</p>
            </div>
          </div>
        </TabsContent>

        {Object.keys(SECTIONS).map(id => (
          <TabsContent key={id} value={id}>{tab === id && <CrudSection id={id} onChanged={loadSummary} />}</TabsContent>
        ))}
        <TabsContent value="rekap"><RekapSection summary={summary} year={year} setYear={setYear} /></TabsContent>
      </Tabs>
    </div>
  );
}
