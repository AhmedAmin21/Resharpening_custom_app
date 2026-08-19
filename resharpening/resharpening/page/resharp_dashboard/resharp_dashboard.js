frappe.pages["resharp-dashboard"].on_page_load = function (wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Resharpening Dashboard",
        single_column: true
    });

    const $main = $(wrapper).find(".layout-main-section");

    page.current_page = 1;
    page.page_size = 25;

    page.current_filters = {
        supplier: null,
        status: null,
        from_date: null,
        to_date: null
    };

    /*
     * Cache only stores details that the user
     * has already opened during this page session.
     */
    page.order_details_cache = {};

    render_dashboard($main, page);

    load_resharpening_orders($main, page, 1);
};


/* =============================================================
   STATUS LABELS
   ============================================================= */

function get_status_label(status) {

    const labels = {

        "Awaiting Manufacturing":
            "في انتظار الإرسال للمصنع",

        "In Manufacturing":
            "في المصنع",

        "Partially Ready":
            "جاهز جزئياً",

        "Ready / Partially Returned":
            "جاهز / مرتجع جزئياً",

        "Ready":
            "جاهز",

        "Closed":
            "مغلق",

        "Invoiced":
            "تم الفوترة والتسليم"
    };

    return labels[status] || status || "";
}


/* =============================================================
   RENDER DASHBOARD
   ============================================================= */

