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
- [x] Outbound child flow generated (10 actions) - AcuityOrder XML construction, Basic Auth, ack parsing, response to router
- [x] Inbound standalone flow generated (14 actions) - HTTP trigger, immediate ack, XML parsing, message type detection, document extraction
- [x] Both flows use Compose placeholders for API calls until sandbox is configured
- [x] 6 environment variables defined (Base URL, Username, Password, SenderID, RecipientID, ProductCode)

---

## In Progress

- Sandbox credential configuration with ClearValue Consulting
  - Blocker: None - ClearValue working with us today
  - Next step: Confirm SenderID, RecipientID, product codes, and sandbox endpoint URL
- AlternativeProductsRouter integration - adding Acuity routing condition

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
| April 17, 2026 | Sal | Feasibility analysis, project setup, flow generation | Analyzed Acuity framework, created feasibility doc, set up project repo/mirror/GitHub, generated both PA flows (outbound child + inbound standalone) with placeholder Compose actions |

---

## Test Results

| Test | Status | Date |
|------|--------|------|
| Sandbox order placement | Pending | - |
| Sandbox report receipt | Pending | - |
| End-to-end with AlternativeProductsRouter | Pending | - |
