import palette from "../../../contracts/palette.json";
import type { Limb } from "./spec";

export const LIMB_COLORS: Record<Limb, string> = palette.limbs;
export const HOLD_COLORS: Record<string, string> = palette.holds;
export const ACCENT = palette.accent;
export const INK = palette.ink;
export const CHALK = palette.chalk;

export const FONT = "Inter, 'SF Pro Display', -apple-system, 'Helvetica Neue', Arial, sans-serif";

export function holdColor(name: string): string {
  return HOLD_COLORS[name] ?? name;
}
