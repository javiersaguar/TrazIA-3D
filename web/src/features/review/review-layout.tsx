"use client";

import { useSyncExternalStore, useState, type ReactNode } from "react";
import {
  Group,
  Panel,
  Separator,
  useDefaultLayout,
  useGroupRef,
  type LayoutStorage,
} from "react-resizable-panels";
import { Segmented } from "@/components/ui/controls";
import styles from "./review.module.css";
const panelStorage: LayoutStorage = {
  getItem: (key) => {
    try {
      return typeof window === "undefined"
        ? null
        : window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  setItem: (key, value) => {
    try {
      if (typeof window !== "undefined")
        window.localStorage.setItem(key, value);
    } catch {
      /* El layout sigue funcionando sin almacenamiento. */
    }
  },
};
const subscribe = (fn: () => void) => {
  const q = window.matchMedia("(max-width:1023px)");
  q.addEventListener("change", fn);
  return () => q.removeEventListener("change", fn);
};
const getMobile = () => window.matchMedia("(max-width:1023px)").matches;
export function ReviewLayout({
  pdf,
  model,
  fields,
  children,
}: {
  pdf: ReactNode;
  model: ReactNode;
  fields: ReactNode;
  children?: ReactNode;
}) {
  const mobile = useSyncExternalStore(subscribe, getMobile, () => false),
    group = useGroupRef();
  const [focus, setFocus] = useState<"all" | "pdf" | "model" | "fields">("all");
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: mobile ? "trazia.review.vertical.v1" : "trazia.review.horizontal.v1",
    panelIds: ["pdf", "model", "fields"],
    onlySaveAfterUserInteractions: true,
    storage: panelStorage,
  });
  return (
    <div className={styles.workspace}>
      <div className={styles.focus}>
        <span>Foco</span>
        <Segmented
          label="Foco de revisión"
          value={focus}
          onChange={(value) => {
            setFocus(value);
            group.current?.setLayout(
              value === "all"
                ? (defaultLayout ?? { pdf: 31, model: 39, fields: 30 })
                : {
                    pdf: value === "pdf" ? 100 : 0,
                    model: value === "model" ? 100 : 0,
                    fields: value === "fields" ? 100 : 0,
                  },
            );
          }}
          options={[
            { value: "all", label: "Todo" },
            { value: "pdf", label: "Plano" },
            { value: "model", label: "Modelo" },
            { value: "fields", label: "Campos" },
          ]}
        />
      </div>
      <div className={styles.panels}>
        <Group
          key={mobile ? "vertical" : "horizontal"}
          id="review-panels"
          groupRef={group}
          orientation={mobile ? "vertical" : "horizontal"}
          defaultLayout={defaultLayout}
          onLayoutChanged={onLayoutChanged}
        >
          <Panel
            id="pdf"
            defaultSize="31%"
            minSize="12%"
            collapsible
            className={styles.panel}
          >
            {pdf}
          </Panel>
          <Separator
            className={styles.separator}
            aria-label="Redimensionar plano y modelo"
          />
          <Panel
            id="model"
            defaultSize="39%"
            minSize="12%"
            collapsible
            className={styles.panel}
          >
            {model}
          </Panel>
          <Separator
            className={styles.separator}
            aria-label="Redimensionar modelo y campos"
          />
          <Panel
            id="fields"
            defaultSize="30%"
            minSize="12%"
            collapsible
            className={styles.panel}
          >
            {fields}
          </Panel>
        </Group>
        {children}
      </div>
    </div>
  );
}
