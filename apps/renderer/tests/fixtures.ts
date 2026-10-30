import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const CONTRACTS = fileURLToPath(new URL("../../../contracts/", import.meta.url));

export function readContract(relative: string): unknown {
  return JSON.parse(readFileSync(`${CONTRACTS}${relative}`, "utf-8"));
}

export function exampleNames(): string[] {
  return readdirSync(`${CONTRACTS}motion-spec/examples`).filter((f) => f.endsWith(".json"));
}
