import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { HELP_DOCS } from "@/lib/helpDocs";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DownloadSimpleIcon, DatabaseIcon, CircleNotchIcon, ArrowClockwiseIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import { toast } from "sonner";

const lbl = "font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground";
const fmt = (s) => (s ? new Date(s).toLocaleString("id-ID", { timeZone: "Asia/Makassar", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) + " WITA" : "-");

function Doc({ doc }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid={`help-doc-${doc.id}`}>
      {doc.sections.map((s) => (
        <section key={s.h} className="border border-border bg-card p-5">
          <h2 className="font-display font-bold text-lg tracking-tight border-l-2 border-primary pl-3">{s.h}</h2>
          <ul className="mt-3 space-y-1.5">{s.p.map((t, i) => <li key={i} className={`text-sm text-muted-foreground ${/^(python|mongodump)/.test(t) ? "font-mono text-xs text-foreground bg-background border border-border p-2 break-all" : ""}`}>{t}</li>)}</ul>
        </section>
      ))}
    </div>
  );
}

function BackupPanel() {
  const [info, setInfo] = useState(null);
  const [media, setMedia] = useState(false);
  const [busy, setBusy] = useState(false);
  const load = async () => { try { setInfo((await api.get("/admin/backup/info")).data); } catch { toast.error("Gagal memuat info backup"); } };
  useEffect(() => { load(); }, []);
  const download = async () => {
    setBusy(true);
    try {
      const res = await api.get("/admin/backup", { params: { include_media: media }, responseType: "blob" });
      const name = (res.headers["content-disposition"] || "").match(/filename="([^"]+)"/)?.[1] || "backup-trirara.json.gz";
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
      toast.success("Backup diunduh — simpan di tempat aman"); load();
    } catch { toast.error("Gagal membuat backup"); }
    finally { setBusy(false); }
  };
  const total = info ? Object.values(info.collections).reduce((a, b) => a + b, 0) : 0;
  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4" data-testid="backup-panel">
      <div className="border border-border bg-card p-5 space-y-4">
        <div className="flex items-center gap-2"><DatabaseIcon size={20} weight="bold" className="text-primary" /><p className="font-display font-black text-xl tracking-tighter">Unduh Backup</p></div>
        <p className="text-sm text-muted-foreground">Membuat salinan seluruh data (hanya-baca). Tidak mengubah atau menghapus data apa pun.</p>
        <label className="flex items-start gap-2 text-sm cursor-pointer border border-border p-3">
          <Checkbox data-testid="backup-include-media" checked={media} onCheckedChange={(v) => setMedia(!!v)} className="mt-0.5" />
          <span>Sertakan gambar WhatsApp <span className="block text-xs text-muted-foreground">Ukuran file jauh lebih besar</span></span>
        </label>
        <Button data-testid="backup-download" disabled={busy} onClick={download} className="w-full rounded-sm bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground">
          {busy ? <CircleNotchIcon size={16} className="mr-2 animate-spin" /> : <DownloadSimpleIcon size={16} weight="bold" className="mr-2" />} Unduh Backup (.json.gz)
        </Button>
        <div className="border-t border-border pt-3 text-xs space-y-1" data-testid="backup-last">
          <p className={lbl}>Backup terakhir</p>
          {info?.last_backup ? <p>{fmt(info.last_backup.at)} · oleh {info.last_backup.by}{info.last_backup.include_media ? " · dengan gambar" : ""}</p> : <p className="text-primary">Belum pernah — unduh backup pertama sekarang</p>}
        </div>
        <p className="text-xs text-muted-foreground flex gap-2"><ShieldCheckIcon size={14} className="text-primary shrink-0" /> Sesi login tidak ikut dicadangkan. File memuat data keuangan & hash kata sandi — simpan secara pribadi.</p>
      </div>
      <div className="xl:col-span-2 border border-border bg-card">
        <div className="flex items-center gap-2 p-4 border-b border-border"><p className="font-display font-black text-xl tracking-tighter mr-auto">Isi Database</p>
          <span className="font-mono text-xs" data-testid="backup-total">{total.toLocaleString("id-ID")} dokumen</span>
          <Button data-testid="backup-refresh" size="sm" variant="outline" onClick={load} className="rounded-sm border-border hover:border-primary hover:text-primary"><ArrowClockwiseIcon size={14} weight="bold" /></Button></div>
        {!info ? <div className="p-4"><Skeleton className="h-40 rounded-sm" /></div> : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4" data-testid="backup-collections">
            {Object.entries(info.collections).map(([k, v]) => (
              <div key={k} className="p-3 border-b border-r border-border"><p className="font-mono text-[10px] text-muted-foreground truncate">{k}</p><p className="font-display font-bold text-lg">{v.toLocaleString("id-ID")}</p></div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function HelpPage() {
  const [tab, setTab] = useState("penggunaan");
  return (
    <div data-testid="help-page">
      <div className="border-b border-border pb-6 mb-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Bantuan</p>
        <h1 className="font-display font-black text-4xl tracking-tighter mt-1">Bantuan & Backup</h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-2xl">Panduan penggunaan aplikasi, pengaturan otomatisasi, prosedur backup & pemulihan database, serta panduan integrasi WhatsApp untuk nanti.</p>
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="h-auto flex flex-wrap justify-start rounded-sm bg-card border border-border p-1 mb-6 gap-1">
          {HELP_DOCS.map((d) => <TabsTrigger key={d.id} value={d.id} data-testid={`help-tab-${d.id}`} className="rounded-sm text-xs px-3 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">{d.title}</TabsTrigger>)}
        </TabsList>
        {HELP_DOCS.map((d) => (
          <TabsContent key={d.id} value={d.id} className="space-y-4">
            {d.id === "backup" && <BackupPanel />}
            <Doc doc={d} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
