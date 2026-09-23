"""Meal suggestion eligibility; real selectors and ranking code with HA boundaries."""
from __future__ import annotations
import ast
from copy import deepcopy
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/cook4me'
PKG = 'cook4me_meal_suitability_tests'
pkg = ModuleType(PKG); pkg.__path__ = [str(COMPONENT)]; sys.modules[PKG] = pkg
from cook4me_meal_suitability_tests.recipe_suitability import is_cooking_guide, meal_candidates
from cook4me_meal_suitability_tests.today_logic import select_diverse
from cook4me_meal_suitability_tests.today_multilang import select_catalog_balanced, select_today_categories
from cook4me_meal_suitability_tests.weekly_variety import signature, available_candidates


def food(label, identity=None, **kw):
    return {'canonicalName': label, 'name': label, 'ingredientId': identity or label, **kw}


def recipe(heading='Rice', ingredients=None, **kw):
    return {'id':heading,'title':heading,'canonicalName':heading,'ingredients':ingredients if ingredients is not None else [food('Rice')],
            'todayCatalogLanguage':'en','language':'en','mealTypes':['breakfast','main'],
            'match':{'safe':True,'score':100}, **kw}


class Classification(unittest.TestCase):
    def test_plain_ingredient_titles(self):
        for title, name in [('Rice','Rice'),('Carrots','Carrot'),('Cauliflower','Cauliflower'),('Bulgur wheat','Bulgur wheat'),('Pepper','Pepper')]:
            with self.subTest(title=title): self.assertTrue(is_cooking_guide(recipe(title,[food(name)])))
    def test_water_does_not_turn_a_guide_into_a_meal(self):
        self.assertTrue(is_cooking_guide(recipe('Cauliflower',[food('Cauliflower'),food('Water')])))
    def test_cooking_aids_and_repeated_food_count_once(self):
        self.assertTrue(is_cooking_guide(recipe('Plain rice',[food('Rice'),food('Rice'),food('Water'),food('Salt'),food('Black pepper'),food('Olive oil')])) )
    def test_real_flavour_ingredients_are_not_ignored(self):
        for addition in ['Milk','Onion','Garlic','Vegetable stock','Soy sauce','Coconut water','Lemon juice']:
            with self.subTest(addition=addition):self.assertFalse(is_cooking_guide(recipe('Rice',[food('Rice'),food(addition)])))
    def test_genuine_simple_dishes_are_preserved(self):
        for title, ingredients in [('Rice porridge',['Rice','Milk']),('Cauliflower soup',['Cauliflower','Water']),('Dulce de leche',['Condensed milk','Water']),('Banana ice cream',['Banana']),('Apple compote',['Apple','Water']),('Yogurt',['Milk','Yogurt starter'])]:
            with self.subTest(title=title):self.assertFalse(is_cooking_guide(recipe(title,list(map(food,ingredients)))))
    def test_titles_are_not_keyword_blacklists(self):
        for title in ['Rice pudding','Rice with vegetables','Carrot soup','Stuffed peppers','Bulgur salad']:
            with self.subTest(title=title):self.assertFalse(is_cooking_guide(recipe(title)))
    def test_multilingual_exact_food_titles(self):
        for title,name,water in [('Reis','Reis','Wasser'),('Karotten','Karotten','Wasser'),('Riz','Riz','Eau'),('Ρύζι','Ρύζι','Νερό'),('ΡΥΖΙ','Ρύζι','Νερό'),('Arroz','Arroz','Agua')]:
            with self.subTest(title=title):self.assertTrue(is_cooking_guide(recipe(title,[{'name':name},{'name':water}])))
    def test_canonical_evidence_independent_of_ui_name(self):
        r=recipe('Cauliflower',[food('Cauliflower',name='Κουνουπίδι'),food('Water',name='Νερό')]);r['title']='Blumenkohl';self.assertTrue(is_cooking_guide(r))
    def test_basic_cooking_prefixes(self):
        for title in ['How to cook rice','Cooked rice','Steamed rice','Boiled rice','Plain rice']:
            with self.subTest(title=title):self.assertTrue(is_cooking_guide(recipe(title)))
    def test_preset_yield_recipe_with_nonmatching_translation(self):
        r=recipe('Bulgur',[food('Bulgur wheat',quantity=300,unitKey='UNIT_27')],source='cook4me_release_catalog',yield_ignored=None)
        r['yield']={'quantity':300,'unitKey':'UNIT_27'};r['durations']={'prepTime':0,'cookingTime':7}
        self.assertTrue(is_cooking_guide(r))
    def test_serving_yield_not_sufficient_to_exclude_a_simple_dish(self):
        r=recipe('Dulce de leche',[food('Condensed milk',quantity=1,unitKey='UNIT_41'),food('Water')],source='cook4me_release_catalog',durations={'prepTime':0,'cookingTime':40})
        r['yield']={'quantity':1,'unitKey':'UNIT_1'};self.assertFalse(is_cooking_guide(r))
    def test_unknown_or_malformed_ingredients_not_guessed_from_title(self):
        for ingredients in [None,[],[{}],['Rice'],[food('Rice'),{}],{'name':'Rice'}]:
            r=recipe();r['ingredients']=ingredients
            with self.subTest(ingredients=ingredients):self.assertFalse(is_cooking_guide(r))
    def test_missing_data_not_an_automatic_quality_claim(self):
        for value in [None,[],True,{},'',recipe('Rice',[]),recipe('Rice',[food('Rice')],canonicalName='',title='')]:
            with self.subTest(value=value):self.assertFalse(is_cooking_guide(value))
    def test_explicit_guide_metadata(self):
        for value in ['cooking_guide', {'name':'Ingredient cooking guide'}, {'key':'basic_ingredient'}]:
            self.assertTrue(is_cooking_guide(recipe('Unknown',[],recipeType=value)))
    def test_opaque_types_and_dish_categories_are_not_guessed(self):
        for value in ['RECIPE_TYPE_1',{'key':'COURSE_1'},'side','breakfast']:
            self.assertFalse(is_cooking_guide(recipe('A dish',[],recipeType=value)))
    def test_measured_water_labels_are_only_cooking_aids(self):
        for water in ['Water, 300 milliliters','200 milliliters of water']:
            self.assertTrue(is_cooking_guide(recipe('Pepper',[food('Pepper'),food(water)])))
        self.assertFalse(is_cooking_guide(recipe('Rice',[food('Rice'),food('200 milliliters of coconut water')])))
    def test_malformed_units_and_empty_normalized_names_are_safe(self):
        r=recipe('A dish',[food('Rice',quantity=100,unitKey={})],source='cook4me_release_catalog',durations={'prepTime':0,'cookingTime':1})
        r['yield']={'quantity':100,'unitKey':['UNIT_27']}
        self.assertFalse(is_cooking_guide(r));self.assertFalse(is_cooking_guide(recipe('???',[{'name':'???'}])))
    def test_unknown_identity_does_not_count_as_water(self):
        self.assertFalse(is_cooking_guide(recipe('Rice',[food('Rice'),{'ingredientId':'unknown'}])))
    def test_canonical_name_wins_over_conflicting_display_label(self):
        self.assertFalse(is_cooking_guide(recipe('Rice',[food('Rice'),food('Milk',name='Water')])))
    def test_different_food_forms_do_not_collapse(self):
        self.assertFalse(is_cooking_guide(recipe('Rice',[food('Rice'),food('Rice flour')])))
    def test_input_not_mutated_and_candidates_keep_original_nodes(self):
        rows=[recipe(),recipe('Rice porridge',[food('Rice'),food('Milk')])];before=deepcopy(rows)
        out=meal_candidates(rows);self.assertEqual(out,[rows[1]]);self.assertIs(out[0],rows[1]);self.assertEqual(before,rows)


