export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/+$/, "");
export const apiEnabled = API_BASE.length > 0;

type RevisionVersion = { identity: string; etag: string };
const versions = new Map<string, RevisionVersion>();

export function apiURL(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export function rememberVersion(revision: string, identity: string, etag: string | null) {
  if (etag) versions.set(revision, { identity, etag });
}

export function revisionVersion(revision: string) {
  return versions.get(revision);
}

export function revisionResource(revision: "A" | "B", resource: "ifc" | "pdf") {
  if (!apiEnabled) return resource === "ifc" ? `/demo/ifc/rev_${revision.toLowerCase()}.ifc`
    : `/demo/docs/GAD_V-101_rev${revision}.pdf`;
  const version = versions.get(revision);
  const id = encodeURIComponent(version?.identity ?? revision);
  return resource === "ifc" ? apiURL(`/revisions/${id}/ifc?draft=true&v=${encodeURIComponent(version?.etag ?? "0")}`)
    : apiURL(`/revisions/${id}/documents/GA-V101`);
}
