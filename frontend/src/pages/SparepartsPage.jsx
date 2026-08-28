import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, formatIDR } from "@/components/common";
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

const empty = { unit_id: "", nomor_nota: "", nama_sparepart: "", tanggal: format(new Date(), "yyyy-MM-dd"), biaya: "" };

export default function SparepartsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [units, setUnits] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);

  const load = async () => {
    const [s, u] = await Promise.all([api.get("/spareparts"), api.get("/units")]);
    setRows(s.data); setUnits(u.data);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.unit_id || !form.nomor_nota || !form.nama_sparepart || !form.tanggal || form.biaya === "") { toast.error("Lengkapi semua field"); return; }
    try {
      await api.post("/spareparts", { ...form, biaya: Number(form.biaya) });
      toast.success("Sparepart tersimpan"); setOpen(false); setForm(empty); load();
    } catch { toast.error("Gagal menyimpan"); }
  };

  const del = async (id) => {
    if (!window.confirm("Hapus catatan ini?")) return;
    await api.delete(`/spareparts/${id}`); toast.success("Terhapus"); load();
  };

  // Aggregate by unit
  const perUnit = rows.reduce((acc, r) => {
    acc[r.unit_id] = acc[r.unit_id] || { unit_label: r.unit_label, total: 0, count: 0 };
    acc[r.unit_id].total += r.biaya; acc[r.unit_id].count += 1;
    return acc;
  }, {});

  const exportRows = rows.map(r => ({
    Tanggal: r.tanggal, Unit: r.unit_label, "No Nota": r.nomor_nota,
    Sparepart: r.nama_sparepart, Biaya: r.biaya,
  }));

  return (
    <div>
      <PageHeader
        overline="// Maintenance / 04"
        title="Penggantian Sparepart"
        description="Log nota penggantian sparepart per unit. Total biaya sparepart per unit dihitung otomatis untuk pelacakan cost of ownership."
        actions={
          <>
            <Button data-testid="export-excel-sparepart" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "spareparts")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-sparepart" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Laporan Penggantian Sparepart",
                columns: ["Tanggal", "Unit", "No Nota", "Sparepart", "Biaya"],
                rows: rows.map(r => [r.tanggal, r.unit_label, r.nomor_nota, r.nama_sparepart, formatIDR(r.biaya)]),
                filename: "spareparts",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            {isAdmin && (
              <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setForm(empty); }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-sparepart-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                    <PlusIcon size={16} weight="bold" className="mr-1.5" /> Nota Baru
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-sm border-border bg-card">
                  <DialogHeader>
                    <DialogTitle className="font-display font-black tracking-tighter text-2xl">Nota Sparepart Baru</DialogTitle>
                  </DialogHeader>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Unit</Label>
                      <Select value={form.unit_id} onValueChange={(v) => setForm({ ...form, unit_id: v })}>
                        <SelectTrigger data-testid="select-sparepart-unit" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih unit" /></SelectTrigger>
                        <SelectContent>{units.map(u => <SelectItem key={u.id} value={u.id}>{u.unit_name} · {u.nomor_lambung}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">No Nota</Label>
                      <Input data-testid="input-nota" className="rounded-sm mt-1.5" value={form.nomor_nota} onChange={e => setForm({ ...form, nomor_nota: e.target.value })} />
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Tanggal</Label>
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button variant="outline" className="w-full mt-1.5 rounded-sm justify-start font-normal">
                            <CalendarBlankIcon size={14} className="mr-2" />{form.tanggal}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0 rounded-sm">
                          <Calendar mode="single" selected={form.tanggal ? parseISO(form.tanggal) : undefined} onSelect={(d) => setForm({ ...form, tanggal: d ? format(d, "yyyy-MM-dd") : "" })} />
                        </PopoverContent>
                      </Popover>
                    </div>
                    <div className="col-span-2">
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Nama Sparepart</Label>
                      <Input data-testid="input-sparepart-name" className="rounded-sm mt-1.5" placeholder="Contoh: Filter Oli, Bucket Teeth, dll" value={form.nama_sparepart} onChange={e => setForm({ ...form, nama_sparepart: e.target.value })} />
                    </div>
                    <div className="col-span-2">
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Biaya (Rp)</Label>
                      <Input data-testid="input-biaya" type="number" className="rounded-sm mt-1.5" value={form.biaya} onChange={e => setForm({ ...form, biaya: e.target.value })} />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button data-testid="save-sparepart-button" onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">Simpan</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
          </>
        }
      />

      {Object.keys(perUnit).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 mb-8 border border-border" data-testid="sparepart-summary">
          {Object.entries(perUnit).map(([id, agg]) => (
            <div key={id} className="p-5 border-r border-b border-border last:border-r-0">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{agg.unit_label}</p>
              <p className="font-display font-black text-2xl tracking-tighter mt-2 text-primary">{formatIDR(agg.total)}</p>
              <p className="font-mono text-[10px] text-muted-foreground mt-1">{agg.count} nota</p>
            </div>
          ))}
        </div>
      )}

      <div className="border border-border overflow-x-auto" data-testid="sparepart-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Tanggal</th>
              <th className="p-3">Unit</th>
              <th className="p-3">No Nota</th>
              <th className="p-3">Sparepart</th>
              <th className="p-3 text-right">Biaya</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={6} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada catatan</td></tr>}
            {rows.map(r => (
              <tr key={r.id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3 font-mono">{r.tanggal}</td>
                <td className="p-3 font-medium">{r.unit_label}</td>
                <td className="p-3 font-mono text-muted-foreground">{r.nomor_nota}</td>
                <td className="p-3">{r.nama_sparepart}</td>
                <td className="p-3 text-right font-mono text-primary">{formatIDR(r.biaya)}</td>
                {isAdmin && (
                  <td className="p-3 text-right">
                    <button data-testid={`delete-sparepart-${r.id}`} onClick={() => del(r.id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
                      <TrashIcon size={14} weight="bold" />
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
