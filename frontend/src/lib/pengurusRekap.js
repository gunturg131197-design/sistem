// =====================================================================
//  REKAP PENGHASILAN PENGURUS — export PDF (A4 landscape) & Excel berkop
// =====================================================================
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import ExcelJS from "exceljs";
import { saveAs } from "file-saver";
import { LH_HEADER, LH_HEADER_RATIO, LH_FOOTER, LH_FOOTER_RATIO } from "./letterhead";
import { COMPANY } from "./company";

const NAVY = [2, 45, 66];
const YELLOW = [254, 194, 2];
const XL_NAVY = "FF022D42";
const XL_SOFT = "FFF3F5F8";
const MON = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export const METRICS = [
  ["jam", "Jam Kerja (HM)"],
  ["pendapatan", "Pendapatan (HM × Tarif)"],
  ["gaji", "Gaji Operator"],
  ["sparepart", "Sparepart"],
  ["bersih", "Penghasilan Bersih"],
];

const num = (n) => Number(n || 0).toLocaleString("id-ID", { maximumFractionDigits: 2 });
const rp = (n) => (Number(n || 0) < 0 ? "-Rp " : "Rp ") + Math.abs(Number(n || 0)).toLocaleString("id-ID", { maximumFractionDigits: 0 });
export const fmtMetric = (k, v) => (k === "jam" ? num(v) : rp(v));
const dateLong = () => new Date().toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });

// Baris tabel detail: setiap pengurus = 5 baris metrik × 12 bulan + total
function detailRows(data) {
  const out = [];
  data.rows.forEach((r, idx) => {
    METRICS.forEach(([k, label], i) => {
      out.push({
        no: i === 0 ? String(idx + 1) : "",
        nama: i === 0 ? r.nama : "",
        metric: label,
        key: k,
        vals: r.months.map((m) => m[k]),
        total: r.total[k],
        first: i === 0,
        last: i === METRICS.length - 1,
      });
    });
  });
  METRICS.forEach(([k, label], i) => {
    out.push({ no: "", nama: i === 0 ? "TOTAL SEMUA" : "", metric: label, key: k, vals: data.months.map((m) => m[k]), total: data.total[k], grand: true, first: i === 0, last: i === METRICS.length - 1 });
  });
  return out;
}

