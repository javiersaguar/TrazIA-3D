import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const revision = JSON.parse(readFileSync(new URL("../../../../examples/vessel_rev_a.json", import.meta.url), "utf8"));
beforeEach(() => { vi.resetModules(); vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000"); });
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

describe("cliente HTTP", () => {
  it("conserva el ETag y serializa dos ediciones contra versiones sucesivas", async () => {
    const seen: string[] = [];
    const fetcher = vi.fn(async (_url: string, init?: RequestInit) => {
      if (!init?.method) return new Response(JSON.stringify(revision), { headers: { ETag: '"1"' } });
      seen.push((init.headers as Record<string, string>)["If-Match"]!);
      const data = structuredClone(revision);
      data.equipment.diameter.state = "accepted";
      return new Response(JSON.stringify(data), { headers: { ETag: `"${seen.length + 1}"` } });
    });
    vi.stubGlobal("fetch", fetcher);
    const client = await import("./client");
    await client.apiRevision("A");
    await Promise.all(["one", "two"].map(idempotencyKey => client.apiUpdate({ rev: "A", path: "diameter", status: "accepted", idempotencyKey })));
    expect(seen).toEqual(['"1"', '"2"']);
    expect(fetcher.mock.calls[1]![0]).toContain(encodeURIComponent(`${revision.project_id}:${revision.equipment.id}:A`));
  });

  it("rechaza un conflicto de versión sin convertirlo en datos de demo", async () => {
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => init?.method
      ? new Response(JSON.stringify({ detail: "La revisión ha cambiado" }), { status: 412 })
      : new Response(JSON.stringify(revision), { headers: { ETag: '"1"' } })));
    const client = await import("./client");
    await expect(client.apiUpdate({ rev: "A", path: "diameter", status: "accepted", idempotencyKey: "one" }))
      .rejects.toMatchObject({ status: 412 });
  });

  it("invalida la URL del IFC cuando cambia la versión de sus datos", async () => {
    const config = await import("./config");
    config.rememberVersion("A", "DEMO-PLANT:V101:A", '"1"');
    const first = config.revisionResource("A", "ifc");
    config.rememberVersion("A", "DEMO-PLANT:V101:A", '"2"');
    expect(config.revisionResource("A", "ifc")).not.toBe(first);
    config.rememberVersion("A", "DEMO-PLANT:V101:A", '"1"');
    expect(config.revisionVersion("A")?.etag).toBe('"2"');
    expect(config.revisionResource("A", "pdf")).toContain("/documents/GA-V101");
  });

  it("sin API conserva las rutas locales y no necesita un servidor", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    const config = await import("./config");
    expect(config.apiEnabled).toBe(false);
    expect(config.revisionResource("B", "ifc")).toBe("/demo/ifc/rev_b.ifc");
  });

  it("conserva una edición persistida con JSONL pendiente y deshace por auditoría", async () => {
    const changed = structuredClone(revision);
    changed.equipment.diameter.value = 2100;
    changed.equipment.diameter.state = "corrected";
    const fetcher = vi.fn(async (_url: string, init?: RequestInit) => {
      if (!init?.method) return new Response(JSON.stringify(revision), { headers: { ETag: '"1"' } });
      if (init.method === "PATCH") return new Response(JSON.stringify({ detail: "JSONL pendiente", persisted: true, revision: changed }), {
        status: 503, headers: { ETag: '"2"', "X-Audit-Id": "8" },
      });
      return new Response(JSON.stringify(revision), { headers: { ETag: '"3"', "X-Audit-Id": "9" } });
    });
    vi.stubGlobal("fetch", fetcher);
    const client = await import("./client");
    const result = await client.apiUpdate({ rev: "A", path: "diameter", status: "corrected", correctedValue: 2100, idempotencyKey: "edit" });
    expect(result).toMatchObject({ auditId: 8, value: 2100, saveWarning: "JSONL pendiente" });
    await client.apiUndo({ rev: "A", path: "diameter", status: "candidate", idempotencyKey: "undo" }, 8);
    expect(fetcher.mock.calls[2]![0]).toContain("audit/8/undo");
    expect(fetcher.mock.calls[2]![1]?.method).toBe("POST");
    expect((fetcher.mock.calls[2]![1]?.headers as Record<string, string>)["If-Match"]).toBe('"2"');
  });
});
