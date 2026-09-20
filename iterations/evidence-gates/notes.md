# Iteration: 0.1.0 development baseline → 0.2.0

Baseline: `2d38d36`. Issue source: independent read-only code review and offline reproductions. Scope: four runtime defects, stricter validation binding, and consumer documentation.

## Evidence and changes

- A scope change could reuse old judgments. Added review scope fingerprints, coverage protocol fingerprints, current planned-query completion checks and non-destructive preparation templates.
- Null/non-string evidence could pass. Added real string-type and nonblank checks for evidence, locator, rationale, claim text and related fields.
- A bad later page could lose good earlier records. Added partial-result preservation for S2/OpenAlex, plus arXiv response-count checks.
- Older success could mask a failed refresh. Resume now considers the latest attempt for the same query fingerprint.
- Independent skill use encountered the undocumented HTTP(S)-only source URL rule. The evidence-source convention is now explicit, including the limits of local-file provenance.

## Validation

29 deterministic tests passed before release preparation. The independent reviewer reran 7 targeted cases and confirmed that the four original issues no longer reproduced. Network smoke separately exercised S2 relevance/bulk/references, arXiv and OpenAlex. An independent offline consumer completed the three-candidate exercise; strict correctly blocked incomplete evidence and coverage.

## Compatibility

Release 0.2.0 deliberately tightens the audit contract. The additive JSON structure remains schema_version 1, but 0.1.x reviews/coverage without fingerprints cannot pass the new gates. Run `prepare`, re-evaluate affected records/coverage, then update them from evidence. Do not mechanically add hashes to certify old judgments. Old runs and reports remain unchanged unless explicitly migrated.

## Limits

No real domain survey, research-quality benchmark, independent human annotation, or field-level recall measurement was completed. Structural gates do not establish semantic support or exhaustive retrieval. This release changes operational reliability, not a proven scientific method-effectiveness metric.
