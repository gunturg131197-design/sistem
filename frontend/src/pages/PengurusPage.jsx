import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import {
  UserPlusIcon, PencilSimpleIcon, TrashIcon, HardHatIcon, ChartBarIcon,
  PhoneIcon, PlusIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const empty = { nama: "", kontak: "", catatan: "" };

export default function PengurusPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState({}); // id -> stats
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editId, setEditId] = useState(null);

  const load = async () => {
    const { data } = await api.get("/pengurus-excavator");
    setRows(data);
    // load stats in parallel (best-effort)
    const results = await Promise.all(
      data.map((r) => api.get(`/pengurus-excavator/${r.id}/stats`).then((x) => [r.id, x.data]).catch(() => [r.id, null]))
    );
    const map = {};
    for (const [id, s] of results) if (s) map[id] = s;
    setStats(map);
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.nama.trim()) { toast.error("Nama wajib diisi"); return; }
    try {
      if (editId) await api.patch(`/pengurus-excavator/${editId}`, form);
      else await api.post("/pengurus-excavator", form);
      toast.success(editId ? "Pengurus diperbarui" : "Pengurus ditambahkan");
      setOpen(false); setForm(empty); setEditId(null); load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan");
    }
  };

  const del = async (id, nama) => {
    if (!window.confirm(`Hapus pengurus "${nama}"?\nData unit & laporan yang sudah tercatat tidak akan berubah.`)) return;
    try {
      await api.delete(`/pengurus-excavator/${id}`);
      toast.success("Terhapus"); load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menghapus");
    }
  };

  const totalCars = Object.values(stats).reduce((a, b) => a + (b?.total_cars || 0), 0);
  const totalJam = Object.values(stats).reduce((a, b) => a + (b?.total_jam || 0), 0);

  return (
    <div>
      <PageHeader
        overline="// Registry / 06"
        title="Pengurus Excavator"
        description="Daftar pengurus / PIC excavator. Nama yang tersimpan di sini otomatis muncul di dropdown pengurus unit & laporan cars — mencegah salah eja."
        actions={
          isAdmin && (
            <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setForm(empty); setEditId(null); } }}>
              <DialogTrigger asChild>
                <Button data-testid="add-pengurus-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                  <UserPlusIcon size={16} weight="bold" className="mr-1.5" /> Tambah Pengurus
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-sm border-border bg-card">
                <DialogHeader>
                  <DialogTitle className="font-display font-black tracking-tighter text-2xl">
                    {editId ? "Edit Pengurus" : "Tambah Pengurus Baru"}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-3">
                  <div>
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Nama Pengurus</Label>
                    <Input data-testid="input-pengurus-nama" className="rounded-sm mt-1.5" placeholder="Contoh: Pak Rudi Hartono" value={form.nama} onChange={e => setForm({ ...form, nama: e.target.value })} />
                  </div>
                  <div>
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Kontak (Opsional)</Label>
                    <Input data-testid="input-pengurus-kontak" className="rounded-sm mt-1.5" placeholder="No HP / WA / email" value={form.kontak} onChange={e => setForm({ ...form, kontak: e.target.value })} />
                  </div>
                  <div>
                    <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Catatan (Opsional)</Label>
                    <Textarea data-testid="input-pengurus-catatan" className="rounded-sm mt-1.5" rows={2} placeholder="Contoh: Pengurus shift pagi zona A" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} />
                  </div>
                  {editId && (
                    <p className="font-mono text-[10px] text-muted-foreground border-l-2 border-primary pl-2">
                      // Mengubah nama akan otomatis me-rename di semua unit & laporan cars yang tercatat.
                    </p>
                  )}
                </div>
                <DialogFooter>
                  <Button data-testid="save-pengurus-button" onClick={save} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">
                    <PlusIcon size={16} weight="bold" className="mr-1.5" /> Simpan
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )
        }
      />

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-0 mb-8 border border-border">
        <div className="p-5 border-r border-border">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5"><HardHatIcon size={12} weight="bold" /> Total Pengurus</p>
          <p className="font-display font-black text-3xl tracking-tighter mt-2 text-primary">{rows.length}</p>
        </div>
        <div className="p-5 border-r border-border">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5"><ChartBarIcon size={12} weight="bold" /> Total Cars Diawasi</p>
          <p className="font-display font-black text-3xl tracking-tighter mt-2">{totalCars}</p>
        </div>
        <div className="p-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5"><ChartBarIcon size={12} weight="bold" /> Total Jam Diawasi</p>
          <p className="font-display font-black text-3xl tracking-tighter mt-2">{totalJam.toFixed(2)} <span className="text-sm font-mono font-normal text-muted-foreground">HRS</span></p>
        </div>
      </div>

      <div className="border border-border overflow-x-auto" data-testid="pengurus-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Nama</th>
              <th className="p-3">Kontak</th>
              <th className="p-3">Catatan</th>
              <th className="p-3 text-right">Unit Diawasi</th>
              <th className="p-3 text-right">Cars</th>
              <th className="p-3 text-right">Jam</th>
              {isAdmin && <th className="p-3 text-right">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={7} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada pengurus terdaftar. Klik "Tambah Pengurus" untuk mulai.</td></tr>
            )}
            {rows.map(r => {
              const s = stats[r.id] || {};
              return (
                <tr key={r.id} className="border-t border-border hover:bg-secondary/30">
                  <td className="p-3 font-medium">{r.nama}</td>
                  <td className="p-3 font-mono text-xs text-muted-foreground">
                    {r.kontak ? (
                      <span className="inline-flex items-center gap-1"><PhoneIcon size={12} weight="bold" /> {r.kontak}</span>
                    ) : <span>—</span>}
                  </td>
                  <td className="p-3 text-muted-foreground text-xs max-w-xs truncate">{r.catatan || <span>—</span>}</td>
                  <td className="p-3 text-right font-mono">{s.units_count ?? 0}</td>
                  <td className="p-3 text-right font-mono text-primary">{s.total_cars ?? 0}</td>
                  <td className="p-3 text-right font-mono">{(s.total_jam ?? 0).toFixed(2)}</td>
                  {isAdmin && (
                    <td className="p-3 text-right">
                      <div className="inline-flex gap-1">
                        <button
                          data-testid={`edit-pengurus-${r.id}`}
                          onClick={() => { setForm({ nama: r.nama, kontak: r.kontak || "", catatan: r.catatan || "" }); setEditId(r.id); setOpen(true); }}
                          className="p-1.5 border border-border hover:border-primary hover:text-primary"
                        >
                          <PencilSimpleIcon size={14} weight="bold" />
                        </button>
                        <button
                          data-testid={`delete-pengurus-${r.id}`}
                          onClick={() => del(r.id, r.nama)}
                          className="p-1.5 border border-border hover:border-accent hover:text-accent"
                        >
                          <TrashIcon size={14} weight="bold" />
                        </button>
                      </div>
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
