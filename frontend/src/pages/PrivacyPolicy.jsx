import React from "react";
import { BrandLockup } from "@/components/Brand";

const SECTIONS = [
  ["Siapa kami", "Aplikasi ini dikelola oleh TRIRARA TUNGGAL PUTRA untuk operasional penyewaan alat berat: pencatatan Hour Meter (HM), laporan operasional, keuangan, serta komunikasi dengan operator, pengurus, dan pemilik melalui WhatsApp Business."],
  ["Data yang kami terima lewat WhatsApp", "Nomor WhatsApp dan nama profil pengirim, isi pesan, serta gambar yang dikirim (bukti transfer dan foto layar Hour Meter), termasuk keterangan (caption) yang menyertainya."],
  ["Tujuan penggunaan", "Data dipakai hanya untuk: membaca dan mencatat pembayaran sewa serta angka Hour Meter, verifikasi oleh admin, mengirim balasan konfirmasi, ringkasan harian, pengingat piutang, dan laporan mingguan kepada pihak terkait. Data tidak dijual dan tidak dipakai untuk iklan."],
  ["Pemrosesan otomatis", "Gambar dibaca oleh layanan kecerdasan buatan untuk mengekstrak nominal, nomor referensi, tanggal, dan angka HM. Data hanya tercatat otomatis bila tingkat keyakinan tinggi dan lolos pemeriksaan; selebihnya diverifikasi manual oleh admin."],
  ["Pihak ketiga", "Pesan dikirim dan diterima melalui WhatsApp Business Platform milik Meta Platforms, Inc. Pembacaan gambar memakai penyedia AI tepercaya. Data hanya dibagikan sejauh diperlukan untuk layanan tersebut."],
  ["Penyimpanan & keamanan", "Data disimpan di server dengan akses terbatas bagi admin yang berwenang. Kredensial integrasi disimpan sebagai rahasia server dan tidak ditampilkan. Setiap tindakan atas data tercatat dalam log audit."],
  ["Masa simpan", "Catatan keuangan dan operasional disimpan selama diperlukan untuk keperluan administrasi dan kewajiban hukum. Gambar dapat dihapus oleh admin setelah data diverifikasi."],
  ["Hak Anda", "Anda dapat meminta salinan, koreksi, atau penghapusan data pribadi Anda, serta berhenti menerima pesan dengan membalas BERHENTI atau menghubungi kami."],
  ["Kontak", "TRIRARA TUNGGAL PUTRA — hubungi admin melalui nomor WhatsApp resmi perusahaan."],
];

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-background text-foreground" data-testid="privacy-page">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <BrandLockup size={40} testid="privacy-brand" />
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary mt-10">// Kebijakan Privasi</p>
        <h1 className="font-display font-black text-4xl tracking-tighter mt-2">Kebijakan Privasi</h1>
        <p className="text-sm text-muted-foreground mt-2">Berlaku sejak 2026. Halaman ini menjelaskan bagaimana data yang diterima melalui WhatsApp Business dan aplikasi diproses.</p>
        <div className="mt-8 space-y-6">
          {SECTIONS.map(([t, b], i) => (
            <section key={t} className="border-l-2 border-primary pl-4" data-testid={`privacy-section-${i}`}>
              <h2 className="font-display font-bold text-lg tracking-tight">{t}</h2>
              <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{b}</p>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