function render_dashboard($main, page) {

    $main.html(`

        <style>

            /* =================================================
               DASHBOARD
               ================================================= */

            .resharp-dashboard {
                padding-bottom: 30px;
            }


            /* =================================================
               DASHBOARD HEADER
               ================================================= */

            .resharp-dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 18px;
                gap: 10px;
                flex-wrap: wrap;
            }


            .resharp-dashboard-title {
                font-size: 18px;
                font-weight: 600;
                color: var(--text-color);
            }


            .resharp-refresh-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }


            .resharp-refresh-icon {
                font-size: 14px;
                line-height: 1;
            }


            /* =================================================
               SUMMARY CARDS
               ================================================= */

            .resharp-summary-card {
                border: 1px solid var(--border-color);
                border-radius: 10px;
                background: var(--card-bg);
                cursor: pointer;

                transition:
                    transform 0.12s ease,
                    box-shadow 0.12s ease,
                    border-color 0.12s ease,
                    background 0.12s ease;

                height: 100%;
                position: relative;
                overflow: hidden;
            }


            .resharp-summary-card::before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
            }


            .resharp-summary-card:hover {
                transform: translateY(-2px);

                box-shadow:
                    0 4px 14px rgba(
                        0,
                        0,
                        0,
                        0.08
                    );
            }


            .resharp-summary-card.active {
                box-shadow:
                    0 0 0 1px
                    rgba(0, 0, 0, 0.05);
            }


            /* =================================================
               AWAITING
               Yellow / Gold
               ================================================= */

            .resharp-summary-card.awaiting {
                background: rgba(
                    241,
                    196,
                    15,
                    0.08
                );
            }


            .resharp-summary-card.awaiting::before {
                background: #d4ac0d;
            }


            .resharp-summary-card.awaiting
            .resharp-summary-number {
                color: #927500;
            }


            .resharp-summary-card.awaiting.active {
                border-color: #d4ac0d;

                background: rgba(
                    241,
                    196,
                    15,
                    0.13
                );
            }


            /* =================================================
               IN MANUFACTURING
               ================================================= */

            .resharp-summary-card.manufacturing {
                background: rgba(
                    91,
                    192,
                    222,
                    0.07
                );
            }


            .resharp-summary-card.manufacturing::before {
                background: #5bc0de;
            }


            .resharp-summary-card.manufacturing
            .resharp-summary-number {
                color: #247b96;
            }


            .resharp-summary-card.manufacturing.active {
                border-color: #5bc0de;

                background: rgba(
                    91,
                    192,
                    222,
                    0.12
                );
            }


            /* =================================================
               PARTIALLY READY
               Orange
               ================================================= */

            .resharp-summary-card.partial {
                background: rgba(
                    243,
                    156,
                    18,
                    0.07
                );
            }


            .resharp-summary-card.partial::before {
                background: #f39c12;
            }


            .resharp-summary-card.partial
            .resharp-summary-number {
                color: #a96200;
            }


            .resharp-summary-card.partial.active {
                border-color: #f39c12;

                background: rgba(
                    243,
                    156,
                    18,
                    0.12
                );
            }


            /* =================================================
               READY / PARTIALLY RETURNED
               ================================================= */

            .resharp-summary-card.returned {
                background: rgba(
                    139,
                    92,
                    246,
                    0.07
                );
            }


            .resharp-summary-card.returned::before {
                background: #8b5cf6;
            }


            .resharp-summary-card.returned
            .resharp-summary-number {
                color: #6d3fc2;
            }


            .resharp-summary-card.returned.active {
                border-color: #8b5cf6;

                background: rgba(
                    139,
                    92,
                    246,
                    0.12
                );
            }


            /* =================================================
               READY
               ================================================= */

            .resharp-summary-card.ready {
                background: rgba(
                    92,
                    184,
                    92,
                    0.07
                );
            }


            .resharp-summary-card.ready::before {
                background: #5cb85c;
            }


            .resharp-summary-card.ready
            .resharp-summary-number {
                color: #398439;
            }


            .resharp-summary-card.ready.active {
                border-color: #5cb85c;

                background: rgba(
                    92,
                    184,
                    92,
                    0.12
                );
            }


            /* =================================================
               CLOSED
               ================================================= */

            .resharp-summary-card.closed {
                background: rgba(
                    108,
                    117,
                    125,
                    0.07
                );
            }


            .resharp-summary-card.closed::before {
                background: #6c757d;
            }


            .resharp-summary-card.closed
            .resharp-summary-number {
                color: #495057;
            }


            .resharp-summary-card.closed.active {
                border-color: #6c757d;

                background: rgba(
                    108,
                    117,
                    125,
                    0.12
                );
            }


            /* =================================================
               INVOICED
               Teal
               ================================================= */

            .resharp-summary-card.invoiced {
                background: rgba(
                    13,
                    148,
                    136,
                    0.08
                );
            }


            .resharp-summary-card.invoiced::before {
                background: #0d9488;
            }


            .resharp-summary-card.invoiced
            .resharp-summary-number {
                color: #0f766e;
            }


            .resharp-summary-card.invoiced.active {
                border-color: #0d9488;

                background: rgba(
                    13,
                    148,
                    136,
                    0.13
                );
            }


            /* =================================================
               SUMMARY CONTENT
               ================================================= */

            .resharp-summary-label {
                font-size: 13px;
                color: var(--text-color);
                margin-bottom: 6px;
                font-weight: 500;
            }


            .resharp-summary-number {
                font-size: 30px;
                font-weight: 600;
                line-height: 1.1;
            }


            .resharp-summary-hint {
                font-size: 11px;
                color: var(--text-muted);
                margin-top: 7px;
            }


            .resharp-summary-qty {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-muted);
                margin-top: 8px;
            }


            /* =================================================
               FILTERS
               ================================================= */

            .resharp-filters {
                padding: 15px;

                border: 1px solid var(--border-color);
                border-radius: 10px;

                background: var(--card-bg);

                margin-bottom: 18px;
            }


            .resharp-filter-row {
                display: flex;

                align-items: flex-end;

                gap: 12px;

                flex-wrap: wrap;
            }


            .resharp-filter-field {
                min-width: 160px;

                display: flex;

                flex-direction: column;

                justify-content: flex-end;
            }


            .resharp-filter-field.supplier {
                min-width: 250px;
            }


            .resharp-filter-label {
                display: block;

                font-size: 13px;
                font-weight: 500;

                margin-bottom: 6px;

                color: var(--text-color);

                /*
                 * Gives all filter labels the same height
                 * so the inputs line up correctly.
                 */
                min-height: 20px;
                line-height: 20px;
            }


            /*
             * Unify input and button heights & margins across all filters
             */
            .resharp-filter-field .form-control,
            .resharp-filter-field select.form-control,
            .resharp-filter-field input.form-control,
            .resharp-filter-field .clear-filters {
                height: 36px;
                line-height: 1.4;
                margin: 0 !important;
                box-sizing: border-box;
            }


            .resharp-filter-field .clear-filters {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0 16px;
            }


            /*
             * Supplier uses a Frappe Link control.
             * Remove internal margins/padding and hide helper elements
             * so its input aligns seamlessly with the normal filters.
             */
            .resharp-filter-field .supplier-filter {
                width: 100%;
                margin: 0 !important;
                padding: 0 !important;
            }


            .resharp-filter-field .frappe-control,
            .resharp-filter-field .form-group,
            .resharp-filter-field .control-input-wrapper,
            .resharp-filter-field .control-input,
            .resharp-filter-field .link-field,
            .resharp-filter-field .awesomplete {
                width: 100%;
                margin: 0 !important;
                padding: 0 !important;
                border: 0;
            }


            .resharp-filter-field .frappe-control .help-box,
            .resharp-filter-field .frappe-control .clearfix,
            .resharp-filter-field .frappe-control .control-label,
            .resharp-filter-field .frappe-control .control-value {
                display: none !important;
                margin: 0 !important;
                padding: 0 !important;
                min-height: 0 !important;
                height: 0 !important;
            }


            /* =================================================
               TABLE
               ================================================= */

            .resharp-table {
                border-radius: 8px;

                overflow: hidden;

                width: 100%;
            }


            .resharp-table thead th {
                background: var(--subtle-fg);

                font-weight: 600;

                white-space: nowrap;

                vertical-align: middle;
            }


            .resharp-table tbody td {
                vertical-align: middle;
            }


            /*
             * Column sizing
             *
             * Supplier       = 180px
             * Receipt        = 170px
             * Not sent       = 95px
             * Status         = 110px
             *
             * The remaining columns have reasonable widths.
             */

            .resharp-table .col-expand {
                width: 45px;
            }

            .resharp-table .col-supplier {
                width: 180px;
            }

            .resharp-table .col-receipt {
                width: 170px;
            }

            .resharp-table .col-date {
                width: 120px;
            }

            .resharp-table .col-received {
                width: 80px;
            }

            .resharp-table .col-not-sent {
                width: 95px;
            }

            .resharp-table .col-manufacturing {
                width: 90px;
            }

            .resharp-table .col-ready {
                width: 80px;
            }

            .resharp-table .col-returned {
                width: 80px;
            }

            .resharp-table .col-status {
                width: 110px;
            }

            .resharp-table .col-action {
                width: 135px;
            }


            .resharp-order-row:hover {
                background: var(--highlight-color);
            }


            /*
             * Quantity cell highlights
             * Subtle pale green for Ready, subtle pale red for Returned
             */
            .ready-qty-cell {
                background-color: #f0fdf4 !important;
                color: #166534;
            }


            .returned-qty-cell {
                background-color: #fef2f2 !important;
                color: #991b1b;
            }


            .resharp-expand-btn {
                width: 28px;
                height: 28px;
                padding: 0;
            }


            .resharp-receipt-link {
                font-weight: 600;

                cursor: pointer;

                text-decoration: none;

                white-space: nowrap;
            }


            .resharp-receipt-link:hover {
                text-decoration: underline;
            }


            .resharp-details-row {
                background: var(--subtle-fg);
            }


            .resharp-details-container {
                padding: 4px;
            }


            .resharp-details-card {
                background: var(--card-bg);

                border: 1px solid var(--border-color);

                border-radius: 8px;

                padding: 14px;
            }


            .resharp-details-title {
                font-weight: 600;

                margin-bottom: 12px;
            }


            .resharp-item-name {
                color: var(--text-muted);

                font-size: 12px;
            }


            /* =================================================
               STATUS BADGES
               ================================================= */

            .resharp-status-badge {
                display: inline-flex;

                align-items: center;

                gap: 6px;

                padding: 5px 10px;

                border-radius: 999px;

                font-size: 11px;

                font-weight: 600;

                white-space: nowrap;
            }


            .resharp-status-dot {
                width: 7px;

                height: 7px;

                border-radius: 50%;
            }


            /* =================================================
               AWAITING STATUS
               Yellow / Gold
               ================================================= */

            .resharp-status-awaiting {
                background: rgba(
                    241,
                    196,
                    15,
                    0.16
                );

                color: #927500;
            }


            .resharp-status-awaiting
            .resharp-status-dot {
                background: #d4ac0d;
            }


            /* =================================================
               MANUFACTURING STATUS
               ================================================= */

            .resharp-status-manufacturing {
                background: rgba(
                    91,
                    192,
                    222,
                    0.14
                );

                color: #247b96;
            }


            .resharp-status-manufacturing
            .resharp-status-dot {
                background: #5bc0de;
            }


            /* =================================================
               PARTIALLY READY
               Orange
               ================================================= */

            .resharp-status-partial {
                background: rgba(
                    243,
                    156,
                    18,
                    0.14
                );

                color: #a96200;
            }


            .resharp-status-partial
            .resharp-status-dot {
                background: #f39c12;
            }


            /* =================================================
               READY / PARTIALLY RETURNED
               ================================================= */

            .resharp-status-returned {
                background: rgba(
                    139,
                    92,
                    246,
                    0.14
                );

                color: #6d3fc2;
            }


            .resharp-status-returned
            .resharp-status-dot {
                background: #8b5cf6;
            }


            /* =================================================
               READY
               ================================================= */

            .resharp-status-ready {
                background: rgba(
                    92,
                    184,
                    92,
                    0.14
                );

                color: #398439;
            }


            .resharp-status-ready
            .resharp-status-dot {
                background: #5cb85c;
            }


            /* =================================================
               CLOSED
               ================================================= */

            .resharp-status-closed {
                background: rgba(
                    108,
                    117,
                    125,
                    0.14
                );

                color: #495057;
            }


            .resharp-status-closed
            .resharp-status-dot {
                background: #6c757d;
            }


            /* =================================================
               INVOICED
               Teal
               ================================================= */

            .resharp-status-invoiced {
                background: rgba(
                    13,
                    148,
                    136,
                    0.14
                );

                color: #0f766e;
            }


            .resharp-status-invoiced
            .resharp-status-dot {
                background: #0d9488;
            }


            /* =================================================
               UNKNOWN
               ================================================= */

            .resharp-status-unknown {
                background: var(--subtle-fg);

                color: var(--text-muted);
            }


            /* =================================================
               ACTION BUTTONS (NOTE & CLOSE)
               ================================================= */

            .resharp-actions-cell {
                display: flex;
                flex-direction: column;
                align-items: stretch;
                justify-content: center;
                gap: 4px;
                width: 100%;
                max-width: 125px;
                margin: 0 auto;
            }


            .resharp-note-btn {
                font-size: 11px;
                padding: 3px 6px;
                white-space: nowrap;
                border-radius: 4px;
                text-align: center;
                line-height: 1.3;
            }


            .resharp-note-btn.has-note {
                background: #fef3c7;
                border-color: #fcd34d;
                color: #92400e;
                font-weight: 600;
            }


            .resharp-note-btn.has-note:hover {
                background: #fde68a;
                border-color: #f59e0b;
                color: #78350f;
            }


            .resharp-close-btn {
                font-size: 12px;
                font-weight: 600;
                padding: 4px 8px;
                white-space: nowrap;
                border-radius: 4px;
                text-align: center;
                line-height: 1.3;
                width: 100%;
            }


            .resharp-close-btn:disabled {
                opacity: 0.65;

                cursor: wait;
            }


            .resharp-invoice-btn {
                font-size: 11px;
                font-weight: 600;
                padding: 3px 6px;
                white-space: nowrap;
                border-radius: 4px;
                text-align: center;
                line-height: 1.3;
                width: 100%;
                background: #0d9488;
                border-color: #0d9488;
                color: #fff;
            }


            .resharp-invoice-btn:hover {
                background: #0f766e;
                border-color: #0f766e;
                color: #fff;
            }


            .resharp-invoice-btn:disabled {
                opacity: 0.65;
                cursor: wait;
            }


            .resharp-open-invoice-btn {
                font-size: 11px;
                font-weight: 600;
                padding: 4px 6px;
                white-space: nowrap;
                border-radius: 4px;
                text-align: center;
                line-height: 1.3;
                width: 100%;
                background: #0d9488;
                border-color: #0d9488;
                color: #fff;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 4px;
            }


            .resharp-open-invoice-btn:hover {
                background: #0f766e;
                border-color: #0f766e;
                color: #fff;
            }


            .resharp-invoiced-badge-wrap {
                display: inline-flex;
                flex-direction: column;
                align-items: flex-start;
                gap: 4px;
            }


            .resharp-invoiced-qty-tag {
                display: inline-flex;
                align-items: center;
                font-size: 10px;
                font-weight: 600;
                color: #0f766e;
                background: rgba(13, 148, 136, 0.14);
                padding: 2px 8px;
                border-radius: 999px;
                white-space: nowrap;
            }


            /* =================================================
               PAGINATION
               ================================================= */

            .resharp-pagination {
                display: flex;

                justify-content: space-between;

                align-items: center;

                margin-top: 15px;

                padding: 8px 0;

                flex-wrap: wrap;

                gap: 10px;
            }


            .resharp-page-buttons {
                display: flex;

                align-items: center;

                gap: 4px;
            }


            .resharp-page-btn {
                min-width: 32px;
            }


            .resharp-page-info {
                color: var(--text-muted);

                font-size: 12px;
            }


            /* =================================================
               EMPTY STATE
               ================================================= */

            .resharp-empty {
                border: 1px solid var(--border-color);

                border-radius: 10px;

                padding: 50px 20px;

                text-align: center;

                color: var(--text-muted);

                background: var(--card-bg);
            }


            /* =================================================
               RESPONSIVE
               ================================================= */

            @media (max-width: 900px) {

                .resharp-summary-number {
                    font-size: 24px;
                }

                .resharp-pagination {
                    justify-content: center;
                }

            }

        </style>


        <div class="resharp-dashboard">


            <!-- =================================================
                 HEADER
                 ================================================= -->

            <div class="resharp-dashboard-header">

                <div class="resharp-dashboard-title">
                    لوحة متابعة عمليات إعادة الشحذ
                </div>


                <button
                    type="button"
                    class="
                        btn
                        btn-default
                        btn-sm
                        resharp-refresh-btn
                    "
                >

                    <span class="resharp-refresh-icon">
                        ↻
                    </span>

                    تحديث

                </button>

            </div>


            <!-- =================================================
                 SUMMARY CARDS
                 ================================================= -->

            <div
                class="row"
                style="margin-bottom: 18px;"
            >


                <!-- Awaiting -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            awaiting
                        "
                        data-summary-status="Awaiting Manufacturing"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                في انتظار الإرسال للمصنع
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="Awaiting Manufacturing"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                تم الاستلام ولم يُرسل للمصنع
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="Awaiting Manufacturing"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>


                <!-- In Manufacturing -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            manufacturing
                        "
                        data-summary-status="In Manufacturing"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                في المصنع
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="In Manufacturing"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                موجود حالياً في المصنع
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="In Manufacturing"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>


                <!-- Partially Ready -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            partial
                        "
                        data-summary-status="Partially Ready"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                جاهز جزئياً
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="Partially Ready"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                جزء من الطلب أصبح جاهزاً
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="Partially Ready"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>


                <!-- Ready / Partially Returned -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            returned
                        "
                        data-summary-status="Ready / Partially Returned"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                جاهز / مرتجع جزئياً
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="Ready / Partially Returned"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                تم تجهيز الطلب مع وجود مرتجع
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="Ready / Partially Returned"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>


                <!-- Ready -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            ready
                        "
                        data-summary-status="Ready"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                جاهز
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="Ready"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                الطلب بالكامل جاهز
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="Ready"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>


                <!-- Closed -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            closed
                        "
                        data-summary-status="Closed"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                مغلق
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="Closed"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                تم إغلاق إذن الاستلام
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="Closed"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>


                <!-- Invoiced -->

                <div class="col-md-4 col-lg-2 mb-3">

                    <div
                        class="
                            resharp-summary-card
                            invoiced
                        "
                        data-summary-status="Invoiced"
                    >

                        <div
                            class="card-body"
                            style="padding: 18px;"
                        >

                            <div class="resharp-summary-label">
                                تم الفوترة والتسليم
                            </div>

                            <div
                                class="resharp-summary-number"
                                data-status="Invoiced"
                            >
                                0
                            </div>

                            <div class="resharp-summary-hint">
                                الطلبات التي تم إصدار فاتورة مبيعات لها
                            </div>

                            <div
                                class="resharp-summary-qty"
                                data-status-qty="Invoiced"
                            >
                                0 قطعة
                            </div>

                        </div>

                    </div>

                </div>

            </div>


            <!-- =================================================
                 FILTERS
                 ================================================= -->

            <div class="resharp-filters">

                <div class="resharp-filter-row">


                    <!-- Supplier -->

                    <div
                        class="
                            resharp-filter-field
                            supplier
                        "
                    >

                        <label class="resharp-filter-label">
                            المورد
                        </label>

                        <div class="supplier-filter"></div>

                    </div>


                    <!-- Status -->

                    <div class="resharp-filter-field">

                        <label class="resharp-filter-label">
                            الحالة
                        </label>

                        <select
                            class="
                                form-control
                                status-filter
                            "
                        >

                            <option value="">
                                كل الحالات
                            </option>

                            <option value="Awaiting Manufacturing">
                                في انتظار الإرسال للمصنع
                            </option>

                            <option value="In Manufacturing">
                                في المصنع
                            </option>

                            <option value="Partially Ready">
                                جاهز جزئياً
                            </option>

                            <option value="Ready / Partially Returned">
                                جاهز / مرتجع جزئياً
                            </option>

                            <option value="Ready">
                                جاهز
                            </option>

                            <option value="Closed">
                                مغلق
                            </option>

                            <option value="Invoiced">
                                تم الفوترة والتسليم
                            </option>

                        </select>

                    </div>


                    <!-- From Date -->

                    <div class="resharp-filter-field">

                        <label class="resharp-filter-label">
                            من تاريخ
                        </label>

                        <input
                            type="date"
                            class="
                                form-control
                                from-date-filter
                            "
                        >

                    </div>


                    <!-- To Date -->

                    <div class="resharp-filter-field">

                        <label class="resharp-filter-label">
                            إلى تاريخ
                        </label>

                        <input
                            type="date"
                            class="
                                form-control
                                to-date-filter
                            "
                        >

                    </div>


                    <!-- Clear -->

                    <div
                        class="resharp-filter-field"
                        style="min-width: auto;"
                    >

                        <button
                            class="
                                btn
                                btn-default
                                clear-filters
                            "
                            type="button"
                        >
                            مسح
                        </button>

                    </div>


                </div>

            </div>


            <!-- =================================================
                 ORDERS
                 ================================================= -->

            <div class="resharp-orders">

                <div class="text-muted">
                    جاري التحميل...
                </div>

            </div>

        </div>
    `);


    /* =========================================================
       SUPPLIER LINK CONTROL
       ========================================================= */

    page.supplier_control =
        frappe.ui.form.make_control({

            parent:
                $main.find(
                    ".supplier-filter"
                ),

            df: {

                fieldtype: "Link",

                options: "Supplier",

                fieldname: "supplier",

                placeholder:
                    "اختر المورد",

                onchange: function () {

                    page.current_filters.supplier =
                        page.supplier_control
                            .get_value() || null;

                    reload_from_first_page(
                        $main,
                        page
                    );
                }

            },

            render_input: true
        });


    page.supplier_control.make();


    /* =========================================================
       REFRESH BUTTON
       ========================================================= */

    $main.find(
        ".resharp-refresh-btn"
    ).on(
        "click",
        function () {

            const $button = $(this);

            const original_html =
                $button.html();

            page.order_details_cache = {};

            $button.prop(
                "disabled",
                true
            );

            $button.html(`
                <span class="resharp-refresh-icon">
                    ↻
                </span>
                جاري التحديث...
            `);


            frappe.call({

                method:
                    "resharpening.api.dashboard.get_resharpening_orders",

                args: {

                    supplier:
                        page.current_filters.supplier,

                    status:
                        page.current_filters.status,

                    from_date:
                        page.current_filters.from_date,

                    to_date:
                        page.current_filters.to_date,

                    page:
                        page.current_page
                },

                callback: function () {

                    load_resharpening_orders(
                        $main,
                        page,
                        page.current_page
                    );
                },

                error: function () {

                    frappe.msgprint(
                        "حدث خطأ أثناء تحديث لوحة المتابعة."
                    );

                },

                always: function () {

                    $button.prop(
                        "disabled",
                        false
                    );

                    $button.html(
                        original_html
                    );
                }

            });

        }
    );


    /* =========================================================
       STATUS FILTER
       ========================================================= */

    $main.find(
        ".status-filter"
    ).on(
        "change",
        function () {

            page.current_filters.status =
                $(this).val() || null;

            update_active_summary_card(
                $main,
                page.current_filters.status
            );

            reload_from_first_page(
                $main,
                page
            );
        }
    );


    /* =========================================================
       FROM DATE
       ========================================================= */

    $main.find(
        ".from-date-filter"
    ).on(
        "change",
        function () {

            page.current_filters.from_date =
                $(this).val() || null;

            reload_from_first_page(
                $main,
                page
            );
        }
    );


    /* =========================================================
       TO DATE
       ========================================================= */

    $main.find(
        ".to-date-filter"
    ).on(
        "change",
        function () {

            page.current_filters.to_date =
                $(this).val() || null;

            reload_from_first_page(
                $main,
                page
            );
        }
    );


    /* =========================================================
       SUMMARY CARD CLICK
       ========================================================= */

    $main.find(
        ".resharp-summary-card"
    ).on(
        "click",
        function () {

            const selected_status =
                $(this).attr(
                    "data-summary-status"
                );

            const current_status =
                page.current_filters.status;


            if (
                current_status ===
                selected_status
            ) {

                page.current_filters.status =
                    null;

                $main.find(
                    ".status-filter"
                ).val("");

                update_active_summary_card(
                    $main,
                    null
                );

            }

            else {

                page.current_filters.status =
                    selected_status;

                $main.find(
                    ".status-filter"
                ).val(
                    selected_status
                );

                update_active_summary_card(
                    $main,
                    selected_status
                );
            }


            reload_from_first_page(
                $main,
                page
            );
        }
    );


    /* =========================================================
       CLEAR FILTERS
       ========================================================= */

    $main.find(
        ".clear-filters"
    ).on(
        "click",
        function () {

            page.current_filters = {

                supplier: null,

                status: null,

                from_date: null,

                to_date: null
            };


            page.current_page = 1;

            page.order_details_cache = {};


            page.supplier_control
                .set_value("");


            $main.find(
                ".status-filter"
            ).val("");


            $main.find(
                ".from-date-filter"
            ).val("");


            $main.find(
                ".to-date-filter"
            ).val("");


            update_active_summary_card(
                $main,
                null
            );


            load_resharpening_orders(
                $main,
                page,
                1
            );
        }
    );
};


