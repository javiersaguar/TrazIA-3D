"use client";

/*
  Único punto donde las pantallas cargan el 3D: solo en cliente y en diferido,
  para que three.js y web-ifc no entren en el bundle inicial.
*/
import dynamic from "next/dynamic";

function ViewerSkeleton() {
  return (
    <div className="drafting-grid flex h-full min-h-[240px] w-full items-center justify-center rounded-[var(--radius-card)]">
      <div className="skeleton h-1.5 w-40" />
    </div>
  );
}

export const IfcViewer = dynamic(() => import("@/features/viewer3d").then((m) => m.IfcViewer), {
  ssr: false,
  loading: ViewerSkeleton,
});

export const PlantScene = dynamic(() => import("@/features/viewer3d").then((m) => m.PlantScene), {
  ssr: false,
  loading: ViewerSkeleton,
});

export const RevisionMorph = dynamic(() => import("@/features/viewer3d").then((m) => m.RevisionMorph), {
  ssr: false,
  loading: ViewerSkeleton,
});
