{
  "brand": {
    "app_name": "TRIRARA TUNGGAL PUTRA",
    "tone": ["industrial", "trustworthy", "high-contrast", "ops-console"],
    "logo_usage": {
      "mark_png_transparent": "Use on navy surfaces (sidebar/header/login hero).",
      "full_logo_jpg_white": "Use on white export/PDF cover pages only (not inside dark UI)."
    }
  },
  "design_tokens_css_hsl": {
    "paste_into": "/app/frontend/src/index.css (:root block)",
    "notes": [
      "Keep HSL tokens (space-separated) to match current shadcn setup.",
      "No transparent overlays: ensure popover/dialog/dropdown surfaces are solid (--popover/--card).",
      "Radius stays sharp (2px) to match existing blueprint/industrial vibe."
    ],
    "tokens": {
      "--background": "210 63% 12%",
      "--foreground": "210 20% 96%",

      "--card": "210 58% 14%",
      "--card-foreground": "210 20% 96%",

      "--popover": "210 56% 13%",
      "--popover-foreground": "210 20% 96%",

      "--muted": "210 40% 18%",
      "--muted-foreground": "210 12% 72%",

      "--secondary": "210 44% 16%",
      "--secondary-foreground": "210 20% 96%",

      "--border": "210 34% 22%",
      "--input": "210 34% 22%",

      "--primary": "46 100% 54%",
      "--primary-foreground": "210 70% 10%",

      "--accent": "4 85% 56%",
      "--accent-foreground": "0 0% 100%",

      "--destructive": "4 85% 56%",
      "--destructive-foreground": "0 0% 100%",

      "--ring": "46 100% 54%",

      "--chart-1": "46 100% 54%",
      "--chart-2": "4 85% 56%",
      "--chart-3": "195 85% 52%",
      "--chart-4": "160 55% 44%",
      "--chart-5": "210 10% 70%",

      "--radius": "2px"
    }
  },
  "recharts_hex": {
    "grid": "#1E3A52",
    "axis": "#8FA6B8",
    "tooltip": {
      "bg": "#0F2D44",
      "border": "#2A4A63",
      "text": "#F3F7FB"
    },
    "series": {
      "yellow_primary": "#FFC20E",
      "red_accent": "#EF3B2D",
      "cyan_info": "#2EC5FF",
      "green_ok": "#3BBF8A",
      "slate_neutral": "#A7B6C4"
    }
  },
  "layout_branding": {
    "sidebar": {
      "treatment": [
        "Background uses --background; add subtle blueprint grid at 3–4% opacity in yellow (existing .grid-bg but reduce alpha).",
        "Top brand block: left-aligned mark + stacked wordmark; keep plenty of padding (px-4 py-4).",
        "Active nav item: solid muted surface with 2px left rail in primary yellow; icon + label in foreground.",
        "Hover: background-color only (no transform), using --secondary."
      ],
      "brand_block": {
        "structure": [
          "[Mark PNG] 28–32px",
          "TRIRARA (font-display, uppercase, tracking-tight, text-foreground)",
          "TUNGGAL PUTRA (font-mono or body, tracking-[0.28em], text-muted-foreground)"
        ],
        "tailwind": "flex items-center gap-3 px-4 py-4 border-b border-border",
        "data_testids": {
          "logo": "app-sidebar-brand-logo",
          "title": "app-sidebar-brand-title"
        }
      }
    },
    "mobile_header": {
      "treatment": [
        "Solid navy bar (bg-background) with bottom border.",
        "Left: mark; center: current page title; right: quick actions (search/notifications).",
        "Keep yellow only for the active indicator dot or small underline (<= 4px height)."
      ],
      "data_testids": {
        "logo": "app-mobile-header-logo",
        "page_title": "app-mobile-header-title"
      }
    },
    "login": {
      "layout_idea": [
        "Split layout on desktop: left brand panel (navy) + right login card; on mobile: stacked with brand header above card.",
        "Brand panel includes: mark, TRIRARA wordmark, and a subtle checkered band (letterhead motif) as a 48px strip at bottom.",
        "Avoid gradients; use pattern overlays (checkered + diagonal stripe) at low opacity (4–6%)."
      ],
      "pattern_css": {
        "checkered_band": "background-image: linear-gradient(90deg, rgba(255,194,14,0.18) 0 50%, transparent 50% 100%), linear-gradient(rgba(255,194,14,0.18) 0 50%, transparent 50% 100%); background-size: 18px 18px; background-position: 0 0, 9px 9px;",
        "stripe_overlay": "background-image: repeating-linear-gradient(135deg, rgba(239,59,45,0.10) 0 10px, transparent 10px 20px);"
      },
      "data_testids": {
        "username": "login-form-username-input",
        "password": "login-form-password-input",
        "submit": "login-form-submit-button",
        "google": "login-form-google-button"
      }
    }
  },
  "dialog_forms_rules": {
    "sectioning": [
      "Use shadcn <Tabs> inside large dialogs: (1) Umum, (2) Operasional, (3) Kondisi Alat, (4) Catatan.",
      "Each section uses a Card with header row: title (font-display) + small helper text (muted).",
      "Use 2-column grid on md+ (gap-4), single column on mobile."
    ],
    "kondisi_alat_checklist": {
      "component": "Use /components/ui/toggle-group.jsx for Baik/Tidak per item + /components/ui/textarea.jsx for keterangan.",
      "interaction": [
        "Each checklist row: label left, ToggleGroup right (two options).",
        "Baik uses secondary surface; Tidak uses accent red surface but only when selected.",
        "Always show a small status pill (Badge) reflecting selection for scanability."
      ],
      "tailwind_row": "flex flex-col md:flex-row md:items-center md:justify-between gap-2 p-3 rounded-[var(--radius)] border border-border bg-card",
      "data_testids": {
        "row": "ops-report-kondisi-alat-item-row",
        "toggle": "ops-report-kondisi-alat-item-toggle",
        "note": "ops-report-kondisi-alat-item-note"
      }
    },
    "dropdown_overlay_rule": "All Select/DropdownMenu/Popover content must use bg-popover text-popover-foreground border-border shadow-md (no opacity classes like bg-background/80)."
  },
  "component_path": {
    "shadcn_primary": [
      "/app/frontend/src/components/ui/button.jsx",
      "/app/frontend/src/components/ui/card.jsx",
      "/app/frontend/src/components/ui/dialog.jsx",
      "/app/frontend/src/components/ui/select.jsx",
      "/app/frontend/src/components/ui/table.jsx",
      "/app/frontend/src/components/ui/tabs.jsx",
      "/app/frontend/src/components/ui/toggle-group.jsx",
      "/app/frontend/src/components/ui/badge.jsx",
      "/app/frontend/src/components/ui/sonner.jsx"
    ]
  },
  "instructions_to_main_agent": [
    "Update /app/frontend/src/index.css :root tokens to the provided HSL values; keep existing font imports.",
    "Replace any visible app name string from EXCAVA.OPS to TRIRARA TUNGGAL PUTRA; sidebar brand shows mark + TRIRARA + TUNGGAL PUTRA.",
    "Ensure all interactive elements and key info have data-testid in kebab-case.",
    "Recharts: set grid/axis/tooltip styles using the provided hex; series colors map to chart-1..5 or explicit hex.",
    "Do not introduce transparent dropdown/dialog backgrounds; use solid popover/card tokens.",
    "Keep corners sharp (2px) and 1px borders; rely on spacing and hierarchy for premium feel."
  ],
  "append_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>  \n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
