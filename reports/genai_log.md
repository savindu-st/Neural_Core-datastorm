# GenAI Transparency Log

**Project:** QuadNova Potential-Based Budget Allocation Engine  
**Report Date:** May 2026  
**Purpose:** Document honest, auditable record of GenAI usage in project

---

## Executive Summary

This log records how GenAI and LLMs were used in the QuadNova project. The project maintains strong rule-based explanations as primary deliverable, with optional GenAI enhancement layer for polishing outlet business explanations.

**Key Principle:** All GenAI outputs are verified against underlying model drivers. No GenAI outputs are deployed without human validation.

---

## GenAI Usage Entry Log

### Entry 1: Outlet Business Explanation Generation

**Date:** May 15, 2026  
**Component:** `src/xai/outlet_reasoning.py` + `src/xai/genai_explainer.py`

| Field | Details |
|-------|---------|
| **Purpose** | Generate business-friendly 4-sentence outlet explanations from structured model drivers |
| **Why GenAI?** | Rule-based explanations are clinical; GenAI adds business polish and readability |
| **Input Data** | <ul><li>Outlet ID and location</li><li>Predicted potential (liters/month)</li><li>Current average sales</li><li>Confidence score (0-100%)</li><li>Top 3 positive drivers (extracted from model)</li><li>Top 3 negative drivers (extracted from model)</li><li>Outlet segment classification</li><li>Recommended action category</li></ul> |
| **Prompt Sent** | "You are a business analyst explaining outlet sales potential to a beverage company executive. Based on these outlet facts, write a 4-sentence business explanation: [structured data]. Sentences: 1) Why this outlet has this potential. 2) Key opportunity drivers. 3) Key constraints. 4) Specific sales team action." |
| **Output Type** | 4-sentence narrative explanation |

**Human Validation Process:**

✅ **Verification Step 1: Driver Accuracy**
- Read GenAI explanation
- Cross-check if mentioned drivers appear in model output
- Flag if explanation invents drivers not in model
- **Result:** ACCEPTED (explanations accurately reflect model drivers)

✅ **Verification Step 2: Causal Claims Audit**
- Check if explanation claims causal relationships without support
- Example to reject: "Competitor outlets are causing low sales" (not supported by model)
- Example to accept: "High competition in area limits growth potential" (supported by competition feature)
- **Result:** ACCEPTED (no unsupported causal claims)

✅ **Verification Step 3: Tone & Audience Appropriateness**
- Verify explanations use business language, not technical model terminology
- Check for executive-appropriate level of detail (not too granular)
- Ensure action is specific and salesforce-implementable
- **Result:** ACCEPTED (tone is professional and actionable)

**Accepted Elements:**
- Clear opportunity size framing ("potential gap of X liters")
- Driver-based explanation (cites competition, demographics, accessibility)
- Actionable recommendation ("increase trade spend by X%")
- Confidence-qualified language ("model predicts with 75% confidence")

**Rejected Elements:**
- Generic advice not specific to outlet ("build relationships" without context)
- Causal claims ("low competition causes high sales" — reversed causality)
- Unsupported benchmarks ("similar outlets in market average 500L" — no source)
- Technical jargon ("latent variable regression," "censored regression")

**Final Decision:** 
✅ **APPROVED FOR DEPLOYMENT**
- Rule-based explanations remain primary (always available)
- GenAI outputs used as optional enhancement layer
- Streamlit app clearly labels where explanations come from
- All explanations undergo human review before app display

---

## GenAI Impact Assessment

### Strengths

✅ **Readability:** GenAI summaries are more engaging than raw model outputs  
✅ **Stakeholder Communication:** Executive-level language improves adoption  
✅ **Time-Saving:** Automated explanation generation vs. manual writing  
✅ **Consistency:** LLM maintains consistent tone across 2000+ outlet explanations  

### Limitations & Mitigations

⚠️ **Hallucination Risk:** LLM might invent supporting details
- Mitigation: Rule-based driver extraction prevents hallucination (drivers are sourced from model, not generated)

⚠️ **API Dependency:** GenAI output quality varies across providers/models
- Mitigation: Rule-based fallback ensures functionality without GenAI

⚠️ **Latency:** GenAI API calls add processing time
- Mitigation: Batch process explanations offline; serve pre-generated text in app

---

## Deployment Transparency

### For End Users

**In Streamlit App:**

```
🤖 [This explanation was enhanced by GenAI]
📋 Base explanation (generated from model drivers)
🔧 [View raw model drivers]
```

Users can toggle between GenAI-enhanced and rule-based versions.

### For Stakeholders

**Question:** "How much did AI generate vs. human analysis?"

**Answer:**
- Model development: 100% human (statistics, feature engineering, validation)
- Outlet explanations: 95% rule-based (driver extraction), 5% GenAI (narrative polish)
- Budget allocation: 100% algorithmic (optimization solver)
- Data quality report: 80% factual (data QA rules), 20% GenAI (narrative writing)

**Bottom Line:** Model decisions are 100% explainable and don't depend on GenAI. GenAI is used only for communication polish, never for core business logic.

---

## Governance & Validation Framework

### Before Deployment: 3-Person Review

1. **Data Science Lead:** Verifies GenAI output matches underlying model/data
2. **Product Manager:** Checks for business appropriateness and tone
3. **Compliance Officer:** Audits for risk, bias, unsupported claims

### During Deployment: Monitoring

- Track app usage (which users view GenAI vs. rule-based explanations)
- Collect feedback ("Was this explanation helpful?")
- Monitor for user complaints about accuracy

### Post-Deployment: Continuous Audit

- Monthly review of 50 random GenAI explanations
- Spot-check for hallucinations or misalignments with model
- Quarterly stakeholder survey on explanation quality

---

## Compliance & Risk Checklist

✅ **Data Privacy:** No customer PII included in GenAI prompts  
✅ **Bias Audit:** GenAI outputs reviewed for geographic or demographic bias  
✅ **Intellectual Property:** No proprietary methods disclosed in prompts  
✅ **Audit Trail:** Full logging of GenAI prompts and outputs  
✅ **Graceful Failure:** System works without GenAI (rule-based fallback)  
✅ **Transparency:** Users informed when GenAI is used  
✅ **Accuracy Standards:** All GenAI outputs validated before deployment  

---

## Conclusion

GenAI was used judiciously in QuadNova to enhance communication and narrative quality, not to replace core model development or business logic. Every GenAI output was:

1. ✅ Grounded in structured model data (not hallucinated)
2. ✅ Validated by human experts before deployment
3. ✅ Supported by rule-based fallback if API unavailable
4. ✅ Transparently labeled in user-facing systems

The project successfully demonstrates that GenAI can add value to business applications when used with appropriate guardrails and transparency.

---

**Report prepared by:** QuadNova Data Science Team  
**Approval:** Project Lead, Compliance Officer  
**Classification:** Business & Technology / Risk Management
