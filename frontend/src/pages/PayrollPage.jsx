import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, formatIDR } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { PlusIcon, TrashIcon, FileXlsIcon, FilePdfIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";

const empty = { operator_id: "", periode: new Date().toISOString().slice(0, 7), gaji: "", kasbon: "" };

export default function PayrollPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [operators, setOperators] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);

  const load = async () => {
    const [p, u] = await Promise.all([api.get("/payroll"), api.get("/users")]);
    setRows(p.data); setOperators(u.data);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.operator_id || !form.periode || form.gaji === "" || form.kasbon === "") { toast.error("Lengkapi semua field"); return; }
    try {
      await api.post("/payroll", {
        operator_id: form.operator_id, periode: form.periode,
        gaji: Number(form.gaji), kasbon: Number(form.kasbon),
      });
      toast.success("Payroll tersimpan"); setOpen(false); setForm(empty); load();
    } catch { toast.error("Gagal menyimpan"); }
  };

  const del = async (id) => {
    if (!window.confirm("Hapus payroll ini?")) return;
    await api.delete(`/payroll/${id}`); toast.success("Terhapus"); load();
  };

  const exportRows = rows.map(r => ({
    Periode: r.periode, Operator: r.operator_name,
    Gaji: r.gaji, Kasbon: r.kasbon, "Gaji Bersih": r.gaji_bersih,
  }));

  return (
    <div>
      <PageHeader
        overline="// Payroll / 03"
        title="Gaji & Kasbon Operator"
        description="Manajemen gaji dan kasbon operator per periode. Gaji bersih dihitung otomatis = Gaji − Kasbon."
        actions={
          <>
            <Button data-testid="export-excel-payroll" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "payroll")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-payroll" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Rekap Gaji Operator",
                columns: ["Periode", "Operator", "Gaji", "Kasbon", "Gaji Bersih"],
                rows: rows.map(r => [r.periode, r.operator_name, formatIDR(r.gaji), formatIDR(r.kasbon), formatIDR(r.gaji_bersih)]),
                filename: "payroll",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            {isAdmin && (
              <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setForm(empty); }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-payroll-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                    <PlusIcon size={16} weight="bold" className="mr-1.5" /> Payroll Baru
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-sm border-border bg-card">
                  <DialogHeader>
                    <DialogTitle className="font-display font-black tracking-tighter text-2xl">Payroll Baru</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Operator</Label>
                      <Select value={form.operator_id} onValueChange={(v) => setForm({ ...form, operator_id: v })}>
                        <SelectTrigger data-testid="select-payroll-operator" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih operator" /></SelectTrigger>
                        <SelectContent>{operators.map(o => <SelectItem key={o.user_id} value={o.user_id}>{o.name}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Periode (YYYY-MM)</Label>
                      <Input data-testid="input-periode" type="month" className="rounded-sm mt-1.5" value={form.periode} onChange={e => setForm({ ...form, periode: e.target.value })} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Gaji (Rp)</Label>
                        <Input data-testid="input-gaji" type="number" className="rounded-sm mt-1.5" value={form.gaji} onChange={e => setForm({ ...form, gaji: e.target.value })} />
                      </div>
                      <div>
                        <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Kasbon (Rp)</Label>
                        <Input data-testid="input-kasbon" type="number" className="rounded-sm mt-1.5" value={form.kasbon} onChange={e => setForm({ ...form, kasbon: e.target.value })} />
                      </div>
                    </div>
                    {form.gaji !== "" && form.kasbon !== "" && (
                      <div className="border border-primary/40 bg-primary/5 p-3">
                        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Gaji Bersih</p>
                        <p className="font-display font-black text-2xl tracking-tighter mt-1 text-primary">{formatIDR(Number(form.gaji) - Number(form.kasbon))}</p>
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
              <th className="p-3 text-right">Gaji</th>
              <th className="p-3 text-right">Kasbon</th>
              <th className="p-3 text-right">Gaji Bersih</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={6} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada payroll</td></tr>}
            {rows.map(r => (
              <tr key={r.id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3 font-mono text-primary">{r.periode}</td>
                <td className="p-3 font-medium">{r.operator_name}</td>
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
