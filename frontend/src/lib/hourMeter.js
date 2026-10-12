// =====================================================================
//  FORM HOUR METER OPERATOR & ALAT BERAT — engine laporan PDF / Excel / Word
//  Susunan mengikuti template "Hour Meter.docx" TRIRARA TUNGGAL PUTRA
// =====================================================================
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import ExcelJS from "exceljs";
import { saveAs } from "file-saver";
import {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  ImageRun, Header, Footer, BorderStyle, ShadingType, VerticalAlign, HorizontalPositionRelativeFrom,
  VerticalPositionRelativeFrom, TextWrappingType, LevelFormat,
} from "docx";
import { LH_HEADER, LH_HEADER_RATIO, LH_FOOTER, LH_FOOTER_RATIO } from "./letterhead";
import { COMPANY } from "./company";

export const KONDISI_ITEMS = [
  ["mesin", "Mesin"],
  ["sistem_hidrolik", "Sistem Hidrolik"],
  ["ban_track", "Ban / Track"],
  ["lampu", "Lampu"],
  ["rem", "Rem"],
  ["kelistrikan", "Kelistrikan"],
];

export const PETUNJUK = [
  "HM Awal diisi sebelum alat mulai bekerja.",
  "HM Akhir diisi setelah alat selesai bekerja.",
  "Total Jam Kerja = HM Akhir dikurangi HM Awal.",
  "Setiap operator wajib mengisi form setiap hari.",
  "Pengawas lapangan wajib memeriksa dan menandatangani form.",
  "Form ini digunakan sebagai dasar rekap pemakaian alat dan penagihan pekerjaan.",
];

const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];

// ---------- format helpers ----------
export const fmtNum = (n, max = 2) => {
  if (n === null || n === undefined || n === "" || Number.isNaN(Number(n))) return "-";
  return Number(n).toLocaleString("id-ID", { maximumFractionDigits: max });
};
export const fmtIDR = (n) => "Rp " + Number(n || 0).toLocaleString("id-ID", { maximumFractionDigits: 0 });
export const fmtDate = (iso) => {
  if (!iso) return "-";
  const [y, m, d] = String(iso).slice(0, 10).split("-");
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
};
export const fmtDateLong = (date = new Date()) => `${date.getDate()} ${BULAN[date.getMonth()]} ${date.getFullYear()}`;
const dash = (v) => (v === null || v === undefined || String(v).trim() === "" ? "-" : String(v));

