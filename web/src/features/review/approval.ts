import { ApiError } from "../../lib/api/client";
import { apiURL, rememberVersion, revisionVersion } from "../../lib/api/config";
import type { RevisionId } from "@/lib/mock/api";
import type { Revision } from "@/lib/types/revision";

/** Usa la versión que el revisor ha visto. Un 412 exige volver a revisar, nunca se reintenta a ciegas. */
export async function approveRevision(
  rev: RevisionId,
  reviewer: string,
  key: string,
) {
  const version = revisionVersion(rev);
  if (!version)
    throw new ApiError(
      428,
      "No se conoce la versión de esta revisión. Recarga los campos.",
    );
  const response = await fetch(
    apiURL(`/revisions/${encodeURIComponent(version.identity)}/approve`),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": version.etag,
        "Idempotency-Key": key,
      },
      body: JSON.stringify({ reviewer: reviewer.trim() }),
    },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      typeof body?.detail === "string"
        ? body.detail
        : `La API respondió ${response.status}`,
    );
  }
  const revision = (await response.json()) as Revision;
  rememberVersion(rev, version.identity, response.headers.get("ETag"));
  return revision;
}
