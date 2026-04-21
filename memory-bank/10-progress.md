# AcuityIntegration - Progress

## Current Status: In Progress

**Owner:** Sal/Brett  
**Last Updated:** April 21, 2026

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

- **Waiting on ClearValue follow-ups** (blocks live sandbox test):
  - Full POST path under `https://clients.valorvaluations.com`
  - PDR ProductCode
  - Correct XML placement for Master Client ID (56135) and Branch ID (1055)
  - IP allowlist requirement + our PA outbound IPs if yes
  - Duplicate PartnerReferenceNumber behavior
  - Inbound delivery retry policy on their side
  - Fast-complete sandbox product code (to demo full round-trip)

---

## Session Log

| Date | Who | Focus | Outcome |
|------|-----|-------|---------|
| April 17, 2026 | Sal | Feasibility analysis, project setup, flow generation | Analyzed Acuity framework, created feasibility doc, set up project repo/mirror/GitHub, generated both PA flows (outbound child + inbound standalone) with placeholder Compose actions |
| April 21, 2026 | Sal | Pre-call live-test tooling for ClearValue meeting | Built stdlib-only Python harness (`tools/acuity_sandbox_test.py` — place-order/dry-run/ping modes), Postman collection + environment (`tools/acuity_sandbox.postman_collection.json`, `acuity_sandbox.postman_environment.json`), interactive step-by-step assistant (`tools/acuity_live_call.py`), and `tools/CALL_CHECKLIST.md`. Dry-run verified XML generation. pip blocked by corp SSL → stdlib-only chosen deliberately. |
| April 21, 2026 | Sal | ClearValue live call — partial intake, live test deferred | **Captured:** vendor brand is Valor Valuations, sandbox host `https://clients.valorvaluations.com` (full POST path still TBD), Master Client ID 56135, Branch ID 1055, PDC = ProductCode `9`, credentials + RecipientID captured to gitignored `CALL_CHECKLIST.md`. **Routing logic:** LPA or CaseFile presence on the JaroDesk order determines PDR vs PDC. **Outstanding (ClearValue owes answers):** PDR product code, full sandbox POST path, IP allowlist, TLS version, mTLS, rate limits, duplicate PartnerReferenceNumber behavior, inbound retry policy, fast-complete sandbox code. **Not done on call:** live place-order test (step 5) and inbound webhook round-trip (step 6) — both punted until ClearValue confirms missing pieces. Added `tools/CALL_CHECKLIST.md` to `.gitignore` to keep captured creds out of GitHub. Updated `context.md` with Valor branding, host, master client/branch IDs, and PDR/PDC mapping rule. |

---

## Test Results

| Test | Status | Date |
|------|--------|------|
| Sandbox order placement | Pending | - |
| Sandbox report receipt | Pending | - |
| End-to-end with AlternativeProductsRouter | Pending | - |