// ---------- normalisasi data laporan (dipakai ketiga format) ----------
export function buildHourMeterModel(r, meta = {}) {
  const ops = [...(r.operations || [])].sort((a, b) => (a.tanggal || "").localeCompare(b.tanggal || ""));
  const operators = (r.operators && r.operators.length ? r.operators : [r.operator_utama]).filter(Boolean);
  const tanggalRange = ops.length
    ? (ops[0].tanggal === ops[ops.length - 1].tanggal ? fmtDate(ops[0].tanggal) : `${fmtDate(ops[0].tanggal)} s/d ${fmtDate(ops[ops.length - 1].tanggal)}`)
    : "-";

  const rekap = ops.map((o) => [
    fmtDate(o.tanggal), fmtNum(o.hour_meter_awal), fmtNum(o.hour_meter_akhir), fmtNum(o.total_jam), dash(o.operator_name), dash(o.keterangan),
  ]);

  const sparepart = [];
  (r.spareparts || []).forEach((s) => {
    const items = s.items && s.items.length ? s.items : [{ nama_sparepart: s.nama_sparepart, qty: 1, harga_satuan: s.biaya, total: s.biaya }];
    items.forEach((it) => {
      sparepart.push([
        String(sparepart.length + 1),
        dash(it.nama_sparepart) + (s.nomor_nota ? ` (Nota ${s.nomor_nota})` : ""),
        s.hm_service !== null && s.hm_service !== undefined && s.hm_service !== "" ? fmtNum(s.hm_service) : "-",
        fmtNum(it.qty),
        fmtIDR(it.harga_satuan),
        fmtIDR(it.total ?? (Number(it.qty || 0) * Number(it.harga_satuan || 0))),
        fmtDate(s.tanggal),
      ]);
    });
  });

  const biaya = {
    sparepart: Number(r.total_sparepart || 0),
    gaji: Number(r.total_gaji || 0),
    pengembalian: Number(r.pengembalian_jam || 0),
    lain: Number(r.lain_lain || 0),
  };
  biaya.total = biaya.sparepart + biaya.gaji + biaya.pengembalian + biaya.lain;

  const kondisi = KONDISI_ITEMS.map(([k, label]) => {
    const it = (r.kondisi_alat || {})[k] || {};
    return { label, baik: it.status === "baik", tidak: it.status === "tidak", keterangan: it.keterangan || "" };
  });

  const catatan = (r.catatan_operator || []).map((c) => `${fmtDate(c.tanggal)} — ${c.operator ? c.operator + ": " : ""}${c.catatan}`);

  return {
    title: "FORM HOUR METER OPERATOR & ALAT BERAT",
    nomor: meta.nomor || "",
    periodeLabel: meta.periodeLabel || "Semua Periode",
    unitLabel: r.unit_label,
    dataUmum: [
      ["Nama Perusahaan", COMPANY.legalName],
      ["Nama Proyek", dash(r.nama_proyek)],
      ["Lokasi Proyek", dash(r.lokasi_proyek)],
      ["Periode", meta.periodeLabel || "Semua Periode"],
      ["Pengawas Lapangan", dash(r.pengawas_lapangan)],
    ],
    identitasOperator: [
      ["Nama Operator", operators.join(", ") || "-"],
      ["Tanggal", tanggalRange],
    ],
    identitasAlat: [
      ["Nama Alat", dash(r.unit_name)],
      ["Merek / Type", dash(r.merek_type)],
      ["Nomor Unit", `${dash(r.nomor_lambung)}${r.serial_number ? `  ·  SN ${r.serial_number}` : ""}`],
      ["Pemilik Alat", dash(r.pemilik_alat)],
      ["Operator", operators.join(", ") || "-"],
      ["Lokasi Proyek", dash(r.lokasi_proyek)],
    ],
    rekapHead: ["Tanggal", "HM Awal", "HM Akhir", "Total HM", "Operator", "Keterangan"],
    rekap,
    rekapTotal: ["TOTAL", fmtNum(r.hm_awal), fmtNum(r.hm_akhir), fmtNum(r.total_hm), "", ""],
    totalPemakaian: [
      ["Total Hour Meter Bulanan", `${fmtNum(r.total_hm)} Jam`],
      ["Total Hari Operasional", `${fmtNum(r.hari_operasional ?? 0, 0)} Hari`],
      ["Total Downtime", `${fmtNum(r.total_downtime ?? 0)} Jam`],
      ["Total Pemakaian Solar", `${fmtNum(r.total_solar ?? 0)} Liter`],
    ],
    keteranganTambahan: r.keterangan_tambahan || "",
    sparepartHead: ["No", "Nama Spare Part", "HM Pada Saat Penggantian", "Qty", "Harga Satuan", "Total Harga", "Tanggal Penggantian"],
    sparepart,
    sparepartTotal: fmtIDR(biaya.sparepart),
    totalBiaya: [
      ["Spare Part", fmtIDR(biaya.sparepart)],
      ["Gaji Operator", fmtIDR(biaya.gaji)],
      ["Pengembalian Jam-Jaman", fmtIDR(biaya.pengembalian)],
      ["Lain-lain", fmtIDR(biaya.lain)],
    ],
    totalBiayaSum: fmtIDR(biaya.total),
    kondisi,
    catatan,
    ttd: [
      { role: "Operator", name: operators[0] || "" },
      { role: "Pengawas Lapangan", name: r.pengawas_lapangan || "" },
      { role: "Mengetahui", name: COMPANY.legalName, isCompany: true },
    ],
    printedAt: fmtDateLong(new Date()),
  };
}

const MIN_REKAP_ROWS = 10;
const MIN_SP_ROWS = 5;
const padRows = (rows, min, cols) => {
  const out = [...rows];
  while (out.length < min) out.push(Array(cols).fill(""));
  return out;
};

// =====================================================================
//  PDF
// =====================================================================
const PW = 210, PH = 297, MX = 14;
const HEADER_H = PW * LH_HEADER_RATIO;
const FOOTER_H = PW * LH_FOOTER_RATIO;
const TOP = HEADER_H + 6;
const BOTTOM = FOOTER_H + 6;
const NAVY = [2, 45, 66];
const YELLOW = [254, 194, 2];
const LABEL_FILL = [238, 242, 246];

// padding baris kosong hanya bila muat di halaman yang sama (hindari baris kosong "tumpah" ke halaman baru)
function pdfSmartPad(y, rows, min, cols, headH, rowH = 7, footH = 7.5) {
  const fit = Math.floor((PH - BOTTOM - y - headH - footH) / rowH);
  if (rows.length >= fit) return rows;
  return padRows(rows, Math.min(min, fit), cols);
}

function pdfLetterhead(doc) {
  doc.addImage(LH_HEADER, "JPEG", 0, 0, PW, HEADER_H);
  doc.addImage(LH_FOOTER, "JPEG", 0, PH - FOOTER_H, PW, FOOTER_H);
}

function pdfEnsure(doc, y, need) {
  if (y + need > PH - BOTTOM) {
    doc.addPage();
    pdfLetterhead(doc);
    return TOP;
  }
  return y;
}

function pdfSection(doc, y, text, need = 22) {
  y = pdfEnsure(doc, y, need);
  doc.setFillColor(...NAVY);
  doc.rect(MX, y, PW - MX * 2, 6.5, "F");
  doc.setFillColor(...YELLOW);
  doc.rect(MX, y, 2.2, 6.5, "F");
  doc.setFont("times", "bold");
  doc.setFontSize(10);
  doc.setTextColor(255, 255, 255);
  doc.text(text, MX + 5, y + 4.6);
  doc.setTextColor(0, 0, 0);
  return y + 6.5;
}

