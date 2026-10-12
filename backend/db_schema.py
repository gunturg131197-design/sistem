"""Skema tabel MariaDB (relasional, satu kolom per field) untuk semua data aplikasi TRIRARA.

Jenis kolom:
  s   VARCHAR(n)            teks pendek (default 255)
  txt MEDIUMTEXT            teks panjang
  date DATE                 tanggal 'YYYY-MM-DD' (dikembalikan ke aplikasi sebagai string yang sama)
  ts  VARCHAR(40)           timestamp ISO-8601 (mis. 2026-10-12T14:29:56.123456+00:00)
  f   DOUBLE                angka desimal (jam, rupiah, liter)
  i   BIGINT                bilangan bulat
  b   BOOLEAN               ya / tidak
  j   JSON                  struktur bertingkat (daftar item sparepart, kondisi alat, hasil AI, dll.)
  blob LONGBLOB             data biner (gambar WhatsApp)

Setiap tabel juga punya:
  _pk     BIGINT AUTO_INCREMENT PRIMARY KEY
  _extra  JSON  (cadangan untuk field baru yang belum punya kolom / nilai yang tipenya tidak cocok,
                 sehingga TIDAK ADA data yang hilang; kolom baru otomatis dibuat bila skema di sini ditambah)

`key` = kolom identitas alami yang dipakai migrasi & restore untuk mencegah duplikasi.
"""

