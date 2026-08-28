import React, { useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { CaretDownIcon, PlusIcon, CheckIcon } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

/**
 * A combobox that lets the user pick a name from a suggestion list
 * OR type a completely new name. Emits raw string via onChange.
 */
export default function PengurusCombobox({
  value,
  onChange,
  options = [],
  placeholder = "Pilih atau ketik nama pengurus…",
  testid = "pengurus-combobox",
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const trimmed = query.trim();
  const lower = trimmed.toLowerCase();
  const filtered = options.filter(o => o.toLowerCase().includes(lower));
  const exactExists = options.some(o => o.toLowerCase() === lower);

  const commit = (v) => {
    onChange(v);
    setOpen(false);
    setQuery("");
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={testid}
          className={cn(
            "w-full mt-1.5 h-10 rounded-sm border border-input bg-background px-3",
            "flex items-center justify-between text-sm text-left",
            "hover:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          )}
        >
          <span className={value ? "text-foreground" : "text-muted-foreground"}>
            {value || placeholder}
          </span>
          <CaretDownIcon size={14} weight="bold" className="text-muted-foreground shrink-0 ml-2" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0 rounded-sm border-border w-[--radix-popover-trigger-width]"
        align="start"
      >
        <Command shouldFilter={false} className="rounded-sm">
          <CommandInput
            data-testid={`${testid}-input`}
            placeholder="Cari atau ketik nama baru…"
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            {filtered.length === 0 && !trimmed && (
              <CommandEmpty className="py-4 px-3 font-mono text-[11px] text-muted-foreground">
                // Belum ada nama tersimpan. Ketik untuk tambah baru.
              </CommandEmpty>
            )}
            {filtered.length > 0 && (
              <CommandGroup heading="Tersimpan">
                {filtered.map((opt) => (
                  <CommandItem
                    key={opt}
                    value={opt}
                    onSelect={() => commit(opt)}
                    data-testid={`${testid}-option-${opt}`}
                    className="cursor-pointer rounded-sm"
                  >
                    <span className="flex-1">{opt}</span>
                    {value === opt && <CheckIcon size={14} weight="bold" className="text-primary" />}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {trimmed && !exactExists && (
              <CommandGroup heading="Buat baru">
                <CommandItem
                  onSelect={() => commit(trimmed)}
                  data-testid={`${testid}-create`}
                  className="cursor-pointer rounded-sm text-primary"
                >
                  <PlusIcon size={14} weight="bold" className="mr-2" />
                  Tambah "<span className="font-medium">{trimmed}</span>"
                </CommandItem>
              </CommandGroup>
            )}
            {value && (
              <CommandGroup>
                <CommandItem
                  onSelect={() => commit("")}
                  data-testid={`${testid}-clear`}
                  className="cursor-pointer rounded-sm text-muted-foreground"
                >
                  — Kosongkan pilihan —
                </CommandItem>
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
