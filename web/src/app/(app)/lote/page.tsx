import { BatchSketch } from "@/features/bocetos/batch-sketch";
import { ReportsSketch } from "@/features/bocetos/reports-sketch";
export default function Page(){ return <div className="space-y-6"><h1 className="text-2xl font-semibold">Lotes e informes</h1><p className="text-sm text-warning">Vista de demostración · cola y exportaciones de ejemplo</p><BatchSketch /><ReportsSketch /></div>; }
