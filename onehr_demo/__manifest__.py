
{'name': 'OneHR Enterprise Demo Dataset',
 'summary': 'Deterministic, compatibility-locked enterprise demo dataset control plane for OneHR',
 'description': '\n'
                'OneHR Demo is the capstone Enterprise Demo Dataset control plane for OneHR NEW on\n'
                'Odoo 19 Community Edition.\n'
                '\n'
                'This bounded MP02-MP06 release preserves the six-model control plane and implements\n'
                'MASTER PROMPT 05-06: deterministic reuse of the selected legal company, synthetic\n'
                'branch/organization foundations, jobs, grades, work locations and positions. The complete MP05-MP24 production contract and\n'
                'all 34 production-sequence policies remain audited as an explicit compatibility\n'
                'contract, but mutable production sequence rows/counters are never a prerequisite\n'
                'for the currently implemented bounded business generators. MP07+ business generators remain planned.\n',
 'author': 'OneHR',
 'website': 'https://github.com/onehr',
 'category': 'Human Resources',
 'version': '19.0.1.0.7',
 'license': 'LGPL-3',
 'depends': ['onehr_analytics',
             'onehr_appraisal',
             'onehr_assignment',
             'onehr_attendance',
             'onehr_base',
             'onehr_career_succession',
             'onehr_corehr',
             'onehr_discipline',
             'onehr_document',
             'onehr_employment_contract',
             'onehr_integrations_api',
             'onehr_job_description',
             'onehr_learning',
             'onehr_mobile_kiosk',
             'onehr_multicompany_branch',
             'onehr_payroll_bridge',
             'onehr_payroll_l10n_id',
             'onehr_pnp',
             'onehr_portal_self_service',
             'onehr_recruitment',
             'onehr_retirement_offboarding',
             'onehr_security',
             'onehr_sop',
             'onehr_timeoff',
             'onehr_workflow_approval'],
 'data': ['security/onehr_demo_groups.xml',
          'security/ir.model.access.csv',
          'security/onehr_demo_rules.xml',
          'data/generator_registry.xml',
          'views/demo_generator_views.xml',
          'views/demo_run_views.xml',
          'views/demo_checkpoint_views.xml',
          'views/demo_reference_views.xml',
          'views/demo_log_views.xml',
          'views/demo_scenario_views.xml',
          'views/menus.xml'],
 'installable': True,
 'application': False}

