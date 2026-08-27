from __future__ import annotations
import ast, csv, io, re, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors=[]
def ok(m): print(f"PASS: {m}")
def fail(m): errors.append(m); print(f"FAIL: {m}")

try: manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text(encoding='utf-8'))
except Exception as exc: manifest={}; fail(f"manifest parse: {exc}")
if manifest.get('name')=='OneHR Employment Contract': ok('PROJECT/ADDON identity')
else: fail('manifest identity')
if manifest.get('version')=='19.0.1.0.0': ok('manifest Odoo 19 version')
else: fail('manifest version')
expected=['onehr_corehr','onehr_security','onehr_workflow_approval']
if manifest.get('depends')==expected: ok(f'hard dependencies exactly {expected}')
else: fail(f"dependencies {manifest.get('depends')!r}")
for rel in manifest.get('data',[]):
    if not (ROOT/rel).exists(): fail(f'missing manifest data: {rel}')

for p in ROOT.rglob('*.py'):
    try: compile(p.read_text(encoding='utf-8'),str(p),'exec')
    except Exception as exc: fail(f'Python compile {p.relative_to(ROOT)}: {exc}')
if not any(x.startswith('Python compile') for x in errors): ok('all Python sources compile')
for p in ROOT.rglob('*.xml'):
    try: ET.parse(p)
    except Exception as exc: fail(f'XML parse {p.relative_to(ROOT)}: {exc}')
if not any(x.startswith('XML parse') for x in errors): ok('all XML files parse')

models='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in (ROOT/'models').glob('*.py'))
for name in ['onehr.contract','onehr.contract.template']:
    if not re.search(rf'_name\s*=\s*["\']{re.escape(name)}["\']',models): fail(f'missing approved core model {name}')
if re.search(r'_name\s*=\s*["\']onehr_employment_contract\.onehr_employment_contract["\']',models): fail('generic scaffold model survived')
else: ok('generic scaffold model removed')
if '.sudo(' in models or '.sudo (' in models: fail('business model source contains sudo()')
else: ok('no business sudo() authorization bypass')
if 'safe_eval' in models or re.search(r'\beval\s*\(',models): fail('executable stored expression pattern')
else: ok('no executable rule/template evaluation')
if models.count('@api.ondelete(at_uninstall=False)')>=2: ok('uninstall-safe business deletion protections')
else: fail('missing ondelete protections')
if re.search(r'\n\s*def\s+unlink\s*\(',models): fail('unlink override found')
else: ok('no uninstall-blocking unlink override')

rows=list(csv.reader(io.StringIO((ROOT/'security/ir.model.access.csv').read_text(encoding='utf-8-sig'))))
print('ACL_ROW_COUNT:',len(rows)-1)
if any(r[3]=='base.group_user' for r in rows[1:] if len(r)>3): fail('base.group_user custom-model ACL')
else: ok('no broad base.group_user custom-model ACL')
if any(r[7]=='1' for r in rows[1:] if len(r)>7): fail('ACL grants unlink')
else: ok('no ACL grants governed-model unlink')

views='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in (ROOT/'views').glob('*.xml'))
for model in ['onehr.contract','onehr.contract.template']:
    kinds={k:0 for k in ['list','form','search']}
    for p in (ROOT/'views').glob('*.xml'):
        tree=ET.parse(p)
        for rec in tree.findall(".//record[@model='ir.ui.view']"):
            mf=rec.find("./field[@name='model']"); af=rec.find("./field[@name='arch']")
            if mf is not None and (mf.text or '').strip()==model and af is not None and list(af):
                tag=list(af)[0].tag
                if tag in kinds: kinds[tag]+=1
    for k,v in kinds.items():
        if not v: fail(f'{model} missing {k} view')
if not any('missing list view' in x for x in errors): ok('enterprise list coverage')
if not any('missing form view' in x for x in errors): ok('professional form coverage')
if not any('missing search view' in x for x in errors): ok('mandatory search coverage')
for marker,label in [
    ('widget="statusbar"','statusbar'),('class="oe_stat_button"','smart buttons'),
    ('Generate Contract Document','body-form action'),('action_done','One2many row action'),
    ('<chatter/>','chatter'),('<calendar','calendar/timeline'),('<pivot','pivot reporting'),('<graph','graph reporting')]:
    if marker in views: ok(label)
    else: fail(f'missing UI marker: {label}')

method_count=0
for p in (ROOT/'tests').glob('test_*.py'):
    method_count += len(re.findall(r'^\s*def\s+test_[A-Za-z0-9_]+\s*\(',p.read_text(encoding='utf-8'),re.M))
print('TEST_METHOD_COUNT:',method_count)
if method_count==20: ok('exactly 20 runtime test methods')
else: fail(f'expected 20 tests, got {method_count}')

for name in ['PROJECT_IDENTITY_PREFLIGHT.md','MODEL_REGISTRY_ALIGNMENT.md','FULL_STRUCTURAL_INVENTORY.md','UI_UX_MATRIX.md','INTEGRATION_CONTRACTS.md','ENTERPRISE_COMPLETENESS_MATRIX.md','IMPLEMENTATION_REPORT.md']:
    if not (ROOT/'docs'/name).exists(): fail(f'missing governance doc {name}')
if not any('missing governance doc' in x for x in errors): ok('governance/completeness documents present')

print('SOURCE_ACCEPTANCE_FAIL_COUNT:',len(errors))
if errors:
    print('ONEHR_EMPLOYMENT_CONTRACT_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL'); sys.exit(1)
print('ONEHR_EMPLOYMENT_CONTRACT_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS')
print('WINDOWS_RUNTIME_ACCEPTANCE: PENDING')
print('ONEHR_EMPLOYMENT_CONTRACT_MOVE_FORWARD_READY: NO')
