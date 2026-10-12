import React from "react";
import logoMark from "@/assets/logo-mark.png";

/** Logo brand TRIRARA TUNGGAL PUTRA: mark (T kuning-merah) + wordmark putih */
export function BrandMark({ size = 32, className = "", testid }) {
  return (
    <img
      src={logoMark}
      alt="Logo Trirara Tunggal Putra"
      data-testid={testid}
      style={{ height: size, width: "auto" }}
      className={`select-none ${className}`}
      draggable={false}
    />
  );
}

export function BrandLockup({ size = 32, compact = false, testid = "brand-lockup" }) {
  return (
    <div className="flex items-center gap-3" data-testid={testid}>
      <BrandMark size={size} testid={`${testid}-logo`} />
      <div className="leading-none">
        <p className={`font-display font-black tracking-tight text-foreground ${compact ? "text-sm" : "text-base"}`} data-testid={`${testid}-title`}>
          TRIRARA
        </p>
        <p className={`font-mono uppercase text-muted-foreground ${compact ? "text-[8px] tracking-[0.3em] mt-1" : "text-[9px] tracking-[0.34em] mt-1.5"}`}>
          Tunggal Putra
        </p>
      </div>
    </div>
  );
}