/* =============================================================
   ACTIVE SUMMARY CARD
   ============================================================= */

function update_active_summary_card(
    $main,
    status
) {

    $main.find(
        ".resharp-summary-card"
    ).removeClass(
        "active"
    );


    if (!status) {
        return;
    }


    $main.find(
        `.resharp-summary-card[data-summary-status="${status}"]`
    ).addClass(
        "active"
    );
}


/* =============================================================
   RELOAD FROM FIRST PAGE
   ============================================================= */

function reload_from_first_page(
    $main,
    page
) {

    page.current_page = 1;

    page.order_details_cache = {};

    load_resharpening_orders(
        $main,
        page,
        1
    );
}


/* =============================================================
   LOAD ORDERS
   ============================================================= */

function load_resharpening_orders(
    $main,
    page,
    requested_page
) {

    page.current_page =
        requested_page || 1;


    $main.find(
        ".resharp-orders"
    ).html(`
        <div class="text-muted">
            جاري التحميل...
        </div>
    `);


    frappe.call({

        method:
            "resharpening.api.dashboard.get_resharpening_orders",

        args: {

            supplier:
                page.current_filters.supplier,

            status:
                page.current_filters.status,

            from_date:
                page.current_filters.from_date,

            to_date:
                page.current_filters.to_date,

            page:
                page.current_page
        },


        callback: function (response) {

            const data =
                response.message || {};


            const orders =
                data.orders || [];


            const total_count =
                data.total_count || 0;


            const total_pages =
                data.total_pages || 0;


            const status_counts =
                data.status_counts || {};


            page.current_page =
                data.page ||
                page.current_page;


            update_summary(
                $main,
                status_counts
            );


            render_orders(
                $main,
                page,
                orders,
                total_count,
                total_pages
            );
        },


        error: function () {

            $main.find(
                ".resharp-orders"
            ).html(`

                <div class="alert alert-danger">

                    حدث خطأ أثناء تحميل طلبات إعادة الشحذ.

                </div>

            `);
        }

    });
}


