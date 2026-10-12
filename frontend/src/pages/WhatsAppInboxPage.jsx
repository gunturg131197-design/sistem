import React, { useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import { PageHeader, formatIDR, CurrencyInput } from "@/components/common";
import PengurusCombobox from "@/components/PengurusCombobox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  WhatsappLogoIcon, UploadSimpleIcon, ReceiptIcon, GaugeIcon, QuestionIcon, CheckIcon, XIcon, ArrowClockwiseIcon, TrashIcon,
  WarningIcon, CircleNotchIcon, PlusIcon, PencilSimpleIcon, ImageIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";
import { AutomationTab, SummaryTab, AuditList } from "@/components/WaAutomation";
import { ConnectionTab, OutboxTab, LEVEL } from "@/components/WaConnection";

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
const STATUS = {
  processing: ["Diproses AI", "border-sky-400/50 text-sky-300"],
  pending: ["Menunggu Verifikasi", "border-primary/70 text-primary"],
  duplicate: ["Duplikat", "border-accent text-accent"],
  approved: ["Disetujui", "border-emerald-500/60 text-emerald-400"],
  rejected: ["Ditolak", "border-border text-muted-foreground"],
  error: ["Gagal", "border-accent text-accent"],
};
const FILTERS = [["pending", "Menunggu"], ["duplicate", "Duplikat"], ["processing", "Diproses"], ["approved", "Disetujui"], ["rejected", "Ditolak"], ["error", "Gagal"], ["all", "Semua"]];
const JENIS = { transfer: ["Bukti Transfer", ReceiptIcon], hour_meter: ["Laporan HM", GaugeIcon], lainnya: ["Lainnya", QuestionIcon] };
const TIPE = [["operator", "Operator"], ["pengurus", "Pengurus"], ["klien", "Klien"], ["lainnya", "Lainnya"]];
const fmtTime = (s) => (s ? new Date(s).toLocaleString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "-");

function StatusPill({ status, testid }) {
  const [l, c] = STATUS[status] || [status, "border-border text-muted-foreground"];
  return <span data-testid={testid} className={`inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border ${c}`}>{status === "processing" && <CircleNotchIcon size={10} weight="bold" className="animate-spin" />}{l}</span>;
}

/** Gambar dimuat lewat axios (cookie sesi) lalu ditampilkan sebagai blob URL. */
function AuthImage({ id, className, alt }) {
  const [src, setSrc] = useState("");
  const [err, setErr] = useState(false);
  useEffect(() => {
    let url = ""; let alive = true;
    api.get(`/wa/inbox/${id}/media`, { responseType: "blob" })
      .then(({ data }) => { if (!alive) return; url = URL.createObjectURL(data); setSrc(url); })
      .catch(() => alive && setErr(true));
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [id]);
  if (err) return <div className={`${className} flex items-center justify-center bg-background text-muted-foreground`}><ImageIcon size={22} /></div>;
  if (!src) return <Skeleton className={`${className} rounded-none`} />;
  return <img src={src} alt={alt} className={className} />;
}

function Summary({ it }) {
  const d = it.draft || {};
  if (it.status === "processing") return <p className="text-xs font-mono text-muted-foreground">// AI sedang membaca gambar…</p>;
  if (it.status === "error") return <p className="text-xs text-accent">{it.error}</p>;
  if (it.jenis === "transfer") return (
    <div className="text-sm">
      <p className="font-display font-black text-xl tracking-tighter text-primary">{formatIDR(d.debit)}</p>
      <p className="font-mono text-[10px] text-muted-foreground">{d.tanggal || "-"} · Ref {d.no_ref || "-"} · {d.pic || "-"}</p>
    </div>
  );
  if (it.jenis === "hour_meter") return (
    <div className="text-sm">
      <p className="font-display font-black text-xl tracking-tighter text-primary">{Number(d.hm_akhir || 0).toLocaleString("id-ID")} <span className="text-xs font-mono font-normal text-muted-foreground">HM</span></p>
      <p className="font-mono text-[10px] text-muted-foreground">{d.tanggal || "-"} {d.jam_foto || ""} · Awal {d.hm_awal ?? "-"}</p>
    </div>
  );
  return <p className="text-xs text-muted-foreground">Tidak dikenali sebagai bukti transfer / foto HM</p>;
}

function InboxTab({ units, operators, pengurusOptions, onCounts }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("pending");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [review, setReview] = useState(null);
  const [counts, setCounts] = useState({});

  const load = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [{ data }, st] = await Promise.all([api.get("/wa/inbox", { params: { status: filter === "pending" ? "pending,processing" : filter } }), api.get("/wa/status")]);
      setItems(data); setCounts(st.data.counts || {}); onCounts && onCounts(st.data);
    } catch { if (!quiet) toast.error("Gagal memuat kotak masuk"); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [filter]);
  const anyProcessing = (counts.processing || 0) > 0;
  useEffect(() => {
    if (!anyProcessing) return undefined;
    const t = setInterval(() => load(true), 4000);
    return () => clearInterval(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anyProcessing, filter]);

  return (
    <div data-testid="wa-inbox-tab">
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex flex-wrap border border-border bg-card">
          {FILTERS.map(([v, l]) => (
            <button key={v} data-testid={`wa-filter-${v}`} onClick={() => setFilter(v)}
              className={`px-3 py-2 text-xs font-mono uppercase tracking-wider transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${filter === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
              {l}{v !== "all" && counts[v] ? <span className="ml-1.5 opacity-80">{counts[v]}</span> : null}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <Button data-testid="wa-refresh" variant="outline" onClick={() => load()} className="rounded-sm border-border hover:border-primary hover:text-primary"><ArrowClockwiseIcon size={16} weight="bold" className="mr-2" /> Muat Ulang</Button>
          <Button data-testid="wa-upload-open" onClick={() => setUploadOpen(true)} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground font-display tracking-tight"><UploadSimpleIcon size={16} weight="bold" className="mr-2" /> Upload Gambar</Button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">{[0, 1, 2].map(i => <Skeleton key={i} className="h-40 rounded-sm" />)}</div>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-border p-10 text-center bg-card" data-testid="wa-empty">
          <WhatsappLogoIcon size={30} className="mx-auto text-muted-foreground" />
          <p className="font-mono text-xs text-muted-foreground mt-3">// Tidak ada pesan dengan status ini</p>
          <Button data-testid="wa-empty-upload" size="sm" onClick={() => setUploadOpen(true)} className="mt-4 rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><UploadSimpleIcon size={14} weight="bold" className="mr-1.5" /> Upload bukti / foto HM</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="wa-inbox-list">
          {items.map((it) => {
            const [jl, JI] = JENIS[it.jenis] || ["—", QuestionIcon];
            return (
              <button key={it.id} data-testid={`wa-item-${it.id}`} onClick={() => setReview(it)}
                className="text-left border border-border bg-card flex hover:border-primary transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {it.media_id ? <AuthImage id={it.id} alt="Lampiran WhatsApp" className="w-24 h-40 object-cover shrink-0 border-r border-border" /> : <div className="w-24 h-40 shrink-0 border-r border-border flex items-center justify-center text-muted-foreground"><ImageIcon size={22} /></div>}
                <div className="p-3 flex-1 min-w-0 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider"><JI size={13} weight="bold" className="text-primary" /> {jl}</span>
                    <span className="flex items-center gap-1">
                      {it.auto_approved && <span data-testid={`wa-item-auto-${it.id}`} className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 bg-emerald-500/15 text-emerald-400">Otomatis</span>}
                      <StatusPill status={it.status} testid={`wa-item-status-${it.id}`} />
                    </span>
                  </div>
                  <Summary it={it} />
                  <div className="mt-auto space-y-1">
                    <p className="text-xs truncate"><span className="text-muted-foreground">Ket:</span> <b>{it.caption || "—"}</b>{it.match?.unit_label ? <span className="text-primary"> → {it.match.unit_label}</span> : null}</p>
                    <p className="font-mono text-[9px] text-muted-foreground truncate">{it.source === "whatsapp" ? <><WhatsappLogoIcon size={10} className="inline mr-1" />{it.from_name || it.from_phone}</> : `Upload · ${it.created_by || "admin"}`} · {fmtTime(it.received_at)}</p>
                    {(it.warnings || []).length > 0 && it.status !== "approved" && (
                      <p className="text-[11px] text-primary flex items-start gap-1"><WarningIcon size={12} weight="bold" className="shrink-0 mt-0.5" /> <span className="line-clamp-1">{it.warnings[0]}{it.warnings.length > 1 ? ` (+${it.warnings.length - 1})` : ""}</span></p>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} onDone={() => { setFilter("pending"); load(); }} />
      {review && <ReviewDialog item={review} units={units} operators={operators} pengurusOptions={pengurusOptions} onClose={() => setReview(null)} onChanged={() => { setReview(null); load(); }} />}
    </div>
  );
}

function UploadDialog({ open, onOpenChange, onDone }) {
  const [files, setFiles] = useState([]);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef(null);
  const reset = () => { setFiles([]); setCaption(""); };
  const submit = async () => {
    if (!files.length) { toast.error("Pilih gambar terlebih dahulu"); return; }
    setBusy(true);
    let ok = 0;
    for (const f of files) {
      const fd = new FormData(); fd.append("file", f); fd.append("caption", caption);
      try { await api.post("/wa/upload", fd); ok += 1; } catch (e) { toast.error(`${f.name}: ${e?.response?.data?.detail || "gagal diupload"}`); }
    }
    setBusy(false);
    if (ok) { toast.success(`${ok} gambar diupload · AI sedang membaca`); reset(); onOpenChange(false); onDone(); }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="rounded-sm border-border bg-card max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display font-black tracking-tighter text-2xl">Upload Bukti / Foto HM</DialogTitle>
          <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Sama seperti pesan WhatsApp — AI membaca, Anda memverifikasi</p>
        </DialogHeader>
        <div className="space-y-3">
          <button type="button" data-testid="wa-upload-drop" onClick={() => ref.current?.click()}
            onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); setFiles([...e.dataTransfer.files].filter(f => f.type.startsWith("image/"))); }}
            className="w-full border-2 border-dashed border-border hover:border-primary p-6 text-center transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <UploadSimpleIcon size={26} className="mx-auto text-primary" />
            <p className="text-sm mt-2">{files.length ? `${files.length} gambar dipilih` : "Klik atau tarik gambar ke sini"}</p>
            <p className="font-mono text-[10px] text-muted-foreground mt-1">{files.length ? files.map(f => f.name).join(", ") : "JPG · PNG · WEBP · maks 12 MB · bisa lebih dari satu"}</p>
          </button>
          <input ref={ref} data-testid="wa-upload-input" type="file" accept="image/*" multiple className="hidden" onChange={(e) => setFiles([...e.target.files])} />
          <div>
            <Label className={lbl}>Keterangan (seperti caption WA)</Label>
            <Input data-testid="wa-upload-caption" className="rounded-sm mt-1.5" placeholder="Contoh: Sdlg 10" value={caption} onChange={(e) => setCaption(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button data-testid="wa-upload-submit" disabled={busy} onClick={submit} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">
            {busy ? <CircleNotchIcon size={16} weight="bold" className="mr-2 animate-spin" /> : <UploadSimpleIcon size={16} weight="bold" className="mr-2" />} {busy ? "Mengupload…" : "Upload & Baca"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function F({ label, children, full }) {
  return <div className={full ? "col-span-2" : "col-span-2 sm:col-span-1"}><Label className={lbl}>{label}</Label>{children}</div>;
}

function ReviewDialog({ item, units, operators, pengurusOptions, onClose, onChanged }) {
  const [jenis, setJenis] = useState(item.jenis === "transfer" || item.jenis === "hour_meter" ? item.jenis : "transfer");
  const [d, setD] = useState({ ...(item.draft || {}) });
  const [busy, setBusy] = useState("");
  const [hist, setHist] = useState([]);
  useEffect(() => { api.get("/wa/audit", { params: { inbox_id: item.id } }).then(({ data }) => setHist(data)).catch(() => {}); }, [item.id]);
  const done = item.status === "approved";
  const locked = done || item.status === "processing";
  const set = (k, v) => setD((x) => ({ ...x, [k]: v }));
  const onUnit = (v) => {
    const u = units.find((x) => x.id === v);
    setD((x) => ({ ...x, unit_id: v, pengurus: x.pengurus || u?.pengurus || "", ...(jenis === "transfer" && !x.tujuan_dana ? { tujuan_dana: u ? `${u.unit_name} - ${u.nomor_lambung}` : "" } : {}) }));
  };
  const act = async (kind) => {
    setBusy(kind);
    try {
      if (kind === "approve") {
        const payload = { ...d };
        if (jenis === "hour_meter") { payload.hm_awal = payload.hm_awal === "" || payload.hm_awal === null ? null : Number(payload.hm_awal); payload.hm_akhir = Number(payload.hm_akhir || 0); payload.jumlah_cars = Number(payload.jumlah_cars || 0); }
        if (jenis === "transfer") payload.debit = Number(payload.debit || 0);
        const { data } = await api.post(`/wa/inbox/${item.id}/approve`, { jenis, draft: payload });
        toast.success(`Disetujui · ${data.result?.no || ""}${data.replied ? " · balasan WA terkirim" : ""}`);
      } else if (kind === "reject") { await api.post(`/wa/inbox/${item.id}/reject`); toast.success("Ditolak"); }
      else if (kind === "reprocess") { await api.post(`/wa/inbox/${item.id}/reprocess`); toast.success("Diproses ulang oleh AI"); }
      else if (kind === "delete") { if (!window.confirm("Hapus pesan ini beserta gambarnya?")) { setBusy(""); return; } await api.delete(`/wa/inbox/${item.id}`); toast.success("Terhapus"); }
      onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal"); }
    finally { setBusy(""); }
  };
  const ai = item.ai || {};
  const t = ai.transfer || {};

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="rounded-sm border-border bg-card max-w-5xl max-h-[92vh] overflow-y-auto" data-testid="wa-review-dialog">
        <DialogHeader>
          <DialogTitle className="font-display font-black tracking-tighter text-2xl flex flex-wrap items-center gap-3">Verifikasi Data <StatusPill status={item.status} testid="wa-review-status" /></DialogTitle>
          <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Ket: <b className="text-foreground">{item.caption || "—"}</b> · {item.source === "whatsapp" ? `WA ${item.from_name || ""} ${item.from_phone}` : `Upload ${item.created_by || ""}`} · {fmtTime(item.received_at)}</p>
        </DialogHeader>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          <div className="lg:col-span-2">
            {item.media_id ? <AuthImage id={item.id} alt="Gambar dari WhatsApp" className="w-full max-h-[60vh] object-contain bg-background border border-border" /> : <div className="h-60 border border-border flex items-center justify-center text-muted-foreground"><ImageIcon size={28} /></div>}
            {jenis === "transfer" && t.total ? <p className="font-mono text-[10px] text-muted-foreground mt-2">AI: total {formatIDR(t.total)} · admin {formatIDR(t.biaya_admin)} · {t.bank_pengirim || "-"} → {t.bank_tujuan || "-"} {t.rekening_tujuan || ""}</p> : null}
          </div>
          <div className="lg:col-span-3 space-y-4">
            {(item.warnings || []).length > 0 && !done && (
              <div className="border border-primary/50 bg-primary/10 p-3 space-y-1" data-testid="wa-review-warnings">
                {item.warnings.map((w, i) => <p key={i} className="text-xs flex items-start gap-1.5"><WarningIcon size={13} weight="bold" className="text-primary shrink-0 mt-0.5" /> {w}</p>)}
              </div>
            )}
            {item.status === "error" && <p className="text-sm text-accent border border-accent/50 p-3">{item.error}</p>}
            {item.auto_check && !done && item.auto_check.reasons?.length > 0 && (
              <div className="border border-border p-3 text-xs space-y-1" data-testid="wa-review-autocheck">
                <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Tidak disimpan otomatis karena · keyakinan AI {Math.round((item.auto_check.confidence || 0) * 100)}%</p>
                {item.auto_check.reasons.map((r, i) => <p key={i} className="text-muted-foreground">• {r}</p>)}
              </div>
            )}
            {done && <p className="text-sm border border-emerald-500/50 text-emerald-400 p-3" data-testid="wa-review-result">Tercatat: <b>{item.result?.no}</b> {item.result?.type === "kas_masuk" ? "(Kas Masuk)" : "(Ops Report)"} · oleh {item.reviewed_by}</p>}

            <div className="flex border border-border w-fit">
              {[["transfer", "Bukti Transfer → Kas Masuk"], ["hour_meter", "Foto HM → Ops Report"]].map(([v, l]) => (
                <button key={v} disabled={locked} data-testid={`wa-jenis-${v}`} onClick={() => setJenis(v)} className={`px-3 py-2 text-xs font-mono uppercase tracking-wider disabled:opacity-60 ${jenis === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{l}</button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <F label="Unit *">
                <Select value={d.unit_id || "none"} disabled={locked} onValueChange={(v) => onUnit(v === "none" ? "" : v)}>
                  <SelectTrigger data-testid="wa-input-unit" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih unit" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">— Pilih unit —</SelectItem>
                    {units.map((u) => <SelectItem key={u.id} value={u.id}>{u.unit_name} · {u.nomor_lambung}{u.kode_wa ? ` (${u.kode_wa})` : ""}</SelectItem>)}
                  </SelectContent>
                </Select>
              </F>
              <F label="Pengurus">
                <div className="mt-1.5"><PengurusCombobox testid="wa-input-pengurus" value={d.pengurus || ""} onChange={(v) => set("pengurus", v)} options={pengurusOptions} placeholder="Pilih / ketik pengurus…" /></div>
              </F>
              <F label="Tanggal *"><Input data-testid="wa-input-tanggal" type="date" disabled={locked} className="rounded-sm mt-1.5" value={d.tanggal || ""} onChange={(e) => set("tanggal", e.target.value)} /></F>
              {jenis === "transfer" ? (
                <>
                  <F label="Nominal (Debit) *"><CurrencyInput data-testid="wa-input-debit" disabled={locked} className="rounded-sm mt-1.5" value={d.debit ?? ""} onChange={(v) => set("debit", v)} /></F>
                  <F label="No. Referensi"><Input data-testid="wa-input-noref" disabled={locked} className="rounded-sm mt-1.5 font-mono" value={d.no_ref || ""} onChange={(e) => set("no_ref", e.target.value)} /></F>
                  <F label="PIC / Pengirim"><Input data-testid="wa-input-pic" disabled={locked} className="rounded-sm mt-1.5" value={d.pic || ""} onChange={(e) => set("pic", e.target.value)} /></F>
                  <F label="Uraian" full><Input data-testid="wa-input-uraian" disabled={locked} className="rounded-sm mt-1.5" value={d.uraian || ""} onChange={(e) => set("uraian", e.target.value)} /></F>
                  <F label="Tujuan Dana" full><Input data-testid="wa-input-tujuan" disabled={locked} className="rounded-sm mt-1.5" value={d.tujuan_dana || ""} onChange={(e) => set("tujuan_dana", e.target.value)} /></F>
                </>
              ) : (
                <>
                  <F label="Operator">
                    <Select value={d.operator_id || "none"} disabled={locked} onValueChange={(v) => set("operator_id", v === "none" ? "" : v)}>
                      <SelectTrigger data-testid="wa-input-operator" className="rounded-sm mt-1.5"><SelectValue placeholder="Pilih operator" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">— Operator unit —</SelectItem>
                        {operators.map((o) => <SelectItem key={o.user_id} value={o.user_id}>{o.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </F>
                  <F label="HM Awal"><Input data-testid="wa-input-hm-awal" type="number" step="0.1" disabled={locked} className="rounded-sm mt-1.5 font-mono" value={d.hm_awal ?? ""} onChange={(e) => set("hm_awal", e.target.value)} /></F>
                  <F label="HM Akhir *"><Input data-testid="wa-input-hm-akhir" type="number" step="0.1" disabled={locked} className="rounded-sm mt-1.5 font-mono" value={d.hm_akhir ?? ""} onChange={(e) => set("hm_akhir", e.target.value)} /></F>
                  <F label="Jumlah Cars"><Input data-testid="wa-input-cars" type="number" disabled={locked} className="rounded-sm mt-1.5 font-mono" value={d.jumlah_cars ?? 0} onChange={(e) => set("jumlah_cars", e.target.value)} /></F>
                  <div className="col-span-2 font-mono text-[11px] text-muted-foreground border-l-2 border-primary pl-2">
                    Total jam: <b className="text-foreground">{Math.max(0, Number(d.hm_akhir || 0) - Number(d.hm_awal ?? d.hm_akhir ?? 0)).toLocaleString("id-ID", { maximumFractionDigits: 2 })}</b> · AI membaca HM {item.ai?.hour_meter?.hm ?? "-"} {item.ai?.hour_meter?.merek ? `(${item.ai.hour_meter.merek})` : ""}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
        <details className="border border-border" data-testid="wa-review-history">
          <summary className="cursor-pointer px-3 py-2 font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground hover:text-foreground">Riwayat aktivitas ({hist.length})</summary>
          <div className="px-3 max-h-52 overflow-y-auto"><AuditList rows={hist} compact testid="wa-review-audit" /></div>
        </details>
        <DialogFooter className="flex-wrap gap-2 sm:justify-between">
          <div className="flex gap-2">
            <Button data-testid="wa-delete" variant="outline" disabled={!!busy} onClick={() => act("delete")} className="rounded-sm border-border hover:border-accent hover:text-accent"><TrashIcon size={14} weight="bold" className="mr-1.5" /> Hapus</Button>
            {!done && <Button data-testid="wa-reprocess" variant="outline" disabled={!!busy || item.status === "processing"} onClick={() => act("reprocess")} className="rounded-sm border-border hover:border-primary hover:text-primary"><ArrowClockwiseIcon size={14} weight="bold" className="mr-1.5" /> Baca Ulang AI</Button>}
          </div>
          {!done && (
            <div className="flex gap-2">
              <Button data-testid="wa-reject" variant="outline" disabled={!!busy || item.status === "rejected"} onClick={() => act("reject")} className="rounded-sm border-accent/60 text-accent hover:bg-accent/10 hover:text-accent"><XIcon size={14} weight="bold" className="mr-1.5" /> Tolak</Button>
              <Button data-testid="wa-approve" disabled={!!busy || locked} onClick={() => act("approve")} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground font-display tracking-tight">
                {busy === "approve" ? <CircleNotchIcon size={14} weight="bold" className="mr-1.5 animate-spin" /> : <CheckIcon size={14} weight="bold" className="mr-1.5" />} Setujui & Simpan
              </Button>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const emptyContact = { phone: "", nama: "", tipe: "operator", user_id: "", unit_id: "", pengurus: "" };

function ContactsTab({ units, operators, pengurusOptions }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyContact);
  const [editId, setEditId] = useState(null);
  const load = async () => { setLoading(true); try { setRows((await api.get("/wa/contacts")).data); } catch { toast.error("Gagal memuat kontak"); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!form.phone || !form.nama) { toast.error("Nomor & nama wajib diisi"); return; }
    try {
      if (editId) await api.patch(`/wa/contacts/${editId}`, form); else await api.post("/wa/contacts", form);
      toast.success("Kontak tersimpan"); setOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); }
  };
  const del = async (r) => { if (!window.confirm(`Hapus kontak ${r.nama}?`)) return; await api.delete(`/wa/contacts/${r.id}`); toast.success("Terhapus"); load(); };
  const unitLabel = (id) => { const u = units.find((x) => x.id === id); return u ? `${u.unit_name} · ${u.nomor_lambung}` : "—"; };
  return (
    <div data-testid="wa-contacts-tab">
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <p className="text-sm text-muted-foreground max-w-2xl">Daftarkan nomor WA operator & pengurus. Foto HM dari nomor operator otomatis masuk ke unit default-nya walau tanpa keterangan; bukti transfer dari nomor pengurus otomatis ditandai ke pengurus tersebut.</p>
        <Button data-testid="wa-contact-add" onClick={() => { setForm(emptyContact); setEditId(null); setOpen(true); }} className="ml-auto rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"><PlusIcon size={16} weight="bold" className="mr-1.5" /> Tambah Kontak</Button>
      </div>
      <div className="border border-border bg-card overflow-x-auto">
        <table className="w-full text-sm" data-testid="wa-contacts-table">
          <thead className="bg-muted"><tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"><th className="p-3">Nama</th><th className="p-3">No. WhatsApp</th><th className="p-3">Tipe</th><th className="p-3">Unit Default</th><th className="p-3">Pengurus</th><th className="p-3 text-right">Aksi</th></tr></thead>
          <tbody>
            {loading && <tr><td colSpan={6} className="p-3"><Skeleton className="h-5 w-full rounded-sm" /></td></tr>}
            {!loading && rows.length === 0 && <tr><td colSpan={6} className="p-8 text-center text-xs font-mono text-muted-foreground">// Belum ada kontak WhatsApp</td></tr>}
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-border hover:bg-secondary/60">
                <td className="p-3 font-medium">{r.nama}</td>
                <td className="p-3 font-mono text-primary">+{r.phone}</td>
                <td className="p-3"><span className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 border border-border">{(TIPE.find(t => t[0] === r.tipe) || [, r.tipe])[1]}</span></td>
                <td className="p-3 text-muted-foreground">{unitLabel(r.unit_id)}</td>
                <td className="p-3 text-muted-foreground">{r.pengurus || "—"}</td>
                <td className="p-3 text-right whitespace-nowrap">
                  <button data-testid={`wa-contact-edit-${r.id}`} onClick={() => { setForm({ ...emptyContact, ...r }); setEditId(r.id); setOpen(true); }} className="p-1.5 border border-border hover:border-primary hover:text-primary mr-1"><PencilSimpleIcon size={14} weight="bold" /></button>
                  <button data-testid={`wa-contact-delete-${r.id}`} onClick={() => del(r)} className="p-1.5 border border-border hover:border-accent hover:text-accent"><TrashIcon size={14} weight="bold" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="rounded-sm border-border bg-card max-w-lg">
          <DialogHeader><DialogTitle className="font-display font-black tracking-tighter text-2xl">{editId ? "Edit Kontak WA" : "Tambah Kontak WA"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1"><Label className={lbl}>No. WhatsApp *</Label><Input data-testid="wa-contact-phone" className="rounded-sm mt-1.5 font-mono" placeholder="0812xxxx / 62812xxxx" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="col-span-2 sm:col-span-1"><Label className={lbl}>Nama *</Label><Input data-testid="wa-contact-nama" className="rounded-sm mt-1.5" value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} /></div>
            <div className="col-span-2 sm:col-span-1"><Label className={lbl}>Tipe</Label>
              <Select value={form.tipe} onValueChange={(v) => setForm({ ...form, tipe: v })}><SelectTrigger data-testid="wa-contact-tipe" className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger><SelectContent>{TIPE.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent></Select>
            </div>
            <div className="col-span-2 sm:col-span-1"><Label className={lbl}>Akun Operator</Label>
              <Select value={form.user_id || "none"} onValueChange={(v) => setForm({ ...form, user_id: v === "none" ? "" : v })}><SelectTrigger data-testid="wa-contact-user" className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">— Tidak ada —</SelectItem>{operators.map((o) => <SelectItem key={o.user_id} value={o.user_id}>{o.name}</SelectItem>)}</SelectContent></Select>
            </div>
            <div className="col-span-2 sm:col-span-1"><Label className={lbl}>Unit Default</Label>
              <Select value={form.unit_id || "none"} onValueChange={(v) => setForm({ ...form, unit_id: v === "none" ? "" : v })}><SelectTrigger data-testid="wa-contact-unit" className="rounded-sm mt-1.5"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">— Tidak ada —</SelectItem>{units.map((u) => <SelectItem key={u.id} value={u.id}>{u.unit_name} · {u.nomor_lambung}</SelectItem>)}</SelectContent></Select>
            </div>
            <div className="col-span-2 sm:col-span-1"><Label className={lbl}>Pengurus</Label><div className="mt-1.5"><PengurusCombobox testid="wa-contact-pengurus" value={form.pengurus} onChange={(v) => setForm({ ...form, pengurus: v })} options={pengurusOptions} /></div></div>
          </div>
          <DialogFooter><Button data-testid="wa-contact-save" onClick={save} className="rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">Simpan</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function WhatsAppInboxPage() {
  const [tab, setTab] = useState("inbox");
  const [units, setUnits] = useState([]);
  const [operators, setOperators] = useState([]);
  const [pengurusOptions, setPengurusOptions] = useState([]);
  const [status, setStatus] = useState(null);
  useEffect(() => {
    Promise.all([api.get("/units"), api.get("/users"), api.get("/pengurus"), api.get("/wa/status")])
      .then(([u, us, pg, st]) => { setUnits(u.data); setOperators(us.data); setPengurusOptions(pg.data); setStatus(st.data); })
      .catch(() => toast.error("Gagal memuat data pendukung"));
  }, []);
  const conn = status?.connection;
  const pending = useMemo(() => (status?.counts?.pending || 0) + (status?.counts?.duplicate || 0), [status]);

  return (
    <div>
      <PageHeader overline="// WhatsApp / 08" title="Kotak Masuk WA"
        description="Bukti transfer & foto layar Hour Meter dari WhatsApp dibaca otomatis oleh AI, dicocokkan ke unit lewat keterangan (mis. Sdlg 10), lalu diverifikasi admin sebelum tercatat ke Kas Masuk dan Ops Report."
        actions={
          <button type="button" onClick={() => setTab("settings")} data-testid="wa-header-status" className={`inline-flex items-center gap-2 px-3 py-2 border font-mono text-[10px] uppercase tracking-widest transition-opacity duration-150 hover:opacity-80 ${(LEVEL[conn?.level] || LEVEL.not_configured).tone}`}>
            <WhatsappLogoIcon size={14} weight="bold" /> {(LEVEL[conn?.level] || LEVEL.not_configured).short}
          </button>
        } />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="h-auto rounded-sm bg-card border border-border p-1 mb-6 gap-1">
          <TabsTrigger value="inbox" data-testid="wa-tab-inbox" className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Kotak Masuk{pending ? ` · ${pending}` : ""}</TabsTrigger>
          <TabsTrigger value="contacts" data-testid="wa-tab-contacts" className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Kontak WA</TabsTrigger>
          <TabsTrigger value="automation" data-testid="wa-tab-automation" className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Otomatisasi & Audit</TabsTrigger>
          <TabsTrigger value="summary" data-testid="wa-tab-summary" className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Ringkasan Harian</TabsTrigger>
          <TabsTrigger value="outbox" data-testid="wa-tab-outbox" className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Pesan Keluar</TabsTrigger>
          <TabsTrigger value="settings" data-testid="wa-tab-settings" className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Koneksi WhatsApp</TabsTrigger>
        </TabsList>
        <TabsContent value="inbox"><InboxTab units={units} operators={operators} pengurusOptions={pengurusOptions} onCounts={setStatus} /></TabsContent>
        <TabsContent value="contacts">{tab === "contacts" && <ContactsTab units={units} operators={operators} pengurusOptions={pengurusOptions} />}</TabsContent>
        <TabsContent value="automation">{tab === "automation" && <AutomationTab />}</TabsContent>
        <TabsContent value="summary">{tab === "summary" && <SummaryTab />}</TabsContent>
        <TabsContent value="outbox">{tab === "outbox" && <OutboxTab />}</TabsContent>
        <TabsContent value="settings">{tab === "settings" && <ConnectionTab onChanged={(c) => setStatus((s) => ({ ...(s || {}), connection: c }))} />}</TabsContent>
      </Tabs>
    </div>
  );
}
