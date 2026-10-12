import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, StatusBadge, UNIT_STATUSES, CurrencyInput } from "@/components/common";
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
import PengurusCombobox from "@/components/PengurusCombobox";

const empty = {
  unit_name: "", nomor_lambung: "", serial_number: "", operator_id: "", operator_name: "", pengurus: "",
  merek_type: "", pemilik_alat: "", nama_proyek: "", lokasi_proyek: "", pengawas_lapangan: "", status: "Aktif",
  tarif_sewa_per_jam: "",
};
const FIELD_KEYS = Object.keys(empty);

function SectionTitle({ children, hint }) {
  return (
    <div className="col-span-2 flex items-end justify-between border-b border-border pb-1.5 mt-2">
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">{children}</p>
      {hint && <p className="font-mono text-[9px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function Field({ label, children, full }) {
  return (
    <div className={full ? "col-span-2" : "col-span-2 sm:col-span-1"}>
      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

export default function UnitsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [units, setUnits] = useState([]);
  const [operators, setOperators] = useState([]);
  const [pengurusOptions, setPengurusOptions] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editId, setEditId] = useState(null);

  const load = async () => {
    const [u, us, pg] = await Promise.all([
      api.get("/units"), api.get("/users"), api.get("/pengurus"),
    ]);
    setUnits(u.data);
    setOperators(us.data);
    setPengurusOptions(pg.data);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.unit_name || !form.nomor_lambung || !form.serial_number) {
      toast.error("Lengkapi semua field wajib");
      return;
    }
    const opUser = operators.find(o => o.user_id === form.operator_id);
    const payload = { ...form, operator_name: opUser?.name || "", tarif_sewa_per_jam: Number(form.tarif_sewa_per_jam || 0) };
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
    "Merek / Type": u.merek_type || "-",
    Status: u.status || "Aktif",
    "Pemilik Alat": u.pemilik_alat || "-",
    "Nama Proyek": u.nama_proyek || "-",
    "Lokasi Proyek": u.lokasi_proyek || "-",
    "Pengawas Lapangan": u.pengawas_lapangan || "-",
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
                columns: ["Unit", "Merek / Type", "No Lambung", "Serial", "Operator", "Proyek", "Lokasi"],
                rows: units.map(u => [u.unit_name, u.merek_type || "-", u.nomor_lambung, u.serial_number, u.operator_name || "-", u.nama_proyek || "-", u.lokasi_proyek || "-"]),
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
                <DialogContent className="rounded-sm border-border bg-card max-w-2xl max-h-[88vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="font-display font-black tracking-tighter text-2xl">{editId ? "Edit Unit" : "Tambah Unit Baru"}</DialogTitle>
                  </DialogHeader>
                  <div className="grid grid-cols-2 gap-3">
                    <SectionTitle hint="Identitas Alat · Form Hour Meter">// Identitas Alat</SectionTitle>
                    <Field label="Nama Alat / Unit Excavator *">
                      <Input data-testid="input-unit-name" className="rounded-sm mt-1.5" placeholder="Contoh: Excavator PC200" value={form.unit_name} onChange={e => setForm({ ...form, unit_name: e.target.value })} />
                    </Field>
                    <Field label="Merek / Type">
                      <Input data-testid="input-merek-type" className="rounded-sm mt-1.5" placeholder="Komatsu / PC200-8" value={form.merek_type} onChange={e => setForm({ ...form, merek_type: e.target.value })} />
                    </Field>
                    <Field label="Nomor Unit / Lambung *">
                      <Input data-testid="input-lambung" className="rounded-sm mt-1.5" placeholder="EX-001" value={form.nomor_lambung} onChange={e => setForm({ ...form, nomor_lambung: e.target.value })} />
                    </Field>
                    <Field label="Serial Number *">
                      <Input data-testid="input-serial" className="rounded-sm mt-1.5" placeholder="SN-XXXX" value={form.serial_number} onChange={e => setForm({ ...form, serial_number: e.target.value })} />
                    </Field>
                    <Field label="Status Unit">
                      <Select value={form.status || "Aktif"} onValueChange={(v) => setForm({ ...form, status: v })}>
                        <SelectTrigger data-testid="select-unit-status" className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {UNIT_STATUSES.map(st => <SelectItem key={st} value={st} data-testid={`unit-status-option-${st.replace(/\s+/g, "-").toLowerCase()}`}>{st}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Pemilik Alat">
                      <Input data-testid="input-pemilik-alat" className="rounded-sm mt-1.5" placeholder="CV. Trirara Tunggal Putra / nama pemilik" value={form.pemilik_alat} onChange={e => setForm({ ...form, pemilik_alat: e.target.value })} />
                    </Field>

                    <Field label="Tarif Sewa per Jam">
                      <CurrencyInput data-testid="input-unit-tarif" className="rounded-sm mt-1.5" placeholder="Rp 0 (pakai tarif pengurus)" value={form.tarif_sewa_per_jam} onChange={(v) => setForm({ ...form, tarif_sewa_per_jam: v })} />
                    </Field>

                    <SectionTitle hint="Data Umum · Form Hour Meter">// Data Proyek</SectionTitle>
                    <Field label="Nama Proyek" full>
                      <Input data-testid="input-nama-proyek" className="rounded-sm mt-1.5" placeholder="Contoh: Normalisasi Sungai" value={form.nama_proyek} onChange={e => setForm({ ...form, nama_proyek: e.target.value })} />
                    </Field>
                    <Field label="Lokasi Proyek">
                      <Input data-testid="input-lokasi-proyek" className="rounded-sm mt-1.5" placeholder="Kota / Kabupaten" value={form.lokasi_proyek} onChange={e => setForm({ ...form, lokasi_proyek: e.target.value })} />
                    </Field>
                    <Field label="Pengawas Lapangan">
                      <Input data-testid="input-pengawas-lapangan" className="rounded-sm mt-1.5" placeholder="Nama pengawas" value={form.pengawas_lapangan} onChange={e => setForm({ ...form, pengawas_lapangan: e.target.value })} />
                    </Field>

                    <SectionTitle>// Operator & Pengurus</SectionTitle>
                    <Field label="Operator (Opsional)">
                      <Select value={form.operator_id || "none"} onValueChange={(v) => setForm({ ...form, operator_id: v === "none" ? "" : v })}>
                        <SelectTrigger data-testid="select-operator" className="rounded-sm mt-1.5">
                          <SelectValue placeholder="Pilih operator" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">— Tidak ada —</SelectItem>
                          {operators.map(op => <SelectItem key={op.user_id} value={op.user_id}>{op.name} ({op.role})</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Pengurus Unit">
                      <PengurusCombobox
                        testid="input-unit-pengurus"
                        value={form.pengurus}
                        onChange={(v) => setForm({ ...form, pengurus: v })}
                        options={pengurusOptions}
                        placeholder="Pilih / ketik pengurus…"
                      />
                    </Field>
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

      <div className="border border-border overflow-x-auto bg-card" data-testid="units-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Unit</th>
              <th className="p-3">Merek / Type</th>
              <th className="p-3">Status</th>
              <th className="p-3">Nomor Lambung</th>
              <th className="p-3">Serial Number</th>
              <th className="p-3">Operator</th>
              <th className="p-3">Proyek</th>
              <th className="p-3">Pengurus</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {units.length === 0 && (
              <tr><td colSpan={9} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada unit terdaftar</td></tr>
            )}
            {units.map(u => (
              <tr key={u.id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3 font-medium">{u.unit_name}</td>
                <td className="p-3 text-muted-foreground">{u.merek_type || "—"}</td>
                <td className="p-3"><StatusBadge status={u.status} testid={`unit-row-status-${u.id}`} /></td>
                <td className="p-3 font-mono text-primary">{u.nomor_lambung}</td>
                <td className="p-3 font-mono text-muted-foreground">{u.serial_number}</td>
                <td className="p-3">{u.operator_name || <span className="text-muted-foreground">—</span>}</td>
                <td className="p-3">
                  {u.nama_proyek ? (
                    <div>
                      <p className="text-sm">{u.nama_proyek}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">{[u.lokasi_proyek, u.pengawas_lapangan && `Pengawas: ${u.pengawas_lapangan}`].filter(Boolean).join(" · ")}</p>
                    </div>
                  ) : <span className="text-muted-foreground">—</span>}
                </td>
                <td className="p-3">{u.pengurus || <span className="text-muted-foreground">—</span>}</td>
                {isAdmin && (
                  <td className="p-3 text-right">
                    <div className="inline-flex gap-1">
                      <button data-testid={`edit-unit-${u.id}`} onClick={() => { setForm({ ...Object.fromEntries(FIELD_KEYS.map(k => [k, u[k] || ""])), status: u.status || "Aktif" }); setEditId(u.id); setOpen(true); }} className="p-1.5 border border-border hover:border-primary hover:text-primary">
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
