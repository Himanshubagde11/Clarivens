"""
Clarivens AI Agent — Service Catalog & Knowledge Base Seed Script.

Seeds initial:
1. ServiceCatalog entries (Clarivens service taxonomy)
2. ServicePackage entries (with placeholder pricing — update via admin)
3. AgentKnowledge entries (Clarivens knowledge base v1.0)
4. AgentVersion entry (v1.0.0)

Run once on first deployment, or call seed_all() idempotently.
Existing records are not overwritten.
"""
import logging
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database import models
from backend.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Service Catalog
# ============================================================

SERVICES = [
    # Data Services
    {
        "name": "Data Cleaning & Preparation",
        "slug": "data-cleaning",
        "category": "data_services",
        "description": "Transform raw, messy data into clean, analysis-ready datasets. We handle duplicates, missing values, inconsistencies, formatting issues, and schema normalization.",
        "short_description": "Turn messy data into clean, analysis-ready datasets.",
        "features": ["Duplicate removal", "Missing value treatment", "Schema normalization", "Data type correction", "Outlier detection", "Quality scoring"],
        "keywords": ["messy", "dirty", "clean", "cleaning", "preparation", "duplicate", "missing", "quality", "raw data", "fix", "excel", "csv"],
    },
    {
        "name": "Data Quality Assessment",
        "slug": "data-quality",
        "category": "data_services",
        "description": "Comprehensive audit of your dataset's completeness, accuracy, consistency, and reliability. Receive a data quality report with actionable recommendations.",
        "short_description": "Comprehensive audit of your data quality.",
        "features": ["Completeness scoring", "Accuracy assessment", "Consistency checks", "Data quality report", "Remediation recommendations"],
        "keywords": ["quality", "audit", "assessment", "completeness", "accuracy", "reliable", "trust", "score"],
    },
    # Analytics
    {
        "name": "Exploratory Data Analysis",
        "slug": "eda",
        "category": "analytics",
        "description": "Deep exploration of your dataset to uncover patterns, distributions, correlations, and anomalies. Delivered as an interactive report.",
        "short_description": "Uncover patterns, trends, and anomalies in your data.",
        "features": ["Statistical summaries", "Correlation analysis", "Distribution analysis", "Outlier detection", "Interactive visualizations", "Executive summary"],
        "keywords": ["explore", "exploration", "pattern", "distribution", "correlation", "understand", "eda", "statistical", "overview", "what is in my data"],
    },
    {
        "name": "Sales Analytics",
        "slug": "sales-analytics",
        "category": "analytics",
        "description": "Analyze sales performance, identify revenue drivers, understand product and regional performance, and detect declining trends.",
        "short_description": "Understand what's driving or hurting your sales.",
        "features": ["Revenue trend analysis", "Product performance", "Regional breakdown", "Sales velocity metrics", "YoY / MoM comparisons", "Top/bottom performer analysis"],
        "keywords": ["sales", "revenue", "orders", "products", "regions", "performance", "decline", "growth", "falling", "increasing", "top products", "best sellers"],
    },
    {
        "name": "Customer Analytics",
        "slug": "customer-analytics",
        "category": "analytics",
        "description": "Understand customer behavior, segment your customer base, track retention and lifetime value, and identify at-risk customers.",
        "short_description": "Understand who your customers are and how they behave.",
        "features": ["Customer segmentation", "LTV analysis", "Retention analysis", "Behavior patterns", "At-risk customer identification", "Customer journey analysis"],
        "keywords": ["customer", "churn", "retention", "leaving", "loyal", "segment", "ltv", "lifetime value", "behavior", "satisfaction", "loyalty"],
    },
    {
        "name": "Financial Analytics",
        "slug": "financial-analytics",
        "category": "analytics",
        "description": "Analyze profitability, cost structures, margins, and financial performance across business units.",
        "short_description": "Analyze profitability, margins, and financial health.",
        "features": ["Profit margin analysis", "Cost breakdown", "Revenue mix analysis", "Financial KPIs", "Period comparisons", "Budget vs actuals"],
        "keywords": ["profit", "margin", "cost", "finance", "financial", "budget", "p&l", "profitability", "expense", "income"],
    },
    {
        "name": "Marketing Analytics",
        "slug": "marketing-analytics",
        "category": "analytics",
        "description": "Measure campaign performance, track conversion funnels, analyze channel ROI, and identify what marketing activities drive results.",
        "short_description": "Understand what marketing is actually working.",
        "features": ["Campaign performance", "Conversion funnel analysis", "Channel ROI", "Attribution modeling", "A/B test analysis", "Lead quality scoring"],
        "keywords": ["marketing", "campaign", "conversion", "funnel", "roi", "leads", "ads", "email", "attribution", "channel"],
    },
    # BI
    {
        "name": "Dashboard Development",
        "slug": "dashboard-development",
        "category": "bi",
        "description": "Custom interactive dashboards that visualize your most important metrics. Built for your team to monitor performance in real time.",
        "short_description": "Custom dashboards to monitor your key metrics.",
        "features": ["Custom KPI dashboards", "Interactive filters", "Real-time capable", "Multi-page reports", "Executive summaries", "Drill-down analysis"],
        "keywords": ["dashboard", "visualization", "chart", "graph", "kpi", "monitor", "track", "real-time", "live", "powerbi", "tableau", "looker"],
    },
    {
        "name": "KPI Automation & Reporting",
        "slug": "kpi-reporting",
        "category": "bi",
        "description": "Automate your business reporting. Set up scheduled KPI reports that are automatically delivered to your team.",
        "short_description": "Automated KPI reporting delivered to your team.",
        "features": ["Automated report generation", "Scheduled delivery", "PDF/Excel export", "Custom templates", "Alert thresholds", "Email distribution"],
        "keywords": ["report", "reporting", "kpi", "automated", "schedule", "weekly", "monthly", "pdf", "export", "template"],
    },
    # AI/ML
    {
        "name": "Predictive Analytics",
        "slug": "predictive-analytics",
        "category": "ai_ml",
        "description": "Use machine learning to predict future outcomes — customer behavior, product demand, revenue, and more — based on your historical data.",
        "short_description": "Predict future outcomes from your historical data.",
        "features": ["Machine learning modeling", "Prediction confidence scores", "Feature importance analysis", "Model validation", "Prediction API", "Explainable AI"],
        "keywords": ["predict", "prediction", "machine learning", "ml", "model", "future", "forecast", "probability", "regression", "classification"],
    },
    {
        "name": "Churn Prediction",
        "slug": "churn-prediction",
        "category": "ai_ml",
        "description": "Identify customers most likely to leave before they do. Build proactive retention strategies based on AI-driven churn scores.",
        "short_description": "Identify at-risk customers before they leave.",
        "features": ["Churn probability scoring", "Risk segmentation", "Key churn drivers", "Retention recommendations", "Early warning alerts", "Cohort analysis"],
        "keywords": ["churn", "leaving", "customer loss", "retention", "cancel", "unsubscribe", "at risk", "loyalty", "predict churn"],
    },
    {
        "name": "Anomaly Detection",
        "slug": "anomaly-detection",
        "category": "ai_ml",
        "description": "Automatically detect unusual patterns in your data — fraud, system failures, demand spikes, or quality issues.",
        "short_description": "Automatically detect unusual patterns in your data.",
        "features": ["Statistical anomaly detection", "Time-series anomalies", "Fraud pattern detection", "Real-time alerting", "Anomaly explanation", "Severity scoring"],
        "keywords": ["anomaly", "unusual", "outlier", "fraud", "spike", "detection", "irregular", "suspicious", "abnormal"],
    },
    # Forecasting
    {
        "name": "Sales Forecasting",
        "slug": "sales-forecasting",
        "category": "forecasting",
        "description": "Predict future sales volumes using time-series models trained on your historical sales data.",
        "short_description": "Predict your future sales with time-series forecasting.",
        "features": ["Time-series forecasting", "Seasonality analysis", "Trend decomposition", "Confidence intervals", "Scenario modeling", "Forecast vs actuals tracking"],
        "keywords": ["sales forecast", "predict sales", "next year", "next quarter", "future sales", "revenue forecast", "projection", "time series"],
    },
    {
        "name": "Demand Forecasting",
        "slug": "demand-forecasting",
        "category": "forecasting",
        "description": "Forecast product demand to optimize inventory, reduce stockouts, and improve supply chain efficiency.",
        "short_description": "Forecast product demand to optimize inventory.",
        "features": ["Product demand forecasting", "Inventory optimization", "Seasonal demand patterns", "SKU-level forecasts", "Supply chain recommendations"],
        "keywords": ["demand", "inventory", "stock", "supply chain", "product demand", "stockout", "warehouse", "forecast demand"],
    },
    # Enterprise
    {
        "name": "Complete Analytics Transformation",
        "slug": "enterprise-transformation",
        "category": "enterprise",
        "description": "End-to-end analytics transformation for your organization. From data infrastructure to dashboards, ML models, and a data-driven culture.",
        "short_description": "Full analytics transformation for your business.",
        "features": ["Data strategy consulting", "Infrastructure setup", "ETL pipeline development", "Dashboard suite", "ML model development", "Team training", "Ongoing support"],
        "keywords": ["enterprise", "transformation", "complete", "end-to-end", "full", "organization", "strategy", "infrastructure", "etl", "everything"],
    },
]