/* =============================================================
   UPDATE SUMMARY CARDS
   ============================================================= */

function update_summary(
    $main,
    counts
) {

    const statuses = [

        "Awaiting Manufacturing",

        "In Manufacturing",

        "Partially Ready",

        "Ready / Partially Returned",

        "Ready",

        "Closed",

        "Invoiced"
    ];


    statuses.forEach(
        function (status) {

            const raw =
                counts[status];

            /*
             * Support both formats:
             *   old: { status: count }
             *   new: { status: { count, total_qty } }
             */
            const is_object =
                raw !== null &&
                typeof raw === "object";

            const order_count =
                is_object
                    ? (raw.count || 0)
                    : (raw || 0);

            const total_qty =
                is_object
                    ? (raw.total_qty || 0)
                    : 0;

            $main.find(
                `.resharp-summary-number[data-status="${status}"]`
            ).text(
                order_count
            );

            $main.find(
                `.resharp-summary-qty[data-status-qty="${status}"]`
            ).text(
                total_qty +
                " قطعة"
            );
        }
    );
}


/* =============================================================
   RENDER ORDERS
   ============================================================= */

function render_orders(
    $main,
    page,
    orders,
    total_count,
    total_pages
) {

    const $container =
        $main.find(
            ".resharp-orders"
        );


    if (!orders.length) {

        $container.html(`

            <div class="resharp-empty">

                <div
                    style="
                        font-size: 18px;
                        font-weight: 600;
                        margin-bottom: 6px;
                    "
                >
                    لا توجد طلبات
                </div>

                <div>
                    حاول تغيير الفلاتر المحددة.
                </div>

            </div>

        `);

        return;
    }


    const first_result =
        get_first_result_number(
            page,
            total_count
        );


    const last_result =
        get_last_result_number(
            page,
            orders.length
        );


    let html = `

        <div
            style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            "
        >

            <div class="text-muted">

                عرض

                <strong>
                    ${first_result}
                </strong>

                -

                <strong>
                    ${last_result}
                </strong>

                من

                <strong>
                    ${total_count}
                </strong>

                طلب

            </div>

        </div>


        <div class="table-responsive">

            <table
                class="
                    table
                    table-bordered
                    resharp-table
                "
            >

                <colgroup>

                    <col class="col-expand">

                    <col class="col-supplier">

                    <col class="col-receipt">

                    <col class="col-date">

                    <col class="col-received">

                    <col class="col-not-sent">

                    <col class="col-manufacturing">

                    <col class="col-ready">

                    <col class="col-returned">

                    <col class="col-status">

                    <col class="col-action">

                </colgroup>


                <thead>

                    <tr>

                        <th></th>

                        <th>
                            المورد
                        </th>

                        <th>
                            إذن الاستلام
                        </th>

                        <th>
                            التاريخ
                        </th>

                        <th class="text-center">
                            المستلم
                        </th>

                        <th class="text-center">
                            لم يُرسل للمصنع
                        </th>

                        <th class="text-center">
                            في المصنع
                        </th>

                        <th class="text-center">
                            الجاهز
                        </th>

                        <th class="text-center">
                            المرتجع
                        </th>

                        <th>
                            الحالة
                        </th>

                        <th class="text-center">
                            الإجراء
                        </th>

                    </tr>

                </thead>

                <tbody>
    `;


    orders.forEach(
        function (order) {

            const receipt =
                frappe.utils.escape_html(
                    order.purchase_receipt
                );


            const can_close =
                order.status === "Ready" ||
                order.status === "Ready / Partially Returned";


            html += `

                <!-- Main order row -->

                <tr
                    class="resharp-order-row"
                    data-purchase-receipt="${receipt}"
                >

                    <!-- Expand -->

                    <td class="text-center">

                        <button
                            type="button"
                            class="
                                btn
                                btn-xs
                                btn-default
                                resharp-expand-btn
                            "
                            data-purchase-receipt="${receipt}"
                            title="عرض الأصناف"
                        >
                            ▶
                        </button>

                    </td>


                    <!-- Supplier -->

                    <td>

                        ${frappe.utils.escape_html(
                            order.supplier || ""
                        )}

                    </td>


                    <!-- Purchase Receipt -->

                    <td>

                        <a
                            href="#Form/Purchase Receipt/${encodeURIComponent(
                                order.purchase_receipt
                            )}"
                            class="resharp-receipt-link"
                            data-purchase-receipt="${receipt}"
                        >
                            ${receipt}
                        </a>

                    </td>


                    <!-- Date -->

                    <td>

                        ${
                            order.receipt_date
                                ? frappe.datetime.str_to_user(
                                    order.receipt_date
                                )
                                : ""
                        }

                    </td>


                    <!-- Received -->

                    <td class="text-center">

                        ${order.received || 0}

                    </td>


                    <!-- Awaiting -->

                    <td class="text-center">

                        ${order.not_sent || 0}

                    </td>


                    <!-- Manufacturing -->

                    <td class="text-center">

                        ${order.in_manufacturing || 0}

                    </td>


                    <!-- Ready -->

                    <td class="text-center ${(order.ready || 0) > 0 ? "ready-qty-cell" : ""}">

                        <strong>
                            ${order.ready || 0}
                        </strong>

                    </td>


                    <!-- Returned -->

                    <td class="text-center ${(order.returned || 0) > 0 ? "returned-qty-cell" : ""}">

                        ${order.returned || 0}

                    </td>


                    <!-- Status -->

                    <td>

                        ${
                            order.status === "Invoiced"
                                ? `
                                    <div class="resharp-invoiced-badge-wrap">
                                        ${get_status_badge(order.status)}
                                        <span class="resharp-invoiced-qty-tag">
                                            الكمية: ${order.invoiced_qty || 0}
                                        </span>
                                    </div>
                                  `
                                : get_status_badge(order.status)
                        }

                    </td>


                    <!-- Action -->

                    <td class="text-center">

                        <div class="resharp-actions-cell">

                            ${
                                order.has_sales_invoice || order.status === "Invoiced"
                                    ? `
                                        <button
                                            type="button"
                                            class="
                                                btn
                                                btn-xs
                                                resharp-open-invoice-btn
                                            "
                                            data-sales-invoice="${frappe.utils.escape_html(
                                                order.sales_invoice || ""
                                            )}"
                                        >
                                            فتح فاتورة المبيعات ↗
                                        </button>
                                      `
                                    : `
                                        <button
                                            type="button"
                                            class="
                                                btn
                                                btn-xs
                                                btn-default
                                                resharp-note-btn
                                                ${order.note ? "has-note" : ""}
                                            "
                                            data-purchase-receipt="${receipt}"
                                            data-note="${frappe.utils.escape_html(order.note || "")}"
                                            title="${order.note ? "عرض / تعديل الملاحظة" : "إضافة ملاحظة"}"
                                        >
                                            ${order.note ? "يوجد ملاحظة" : "ملاحظة"}
                                        </button>

                                        ${
                                            can_close
                                                ? `
                                                    <button
                                                        type="button"
                                                        class="
                                                            btn
                                                            btn-xs
                                                            btn-primary
                                                            resharp-close-btn
                                                        "
                                                        data-purchase-receipt="${receipt}"
                                                        data-status="${frappe.utils.escape_html(
                                                            order.status
                                                        )}"
                                                    >
                                                        إغلاق
                                                    </button>
                                                  `
                                                : ""
                                        }

                                        ${
                                            order.status === "Closed" && !order.has_sales_invoice
                                                ? `
                                                    <button
                                                        type="button"
                                                        class="
                                                            btn
                                                            btn-xs
                                                            resharp-invoice-btn
                                                        "
                                                        data-purchase-receipt="${receipt}"
                                                    >
                                                        فاتورة مبيعات
                                                    </button>
                                                  `
                                                : ""
                                        }
                                      `
                            }

                        </div>

                    </td>

                </tr>


                <!-- Details -->

                <tr
                    class="resharp-details-row"
                    data-details-for="${receipt}"
                    style="display: none;"
                >

                    <td colspan="11">

                        <div
                            class="
                                resharp-details-container
                            "
                        ></div>

                    </td>

                </tr>

            `;
        }
    );


    html += `

                </tbody>

            </table>

        </div>


        ${render_pagination(
            page,
            total_pages
        )}

    `;


    $container.html(
        html
    );


    /* =========================================================
       EXPAND BUTTON
       ========================================================= */

    $container.find(
        ".resharp-expand-btn"
    ).on(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();


            const purchase_receipt =
                $(this).attr(
                    "data-purchase-receipt"
                );


            toggle_order_details(
                $container,
                page,
                purchase_receipt,
                $(this)
            );
        }
    );


    /* =========================================================
       PURCHASE RECEIPT LINK
       ========================================================= */

    $container.find(
        ".resharp-receipt-link"
    ).on(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();


            const purchase_receipt =
                $(this).attr(
                    "data-purchase-receipt"
                );


            frappe.set_route(
                "Form",
                "Purchase Receipt",
                purchase_receipt
            );
        }
    );


    /* =========================================================
       NOTE BUTTON
       ========================================================= */

    $container.find(
        ".resharp-note-btn"
    ).on(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();


            const $button =
                $(this);


            const purchase_receipt =
                $button.attr(
                    "data-purchase-receipt"
                );


            const current_note =
                $button.attr(
                    "data-note"
                ) || "";


            const dialog = new frappe.ui.Dialog({

                title: `ملاحظة على الإذن ${frappe.utils.escape_html(purchase_receipt)}`,

                fields: [
                    {
                        fieldname: "note",
                        fieldtype: "Small Text",
                        label: "الملاحظة",
                        default: current_note,
                        placeholder: "اكتب الملاحظة هنا..."
                    }
                ],

                primary_action_label: "حفظ",

                primary_action: function (values) {

                    const new_note =
                        (values.note || "").trim();

                    dialog.hide();

                    frappe.call({

                        method:
                            "resharpening.api.dashboard.save_resharpening_note",

                        args: {
                            purchase_receipt:
                                purchase_receipt,
                            note:
                                new_note
                        },

                        freeze: true,

                        freeze_message:
                            "جاري حفظ الملاحظة...",

                        callback: function (response) {

                            const result =
                                response.message || {};

                            if (result.success) {

                                frappe.show_alert({
                                    message:
                                        "تم حفظ الملاحظة بنجاح.",
                                    indicator:
                                        "green"
                                });

                                // Update button in place
                                $button.attr(
                                    "data-note",
                                    new_note
                                );

                                if (new_note) {
                                    $button
                                        .addClass("has-note")
                                        .attr("title", "عرض / تعديل الملاحظة")
                                        .text("يوجد ملاحظة");
                                } else {
                                    $button
                                        .removeClass("has-note")
                                        .attr("title", "إضافة ملاحظة")
                                        .text("ملاحظة");
                                }

                            } else {

                                frappe.msgprint({
                                    title: "خطأ",
                                    indicator: "red",
                                    message:
                                        result.message ||
                                        "فشل حفظ الملاحظة."
                                });

                            }

                        }

                    });

                }

            });

            dialog.set_secondary_action_label("إلغاء");

            dialog.show();

        }
    );


    /* =========================================================
       CLOSE BUTTON
       ========================================================= */

    $container.find(
        ".resharp-close-btn"
    ).on(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();


            const $button =
                $(this);


            const purchase_receipt =
                $button.attr(
                    "data-purchase-receipt"
                );


            const status =
                $button.attr(
                    "data-status"
                );


            const arabic_status =
                get_status_label(
                    status
                );


            frappe.confirm(

                `هل أنت متأكد من إغلاق إذن الاستلام <strong>${frappe.utils.escape_html(
                    purchase_receipt
                )}</strong>؟<br><br>` +

                `الحالة الحالية: <strong>${frappe.utils.escape_html(
                    arabic_status
                )}</strong>`,

                function () {

                    $button.prop(
                        "disabled",
                        true
                    );


                    $button.text(
                        "جاري الإغلاق..."
                    );


                    frappe.call({

                        method:
                            "resharpening.api.dashboard.close_resharpening_order",

                        args: {

                            purchase_receipt:
                                purchase_receipt
                        },


                        callback:
                            function (response) {

                                const result =
                                    response.message || {};


                                if (
                                    result.success
                                ) {

                                    delete page.order_details_cache[
                                        purchase_receipt
                                    ];


                                    frappe.show_alert({

                                        message:
                                            "تم إغلاق إذن الاستلام بنجاح.",

                                        indicator:
                                            "green"

                                    });


                                    load_resharpening_orders(
                                        $main,
                                        page,
                                        page.current_page
                                    );

                                }

                                else {

                                    frappe.msgprint(
                                        "لم يتم إغلاق إذن الاستلام."
                                    );

                                }

                            },


                        error:
                            function () {

                                frappe.msgprint(
                                    "حدث خطأ أثناء إغلاق إذن الاستلام."
                                );

                            },


                        always:
                            function () {

                                $button.prop(
                                    "disabled",
                                    false
                                );

                                $button.text(
                                    "إغلاق"
                                );

                            }

                    });

                }

            );
        }
    );


    /* =========================================================
       SALES INVOICE BUTTON (CREATE)
       ========================================================= */

    $container.find(
        ".resharp-invoice-btn"
    ).on(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();


            const $button =
                $(this);


            const purchase_receipt =
                $button.attr(
                    "data-purchase-receipt"
                );


            $button.prop(
                "disabled",
                true
            );

            $button.text(
                "جاري الإنشاء..."
            );


            frappe.call({

                method:
                    "resharpening.api.dashboard.create_resharpening_sales_invoice",

                args: {
                    purchase_receipt:
                        purchase_receipt
                },

                callback: function (response) {

                    const result =
                        response.message || {};


                    if (result.existing && result.sales_invoice_name) {

                        frappe.show_alert({
                            message:
                                "تم العثور على فاتورة مبيعات سابقة، جاري فتحها...",
                            indicator:
                                "blue"
                        });

                        frappe.set_route(
                            "Form",
                            "Sales Invoice",
                            result.sales_invoice_name
                        );

                        return;
                    }


                    if (result.invoice_data) {

                        const invoice_data =
                            result.invoice_data;


                        frappe.model.with_doctype(
                            "Sales Invoice",
                            function () {

                                const new_doc =
                                    frappe.model.get_new_doc(
                                        "Sales Invoice"
                                    );


                                new_doc.customer =
                                    invoice_data.customer;

                                new_doc.custom_resharpening_purchase_receipt =
                                    invoice_data.custom_resharpening_purchase_receipt;

                                if (invoice_data.company) {
                                    new_doc.company =
                                        invoice_data.company;
                                }


                                if (
                                    invoice_data.items &&
                                    invoice_data.items.length
                                ) {

                                    new_doc.items = [];

                                    invoice_data.items.forEach(
                                        function (item) {

                                            const row =
                                                frappe.model.add_child(
                                                    new_doc,
                                                    "items"
                                                );

                                            row.item_code =
                                                item.item_code;

                                            row.item_name =
                                                item.item_name ||
                                                item.item_code;

                                            row.qty =
                                                item.qty;

                                            row.uom =
                                                item.uom ||
                                                "Nos";

                                            row.stock_uom =
                                                item.stock_uom ||
                                                item.uom ||
                                                "Nos";

                                            row.conversion_factor =
                                                item.conversion_factor ||
                                                1;

                                            if (item.description) {
                                                row.description =
                                                    item.description;
                                            }
                                        }
                                    );
                                }


                                frappe.set_route(
                                    "Form",
                                    "Sales Invoice",
                                    new_doc.name
                                );
                            }
                        );
                    }
                },

                error: function () {
                    // Handled by frappe msgprint
                },

                always: function () {

                    $button.prop(
                        "disabled",
                        false
                    );

                    $button.text(
                        "فاتورة مبيعات"
                    );
                }

            });
        }
    );


    /* =========================================================
       OPEN SALES INVOICE BUTTON
       ========================================================= */

    $container.find(
        ".resharp-open-invoice-btn"
    ).on(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();


            const sales_invoice =
                $(this).attr(
                    "data-sales-invoice"
                );


            if (sales_invoice) {

                frappe.set_route(
                    "Form",
                    "Sales Invoice",
                    sales_invoice
                );

            } else {

                frappe.msgprint(
                    "لم يتم العثور على اسم فاتورة المبيعات."
                );

            }
        }
    );

    $container.find(
        ".resharp-page-btn"
    ).on(
        "click",
        function () {

            const target_page =
                parseInt(
                    $(this).attr(
                        "data-page"
                    )
                );


            if (
                !target_page ||
                target_page < 1 ||
                target_page > total_pages ||
                target_page === page.current_page
            ) {

                return;
            }


            load_resharpening_orders(
                $main,
                page,
                target_page
            );
        }
    );
}