const pdfBase = (doc) => ({
  margin: { top: TOP, bottom: BOTTOM, left: MX, right: MX },
  theme: "grid",
  styles: { font: "times", fontSize: 9, cellPadding: 1.8, lineColor: [150, 160, 170], lineWidth: 0.2, textColor: [20, 20, 20], overflow: "linebreak" },
  headStyles: { fillColor: NAVY, textColor: 255, fontStyle: "bold", halign: "center" },
  didDrawPage: () => pdfLetterhead(doc),
});

function pdfKV(doc, y, rows) {
  autoTable(doc, {
    ...pdfBase(doc),
    startY: y,
    body: rows,
    columnStyles: { 0: { cellWidth: 55, fontStyle: "bold", fillColor: LABEL_FILL } },
  });
  return doc.lastAutoTable.finalY;
}

function pdfLines(doc, y, lines, minLines = 3) {
  const w = PW - MX * 2;
  const all = [...lines];
  doc.setFont("times", "normal");
  doc.setFontSize(9.5);
  y += 2;
  const wrapped = [];
  all.forEach((l) => doc.splitTextToSize(l, w - 4).forEach((x) => wrapped.push(x)));
  while (wrapped.length < minLines) wrapped.push("");
  wrapped.forEach((line) => {
    y = pdfEnsure(doc, y, 7);
    if (line) doc.text(line, MX + 2, y + 4.2);
    doc.setDrawColor(170, 170, 170);
    doc.setLineDashPattern([0.6, 0.8], 0);
    doc.setLineWidth(0.2);
    doc.line(MX, y + 5.6, MX + w, y + 5.6);
    doc.setLineDashPattern([], 0);
    y += 6.4;
  });
  return y;
}

function pdfCheck(doc, cell) {
  const cx = cell.x + cell.width / 2, cy = cell.y + cell.height / 2;
  doc.setDrawColor(...NAVY);
  doc.setLineWidth(0.6);
  doc.line(cx - 1.8, cy, cx - 0.5, cy + 1.4);
  doc.line(cx - 0.5, cy + 1.4, cx + 2, cy - 1.6);
}

