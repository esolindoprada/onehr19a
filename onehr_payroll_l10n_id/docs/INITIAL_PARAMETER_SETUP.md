# Initial Indonesia Payroll Parameter Setup

The module deliberately does **not** auto-create an active company parameter record.
A statutory localization package must not become payroll-active merely because an addon was installed.

After activation:

1. Open **OneHR → Payroll → Localization (ID)** as Payroll Manager.
2. Create one parameter bundle for the company.
3. Set the bundle **Valid From** date to the real start of the rates/ceilings represented.
4. Review every PPh21/PTKP/TER, BPJS and THR section.
5. Pay special attention to the current BPJS JP wage ceiling and its effective date.
6. Fill/update the company THR holiday calendar if it is part of payroll hand-off.
7. Use **Validate Parameter Structure**.
8. Record legal/source notes where needed.
9. Use **Mark Regulatory Review Complete**.
10. Only then generate Payroll Bridge exports.

Payroll Bridge will reject generation if no reviewed effective parameter covers the payroll-period end date.

When a rate/ceiling/rule changes:

- do not overwrite a version already used by payroll evidence;
- use **Create New Version** for a future/effective change;
- use **Create Correction Revision** for a governed correction;
- review the new/corrected version again before payroll use.

This creates an auditable regulatory chain without inventing a fake approval workflow.
