"""
CLARIVENS ENTERPRISE DATA INTELLIGENCE
Architecture & Flow Diagram Generator
Author: Himanshu Bagde (Azure Data Engineer & Cloud Analytics Architect)
Organization: CLARIVENS DATA PLATFORMS

Generates 3 presentation-ready architectural diagrams:
1. architecture-diagram.png: Full Cloud Architecture (ADLS, ADF, Azure SQL, Python DQ, Power BI, Monitoring)
2. data-flow.png: End-to-End Data Pipeline Flow & Quality Gates
3. star-schema.png: Star Schema Dimensional Model ERD

Theme: Clarivens Black + Orange + Liquid Glassmorphism
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.dirname(__file__)

# Clarivens Enterprise Color Palette
BG_COLOR = "#050505"
CARD_BG = "#0E0E12"
CARD_INNER = "#141418"
BORDER_COLOR = "#222226"

ORANGE = "#FF6A00"
ORANGE_BRIGHT = "#FF7A00"
ORANGE_SOFT = "#FF8A1F"
ORANGE_HIGHLIGHT = "#FFB067"

AMBER = "#F59E0B"
GREEN = "#10B981"
RED = "#EF4444"
WHITE = "#FFFFFF"
MUTED = "#8E8E93"
GRAY_LIGHT = "#E4E4E7"

def draw_diagram_header(fig, ax, title, subtitle):
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "clarivens_icon.png")
    if os.path.exists(logo_path):
        import matplotlib.image as mpimg
        logo_img = mpimg.imread(logo_path)
        logo_ax = ax.inset_axes([0.035, 0.925, 0.022, 0.048])
        logo_ax.imshow(logo_img, aspect="equal")
        logo_ax.axis("off")
    else:
        logo_bg = patches.FancyBboxPatch((0.038, 0.932), 0.016, 0.038, boxstyle="round,pad=0.003,rounding_size=0.005",
                                         transform=ax.transAxes, facecolor="#141418", edgecolor=ORANGE, linewidth=1.2)
        ax.add_patch(logo_bg)
        ax.text(0.046, 0.951, "C", transform=ax.transAxes, color=ORANGE_BRIGHT, fontsize=11, fontweight="bold", ha="center", va="center")

    ax.text(0.062, 0.956, title, color=WHITE, fontsize=15, fontweight="bold")
    ax.text(0.062, 0.932, subtitle, color=ORANGE_SOFT, fontsize=9.5)

def create_architecture_diagram():
    print("Generating architecture-diagram.png...")
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.axis("off")

    draw_diagram_header(fig, ax,
                        "CLARIVENS ENTERPRISE DATA INTELLIGENCE",
                        "Production End-to-End Architecture: Azure Data Factory, Azure SQL Database, Python DQ & Power BI")

    # 4 Architecture Columns / Swimlanes
    columns = [
        ("1. INGESTION & SOURCES", 0.038, 0.205, [
            ("CSV Feeds (ADLS Gen2)", "12 Monthly Sales (120k+ rows)\n12 Weekly Inventory (42k+ rows)\nMaster Products, Stores, Suppliers\nPO Purchases & Return Events"),
            ("Mock REST API Feed", "Supplier Catalog & Replenishment SLAs\nDynamic Price & Safety Stock Feed\nBearer Token Auth & Pagination")
        ]),
        ("2. ORCHESTRATION & DQ", 0.275, 0.22, [
            ("Azure Data Factory v2", "PL_Master_Retail_Inventory\n11 Parameterized Child Pipelines\nTumbling & Schedule Triggers\nAutomated Retries & Logging"),
            ("Python Data Quality Gate", "12 Modular Validation Rules (75 checks)\nSchema, Nulls, Duplicates, Math\nAutomated Cleansing & Reconcile\nQuality Gate Enforcement (>= 98%)")
        ]),
        ("3. STORAGE & WAREHOUSE", 0.525, 0.22, [
            ("Staging Layer (stg schema)", "Raw Landing Tables\nIngestion Auditing Timestamps\nPre-Copy Truncate & Bulk Insert"),
            ("Star Schema Warehouse (dw)", "FactSales, FactInventory, FactPurchases\nDimDate, DimProduct, DimStore\nDimSupplier, DimCategory\nSCD Type 1/2 & Surrogate Keys")
        ]),
        ("4. ANALYTICS & OBSERVABILITY", 0.775, 0.20, [
            ("Power BI Analytics Suite", "6 Executive & Operational Pages\nInventory Stockout Risk Matrix\n25+ DAX Measures & Liquid Theme\nInteractive Slicers & Tooltips"),
            ("Audit & Governance", "audit.PipelineExecutionLog\naudit.DataQualityLog\naudit.ETL_Control (High-Watermark)")
        ])
    ]

    for col_title, x, w, boxes in columns:
        # Outer container (Liquid Glass Card)
        rect_col = patches.FancyBboxPatch((x, 0.05), w, 0.84, boxstyle="round,pad=0.012,rounding_size=0.015",
                                          facecolor=CARD_BG, edgecolor=BORDER_COLOR, linewidth=1.2)
        ax.add_patch(rect_col)
        
        # Orange top indicator
        col_accent = patches.Rectangle((x + 0.01, 0.887), w - 0.02, 0.003, transform=ax.transAxes, facecolor=ORANGE, alpha=0.8)
        ax.add_patch(col_accent)
        
        ax.text(x + 0.014, 0.855, col_title, color=ORANGE_BRIGHT, fontsize=9.5, fontweight="bold")

        # Inner components
        y_box = 0.50
        for title, desc in boxes:
            rect_b = patches.FancyBboxPatch((x + 0.01, y_box), w - 0.02, 0.31, boxstyle="round,pad=0.008,rounding_size=0.01",
                                            facecolor=CARD_INNER, edgecolor=BORDER_COLOR, linewidth=1)
            ax.add_patch(rect_b)
            
            # Subtle orange border highlight on inner box
            ax.text(x + 0.02, y_box + 0.26, title, color=WHITE, fontsize=9.5, fontweight="bold")
            ax.text(x + 0.02, y_box + 0.04, desc, color=MUTED, fontsize=8, linespacing=1.65)
            y_box -= 0.38

    # Connecting Flow Arrows (Clarivens Orange)
    arrow_props = dict(arrowstyle="->,head_width=0.45,head_length=0.7", color=ORANGE, lw=2.5)
    ax.annotate("", xy=(0.275, 0.65), xytext=(0.245, 0.65), arrowprops=arrow_props)
    ax.annotate("", xy=(0.525, 0.65), xytext=(0.495, 0.65), arrowprops=arrow_props)
    ax.annotate("", xy=(0.775, 0.65), xytext=(0.745, 0.65), arrowprops=arrow_props)

    # Bottom Audit feedback loop arrow (Clarivens Orange Soft)
    ax.annotate("", xy=(0.38, 0.18), xytext=(0.775, 0.18),
                arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", color=ORANGE_SOFT, lw=1.5, ls="--"))
    ax.text(0.575, 0.20, "Telemetry, Audit Logs & Watermark State Feedback", color=ORANGE_SOFT, fontsize=8, fontweight="bold", ha="center")

    plt.savefig(os.path.join(OUTPUT_DIR, "architecture-diagram.png"), dpi=200, bbox_inches="tight")
    plt.close()
    print("  -> Saved architecture-diagram.png")

def create_data_flow_diagram():
    print("Generating data-flow.png...")
    fig, ax = plt.subplots(figsize=(16, 9), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.axis("off")

    draw_diagram_header(fig, ax,
                        "CLARIVENS ENTERPRISE DATA INTELLIGENCE — END-TO-END DATA FLOW",
                        "Sequential Ingestion, Quality Evaluation, Incremental Watermarking & Star Schema Load")

    steps = [
        ("Step 1: Raw Ingestion", "ADLS Gen2 CSVs & REST API\nIngested into stg.* tables\nADF Copy Activities with retries", 0.04, 0.50, ORANGE_BRIGHT),
        ("Step 2: Quality Gate", "Python Validation Engine\nEvaluates 12 core rule categories\nQuality score >= 98% gate", 0.28, 0.50, ORANGE),
        ("Step 3: Dimensional ETL", "dw.sp_Load_FactSales\ndw.sp_Load_FactInventory\nResolves surrogate keys & deduplicates", 0.52, 0.50, ORANGE_SOFT),
        ("Step 4: Metric Engine", "sp_Update_InventoryMetrics\nCalculates ADS & Days of Inventory\nFlags Critical/High Stockout alerts", 0.76, 0.50, ORANGE_HIGHLIGHT)
    ]

    for title, desc, x, y, col in steps:
        rect = patches.FancyBboxPatch((x, y - 0.12), 0.20, 0.28, boxstyle="round,pad=0.012,rounding_size=0.012",
                                      facecolor=CARD_BG, edgecolor=col, linewidth=1.8)
        ax.add_patch(rect)
        
        # Inner header accent
        ax.text(x + 0.015, y + 0.105, title, color=col, fontsize=10.5, fontweight="bold")
        ax.text(x + 0.015, y - 0.08, desc, color=WHITE, fontsize=8.5, linespacing=1.65)

    # Orange Data Flow Connectors
    for start_x in [0.24, 0.48, 0.72]:
        ax.annotate("", xy=(start_x + 0.04, 0.52), xytext=(start_x, 0.52),
                    arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.7", color=ORANGE, lw=2.5))

    # Lower Observability Box
    rect_obs = patches.FancyBboxPatch((0.04, 0.10), 0.92, 0.21, boxstyle="round,pad=0.012,rounding_size=0.012",
                                      facecolor=CARD_INNER, edgecolor=BORDER_COLOR, linewidth=1.2)
    ax.add_patch(rect_obs)
    
    # Orange top line
    obs_accent = patches.Rectangle((0.05, 0.307), 0.90, 0.002, transform=ax.transAxes, facecolor=ORANGE, alpha=0.8)
    ax.add_patch(obs_accent)
    
    ax.text(0.06, 0.265, "CENTRALIZED OBSERVABILITY & HIGH-WATERMARK CONTROLS", color=ORANGE_BRIGHT, fontsize=10.5, fontweight="bold")
    ax.text(0.06, 0.145,
            "• audit.ETL_Control: High-watermark mechanism tracking LastWatermarkValue (SaleDate) to ensure only Delta transactions are processed.\n"
            "• audit.DataQualityLog: Structured record of every validation check (RuleName, TotalRecords, FailedRecords, PassPercentage, Status).\n"
            "• audit.PipelineExecutionLog: Full activity execution telemetry (RunID, ActivityName, RowsProcessed, RowsFailed, Duration, Status).",
            color=MUTED, fontsize=8.5, linespacing=1.6)

    plt.savefig(os.path.join(OUTPUT_DIR, "data-flow.png"), dpi=200, bbox_inches="tight")
    plt.close()
    print("  -> Saved data-flow.png")

def create_star_schema_diagram():
    print("Generating star-schema.png...")
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.axis("off")

    draw_diagram_header(fig, ax,
                        "CLARIVENS ENTERPRISE DATA INTELLIGENCE — STAR SCHEMA DATA MODEL",
                        "Enterprise Dimensional Architecture in Azure SQL Database (dw schema)")

    # Central Fact Tables (Orange Highlighted)
    facts = [
        ("dw.FactSales", 0.38, 0.55, 0.24, 0.32, [
            ("SalesSK (PK)", True), ("SaleID", False), ("DateKey (FK)", True),
            ("ProductSK (FK)", True), ("StoreSK (FK)", True), ("Quantity", False),
            ("Revenue", False), ("Cost", False), ("GrossProfit", False), ("PaymentMethod", False)
        ]),
        ("dw.FactInventory", 0.38, 0.12, 0.24, 0.36, [
            ("InventorySK (PK)", True), ("InventoryID", False), ("DateKey (FK)", True),
            ("ProductSK (FK)", True), ("StoreSK (FK)", True), ("OpeningStock", False),
            ("ReceivedQuantity", False), ("ClosingStock", False), ("InventoryValue", False),
            ("DaysOfInventory", False), ("StockoutRiskLevel", False), ("ReorderRequired", False)
        ])
    ]

    # Surrounding Dimension Tables (Dark Glass with Clean Borders)
    dimensions = [
        ("dw.DimProduct", 0.06, 0.55, 0.22, 0.32, [
            ("ProductSK (PK)", True), ("ProductID", False), ("ProductName", False),
            ("CategoryID (FK)", True), ("CategoryName", False), ("Brand", False),
            ("UnitCost", False), ("UnitPrice", False), ("ReorderLevel", False), ("IsCurrent", False)
        ]),
        ("dw.DimStore", 0.06, 0.15, 0.22, 0.28, [
            ("StoreSK (PK)", True), ("StoreID", False), ("StoreName", False),
            ("City", False), ("State", False), ("Region", False), ("StoreType", False), ("SquareFeet", False)
        ]),
        ("dw.DimDate", 0.72, 0.55, 0.22, 0.32, [
            ("DateKey (PK)", True), ("FullDate", False), ("DayName", False),
            ("MonthName", False), ("CalendarQuarter", False), ("CalendarYear", False),
            ("FiscalQuarter", False), ("IsFestivalSeason", False), ("IsWeekend", False)
        ]),
        ("dw.DimSupplier", 0.72, 0.15, 0.22, 0.28, [
            ("SupplierSK (PK)", True), ("SupplierID", False), ("SupplierName", False),
            ("City", False), ("State", False), ("Rating", False), ("LeadTimeDays", False), ("PaymentTerms", False)
        ])
    ]

    def draw_table_card(title, x, y, w, h, cols, is_fact=False):
        edge_col = ORANGE if is_fact else BORDER_COLOR
        bg_col = CARD_BG
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.01",
                                      facecolor=bg_col, edgecolor=edge_col, linewidth=1.5 if is_fact else 1)
        ax.add_patch(rect)
        
        # Header banner
        hdr_bg = "#18181C" if is_fact else "#101014"
        rect_hdr = patches.Rectangle((x, y + h - 0.04), w, 0.04, facecolor=hdr_bg, edgecolor=edge_col, linewidth=0.5)
        ax.add_patch(rect_hdr)
        
        # Header text
        title_col = ORANGE_BRIGHT if is_fact else WHITE
        ax.text(x + 0.012, y + h - 0.025, title, color=title_col, fontsize=9.5, fontweight="bold")

        curr_y = y + h - 0.07
        for cname, is_key in cols:
            k_col = ORANGE if is_key else WHITE
            fontw = "bold" if is_key else "normal"
            ax.text(x + 0.015, curr_y, cname, color=k_col, fontsize=8, fontweight=fontw)
            curr_y -= 0.027

    for title, x, y, w, h, cols in facts:
        draw_table_card(title, x, y, w, h, cols, is_fact=True)

    for title, x, y, w, h, cols in dimensions:
        draw_table_card(title, x, y, w, h, cols, is_fact=False)

    # Relationship connectors (Orange dashed lines)
    conn_props = dict(arrowstyle="<->", color=ORANGE_SOFT, lw=1.5, ls="--")
    # DimProduct to FactSales
    ax.annotate("", xy=(0.38, 0.72), xytext=(0.28, 0.72), arrowprops=conn_props)
    # DimDate to FactSales
    ax.annotate("", xy=(0.62, 0.72), xytext=(0.72, 0.72), arrowprops=conn_props)
    # DimStore to FactSales
    ax.annotate("", xy=(0.38, 0.60), xytext=(0.28, 0.30), arrowprops=conn_props)
    # DimProduct to FactInventory
    ax.annotate("", xy=(0.38, 0.28), xytext=(0.28, 0.60), arrowprops=conn_props)
    # DimStore to FactInventory
    ax.annotate("", xy=(0.38, 0.22), xytext=(0.28, 0.22), arrowprops=conn_props)
    # DimDate to FactInventory
    ax.annotate("", xy=(0.62, 0.28), xytext=(0.72, 0.60), arrowprops=conn_props)

    plt.savefig(os.path.join(OUTPUT_DIR, "star-schema.png"), dpi=200, bbox_inches="tight")
    plt.close()
    print("  -> Saved star-schema.png")

def main():
    print("==========================================================================")
    print(" CLARIVENS ENTERPRISE DATA INTELLIGENCE — ARCHITECTURE DIAGRAM GENERATOR")
    print(" Rendering Presentation-Ready Black & Orange Architecture Diagrams")
    print("==========================================================================")
    create_architecture_diagram()
    create_data_flow_diagram()
    create_star_schema_diagram()
    print("==========================================================================")
    print(f" All 3 Architecture Diagrams saved in {OUTPUT_DIR}")
    print("==========================================================================")

if __name__ == "__main__":
    main()
