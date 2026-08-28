import React from "react";

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
  if (n === null || n === undefined) return "Rp 0";
  return "Rp " + Number(n).toLocaleString("id-ID");
}
