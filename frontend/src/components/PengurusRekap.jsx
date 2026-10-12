import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { formatIDR } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FilePdfIcon, FileXlsIcon, CaretRightIcon, CaretDownIcon, WarningIcon, CoinsIcon, ArrowUpRightIcon, WalletIcon, ClockIcon, ArrowClockwiseIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";
import { METRICS, fmtMetric, exportPengurusRekapPDF, exportPengurusRekapExcel } from "@/lib/pengurusRekap";

const MON = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const VIEWS = [
  ["pendapatan", "Pendapatan"],
  ["pengeluaran", "Pengeluaran"],
  ["bersih", "Penghasilan Bersih"],
  ["diterima", "Transfer Diterima"],
  ["piutang", "Piutang"],
  ["jam", "Jam Kerja"],
];
const short = (k, v) => {
  if (!v) return "—";
  if (k === "jam") return Number(v).toLocaleString("id-ID", { maximumFractionDigits: 2 });
  const a = Math.abs(v);
  const s = a >= 1e9 ? `${(a / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 2 })} M` : a >= 1e6 ? `${(a / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt` : a.toLocaleString("id-ID");
  return (v < 0 ? "-" : "") + s;
};
const tone = (k, v) => (k === "piutang" ? (v > 0 ? "text-accent" : v < 0 ? "text-emerald-400" : "text-muted-foreground") : k === "diterima" ? (v ? "text-emerald-400" : "text-muted-foreground") : k === "bersih" ? (v < 0 ? "text-accent" : v > 0 ? "text-emerald-400" : "text-muted-foreground") : k === "pengeluaran" ? (v ? "text-accent" : "text-muted-foreground") : v ? "" : "text-muted-foreground");