/* =============================================================
   PAGINATION
   ============================================================= */

function render_pagination(
    page,
    total_pages
) {

    if (total_pages <= 1) {
        return "";
    }


    let html = `

        <div class="resharp-pagination">

            <div class="resharp-page-info">

                الصفحة

                <strong>
                    ${page.current_page}
                </strong>

                من

                <strong>
                    ${total_pages}
                </strong>

            </div>


            <div class="resharp-page-buttons">


                <!-- Previous -->

                <button
                    class="
                        btn
                        btn-default
                        btn-sm
                        resharp-page-btn
                    "
                    data-page="${page.current_page - 1}"
                    ${
                        page.current_page <= 1
                            ? "disabled"
                            : ""
                    }
                >
                    ‹
                </button>

    `;


    const max_visible_pages = 7;


    let start_page =
        Math.max(
            1,
            page.current_page - 3
        );


    let end_page =
        Math.min(
            total_pages,
            start_page +
                max_visible_pages -
                1
        );


    if (
        end_page - start_page + 1
        < max_visible_pages
    ) {

        start_page =
            Math.max(
                1,
                end_page -
                    max_visible_pages +
                    1
            );
    }


    /* First page */

    if (start_page > 1) {

        html += `

            <button
                class="
                    btn
                    btn-default
                    btn-sm
                    resharp-page-btn
                "
                data-page="1"
            >
                1
            </button>

        `;


        if (start_page > 2) {

            html += `

                <span
                    style="
                        padding: 0 4px;
                    "
                >
                    ...
                </span>

            `;
        }
    }


    /* Page numbers */

    for (
        let i = start_page;
        i <= end_page;
        i++
    ) {

        html += `

            <button
                class="
                    btn
                    btn-sm
                    resharp-page-btn
                    ${
                        i === page.current_page
                            ? "btn-primary"
                            : "btn-default"
                    }
                "
                data-page="${i}"
            >
                ${i}
            </button>

        `;
    }


    /* Last page */

    if (
        end_page < total_pages
    ) {

        if (
            end_page <
            total_pages - 1
        ) {

            html += `

                <span
                    style="
                        padding: 0 4px;
                    "
                >
                    ...
                </span>

            `;
        }


        html += `

            <button
                class="
                    btn
                    btn-default
                    btn-sm
                    resharp-page-btn
                "
                data-page="${total_pages}"
            >
                ${total_pages}
            </button>

        `;
    }


    /* Next */

    html += `

                <button
                    class="
                        btn
                        btn-default
                        btn-sm
                        resharp-page-btn
                    "
                    data-page="${page.current_page + 1}"
                    ${
                        page.current_page >= total_pages
                            ? "disabled"
                            : ""
                    }
                >
                    ›
                </button>

            </div>

        </div>

    `;


    return html;
}