function pdfRenderUnit(doc, m, first) {
  if (!first) { doc.addPage(); }
  pdfLetterhead(doc);
  let y = TOP;

  // Judul
  doc.setFont("times", "bold");
  doc.setFontSize(14);
  doc.setTextColor(...NAVY);
  doc.text(m.title, PW / 2, y + 2, { align: "center" });
  doc.setDrawColor(...YELLOW);
  doc.setLineWidth(0.9);
  doc.line(PW / 2 - 40, y + 4.2, PW / 2 + 40, y + 4.2);
  doc.setFont("times", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(60, 60, 60);
  const meta = [m.nomor ? `Nomor: ${m.nomor}` : null, `Unit: ${m.unitLabel}`].filter(Boolean).join("     ·     ");
  doc.text(meta, PW / 2, y + 9, { align: "center" });
  doc.setTextColor(0, 0, 0);
  y += 13;

  y = pdfSection(doc, y, "DATA UMUM");
  y = pdfKV(doc, y, m.dataUmum) + 4;

  y = pdfSection(doc, y, "FORM HOUR METER HARIAN OPERATOR  —  IDENTITAS OPERATOR");
  y = pdfKV(doc, y, m.identitasOperator) + 4;

  y = pdfSection(doc, y, "HOUR METER ALAT BERAT  —  IDENTITAS ALAT");
  y = pdfKV(doc, y, m.identitasAlat) + 4;

  y = pdfSection(doc, y, "REKAP BULANAN HOUR METER", 30);
  autoTable(doc, {
    ...pdfBase(doc),
    startY: y,
    head: [m.rekapHead],
    body: pdfSmartPad(y, m.rekap, MIN_REKAP_ROWS, 6, 8),
    foot: [m.rekapTotal],
    showFoot: "lastPage",
    footStyles: { fillColor: YELLOW, textColor: NAVY, fontStyle: "bold", halign: "center" },
    columnStyles: { 0: { halign: "center", cellWidth: 24 }, 1: { halign: "right", cellWidth: 24 }, 2: { halign: "right", cellWidth: 24 }, 3: { halign: "right", cellWidth: 22 }, 4: { cellWidth: 38 } },
    bodyStyles: { minCellHeight: 6 },
  });
  y = doc.lastAutoTable.finalY + 4;

  y = pdfSection(doc, y, "TOTAL PEMAKAIAN JAM ALAT", 34);
  autoTable(doc, {
    ...pdfBase(doc),
    startY: y,
    head: [["Uraian", "Jumlah"]],
    body: m.totalPemakaian,
    columnStyles: { 0: { cellWidth: 100, fontStyle: "bold", fillColor: LABEL_FILL }, 1: { halign: "right" } },
  });
  y = doc.lastAutoTable.finalY + 4;

  y = pdfSection(doc, y, "KETERANGAN TAMBAHAN");
  y = pdfLines(doc, y, m.keteranganTambahan ? m.keteranganTambahan.split("\n") : [], 3) + 3;

  y = pdfSection(doc, y, "DETAIL PENGGANTIAN SPARE PART", 30);
  autoTable(doc, {
    ...pdfBase(doc),
    startY: y,
    head: [m.sparepartHead],
    body: pdfSmartPad(y, m.sparepart, MIN_SP_ROWS, 7, 12),
    foot: [["", "TOTAL SPARE PART", "", "", "", m.sparepartTotal, ""]],
    showFoot: "lastPage",
    footStyles: { fillColor: YELLOW, textColor: NAVY, fontStyle: "bold" },
    styles: { ...pdfBase(doc).styles, fontSize: 8.5 },
    columnStyles: { 0: { halign: "center", cellWidth: 9 }, 1: { cellWidth: 48 }, 2: { halign: "right", cellWidth: 24 }, 3: { halign: "right", cellWidth: 12 }, 4: { halign: "right", cellWidth: 27 }, 5: { halign: "right", cellWidth: 29 }, 6: { halign: "center" } },
    bodyStyles: { minCellHeight: 6 },
  });
  y = doc.lastAutoTable.finalY + 4;

  y = pdfSection(doc, y, "TOTAL BIAYA PENGGANTIAN", 40);
  autoTable(doc, {
    ...pdfBase(doc),
    startY: y,
    head: [["Uraian", "Nilai (Rp)"]],
    body: m.totalBiaya,
    foot: [["TOTAL", m.totalBiayaSum]],
    footStyles: { fillColor: YELLOW, textColor: NAVY, fontStyle: "bold" },
    columnStyles: { 0: { cellWidth: 100, fontStyle: "bold", fillColor: LABEL_FILL }, 1: { halign: "right" } },
    didParseCell: (d) => { if (d.section === "foot" && d.column.index === 1) d.cell.styles.halign = "right"; },
  });
  y = doc.lastAutoTable.finalY + 4;

  y = pdfSection(doc, y, "KONDISI ALAT", 48);
  autoTable(doc, {
    ...pdfBase(doc),
    startY: y,
    head: [["Pemeriksaan", "Baik", "Tidak", "Keterangan"]],
    body: m.kondisi.map((k) => [k.label, "", "", k.keterangan]),
    columnStyles: { 0: { cellWidth: 55, fontStyle: "bold", fillColor: LABEL_FILL }, 1: { cellWidth: 20, halign: "center" }, 2: { cellWidth: 20, halign: "center" } },
    didDrawCell: (d) => {
      if (d.section !== "body") return;
      const k = m.kondisi[d.row.index];
      if ((d.column.index === 1 && k.baik) || (d.column.index === 2 && k.tidak)) pdfCheck(doc, d.cell);
    },
  });
  y = doc.lastAutoTable.finalY + 4;

  y = pdfSection(doc, y, "CATATAN OPERATOR");
  y = pdfLines(doc, y, m.catatan, 3) + 3;

  y = pdfSection(doc, y, "PETUNJUK PENGISIAN", 40);
  doc.setFont("times", "normal");
  doc.setFontSize(9.5);
  y += 2;
  PETUNJUK.forEach((p, i) => {
    y = pdfEnsure(doc, y, 6);
    doc.text(`${i + 1}.`, MX + 2, y + 4);
    doc.text(p, MX + 8, y + 4);
    y += 5.2;
  });
  y += 4;

  // Tanda tangan
  y = pdfEnsure(doc, y, 40);
  const colW = (PW - MX * 2) / 3;
  doc.setFontSize(9.5);
  doc.text(`Dicetak: ${m.printedAt}`, PW - MX, y, { align: "right" });
  y += 6;
  m.ttd.forEach((t, i) => {
    const cx = MX + colW * i + colW / 2;
    doc.setFont("times", "normal");
    doc.text(i === 2 ? "Mengetahui," : i === 0 ? "Dibuat oleh," : "Diperiksa oleh,", cx, y, { align: "center" });
    doc.setFont("times", "bold");
    doc.text(i === 2 ? "Pimpinan" : t.role, cx, y + 5, { align: "center" });
    doc.setDrawColor(60, 60, 60);
    doc.setLineWidth(0.3);
    doc.line(cx - 25, y + 27, cx + 25, y + 27);
    doc.setFont("times", "normal");
    doc.text(i === 2 ? COMPANY.legalName : (t.name || "(..............................)"), cx, y + 31.5, { align: "center" });
  });
}

export function exportHourMeterPDF(reports, metaOrFn, filename) {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  reports.forEach((r, i) => pdfRenderUnit(doc, buildHourMeterModel(r, typeof metaOrFn === "function" ? metaOrFn(r) : metaOrFn), i === 0));
  // nomor halaman
  const total = doc.getNumberOfPages();
  for (let p = 1; p <= total; p++) {
    doc.setPage(p);
    doc.setFont("times", "italic");
    doc.setFontSize(8);
    doc.setTextColor(...NAVY);
    doc.text(`Halaman ${p} / ${total}`, PW - MX, PH - FOOTER_H * 0.45, { align: "right" });
  }
  doc.save(`${filename}.pdf`);
}

// =====================================================================
//  EXCEL (exceljs)
// =====================================================================
const XL_NAVY = "FF022D42";
const XL_YELLOW = "FFFEC202";
const XL_LABEL = "FFEEF2F6";
const XL_FONT = "Times New Roman";
const XL_COLS = [7, 26, 15, 12, 17, 19, 22]; // A..G
const thin = { style: "thin", color: { argb: "FF8A97A3" } };
const allBorders = { top: thin, left: thin, bottom: thin, right: thin };

function xlCell(ws, addr, value, opts = {}) {
  const c = ws.getCell(addr);
  c.value = value;
  c.font = { name: XL_FONT, size: opts.size || 10, bold: !!opts.bold, italic: !!opts.italic, color: { argb: opts.color || "FF141414" } };
  c.alignment = { vertical: "middle", horizontal: opts.align || "left", wrapText: true };
  if (opts.fill) c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: opts.fill } };
  if (opts.border !== false) c.border = allBorders;
  return c;
}

