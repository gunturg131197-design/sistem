import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { LH_HEADER, LH_HEADER_RATIO, LH_FOOTER, LH_FOOTER_RATIO } from "./letterhead";

// ---------- Excel ----------
export function exportToExcel(rows, filename, sheetName = "Data") {
  const ws = XLSX.utils.json_to_sheet(rows && rows.length ? rows : [{ Info: "Tidak ada data" }]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  XLSX.writeFile(wb, `${filename}.xlsx`);
}

export function exportToExcelMultiSheet(sheets, filename) {
  const wb = XLSX.utils.book_new();
  sheets.forEach(({ name, rows }) => {
    const ws = XLSX.utils.json_to_sheet(rows && rows.length ? rows : [{ Info: "Tidak ada data" }]);
    XLSX.utils.book_append_sheet(wb, ws, (name || "Sheet").slice(0, 31));
  });
  XLSX.writeFile(wb, `${filename}.xlsx`);
}

// ---------- PDF (kop surat TRIRARA TUNGGAL PUTRA) ----------
const PAGE_W = 210;   // A4 portrait mm
const PAGE_H = 297;
const HEADER_H = PAGE_W * LH_HEADER_RATIO;   // ~53.5mm
const FOOTER_H = PAGE_W * LH_FOOTER_RATIO;   // ~27.5mm
const MARGIN_TOP = HEADER_H + 6;
const MARGIN_BOTTOM = FOOTER_H + 6;
const MARGIN_X = 14;

const NAVY = [26, 42, 68];
const YELLOW = [234, 179, 8];

function idr(n) {
  if (n === null || n === undefined || n === "") return "Rp 0";
  return "Rp " + Number(n).toLocaleString("id-ID");
}

function drawLetterhead(doc) {
  doc.addImage(LH_HEADER, "JPEG", 0, 0, PAGE_W, HEADER_H);
  doc.addImage(LH_FOOTER, "JPEG", 0, PAGE_H - FOOTER_H, PAGE_W, FOOTER_H);
}

function newDoc() {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  return doc;
}

// Judul dokumen di dalam area aman (di bawah kop)
function drawTitle(doc, title, subtitle) {
  doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text(title, MARGIN_X, MARGIN_TOP);
  if (subtitle) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(90, 90, 90);
    doc.text(subtitle, MARGIN_X, MARGIN_TOP + 5.5);
  }
  doc.setTextColor(0, 0, 0);
  return MARGIN_TOP + (subtitle ? 10 : 5);
}

const baseTableOpts = (doc) => ({
  margin: { top: MARGIN_TOP, bottom: MARGIN_BOTTOM, left: MARGIN_X, right: MARGIN_X },
  styles: { fontSize: 8, cellPadding: 2, overflow: "linebreak" },
  headStyles: { fillColor: NAVY, textColor: 255, fontStyle: "bold" },
  alternateRowStyles: { fillColor: [245, 246, 248] },
  didDrawPage: () => drawLetterhead(doc),
});

function ensureSpace(doc, y, needed) {
  if (y + needed > PAGE_H - MARGIN_BOTTOM) {
    doc.addPage();
    drawLetterhead(doc);
    return MARGIN_TOP;
  }
  return y;
}

function sectionTitle(doc, y, text) {
  y = ensureSpace(doc, y, 12);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
  doc.text(text, MARGIN_X, y);
  // garis aksen kuning
  doc.setDrawColor(YELLOW[0], YELLOW[1], YELLOW[2]);
  doc.setLineWidth(0.8);
  doc.line(MARGIN_X, y + 1.5, MARGIN_X + 30, y + 1.5);
  doc.setTextColor(0, 0, 0);
  return y + 4;
}

// Tabel generik dengan kop
export function exportToPDF({ title, columns, rows, filename }) {
  const doc = newDoc();
  const startY = drawTitle(doc, title, `Digenerate: ${new Date().toLocaleString("id-ID")}`);
  autoTable(doc, {
    head: [columns],
    body: rows,
    startY: startY + 3,
    ...baseTableOpts(doc),
  });
  doc.save(`${filename}.pdf`);
}

// Laporan lengkap satu unit
export function exportUnitReportPDF(report, filename) {
  const doc = newDoc();
  let y = drawTitle(doc, `Laporan Unit — ${report.unit_label}`, `Serial: ${report.serial_number || "-"}   |   Digenerate: ${new Date().toLocaleString("id-ID")}`);

  // Ringkasan
  const summary = [
    ["Operator Utama", report.operator_utama || "-"],
    ["Operator Terlibat", (report.operators || []).join(", ") || "-"],
    ["Total Cars Baru", String(report.total_cars)],
    ["HM Awal", String(report.hm_awal)],
    ["HM Akhir", String(report.hm_akhir)],
    ["Total HM (Jam)", String(report.total_hm)],
    ["Total Gaji Operator", idr(report.total_gaji)],
    ["Total Kasbon", idr(report.total_kasbon)],
    ["Total Gaji Bersih", idr(report.total_gaji_bersih)],
    ["Total Penggantian Sparepart", idr(report.total_sparepart)],
  ];
  y = sectionTitle(doc, y + 2, "Ringkasan Unit");
  autoTable(doc, { head: [["Keterangan", "Nilai"]], body: summary, startY: y + 2, ...baseTableOpts(doc) });
  y = doc.lastAutoTable.finalY + 4;

  // Operasional
  y = sectionTitle(doc, y, "Operasional");
  autoTable(doc, {
    head: [["Tanggal", "Operator", "Pengurus", "HM Awal", "HM Akhir", "Total Jam", "Cars"]],
    body: (report.operations || []).map(o => [o.tanggal, o.operator_name, o.pengurus || "-", o.hour_meter_awal, o.hour_meter_akhir, o.total_jam, o.jumlah_cars]),
    startY: y + 2,
    ...baseTableOpts(doc),
  });
  y = doc.lastAutoTable.finalY + 4;

  // Gaji
  y = sectionTitle(doc, y, "Gaji Operator");
  autoTable(doc, {
    head: [["Periode", "Operator", "Tarif/Jam", "Jam Dibayar", "Gaji", "Kasbon", "Gaji Bersih"]],
    body: (report.payroll || []).map(p => [p.periode, p.operator_name, idr(p.tarif_per_jam), p.jam_dibayar, idr(p.gaji), idr(p.kasbon), idr(p.gaji_bersih)]),
    startY: y + 2,
    ...baseTableOpts(doc),
  });
  y = doc.lastAutoTable.finalY + 4;

  // Sparepart
  y = sectionTitle(doc, y, "Penggantian Sparepart");
  autoTable(doc, {
    head: [["Tanggal", "No Nota", "HM Service", "Sparepart", "Total Nota"]],
    body: (report.spareparts || []).map(s => [s.tanggal, s.nomor_nota, s.hm_service ?? "-", s.nama_sparepart || (s.items || []).map(i => i.nama_sparepart).join(", "), idr(s.biaya)]),
    startY: y + 2,
    ...baseTableOpts(doc),
  });

  doc.save(`${filename}.pdf`);
}
