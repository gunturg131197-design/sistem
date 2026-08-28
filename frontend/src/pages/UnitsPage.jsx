import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { PlusIcon, TrashIcon, PencilSimpleIcon, FileXlsIcon, FilePdfIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";

const empty = { unit_name: "", nomor_lambung: "", serial_number: "", operator_id: "", operator_name: "", pengurus: "" };

export default function UnitsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [units, setUnits] = useState([]);
  const [operators, setOperators] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editId, setEditId] = useState(null);

  const load = async () => {
    const [u, us] = await Promise.all([api.get("/units"), api.get("/users")]);
    setUnits(u.data);
    setOperators(us.data);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.unit_name || !form.nomor_lambung || !form.serial_number) {
      toast.error("Lengkapi semua field wajib");
      return;
    }
    const opUser = operators.find(o => o.user_id === form.operator_id);
    const payload = { ...form, operator_name: opUser?.name || "" };
    try {
      if (editId) await api.patch(`/units/${editId}`, payload);
      else await api.post("/units", payload);
      toast.success("Unit tersimpan");
      setOpen(false); setForm(empty); setEditId(null);
      load();
    } catch { toast.error("Gagal menyimpan unit"); }
  };

  const del = async (id) => {
    if (!window.confirm("Hapus unit ini?")) return;
    await api.delete(`/units/${id}`);
    toast.success("Unit dihapus");
    load();
  };

  const exportRows = units.map(u => ({
    Unit: u.unit_name,
    "Nomor Lambung": u.nomor_lambung,
    "Serial Number": u.serial_number,
    Operator: u.operator_name || "-",
    Pengurus: u.pengurus || "-",
  }));

  return (
    <div>
      <PageHeader
        overline="// Registry / 01"
        title="Unit Excavator"
        description="Daftar armada excavator beserta identifikasi lambung, serial number, dan operator yang bertanggung jawab."
        actions={
          <>
            <Button data-testid="export-excel-units" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "excavator-units")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-units" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Daftar Unit Excavator",
                columns: ["Unit", "Nomor Lambung", "Serial Number", "Operator", "Pengurus"],
                rows: units.map(u => [u.unit_name, u.nomor_lambung, u.serial_number, u.operator_name || "-", u.pengurus || "-"]),
                filename: "excavator-units",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            {isAdmin && (
              <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setForm(empty); setEditId(null); } }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-unit-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                    <PlusIcon size={16} weight="bold" className="mr-1.5" /> Tambah Unit
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-sm border-border bg-card">
                  <DialogHeader>
                    <DialogTitle className="font-display font-black tracking-tighter text-2xl">{editId ? "Edit Unit" : "Tambah Unit Baru"}</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Unit Excavator</Label>
                      <Input data-testid="input-unit-name" className="rounded-sm mt-1.5" placeholder="Contoh: CAT 320D" value={form.unit_name} onChange={e => setForm({ ...form, unit_name: e.target.value })} />
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Nomor Lambung</Label>
                      <Input data-testid="input-lambung" className="rounded-sm mt-1.5" placeholder="EX-001" value={form.nomor_lambung} onChange={e => setForm({ ...form, nomor_lambung: e.target.value })} />
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Serial Number</Label>
                      <Input data-testid="input-serial" className="rounded-sm mt-1.5" placeholder="SN-XXXX" value={form.serial_number} onChange={e => setForm({ ...form, serial_number: e.target.value })} />
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Operator (Opsional)</Label>
                      <Select value={form.operator_id || "none"} onValueChange={(v) => setForm({ ...form, operator_id: v === "none" ? "" : v })}>
                        <SelectTrigger data-testid="select-operator" className="rounded-sm mt-1.5">
                          <SelectValue placeholder="Pilih operator" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">— Tidak ada —</SelectItem>
                          {operators.map(op => <SelectItem key={op.user_id} value={op.user_id}>{op.name} ({op.role})</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Pengurus Unit</Label>
                      <Input data-testid="input-unit-pengurus" className="rounded-sm mt-1.5" placeholder="Nama pengurus / PIC unit" value={form.pengurus} onChange={e => setForm({ ...form, pengurus: e.target.value })} />
                      <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">Penanggung jawab unit di lapangan.</p>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button data-testid="save-unit-button" onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">Simpan</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
          </>
        }
      />

      <div className="border border-border" data-testid="units-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Unit</th>
              <th className="p-3">Nomor Lambung</th>
              <th className="p-3">Serial Number</th>
              <th className="p-3">Operator</th>
              <th className="p-3">Pengurus</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {units.length === 0 && (
              <tr><td colSpan={6} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada unit terdaftar</td></tr>
            )}
            {units.map(u => (
              <tr key={u.id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3 font-medium">{u.unit_name}</td>
                <td className="p-3 font-mono text-primary">{u.nomor_lambung}</td>
                <td className="p-3 font-mono text-muted-foreground">{u.serial_number}</td>
                <td className="p-3">{u.operator_name || <span className="text-muted-foreground">—</span>}</td>
                <td className="p-3">{u.pengurus || <span className="text-muted-foreground">—</span>}</td>
                {isAdmin && (
                  <td className="p-3 text-right">
                    <div className="inline-flex gap-1">
                      <button data-testid={`edit-unit-${u.id}`} onClick={() => { setForm({ unit_name: u.unit_name, nomor_lambung: u.nomor_lambung, serial_number: u.serial_number, operator_id: u.operator_id || "", operator_name: u.operator_name || "", pengurus: u.pengurus || "" }); setEditId(u.id); setOpen(true); }} className="p-1.5 border border-border hover:border-primary hover:text-primary">
                        <PencilSimpleIcon size={14} weight="bold" />
                      </button>
                      <button data-testid={`delete-unit-${u.id}`} onClick={() => del(u.id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
                        <TrashIcon size={14} weight="bold" />
                      </button>
                    </div>
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