PACKAGES = {
    "data-cleaning": [
        {"name": "Starter", "price": 299.0, "currency": "USD", "description": "Up to 50,000 rows", "features": ["Data cleaning", "Quality report"], "limits": {"rows": 50000, "turnaround_days": 5}, "display_order": 1},
        {"name": "Business", "price": 699.0, "currency": "USD", "description": "Up to 500,000 rows", "features": ["Data cleaning", "Quality report", "Schema normalization", "Priority support"], "limits": {"rows": 500000, "turnaround_days": 3}, "display_order": 2},
        {"name": "Enterprise", "price": 1499.0, "currency": "USD", "description": "Unlimited rows", "features": ["Full data cleaning", "Quality report", "Schema normalization", "Priority support", "Dedicated analyst"], "limits": {"rows": -1, "turnaround_days": 2}, "display_order": 3},
    ],
    "eda": [
        {"name": "Starter", "price": 499.0, "currency": "USD", "description": "Single dataset EDA", "features": ["Statistical summary", "Correlation analysis", "EDA report"], "limits": {"datasets": 1, "turnaround_days": 5}, "display_order": 1},
        {"name": "Business", "price": 999.0, "currency": "USD", "description": "Up to 3 datasets", "features": ["Statistical summary", "Correlation analysis", "EDA report", "Interactive visuals", "Recommendations"], "limits": {"datasets": 3, "turnaround_days": 3}, "display_order": 2},
    ],
    "sales-analytics": [
        {"name": "Analysis Report", "price": 799.0, "currency": "USD", "description": "Full sales analytics report", "features": ["Revenue trend", "Product performance", "Regional analysis", "YoY comparisons", "Executive summary"], "limits": {"turnaround_days": 5}, "display_order": 1},
        {"name": "Analysis + Dashboard", "price": 1499.0, "currency": "USD", "description": "Report + interactive dashboard", "features": ["Full sales analytics", "Interactive dashboard", "Custom KPIs", "Drill-downs"], "limits": {"turnaround_days": 7}, "display_order": 2},
    ],
    "customer-analytics": [
        {"name": "Customer Insights", "price": 899.0, "currency": "USD", "description": "Full customer analytics report", "features": ["Segmentation", "LTV analysis", "Retention analysis", "Behavior patterns"], "limits": {"turnaround_days": 5}, "display_order": 1},
        {"name": "Customer Intelligence Suite", "price": 1799.0, "currency": "USD", "description": "Insights + predictions + dashboard", "features": ["Full analytics", "Churn prediction", "Dashboard", "Recommendations"], "limits": {"turnaround_days": 7}, "display_order": 2},
    ],
    "dashboard-development": [
        {"name": "Single Dashboard", "price": 1299.0, "currency": "USD", "description": "One custom dashboard", "features": ["Custom design", "Up to 10 KPIs", "Interactive filters", "PDF export"], "limits": {"pages": 1, "turnaround_days": 10}, "display_order": 1},
        {"name": "Dashboard Suite", "price": 2499.0, "currency": "USD", "description": "Multi-page dashboard suite", "features": ["Custom design", "Unlimited KPIs", "Multi-page", "Interactive filters", "Drill-downs", "Training session"], "limits": {"pages": 5, "turnaround_days": 14}, "display_order": 2},
    ],
    "predictive-analytics": [
        {"name": "Single Model", "price": 1999.0, "currency": "USD", "description": "One predictive model", "features": ["ML model", "Validation report", "Feature importance", "Prediction outputs"], "limits": {"models": 1, "turnaround_days": 10}, "display_order": 1},
        {"name": "Advanced Predictive Suite", "price": 3999.0, "currency": "USD", "description": "Multiple models + API", "features": ["Multiple models", "Model comparison", "Prediction API", "Ongoing support"], "limits": {"models": 3, "turnaround_days": 14}, "display_order": 2},
    ],
    "churn-prediction": [
        {"name": "Churn Model", "price": 1499.0, "currency": "USD", "description": "Churn prediction + scoring", "features": ["Churn model", "Risk scoring", "Driver analysis", "Retention recommendations"], "limits": {"turnaround_days": 10}, "display_order": 1},
    ],
    "sales-forecasting": [
        {"name": "Forecast Report", "price": 1299.0, "currency": "USD", "description": "12-month sales forecast", "features": ["Time-series model", "12-month forecast", "Confidence intervals", "Seasonal analysis"], "limits": {"months_forward": 12, "turnaround_days": 7}, "display_order": 1},
        {"name": "Forecast + Dashboard", "price": 2199.0, "currency": "USD", "description": "Forecast + tracking dashboard", "features": ["Full forecast", "Live tracking dashboard", "Forecast vs actuals"], "limits": {"months_forward": 24, "turnaround_days": 10}, "display_order": 2},
    ],
    "enterprise-transformation": [
        {"name": "Enterprise Package", "price": 9999.0, "currency": "USD", "description": "Full analytics transformation", "features": ["Strategy consulting", "Infrastructure", "ETL pipelines", "Dashboards", "ML models", "Training", "3 months support"], "limits": {"turnaround_days": 60}, "display_order": 1},
    ],
}