class Selection(unittest.TestCase):
    def setUp(self):
        self.guide=recipe();self.meal=recipe('Porridge',[food('Rice'),food('Milk')]);self.meal['match']['score']=1
    def test_legacy_daily_never_uses_guide_even_without_variety(self):
        for enabled in [False,True]:self.assertEqual([r['id'] for r in select_diverse([self.guide,self.meal],8,enabled=enabled)],[self.meal['id']])
    def test_language_balancing_never_fills_quota_with_guides(self):
        self.guide['todayCatalogLanguage']='de'
        self.assertEqual([r['id'] for r in select_catalog_balanced([self.guide,self.meal],8,['de','en'])],[self.meal['id']])
    def test_category_counts_and_rotation_use_eligible_meals(self):
        r=select_today_categories([self.guide,self.meal],['breakfast'],['en'],history=[{'familyId':'id:Porridge','language':'en'}])
        self.assertEqual(r['categoryCounts']['breakfast'],1);self.assertEqual(r['items'][0]['id'],self.meal['id'])
    def test_all_meal_types_with_only_guides_remain_empty(self):
        from cook4me_meal_suitability_tests.today_logic import MEAL_TYPES
        self.guide['mealTypes']=list(MEAL_TYPES)
        r=select_today_categories([self.guide],list(MEAL_TYPES),['en'])
        self.assertEqual(r['items'],[]);self.assertEqual(r['emptyMealTypes'],list(MEAL_TYPES));self.assertTrue(all(v==0 for v in r['categoryCounts'].values()))
    def test_weekly_fallback_never_reintroduces_guide(self):
        rows=[self.guide,self.meal];signatures={id(row):signature(row) for row in rows}
        for avoid in [[],[signature(self.meal)]]:
            out=available_candidates(rows,signatures,[],avoid)
            self.assertNotIn(self.guide,out)
        self.assertEqual(available_candidates(rows,signatures,[]),[self.meal])


