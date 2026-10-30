import { afterEach, describe, expect, it, vi } from "vitest";
import { rememberVersion, revisionVersion } from "../../lib/api/config";
import { approveRevision } from "./approval";

afterEach(() => vi.unstubAllGlobals());
describe("aprobación sobre la versión revisada", () => {
  it("envía el ETag visto y conserva la nueva versión al guardar", async () => {
    rememberVersion("A", "project:V-101:A", '"v7"');
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ revision: "A", approval: { reviewer: "Ana" } }),
          { headers: { ETag: '"v8"' } },
        ),
      );
    vi.stubGlobal("fetch", fetch);
    await approveRevision("A", " Ana ", "request-key");
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = fetch.mock.calls[0]!;
    expect(url).toContain("project%3AV-101%3AA/approve");
    expect(options.headers).toMatchObject({
      "If-Match": '"v7"',
      "Idempotency-Key": "request-key",
    });
    expect(JSON.parse(options.body)).toEqual({ reviewer: "Ana" });
    expect(revisionVersion("A")?.etag).toBe('"v8"');
  });
  it("un conflicto no refresca ni aprueba automáticamente otra versión", async () => {
    rememberVersion("B", "project:V-101:B", '"v1"');
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "La revisión cambió" }), {
          status: 412,
        }),
      );
    vi.stubGlobal("fetch", fetch);
    await expect(approveRevision("B", "Ana", "key")).rejects.toMatchObject({
      status: 412,
    });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(revisionVersion("B")?.etag).toBe('"v1"');
  });
});
