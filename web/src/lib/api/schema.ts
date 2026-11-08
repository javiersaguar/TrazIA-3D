/* Tipos del contrato HTTP. Actualizar con pnpm gen:api. */
export interface paths {
    "/viewer/bcf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bcf */
        post: operations["bcf_viewer_bcf_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/design-operations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Design Operations */
        get: operations["design_operations_revisions__identity__design_operations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/change-proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Proposals */
        get: operations["list_proposals_revisions__identity__change_proposals_get"];
        put?: never;
        /** Create Proposal */
        post: operations["create_proposal_revisions__identity__change_proposals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/change-proposals/{identity}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Proposal */
        get: operations["get_proposal_change_proposals__identity__get"];
        /** Replace Proposal */
        put: operations["replace_proposal_change_proposals__identity__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/change-proposals/{identity}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview */
        post: operations["preview_change_proposals__identity__preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/change-proposals/{identity}/preview.ifc": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Preview Ifc */
        get: operations["preview_ifc_change_proposals__identity__preview_ifc_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/change-proposals/{identity}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply */
        post: operations["apply_change_proposals__identity__apply_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/change-proposals/{identity}/discard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Discard */
        post: operations["discard_change_proposals__identity__discard_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/change-proposals/{identity}/revert": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Revert
         * @description Prepara la revisión compensatoria; se previsualiza y confirma como cualquier otra.
         */
        post: operations["revert_change_proposals__identity__revert_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/copiloto/design-proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Design Intent
         * @description Prepara un borrador desde texto. No crea, valida ni confirma ninguna propuesta.
         */
        post: operations["design_intent_copiloto_design_proposals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/artifacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Artifacts */
        get: operations["artifacts_revisions__identity__artifacts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/design-report.pdf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Design Report Pdf
         * @description PDF derivado con la tabla de cambios y anotaciones; el original no se modifica.
         */
        get: operations["design_report_pdf_revisions__identity__design_report_pdf_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/reference-system": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Reference System */
        get: operations["reference_system_reference_system_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Review Session */
        post: operations["start_review_session_review_sessions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/review-sessions/{session_id}/finish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Finish Review Session */
        post: operations["finish_review_session_review_sessions__session_id__finish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/review-metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Review Metrics */
        get: operations["review_metrics_revisions__identity__review_metrics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/revisions/{identity}/validation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Review Validation */
        get: operations["review_validation_revisions__identity__validation_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/equipment/{tag}/review-metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Equipment Review Metrics */
        get: operations["equipment_review_metrics_equipment__tag__review_metrics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
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
    "/revisions/{identity}/audit/{audit_id}/undo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Undo Field */
        post: operations["undo_field_revisions__identity__audit__audit_id__undo_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/correcciones/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Export Corrections */
        post: operations["export_corrections_correcciones_export_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/correcciones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Correction Log */
        get: operations["correction_log_correcciones_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/diff/visual": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Diff Visual */
        get: operations["diff_visual_diff_visual_get"];
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
    "/learning/corrections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Learning Corrections */
        get: operations["learning_corrections_learning_corrections_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/learning/few-shot": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Few Shot */
        get: operations["few_shot_learning_few_shot_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/learning/few-shot/{example_id}/evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Few Shot Evidence */
        get: operations["few_shot_evidence_learning_few_shot__example_id__evidence_get"];
        put?: never;
        post?: never;
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
        /** ApplyInput */
        ApplyInput: {
            /** Actor */
            actor: string;
            /** Proposal Sha256 */
            proposal_sha256: string;
            /** Preview Ifc Sha256 */
            preview_ifc_sha256: string;
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
        /** Citation */
        Citation: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "field" | "evidence" | "change" | "rule";
            /** Title */
            title: string;
            /** Excerpt */
            excerpt: string;
            /** Path */
            path?: string | null;
            /** Document Id */
            document_id?: string | null;
            /** Filename */
            filename?: string | null;
            /** Sha256 */
            sha256?: string | null;
            /** Page */
            page?: number | null;
            /** Bbox */
            bbox?: number[] | null;
            /** Sheet */
            sheet?: string | null;
            /** Cell */
            cell?: string | null;
            /**
             * Original Verified
             * @default false
             */
            original_verified?: boolean;
        };
        /** Clarification */
        Clarification: {
            /** Question */
            question: string;
            /** Options */
            options?: string[];
            /** Operation Id */
            operation_id?: string | null;
        };
        /** ColumnParameters */
        ColumnParameters: {
            /** Sections */
            sections: components["schemas"]["ColumnSection"][];
        };
        /** ColumnSection */
        ColumnSection: {
            /** Id */
            id: string;
            diameter: components["schemas"]["PositiveDimension"];
            top_diameter?: components["schemas"]["PositiveDimension"] | null;
            height: components["schemas"]["PositiveDimension"];
        };
        /** CopilotAnswer */
        CopilotAnswer: {
            /**
             * Cached
             * @default false
             */
            cached?: boolean;
            /** Abstained */
            abstained: boolean;
            /** Reason */
            reason?: string | null;
            /** Statements */
            statements: components["schemas"]["Statement"][];
            /** Proposals */
            proposals: components["schemas"]["Statement"][];
            /** Citations */
            citations: components["schemas"]["Citation"][];
            /**
             * Read Only
             * @default true
             * @constant
             */
            read_only?: true;
            /** Model */
            model: string;
            /** Revision Id */
            revision_id: string;
            /** Revision Version */
            revision_version: number;
            /** Input Sha256 */
            input_sha256: string;
            /** Prompt Sha256 */
            prompt_sha256: string;
            /** Tools Used */
            tools_used: string[];
            run: components["schemas"]["RunInfo"];
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
            /** Previous Id */
            previous_id?: string | null;
        };
        /**
         * Derivation
         * @description Revisión creada desde otra por una propuesta confirmada, no por una extracción.
         */
        Derivation: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "cambio_diseno" | "reversion";
            /** Revision Id */
            revision_id: string;
            /** Input Sha256 */
            input_sha256: string;
            /** Proposal Id */
            proposal_id: string;
            /** Order Document Id */
            order_document_id: string;
        };
        /**
         * DesignRef
         * @description Orden de diseño confirmada por una persona; no es una lectura del plano.
         */
        DesignRef: {
            /**
             * Kind
             * @default cambio_diseno
             * @constant
             */
            kind?: "cambio_diseno";
            /** Proposal Id */
            proposal_id: string;
            /** Operation Id */
            operation_id: string;
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
        /** Direction3 */
        Direction3: {
            x: components["schemas"]["DirectionComponent"];
            y: components["schemas"]["DirectionComponent"];
            z: components["schemas"]["DirectionComponent"];
        };
        /** DirectionComponent */
        DirectionComponent: {
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
             * @default 1
             * @constant
             */
            unit?: "1";
        };
        /** DiscardInput */
        DiscardInput: {
            /** Actor */
            actor: string;
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
            /** Role */
            role?: "orden_diseno" | null;
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
            horizontal?: components["schemas"]["HorizontalParameters"] | null;
            column?: components["schemas"]["ColumnParameters"] | null;
            tank?: components["schemas"]["TankParameters"] | null;
            /** Platforms */
            platforms?: components["schemas"]["PlatformParameters"][];
            /** Ladders */
            ladders?: components["schemas"]["LadderParameters"][];
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
            /** Decimal Separator */
            decimal_separator?: ("." | ",") | null;
            source?: components["schemas"]["Source"] | null;
            /** Explanation */
            explanation?: string | null;
            /** Actor */
            actor: string;
            /** Seconds */
            seconds?: number | null;
            /** Review Session Id */
            review_session_id?: string | null;
            /** Action */
            action?: ("accept" | "correct" | "assume" | "reject") | null;
            /** Expected */
            expected?: {
                [key: string]: unknown;
            } | null;
        };
        /** FinishInput */
        FinishInput: {
            /** Active Seconds */
            active_seconds: number;
        };
        /** FlangeParameters */
        FlangeParameters: {
            outer_diameter: components["schemas"]["PositiveDimension"];
            thickness: components["schemas"]["PositiveDimension"];
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HorizontalParameters */
        HorizontalParameters: {
            diameter: components["schemas"]["PositiveDimension"];
            length: components["schemas"]["PositiveDimension"];
            head_depth: components["schemas"]["PositiveDimension"];
            support_height: components["schemas"]["PositiveDimension"];
            saddle_width: components["schemas"]["PositiveDimension"];
            saddle_span: components["schemas"]["PositiveDimension"];
            /** Saddle Positions */
            saddle_positions: components["schemas"]["Dimension"][];
        };
        /** IntentInput */
        IntentInput: {
            /** Revision Id */
            revision_id: string;
            /** Text */
            text: string;
            /** Selected Id */
            selected_id?: string | null;
            /**
             * Use Model
             * @default false
             */
            use_model?: boolean;
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
            /**
             * Use Learning
             * @default true
             */
            use_learning?: boolean;
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
        /** LadderParameters */
        LadderParameters: {
            /** Id */
            id: string;
            origin: components["schemas"]["Vector3"];
            width: components["schemas"]["PositiveDimension"];
            height: components["schemas"]["PositiveDimension"];
            rail_diameter: components["schemas"]["PositiveDimension"];
            rung_spacing: components["schemas"]["PositiveDimension"];
        };
        /** Nozzle */
        Nozzle: {
            /** Id */
            id: string;
            /** Stable Id */
            stable_id?: string | null;
            diameter: components["schemas"]["Dimension"];
            projection: components["schemas"]["Dimension"];
            elevation: components["schemas"]["Elevation"];
            azimuth: components["schemas"]["Angle"];
            position?: components["schemas"]["Vector3"] | null;
            direction?: components["schemas"]["Direction3"] | null;
            flange?: components["schemas"]["FlangeParameters"] | null;
            service?: components["schemas"]["Attribute"] | null;
            rating?: components["schemas"]["Attribute"] | null;
            /** Nozzle Type */
            nozzle_type?: ("radial" | "tangential" | "top" | "bottom" | "inclined") | null;
        };
        /** OperationInput */
        OperationInput: {
            /** Id */
            id?: string | null;
            /** Target */
            target: string;
            /** Value */
            value: number | string;
            /** Unit */
            unit?: string | null;
            /** Decimal Separator */
            decimal_separator?: ("." | ",") | null;
            /** Datum */
            datum?: ("suelo" | "tangente_inferior" | "interno" | "norte") | null;
        };
        /** PlatformParameters */
        PlatformParameters: {
            /** Id */
            id: string;
            origin: components["schemas"]["Vector3"];
            size: components["schemas"]["Vector3"];
        };
        /** PositiveDimension */
        PositiveDimension: {
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
        /** PreviewInput */
        PreviewInput: {
            /**
             * Express Rules
             * @default true
             */
            express_rules?: boolean;
            /**
             * Timeout Seconds
             * @default 180
             */
            timeout_seconds?: number;
        };
        /** ProposalInput */
        ProposalInput: {
            /** Operations */
            operations?: components["schemas"]["OperationInput"][];
            /** Reason */
            reason: string;
            /** Actor */
            actor: string;
            /**
             * Origin
             * @default formulario
             * @enum {string}
             */
            origin?: "formulario" | "chat" | "deshacer";
            /** Request Text */
            request_text?: string | null;
            /** Clarifications */
            clarifications?: components["schemas"]["Clarification"][];
        };
        /** RevertInput */
        RevertInput: {
            /** Actor */
            actor: string;
            /** Reason */
            reason: string;
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
            /** Unplaced Nozzles */
            unplaced_nozzles?: string[];
            derived_from?: components["schemas"]["Derivation"] | null;
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
        /** SessionInput */
        SessionInput: {
            /** Revision Id */
            revision_id: string;
            /** Actor */
            actor: string;
            /**
             * Kind
             * @default human
             */
            kind?: string;
        };
        /** Snapshot */
        Snapshot: {
            /** Png Base64 */
            png_base64: string;
            /** Eye */
            eye: number[];
            /** Target */
            target: number[];
            /** Up */
            up: number[];
            /** Zoom */
            zoom: number;
            /** Viewport Height */
            viewport_height: number;
            /** Guid */
            guid: string;
            /**
             * Actor
             * @default Revisor sin identificar
             */
            actor?: string;
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
            channel?: ("texto" | "tabla" | "cota" | "cajetin" | "hoja_datos" | "vesor" | "ocr" | "detector" | "vision" | "geometria" | "rag" | "memoria_revision" | "humano" | "diseno") | null;
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
            design?: components["schemas"]["DesignRef"] | null;
        };
        /** Statement */
        Statement: {
            /** Text */
            text: string;
            /** Citations */
            citations: string[];
        };
        /** StudyInput */
        StudyInput: {
            /** Conjuntos */
            conjuntos?: ("s-dev" | "s-reservado" | "s-adversarial" | "s-mecanico")[];
            /** Variantes */
            variantes?: string[];
            /** Casos */
            casos?: number | null;
            /** Degradaciones */
            degradaciones?: string[] | null;
            /**
             * Remuestreos
             * @default 1000
             */
            remuestreos?: number;
            /**
             * Semilla
             * @default 2026
             */
            semilla?: number;
            /**
             * Timeout Seconds
             * @default 3600
             */
            timeout_seconds?: number;
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
        /** TankParameters */
        TankParameters: {
            diameter: components["schemas"]["PositiveDimension"];
            height: components["schemas"]["PositiveDimension"];
            /**
             * Roof
             * @enum {string}
             */
            roof: "flat" | "conical" | "domed";
            roof_height: components["schemas"]["Dimension"];
        };
        /** UndoInput */
        UndoInput: {
            /** Actor */
            actor: string;
            /** Seconds */
            seconds?: number | null;
            /** Review Session Id */
            review_session_id?: string | null;
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
    bcf_viewer_bcf_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Snapshot"];
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
    design_operations_revisions__identity__design_operations_get: {
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
    list_proposals_revisions__identity__change_proposals_get: {
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
    create_proposal_revisions__identity__change_proposals_post: {
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
                "application/json": components["schemas"]["ProposalInput"];
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
    get_proposal_change_proposals__identity__get: {
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
    replace_proposal_change_proposals__identity__put: {
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
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProposalInput"];
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
    preview_change_proposals__identity__preview_post: {
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
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PreviewInput"] | null;
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
    preview_ifc_change_proposals__identity__preview_ifc_get: {
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
    apply_change_proposals__identity__apply_post: {
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
                "application/json": components["schemas"]["ApplyInput"];
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
    discard_change_proposals__identity__discard_post: {
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
        requestBody: {
            content: {
                "application/json": components["schemas"]["DiscardInput"];
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
    revert_change_proposals__identity__revert_post: {
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
                "application/json": components["schemas"]["RevertInput"];
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
    design_intent_copiloto_design_proposals_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IntentInput"];
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
    artifacts_revisions__identity__artifacts_get: {
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
    design_report_pdf_revisions__identity__design_report_pdf_get: {
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
    reference_system_reference_system_get: {
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
    start_review_session_review_sessions_post: {
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
                "application/json": components["schemas"]["SessionInput"];
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
    finish_review_session_review_sessions__session_id__finish_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FinishInput"];
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
    review_metrics_revisions__identity__review_metrics_get: {
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
    review_validation_revisions__identity__validation_get: {
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
    equipment_review_metrics_equipment__tag__review_metrics_get: {
        parameters: {
            query?: {
                project_id?: string | null;
            };
            header?: never;
            path: {
                tag: string;
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
    undo_field_revisions__identity__audit__audit_id__undo_post: {
        parameters: {
            query?: never;
            header?: {
                "if-match"?: string | null;
                "idempotency-key"?: string | null;
            };
            path: {
                identity: string;
                audit_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UndoInput"];
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
    export_corrections_correcciones_export_post: {
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
    correction_log_correcciones_get: {
        parameters: {
            query?: {
                desde?: string | null;
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
                layers?: boolean;
                marks?: boolean;
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
    diff_visual_diff_visual_get: {
        parameters: {
            query: {
                document_id: string;
                page?: number;
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
            query?: {
                job_id?: string | null;
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
    launch_study_estudio_post: {
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
                "application/json": components["schemas"]["StudyInput"];
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
    learning_corrections_learning_corrections_get: {
        parameters: {
            query?: {
                after?: number;
                limit?: number;
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
    few_shot_learning_few_shot_get: {
        parameters: {
            query?: {
                path?: string | null;
                strategy?: string | null;
                target_revision_id?: string | null;
                limit?: number;
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
    few_shot_evidence_learning_few_shot__example_id__evidence_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                example_id: string;
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
                    "application/json": components["schemas"]["CopilotAnswer"];
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
