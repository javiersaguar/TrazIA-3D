import { Shapes } from "lucide-react";
import Image from "next/image";

import { Icon } from "@/components/ui/primitives";
import thumbnails from "./family-thumbnails.json";

/** Imagen del catálogo. Las familias creadas por el usuario conservan un icono. */
export function FamilyThumb({ kind, size = 96 }: { kind: string; size?: number }) {
  return (
    <div
      className="drafting-grid flex shrink-0 items-center justify-center overflow-hidden rounded-[var(--radius-control)] text-faint"
      style={{ width: size, height: size }}
      aria-hidden
    >
      {Object.hasOwn(thumbnails, kind) ? (
        <Image
          src={`/demo/familias/${kind}.webp`}
          alt=""
          width={216}
          height={216}
          unoptimized
          className="size-full object-contain"
        />
      ) : (
        <Icon icon={Shapes} size={Math.round(size / 3)} />
      )}
    </div>
  );
}
