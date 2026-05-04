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

**Resolved May 4, 2026 (ClearValue follow-up answers):**
- ✅ Outbound POST URL: `https://clients.valorvaluations.com/adapters/Integration/Acuity`
- ✅ Inbound auth: none — Valor does not authenticate itself when posting to us. Mitigation: validate `SenderID` element in our HTTP-trigger flow.
- ✅ IP allowlist: not required.
- ✅ TLS: 1.2 or 1.3 supported.
- ✅ Rate limits: none, but sequential delivery required (updates applied in receive order).
- ✅ Auth failure: HTTP 401.
- ✅ Schema validation failure: `<Error><ErrorCode>0500</ErrorCode><ErrorMessage>...</ErrorMessage></Error>` at the top level (NOT wrapped in `<AcuityAcknowledgement>`). Confirmed May 4 with `'fakepropertytype' is not a valid value for AcuityPropertyType` sample.
- ✅ Outbound→Valor retry policy: on us; Valor→us retry: ~3 connection attempts, then dropped.
- ✅ Sandbox cleanup: not applicable.
- ✅ AcuityOrderUpdate exists for partial updates (vs full AcuityOrder for placement).
- ✅ Inbound URL slot: Valor supports a single outbound URL — re-registering after a PA solution import requires updating Valor too.
- ✅ Generic RecipientID "VALOR" is acceptable when sending us → Valor.

**Still outstanding (blocks Tier 1 ship):**
- ✅ **PDR ProductCode** — RESOLVED 2026-05-04 (Sal follow-up): there is no separate PDR ProductCode. ProductCode is always `9` for both PDR and PDC. Differentiator is the LPA Key (`FreddieMacLPAKey`) or CaseFile ID (`FannieMaeCaseFileID`) carried in `<ForeignOrderIdentifier>` on the AcuityOrder XML. Empty = PDC behavior; populated = PDR behavior. This fits cleanly into the existing 6.4.0 schema (no custom extension). Source of LPA Key / CaseFile ID on JaroDesk-side TBD — confirm during stakeholder review.
- ⚠️ **3003 "client profile cannot be determined"** — first live POST May 4 returned this. Awaiting Valor's response on whether (a) `OPTEON` is the wrong SenderID value, (b) MasterClientID 56135 / BranchID 1055 need to be on the wire and where, or (c) account-side provisioning issue. Schema-validation is now passing — this is a business-layer block, not a wire-format block.
- ⚠️ **MasterClientID (56135) and BranchID (1055) XML placement** — `ForeignOrderIdentifier` is now ruled out (it's reserved for GSE/FHA/Fannie/Freddie loan-tracking IDs per the enum, and its primary use is now confirmed to be the PDR/PDC differentiator). Remaining candidates: `OperationalTag1/2`, `CostCenter`, `InvestorCode`, `BatchName` — or possibly nothing at all if Basic Auth alone identifies the account on Valor's side. Bundled into the consolidated Valor email already sent.
- ⚠️ **Duplicate PartnerReferenceNumber behavior** — still unanswered. Affects retry semantics on connection-level failures.
- ⚠️ **Fast-complete sandbox code** — not provided; needed to demo a full round-trip without waiting for a real inspector.

**Code-level work blocked on PDR code only:**
- Outbound child placeholder POST → real `HTTP_-_Acuity_Order` (same XML body, real auth, retryPolicy=none): can build today using `https://clients.valorvaluations.com/adapters/Integration/Acuity`. Will work for PDC orders immediately.
- Inbound flow JaroDesk upload (placeholder → real 3-step Uppy.js upload + tag + deliver): can build today, no ClearValue dependency.
- Outbound error parser widening (current code only reads `AcuityAcknowledgement.Error.*`; needs to also read top-level `Error.*` per the May 4 sample) — apply the same multi-shape coalesce + `string(...)` fallback pattern from the Magellan AVM Child v33 fix.
- SenderID validation gate on inbound (one Condition; reject anything where `SenderID != "VALOR"`) — closes the open-HTTP-trigger gap.

---

## Session Log

| Date | Who | Focus | Outcome |
|------|-----|-------|---------|
| April 17, 2026 | Sal | Feasibility analysis, project setup, flow generation | Analyzed Acuity framework, created feasibility doc, set up project repo/mirror/GitHub, generated both PA flows (outbound child + inbound standalone) with placeholder Compose actions |
| April 21, 2026 | Sal | Pre-call live-test tooling for ClearValue meeting | Built stdlib-only Python harness (`tools/acuity_sandbox_test.py` — place-order/dry-run/ping modes), Postman collection + environment (`tools/acuity_sandbox.postman_collection.json`, `acuity_sandbox.postman_environment.json`), interactive step-by-step assistant (`tools/acuity_live_call.py`), and `tools/CALL_CHECKLIST.md`. Dry-run verified XML generation. pip blocked by corp SSL → stdlib-only chosen deliberately. |
| May 4, 2026 | Sal | ClearValue/Valor follow-up answers received | Most outstanding integration questions resolved by Valor (see Blockers section above). Tier 1 (functional MVP) is now unblocked for **PDC orders only**; **PDR ProductCode is still TBD** so PDR routing must wait. Newly captured: outbound POST URL `https://clients.valorvaluations.com/adapters/Integration/Acuity`; Valor does not authenticate when posting to us (mitigate via SenderID validation, not IP allowlist); error response on schema failure is a top-level `<Error>` element (NOT wrapped in `AcuityAcknowledgement`) — implication: the outbound child's response parser must probe both shapes via coalesce, mirroring the Magellan AVM Child v33 multi-shape pattern. Sequential delivery required (Valor applies updates in receive order). AcuityOrderUpdate exists for partial-update flows. Valor retries inbound delivery to us 3x. |
| April 21, 2026 | Sal | ClearValue live call — partial intake, live test deferred | **Captured:** vendor brand is Valor Valuations, sandbox host `https://clients.valorvaluations.com` (full POST path still TBD), Master Client ID 56135, Branch ID 1055, PDC = ProductCode `9`, credentials + RecipientID captured to gitignored `CALL_CHECKLIST.md`. **Routing logic:** LPA or CaseFile presence on the JaroDesk order determines PDR vs PDC. **Outstanding (ClearValue owes answers):** PDR product code, full sandbox POST path, IP allowlist, TLS version, mTLS, rate limits, duplicate PartnerReferenceNumber behavior, inbound retry policy, fast-complete sandbox code. **Not done on call:** live place-order test (step 5) and inbound webhook round-trip (step 6) — both punted until ClearValue confirms missing pieces. Added `tools/CALL_CHECKLIST.md` to `.gitignore` to keep captured creds out of GitHub. Updated `context.md` with Valor branding, host, master client/branch IDs, and PDR/PDC mapping rule. |

---

## Test Results

| Test | Status | Date |
|------|--------|------|
| Sandbox order placement | Pending | - |
| Sandbox report receipt | Pending | - |
| End-to-end with AlternativeProductsRouter | Pending | - |