// tulis sel dengan merge range (kolom 1-based)
function xlPut(ws, row, c1, c2, value, opts) {
  const a = ws.getCell(row, c1).address;
  if (c2 > c1) {
    ws.mergeCells(row, c1, row, c2);
    for (let c = c1; c <= c2; c++) { const x = ws.getCell(row, c); if (opts?.border !== false) x.border = allBorders; if (opts?.fill) x.fill = { type: "pattern", pattern: "solid", fgColor: { argb: opts.fill } }; }
  }
  return xlCell(ws, a, value, opts);
}

function xlSection(ws, row, text) {
  ws.getRow(row).height = 20;
  xlPut(ws, row, 1, 7, text, { bold: true, color: "FFFFFFFF", fill: XL_NAVY, size: 11, border: false });
  ws.getCell(row, 1).border = { left: { style: "thick", color: { argb: XL_YELLOW } } };
  return row + 1;
}

function xlKV(ws, row, rows) {
  rows.forEach(([k, v]) => {
    xlPut(ws, row, 1, 3, k, { bold: true, fill: XL_LABEL });
    xlPut(ws, row, 4, 7, v);
    ws.getRow(row).height = 18;
    row++;
  });
  return row + 1;
}

function xlTable(ws, row, head, body, spans, aligns = [], foot) {
  const put = (r, vals, opts) => {
    let col = 1;
    vals.forEach((v, i) => {
      const span = spans[i];
      xlPut(ws, r, col, col + span - 1, v, { ...opts, align: opts.head ? "center" : (aligns[i] || "left") });
      col += span;
    });
    ws.getRow(r).height = opts.head ? 30 : 17;
  };
  put(row++, head, { bold: true, color: "FFFFFFFF", fill: XL_NAVY, head: true });
  body.forEach((b) => put(row++, b, {}));
  if (foot) put(row++, foot, { bold: true, fill: XL_YELLOW, color: XL_NAVY });
  return row + 1;
}

function xlLines(ws, row, lines, min = 3) {
  const all = [...lines];
  while (all.length < min) all.push("");
  all.forEach((l) => {
    xlPut(ws, row, 1, 7, l, { border: false });
    for (let c = 1; c <= 7; c++) ws.getCell(row, c).border = { bottom: { style: "dotted", color: { argb: "FF9AA5B1" } } };
    ws.getRow(row).height = 18;
    row++;
  });
  return row + 1;
}

