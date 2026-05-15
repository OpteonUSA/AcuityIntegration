# AcuityIntegration - Progress

## Current Status: In Progress

**Owner:** Sal Vacanti
**Last Updated:** May 15, 2026

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

- **Bidirectional connectivity wire-proven** (May 7 inbound + May 4 outbound postman). One `AcuityReport` has been received and captured at `responses/response-report.md` with full HTTP trigger envelope, raw XML, our ack, and the post-parse JSON shape.
- **All May 14 meeting blockers resolved** — see "Resolved" section below; nothing outstanding from Valor's side except the canonical inbound message-type inventory (Jeanette committed to send).
- **Generator v36 ready to import** (Acuity Outbound Path B refactor + inbound ack SenderID fix). v37 work queued: router-side wiring of GSE identifiers from JaroDesk incremental endpoint.
- Code-level work remaining (sequenced):
  1. **(v36 import)** Import `AlternativeProductsRouter_1_0_0_36_unmanaged.zip` to PA DEV; verify both Acuity flows turn on cleanly.
  2. **(v37 router refactor)** Add `HTTP_-_Get_Order_Incremental` action calling `GET /v1/order/{id}/incremental`; parse `body.details.details.lpaKey` + `duCaseFileId`; populate router variables; pass to Acuity Outbound child in PDR/PDC cases.
  3. **(v37)** Add SenderID validation Condition to inbound flow (reject `SenderID != "OPTEONAMC"`) — closes the open-HTTP-trigger gap since Valor doesn't authenticate when posting to us.
  4. **(v37)** Wire the real outbound POST in Acuity Outbound Child (replace placeholder Compose; `retryPolicy=none`).
  5. **(v37)** Widen outbound error parser via multi-shape coalesce + `string(...)` fallback (Magellan v33 pattern) to surface top-level `<Error>` AND `<AcuityAcknowledgement><Error>` shapes. Add explicit handling for the **`3019` duplicate `PartnerReferenceNumber`** code — write JaroDesk-visible note when fired.
  6. **(v37)** Build real JaroDesk 3-step Uppy.js upload (getSignedURL → S3 PUT → register) for `AcuityReport` only; other message types are status-only. Use the May 7 `AcuityReport` at `responses/response-report.md` as the test fixture.
  7. **(v37)** Idempotency table (Dataverse, keyed on `PartnerReferenceNumber`) to track "sent / acked" before retrying on transient 5xx — duplicate-PRN rejection in PROD makes blind retries unsafe.
  8. **(beyond v37)** Build out Case logic in `Acuity Inbound - Receive Report` for the full message-type catalog (awaiting Jeanette's inventory; 8 milestone bodies from May 7 already in PA run history as starting material).

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

**All previously-open blockers resolved as of 2026-05-14 (Acuity meeting with Jeanette / Valor).** No remaining items blocking Tier 1 ship for either PDR or PDC.

**Resolved May 14, 2026 (Acuity meeting):**
- ✅ **MasterClientID / BranchID XML placement** — confirmed NOT on the wire. Basic Auth + SenderID alone is the identity binding. Master/Branch are Valor-side account record fields only.
- ✅ **Duplicate `PartnerReferenceNumber` in PROD** — Valor returns error code `3019`. Sandbox accepting duplicates was non-representative; PROD is stricter. Our handling: write JaroDesk-visible duplicate-detection note + design retry path around an idempotency table.
- ✅ **"Sandbox" vs PROD distinction is moot** — there is no separate sandbox environment. Both Opteon and Valor operate in PROD on both sides. Same endpoint + creds + account IDs across our DEV/UAT/PROD Power Automate environments. Every test order is a real Valor order.
- ✅ **Fast-complete sandbox code** — does not exist. Valor cannot test-submit to Fannie/Freddie GSE APIs from anywhere. Full end-to-end demos require a real inspector (PDC) or are gated on the real GSE submission step (PDR).
- ✅ **Enum mapping** for `PropertyType`, `LoanType`, `LoanPurpose`, `ContactType` — passes 1:1 from JaroDesk to Valor; no transformation layer needed.
- ✅ **`<ForeignOrderIdentifier>` shape** — mutually exclusive, GSE-program-paired:
  - ACE + PDR → `Type="FreddieMacLPAKey"`
  - ValueAcceptance + PDC → `Type="FannieMaeCaseFileID"`
- ✅ **`<SalesPrice>`** — Valor confirmed it is NOT consumed. Drop from outbound payload.
- ✅ **JaroDesk Entry contact** → maps to Valor `<PropertyAccess>` element.
- ✅ **JaroDesk source for GSE identifiers** — `GET /v1/order/{id}/incremental` returns `body.details.details.lpaKey` and `body.details.details.duCaseFileId`. v37 router work uses this endpoint.
- ✅ **Vendor profile setup in JaroDesk** — `orders@valorvaluations.com` for PROD; `jeanette@valorvaluations.com` for testing. Provisional plan: add Jeanette to the live vendor account so test orders ride real JaroDesk routing.

**Awaiting from Valor (low-priority, post-meeting deliverable):**
- Jeanette will send the complete inbound message-type inventory so we can size the Case-build scope before relying solely on the 8 milestone messages captured May 7.

**Bug surfaced + fixed in v36 (2026-05-15):**
- The inbound `Acuity Inbound - Receive Report` flow's ack to Valor had `<SenderID>OPTEON</SenderID>` (should always be `OPTEONAMC`). Hardcoded literal in the generator; fixed at line 2912. RecipientID kept as `ACUITY` pending more captured examples before changing.

---

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
- ✅ **3003 RESOLVED** (Valor reply + retest 2026-05-04): correct SenderID is `OPTEONAMC`. Postman retest with `senderId=OPTEONAMC` returned `Success=true` + `ProviderReferenceNumber=1098324.1`. **Tier 1 outbound (AcuityOrder placement) is now wire-validated end-to-end against Valor's sandbox.** Sample at `responses/success_001_first_accepted_order.xml`.
- ✅ **MasterClientID 56135 / BranchID 1055** — confirmed NOT needed in the XML. They're Valor-side account identifiers tied to Basic Auth + SenderID combination, exactly as originally hypothesized before being challenged by the 3003. No schema-extension or custom-element work needed.
- ✅ **Duplicate PartnerReferenceNumber behavior** (sandbox): NOT rejected — Valor accepted the same `OPTEON-TEST-POSTMAN-001` that previously produced 3003. Open question for PROD behavior.
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
| May 7, 2026 | Sal | Bidirectional sandbox connectivity confirmed | Valor confirmed receipt of the new order request through Postman. Acuity Inbound webhook URL was provided to Valor and Valor delivered **8 distinct milestone messages** to the `Acuity Inbound - Receive Report` flow in Power Automate. Both directions of the Acuity protocol are now wire-proven against Valor's sandbox. Session was status-confirmation only — no code changes; queued the next-session punch list (8-run audit, SenderID gate, real outbound POST + error parser widening, real JaroDesk Uppy upload for `AcuityReport`, `cre4a_apikey` fix). |
| May 14, 2026 | Sal | Acuity meeting with Jeanette (Valor) | All previously-open blockers resolved (see Blockers section). Net protocol clarifications: Master/Branch IDs stay off the wire; duplicate PRN in PROD returns error 3019; no separate sandbox environment exists; PropertyType/LoanType/LoanPurpose/ContactType enums pass 1:1; ForeignOrderIdentifier is mutually exclusive (ACE+PDR→FreddieMacLPAKey, ValueAcceptance+PDC→FannieMaeCaseFileID); SalesPrice is not consumed; JaroDesk Entry contact maps to PropertyAccess; vendor profile setup planned with Jeanette on the live vendor account for test routing. Live notes captured at `_meeting_notes/2026-05-14_acuity_prep.md`. |
| May 15, 2026 | Sal | First real AcuityReport received; v36 generator refactor | Captured first end-to-end `AcuityReport` from Valor (sample at `responses/response-report.md` — includes HTTP envelope, raw XML, our ack, and post-parse JSON shape; one AppraisalReport PDF inline as base64). Surfaced bug: inbound ack sent `<SenderID>OPTEON</SenderID>` instead of always-`OPTEONAMC`. Generator refactor v36: (a) inbound ack SenderID fixed to OPTEONAMC literal; (b) Acuity Outbound Path B refactor — dropped pipe-split of `cre4a_apikey`, SenderID now reads it directly, RecipientID/ProductCode hardcoded (`VALOR`/`9`) since they're stable constants per Valor 2026-05-14; (c) added `ACUITY_OUT_CHILD_INPUTS` trigger schema with `FreddieMacLPAKey` + `FannieMaeCaseFileID` (both optional); (d) added `Compose_-_ForeignOrderIdentifier_XML` with conditional emission. Output: `AlternativeProductsRouter_1_0_0_36_unmanaged.zip`. Router-side wiring of the GSE identifiers from `GET /v1/order/{id}/incremental` queued for v37. context.md updated with all meeting outcomes + new error code 3019. |

---

## Test Results

| Test | Status | Date |
|------|--------|------|
| Sandbox order placement | Pending | - |
| Sandbox report receipt | Pending | - |
| End-to-end with AlternativeProductsRouter | Pending | - |
