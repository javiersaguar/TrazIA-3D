"use client";

import { useQuery } from "@tanstack/react-query";
import { getChanges, getEquipment, getReviewFields, getRevision, type RevisionId } from "./mock/api";

export const qk = {
  revision: (rev: RevisionId) => ["revision", rev] as const,
  fields: (rev: RevisionId) => ["review-fields", rev] as const,
  changes: () => ["changes", "A", "B"] as const,
  equipment: () => ["equipment"] as const,
};

export const useRevision = (rev: RevisionId) => useQuery({ queryKey: qk.revision(rev), queryFn: () => getRevision(rev) });

export const useReviewFields = (rev: RevisionId) =>
  useQuery({ queryKey: qk.fields(rev), queryFn: () => getReviewFields(rev) });

export const useChanges = () => useQuery({ queryKey: qk.changes(), queryFn: getChanges });

export const useEquipment = () => useQuery({ queryKey: qk.equipment(), queryFn: getEquipment });
