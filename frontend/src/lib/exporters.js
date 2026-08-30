import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

export function exportToExcel(rows, filename, sheetName = "Data") {
  const ws = XLSX.utils.json_to_sheet(rows);
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

function idr(n) {
  if (n === null || n === undefined || n === "") return "Rp 0";
  return "Rp " + Number(n).toLocaleString("id-ID");
}

/**
 * Laporan lengkap satu unit menjadi PDF (ringkasan + operasional + sparepart + payroll).
 */
export function exportUnitReportPDF(report, filename) {
  const doc = new jsPDF({ orientation: "landscape" });
  let y = 14;
  doc.setFontSize(15);
  doc.text(`Laporan Unit — ${report.unit_label}`, 14, y); y += 6;
  doc.setFontSize(9);
  doc.text(`Serial: ${report.serial_number || "-"}   |   Generated: ${new Date().toLocaleString("id-ID")}`, 14, y); y += 6;

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
  autoTable(doc, {
    head: [["Ringkasan", "Nilai"]],
    body: summary,
    startY: y,
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [234, 179, 8], textColor: 0, fontStyle: "bold" },
  });
  y = doc.lastAutoTable.finalY + 6;

  // Operasional
  doc.setFontSize(11); doc.text("Operasional", 14, y); y += 2;
  autoTable(doc, {
    head: [["Tanggal", "Operator", "Pengurus", "HM Awal", "HM Akhir", "Total Jam", "Cars"]],
    body: (report.operations || []).map(o => [o.tanggal, o.operator_name, o.pengurus || "-", o.hour_meter_awal, o.hour_meter_akhir, o.total_jam, o.jumlah_cars]),
    startY: y + 2,
    styles: { fontSize: 8, cellPadding: 1.5 },
    headStyles: { fillColor: [234, 179, 8], textColor: 0, fontStyle: "bold" },
  });
  y = doc.lastAutoTable.finalY + 6;

  // Payroll
  doc.setFontSize(11); doc.text("Gaji Operator", 14, y); y += 2;
  autoTable(doc, {
    head: [["Periode", "Operator", "Tarif/Jam", "Jam Dibayar", "Gaji", "Kasbon", "Gaji Bersih"]],
    body: (report.payroll || []).map(p => [p.periode, p.operator_name, idr(p.tarif_per_jam), p.jam_dibayar, idr(p.gaji), idr(p.kasbon), idr(p.gaji_bersih)]),
    startY: y + 2,
    styles: { fontSize: 8, cellPadding: 1.5 },
    headStyles: { fillColor: [234, 179, 8], textColor: 0, fontStyle: "bold" },
  });
  y = doc.lastAutoTable.finalY + 6;

  // Sparepart
  doc.setFontSize(11); doc.text("Penggantian Sparepart", 14, y); y += 2;
  autoTable(doc, {
    head: [["Tanggal", "No Nota", "HM Service", "Sparepart", "Total Nota"]],
    body: (report.spareparts || []).map(s => [s.tanggal, s.nomor_nota, s.hm_service ?? "-", s.nama_sparepart || (s.items || []).map(i => i.nama_sparepart).join(", "), idr(s.biaya)]),
    startY: y + 2,
    styles: { fontSize: 8, cellPadding: 1.5 },
    headStyles: { fillColor: [234, 179, 8], textColor: 0, fontStyle: "bold" },
  });

  doc.save(`${filename}.pdf`);
}

export function exportToPDF({ title, columns, rows, filename }) {
  const doc = new jsPDF({ orientation: "landscape" });
  doc.setFontSize(14);
  doc.text(title, 14, 14);
  doc.setFontSize(9);
  doc.text(`Generated: ${new Date().toLocaleString("id-ID")}`, 14, 20);
  autoTable(doc, {
    head: [columns],
    body: rows,
    startY: 26,
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [234, 179, 8], textColor: 0, fontStyle: "bold" },
    alternateRowStyles: { fillColor: [245, 245, 245] },
  });
  doc.save(`${filename}.pdf`);
}
