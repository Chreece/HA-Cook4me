"""Real catalog editions and the production weekly selection loop."""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT=Path(__file__).resolve().parents[1]
PREFIX='cook4me_weekly_v69'
package=types.ModuleType(PREFIX);package.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[PREFIX]=package


class WeeklyVarietyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release=importlib.import_module(f'{PREFIX}.release_catalog')
        cls.variety=importlib.import_module(f'{PREFIX}.weekly_variety')
        # Five original editions from the reported screenshot, with distinct
        # language-specific IDs, image URLs, title wording and regional foods.
        cls.real=[cls.release.recipe_by_variant(id,language='el',configured_language='de',country='DE',group_families=True)
            for id in ['271141','924846','331286','511708','502225']]

    def test_real_crumble_and_porridge_editions_do_not_create_variety(self):
        signatures=[self.variety.signature(row) for row in self.real]
        for i,j in [(0,1),(0,2),(1,2),(3,4)]:
            self.assertTrue(self.variety.similar(signatures[i],signatures[j]),(i,j))
        self.assertFalse(self.variety.similar(signatures[0],signatures[3]))

    def test_reused_image_or_generic_title_alone_never_blocks_distinct_foods(self):
        base={'id':'one','canonicalName':'Vegetable soup','cover':'same.jpg','ingredients':[{'canonicalName':name} for name in ['Carrot','Onion','Milk']]}
        different={**base,'id':'two','ingredients':[{'canonicalName':name} for name in ['Pumpkin','Garlic','Water']]}
        self.assertFalse(self.variety.similar(self.variety.signature(base),self.variety.signature(different)))
        same_foods={**base,'id':'three','canonicalName':'Roasted carrot gratin','cover':'different.jpg'}
        self.assertFalse(self.variety.similar(self.variety.signature(base),self.variety.signature(same_foods)))
        empty={'id':'four','canonicalName':'Vegetable soup','cover':'same.jpg'}
        self.assertFalse(self.variety.similar(self.variety.signature(base),self.variety.signature(empty)))
        simple={'id':'rice-de','canonicalName':'Rice','ingredients':[{'canonicalName':'Rice'},{'canonicalName':'Water'}]}
        self.assertTrue(self.variety.similar(self.variety.signature(simple),self.variety.signature({**simple,'id':'rice-fr','title':'Riz','cover':'different.jpg'})))
        self.assertTrue(self.variety.similar(self.variety.signature({**base,'displayFamilyId':'family:1'}),self.variety.signature({**different,'displayFamilyId':'family:1'})))

    def generate(self,candidates,slots=(),replace=''):
        lifecycle=types.SimpleNamespace(slots=deepcopy(list(slots)),leftovers=[],settings={'mealTypes':['breakfast'],'leftoversFirst':False})
        async def save(start,rows): lifecycle.slots=deepcopy(rows)
        lifecycle.async_replace_week=save
        bridge=types.SimpleNamespace(recipe_hub=types.SimpleNamespace(profile={'houseIngredients':[]},ui_preferences={}))
        namespace=dict(__package__=PREFIX,date=date,timedelta=timedelta,deepcopy=deepcopy,
            _text=lambda x:str(x or '').strip(),
            nutrition_store_for_bridge=AsyncMock(return_value=types.SimpleNamespace(generic={},stock_lots={})),
            cost_store_for_bridge=AsyncMock(return_value=object()),normalize_nutrition_goal=lambda x:x,
            meal_history_store_for_bridge=AsyncMock(return_value=types.SimpleNamespace(recent=lambda _:[])),
            recipe_identity=importlib.import_module(f'{PREFIX}.today_logic').recipe_identity,
            recipe_matches_meal_types=lambda row,wanted:'breakfast' in row.get('mealTypes',[]),
            calculate_recipe_nutrition_fefo=lambda *a,**k:{'totals':{}},nutrition_goal_bonus=lambda *a:{'bonus':0},
            _plan_penalty=lambda *a:0,_recipe_cost_with_store=lambda *a:{})
        path=ROOT/'custom_components/cook4me/websocket_v20.py';tree=ast.parse(path.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_generate_week')
        future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[future,node],type_ignores=[])),str(path),'exec'),namespace)
        search=AsyncMock(return_value={'items':candidates})
        with patch.dict(sys.modules,{f'{PREFIX}.shared_recipe_runtime':types.SimpleNamespace(search_filtered=search)}):
            asyncio.run(namespace['_generate_week'](None,bridge,lifecycle,week_start='2026-09-15',languages=['de','fr','en'],diet='vegetarian',query='',refresh=False,shared_filters={'nutritionGoal':'balanced','mealTypes':['breakfast']},replace_slot_id=replace))
        return lifecycle.slots

    def candidates(self):
        rows=deepcopy(self.real)
        # Distinct breakfasts remain available after duplicate editions are skipped.
        for i in range(6):
            rows.append({'id':f'other-{i}','title':f'Breakfast {i}','canonicalName':f'Breakfast {i}',
                'ingredients':[{'canonicalName':f'Food {i} A'},{'canonicalName':f'Food {i} B'},{'canonicalName':f'Food {i} C'}]})
        for i,row in enumerate(rows):
            row['mealTypes']=['breakfast'];row['match']={'score':100-i}
        return rows

    def test_generation_fills_seven_days_without_translated_repeats(self):
        candidates=self.candidates();before=deepcopy(candidates)
        slots=self.generate(candidates)
        self.assertEqual(len(slots),7)
        self.assertEqual([row['date'] for row in slots],[(date(2026,9,15)+timedelta(days=i)).isoformat() for i in range(7)])
        selected=[]
        for slot in slots:
            signature=self.variety.signature(slot['recipe'])
            self.assertFalse(self.variety.already_planned(signature,selected))
            selected.append(signature)
        self.assertEqual(candidates,before,'No catalog or sending identity is rewritten')

    def test_regenerate_avoids_target_and_other_days_but_keeps_their_slots(self):
        candidates=self.candidates()
        slots=[{'id':'target','date':'2026-09-15','mealType':'breakfast','recipe':candidates[0]},
            {'id':'keep','date':'2026-09-16','mealType':'breakfast','recipe':candidates[3]}]
        result=self.generate(candidates,slots,'target')
        self.assertEqual(next(row for row in result if row['id']=='keep'),slots[1])
        replaced=next(row for row in result if row['date']=='2026-09-15')['recipe']
        self.assertFalse(any(self.variety.similar(self.variety.signature(replaced),self.variety.signature(row['recipe'])) for row in slots))

    def test_limited_catalog_does_not_fill_remaining_days_with_duplicate_languages(self):
        candidates=self.candidates()[:3]
        self.assertEqual(len(self.generate(candidates)),1)


if __name__=='__main__': unittest.main()
