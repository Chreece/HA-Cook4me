"""Food-name-only search without altering raw evidence or ingredient identity."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import unittest
from test_catalog_lifecycle_v227 import catalog
from test_catalog_amounts_v225 import presentation, PKG

ROOT=Path(__file__).resolve().parents[1]
search=importlib.import_module(PKG+'.catalog_name_search')

class NameSearchTests(unittest.TestCase):
    def test_annotations_are_not_independent_food_names(self):
        examples={
            'Lachsfilets à 200g, gesalzen und gepfeffert':'lachsfilets a 200g',
            'Frischkäse, mit Salz und Pfeffer würzen.':'frischkase',
            'Avocado, peeled and diced, mixed with lemon juice':'avocado',
            'Butter, combined with chocolate and melted in a bain-marie':'butter',
            'Lamb cut into cubes and seasoned with salt and pepper':'lamb',
            'Tortilla chips zum Servieren':'tortilla chips',
            'Cream 30% fat':'cream 30 fat',
            'Canned tomatoes':'canned tomatoes',
            'Dried tomatoes':'dried tomatoes',
            'Salt and pepper':'salt and pepper',
            'Cheese with black pepper':'cheese with black pepper',
            'Olive oil (for greasing)':'olive oil',
            'Weizenmehl Type 550':'weizenmehl type 550',
            '1,5 EL Olivenöl':'1 5 el olivenol',
            '3:1 preserving sugar':'3 1 preserving sugar',
        }
        for raw,expected in examples.items():
            with self.subTest(raw=raw):self.assertEqual(search.food_name_alias(raw),expected)

    def test_all_words_use_one_name_not_fragments_of_separate_aliases(self):
        data={'ingredients':[{'id':'example','canonicalName':'Rice','aliases':{'de':['Kartoffel']}}]}
        self.assertEqual(presentation.ingredient_choices(data,'en','rice kartoffel'),[])
        self.assertTrue(presentation.ingredient_choices(data,'en','Kartoff'))
        self.assertEqual(presentation.ingredient_choices({'ingredients':[{'id':'pineapple','canonicalName':'Pineapple'}]},'en','apple'),[])

    def test_joined_form_qualifiers_keep_food_name_searchable(self):
        data={'ingredients':[{'id':'frozen','canonicalName':'Frozen asparagus','translations':{'de':'Tiefkühlspargel'}}]}
        self.assertEqual(len(presentation.ingredient_choices(data,'el','Spargel')),1)
        self.assertEqual(len(presentation.ingredient_choices(data,'el','Tiefkühlspargel')),1)
        self.assertEqual(presentation.ingredient_choices(data,'el','pargel'),[])
        salt={'ingredients':[{'id':'sea','canonicalName':'Sea salt','translations':{'de':'Meersalz'}}]}
        self.assertEqual(len(presentation.ingredient_choices(salt,'el','Salz')),1)

    def test_recipe_query_expansion_does_not_broaden_food_identities(self):
        data={'ingredients':[{'id':'pepper','canonicalName':'Pepper','translations':{'de':'Pfeffer'}},
             {'id':'paprika','canonicalName':'Bell pepper','translations':{'de':'Paprika'}},
             {'id':'salmon','canonicalName':'Salmon fillets','aliases':{'de':['Lachsfilets, gesalzen und gepfeffert']}},
             {'id':'cheese','canonicalName':'Fresh cheese','aliases':{'de':['Frischkäse, mit Salz und Pfeffer würzen.']}}],
             '_runtimeSearchIndex':{'catalogQueryAliases':{'*':{'pfeffer':['pepper']}}}}
        before=deepcopy(data)
        self.assertEqual([r['ingredientId'] for r in presentation.ingredient_choices(data,'el','Pfeffer')],['pepper'])
        self.assertEqual(data,before)
        salmon=next(r for r in presentation.ingredient_choices(data,'el') if r['ingredientId']=='salmon')
        self.assertIn('Lachsfilets, gesalzen und gepfeffert',salmon['searchAliases'])
        self.assertNotIn('pfeffer',' '.join(salmon['nameSearchAliases']))

    def test_full_catalog_browser_and_backend_alias_projection_agree(self):
        rows=catalog.ingredient_choices('el')
        aliases=sorted({a for row in rows for a in row['searchAliases']})
        module=(ROOT/'custom_components/cook4me/frontend/ingredient-name-search-v270.js').as_uri()
        program=f'''import {{foodNameAlias,ingredientNameScore}} from {json.dumps(module)};
import {{readFileSync}} from 'node:fs';
const data=JSON.parse(readFileSync(0,'utf8'));
console.log(JSON.stringify({{aliases:data.aliases.map(foodNameAlias),results:Object.fromEntries(data.queries.map(q=>[q,data.rows.filter(r=>ingredientNameScore(r,q)>0).map(r=>r.ingredientId)]))}}));'''
        queries=['Pfeffer','Natron','lemon','chocolate','apple','ΜΑΓΕΙΡΙΚΗ ΣΟΔΑ','ground black pepper','canned tomatoes','30% fat','Spargel','Tiefkühlspargel','Vollkorn','Dosen','Salz']
        result=json.loads(subprocess.check_output(['node','--input-type=module','-e',program],input=json.dumps({'aliases':aliases,'rows':rows,'queries':queries}).encode()))
        self.assertEqual(result['aliases'],[search.food_name_alias(a) for a in aliases])
        for q in queries:
            self.assertEqual(set(result['results'][q]),{r['ingredientId'] for r in catalog.ingredient_choices('el',q)},q)
        names={r['canonicalName'] for r in rows if r['ingredientId'] in result['results']['Pfeffer']}
        self.assertNotIn('Salmon fillets',names);self.assertNotIn('Fresh cheese',names)
        self.assertIn('Pepper',names);self.assertIn('Ground black pepper',names)
        self.assertEqual(len(rows),3249)
        print(f'PASS: {len(rows)} ingredients / {len(aliases)} unique raw aliases; browser/backend parity for {len(queries)} queries')

if __name__=='__main__':unittest.main()
