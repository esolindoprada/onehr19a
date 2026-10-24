
# onehr_corehr — Direct Full Addon Build v1

## Delivery

Built as one coherent Direct Full Addon Build. Codex was not used.

## Core architecture

The old scaffold description proposed a parallel `onehr.employee`. That ownership
is corrected: Odoo 19 `hr.employee` is the employee master and `hr.version`
holds versioned employment facts. OneHR extends those canonical models.

The addon implements all 13 Registry ownership rows and no additional OneHR
persistent/transient business model.

## Employee master

Native employee receives:
- enterprise employee number with automatic sequence;
- profile completeness/status;
- engagement/grade/primary-position version façade fields;
- lifecycle/history smart buttons and inline enterprise profile tabs;
- minimum-necessary derived accommodation flag.

Only the employee number is copied into `hr.employee.public`.

## Identifiers

The portfolio exists for enterprise identifiers requiring multiple/effective
records. Routine lists display masked values. Raw values and notes are restricted
to Identifier Steward. The security audit records that a sensitive read/change
occurred but does not store the raw identifier value in audit metadata.

## Occupational health

Three isolated models are available only to explicit Occupational Health users:
- Work Incident (ED3 controlled case);
- Medical Assessment (ED3 finalize/supersede);
- Disability/Accommodation (ED1 minimum necessary).

Core HR Manager and Security Admin do not imply Occupational Health access.

## Documents and imports

Core HR intentionally does not implement `onehr.employee.document`. Personal
document versioning, expiry, reminders and e-sign belong to `onehr_document`.

The historical import-wizard intent is fulfilled through Odoo's native Data
Import on the enterprise lists. No unregistered transient wizard is introduced.

## Reporting

A safe OneHR Employee Profile Summary PDF is bound to `hr.employee`. It excludes
national identifiers, medical payload and disability detail.

## Current gate status

DIRECT_FULL_SOURCE_BUILD: BUILT
SOURCE_ACCEPTANCE: EXECUTED_BY_PACKAGE_TOOL
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_COREHR_MOVE_FORWARD_READY: NO

## Odoo 19 Compatibility Correction v1.1

Target runtime evidence on Odoo 19.0.20251217 proved that the report action
security field is `group_ids`, not `groups_id`. The Employee Profile report was
corrected without removing or weakening its Core HR Officer restriction. The
source gate now checks this ORM contract explicitly.

