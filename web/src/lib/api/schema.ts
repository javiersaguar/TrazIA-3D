/* Tipos del contrato HTTP. Actualizar con pnpm gen:api. */
export interface paths {
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload */
        post: operations["upload_documents_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/equipment": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Equipment */
        get: operations["equipment_equipment_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/equipment/{tag}/revisions/{rev}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Revision */
        get: operations["revision_equipment__tag__revisions__rev__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/fields": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Review Fields */
        get: operations["review_fields_revisions__identity__fields_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/fields/{path}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Field */
        patch: operations["update_field_revisions__identity__fields__path__patch"];
        trace?: never;
    };
    "/revisions/{identity}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Revision */
        post: operations["approve_revision_revisions__identity__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit */
        get: operations["audit_revisions__identity__audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/ifc": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ifc */
        get: operations["ifc_revisions__identity__ifc_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/documents/{document_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Original */
        get: operations["original_revisions__identity__documents__document_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/equipment/{tag}/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Job */
        post: operations["create_job_equipment__tag__jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/jobs/{identity}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Job */
        get: operations["job_jobs__identity__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/jobs/{identity}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel */
        post: operations["cancel_jobs__identity__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/jobs/{identity}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Events */
        get: operations["events_jobs__identity__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/diff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Diff */
        get: operations["diff_diff_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/diff/bcf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bcf */
        get: operations["bcf_diff_bcf_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/bench": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bench */
        get: operations["bench_bench_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plant": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Plant */
        get: operations["plant_plant_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/estudio": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Study */
        get: operations["study_estudio_get"];
        put?: never;
        /** Launch Study */
        post: operations["launch_study_estudio_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/copiloto": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Copilot */
        post: operations["copilot_copiloto_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Alternative */
        Alternative: {
            /** Value */
            value: number | string;
            /** Unit */
            unit: string;
            source: components["schemas"]["Source"];
        };
        /** Angle */
        Angle: {
            source: components["schemas"]["Source"];
            /**
             * State
             * @default candidate
             * @enum {string}
             */
            state?: "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
            interval?: components["schemas"]["Interval"] | null;
            /** Alternatives */
            alternatives?: components["schemas"]["Alternative"][];
            /** Explanation */
            explanation?: string | null;
            /** Value */
            value: number;
            /**
             * Unit
             * @default deg
             * @constant
             */
            unit?: "deg";
        };
        /** Approval */
        Approval: {
            /** Reviewer */
            reviewer: string;
            /**
             * Timestamp
             * Format: date-time
             */
            timestamp: string;
            /** Input Sha256 */
            input_sha256: string;
        };
        /** ApprovalInput */
        ApprovalInput: {
            /** Reviewer */
            reviewer: string;
        };
        /** Attribute */
        Attribute: {
            source: components["schemas"]["Source"];
            /**
             * State
             * @default candidate
             * @enum {string}
             */
            state?: "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
            interval?: components["schemas"]["Interval"] | null;
            /** Alternatives */
            alternatives?: components["schemas"]["Alternative"][];
            /** Explanation */
            explanation?: string | null;
            /** Value */
            value: number | string;
            /** Unit */
            unit: string;
        };
        /** Body_upload_documents_post */
        Body_upload_documents_post: {
            /** File */
            file: string;
            /** Document Id */
            document_id?: string | null;
            /**
             * Revision
             * @default A
             */
            revision?: string;
        };
        /** CopilotInput */
        CopilotInput: {
            /** Question */
            question: string;
            /**
             * Revision Id
             * @default A
             */
            revision_id?: string;
            /** Path */
            path?: string | null;
        };
        /** Dimension */
        Dimension: {
            source: components["schemas"]["Source"];
            /**
             * State
             * @default candidate
             * @enum {string}
             */
            state?: "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
            interval?: components["schemas"]["Interval"] | null;
            /** Alternatives */
            alternatives?: components["schemas"]["Alternative"][];
            /** Explanation */
            explanation?: string | null;
            /** Value */
            value: number;
            /**
             * Unit
             * @default mm
             * @constant
             */
            unit?: "mm";
        };
        /** Document */
        Document: {
            /** Id */
            id: string;
            /** Filename */
            filename: string;
            /** Revision */
            revision: string;
            /** Sha256 */
            sha256: string;
            /** Page Count */
            page_count?: number | null;
        };
        /** Elevation */
        Elevation: {
            source: components["schemas"]["Source"];
            /**
             * State
             * @default candidate
             * @enum {string}
             */
            state?: "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
            interval?: components["schemas"]["Interval"] | null;
            /** Alternatives */
            alternatives?: components["schemas"]["Alternative"][];
            /** Explanation */
            explanation?: string | null;
            /** Value */
            value: number;
            /**
             * Unit
             * @default mm
             * @constant
             */
            unit?: "mm";
        };
        /** Envelope */
        Envelope: {
            origin: components["schemas"]["Vector3"];
            size: components["schemas"]["Vector3"];
        };
        /** Equipment */
        Equipment: {
            /** Id */
            id: string;
            tag: components["schemas"]["Tag"];
            /**
             * Kind
             * @default vertical_vessel
             * @enum {string}
             */
            kind?: "vertical_vessel" | "horizontal_vessel" | "column" | "tank" | "pump" | "compressor" | "generic";
            /**
             * Lod
             * @default 2
             * @enum {integer}
             */
            lod?: 1 | 2 | 3;
            /** Support */
            support?: ("skirt" | "legs" | "saddles" | "lugs" | "baseplate" | "none") | null;
            envelope?: components["schemas"]["Envelope"] | null;
            diameter?: components["schemas"]["Dimension"] | null;
            height?: components["schemas"]["Dimension"] | null;
            head_depth?: components["schemas"]["Dimension"] | null;
            skirt_height?: components["schemas"]["Dimension"] | null;
            skirt_thickness?: components["schemas"]["Dimension"] | null;
            /** Attributes */
            attributes?: {
                [key: string]: components["schemas"]["Attribute"];
            };
            /** Nozzles */
            nozzles: components["schemas"]["Nozzle"][];
        };
        /** FieldInput */
        FieldInput: {
            /**
             * State
             * @enum {string}
             */
            state: "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
            /** Value */
            value?: number | string | null;
            /** Unit */
            unit?: string | null;
            source?: components["schemas"]["Source"] | null;
            /** Explanation */
            explanation?: string | null;
            /** Actor */
            actor: string;
            /** Seconds */
            seconds?: number | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** Interval */
        Interval: {
            /** Low */
            low: number;
            /** High */
            high: number;
            /** Level */
            level: number;
            /**
             * Method
             * @default conformal
             * @constant
             */
            method?: "conformal";
        };
        /** JobInput */
        JobInput: {
            /** Documents */
            documents: string[];
            /**
             * Project Id
             * @default DEMO-PLANT
             */
            project_id?: string;
            /**
             * Equipment Id
             * @description ID estable del equipo; no cambia al renombrar el tag
             * @default vessel-001
             */
            equipment_id?: string;
            /**
             * Revision
             * @default C
             */
            revision?: string;
            /**
             * Strategy
             * @default b_reglas
             */
            strategy?: string;
            /** Providers */
            providers?: string[];
            /**
             * Dataset
             * @default synthetic
             * @enum {string}
             */
            dataset?: "synthetic" | "real";
            /** Previous Id */
            previous_id?: string | null;
            /**
             * Timeout Seconds
             * @default 300
             */
            timeout_seconds?: number;
            /**
             * Max Attempts
             * @default 3
             */
            max_attempts?: number;
            /**
             * Retry Backoff Seconds
             * @default 1
             */
            retry_backoff_seconds?: number;
        };
        /** Nozzle */
        Nozzle: {
            /** Id */
            id: string;
            diameter: components["schemas"]["Dimension"];
            projection: components["schemas"]["Dimension"];
            elevation: components["schemas"]["Elevation"];
            azimuth: components["schemas"]["Angle"];
            service?: components["schemas"]["Attribute"] | null;
            rating?: components["schemas"]["Attribute"] | null;
            /** Nozzle Type */
            nozzle_type?: ("radial" | "tangential" | "top" | "bottom" | "inclined") | null;
        };
        /** Revision */
        Revision: {
            /**
             * Schema Version
             * @default 0.3
             * @constant
             */
            schema_version?: "0.3";
            /** Project Id */
            project_id: string;
            /** Revision */
            revision: string;
            /**
             * Dataset
             * @enum {string}
             */
            dataset: "synthetic" | "real";
            /** Documents */
            documents: components["schemas"]["Document"][];
            equipment: components["schemas"]["Equipment"];
            approval?: components["schemas"]["Approval"] | null;
            run?: components["schemas"]["RunInfo"] | null;
        };
        /** RunInfo */
        RunInfo: {
            /** Strategy */
            strategy: string;
            /** Providers */
            providers: string[];
            /** Seconds */
            seconds: number;
            /** Gpu Seconds */
            gpu_seconds?: number | null;
            /** Tokens In */
            tokens_in?: number | null;
            /** Tokens Out */
            tokens_out?: number | null;
            /** Cost Eur */
            cost_eur?: number | null;
            /** External Calls */
            external_calls: number;
            /**
             * Accounting Complete
             * @default true
             */
            accounting_complete?: boolean;
        };
        /** Source */
        Source: {
            /** Document Id */
            document_id: string;
            /** Page */
            page?: number | null;
            /** Sheet */
            sheet?: string | null;
            /** Cell */
            cell?: string | null;
            /** Locator */
            locator: string;
            /** Bbox */
            bbox?: [
                number,
                number,
                number,
                number
            ] | null;
            /** Confidence */
            confidence: number;
            /**
             * Reviewed
             * @default false
             */
            reviewed?: boolean;
            /** Confidence Raw */
            confidence_raw?: number | null;
            /** Channel */
            channel?: ("texto" | "tabla" | "cota" | "cajetin" | "hoja_datos" | "vesor" | "ocr" | "detector" | "vision" | "geometria" | "rag" | "memoria_revision" | "humano") | null;
            /** Strategy */
            strategy?: string | null;
            /** Model */
            model?: string | null;
            /** Prompt Sha256 */
            prompt_sha256?: string | null;
            /** Grounded */
            grounded?: boolean | null;
            /** Text Original */
            text_original?: string | null;
            /** Unit Original */
            unit_original?: string | null;
        };
        /** Tag */
        Tag: {
            source: components["schemas"]["Source"];
            /**
             * State
             * @default candidate
             * @enum {string}
             */
            state?: "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
            interval?: components["schemas"]["Interval"] | null;
            /** Alternatives */
            alternatives?: components["schemas"]["Alternative"][];
            /** Explanation */
            explanation?: string | null;
            /** Value */
            value: string;
            /**
             * Unit
             * @default 1
             * @constant
             */
            unit?: "1";
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** Vector3 */
        Vector3: {
            x: components["schemas"]["Dimension"];
            y: components["schemas"]["Dimension"];
            z: components["schemas"]["Dimension"];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    upload_documents_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_documents_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    equipment_equipment_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    revision_equipment__tag__revisions__rev__get: {
        parameters: {
            query?: {
                project_id?: string;
            };
            header?: never;
            path: {
                tag: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Revision"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_fields_revisions__identity__fields_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_field_revisions__identity__fields__path__patch: {
        parameters: {
            query?: never;
            header?: {
                "if-match"?: string | null;
                "idempotency-key"?: string | null;
            };
            path: {
                identity: string;
                path: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FieldInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Revision"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_revision_revisions__identity__approve_post: {
        parameters: {
            query?: never;
            header?: {
                "if-match"?: string | null;
                "idempotency-key"?: string | null;
            };
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApprovalInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Revision"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    audit_revisions__identity__audit_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ifc_revisions__identity__ifc_get: {
        parameters: {
            query?: {
                schema?: "IFC4" | "IFC4X3" | "IFC2X3";
                draft?: boolean;
            };
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    original_revisions__identity__documents__document_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_job_equipment__tag__jobs_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string | null;
            };
            path: {
                tag: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["JobInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    job_jobs__identity__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_jobs__identity__cancel_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string | null;
            };
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    events_jobs__identity__events_get: {
        parameters: {
            query?: never;
            header?: {
                "last-event-id"?: number;
            };
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    diff_diff_get: {
        parameters: {
            query?: {
                from?: string;
                to?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bcf_diff_bcf_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    bench_bench_get: {
        parameters: {
            query?: {
                extractor?: "etiquetas" | "combinado";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    plant_plant_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    study_estudio_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    launch_study_estudio_post: {
        parameters: {
            query?: never;
            header?: {
                "idempotency-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    copilot_copiloto_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CopilotInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
