import React from "react";
import { Input } from "@/components/ui/input";

export function PageHeader({ overline, title, description, actions, testid = "page-header" }) {
  return (
    <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 mb-8 pb-6 border-b border-border" data-testid={testid}>
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-primary mb-3">{overline}</p>
        <h1 className="font-display font-black text-3xl sm:text-4xl lg:text-5xl tracking-tighter">{title}</h1>
        {description && <p className="mt-2 text-sm text-muted-foreground max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}

export function StatBox({ label, value, unit, accent = "primary", icon: Icon, testid }) {
  const accentClass = accent === "primary" ? "text-primary" : accent === "accent" ? "text-accent" : "text-foreground";
  return (
    <div className="border border-border p-5 bg-muted/30 relative" data-testid={testid}>
      <div className="flex items-start justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
        {Icon && <Icon size={16} weight="bold" className="text-muted-foreground" />}
      </div>
      <p className={`font-display font-black text-3xl tracking-tighter mt-3 ${accentClass}`}>
        {value}
        {unit && <span className="text-sm font-normal text-muted-foreground ml-1.5 font-mono">{unit}</span>}
      </p>
      <div className="absolute bottom-0 left-0 h-0.5 w-8 bg-primary" />
    </div>
  );
}

export function formatIDR(n) {
  if (n === null || n === undefined || n === "") return "Rp 0";
  return "Rp " + Number(n).toLocaleString("id-ID");
}

// Ambil digit dari string berformat -> number
export function parseIDR(str) {
  if (str === null || str === undefined) return "";
  const digits = String(str).replace(/[^0-9]/g, "");
  return digits;
}

function groupThousand(digits) {
  if (!digits) return "";
  return Number(digits).toLocaleString("id-ID");
}

/**
 * Input mata uang: menampilkan format Rupiah (Rp 1.000.000) sambil mengetik.
 * value = angka mentah (number|string). onChange(rawNumber:number|"") .
 */
export function CurrencyInput({ value, onChange, className = "", ...props }) {
  const digits = value === "" || value === null || value === undefined ? "" : String(value).replace(/[^0-9]/g, "");
  const display = digits ? "Rp " + groupThousand(digits) : "";
  return (
    <Input
      {...props}
      inputMode="numeric"
      className={className}
      value={display}
      onChange={(e) => {
        const raw = e.target.value.replace(/[^0-9]/g, "");
        onChange(raw === "" ? "" : Number(raw));
      }}
    />
  );
}