# ============================================================
# Knowledge Base
# ============================================================

KNOWLEDGE_ENTRIES = [
    {
        "title": "What is Clarivens?",
        "content": "Clarivens is a professional Data Analytics, Business Intelligence, AI/ML and Data Science company. We help businesses transform raw data into actionable insights, dashboards, predictive models, and automated reports. We specialize in working with businesses that have data but aren't sure how to use it effectively.",
        "category": "faq",
        "tags": ["about", "clarivens", "what is", "company", "services"],
    },
    {
        "title": "Clarivens Service Overview",
        "content": "Clarivens offers six service categories: (1) Data Services — cleaning, preparation, and quality assessment; (2) Analytics — exploratory data analysis, sales analytics, customer analytics, financial analytics, and marketing analytics; (3) Business Intelligence — dashboard development, KPI automation, and reporting; (4) AI/ML — predictive analytics, churn prediction, anomaly detection, and recommendation systems; (5) Forecasting — sales forecasting, demand forecasting, and revenue forecasting; (6) Enterprise — complete analytics transformation.",
        "category": "service",
        "tags": ["services", "overview", "categories", "what we offer"],
    },
    {
        "title": "How Clarivens Works — The Process",
        "content": "Our process: (1) Discovery call to understand your business problem and data; (2) Dataset review and quality assessment; (3) Proposal with recommended services and pricing; (4) Data upload and secure processing; (5) Analysis execution by our analytics engine; (6) Results review with AI-assisted insights; (7) Report delivery and Q&A. We sign NDAs on every project to protect your confidential data.",
        "category": "methodology",
        "tags": ["process", "how it works", "workflow", "methodology", "nda"],
    },
    {
        "title": "Data Privacy and Security",
        "content": "Your data is handled with the highest level of confidentiality. We sign NDAs on every project. Data is stored securely and never shared with third parties. Client datasets are strictly isolated — no data from one client is ever visible to another. We use UUID-based file storage, encrypted transmission, and role-based access controls.",
        "category": "faq",
        "tags": ["privacy", "security", "nda", "confidential", "data protection", "safe"],
    },
    {
        "title": "What datasets does Clarivens work with?",
        "content": "We work with CSV files, Excel files (xlsx, xls), and JSON datasets. We can handle datasets from small (a few hundred rows) to large (millions of rows). Common dataset types include sales transaction data, customer records, financial data, marketing campaign data, HR/employee data, inventory data, and web analytics data.",
        "category": "faq",
        "tags": ["dataset", "csv", "excel", "file format", "data types", "upload"],
    },
    {
        "title": "Clarivens Turnaround Times",
        "content": "Standard turnaround times vary by service: Data Cleaning (3-5 business days), Exploratory Data Analysis (3-5 days), Sales Analytics Report (5-7 days), Dashboard Development (7-14 days), Predictive Models (7-14 days), Sales Forecasting (5-10 days). Rush turnaround is available for Business and Enterprise packages.",
        "category": "service",
        "tags": ["turnaround", "timeline", "how long", "delivery", "time"],
    },
    {
        "title": "Sales Analytics — What We Deliver",
        "content": "Our Sales Analytics service analyzes your historical sales data to: identify what's driving revenue growth or decline, compare product performance, analyze regional and channel performance, track sales velocity and conversion rates, compare year-over-year and month-over-month performance, identify your top and bottom performers, and uncover seasonal patterns.",
        "category": "service",
        "tags": ["sales", "revenue", "analytics", "performance", "product", "region"],
    },
    {
        "title": "Churn Prediction — How It Works",
        "content": "Our churn prediction model analyzes customer behavior patterns to assign a churn probability score to each customer. We identify the top factors driving churn, segment customers by risk level, and provide actionable retention recommendations. The model is trained on your historical customer data and validated against held-out test periods.",
        "category": "methodology",
        "tags": ["churn", "customer", "prediction", "retention", "machine learning", "model"],
    },
    {
        "title": "Dashboard Development — What We Build",
        "content": "We build custom interactive dashboards using your data. Each dashboard includes: KPI tiles with trend indicators, interactive date filters and drill-downs, department or product breakdowns, comparison charts, and executive summary views. Dashboards are delivered as interactive reports or integrated into your existing BI tool.",
        "category": "service",
        "tags": ["dashboard", "visualization", "kpi", "interactive", "bi", "report"],
    },
    {
        "title": "Forecasting — Time Series Models",
        "content": "Our forecasting service uses time-series models (including trend decomposition, seasonality analysis, and statistical forecasting methods) trained on your historical data. We provide: forecasts with confidence intervals, seasonal pattern identification, trend analysis, and scenario modeling. Forecasts are validated against historical periods.",
        "category": "methodology",
        "tags": ["forecast", "time series", "prediction", "future", "seasonality", "trend"],
    },
    {
        "title": "Data Cleaning — What We Fix",
        "content": "Our data cleaning service addresses: duplicate records, missing values (filled using statistical methods appropriate to each column type), inconsistent formatting, wrong data types, outliers, encoding issues, and structural problems. You receive a cleaned dataset plus a quality report documenting every change made.",
        "category": "service",
        "tags": ["cleaning", "duplicates", "missing values", "quality", "formatting", "outliers"],
    },
    {
        "title": "Payment and Pricing — General",
        "content": "Pricing depends on the service, dataset size, and package selected. We offer Starter, Business, and Enterprise packages for most services. All pricing is transparent and agreed upfront. We accept payment before project start. Contact us for custom enterprise quotes. NDA is included in every engagement.",
        "category": "pricing",
        "tags": ["pricing", "payment", "cost", "how much", "packages", "quote"],
    },
]


