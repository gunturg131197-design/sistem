import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { PlusIcon, TrashIcon, CalendarBlankIcon, FileXlsIcon, FilePdfIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";
import { format, parseISO } from "date-fns";

const empty = { unit_id: "", tanggal: format(new Date(), "yyyy-MM-dd"), hour_meter_awal: "", hour_meter_akhir: "", jumlah_cars: "", pengurus: "" };

export default function OperationsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [units, setUnits] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);

  const load = async () => {
    const [ops, u] = await Promise.all([api.get("/operations"), api.get("/units")]);
    setRows(ops.data); setUnits(u.data);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.unit_id || !form.tanggal || form.hour_meter_awal === "" || form.hour_meter_akhir === "" || form.jumlah_cars === "") {
      toast.error("Lengkapi semua field"); return;
    }
    if (Number(form.hour_meter_akhir) < Number(form.hour_meter_awal)) {
      toast.error("HM akhir harus ≥ HM awal"); return;
    }
    try {
      await api.post("/operations", {
        unit_id: form.unit_id,
        tanggal: form.tanggal,
        hour_meter_awal: Number(form.hour_meter_awal),
        hour_meter_akhir: Number(form.hour_meter_akhir),
        jumlah_cars: Number(form.jumlah_cars),
        pengurus: form.pengurus || "",
      });
      toast.success("Laporan operasional tersimpan");
      setOpen(false); setForm(empty); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
  };

  const del = async (id) => {
    if (!window.confirm("Hapus laporan ini?")) return;
    await api.delete(`/operations/${id}`); toast.success("Terhapus"); load();
  };

  const exportRows = rows.map(r => ({
    Tanggal: r.tanggal, Unit: r.unit_label, Operator: r.operator_name,
    Pengurus: r.pengurus || "-",
    "HM Awal": r.hour_meter_awal, "HM Akhir": r.hour_meter_akhir,
    "Total Jam": r.total_jam, "Jumlah Cars": r.jumlah_cars,
  }));

  return (
    <div>
      <PageHeader
        overline="// Ops Report / 02"
        title="Laporan Operasional"
        description="Rekam hour meter awal & akhir, jumlah cars yang diproduksi, dan tanggal operasi. Total jam kerja dihitung otomatis."
        actions={
          <>
            <Button data-testid="export-excel-ops" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "operations-report")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-ops" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Laporan Operasional Excavator",
                columns: ["Tanggal", "Unit", "Operator", "Pengurus", "HM Awal", "HM Akhir", "Total Jam", "Cars"],
                rows: rows.map(r => [r.tanggal, r.unit_label, r.operator_name, r.pengurus || "-", r.hour_meter_awal, r.hour_meter_akhir, r.total_jam, r.jumlah_cars]),
                filename: "operations-report",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setForm(empty); }}>
              <DialogTrigger asChild>
                <Button data-testid="add-operation-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                  <PlusIcon size={16} weight="bold" className="mr-1.5" /> Laporan Baru
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-sm border-border bg-card">
                <DialogHeader>
                  <DialogTitle className="font-display font-black tracking-tighter text-2xl">Laporan Operasional Baru</DialogTitle>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Unit</Label>
                    <Select value={form.unit_id} onValueChange={(v) => setForm({ ...form, unit_id: v })}>
                      <SelectTrigger data-testid="select-op-unit" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih unit" /></SelectTrigger>
                      <SelectContent>
                        {units.map(u => <SelectItem key={u.id} value={u.id}>{u.unit_name} · {u.nomor_lambung}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-2">
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Tanggal Cars</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button data-testid="select-op-date" variant="outline" className="w-full mt-1.5 rounded-sm justify-start font-normal">
                          <CalendarBlankIcon size={16} className="mr-2" />
                          {form.tanggal || "Pilih tanggal"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0 rounded-sm">
                        <Calendar mode="single" selected={form.tanggal ? parseISO(form.tanggal) : undefined} onSelect={(d) => setForm({ ...form, tanggal: d ? format(d, "yyyy-MM-dd") : "" })} />
                      </PopoverContent>
                    </Popover>
                  </div>
                  <div>
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">HM Awal</Label>
                    <Input data-testid="input-hm-awal" type="number" step="0.1" className="rounded-sm mt-1.5" value={form.hour_meter_awal} onChange={e => setForm({ ...form, hour_meter_awal: e.target.value })} />
                  </div>
                  <div>
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">HM Akhir</Label>
                    <Input data-testid="input-hm-akhir" type="number" step="0.1" className="rounded-sm mt-1.5" value={form.hour_meter_akhir} onChange={e => setForm({ ...form, hour_meter_akhir: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Jumlah Cars Baru</Label>
                    <Input data-testid="input-jumlah-cars" type="number" className="rounded-sm mt-1.5" value={form.jumlah_cars} onChange={e => setForm({ ...form, jumlah_cars: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Pengurus Cars</Label>
                    <Input data-testid="input-op-pengurus" className="rounded-sm mt-1.5" placeholder="Nama pengurus / PIC cars produksi hari ini" value={form.pengurus} onChange={e => setForm({ ...form, pengurus: e.target.value })} />
                  </div>
                  {form.hour_meter_awal !== "" && form.hour_meter_akhir !== "" && (
                    <div className="col-span-2 border border-primary/40 bg-primary/5 p-3">
                      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Auto Calculation</p>
                      <p className="font-display font-black text-2xl tracking-tighter mt-1 text-primary">
                        {Math.max(0, Number(form.hour_meter_akhir) - Number(form.hour_meter_awal)).toFixed(2)} <span className="text-sm font-normal font-mono">HRS</span>
                      </p>
                    </div>
                  )}
                </div>
                <DialogFooter>
                  <Button data-testid="save-operation-button" onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">Simpan Laporan</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      <div className="border border-border overflow-x-auto" data-testid="operations-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Tanggal</th>
              <th className="p-3">Unit</th>
              <th className="p-3">Operator</th>
              <th className="p-3">Pengurus</th>
              <th className="p-3 text-right">HM Awal</th>
              <th className="p-3 text-right">HM Akhir</th>
              <th className="p-3 text-right">Total Jam</th>
              <th className="p-3 text-right">Cars</th>
              <th className="p-3 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={9} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada laporan</td></tr>}
            {rows.map(r => (
              <tr key={r.id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3 font-mono">{r.tanggal}</td>
                <td className="p-3 font-medium">{r.unit_label}</td>
                <td className="p-3 text-muted-foreground">{r.operator_name}</td>
                <td className="p-3">{r.pengurus || <span className="text-muted-foreground">—</span>}</td>
                <td className="p-3 text-right font-mono">{r.hour_meter_awal}</td>
                <td className="p-3 text-right font-mono">{r.hour_meter_akhir}</td>
                <td className="p-3 text-right font-mono text-primary">{r.total_jam}</td>
                <td className="p-3 text-right font-mono">{r.jumlah_cars}</td>
                <td className="p-3 text-right">
                  {(user?.role === "admin" || user?.user_id === r.operator_id) && (
                    <button data-testid={`delete-op-${r.id}`} onClick={() => del(r.id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
                      <TrashIcon size={14} weight="bold" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
