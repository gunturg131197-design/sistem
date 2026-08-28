import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

export function exportToExcel(rows, filename, sheetName = "Data") {
  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  XLSX.writeFile(wb, `${filename}.xlsx`);
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