/* =============================================================
   PAGINATION HELPERS
   ============================================================= */

function get_first_result_number(
    page,
    total_count
) {

    if (!total_count) {
        return 0;
    }


    return (
        (page.current_page - 1)
        * page.page_size
    ) + 1;
}


function get_last_result_number(
    page,
    current_page_count
) {

    return (
        (page.current_page - 1)
        * page.page_size
    ) + current_page_count;
}


/* =============================================================
   TOGGLE ORDER DETAILS
   ============================================================= */

function toggle_order_details(
    $container,
    page,
    purchase_receipt,
    $button
) {

    const $details_row =
        $container.find(
            ".resharp-details-row"
        ).filter(
            function () {

                return $(this).attr(
                    "data-details-for"
                ) === purchase_receipt;
            }
        );


    const is_visible =
        $details_row.is(":visible");


    /* CLOSE */

    if (is_visible) {

        $details_row.hide();

        $button.text(
            "▶"
        );

        return;
    }


    /* OPEN */

    $details_row.show();

    $button.text(
        "▼"
    );


    /* CACHE */

    if (
        page.order_details_cache[
            purchase_receipt
        ]
    ) {

        render_order_details_row(
            $details_row,
            page.order_details_cache[
                purchase_receipt
            ]
        );

        return;
    }


    /* LOADING */

    $details_row.find(
        ".resharp-details-container"
    ).html(`

        <div class="text-muted">
            جاري تحميل الأصناف...
        </div>

    `);


    /* API */

    frappe.call({

        method:
            "resharpening.api.dashboard.get_resharpening_order_details",

        args: {

            purchase_receipt:
                purchase_receipt
        },


        callback: function (response) {

            const data =
                response.message;


            if (!data) {

                $details_row.find(
                    ".resharp-details-container"
                ).html(`

                    <div class="alert alert-danger">

                        تعذر تحميل تفاصيل الطلب.

                    </div>

                `);

                return;
            }


            page.order_details_cache[
                purchase_receipt
            ] = data;


            render_order_details_row(
                $details_row,
                data
            );
        },


        error: function () {

            $details_row.find(
                ".resharp-details-container"
            ).html(`

                <div class="alert alert-danger">

                    حدث خطأ أثناء تحميل تفاصيل الطلب.

                </div>

            `);
        }

    });
}


