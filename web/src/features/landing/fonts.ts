import { Archivo } from "next/font/google";

/** Rotulación de la portada: Archivo estrecha, cercana a la letra técnica de los planos. */
export const display = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--font-display", display: "swap" });
