import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { PlusIcon, TrashIcon, CalendarBlankIcon, FileXlsIcon, FilePdfIcon, PencilSimpleIcon, CheckIcon, XIcon, WarningIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";
import { KONDISI_ITEMS } from "@/lib/hourMeter";
import { format, parseISO } from "date-fns";
import PengurusCombobox from "@/components/PengurusCombobox";

const emptyKondisi = () => Object.fromEntries(KONDISI_ITEMS.map(([k]) => [k, { status: "", keterangan: "" }]));
const makeEmpty = () => ({
  unit_id: "", tanggal: format(new Date(), "yyyy-MM-dd"), hour_meter_awal: "", hour_meter_akhir: "", jumlah_cars: "", pengurus: "",
  keterangan: "", downtime_jam: "", solar_liter: "", catatan_operator: "", kondisi_alat: emptyKondisi(),
});

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";

function kondisiSummary(ka) {
  const vals = Object.values(ka || {});
  const filled = vals.filter(v => v && v.status);
  const bad = filled.filter(v => v.status === "tidak").length;
  return { filled: filled.length, bad };
}

export default function OperationsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [units, setUnits] = useState([]);
  const [pengurusOptions, setPengurusOptions] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(makeEmpty());
  const [editId, setEditId] = useState(null);
  const [tab, setTab] = useState("umum");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const [ops, u, pg] = await Promise.all([api.get("/operations"), api.get("/units"), api.get("/pengurus")]);
      setRows(ops.data); setUnits(u.data); setPengurusOptions(pg.data);
    } catch { toast.error("Gagal memuat data"); }
  };
  useEffect(() => { load(); }, []);

  const setK = (key, patch) => setForm(f => ({ ...f, kondisi_alat: { ...f.kondisi_alat, [key]: { ...f.kondisi_alat[key], ...patch } } }));

  const openNew = () => { setForm(makeEmpty()); setEditId(null); setTab("umum"); setOpen(true); };
  const openEdit = (r) => {
    setForm({
      unit_id: r.unit_id, tanggal: r.tanggal, hour_meter_awal: r.hour_meter_awal, hour_meter_akhir: r.hour_meter_akhir,
      jumlah_cars: r.jumlah_cars, pengurus: r.pengurus || "", keterangan: r.keterangan || "",
      downtime_jam: r.downtime_jam ?? "", solar_liter: r.solar_liter ?? "", catatan_operator: r.catatan_operator || "",
      kondisi_alat: { ...emptyKondisi(), ...(r.kondisi_alat || {}) },
    });
    setEditId(r.id); setTab("umum"); setOpen(true);
  };

  const save = async () => {
    if (!form.unit_id || !form.tanggal || form.hour_meter_awal === "" || form.hour_meter_akhir === "" || form.jumlah_cars === "") {
      setTab("umum"); toast.error("Lengkapi field wajib di tab Umum"); return;
    }
    if (Number(form.hour_meter_akhir) < Number(form.hour_meter_awal)) { setTab("umum"); toast.error("HM akhir harus ≥ HM awal"); return; }
    const payload = {
      unit_id: form.unit_id,
      tanggal: form.tanggal,
      hour_meter_awal: Number(form.hour_meter_awal),
      hour_meter_akhir: Number(form.hour_meter_akhir),
      jumlah_cars: Number(form.jumlah_cars),
      pengurus: form.pengurus || "",
      keterangan: form.keterangan || "",
      downtime_jam: form.downtime_jam === "" ? 0 : Number(form.downtime_jam),
      solar_liter: form.solar_liter === "" ? 0 : Number(form.solar_liter),
      catatan_operator: form.catatan_operator || "",
      kondisi_alat: form.kondisi_alat,
    };
    setSaving(true);
    try {
      if (editId) await api.patch(`/operations/${editId}`, payload);
      else await api.post("/operations", payload);
      toast.success(editId ? "Laporan diperbarui" : "Laporan operasional tersimpan");
      setOpen(false); setForm(makeEmpty()); setEditId(null); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
    finally { setSaving(false); }
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
    "Downtime (Jam)": r.downtime_jam || 0, "Solar (Liter)": r.solar_liter || 0,
    Keterangan: r.keterangan || "", "Catatan Operator": r.catatan_operator || "",
  }));

  const ks = kondisiSummary(form.kondisi_alat);

  return (
    <div>
      <PageHeader
        overline="// Ops Report / 02"
        title="Laporan Operasional"
        description="Form hour meter harian operator: HM awal & akhir, cars, downtime, pemakaian solar, kondisi alat, dan catatan. Total jam kerja dihitung otomatis."
        actions={
          <>
            <Button data-testid="export-excel-ops" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "operations-report")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-ops" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Laporan Operasional Harian",
                columns: ["Tanggal", "Unit", "Operator", "HM Awal", "HM Akhir", "Total Jam", "Cars", "Downtime", "Solar (L)", "Keterangan"],
                rows: rows.map(r => [r.tanggal, r.unit_label, r.operator_name, r.hour_meter_awal, r.hour_meter_akhir, r.total_jam, r.jumlah_cars, r.downtime_jam || 0, r.solar_liter || 0, r.keterangan || "-"]),
                filename: "operations-report",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setForm(makeEmpty()); setEditId(null); } }}>
              <DialogTrigger asChild>
                <Button data-testid="add-operation-button" onClick={openNew} className="rounded-sm bg-primary hover:bg-primary/90 text-primary-foreground hover:text-primary-foreground font-display tracking-tight">
                  <PlusIcon size={16} weight="bold" className="mr-1.5" /> Laporan Baru
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-sm border-border bg-card max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="font-display font-black tracking-tighter text-2xl">{editId ? "Edit Laporan Harian" : "Laporan Operasional Baru"}</DialogTitle>
                  <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Form Hour Meter Harian Operator</p>
                </DialogHeader>

                <Tabs value={tab} onValueChange={setTab}>
                  <TabsList className="grid grid-cols-4 w-full rounded-sm bg-background border border-border h-auto p-1">
                    <TabsTrigger data-testid="ops-tab-umum" value="umum" className="rounded-sm text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Umum</TabsTrigger>
                    <TabsTrigger data-testid="ops-tab-operasional" value="operasional" className="rounded-sm text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Operasional</TabsTrigger>
                    <TabsTrigger data-testid="ops-tab-kondisi" value="kondisi" className="rounded-sm text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                      Kondisi Alat {ks.bad > 0 && <span className="ml-1 h-1.5 w-1.5 bg-accent inline-block" />}
                    </TabsTrigger>
                    <TabsTrigger data-testid="ops-tab-catatan" value="catatan" className="rounded-sm text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Catatan</TabsTrigger>
                  </TabsList>

                  {/* UMUM */}
                  <TabsContent value="umum" className="mt-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="col-span-2">
                        <Label className={lbl}>Unit *</Label>
                        <Select value={form.unit_id} onValueChange={(v) => setForm({ ...form, unit_id: v })}>
                          <SelectTrigger data-testid="select-op-unit" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih unit" /></SelectTrigger>
                          <SelectContent>
                            {units.map(u => <SelectItem key={u.id} value={u.id}>{u.unit_name} · {u.nomor_lambung}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="col-span-2">
                        <Label className={lbl}>Tanggal *</Label>
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
                        <Label className={lbl}>HM Awal *</Label>
                        <Input data-testid="input-hm-awal" type="number" step="0.1" className="rounded-sm mt-1.5" value={form.hour_meter_awal} onChange={e => setForm({ ...form, hour_meter_awal: e.target.value })} />
                      </div>
                      <div>
                        <Label className={lbl}>HM Akhir *</Label>
                        <Input data-testid="input-hm-akhir" type="number" step="0.1" className="rounded-sm mt-1.5" value={form.hour_meter_akhir} onChange={e => setForm({ ...form, hour_meter_akhir: e.target.value })} />
                      </div>
                      <div className="col-span-2">
                        <Label className={lbl}>Jumlah Cars Baru *</Label>
                        <Input data-testid="input-jumlah-cars" type="number" className="rounded-sm mt-1.5" value={form.jumlah_cars} onChange={e => setForm({ ...form, jumlah_cars: e.target.value })} />
                      </div>
                      <div className="col-span-2">
                        <Label className={lbl}>Pengurus Cars</Label>
                        <PengurusCombobox testid="input-op-pengurus" value={form.pengurus} onChange={(v) => setForm({ ...form, pengurus: v })} options={pengurusOptions} placeholder="Pilih atau ketik nama pengurus cars…" />
                      </div>
                      {form.hour_meter_awal !== "" && form.hour_meter_akhir !== "" && (
                        <div className="col-span-2 border border-primary/40 bg-primary/5 p-3" data-testid="ops-auto-total">
                          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Total HM (otomatis)</p>
                          <p className="font-display font-black text-2xl tracking-tighter mt-1 text-primary">
                            {Math.max(0, Number(form.hour_meter_akhir) - Number(form.hour_meter_awal)).toFixed(2)} <span className="text-sm font-normal font-mono">JAM</span>
                          </p>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  {/* OPERASIONAL */}
                  <TabsContent value="operasional" className="mt-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className={lbl}>Downtime (Jam)</Label>
                        <Input data-testid="input-downtime" type="number" step="0.1" min="0" placeholder="0" className="rounded-sm mt-1.5" value={form.downtime_jam} onChange={e => setForm({ ...form, downtime_jam: e.target.value })} />
                      </div>
                      <div>
                        <Label className={lbl}>Pemakaian Solar (Liter)</Label>
                        <Input data-testid="input-solar" type="number" step="0.1" min="0" placeholder="0" className="rounded-sm mt-1.5" value={form.solar_liter} onChange={e => setForm({ ...form, solar_liter: e.target.value })} />
                      </div>
                      <div className="col-span-2">
                        <Label className={lbl}>Keterangan Harian</Label>
                        <Input data-testid="input-keterangan" className="rounded-sm mt-1.5" placeholder="Contoh: Galian saluran, hujan 1 jam" value={form.keterangan} onChange={e => setForm({ ...form, keterangan: e.target.value })} />
                        <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">Tampil di kolom "Keterangan" pada Rekap Bulanan Hour Meter.</p>
                      </div>
                    </div>
                  </TabsContent>

                  {/* KONDISI ALAT */}
                  <TabsContent value="kondisi" className="mt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Pemeriksaan harian · {ks.filled}/{KONDISI_ITEMS.length} diisi</p>
                      {ks.bad > 0 && <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 bg-accent text-accent-foreground flex items-center gap-1"><WarningIcon size={11} weight="bold" /> {ks.bad} tidak baik</span>}
                    </div>
                    {KONDISI_ITEMS.map(([key, label]) => {
                      const it = form.kondisi_alat[key] || {};
                      return (
                        <div key={key} data-testid={`kondisi-row-${key}`} className="border border-border bg-background p-3 space-y-2">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-semibold">{label}</p>
                            <ToggleGroup type="single" value={it.status || ""} onValueChange={(v) => setK(key, { status: v || "" })} className="gap-1">
                              <ToggleGroupItem data-testid={`kondisi-${key}-baik`} value="baik" className="rounded-sm h-8 px-3 text-xs border border-border data-[state=on]:bg-emerald-500 data-[state=on]:text-white data-[state=on]:border-emerald-500">
                                <CheckIcon size={12} weight="bold" className="mr-1" /> Baik
                              </ToggleGroupItem>
                              <ToggleGroupItem data-testid={`kondisi-${key}-tidak`} value="tidak" className="rounded-sm h-8 px-3 text-xs border border-border data-[state=on]:bg-accent data-[state=on]:text-accent-foreground data-[state=on]:border-accent">
                                <XIcon size={12} weight="bold" className="mr-1" /> Tidak
                              </ToggleGroupItem>
                            </ToggleGroup>
                          </div>
                          <Input data-testid={`kondisi-${key}-keterangan`} className="rounded-sm h-8 text-xs" placeholder="Keterangan (opsional)" value={it.keterangan || ""} onChange={e => setK(key, { keterangan: e.target.value })} />
                        </div>
                      );
                    })}
                  </TabsContent>

                  {/* CATATAN */}
                  <TabsContent value="catatan" className="mt-4">
                    <Label className={lbl}>Catatan Operator</Label>
                    <Textarea data-testid="input-catatan-operator" rows={6} className="rounded-sm mt-1.5" placeholder="Catatan kejadian, kerusakan, permintaan servis, dll." value={form.catatan_operator} onChange={e => setForm({ ...form, catatan_operator: e.target.value })} />
                  </TabsContent>
                </Tabs>

                <DialogFooter className="gap-2">
                  {tab !== "catatan" && (
                    <Button variant="outline" data-testid="ops-next-tab" className="rounded-sm border-border hover:border-primary hover:text-primary"
                      onClick={() => setTab({ umum: "operasional", operasional: "kondisi", kondisi: "catatan" }[tab])}>
                      Lanjut
                    </Button>
                  )}
                  <Button data-testid="save-operation-button" disabled={saving} onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-primary-foreground hover:text-primary-foreground">
                    {saving ? "Menyimpan…" : editId ? "Simpan Perubahan" : "Simpan Laporan"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      <div className="border border-border overflow-x-auto bg-card" data-testid="operations-table">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Tanggal</th>
              <th className="p-3">Unit</th>
              <th className="p-3">Operator</th>
              <th className="p-3 text-right">HM Awal</th>
              <th className="p-3 text-right">HM Akhir</th>
              <th className="p-3 text-right">Total Jam</th>
              <th className="p-3 text-right">Cars</th>
              <th className="p-3 text-right">Downtime</th>
              <th className="p-3 text-right">Solar</th>
              <th className="p-3">Kondisi</th>
              <th className="p-3">Keterangan</th>
              <th className="p-3 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={12} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada laporan</td></tr>}
            {rows.map(r => {
              const s = kondisiSummary(r.kondisi_alat);
              const canEdit = user?.role === "admin" || user?.user_id === r.operator_id;
              return (
                <tr key={r.id} className="border-t border-border hover:bg-secondary/60" data-testid={`op-row-${r.id}`}>
                  <td className="p-3 font-mono whitespace-nowrap">{r.tanggal}</td>
                  <td className="p-3 font-medium whitespace-nowrap">{r.unit_label}</td>
                  <td className="p-3 text-muted-foreground">{r.operator_name}</td>
                  <td className="p-3 text-right font-mono">{r.hour_meter_awal}</td>
                  <td className="p-3 text-right font-mono">{r.hour_meter_akhir}</td>
                  <td className="p-3 text-right font-mono text-primary">{r.total_jam}</td>
                  <td className="p-3 text-right font-mono">{r.jumlah_cars}</td>
                  <td className="p-3 text-right font-mono">{r.downtime_jam ? `${r.downtime_jam} j` : "—"}</td>
                  <td className="p-3 text-right font-mono">{r.solar_liter ? `${r.solar_liter} L` : "—"}</td>
                  <td className="p-3">
                    {s.filled === 0 ? <span className="text-muted-foreground">—</span> : s.bad > 0 ? (
                      <span className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border border-accent text-accent">{s.bad} Tidak</span>
                    ) : (
                      <span className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border border-emerald-500/60 text-emerald-400">Baik</span>
                    )}
                  </td>
                  <td className="p-3 text-muted-foreground max-w-[220px] truncate" title={r.keterangan || ""}>{r.keterangan || "—"}</td>
                  <td className="p-3 text-right whitespace-nowrap">
                    {canEdit && (
                      <div className="inline-flex gap-1">
                        <button data-testid={`edit-op-${r.id}`} onClick={() => openEdit(r)} className="p-1.5 border border-border hover:border-primary hover:text-primary">
                          <PencilSimpleIcon size={14} weight="bold" />
                        </button>
                        <button data-testid={`delete-op-${r.id}`} onClick={() => del(r.id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
                          <TrashIcon size={14} weight="bold" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