/* =============================================================
   RENDER ORDER DETAILS
   ============================================================= */

function render_order_details_row(
    $details_row,
    data
) {

    let html = `

        <div class="resharp-details-card">

            <div class="resharp-details-title">
                الأصناف
            </div>


            <div class="table-responsive">

                <table
                    class="
                        table
                        table-bordered
                        table-sm
                    "
                    style="margin-bottom: 0;"
                >

                    <thead>

                        <tr>

                            <th>
                                الصنف
                            </th>

                            <th class="text-center">
                                المستلم
                            </th>

                            <th class="text-center">
                                لم يُرسل للمصنع
                            </th>

                            <th class="text-center">
                                في المصنع
                            </th>

                            <th class="text-center">
                                الجاهز
                            </th>

                            <th class="text-center">
                                المرتجع
                            </th>

                        </tr>

                    </thead>

                    <tbody>

    `;


    /* NO ITEMS */

    if (
        !data.items ||
        !data.items.length
    ) {

        html += `

            <tr>

                <td
                    colspan="6"
                    class="
                        text-muted
                        text-center
                    "
                >

                    لا توجد أصناف.

                </td>

            </tr>

        `;
    }


    /* ITEMS */

    (data.items || []).forEach(
        function (item) {

            html += `

                <tr>

                    <!-- Item -->

                    <td>

                        <strong>

                            ${frappe.utils.escape_html(
                                item.item_code || ""
                            )}

                        </strong>


                        ${
                            item.item_name
                                ? `

                                    <div
                                        class="
                                            resharp-item-name
                                        "
                                    >

                                        ${frappe.utils.escape_html(
                                            item.item_name
                                        )}

                                    </div>

                                  `
                                : ""
                        }

                    </td>


                    <!-- Received -->

                    <td class="text-center">

                        ${item.received || 0}

                    </td>


                    <!-- Awaiting -->

                    <td class="text-center">

                        ${item.not_sent || 0}

                    </td>


                    <!-- Manufacturing -->

                    <td class="text-center">

                        ${item.in_manufacturing || 0}

                    </td>


                    <!-- Ready -->

                    <td class="text-center ${(item.ready || 0) > 0 ? "ready-qty-cell" : ""}">

                        <strong>
                            ${item.ready || 0}
                        </strong>

                    </td>


                    <!-- Returned -->

                    <td class="text-center ${(item.returned || 0) > 0 ? "returned-qty-cell" : ""}">

                        ${item.returned || 0}

                    </td>

                </tr>

            `;
        }
    );


    html += `

                    </tbody>

                </table>

            </div>

        </div>

    `;


    $details_row.find(
        ".resharp-details-container"
    ).html(
        html
    );
}


/* =============================================================
   STATUS BADGE
   ============================================================= */

function get_status_badge(
    status
) {

    let css_class =
        "resharp-status-unknown";


    if (
        status === "Awaiting Manufacturing"
    ) {

        css_class =
            "resharp-status-awaiting";
    }


    else if (
        status === "In Manufacturing"
    ) {

        css_class =
            "resharp-status-manufacturing";
    }


    else if (
        status === "Partially Ready"
    ) {

        css_class =
            "resharp-status-partial";
    }


    else if (
        status === "Ready / Partially Returned"
    ) {

        css_class =
            "resharp-status-returned";
    }


    else if (
        status === "Ready"
    ) {

        css_class =
            "resharp-status-ready";
    }


    else if (
        status === "Closed"
    ) {

        css_class =
            "resharp-status-closed";
    }


    else if (
        status === "Invoiced"
    ) {

        css_class =
            "resharp-status-invoiced";
    }


    return `

        <span
            class="
                resharp-status-badge
                ${css_class}
            "
        >

            <span
                class="
                    resharp-status-dot
                "
            ></span>


            ${frappe.utils.escape_html(
                get_status_label(status)
            )}

        </span>

    `;
}