export function exportPengurusRekapPDF(data, meta, filename) {
  const W = 297, H = 210, mx = 8;
  const hh = W * LH_HEADER_RATIO * 0.6, fh = W * LH_FOOTER_RATIO * 0.6;
  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const kop = () => {
    doc.addImage(LH_HEADER, "JPEG", 0, 0, W, hh);
    doc.addImage(LH_FOOTER, "JPEG", 0, H - fh, W, fh);
  };
  kop();
  let y = hh + 6;
  doc.setFont("times", "bold"); doc.setFontSize(14); doc.setTextColor(...NAVY);
  doc.text("REKAP PENGHASILAN PENGURUS EXCAVATOR", W / 2, y, { align: "center" });
  doc.setDrawColor(...YELLOW); doc.setLineWidth(0.9); doc.line(W / 2 - 45, y + 1.8, W / 2 + 45, y + 1.8);
  doc.setFont("times", "normal"); doc.setFontSize(9); doc.setTextColor(60, 60, 60);
  doc.text([`Perusahaan: ${COMPANY.legalName}`, `Tahun: ${data.year}`, meta?.nomor ? `Nomor: ${meta.nomor}` : null].filter(Boolean).join("     ·     "), W / 2, y + 6.5, { align: "center" });
  y += 10;

  // Ringkasan per pengurus (tahunan)
  autoTable(doc, {
    startY: y,
    margin: { top: hh + 6, bottom: fh + 6, left: mx, right: mx },
    theme: "grid",
    head: [["No", "Pengurus", "Tarif/Jam", "Unit Diurus", "Total Jam", "Pendapatan", "Gaji Operator", "Sparepart", "Penghasilan Bersih"]],
    body: [
      ...data.rows.map((r, i) => [i + 1, r.nama, r.tarif_pengurus ? rp(r.tarif_pengurus) : "per unit", (r.units || []).join(", ") || "-", num(r.total.jam), rp(r.total.pendapatan), rp(r.total.gaji), rp(r.total.sparepart), rp(r.total.bersih)]),
      ["", "TOTAL", "", "", num(data.total.jam), rp(data.total.pendapatan), rp(data.total.gaji), rp(data.total.sparepart), rp(data.total.bersih)],
    ],
    styles: { font: "times", fontSize: 8.5, cellPadding: 1.4, lineColor: [150, 160, 170], lineWidth: 0.2, textColor: [20, 20, 20] },
    headStyles: { fillColor: NAVY, textColor: 255, fontStyle: "bold", halign: "center" },
    columnStyles: { 0: { cellWidth: 9, halign: "center" }, 1: { cellWidth: 40 }, 2: { cellWidth: 24, halign: "right" }, 4: { cellWidth: 20, halign: "right" }, 5: { cellWidth: 30, halign: "right" }, 6: { cellWidth: 28, halign: "right" }, 7: { cellWidth: 28, halign: "right" }, 8: { cellWidth: 32, halign: "right" } },
    didParseCell: (d) => {
      if (d.section === "body" && d.row.index === data.rows.length) { d.cell.styles.fontStyle = "bold"; d.cell.styles.fillColor = [254, 243, 199]; }
      if (d.section === "body" && d.column.index === 8 && String(d.cell.raw).startsWith("-")) d.cell.styles.textColor = [200, 30, 20];
    },
    didDrawPage: () => kop(),
  });

  // Detail bulanan
  let ty = doc.lastAutoTable.finalY + 6;
  if (ty + 20 > H - fh) { doc.addPage(); kop(); ty = hh + 8; }
  doc.setFont("times", "bold"); doc.setFontSize(11); doc.setTextColor(...NAVY);
  doc.text("RINCIAN PER BULAN", mx, ty);
  doc.setDrawColor(...YELLOW); doc.line(mx, ty + 1.5, mx + 32, ty + 1.5);
  const rows = detailRows(data);
  autoTable(doc, {
    startY: ty + 3,
    margin: { top: hh + 6, bottom: fh + 6, left: mx, right: mx },
    theme: "grid",
    head: [["No", "Pengurus", "Keterangan", ...MON, "Total"]],
    body: rows.map((r) => [r.no, r.nama, r.metric, ...r.vals.map((v) => (v ? fmtMetric(r.key, v).replace("Rp ", "") : "-")), fmtMetric(r.key, r.total)]),
    styles: { font: "times", fontSize: 6.8, cellPadding: 0.9, lineColor: [170, 178, 186], lineWidth: 0.15, textColor: [20, 20, 20], halign: "right" },
    headStyles: { fillColor: NAVY, textColor: 255, fontStyle: "bold", halign: "center" },
    columnStyles: { 0: { cellWidth: 7, halign: "center" }, 1: { cellWidth: 28, halign: "left" }, 2: { cellWidth: 30, halign: "left" }, 15: { cellWidth: 24, fontStyle: "bold" } },
    didParseCell: (d) => {
      if (d.section !== "body") return;
      const r = rows[d.row.index];
      if (r.key === "bersih") { d.cell.styles.fontStyle = "bold"; d.cell.styles.fillColor = [254, 249, 225]; }
      if (r.grand) d.cell.styles.fillColor = r.key === "bersih" ? [254, 236, 170] : [235, 240, 245];
      if (d.column.index >= 3 && String(d.cell.raw).startsWith("-") && d.cell.raw !== "-") d.cell.styles.textColor = [200, 30, 20];
    },
    didDrawPage: () => kop(),
  });

  let fy = doc.lastAutoTable.finalY + 6;
  if (fy + 30 > H - fh) { doc.addPage(); kop(); fy = hh + 10; }
  doc.setFont("times", "italic"); doc.setFontSize(8); doc.setTextColor(90, 90, 90);
  doc.text("Pendapatan = Jam kerja (HM) × tarif sewa per jam (tarif unit; bila kosong memakai tarif pengurus). Bersih = Pendapatan - (Gaji operator + Sparepart).", mx, fy);
  doc.setFont("times", "normal"); doc.setFontSize(9.5); doc.setTextColor(20, 20, 20);
  doc.text(`Dicetak: ${dateLong()}`, W - mx, fy + 5, { align: "right" });
  [["Dibuat oleh,", "Admin"], ["Mengetahui,", "Pimpinan"]].forEach(([a, b], i) => {
    const cx = i === 0 ? W - mx - 95 : W - mx - 30;
    doc.setFont("times", "normal"); doc.text(a, cx, fy + 10, { align: "center" });
    doc.setFont("times", "bold"); doc.text(b, cx, fy + 14.5, { align: "center" });
    doc.setLineWidth(0.3); doc.setDrawColor(60, 60, 60); doc.line(cx - 24, fy + 28, cx + 24, fy + 28);
  });
  doc.save(`${filename}.pdf`);
}

