# OneHR Recruitment — Bounded Runtime Repair Attempt 2/2

TASK: `ONEHR-RECRUITMENT-DIRECT-FULL-RUNTIME-20260903`  
ATTEMPT: `2 / 2`  
TARGET_ADDON: `onehr_recruitment`  
TARGET_PLATFORM: Odoo 19 Community Edition (`19.0.20251217`)  
WRITE_SCOPE: `onehr_recruitment` only  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

## Concrete runtime evidence

Activation reached Python model-class setup and failed in:

`onehr_recruitment/models/interview.py`

Model:

`onehr.interview.score`

Field:

`scorecard_values = fields.Properties(...)`

Observed Odoo 19 failure:

`AssertionError: Error calling __set_name__ on 'Properties' instance 'scorecard_values' in 'OneHRInterviewScore'`

The source used:

`definition="session_id.template_id.scorecard_definition"`

Odoo 19 `fields.Properties` requires the `definition` string to contain exactly one dot:
`<definition_record_field>.<properties_definition_field>`.

The supplied definition contains two dots and therefore fails during field setup before
the Recruitment registry can finish loading.

## Architecture-preserving correction

`onehr.interview.score` already has the related stored Many2one:

`template_id = fields.Many2one(related="session_id.template_id", ...)`

and `onehr.interview.template` owns:

`scorecard_definition = fields.PropertiesDefinition(...)`

Therefore the Odoo 19-compatible definition is:

`definition="template_id.scorecard_definition"`

This keeps exactly the same business container and scorecard definition. It does not
change model ownership, interview history, scorecard semantics, workflow, security,
dependencies, approval integration, native Recruitment ownership, or ED classification.

## Prevention

`tools/source_acceptance.py` now scans every Recruitment `fields.Properties(...)` call
and fails if `definition=` is not a literal string containing exactly one dot. It also
asserts the approved scorecard contract `template_id.scorecard_definition`.

## Release marker

Previous source version: `19.0.1.0.0`  
Bounded repair version: `19.0.1.0.1`

## Retry hard gate

This is Attempt 2/2 for the current Recruitment Direct Full build task.

If activation of this exact repaired source fails again, do not perform an automatic
third source mutation. Capture the first complete traceback and classify it under the
OneHR root Guardrail.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST`  
`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO`
