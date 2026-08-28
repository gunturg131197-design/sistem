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
import {
  PlusIcon, TrashIcon, UserPlusIcon, KeyIcon, EyeIcon, EyeSlashIcon, CopyIcon, ShieldCheckIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const empty = { name: "", email: "", role: "operator", pin: "" };

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);

  const [pinDialog, setPinDialog] = useState(null); // { user, pin }
  const [verifyDialog, setVerifyDialog] = useState(null); // { user, pinInput }
  const [showPin, setShowPin] = useState({}); // { user_id: bool }

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
    if (form.pin && !/^\d{4,6}$/.test(form.pin)) { toast.error("PIN harus 4-6 digit angka"); return; }
    try {
      await api.post("/users/manual", {
        name: form.name.trim(),
        email: form.email.trim() || null,
        role: form.role,
        pin: form.pin || null,
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

  const savePin = async () => {
    const val = (pinDialog.pin || "").trim();
    if (val && !/^\d{4,6}$/.test(val)) { toast.error("PIN harus 4-6 digit angka"); return; }
    try {
      await api.patch(`/users/${pinDialog.user.user_id}/pin`, { pin: val || null });
      toast.success(val ? "PIN tersimpan" : "PIN dihapus");
      setPinDialog(null); load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan PIN");
    }
  };

  const copyPin = (pin) => {
    if (!pin) return;
    navigator.clipboard.writeText(pin);
    toast.success(`PIN ${pin} disalin ke clipboard`);
  };

  const verifyPin = async () => {
    const { user, pinInput } = verifyDialog;
    if (!pinInput) { toast.error("Masukkan PIN"); return; }
    try {
      const { data } = await api.post("/users/verify-pin", { user_id: user.user_id, pin: pinInput });
      if (data.ok) toast.success(`✔ PIN valid — ${data.name}`);
      else toast.error("✘ PIN salah");
      setVerifyDialog(null);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Verifikasi gagal");
    }
  };

  return (
    <div>
      <PageHeader
        overline="// Access Control / 05"
        title="Manajemen Operator"
        description="Kelola akses tim. Tambahkan operator manual dengan PIN 4-6 digit untuk verifikasi shift di lapangan tanpa perlu login Google."
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
                <div>
                  <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5">
                    <KeyIcon size={12} weight="bold" /> PIN Shift (Opsional · 4-6 digit)
                  </Label>
                  <Input
                    data-testid="input-manual-pin"
                    className="rounded-sm mt-1.5 font-mono tracking-[0.4em]"
                    placeholder="Contoh: 1234"
                    inputMode="numeric"
                    maxLength={6}
                    value={form.pin}
                    onChange={e => setForm({ ...form, pin: e.target.value.replace(/\D/g, "") })}
                  />
                  <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
                    PIN dipakai untuk verifikasi handover shift. Bisa di-reset kapan saja.
                  </p>
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

      <div className="border border-border overflow-x-auto" data-testid="users-table">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              <th className="p-3">Operator</th>
              <th className="p-3">Email</th>
              <th className="p-3">Tipe</th>
              <th className="p-3 w-40">Role</th>
              <th className="p-3">PIN Shift</th>
              <th className="p-3 text-right w-32">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && <tr><td colSpan={6} className="p-8 text-center text-muted-foreground text-xs font-mono">// Belum ada user</td></tr>}
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
                <td className="p-3">
                  {u.manual ? (
                    u.pin ? (
                      <div className="inline-flex items-center gap-1.5 border border-primary/40 bg-primary/5 px-2 py-1">
                        <KeyIcon size={12} weight="bold" className="text-primary" />
                        <span data-testid={`pin-value-${u.user_id}`} className="font-mono text-xs tracking-[0.35em] text-primary">
                          {showPin[u.user_id] ? u.pin : "••••"}
                        </span>
                        <button
                          data-testid={`toggle-pin-${u.user_id}`}
                          onClick={() => setShowPin(s => ({ ...s, [u.user_id]: !s[u.user_id] }))}
                          className="text-muted-foreground hover:text-primary"
                          title={showPin[u.user_id] ? "Sembunyikan" : "Tampilkan"}
                        >
                          {showPin[u.user_id] ? <EyeSlashIcon size={12} weight="bold" /> : <EyeIcon size={12} weight="bold" />}
                        </button>
                        <button
                          data-testid={`copy-pin-${u.user_id}`}
                          onClick={() => copyPin(u.pin)}
                          className="text-muted-foreground hover:text-primary"
                          title="Salin PIN"
                        >
                          <CopyIcon size={12} weight="bold" />
                        </button>
                      </div>
                    ) : (
                      <span className="font-mono text-[10px] text-muted-foreground">— tidak diset —</span>
                    )
                  ) : (
                    <span className="font-mono text-[10px] text-muted-foreground">n/a</span>
                  )}
                </td>
                <td className="p-3 text-right">
                  <div className="inline-flex gap-1">
                    {u.manual && (
                      <>
                        <button
                          data-testid={`set-pin-${u.user_id}`}
                          onClick={() => setPinDialog({ user: u, pin: u.pin || "" })}
                          className="p-1.5 border border-border hover:border-primary hover:text-primary"
                          title={u.pin ? "Reset PIN" : "Set PIN"}
                        >
                          <KeyIcon size={14} weight="bold" />
                        </button>
                        {u.pin && (
                          <button
                            data-testid={`verify-pin-${u.user_id}`}
                            onClick={() => setVerifyDialog({ user: u, pinInput: "" })}
                            className="p-1.5 border border-border hover:border-primary hover:text-primary"
                            title="Verifikasi PIN"
                          >
                            <ShieldCheckIcon size={14} weight="bold" />
                          </button>
                        )}
                        <button
                          data-testid={`delete-user-${u.user_id}`}
                          onClick={() => removeUser(u.user_id)}
                          className="p-1.5 border border-border hover:border-accent hover:text-accent"
                          title="Hapus"
                        >
                          <TrashIcon size={14} weight="bold" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Set/Reset PIN dialog */}
      <Dialog open={!!pinDialog} onOpenChange={(v) => { if (!v) setPinDialog(null); }}>
        <DialogContent className="rounded-sm border-border bg-card">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl flex items-center gap-2">
              <KeyIcon size={22} weight="bold" className="text-primary" /> {pinDialog?.user?.pin ? "Reset PIN" : "Set PIN"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Operator: <span className="font-medium text-foreground">{pinDialog?.user?.name}</span></p>
            <div>
              <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">PIN Baru (4-6 digit, kosongkan untuk hapus)</Label>
              <Input
                data-testid="input-pin-value"
                className="rounded-sm mt-1.5 font-mono tracking-[0.4em] text-center text-lg"
                placeholder="0000"
                inputMode="numeric"
                maxLength={6}
                value={pinDialog?.pin || ""}
                onChange={e => setPinDialog({ ...pinDialog, pin: e.target.value.replace(/\D/g, "") })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button data-testid="save-pin-button" onClick={savePin} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">
              Simpan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Verify PIN dialog */}
      <Dialog open={!!verifyDialog} onOpenChange={(v) => { if (!v) setVerifyDialog(null); }}>
        <DialogContent className="rounded-sm border-border bg-card">
          <DialogHeader>
            <DialogTitle className="font-display font-black tracking-tighter text-2xl flex items-center gap-2">
              <ShieldCheckIcon size={22} weight="bold" className="text-primary" /> Verifikasi PIN Shift
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Operator: <span className="font-medium text-foreground">{verifyDialog?.user?.name}</span></p>
            <div>
              <Label className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Masukkan PIN dari operator</Label>
              <Input
                data-testid="input-verify-pin"
                className="rounded-sm mt-1.5 font-mono tracking-[0.4em] text-center text-lg"
                placeholder="••••"
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={verifyDialog?.pinInput || ""}
                onChange={e => setVerifyDialog({ ...verifyDialog, pinInput: e.target.value.replace(/\D/g, "") })}
                onKeyDown={e => { if (e.key === "Enter") verifyPin(); }}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button data-testid="verify-pin-button" onClick={verifyPin} className="rounded-sm bg-primary hover:bg-primary/90 text-black hover:text-black">
              Verifikasi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
