# AcuityIntegration - Progress

## Current Status: In Progress

**Owner:** Sal/Brett  
**Last Updated:** April 17, 2026

---

## Strategic KPI Summary

**Focus:** TAT  
**Touches Removed:** TBD per instance | TBD monthly | TBD annually  
**FTE Hours Saved:** TBD per instance | TBD monthly | TBD annually  

*See `kpi.md` for detailed metrics and calculations.*

---

## Completed

- [x] Feasibility analysis - reviewed Acuity framework spec, mapped to existing architecture
- [x] Project setup - local repo, GitHub repo, SharePoint mirror, DASHBOARD entry

---

## In Progress

- Sandbox credential configuration with ClearValue Consulting
  - Blocker: None - ClearValue working with us today
  - Next step: Confirm SenderID, RecipientID, product codes, and sandbox endpoint URL

---

## Upcoming

1. Document Acuity sandbox endpoint details in `_micro_integrations/acuity/`
2. Build MVP outbound flow (AcuityOrder XML construction + POST)
3. Build MVP inbound flow (HTTP trigger + AcuityReport parsing)
4. Test end-to-end with sandbox
5. Wire up as child flow in AlternativeProductsRouter
6. Add order mapping storage (SharePoint list or Dataverse table)

---

## Blockers

- None currently

---

## Session Log

| Date | Who | Focus | Outcome |
|------|-----|-------|---------|
| April 17, 2026 | Sal | Feasibility analysis & project setup | Analyzed Acuity framework, created feasibility doc, set up project repo/mirror/GitHub |

---

## Test Results

| Test | Status | Date |
|------|--------|------|
| Sandbox order placement | Pending | - |
| Sandbox report receipt | Pending | - |
| End-to-end with AlternativeProductsRouter | Pending | - |