# ============================================================
# Seed Functions
# ============================================================

def seed_services(db: Session) -> int:
    """Seeds service catalog and packages. Skips existing records. Returns count added."""
    added = 0
    for svc_data in SERVICES:
        existing = db.query(models.ServiceCatalog).filter(
            models.ServiceCatalog.slug == svc_data["slug"]
        ).first()
        if existing:
            continue

        svc = models.ServiceCatalog(**svc_data)
        db.add(svc)
        db.flush()

        # Add packages for this service
        for pkg_data in PACKAGES.get(svc_data["slug"], []):
            pkg = models.ServicePackage(service_id=svc.id, **pkg_data)
            db.add(pkg)

        added += 1

    db.commit()
    return added


def seed_knowledge(db: Session) -> int:
    """Seeds knowledge base. Skips existing records by title. Returns count added."""
    added = 0
    for entry in KNOWLEDGE_ENTRIES:
        existing = db.query(models.AgentKnowledge).filter(
            models.AgentKnowledge.title == entry["title"]
        ).first()
        if existing:
            continue

        kb = models.AgentKnowledge(**entry, kb_version="1.0", is_active=True)
        db.add(kb)
        added += 1

    db.commit()
    return added


def seed_agent_version(db: Session) -> None:
    """Seeds the initial agent version record."""
    existing = db.query(models.AgentVersion).filter(
        models.AgentVersion.version == settings.agent_version
    ).first()
    if existing:
        return

    version = models.AgentVersion(
        version=settings.agent_version,
        primary_model=settings.agent_primary_model,
        fast_model=settings.agent_fast_model,
        prompt_version="1.0",
        knowledge_version=settings.agent_knowledge_version,
        tool_version="1.0",
        policy_version="1.0",
        status="production",
        release_notes="Initial Clarivens AI release.",
    )
    db.add(version)
    db.commit()


def seed_all() -> dict:
    """
    Seeds all initial data. Safe to call multiple times (idempotent).
    """
    db = SessionLocal()
    try:
        services_added = seed_services(db)
        knowledge_added = seed_knowledge(db)
        seed_agent_version(db)
        logger.info(
            "[Seed] Services added: %d, Knowledge chunks added: %d",
            services_added, knowledge_added,
        )
        return {
            "services_added": services_added,
            "knowledge_added": knowledge_added,
            "status": "success",
        }
    except Exception as e:
        db.rollback()
        logger.error("[Seed] Seeding failed: %s", type(e).__name__)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    result = seed_all()
    print(result)
    sys.exit(0 if result["status"] == "success" else 1)