function xlRenderUnit(wb, m, sheetName, imgHeader, imgFooter) {
  const ws = wb.addWorksheet(sheetName, {
    pageSetup: { paperSize: 9, orientation: "portrait", fitToPage: true, fitToWidth: 1, fitToHeight: 0, margins: { left: 0.3, right: 0.3, top: 0.3, bottom: 0.3, header: 0, footer: 0 } },
    views: [{ showGridLines: false }],
  });
  ws.columns = XL_COLS.map((w) => ({ width: w }));
  const totalPx = XL_COLS.reduce((a, b) => a + b, 0) * 7.2;

  // Kop
  for (let r = 1; r <= 5; r++) ws.getRow(r).height = 18;
  ws.addImage(imgHeader, { tl: { col: 0, row: 0 }, ext: { width: totalPx, height: totalPx * LH_HEADER_RATIO } });
  let row = 7;
  xlPut(ws, row, 1, 7, m.title, { bold: true, size: 14, align: "center", color: XL_NAVY, border: false });
  ws.getRow(row).height = 22; row++;
  xlPut(ws, row, 1, 7, [m.nomor ? `Nomor: ${m.nomor}` : null, `Unit: ${m.unitLabel}`].filter(Boolean).join("   ·   "), { align: "center", border: false, italic: true });
  row += 2;

  row = xlSection(ws, row, "DATA UMUM");
  row = xlKV(ws, row, m.dataUmum);
  row = xlSection(ws, row, "FORM HOUR METER HARIAN OPERATOR — IDENTITAS OPERATOR");
  row = xlKV(ws, row, m.identitasOperator);
  row = xlSection(ws, row, "HOUR METER ALAT BERAT — IDENTITAS ALAT");
  row = xlKV(ws, row, m.identitasAlat);

  row = xlSection(ws, row, "REKAP BULANAN HOUR METER");
  row = xlTable(ws, row, m.rekapHead, padRows(m.rekap, MIN_REKAP_ROWS, 6), [2, 1, 1, 1, 1, 1], ["center", "right", "right", "right", "left", "left"], m.rekapTotal);

  row = xlSection(ws, row, "TOTAL PEMAKAIAN JAM ALAT");
  row = xlTable(ws, row, ["Uraian", "Jumlah"], m.totalPemakaian, [4, 3], ["left", "right"]);

  row = xlSection(ws, row, "KETERANGAN TAMBAHAN");
  row = xlLines(ws, row, m.keteranganTambahan ? m.keteranganTambahan.split("\n") : []);

  row = xlSection(ws, row, "DETAIL PENGGANTIAN SPARE PART");
  row = xlTable(ws, row, m.sparepartHead, padRows(m.sparepart, MIN_SP_ROWS, 7), [1, 1, 1, 1, 1, 1, 1], ["center", "left", "right", "right", "right", "right", "center"], ["", "TOTAL SPARE PART", "", "", "", m.sparepartTotal, ""]);

  row = xlSection(ws, row, "TOTAL BIAYA PENGGANTIAN");
  row = xlTable(ws, row, ["Uraian", "Nilai (Rp)"], m.totalBiaya, [4, 3], ["left", "right"], ["TOTAL", m.totalBiayaSum]);

  row = xlSection(ws, row, "KONDISI ALAT");
  row = xlTable(ws, row, ["Pemeriksaan", "Baik", "Tidak", "Keterangan"], m.kondisi.map((k) => [k.label, k.baik ? "✓" : "", k.tidak ? "✓" : "", k.keterangan]), [2, 1, 1, 3], ["left", "center", "center", "left"]);

  row = xlSection(ws, row, "CATATAN OPERATOR");
  row = xlLines(ws, row, m.catatan);

  row = xlSection(ws, row, "PETUNJUK PENGISIAN");
  PETUNJUK.forEach((p, i) => { xlPut(ws, row, 1, 7, `${i + 1}. ${p}`, { border: false }); row++; });
  row += 1;

  // TTD
  xlPut(ws, row, 5, 7, `Dicetak: ${m.printedAt}`, { border: false, align: "right", italic: true });
  row += 1;
  const groups = [[1, 2], [3, 5], [6, 7]];
  const lbl = ["Dibuat oleh,", "Diperiksa oleh,", "Mengetahui,"];
  const role = ["Operator", "Pengawas Lapangan", "Pimpinan"];
  groups.forEach(([a, b], i) => {
    xlPut(ws, row, a, b, lbl[i], { border: false, align: "center" });
    xlPut(ws, row + 1, a, b, role[i], { border: false, align: "center", bold: true });
    xlPut(ws, row + 5, a, b, i === 2 ? COMPANY.legalName : (m.ttd[i].name || "(..............................)"), { border: false, align: "center" });
    for (let c = a; c <= b; c++) ws.getCell(row + 5, c).border = { top: thin };
  });
  for (let r = row + 2; r <= row + 4; r++) ws.getRow(r).height = 18;
  row += 7;

  ws.addImage(imgFooter, { tl: { col: 0, row: row }, ext: { width: totalPx, height: totalPx * LH_FOOTER_RATIO } });
  ws.pageSetup.printArea = `A1:G${row + 5}`;
}