def function(path,name,namespace):
    """Execute the production function body; replace only HA/scoring dependencies."""
    tree=ast.parse((COMPONENT/path).read_text())
    found=next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    found=deepcopy(found);found.decorator_list=[]
    scope={'__name__':PKG+'.test_boundary','__package__':PKG,'deepcopy':deepcopy,**namespace}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),found],type_ignores=[])),str(COMPONENT/path),'exec'),scope)
    return scope[name]


class RankRoutes(unittest.TestCase):
    def test_primary_rank_excludes_before_limit_without_changing_diet_filter(self):
        scored=[]
        def score(row,profile):
            scored.append(row['id']);return {'safe':True,'eligibleWithSubstitutions':True,'score':1}
        rank=function('websocket_v13.py','_rank_filtered',{'score_recipe':score,'enrich_match_with_house_keys':lambda row,match,house:match,'dt_util':SimpleNamespace(now=datetime.now)})
        bridge=SimpleNamespace(recipe_hub=SimpleNamespace(profile={},habit_terms=[]))
        good=recipe('Porridge',[food('Rice'),food('Milk')])
        self.assertEqual([r['id'] for r in rank(bridge,[recipe()]*80+[good],diet='profile',limit=1)],[good['id']])
        self.assertEqual(scored,[good['id']])
        # Manual saved-plan/search validation still invokes the same diet rules.
        self.assertEqual(len(rank(bridge,[recipe()],diet='profile',limit=1,for_suggestions=False)),1)
    def test_legacy_voice_hub_rank_excludes_guides(self):
        rank=function('recipe_hub.py','rank',{})
        class Hub:
            def annotate(self,row):return deepcopy(row)
        self.assertEqual(rank(Hub(),[recipe(),recipe('Soup',[food('Carrot'),food('Water')])])[0]['title'],'Soup')
    def test_suggestion_and_manual_processor_contexts_explicit(self):
        tree=ast.parse((COMPONENT/'shared_recipe_runtime.py').read_text())
        search=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='search_filtered')
        calls=[n for n in ast.walk(search) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='processor']
        self.assertTrue(any(k.arg=='for_suggestions' and isinstance(k.value,ast.Constant) and k.value.value is True for k in calls[0].keywords))
        processor=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='processor')
        defaults=dict(zip(processor.args.kwonlyargs,processor.args.kw_defaults))
        self.assertIs(next(v.value for k,v in defaults.items() if k.arg=='for_suggestions'),False)
        calls=[n for n in ast.walk(processor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_rank_filtered']
        self.assertTrue(any(k.arg=='for_suggestions' and isinstance(k.value,ast.Name) and k.value.id=='for_suggestions' for k in calls[0].keywords))
    def test_explicit_ai_creation_does_not_report_guide_as_diet_failure(self):
        tree=ast.parse((COMPONENT/'websocket_v22.py').read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_rank_filtered']
        self.assertTrue(any(k.arg=='for_suggestions' and isinstance(k.value,ast.Constant) and k.value.value is False for k in calls[0].keywords))


class CatalogAudit(unittest.TestCase):
    def test_shipped_multilingual_guides_and_real_simple_meals(self):
        # Materialize real compact records with their source ingredient names,
        # exactly the evidence the release renderer expands before ranking.
        catalog=json.loads((COMPONENT/'catalog/merged_catalog.v1.json').read_text())
        ingredients={r['id']:r for r in catalog['ingredients']}
        seen=set();excluded=0;kept=[];counts={}
        target={'Rice','Carrots','Cauliflower','Bulgur','Bulgur wheat','Pepper'}
        for family in catalog['recipes']:
            for variant in family.get('variants',[]):
                r={**variant,'canonicalName':family['canonicalName'],'source':'cook4me_release_catalog'}
                r['ingredients']=[{**ingredients.get(i.get('ingredientId'),{}),**i} for i in variant.get('ingredients',[])]
                guide=is_cooking_guide(r)
                if guide:
                    excluded+=1;language=variant.get('language','');counts[language]=counts.get(language,0)+1
                if family['canonicalName'] in target:
                    self.assertTrue(guide,(family['canonicalName'],variant['title']));seen.add(family['canonicalName'])
                if family['canonicalName'] in {'Dulce de leche','Dulce de leche sweets','Rice pudding','Yogurt'}:
                    self.assertFalse(guide,family['canonicalName']);kept.append(family['canonicalName'])
        self.assertEqual(seen,target);self.assertGreater(len(kept),0)
        print('CATALOG AUDIT:',json.dumps({'excludedBasicGuideVariants':excluded,'languages':counts,'preservedSimpleDishExamples':sorted(set(kept))},ensure_ascii=False))


if __name__=='__main__':unittest.main()
