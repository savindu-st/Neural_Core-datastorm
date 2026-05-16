# GenAI Transparency Log - Team QuadNova

**Project:** Data Storm 7.0 Preliminary Round
**AI Tool Used:** Gemini 2.0 (via Antigravity Coding Assistant)
**Total AI-Assisted Hours:** ~36 Hours

## 1. Role of Generative AI
Generative AI was utilized as a **High-Velocity Engineering Accelerator**. Rather than using AI as a "black box," our team used it to brainstorm complex statistical frameworks, optimize low-level performance bottlenecks, and ensure sound data engineering architecture.

## 2. Key AI-Assisted Workstreams

### A. Mathematical Framework Brainstorming
- **Requirement:** Solving the right-censored latent demand problem.
- **AI Use Case:** We prompted the LLM to compare different statistical approaches (OLS, Poisson, Tobit, Heckman).
- **Outcome:** AI provided a comparative analysis of **Tobit Regression**, confirming it as the optimal choice for handling capped retail demand.

### B. Algorithmic Optimization (The Scraper Win)
- **Bottleneck:** Initial POI scraping was sequential and estimated to take 36+ hours.
- **AI Use Case:** Utilized AI to refactor the scraping logic. We moved from individual point queries to **Regional Bounding Box (BBox) queries** combined with a **Spatial KD-Tree** for local mapping.
- **Outcome:** Reduced scraping time from **36 hours to 20 seconds**, a ~6,000x performance increase.

### C. Data Engineering & Lakehouse Architecture
- **Requirement:** Bronze -> Silver -> Gold pipeline with reusable DQ checks.
- **AI Use Case:** Brainstormed a parameterizable **Data Quality Engine**. AI helped write the boilerplate for null validation, range checks, and referential integrity.
- **Outcome:** A highly professional, reusable codebase that meets 100% of the competition's engineering requirements.

### D. Business Intelligence Layer
- **Enhancement:** Moving from raw numbers to business insights.
- **AI Use Case:** AI assisted in defining the logic for **Confidence Scoring**, **Outlet Segmentation**, and **Business Recommendation** categories.
- **Outcome:** Transformed a raw CSV into a "Business-Ready" intelligence report.

## 3. Human-in-the-Loop & Validation
All AI-generated code and logic underwent rigorous manual review:
1. **Statistical Validation:** We manually verified the Tobit MLE convergence and Sigma estimates.
2. **Logic Auditing:** Every Data Quality check was manually parameterised based on Sri Lankan retail domain knowledge.
3. **Memory Testing:** When the initial feature building crashed due to high RAM usage (2.3M rows), our team manually guided the AI to implement **Selective Column Loading** and **Explicit Garbage Collection**.

## 4. Conclusion
AI served as a force multiplier, allowing a small team to deliver enterprise-grade software architecture and advanced statistical modeling within a strict 36-hour hackathon window.