export async function exportHourMeterExcel(reports, metaOrFn, filename) {
  const wb = new ExcelJS.Workbook();
  wb.creator = COMPANY.legalName;
  wb.created = new Date();
  const imgHeader = wb.addImage({ base64: LH_HEADER, extension: "jpeg" });
  const imgFooter = wb.addImage({ base64: LH_FOOTER, extension: "jpeg" });
  const used = new Set();
  reports.forEach((r) => {
    let name = `${r.unit_name} ${r.nomor_lambung}`.replace(/[\\/?*[\]:]/g, "-").slice(0, 28) || "Unit";
    let n = name, i = 2;
    while (used.has(n)) n = `${name.slice(0, 26)}-${i++}`;
    used.add(n);
    xlRenderUnit(wb, buildHourMeterModel(r, typeof metaOrFn === "function" ? metaOrFn(r) : metaOrFn), n, imgHeader, imgFooter);
  });
  const buf = await wb.xlsx.writeBuffer();
  saveAs(new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${filename}.xlsx`);
}

// =====================================================================
//  WORD (docx)
// =====================================================================
const W_NAVY = "022D42";
const W_YELLOW = "FEC202";
const W_LABEL = "EEF2F6";
const PAGE_W_TW = 11906, PAGE_H_TW = 16838;
const MARGIN_TW = 1000;
const CONTENT_TW = PAGE_W_TW - MARGIN_TW * 2;
const EMU_PX = 9525;
const PAGE_W_PX = 794, PAGE_H_PX = 1123;
const wBorder = { style: BorderStyle.SINGLE, size: 4, color: "8A97A3" };
const wBorders = { top: wBorder, bottom: wBorder, left: wBorder, right: wBorder };

const b64ToBytes = (dataUrl) => {
  const bin = atob(dataUrl.split(",")[1]);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
};

const wRun = (text, o = {}) => new TextRun({ text: String(text ?? ""), font: "Times New Roman", size: o.size || 20, bold: !!o.bold, italics: !!o.italic, color: o.color || "141414" });
const wPara = (text, o = {}) => new Paragraph({ alignment: o.align || AlignmentType.LEFT, spacing: { before: o.before ?? 0, after: o.after ?? 0 }, children: [wRun(text, o)] });

function wCell(text, o = {}) {
  return new TableCell({
    children: String(text ?? "").split("\n").map((t) => wPara(t, o)),
    width: { size: o.width, type: WidthType.DXA },
    columnSpan: o.span,
    shading: o.fill ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    borders: wBorders,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
  });
}

function wTable(widths, head, body, aligns = [], foot) {
  const total = widths.reduce((a, b) => a + b, 0);
  const rows = [];
  const mk = (vals, o) => new TableRow({
    tableHeader: !!o.head,
    children: vals.map((v, i) => wCell(v, { width: widths[i], align: o.head ? AlignmentType.CENTER : (aligns[i] || AlignmentType.LEFT), ...o })),
  });
  if (head) rows.push(mk(head, { head: true, bold: true, color: "FFFFFF", fill: W_NAVY }));
  body.forEach((b) => rows.push(mk(b, {})));
  if (foot) rows.push(mk(foot, { bold: true, fill: W_YELLOW, color: W_NAVY }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows });
}

function wKV(rows) {
  const w = [3200, CONTENT_TW - 3200];
  return new Table({
    width: { size: CONTENT_TW, type: WidthType.DXA },
    columnWidths: w,
    rows: rows.map(([k, v]) => new TableRow({ children: [wCell(k, { width: w[0], bold: true, fill: W_LABEL }), wCell(v, { width: w[1] })] })),
  });
}

function wSection(text) {
  return new Paragraph({
    spacing: { before: 220, after: 80 },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: W_NAVY },
    border: { left: { style: BorderStyle.SINGLE, size: 36, color: W_YELLOW, space: 4 } },
    children: [wRun(` ${text}`, { bold: true, color: "FFFFFF", size: 21 })],
  });
}

function wLines(lines, min = 3) {
  const all = [...lines];
  while (all.length < min) all.push("");
  return all.map((l) => new Paragraph({
    spacing: { before: 60, after: 60 },
    border: { bottom: { style: BorderStyle.DOTTED, size: 6, color: "9AA5B1", space: 2 } },
    children: [wRun(l || " ")],
  }));
}

function wUnitChildren(m, first, idx = 0) {
  const C = [];
  C.push(new Paragraph({ pageBreakBefore: !first, alignment: AlignmentType.CENTER, spacing: { after: 40 }, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: W_YELLOW, space: 2 } }, children: [wRun(m.title, { bold: true, size: 28, color: W_NAVY })] }));
  C.push(wPara([m.nomor ? `Nomor: ${m.nomor}` : null, `Unit: ${m.unitLabel}`].filter(Boolean).join("   ·   "), { align: AlignmentType.CENTER, italic: true, after: 80, before: 60 }));

  C.push(wSection("DATA UMUM"), wKV(m.dataUmum));
  C.push(wSection("FORM HOUR METER HARIAN OPERATOR — IDENTITAS OPERATOR"), wKV(m.identitasOperator));
  C.push(wSection("HOUR METER ALAT BERAT — IDENTITAS ALAT"), wKV(m.identitasAlat));

  const A = AlignmentType;
  C.push(wSection("REKAP BULANAN HOUR METER"));
  C.push(wTable([1500, 1450, 1450, 1350, 2000, CONTENT_TW - 7750], m.rekapHead, padRows(m.rekap, MIN_REKAP_ROWS, 6), [A.CENTER, A.RIGHT, A.RIGHT, A.RIGHT, A.LEFT, A.LEFT], m.rekapTotal));

  C.push(wSection("TOTAL PEMAKAIAN JAM ALAT"));
  C.push(wTable([5600, CONTENT_TW - 5600], ["Uraian", "Jumlah"], m.totalPemakaian, [A.LEFT, A.RIGHT]));

  C.push(wSection("KETERANGAN TAMBAHAN"), ...wLines(m.keteranganTambahan ? m.keteranganTambahan.split("\n") : []));

  C.push(wSection("DETAIL PENGGANTIAN SPARE PART"));
  C.push(wTable([550, 2650, 1300, 700, 1500, 1600, CONTENT_TW - 8300], m.sparepartHead, padRows(m.sparepart, MIN_SP_ROWS, 7), [A.CENTER, A.LEFT, A.RIGHT, A.RIGHT, A.RIGHT, A.RIGHT, A.CENTER], ["", "TOTAL SPARE PART", "", "", "", m.sparepartTotal, ""]));

  C.push(wSection("TOTAL BIAYA PENGGANTIAN"));
  C.push(wTable([5600, CONTENT_TW - 5600], ["Uraian", "Nilai (Rp)"], m.totalBiaya, [A.LEFT, A.RIGHT], ["TOTAL", m.totalBiayaSum]));

  C.push(wSection("KONDISI ALAT"));
  C.push(wTable([3000, 1100, 1100, CONTENT_TW - 5200], ["Pemeriksaan", "Baik", "Tidak", "Keterangan"], m.kondisi.map((k) => [k.label, k.baik ? "✓" : "", k.tidak ? "✓" : "", k.keterangan]), [A.LEFT, A.CENTER, A.CENTER, A.LEFT]));

  C.push(wSection("CATATAN OPERATOR"), ...wLines(m.catatan));

  C.push(wSection("PETUNJUK PENGISIAN"));
  PETUNJUK.forEach((p) => C.push(new Paragraph({ numbering: { reference: "petunjuk", level: 0, instance: idx + 1 }, spacing: { after: 30 }, children: [wRun(p)] })));

  // TTD
  C.push(wPara(`Dicetak: ${m.printedAt}`, { align: AlignmentType.RIGHT, italic: true, before: 240, after: 120 }));
  const third = Math.floor(CONTENT_TW / 3);
  const noB = { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } };
  const lbl = ["Dibuat oleh,", "Diperiksa oleh,", "Mengetahui,"];
  const role = ["Operator", "Pengawas Lapangan", "Pimpinan"];
  C.push(new Table({
    width: { size: third * 3, type: WidthType.DXA },
    columnWidths: [third, third, third],
    rows: [new TableRow({
      children: [0, 1, 2].map((i) => new TableCell({
        width: { size: third, type: WidthType.DXA },
        borders: noB,
        children: [
          wPara(lbl[i], { align: AlignmentType.CENTER }),
          wPara(role[i], { align: AlignmentType.CENTER, bold: true, after: 900 }),
          wPara(i === 2 ? COMPANY.legalName : (m.ttd[i].name || "(..............................)"), { align: AlignmentType.CENTER, bold: i !== 2 }),
        ],
      })),
    })],
  }));
  return C;
}

export async function exportHourMeterDocx(reports, metaOrFn, filename) {
  const hdr = b64ToBytes(LH_HEADER);
  const ftr = b64ToBytes(LH_FOOTER);
  const hH = Math.round(PAGE_W_PX * LH_HEADER_RATIO);
  const fH = Math.round(PAGE_W_PX * LH_FOOTER_RATIO);
  const floatImg = (data, h, vOffsetPx) => new ImageRun({
    type: "jpg",
    data,
    transformation: { width: PAGE_W_PX, height: h },
    floating: {
      horizontalPosition: { relative: HorizontalPositionRelativeFrom.PAGE, offset: 0 },
      verticalPosition: { relative: VerticalPositionRelativeFrom.PAGE, offset: vOffsetPx * EMU_PX },
      wrap: { type: TextWrappingType.NONE },
      behindDocument: true,
      allowOverlap: true,
    },
  });

  const children = [];
  reports.forEach((r, i) => children.push(...wUnitChildren(buildHourMeterModel(r, typeof metaOrFn === "function" ? metaOrFn(r) : metaOrFn), i === 0, i)));

  const doc = new Document({
    creator: COMPANY.legalName,
    title: "Form Hour Meter Operator & Alat Berat",
    styles: { default: { document: { run: { font: "Times New Roman", size: 20 } } } },
    numbering: { config: [{ reference: "petunjuk", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
    sections: [{
      properties: {
        page: {
          size: { width: PAGE_W_TW, height: PAGE_H_TW },
          margin: { top: Math.round((hH + 22) * 15), bottom: Math.round((fH + 18) * 15), left: MARGIN_TW, right: MARGIN_TW, header: 0, footer: 0 },
        },
      },
      headers: { default: new Header({ children: [new Paragraph({ children: [floatImg(hdr, hH, 0)] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ children: [floatImg(ftr, fH, PAGE_H_PX - fH)] })] }) },
      children,
    }],
  });
  const blob = await Packer.toBlob(doc);
  saveAs(blob, `${filename}.docx`);
}