TABLES = {
    # ---------------- Pengguna & sesi ----------------
    "users": {
        "key": ["user_id"],
        "cols": [("user_id", "s", 64), ("email", "s"), ("name", "s"), ("picture", "txt"), ("role", "s", 20), ("manual", "b"),
                 ("pin", "s"), ("username", "s", 100), ("password_hash", "s"), ("phone", "s", 30), ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["user_id"]],
        "index": [["email"], ["username"], ["role"]],
    },
    "user_sessions": {
        "key": ["session_token"],
        "cols": [("session_token", "s", 191), ("user_id", "s", 64), ("expires_at", "ts"), ("created_at", "ts")],
        "unique": [["session_token"]],
        "index": [["user_id"]],
    },
    # ---------------- Master data ----------------
    "units": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("unit_name", "s"), ("nomor_lambung", "s", 100), ("serial_number", "s", 150), ("operator_id", "s", 64),
                 ("operator_name", "s"), ("pengurus", "s"), ("nama_proyek", "s"), ("lokasi_proyek", "s"), ("pengawas_lapangan", "s"),
                 ("merek_type", "s"), ("pemilik_alat", "s"), ("tarif_sewa_per_jam", "f"), ("kode_wa", "s"), ("status", "s", 50),
                 ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["pengurus"], ["operator_id"], ["nomor_lambung"]],
    },
    "pengurus_excavator": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("nama", "s"), ("kontak", "s"), ("catatan", "txt"), ("tarif_sewa_per_jam", "f"), ("phone", "s", 30),
                 ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["nama"]],
    },
    # ---------------- Operasional ----------------
    "operations": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("unit_id", "s", 64), ("unit_label", "s"), ("operator_id", "s", 64), ("operator_name", "s"), ("tanggal", "date"),
                 ("hour_meter_awal", "f"), ("hour_meter_akhir", "f"), ("total_jam", "f"), ("jumlah_cars", "i"), ("pengurus", "s"),
                 ("keterangan", "txt"), ("downtime_jam", "f"), ("solar_liter", "f"), ("catatan_operator", "txt"), ("kondisi_alat", "j"),
                 ("source", "s", 30), ("inbox_id", "s", 64), ("auto_approved", "b"), ("hm_flag", "b"), ("hm_anomalies", "j"),
                 ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["unit_id", "tanggal"], ["tanggal"], ["pengurus"], ["operator_id"], ["inbox_id"]],
    },
    "payroll": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("operator_id", "s", 64), ("operator_name", "s"), ("unit_id", "s", 64), ("unit_label", "s"), ("periode", "s", 10),
                 ("tarif_per_jam", "f"), ("jam_kerja", "f"), ("jam_dibayar", "f"), ("gaji", "f"), ("kasbon", "f"), ("gaji_bersih", "f"),
                 ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["periode"], ["operator_id"], ["unit_id"]],
    },
    "spareparts": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("unit_id", "s", 64), ("unit_label", "s"), ("nomor_nota", "s", 150), ("nama_sparepart", "txt"), ("hm_service", "f"),
                 ("items", "j"), ("tanggal", "date"), ("biaya", "f"), ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["unit_id"], ["tanggal"]],
    },
    "report_archive": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("nomor", "s", 100), ("seq", "i"), ("month", "i"), ("year", "i"), ("jenis", "s", 30), ("unit_label", "s"),
                 ("periode_label", "s"), ("issued_by", "s"), ("created_at", "ts")],
        "unique": [["id"]],
        "index": [["seq"]],
    },
    "report_extras": {
        "key": ["key"],
        "cols": [("key", "s", 150), ("unit_id", "s", 64), ("periode", "s", 10), ("pengembalian_jam", "f"), ("lain_lain", "f"),
                 ("keterangan_tambahan", "txt"), ("updated_at", "ts"), ("updated_by", "s")],
        "unique": [["key"]],
        "index": [["periode"]],
    },
    # ---------------- Sistem ----------------
    "app_counters": {
        "key": ["key"],
        "cols": [("key", "s", 150), ("value", "i")],
        "unique": [["key"]],
        "index": [],
    },
    "app_settings": {  # pengaturan per fitur: kolom tetap + isi pengaturan di _extra (JSON)
        "key": ["key"],
        "cols": [("key", "s", 150), ("enabled", "b"), ("updated_at", "ts"), ("updated_by", "s")],
        "unique": [["key"]],
        "index": [],
    },
    "cron_runs": {
        "key": ["run_id"],
        "cols": [("run_id", "s", 191), ("job", "s", 50), ("tanggal", "s", 10), ("trigger", "s", 50), ("received_at", "ts"), ("finished_at", "ts"),
                 ("counts", "j"), ("result", "j")],
        "unique": [["run_id"]],
        "index": [["job"]],
    },
    # ---------------- Keuangan ----------------
    "kas_masuk": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("tanggal", "date"), ("uraian", "txt"), ("tujuan_dana", "s"), ("debit", "f"), ("pic", "s"), ("pengurus", "s"),
                 ("no_ref", "s", 150), ("no_bukti", "s", 50), ("source", "s", 30), ("source_id", "s", 64), ("inbox_id", "s", 64),
                 ("created_at", "ts"), ("created_by", "s"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["tanggal"], ["pengurus"], ["source", "source_id"], ["no_bukti"]],
    },
    "kas_keluar": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("tanggal", "date"), ("uraian", "txt"), ("penerima", "s"), ("jenis", "s", 10), ("no_bukti", "s", 50), ("kredit", "f"),
                 ("keterangan", "txt"), ("source", "s", 30), ("source_id", "s", 64), ("created_at", "ts"), ("created_by", "s"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["tanggal"], ["source", "source_id"], ["no_bukti"]],
    },
    "invoices": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("tanggal", "date"), ("nama_client", "s"), ("deskripsi", "txt"), ("jumlah", "f"), ("status", "s", 30),
                 ("no_invoice", "s", 100), ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["tanggal"], ["status"]],
    },
    "surat_masuk": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("tanggal_surat", "date"), ("nomor_surat", "s"), ("pengirim", "s"), ("perihal", "txt"), ("tanggal_terima", "s", 10),
                 ("keterangan", "txt"), ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["tanggal_surat"]],
    },
    "surat_keluar": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("tanggal_surat", "date"), ("nomor_surat", "s"), ("tujuan_surat", "s"), ("perihal", "txt"), ("pengirim", "s"),
                 ("keterangan", "txt"), ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["tanggal_surat"]],
    },
    "bonus_admin": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("unit_id", "s", 64), ("unit", "s"), ("milestone", "i"), ("jam_per_bonus", "f"), ("jam_target", "f"),
                 ("tanggal_tercapai", "date"), ("nominal", "f"), ("admin", "s"), ("paid_at", "date"), ("paid_by", "s"), ("no_bukti", "s", 50),
                 ("created_at", "ts")],
        "unique": [["id"], ["unit_id", "milestone", "jam_per_bonus"]],
        "index": [],
    },
    # ---------------- WhatsApp ----------------
    "wa_audit": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("at", "ts"), ("action", "s", 60), ("actor", "s"), ("inbox_id", "s", 64), ("detail", "txt"), ("data", "j")],
        "unique": [["id"]],
        "index": [["at"], ["action"], ["inbox_id"]],
    },
    "wa_contacts": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("phone", "s", 30), ("nama", "s"), ("tipe", "s", 20), ("user_id", "s", 64), ("unit_id", "s", 64), ("pengurus", "s"),
                 ("created_at", "ts"), ("updated_at", "ts")],
        "unique": [["id"]],
        "index": [["phone"], ["nama"]],
    },
    "wa_inbox": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("source", "s", 30), ("message_id", "s", 191), ("from_phone", "s", 30), ("from_name", "s"), ("caption", "txt"),
                 ("media_id", "s", 64), ("status", "s", 20), ("jenis", "s", 30), ("ai", "j"), ("draft", "j"), ("warnings", "j"), ("match", "j"),
                 ("result", "j"), ("error", "txt"), ("auto_check", "j"), ("auto_approved", "b"), ("hm_flag", "b"), ("hm_anomalies", "j"),
                 ("simulated", "b"), ("received_at", "ts"), ("processed_at", "ts"), ("reviewed_at", "ts"), ("reviewed_by", "s"), ("created_by", "s")],
        "unique": [["id"]],
        "index": [["status"], ["message_id"], ["received_at"], ["from_phone"]],
    },
    "wa_media": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("data", "blob"), ("mime", "s", 50), ("orig_mime", "s", 100), ("created_at", "ts")],
        "unique": [["id"]],
        "index": [],
    },
    "wa_outbox": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("kind", "s", 50), ("label", "s"), ("to", "s", 30), ("message", "j"), ("ref", "j"), ("attempts", "i"),
                 ("status", "s", 20), ("error", "txt"), ("dedupe_key", "s", 191), ("logical_key", "s", 191), ("wa_message_id", "s", 191),
                 ("history", "j"), ("retriable", "b"), ("uncertain", "b"), ("actor", "s"), ("created_at", "ts"), ("sending_since", "ts"),
                 ("sent_at", "ts"), ("next_retry_at", "ts"), ("failed_at", "ts")],
        "unique": [["id"], ["dedupe_key"]],
        "index": [["wa_message_id"], ["status", "next_retry_at"], ["logical_key"], ["created_at"]],
    },
    "wa_reminders": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("run_id", "s", 64), ("trigger", "s", 30), ("tanggal", "s", 10), ("pengurus", "s"), ("phone", "s", 30),
                 ("piutang", "f"), ("umur_hari", "i"), ("text", "txt"), ("status", "s", 20), ("error", "txt"), ("mode", "s", 20),
                 ("outbox_id", "s", 64), ("actor", "s"), ("created_at", "ts")],
        "unique": [["id"]],
        "index": [["pengurus"], ["created_at"]],
    },
    "wa_summaries": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("run_id", "s", 64), ("trigger", "s", 30), ("tanggal", "s", 10), ("pengurus", "s"), ("phone", "s", 30),
                 ("text", "txt"), ("params", "j"), ("status", "s", 20), ("error", "txt"), ("mode", "s", 20), ("outbox_id", "s", 64),
                 ("actor", "s"), ("created_at", "ts")],
        "unique": [["id"]],
        "index": [["tanggal"], ["created_at"]],
    },
    "wa_weekly": {
        "key": ["id"],
        "cols": [("id", "s", 64), ("run_id", "s", 64), ("trigger", "s", 30), ("week_start", "s", 10), ("week_end", "s", 10), ("nama", "s"),
                 ("phone", "s", 30), ("text", "txt"), ("total_jam", "f"), ("total_pemasukan", "f"), ("total_bayar", "f"), ("total_piutang", "f"),
                 ("pending_count", "i"), ("status", "s", 20), ("error", "txt"), ("mode", "s", 20), ("outbox_id", "s", 64), ("actor", "s"),
                 ("created_at", "ts")],
        "unique": [["id"]],
        "index": [["week_start"], ["created_at"]],
    },
    "wa_seen_messages": {
        "key": ["message_id"],
        "cols": [("message_id", "s", 191), ("at", "ts"), ("simulated", "b")],
        "unique": [["message_id"]],
        "index": [],
    },
    "wa_last_inbound": {
        "key": ["phone"],
        "cols": [("phone", "s", 30), ("at", "ts")],
        "unique": [["phone"]],
        "index": [],
    },
}