export async function exportPengurusRekapExcel(data, meta, filename) {
  const wb = new ExcelJS.Workbook();
  wb.creator = COMPANY.legalName;
  const ws = wb.addWorksheet("Rekap Pengurus", {
    pageSetup: { paperSize: 9, orientation: "landscape", fitToPage: true, fitToWidth: 1, fitToHeight: 0, margins: { left: 0.25, right: 0.25, top: 0.3, bottom: 0.3, header: 0, footer: 0 } },
    views: [{ showGridLines: false }],
  });
  const widths = [5, 24, 24, ...Array(12).fill(13), 16];
  ws.columns = widths.map((w) => ({ width: w }));
  const NC = widths.length;
  const totalPx = widths.reduce((a, b) => a + b, 0) * 7.2;
  const imgH = wb.addImage({ base64: LH_HEADER, extension: "jpeg" });
  const imgF = wb.addImage({ base64: LH_FOOTER, extension: "jpeg" });
  ws.addImage(imgH, { tl: { col: 0, row: 0 }, ext: { width: totalPx, height: totalPx * LH_HEADER_RATIO * 0.6 } });
  const headRows = Math.ceil((totalPx * LH_HEADER_RATIO * 0.6) / 20) + 1;
  for (let r = 1; r <= headRows; r++) ws.getRow(r).height = 15;

  const thin = { style: "thin", color: { argb: "FF9AA5B1" } };
  const border = { top: thin, left: thin, bottom: thin, right: thin };
  const merge = (row, c1, c2, value, st = {}) => {
    if (c2 > c1) ws.mergeCells(row, c1, row, c2);
    const cell = ws.getCell(row, c1);
    cell.value = value;
    cell.font = { name: "Times New Roman", size: st.size || 10, bold: !!st.bold, italic: !!st.italic, color: { argb: st.color || "FF141414" } };
    cell.alignment = { horizontal: st.align || "left", vertical: "middle", wrapText: true };
    return cell;
  };
  const put = (row, col, value, st = {}) => {
    const cell = ws.getCell(row, col);
    cell.value = value;
    cell.font = { name: "Times New Roman", size: 9, bold: !!st.bold, color: { argb: st.color || "FF141414" } };
    cell.alignment = { horizontal: st.align || "left", vertical: "middle", wrapText: true };
    cell.border = border;
    if (st.fill) cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: st.fill } };
    if (st.numFmt) cell.numFmt = st.numFmt;
    return cell;
  };
  const RP = '"Rp" #,##0;[Red]-"Rp" #,##0;"-"';
  const JAM = '#,##0.##;-#,##0.##;"-"';

  let row = headRows + 1;
  merge(row, 1, NC, "REKAP PENGHASILAN PENGURUS EXCAVATOR", { bold: true, size: 15, align: "center", color: XL_NAVY }); ws.getRow(row).height = 22; row++;
  merge(row, 1, NC, [`Perusahaan: ${COMPANY.legalName}`, `Tahun: ${data.year}`, meta?.nomor ? `Nomor: ${meta.nomor}` : null].filter(Boolean).join("   ·   "), { italic: true, align: "center" }); row += 2;

  // Ringkasan
  merge(row, 1, NC, "RINGKASAN TAHUNAN", { bold: true, size: 11, color: XL_NAVY }); row++;
  const sumHead = ["No", "Pengurus", "Unit Diurus", "Tarif/Jam", "Total Jam", "Pendapatan", "Gaji Operator", "Sparepart", "Penghasilan Bersih"];
  sumHead.forEach((h, i) => put(row, i + 1, h, { bold: true, color: "FFFFFFFF", fill: XL_NAVY, align: "center" }));
  ws.getRow(row).height = 20; row++;
  data.rows.forEach((r, i) => {
    put(row, 1, i + 1, { align: "center" }); put(row, 2, r.nama, { bold: true }); put(row, 3, (r.units || []).join(", ") || "-");
    put(row, 4, r.tarif_pengurus || "per unit", { align: "right", numFmt: RP }); put(row, 5, r.total.jam, { align: "right", numFmt: JAM });
    put(row, 6, r.total.pendapatan, { align: "right", numFmt: RP }); put(row, 7, r.total.gaji, { align: "right", numFmt: RP });
    put(row, 8, r.total.sparepart, { align: "right", numFmt: RP }); put(row, 9, r.total.bersih, { align: "right", numFmt: RP, bold: true });
    row++;
  });
  put(row, 1, ""); put(row, 2, "TOTAL", { bold: true, fill: "FFFEF3C7" }); put(row, 3, "", { fill: "FFFEF3C7" }); put(row, 4, "", { fill: "FFFEF3C7" });
  ["jam", "pendapatan", "gaji", "sparepart", "bersih"].forEach((k, i) => put(row, 5 + i, data.total[k], { bold: true, align: "right", numFmt: k === "jam" ? JAM : RP, fill: "FFFEF3C7" }));
  row += 2;

  // Rincian bulanan
  merge(row, 1, NC, "RINCIAN PER BULAN", { bold: true, size: 11, color: XL_NAVY }); row++;
  ["No", "Pengurus", "Keterangan", ...MON, "Total"].forEach((h, i) => put(row, i + 1, h, { bold: true, color: "FFFFFFFF", fill: XL_NAVY, align: "center" }));
  ws.getRow(row).height = 20; row++;
  detailRows(data).forEach((r) => {
    const fill = r.grand ? (r.key === "bersih" ? "FFFEECAA" : "FFEBF0F5") : r.key === "bersih" ? "FFFEF9E1" : undefined;
    const fmt = r.key === "jam" ? JAM : RP;
    put(row, 1, r.no, { align: "center", fill }); put(row, 2, r.nama, { bold: true, fill }); put(row, 3, r.metric, { fill, bold: r.key === "bersih" });
    r.vals.forEach((v, i) => put(row, 4 + i, v || 0, { align: "right", numFmt: fmt, fill, bold: r.key === "bersih" }));
    put(row, 16, r.total, { align: "right", numFmt: fmt, bold: true, fill: fill || XL_SOFT });
    row++;
  });
  row++;
  merge(row, 1, NC, "Pendapatan = Jam kerja (HM) × tarif sewa per jam (tarif unit; bila kosong memakai tarif pengurus). Bersih = Pendapatan - (Gaji operator + Sparepart).", { italic: true, size: 9, color: "FF5A5A5A" }); row += 2;
  merge(row, 12, NC, `Dicetak: ${dateLong()}`, { italic: true, align: "right" }); row++;
  merge(row, 9, 11, "Dibuat oleh,", { align: "center" }); merge(row, 13, 16, "Mengetahui,", { align: "center" }); row++;
  merge(row, 9, 11, "Admin", { align: "center", bold: true }); merge(row, 13, 16, "Pimpinan", { align: "center", bold: true });
  row += 4;
  for (const c of [9, 10, 11, 13, 14, 15, 16]) ws.getCell(row, c).border = { top: { style: "thin" } };
  row += 2;
  ws.addImage(imgF, { tl: { col: 0, row }, ext: { width: totalPx, height: totalPx * LH_FOOTER_RATIO * 0.6 } });
  const buf = await wb.xlsx.writeBuffer();
  saveAs(new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${filename}.xlsx`);
}
