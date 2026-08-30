import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, formatIDR, CurrencyInput } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { PlusIcon, TrashIcon, FileXlsIcon, FilePdfIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";

const empty = () => ({ operator_id: "", unit_id: "", periode: new Date().toISOString().slice(0, 7), tarif_per_jam: "", jam_dibayar: "", kasbon: "" });

export default function PayrollPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [operators, setOperators] = useState([]);
  const [units, setUnits] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty());
  const [hours, setHours] = useState(null); // {total_jam_kerja,total_jam_dibayar,jam_belum_dibayar}
  const [loadingHours, setLoadingHours] = useState(false);

  const load = async () => {
    const [p, u, un] = await Promise.all([api.get("/payroll"), api.get("/users"), api.get("/units")]);
    setRows(p.data); setOperators(u.data); setUnits(un.data);
  };
  useEffect(() => { load(); }, []);

  // Ambil jam kerja saat operator + unit dipilih
  useEffect(() => {
    const fetchHours = async () => {
      if (!form.operator_id || !form.unit_id) { setHours(null); return; }
      setLoadingHours(true);
      try {
        const { data } = await api.get("/payroll/hours", { params: { operator_id: form.operator_id, unit_id: form.unit_id } });
        setHours(data);
        // default jam dibayar = sisa jam belum dibayar
        setForm((f) => ({ ...f, jam_dibayar: f.jam_dibayar === "" ? String(data.jam_belum_dibayar) : f.jam_dibayar }));
      } catch { setHours(null); }
      finally { setLoadingHours(false); }
    };
    fetchHours();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.operator_id, form.unit_id]);

  const gaji = (Number(form.jam_dibayar) || 0) * (Number(form.tarif_per_jam) || 0);
  const gajiBersih = gaji - (Number(form.kasbon) || 0);

  const save = async () => {
    if (!form.operator_id || !form.unit_id || !form.periode || form.tarif_per_jam === "" || form.jam_dibayar === "") {
      toast.error("Lengkapi operator, unit, periode, tarif & jam dibayar"); return;
    }
    try {
      await api.post("/payroll", {
        operator_id: form.operator_id,
        unit_id: form.unit_id,
        periode: form.periode,
        tarif_per_jam: Number(form.tarif_per_jam),
        jam_dibayar: Number(form.jam_dibayar),
        kasbon: Number(form.kasbon) || 0,
      });
      toast.success("Payroll tersimpan"); setOpen(false); setForm(empty()); setHours(null); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
  };

  const del = async (id) => {
    if (!window.confirm("Hapus payroll ini?")) return;
    await api.delete(`/payroll/${id}`); toast.success("Terhapus"); load();
  };

  const exportRows = rows.map(r => ({
    Periode: r.periode, Operator: r.operator_name, Unit: r.unit_label || "-",
    "Tarif/Jam": r.tarif_per_jam || 0, "Jam Kerja": r.jam_kerja || 0, "Jam Dibayar": r.jam_dibayar || 0,
    Gaji: r.gaji, Kasbon: r.kasbon, "Gaji Bersih": r.gaji_bersih,
  }));

  return (
    <div>
      <PageHeader
        overline="// Payroll / 03"
        title="Gaji & Kasbon Operator"
        description="Gaji dihitung per jam: Gaji = Jam Dibayar × Tarif/Jam. Jam kerja disinkron otomatis dari Ops Report (HM akhir − HM awal) per operator & unit."
        actions={
          <>
            <Button data-testid="export-excel-payroll" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "payroll")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-payroll" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Rekap Gaji Operator",
                columns: ["Periode", "Operator", "Unit", "Tarif/Jam", "Jam Kerja", "Jam Dibayar", "Gaji", "Kasbon", "Gaji Bersih"],
                rows: rows.map(r => [r.periode, r.operator_name, r.unit_label || "-", formatIDR(r.tarif_per_jam), r.jam_kerja, r.jam_dibayar, formatIDR(r.gaji), formatIDR(r.kasbon), formatIDR(r.gaji_bersih)]),
                filename: "payroll",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            {isAdmin && (
              <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setForm(empty()); setHours(null); } }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-payroll-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                    <PlusIcon size={16} weight="bold" className="mr-1.5" /> Payroll Baru
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-sm border-border bg-card max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="font-display font-black tracking-tighter text-2xl">Payroll Baru</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Operator</Label>
                        <Select value={form.operator_id} onValueChange={(v) => setForm({ ...form, operator_id: v, jam_dibayar: "" })}>
                          <SelectTrigger data-testid="select-payroll-operator" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih operator" /></SelectTrigger>
                          <SelectContent>{operators.map(o => <SelectItem key={o.user_id} value={o.user_id}>{o.name}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Unit yang Dibawa</Label>
                        <Select value={form.unit_id} onValueChange={(v) => setForm({ ...form, unit_id: v, jam_dibayar: "" })}>
                          <SelectTrigger data-testid="select-payroll-unit" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih unit" /></SelectTrigger>
                          <SelectContent>{units.map(u => <SelectItem key={u.id} value={u.id}>{u.unit_name} · {u.nomor_lambung}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Ringkasan jam kerja */}
                    {(form.operator_id && form.unit_id) && (
                      <div className="grid grid-cols-3 gap-0 border border-border" data-testid="hours-summary">
                        <div className="p-3 border-r border-border">
                          <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">Total Jam Kerja</p>
                          <p className="font-display font-black text-lg tracking-tighter mt-1">{loadingHours ? "…" : (hours?.total_jam_kerja ?? 0)}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">HRS</span></p>
                        </div>
                        <div className="p-3 border-r border-border">
                          <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">Sudah Dibayar</p>
                          <p className="font-display font-black text-lg tracking-tighter mt-1 text-accent">{loadingHours ? "…" : (hours?.total_jam_dibayar ?? 0)}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">HRS</span></p>
                        </div>
                        <div className="p-3">
                          <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">Belum Dibayar</p>
                          <p className="font-display font-black text-lg tracking-tighter mt-1 text-primary">{loadingHours ? "…" : (hours?.jam_belum_dibayar ?? 0)}<span className="text-[10px] font-mono font-normal text-muted-foreground ml-1">HRS</span></p>
                        </div>
                      </div>
                    )}

                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Periode (YYYY-MM)</Label>
                      <Input data-testid="input-periode" type="month" className="rounded-sm mt-1.5" value={form.periode} onChange={e => setForm({ ...form, periode: e.target.value })} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Tarif per Jam</Label>
                        <CurrencyInput data-testid="input-tarif" className="rounded-sm mt-1.5" placeholder="Rp 0" value={form.tarif_per_jam} onChange={(v) => setForm({ ...form, tarif_per_jam: v })} />
                      </div>
                      <div>
                        <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Jam Dibayar (HRS)</Label>
                        <Input data-testid="input-jam-dibayar" type="number" step="0.1" min="0" className="rounded-sm mt-1.5" value={form.jam_dibayar} onChange={e => setForm({ ...form, jam_dibayar: e.target.value })} />
                      </div>
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Kasbon</Label>
                      <CurrencyInput data-testid="input-kasbon" className="rounded-sm mt-1.5" placeholder="Rp 0" value={form.kasbon} onChange={(v) => setForm({ ...form, kasbon: v })} />
                    </div>

                    {form.tarif_per_jam !== "" && form.jam_dibayar !== "" && (
                      <div className="border border-primary/40 bg-primary/5 p-3 space-y-1">
                        <div className="flex justify-between items-baseline">
                          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Gaji ({form.jam_dibayar} HRS × {formatIDR(form.tarif_per_jam)})</p>
                          <p className="font-mono text-sm">{formatIDR(gaji)}</p>
                        </div>
                        <div className="flex justify-between items-baseline">
                          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Kasbon</p>
                          <p className="font-mono text-sm text-accent">− {formatIDR(Number(form.kasbon) || 0)}</p>
                        </div>
                        <div className="flex justify-between items-baseline pt-1 border-t border-primary/30">
                          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Gaji Bersih</p>
                          <p className="font-display font-black text-2xl tracking-tighter text-primary" data-testid="gaji-bersih-preview">{formatIDR(gajiBersih)}</p>
                        </div>
                      </div>
                    )}
                  </div>
                  <DialogFooter>
                    <Button data-testid="save-payroll-button" onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">Simpan</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
          </>
        }
      />

      <div className="border border-border overflow-x-auto" data-testid="payroll-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Periode</th>
              <th className="p-3">Operator</th>
              <th className="p-3">Unit</th>
              <th className="p-3 text-right">Tarif/Jam</th>
              <th className="p-3 text-right">Jam Kerja</th>
              <th className="p-3 text-right">Jam Dibayar</th>
              <th className="p-3 text-right">Gaji</th>
              <th className="p-3 text-right">Kasbon</th>
              <th className="p-3 text-right">Gaji Bersih</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={isAdmin ? 10 : 9} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada payroll</td></tr>}
            {rows.map(r => (
              <tr key={r.id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3 font-mono text-primary whitespace-nowrap">{r.periode}</td>
                <td className="p-3 font-medium">{r.operator_name}</td>
                <td className="p-3 text-muted-foreground">{r.unit_label || "—"}</td>
                <td className="p-3 text-right font-mono">{formatIDR(r.tarif_per_jam)}</td>
                <td className="p-3 text-right font-mono">{r.jam_kerja ?? 0}</td>
                <td className="p-3 text-right font-mono">{r.jam_dibayar ?? 0}</td>
                <td className="p-3 text-right font-mono">{formatIDR(r.gaji)}</td>
                <td className="p-3 text-right font-mono text-accent">{formatIDR(r.kasbon)}</td>
                <td className="p-3 text-right font-mono font-semibold">{formatIDR(r.gaji_bersih)}</td>
                {isAdmin && (
                  <td className="p-3 text-right">
                    <button data-testid={`delete-payroll-${r.id}`} onClick={() => del(r.id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
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
