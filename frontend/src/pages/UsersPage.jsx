import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { PlusIcon, TrashIcon, UserPlusIcon } from "@phosphor-icons/react";
import { toast } from "sonner";

const empty = { name: "", email: "", role: "operator" };

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);

  const load = async () => {
    const { data } = await api.get("/users");
    setUsers(data);
  };
  useEffect(() => { load(); }, []);

  const changeRole = async (uid, role) => {
    try {
      await api.patch(`/users/${uid}/role`, { role });
      toast.success("Role diperbarui");
      load();
    } catch { toast.error("Gagal update role"); }
  };

  const addManual = async () => {
    if (!form.name.trim()) { toast.error("Nama wajib diisi"); return; }
    try {
      await api.post("/users/manual", {
        name: form.name.trim(),
        email: form.email.trim() || null,
        role: form.role,
      });
      toast.success("Operator ditambahkan");
      setOpen(false); setForm(empty); load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menambahkan");
    }
  };

  const removeUser = async (uid) => {
    if (!window.confirm("Hapus operator manual ini?")) return;
    try {
      await api.delete(`/users/${uid}`);
      toast.success("Terhapus"); load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menghapus");
    }
  };

  return (
    <div>
      <PageHeader
        overline="// Access Control / 05"
        title="Manajemen Operator"
        description="Kelola akses tim. Tambahkan operator secara manual (tanpa perlu login Google) untuk kebutuhan payroll & assignment unit."
        actions={
          <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setForm(empty); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-manual-operator-button" className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black font-display tracking-tight">
                <UserPlusIcon size={16} weight="bold" className="mr-1.5" /> Tambah Operator Manual
              </Button>
            </DialogTrigger>
            <DialogContent className="rounded-sm border-border bg-card">
              <DialogHeader>
                <DialogTitle className="font-display font-black tracking-tighter text-2xl">Tambah Operator Manual</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Nama Operator</Label>
                  <Input data-testid="input-manual-name" className="rounded-sm mt-1.5" placeholder="Contoh: Budi Santoso" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                </div>
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Email (Opsional)</Label>
                  <Input data-testid="input-manual-email" className="rounded-sm mt-1.5" placeholder="Kosongkan jika tidak ada" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                  <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
                    Operator manual tidak bisa login. Cocok untuk pencatatan payroll & assignment unit saja.
                  </p>
                </div>
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Role</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                    <SelectTrigger data-testid="input-manual-role" className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="operator">Operator</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button data-testid="save-manual-operator-button" onClick={addManual} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">
                  <PlusIcon size={16} weight="bold" className="mr-1.5" /> Simpan
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="border border-border" data-testid="users-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Operator</th>
              <th className="p-3">Email</th>
              <th className="p-3">Tipe</th>
              <th className="p-3 w-40">Role</th>
              <th className="p-3 text-right w-20">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && <tr><td colSpan={5} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada user</td></tr>}
            {users.map(u => (
              <tr key={u.user_id} className="border-t border-border hover:bg-secondary/30">
                <td className="p-3">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8 rounded-sm">
                      <AvatarImage src={u.picture} />
                      <AvatarFallback className="rounded-sm bg-secondary text-[10px] font-mono">{u.name?.[0]?.toUpperCase()}</AvatarFallback>
                    </Avatar>
                    <span className="font-medium">{u.name}</span>
                  </div>
                </td>
                <td className="p-3 font-mono text-muted-foreground text-xs">{u.email}</td>
                <td className="p-3">
                  <Badge className={`rounded-sm text-[9px] font-mono uppercase tracking-widest px-1.5 py-0 ${u.manual ? "bg-secondary text-foreground" : "bg-primary/20 text-primary border border-primary/40"}`}>
                    {u.manual ? "Manual" : "Google"}
                  </Badge>
                </td>
                <td className="p-3">
                  <Select value={u.role} onValueChange={(v) => changeRole(u.user_id, v)}>
                    <SelectTrigger data-testid={`role-select-${u.user_id}`} className="rounded-sm h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="operator">Operator</SelectItem>
                    </SelectContent>
                  </Select>
                </td>
                <td className="p-3 text-right">
                  {u.manual && (
                    <button data-testid={`delete-user-${u.user_id}`} onClick={() => removeUser(u.user_id)} className="p-1.5 border border-border hover:border-accent hover:text-accent">
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