export default function PengurusRekap({ refreshKey }) {
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState(thisYear);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [view, setView] = useState("pendapatan");
  const [expanded, setExpanded] = useState({});
  const [busy, setBusy] = useState("");

  const load = async () => {
    setLoading(true); setError(false);
    try { const { data: d } = await api.get("/pengurus-rekap", { params: { year } }); setData(d); }
    catch { setError(true); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [year, refreshKey]);

  const doExport = async (fmt) => {
    if (!data?.rows?.length) { toast.error("Belum ada data untuk diunduh"); return; }
    setBusy(fmt);
    try {
      const { data: n } = await api.post("/reports/number", { month: year === thisYear ? new Date().getMonth() + 1 : 12, year, jenis: "semua", unit_label: "Rekap Penghasilan Pengurus", periode_label: `Tahun ${year}` });
      const fname = `Rekap-Penghasilan-Pengurus_${year}`;
      if (fmt === "pdf") exportPengurusRekapPDF(data, { nomor: n.nomor }, fname);
      else await exportPengurusRekapExcel(data, { nomor: n.nomor }, fname);
      toast.success(`${fmt === "pdf" ? "PDF" : "Excel"} diunduh · ${n.nomor}`);
    } catch (e) { console.error(e); toast.error("Gagal membuat file rekap"); }
    finally { setBusy(""); }
  };

  const rows = data?.rows || [];
  const missing = rows.filter((r) => r.jam_tanpa_tarif > 0);
  const viewLabel = VIEWS.find(([k]) => k === view)?.[1];

  return (
    <section className="mt-10" data-testid="pengurus-rekap">
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4 mb-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Rekap Penghasilan</p>
          <h2 className="font-display font-black text-3xl tracking-tighter">Penghasilan per Pengurus · {year}</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">Pendapatan = jam kerja (HM) × tarif sewa per jam. Pengeluaran = gaji operator + sparepart unit yang diurus. Bersih = pendapatan − pengeluaran. Transfer Diterima = Kas Masuk yang ditandai pengurus (termasuk dari WhatsApp); Piutang = pendapatan − transfer diterima.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
            <SelectTrigger data-testid="rekap-pengurus-year" className="rounded-sm w-28 bg-card"><SelectValue /></SelectTrigger>
            <SelectContent>{[0, 1, 2, 3, 4].map((d) => <SelectItem key={d} value={String(thisYear - d)}>{thisYear - d}</SelectItem>)}</SelectContent>
          </Select>
          <Button data-testid="rekap-pengurus-excel" variant="outline" disabled={!!busy} onClick={() => doExport("xlsx")} className="rounded-sm border-border hover:border-primary hover:text-primary">
            <FileXlsIcon size={16} weight="bold" className="mr-2" /> {busy === "xlsx" ? "Membuat…" : "Excel"}
          </Button>
          <Button data-testid="rekap-pengurus-pdf" disabled={!!busy} onClick={() => doExport("pdf")} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground font-display tracking-tight">
            <FilePdfIcon size={16} weight="bold" className="mr-2" /> {busy === "pdf" ? "Membuat…" : "PDF Berkop"}
          </Button>
        </div>
      </div>

      {/* Ringkasan */}
      <div className="grid grid-cols-2 xl:grid-cols-4 border border-border bg-card mb-4">
        {[
          ["Total Pendapatan", data?.total?.pendapatan, CoinsIcon, "text-primary", "rekap-total-pendapatan"],
          ["Total Pengeluaran", data?.total?.pengeluaran, ArrowUpRightIcon, "text-accent", "rekap-total-pengeluaran"],
          ["Penghasilan Bersih", data?.total?.bersih, WalletIcon, (data?.total?.bersih || 0) < 0 ? "text-accent" : "text-emerald-400", "rekap-total-bersih"],
          ["Total Jam Kerja", data?.total?.jam, ClockIcon, "", "rekap-total-jam"],
        ].map(([l, v, Icon, c, tid], i) => (
          <div key={l} className={`p-4 ${i < 3 ? "xl:border-r" : ""} ${i % 2 === 0 ? "border-r xl:border-r" : ""} ${i < 2 ? "border-b xl:border-b-0" : ""} border-border`}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5"><Icon size={12} weight="bold" /> {l}</p>
            {loading ? <Skeleton className="h-8 w-32 mt-2 rounded-sm" /> : (
              <p data-testid={tid} className={`font-display font-black text-2xl tracking-tighter mt-1.5 ${c}`}>
                {l.includes("Jam") ? <>{Number(v || 0).toLocaleString("id-ID", { maximumFractionDigits: 2 })} <span className="text-xs font-mono font-normal text-muted-foreground">JAM</span></> : formatIDR(v)}
              </p>
            )}
          </div>
        ))}
      </div>

      {missing.length > 0 && (
        <div data-testid="rekap-missing-tarif" className="flex items-start gap-2 border border-primary/50 bg-primary/10 px-4 py-3 mb-4 text-xs">
          <WarningIcon size={16} weight="bold" className="text-primary shrink-0 mt-0.5" />
          <p><b className="text-primary">Tarif belum diisi:</b> {missing.map((r) => `${r.nama} (${r.jam_tanpa_tarif.toLocaleString("id-ID")} jam)`).join(", ")}. Jam tersebut belum menghasilkan pendapatan — isi <b>Tarif Sewa per Jam</b> di Unit Registry atau di data pengurus.</p>
        </div>
      )}

      {/* Pilihan tampilan */}
      <div className="flex flex-wrap border border-border bg-card w-fit mb-3" role="tablist">
        {VIEWS.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={view === k} data-testid={`rekap-view-${k}`} onClick={() => setView(k)}
            className={`px-3 py-2 text-xs font-mono uppercase tracking-wider transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${view === k ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
            {l}
          </button>
        ))}
      </div>

      <div className="border border-border bg-card overflow-x-auto" data-testid="rekap-pengurus-table">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3 sticky left-0 bg-muted min-w-[200px]">Pengurus</th>
              {MON.map((m) => <th key={m} className="p-3 text-right whitespace-nowrap">{m}</th>)}
              <th className="p-3 text-right whitespace-nowrap text-primary">Total {viewLabel}</th>
            </tr>
          </thead>
          <tbody>
            {loading && [0, 1, 2].map((i) => (
              <tr key={i} className="border-t border-border"><td colSpan={14} className="p-3"><Skeleton className="h-5 w-full rounded-sm" /></td></tr>
            ))}
            {!loading && error && (
              <tr><td colSpan={14} className="p-8 text-center">
                <p className="text-xs font-mono text-muted-foreground mb-3">// Gagal memuat rekap penghasilan</p>
                <Button data-testid="rekap-retry" size="sm" variant="outline" onClick={load} className="rounded-sm"><ArrowClockwiseIcon size={14} weight="bold" className="mr-1.5" /> Coba lagi</Button>
              </td></tr>
            )}
            {!loading && !error && rows.length === 0 && (
              <tr><td colSpan={14} className="p-8 text-center text-xs font-mono text-muted-foreground">// Belum ada data operasi pada tahun {year}</td></tr>
            )}
            {!loading && !error && rows.map((r) => {
              const open = !!expanded[r.nama];
              return (
                <React.Fragment key={r.nama}>
                  <tr className="border-t border-border hover:bg-secondary/60 cursor-pointer" data-testid={`rekap-row-${r.pengurus_id || "none"}`} onClick={() => setExpanded({ ...expanded, [r.nama]: !open })}>
                    <td className="p-3 sticky left-0 bg-card">
                      <div className="flex items-center gap-2">
                        {open ? <CaretDownIcon size={12} weight="bold" className="text-primary" /> : <CaretRightIcon size={12} weight="bold" className="text-muted-foreground" />}
                        <div>
                          <p className="font-medium">{r.nama}</p>
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{r.units.length} unit · {r.tarif_pengurus ? `${formatIDR(r.tarif_pengurus)}/jam` : "tarif per unit"}</p>
                        </div>
                      </div>
                    </td>
                    {r.months.map((m) => <td key={m.periode} className={`p-3 text-right font-mono text-xs whitespace-nowrap ${tone(view, m[view])}`}>{short(view, m[view])}</td>)}
                    <td className={`p-3 text-right font-display font-black whitespace-nowrap ${view === "bersih" ? tone("bersih", r.total[view]) : "text-primary"}`} data-testid={`rekap-total-${r.pengurus_id || "none"}`}>{fmtMetric(view === "pengeluaran" ? "gaji" : view, r.total[view])}</td>
                  </tr>
                  {open && METRICS.map(([k, l]) => (
                    <tr key={k} className="bg-background/60 border-t border-border/50" data-testid={`rekap-detail-${r.pengurus_id || "none"}-${k}`}>
                      <td className="py-2 pl-10 pr-3 sticky left-0 bg-background font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{l}</td>
                      {r.months.map((m) => <td key={m.periode} className={`py-2 px-3 text-right font-mono text-[11px] whitespace-nowrap ${tone(k, m[k])}`}>{short(k, m[k])}</td>)}
                      <td className={`py-2 px-3 text-right font-mono text-xs font-semibold whitespace-nowrap ${tone(k, r.total[k])}`}>{fmtMetric(k, r.total[k])}</td>
                    </tr>
                  ))}
                  {open && (
                    <tr className="bg-background/60 border-t border-border/50">
                      <td colSpan={14} className="py-2 pl-10 pr-3 font-mono text-[10px] text-muted-foreground">Unit: {r.units.join(", ") || "—"}</td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
          {!loading && !error && rows.length > 0 && (
            <tfoot>
              <tr className="border-t-2 border-primary bg-muted">
                <td className="p-3 sticky left-0 bg-muted font-mono text-[10px] uppercase tracking-[0.2em] text-primary">Total · {rows.length} pengurus</td>
                {data.months.map((m) => <td key={m.periode} className={`p-3 text-right font-mono text-xs font-semibold whitespace-nowrap ${tone(view, m[view])}`}>{short(view, m[view])}</td>)}
                <td className={`p-3 text-right font-display font-black whitespace-nowrap ${view === "bersih" ? tone("bersih", data.total[view]) : "text-primary"}`} data-testid="rekap-grand-total">{fmtMetric(view === "pengeluaran" ? "gaji" : view, data.total[view])}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      <p className="font-mono text-[10px] text-muted-foreground mt-2">Klik baris pengurus untuk melihat rincian jam, pendapatan, gaji, sparepart & bersih per bulan. Biaya unit dibebankan ke pengurus dengan jam kerja terbanyak di unit tersebut pada bulan itu.</p>
    </section>
  );
}
