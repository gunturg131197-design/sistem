import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, formatIDR, CurrencyInput } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { PlusIcon, TrashIcon, CalendarBlankIcon, FileXlsIcon, FilePdfIcon, WrenchIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { exportToExcel, exportToPDF } from "@/lib/exporters";
import { format, parseISO } from "date-fns";

const emptyItem = () => ({ nama_sparepart: "", qty: "1", harga_satuan: "" });
const empty = () => ({
  unit_id: "",
  nomor_nota: "",
  tanggal: format(new Date(), "yyyy-MM-dd"),
  hm_service: "",
  items: [emptyItem()],
});

// Info service kelipatan 250 jam
function serviceHint(hm) {
  const v = Number(hm);
  if (!hm || isNaN(v) || v <= 0) return null;
  const isMultiple = v % 250 === 0;
  const next = Math.ceil((v + 0.0001) / 250) * 250;
  return { isMultiple, next };
}

export default function SparepartsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [units, setUnits] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty());

  const load = async () => {
    const [s, u] = await Promise.all([api.get("/spareparts"), api.get("/units")]);
    setRows(s.data); setUnits(u.data);
  };
  useEffect(() => { load(); }, []);

  // Normalize items untuk baris lama (tanpa items array)
  const getItems = (r) => {
    if (Array.isArray(r.items) && r.items.length > 0) return r.items;
    return [{ nama_sparepart: r.nama_sparepart || "-", qty: 1, harga_satuan: r.biaya || 0, total: r.biaya || 0 }];
  };

  const notaTotal = form.items.reduce((sum, it) => sum + (Number(it.qty) || 0) * (Number(it.harga_satuan) || 0), 0);

  const setItem = (idx, patch) => {
    setForm((f) => ({ ...f, items: f.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)) }));
  };
  const addItem = () => setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }));
  const removeItem = (idx) => setForm((f) => ({ ...f, items: f.items.length > 1 ? f.items.filter((_, i) => i !== idx) : f.items }));

  const save = async () => {
    if (!form.unit_id || !form.nomor_nota || !form.tanggal) { toast.error("Lengkapi unit, no nota & tanggal"); return; }
    const cleanItems = form.items
      .filter((it) => it.nama_sparepart.trim() !== "")
      .map((it) => ({
        nama_sparepart: it.nama_sparepart.trim(),
        qty: Number(it.qty) || 0,
        harga_satuan: Number(it.harga_satuan) || 0,
      }));
    if (cleanItems.length === 0) { toast.error("Tambahkan minimal 1 sparepart"); return; }
    if (cleanItems.some((it) => it.qty <= 0 || it.harga_satuan <= 0)) { toast.error("Qty & harga satuan harus lebih dari 0"); return; }
    try {
      await api.post("/spareparts", {
        unit_id: form.unit_id,
        nomor_nota: form.nomor_nota,
        tanggal: form.tanggal,
        hm_service: form.hm_service === "" ? null : Number(form.hm_service),
        items: cleanItems,
      });
      toast.success("Nota sparepart tersimpan"); setOpen(false); setForm(empty()); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
  };

  const del = async (id) => {
    if (!window.confirm("Hapus nota ini?")) return;
    await api.delete(`/spareparts/${id}`); toast.success("Terhapus"); load();
  };

  // Aggregate by unit
  const perUnit = rows.reduce((acc, r) => {
    acc[r.unit_id] = acc[r.unit_id] || { unit_label: r.unit_label, total: 0, count: 0 };
    acc[r.unit_id].total += r.biaya; acc[r.unit_id].count += 1;
    return acc;
  }, {});

  // Export: satu baris per item
  const exportRows = rows.flatMap((r) =>
    getItems(r).map((it) => ({
      Tanggal: r.tanggal,
      Unit: r.unit_label,
      "No Nota": r.nomor_nota,
      "HM Service": r.hm_service ?? "-",
      Sparepart: it.nama_sparepart,
      Qty: it.qty,
      "Harga Satuan": it.harga_satuan,
      "Total": it.total ?? (Number(it.qty) * Number(it.harga_satuan)),
    }))
  );

  const hint = serviceHint(form.hm_service);

  return (
    <div>
      <PageHeader
        overline="// Maintenance / 04"
        title="Penggantian Sparepart"
        description="Log nota penggantian sparepart per unit. Satu nota bisa berisi banyak sparepart. Servis dilakukan setiap kelipatan 250 jam (HM)."
        actions={
          <>
            <Button data-testid="export-excel-sparepart" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary" onClick={() => exportToExcel(exportRows, "spareparts")}>
              <FileXlsIcon size={16} weight="bold" className="mr-2" /> Excel
            </Button>
            <Button data-testid="export-pdf-sparepart" variant="outline" className="rounded-sm border-border hover:border-primary hover:text-primary"
              onClick={() => exportToPDF({
                title: "Laporan Penggantian Sparepart",
                columns: ["Tanggal", "Unit", "No Nota", "HM Service", "Sparepart", "Qty", "Harga Satuan", "Total"],
                rows: exportRows.map(r => [r.Tanggal, r.Unit, r["No Nota"], r["HM Service"], r.Sparepart, r.Qty, formatIDR(r["Harga Satuan"]), formatIDR(r.Total)]),
                filename: "spareparts",
              })}>
              <FilePdfIcon size={16} weight="bold" className="mr-2" /> PDF
            </Button>
            {isAdmin && (
              <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setForm(empty()); }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-sparepart-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                    <PlusIcon size={16} weight="bold" className="mr-1.5" /> Nota Baru
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-sm border-border bg-card max-w-2xl max-h-[90vh] overflow-y-auto">
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
                      <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Servis pada HM ke- (kelipatan 250 jam)</Label>
                      <Input data-testid="input-hm-service" type="number" step="1" className="rounded-sm mt-1.5" placeholder="Contoh: 250, 500, 750…" value={form.hm_service} onChange={e => setForm({ ...form, hm_service: e.target.value })} />
                      {hint && (
                        <p className={`font-mono text-[10px] mt-1.5 ${hint.isMultiple ? "text-primary" : "text-muted-foreground"}`}>
                          {hint.isMultiple ? "✓ Tepat pada jadwal servis 250 jam" : `Servis terjadwal terdekat: HM ${hint.next.toLocaleString("id-ID")}`}
                        </p>
                      )}
                    </div>

                    {/* Daftar item sparepart */}
                    <div className="col-span-2 border border-border">
                      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border">
                        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">// Daftar Sparepart</p>
                        <Button type="button" data-testid="add-item-button" size="sm" variant="outline" className="rounded-sm h-7 border-primary text-primary hover:bg-primary hover:text-black" onClick={addItem}>
                          <PlusIcon size={13} weight="bold" className="mr-1" /> Tambah Sparepart
                        </Button>
                      </div>
                      <div className="p-3 space-y-3">
                        {form.items.map((it, idx) => {
                          const lineTotal = (Number(it.qty) || 0) * (Number(it.harga_satuan) || 0);
                          return (
                            <div key={idx} className="grid grid-cols-12 gap-2 items-end" data-testid={`item-row-${idx}`}>
                              <div className="col-span-12 sm:col-span-5">
                                {idx === 0 && <Label className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">Nama Sparepart</Label>}
                                <Input data-testid={`item-nama-${idx}`} className="rounded-sm mt-1" placeholder="Filter Oli, Bucket Teeth…" value={it.nama_sparepart} onChange={e => setItem(idx, { nama_sparepart: e.target.value })} />
                              </div>
                              <div className="col-span-3 sm:col-span-2">
                                {idx === 0 && <Label className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">Qty</Label>}
                                <Input data-testid={`item-qty-${idx}`} type="number" step="1" min="0" className="rounded-sm mt-1" value={it.qty} onChange={e => setItem(idx, { qty: e.target.value })} />
                              </div>
                              <div className="col-span-6 sm:col-span-3">
                                {idx === 0 && <Label className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">Harga Satuan</Label>}
                                <CurrencyInput data-testid={`item-harga-${idx}`} className="rounded-sm mt-1" placeholder="Rp 0" value={it.harga_satuan} onChange={(v) => setItem(idx, { harga_satuan: v })} />
                              </div>
                              <div className="col-span-3 sm:col-span-2 flex items-center gap-1">
                                <div className="flex-1 text-right">
                                  {idx === 0 && <Label className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground block">Total</Label>}
                                  <span className="font-mono text-xs text-primary block mt-1 truncate" data-testid={`item-total-${idx}`}>{formatIDR(lineTotal)}</span>
                                </div>
                                <button type="button" data-testid={`item-remove-${idx}`} onClick={() => removeItem(idx)} className="p-1.5 border border-border hover:border-accent hover:text-accent shrink-0" title="Hapus baris">
                                  <TrashIcon size={13} weight="bold" />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div className="flex items-center justify-between px-3 py-2.5 border-t border-primary/40 bg-primary/5">
                        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Total Nota</p>
                        <p className="font-display font-black text-xl tracking-tighter text-primary" data-testid="nota-total">{formatIDR(notaTotal)}</p>
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button data-testid="save-sparepart-button" onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">Simpan Nota</Button>
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
              <th className="p-3 text-right">HM Service</th>
              <th className="p-3">Sparepart</th>
              <th className="p-3 text-right">Total Nota</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={isAdmin ? 7 : 6} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada catatan</td></tr>}
            {rows.map(r => {
              const items = getItems(r);
              return (
                <tr key={r.id} className="border-t border-border hover:bg-secondary/30 align-top">
                  <td className="p-3 font-mono whitespace-nowrap">{r.tanggal}</td>
                  <td className="p-3 font-medium">{r.unit_label}</td>
                  <td className="p-3 font-mono text-muted-foreground">{r.nomor_nota}</td>
                  <td className="p-3 text-right font-mono">
                    {r.hm_service != null ? (
                      <span className="inline-flex items-center gap-1 text-primary"><WrenchIcon size={12} weight="bold" />{Number(r.hm_service).toLocaleString("id-ID")}</span>
                    ) : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="p-3">
                    <div className="space-y-1">
                      {items.map((it, i) => (
                        <div key={i} className="flex justify-between gap-4 text-xs">
                          <span>{it.nama_sparepart} <span className="text-muted-foreground font-mono">×{it.qty}</span></span>
                          <span className="font-mono text-muted-foreground whitespace-nowrap">{formatIDR(it.total ?? Number(it.qty) * Number(it.harga_satuan))}</span>
                        </div>
                      ))}
                    </div>
                  </td>
                  <td className="p-3 text-right font-mono text-primary font-semibold whitespace-nowrap">{formatIDR(r.biaya)}</td>
                  {isAdmin && (
                    <td className="p-3 text-right">
                      <button data-testid={`delete-sparepart-${r.id}`} onClick={() => del(r.id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
                        <TrashIcon size={14} weight="bold" />
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
