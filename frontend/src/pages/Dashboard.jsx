import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, StatBox, formatIDR } from "@/components/common";
import { ClockIcon, TruckIcon, WrenchIcon, StackIcon } from "@phosphor-icons/react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from "recharts";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/summary").then(r => setData(r.data)).catch(() => {});
  }, []);

  const totals = data?.totals || {};
  const perUnit = data?.per_unit || [];
  const daily = data?.daily || [];

  return (
    <div data-testid="dashboard-root">
      <PageHeader
        overline={`// System / ${user?.role === "admin" ? "Command Center" : "Operator Console"}`}
        title={`Selamat datang, ${user?.name?.split(" ")[0] || "Operator"}.`}
        description="Ringkasan operasional armada excavator secara real-time. Semua data dihitung berdasarkan laporan yang telah masuk."
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 mb-10 border border-border">
        <div className="border-r border-border"><StatBox testid="stat-total-jam" label="Total Jam Kerja" value={totals.total_jam ?? 0} unit="HRS" icon={ClockIcon} /></div>
        <div className="border-r border-border"><StatBox testid="stat-total-cars" label="Total Cars Produksi" value={totals.total_cars ?? 0} unit="CARS" icon={StackIcon} accent="primary" /></div>
        <div className="border-r border-border"><StatBox testid="stat-total-sparepart" label="Biaya Sparepart" value={formatIDR(totals.total_biaya_sparepart)} icon={WrenchIcon} accent="accent" /></div>
        <div><StatBox testid="stat-total-units" label="Unit Aktif" value={totals.total_units ?? 0} unit="UNIT" icon={TruckIcon} /></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 border border-border p-6 bg-muted/20">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Trend 14 Hari</p>
              <h3 className="font-display font-black text-xl tracking-tighter mt-1">Produksi Cars Harian</h3>
            </div>
          </div>
          <div className="h-72" data-testid="chart-daily-cars">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={daily}>
                <CartesianGrid stroke="#27272A" strokeDasharray="0" vertical={false} />
                <XAxis dataKey="tanggal" stroke="#71717A" fontSize={10} tickLine={false} />
                <YAxis stroke="#71717A" fontSize={10} tickLine={false} />
                <Tooltip contentStyle={{ background: "#09090B", border: "1px solid #27272A", borderRadius: 0, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.2em" }} />
                <Line type="monotone" dataKey="cars" stroke="#EAB308" strokeWidth={2.5} dot={{ fill: "#EAB308", r: 3 }} />
                <Line type="monotone" dataKey="jam" stroke="#3B82F6" strokeWidth={2} dot={{ fill: "#3B82F6", r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="lg:col-span-2 border border-border p-6 bg-muted/20">
          <div className="mb-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Per Unit</p>
            <h3 className="font-display font-black text-xl tracking-tighter mt-1">Biaya Sparepart</h3>
          </div>
          <div className="h-72" data-testid="chart-cost-per-unit">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={perUnit} layout="vertical">
                <CartesianGrid stroke="#27272A" horizontal={false} />
                <XAxis type="number" stroke="#71717A" fontSize={10} tickLine={false} />
                <YAxis type="category" dataKey="unit_label" stroke="#71717A" fontSize={10} width={110} tickLine={false} />
                <Tooltip contentStyle={{ background: "#09090B", border: "1px solid #27272A", borderRadius: 0, fontSize: 12 }} formatter={(v) => formatIDR(v)} />
                <Bar dataKey="total_biaya_sparepart" fill="#EAB308" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-10 border border-border">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary">// Fleet Overview</p>
            <h3 className="font-display font-black text-xl tracking-tighter mt-1">Rekap Per Unit</h3>
          </div>
        </div>
        <div className="overflow-x-auto" data-testid="fleet-overview-table">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="text-left font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                <th className="p-3">Unit</th>
                <th className="p-3 text-right">Total Jam</th>
                <th className="p-3 text-right">Total Cars</th>
                <th className="p-3 text-right">Biaya Sparepart</th>
              </tr>
            </thead>
            <tbody>
              {perUnit.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-muted-foreground text-xs font-mono">// Belum ada data</td></tr>
              )}
              {perUnit.map((u) => (
                <tr key={u.unit_id} className="border-t border-border hover:bg-secondary/30">
                  <td className="p-3 font-medium">{u.unit_label}</td>
                  <td className="p-3 text-right font-mono">{u.total_jam.toFixed(2)} hrs</td>
                  <td className="p-3 text-right font-mono">{u.total_cars}</td>
                  <td className="p-3 text-right font-mono text-primary">{formatIDR(u.total_biaya_sparepart)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
