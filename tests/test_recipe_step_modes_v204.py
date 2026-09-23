"""Program extraction and translation preserve evidence, not inferred recipes."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / 'custom_components/cook4me'
sys.path.insert(0, str(COMP / 'vendor'))
from cook4me_recipe_catalog import extract_recipe_steps
spec = importlib.util.spec_from_file_location('mode_translation', COMP / 'recipe_translation.py')
translation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translation)

def sequence(group='APPLIANCE_GROUP_15', *names):
    return {'applianceGroup': {'key': group} if group else None,
            'operations': [{'program': {'key': f'PROGRAM_{i}', 'name': name}} for i, name in enumerate(names)]}

def steps(sequences, **other):
    return extract_recipe_steps({'steps': [{'fid': 'step-0', 'applicationDescription': 'Cook for 5 minutes.',
                                            'sequences': sequences, **other}]})[0]

class StepModeEvidence(unittest.TestCase):
    def test_cook4me_sequence_wins_over_other_appliance(self):
        row=steps([sequence('APPLIANCE_GROUP_1','Blending'),sequence('APPLIANCE_GROUP_15','Pressure cooking')])
        self.assertEqual(row['programName'],'Pressure cooking')
        self.assertEqual(row['programs'][0]['applianceGroup'],'APPLIANCE_GROUP_15')
    def test_foreign_appliance_is_not_cook4me_fallback(self):
        row=steps([sequence('APPLIANCE_GROUP_1','Blending')])
        self.assertNotIn('programName',row)
        self.assertEqual(row['programs'],[])
    def test_multiple_operations_kept_in_source_order(self):
        row=steps([sequence('APPLIANCE_GROUP_15','Browning','Pressure cooking','Keep warm')])
        self.assertEqual([r['programName'] for r in row['programs']],['Browning','Pressure cooking','Keep warm'])
        self.assertEqual(row['programName'],'Browning')
    def test_multiple_matching_sequences_keep_order(self):
        row=steps([sequence('APPLIANCE_GROUP_15','Browning'),sequence('APPLIANCE_GROUP_15','Pressure cooking')])
        self.assertEqual(len(row['programs']),2)
    def test_unscoped_legacy_sequence_still_usable(self):
        row=steps([sequence(None,'Pressure cooking')])
        self.assertEqual(row['programName'],'Pressure cooking')
    def test_explicit_empty_device_sequence_does_not_borrow_other_modes(self):
        row=steps([sequence(None,'Browning'),sequence('APPLIANCE_GROUP_15')])
        self.assertEqual(row['programs'],[])
    def test_string_appliance_group_supported(self):
        seq=sequence('APPLIANCE_GROUP_15','Pressure cooking');seq['applianceGroup']='APPLIANCE_GROUP_15'
        self.assertEqual(steps([seq])['programName'],'Pressure cooking')
    def test_null_and_malformed_operations_are_ignored(self):
        self.assertEqual(steps([None,{}, {'operations':[None,{}, {'program':None}]}])['programs'],[])
    def test_opaque_keys_are_preserved_not_assigned_modes(self):
        row=steps([{'applianceGroup':{'key':'APPLIANCE_GROUP_15'},'operations':[{'program':{'key':'PROGRAM_999'}}]}])
        self.assertEqual(row['programKey'],'PROGRAM_999');self.assertNotIn('programName',row)
    def test_preparation_keeps_its_type_without_fake_program(self):
        row=steps([],type={'key':'STEP_TYPE_X','name':'Preparation'})
        self.assertEqual(row['typeName'],'Preparation');self.assertEqual(row['programs'],[])
    def test_no_search_in_instruction_or_recipe_title(self):
        row=extract_recipe_steps({'title':'Pressure cooking','steps':[{'instruction':'Do not pressure cook.'}]})[0]
        self.assertEqual(row['programs'],[])
    def test_original_data_never_changes(self):
        data={'steps':[{'sequences':[sequence('APPLIANCE_GROUP_15','Pressure cooking')],'instruction':'Cook'}]}
        before=deepcopy(data);extract_recipe_steps(data);self.assertEqual(data,before)
    def test_ids_positions_and_instructions_preserved(self):
        row=steps([sequence('APPLIANCE_GROUP_15','Pressure cooking')])
        self.assertEqual((row['functionalId'],row['stepIndex'],row['instruction']),('step-0',0,'Cook for 5 minutes.'))
    def test_translation_preserves_current_source_mode(self):
        recipe={'title':'Rice','steps':[steps([sequence('APPLIANCE_GROUP_15','Pressure cooking')])]}
        out=translation.apply_saved_translation(recipe,{'title':'Ρύζι','steps':['Μαγειρέψτε για 5 λεπτά.']},'el')
        self.assertEqual(out['steps'][0]['programs'],recipe['steps'][0]['programs'])
        self.assertEqual(out['steps'][0]['functionalId'],'step-0')
        self.assertEqual(out['steps'][0]['instruction'],'Μαγειρέψτε για 5 λεπτά.')
    def test_translation_cache_does_not_supply_outdated_program(self):
        old={'title':'Rice','steps':[steps([sequence('APPLIANCE_GROUP_15','Browning')])]}
        new=deepcopy(old);new['steps']=[steps([sequence('APPLIANCE_GROUP_15','Pressure cooking')])]
        self.assertEqual(translation.text_translation_cache_key(old,'el'),translation.text_translation_cache_key(new,'el'))
        out=translation.apply_saved_translation(new,{'title':'Ρύζι','steps':['Μαγειρέψτε για 5 λεπτά.']},'el')
        self.assertEqual(out['steps'][0]['programName'],'Pressure cooking')

if __name__=='__main__':unittest.main()
