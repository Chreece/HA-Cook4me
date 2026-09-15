"""Exercise actual preferences, event detection and speech delivery with HA I/O isolated."""
import ast
import asyncio
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'cook4me_announcements_v72'
package = types.ModuleType(PREFIX); package.__path__ = [str(ROOT/'custom_components/cook4me')]; sys.modules[PREFIX] = package
NS = types.SimpleNamespace


class AnnouncementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = NS(rows=[], async_update_entity=self.update_entity)
        self.generate = AsyncMock(return_value=NS(data={'text': 'Ανακατέψτε για 2 λεπτά'}))
        fake = {
            'homeassistant.core': NS(Context=lambda **kw: NS(**kw)),
            'homeassistant.auth.permissions.const': NS(POLICY_CONTROL='control', POLICY_READ='read'),
            'homeassistant.helpers.storage': NS(Store=lambda *args: NS(async_save=AsyncMock(), async_load=AsyncMock(return_value=None))),
            'homeassistant.components.media_player': NS(MediaPlayerEntityFeature=NS(PLAY_MEDIA=512, MEDIA_ANNOUNCE=1048576)),
            'homeassistant.components.ai_task.const': NS(AITaskEntityFeature=NS(GENERATE_DATA=1)),
            'homeassistant.components': NS(ai_task=NS(async_generate_data=self.generate)),
            'homeassistant.helpers': NS(entity_registry=NS(async_get=lambda hass:self.registry, async_entries_for_config_entry=lambda reg,id:[r for r in reg.rows if r.entry_id==id], RegistryEntryDisabler=NS(INTEGRATION='integration'))),
            PREFIX+'.websocket_v5': NS(_parse_ai_json=lambda data:json.loads(data) if isinstance(data,str) else data),
        }
        self.patcher = patch.dict(sys.modules, fake); self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.settings_mod = importlib.import_module(PREFIX+'.device_settings')
        self.mod = importlib.import_module(PREFIX+'.announcements')
        self.users = {id:self.user(id) for id in ('alice','bob')}
        self.states = {}
        def state(id, features=0, value='unknown'):
            self.states[id] = NS(entity_id=id,state=value,attributes={'supported_features':features,'friendly_name':id})
        for player in ('media_player.kitchen','media_player.living'): state(player,1049088,'idle')
        state('media_player.tv',512,'idle'); state('media_player.no_audio',1,'idle'); state('media_player.offline',512,'unavailable')
        for id in ('tts.piper','ai_task.local'): state(id)
        self.tts = NS(entity_id='tts.piper', available=True, default_language='en_US', supported_languages=['en_US','el_GR'], async_get_supported_voices=lambda lang:[NS(voice_id='voice1',name='Voice One')])
        self.ai = NS(entity_id='ai_task.local',available=True,supported_features=1)
        self.hass = NS(data={'tts':NS(entities=[self.tts]),'ai_task':NS(entities=[self.ai])},
            states=NS(get=self.states.get,async_all=lambda domain:[s for id,s in self.states.items() if id.startswith(domain+'.')]),
            auth=NS(async_get_user=AsyncMock(side_effect=lambda id:self.users.get(id))),
            services=NS(async_call=AsyncMock()), async_create_background_task=lambda coro,name:asyncio.create_task(coro))
        self.callbacks=[]
        self.bridge = NS(hass=self.hass,device_uuid='device1',entry=NS(entry_id='entry1'),data=self.data(),async_add_listener=self.add_listener)
        self.registry.rows=[NS(entry_id='entry1',entity_id='sensor.cook4me_state',unique_id='device1_summary',platform='cook4me',disabled_by=None)]
        self.settings=self.settings_mod.DeviceSettings(self.bridge);await self.settings.async_load()
        self.manager=self.mod.Announcements(self.bridge,self.settings)
        self.addAsyncCleanup(self.manager.close)

    def user(self,id,denied=()):
        return NS(id=id,is_active=True,permissions=NS(check_entity=lambda entity,policy:entity not in denied))

    def update_entity(self,id,**kw):
        row=next(r for r in self.registry.rows if r.entity_id==id)
        for k,v in kw.items():setattr(row,k,v)

    def add_listener(self,callback):
        self.callbacks.append(callback)
        return lambda:self.callbacks.remove(callback)

    def data(self,**kw):
        return {'connected':True,'active':False,'phase':'idle',**kw}

    def prefs(self,**kw):
        return {**deepcopy(self.settings_mod.DEFAULTS),'enabled':True,'players':['media_player.kitchen'],'tts':'tts.piper','language':'el_GR',**kw}

    async def save(self,id='alice',**kw):
        return await self.settings.async_save(self.users[id],self.prefs(**kw))

    async def publish(self,**kw):
        self.bridge.data.update(kw);self.manager.on_update()
        if self.manager.worker:await self.manager.worker

    def test_choices_filter_capabilities_permissions_and_unknown_ai_state(self):
        user=self.user('alice',{'media_player.living'})
        options=self.settings_mod.choices(self.hass,user)
        self.assertEqual({p['id'] for p in options['players']},{'media_player.kitchen','media_player.tv'})
        self.assertEqual(options['ai'][0]['id'],'ai_task.local')
        self.assertEqual(options['tts'][0]['voices']['el_GR'][0]['id'],'voice1')
        self.ai.available=False
        self.assertEqual(self.settings_mod.choices(self.hass,user)['ai'],[])

    async def test_preferences_persist_per_user_and_serialize_writes(self):
        await asyncio.gather(self.save(), self.save('bob',players=['media_player.living'],language='en_US'))
        saved=deepcopy(self.settings.store.async_save.call_args.args[0])
        restored=self.settings_mod.DeviceSettings(self.bridge)
        restored.store.async_load=AsyncMock(return_value=saved);await restored.async_load()
        self.assertEqual(restored.for_user('alice')['players'],['media_player.kitchen'])
        self.assertEqual(restored.for_user('bob')['language'],'en_US')
        self.assertFalse(restored.for_user('someone_else')['enabled'])
        snapshot=restored.for_user('alice');snapshot['players'].clear()
        self.assertTrue(restored.for_user('alice')['players'])

    async def test_preferences_validate_language_voice_player_and_ai(self):
        for patch_values in ({'language':'xx'},{'voice':'bad'},{'players':['media_player.no_audio']},{'ai':'ai_task.missing'},{'enabled':'yes'}):
            with self.subTest(patch_values=patch_values),self.assertRaises(ValueError):await self.save(**patch_values)
        self.users['alice']=self.user('alice',{'media_player.kitchen'})
        with self.assertRaises(ValueError):await self.save()
        result=await self.save(enabled=False,players=['media_player.offline'])
        self.assertFalse(result['enabled'])

    async def test_migration_once_keeps_summary_connection_other_device_and_manual_reenable(self):
        def row(key,entry='entry1',disabled=None):return NS(entry_id=entry,entity_id='sensor.'+key+entry,unique_id='device1_'+key,platform='cook4me',disabled_by=disabled)
        self.registry.rows.extend([row('phase'),row('instruction'),row('connected'),row('step',disabled='user'),row('status',entry='other')])
        for row in self.registry.rows:
            if row.unique_id in {'device1_summary','device1_connected'}:
                self.states[row.entity_id]=NS(state='idle' if row.unique_id.endswith('summary') else 'on',attributes={})
        await self.settings.async_consolidate_entities()
        self.assertEqual([r.disabled_by for r in self.registry.rows],[None,'integration','integration',None,'user',None])
        self.registry.rows[1].disabled_by=None
        await self.settings.async_consolidate_entities()
        self.assertIsNone(self.registry.rows[1].disabled_by)

    async def test_migration_waits_for_both_live_primary_entities_before_disabling_legacy(self):
        legacy=NS(entry_id='entry1',entity_id='sensor.phase',unique_id='device1_phase',platform='cook4me',disabled_by=None)
        connected=NS(entry_id='entry1',entity_id='binary_sensor.connected',unique_id='device1_connected',platform='cook4me',disabled_by=None)
        self.registry.rows.extend([legacy,connected])
        for summary_state,connection_state in [(None,None),('idle',None),('unavailable','on'),('idle','unknown')]:
            self.states.pop('sensor.cook4me_state',None);self.states.pop('binary_sensor.connected',None)
            if summary_state:self.states['sensor.cook4me_state']=NS(state=summary_state,attributes={})
            if connection_state:self.states['binary_sensor.connected']=NS(state=connection_state,attributes={})
            await self.settings.async_consolidate_entities()
            self.assertIsNone(legacy.disabled_by)
            self.assertFalse(self.settings.data['entitiesConsolidated'])
        # A legitimately offline device still has two loaded primary entities.
        self.states['sensor.cook4me_state']=NS(state='offline',attributes={})
        self.states['binary_sensor.connected']=NS(state='off',attributes={})
        await self.settings.async_consolidate_entities()
        self.assertEqual(legacy.disabled_by,'integration')
        self.assertTrue(self.settings.data['entitiesConsolidated'])

    async def test_restored_state_is_not_proof_of_successful_entity_registration(self):
        self.registry.rows.extend([
            NS(entry_id='entry1',entity_id='sensor.phase',unique_id='device1_phase',platform='cook4me',disabled_by=None),
            NS(entry_id='entry1',entity_id='binary_sensor.connected',unique_id='device1_connected',platform='cook4me',disabled_by=None)])
        self.states['sensor.cook4me_state']=NS(state='idle',attributes={'restored':True})
        self.states['binary_sensor.connected']=NS(state='on',attributes={})
        await self.settings.async_consolidate_entities()
        self.assertIsNone(self.registry.rows[1].disabled_by)
        self.assertFalse(self.settings.data['entitiesConsolidated'])

    def test_startup_metadata_and_reconnect_do_not_replay_steps(self):
        live=self.data(active=True,phase='cooking',variantFunctionalId='r',stepFunctionalId='s1',stepIndex=0)
        tracker=self.mod.CookingEvents(live)
        live['currentInstruction']='Stir'
        self.assertEqual(tracker.update(live),[])
        live['connected']=False;self.assertEqual(tracker.update(live),[('connection','offline')])
        self.assertEqual(tracker.update(live),[])
        live['connected']=True;self.assertEqual(tracker.update(live),[('connection','online')])
        self.assertEqual(tracker.update(live),[])
        tracker=self.mod.CookingEvents({})
        self.assertEqual(tracker.update(live),[])

    async def test_live_recipe_step_delayed_metadata_and_progress_dedupe(self):
        await self.save()
        await self.publish(variantFunctionalId='recipe1',recipeTitle='Salad',stepFunctionalId='s1',stepIndex=0,phase='preparation',active=True)
        self.assertEqual(self.hass.services.async_call.await_count,1)
        await self.publish(currentInstruction='Stir for 2 minutes')
        self.assertEqual(self.hass.services.async_call.await_count,2)
        for n in range(10):await self.publish(progress=n,remainingTime=100-n)
        self.assertEqual(self.hass.services.async_call.await_count,2)
        await self.publish(stepFunctionalId='s2',stepIndex=1,currentInstruction='Serve')
        self.assertEqual(self.hass.services.async_call.await_count,3)
        args=self.hass.services.async_call.call_args
        self.assertEqual(args.args[:2],('tts','speak'))
        self.assertEqual(args.args[2]['media_player_entity_id'],['media_player.kitchen'])
        self.assertEqual(args.args[2]['language'],'el_GR');self.assertIn('Βήμα 2',args.args[2]['message'])
        self.assertEqual(args.kwargs['context'].user_id,'alice');self.generate.assert_not_awaited()

    async def test_each_user_gets_own_language_and_speakers_and_shared_delivery_dedupes(self):
        await self.save();await self.save('bob')
        await self.publish(variantFunctionalId='recipe1',recipeTitle='Salad')
        self.assertEqual(self.hass.services.async_call.await_count,1)
        await self.save('bob',players=['media_player.living'],language='en_US')
        await self.publish(phase='cooking',active=True)
        self.assertEqual(self.hass.services.async_call.await_count,3)
        calls=self.hass.services.async_call.call_args_list
        self.assertEqual(calls[-1].args[2]['media_player_entity_id'],['media_player.living'])
        self.assertEqual(calls[-1].args[2]['message'],'Cooking')

    async def test_selected_ai_translates_before_tts_with_cache_and_no_fallback(self):
        prefs=await self.save(ai='ai_task.local')
        await self.manager.speak(self.users['alice'],prefs,'Stir for 2 minutes')
        self.assertEqual(self.hass.services.async_call.call_args.args[2]['message'],'Ανακατέψτε για 2 λεπτά')
        self.assertEqual(self.generate.call_args.kwargs['entity_id'],'ai_task.local')
        await self.manager.speak(self.users['alice'],prefs,'Stir for 2 minutes');self.assertEqual(self.generate.await_count,1)
        self.generate.return_value=NS(data={'text':'Cook for 3 minutes'})
        with self.assertRaises(ValueError):await self.manager.speak(self.users['alice'],prefs,'Cook for 2 minutes')
        self.assertEqual(self.hass.services.async_call.await_count,2)

    async def test_stale_step_or_disabled_preferences_after_slow_ai_is_not_spoken(self):
        await self.save(ai='ai_task.local')
        async def slow(**kw):
            self.bridge.data['stepFunctionalId']='newer'
            return NS(data={'text':'Ανακατέψτε για 2 λεπτά'})
        self.generate.side_effect=lambda *args,**kwargs:slow(**kwargs)
        # AsyncMock's side effect must itself be async to await it.
        async def generate(*args,**kwargs):return await slow(**kwargs)
        self.generate.side_effect=generate
        await self.publish(variantFunctionalId='r',stepFunctionalId='s1',currentInstruction='Stir for 2 minutes')
        self.hass.services.async_call.assert_not_awaited()
        self.assertEqual(self.manager.status['alice']['state'],'skipped')

    async def test_revoked_user_or_speaker_permission_never_controls_speakers(self):
        await self.save()
        self.users['alice'].is_active=False
        await self.publish(variantFunctionalId='r',recipeTitle='Salad')
        self.hass.services.async_call.assert_not_awaited()
        self.users['alice']=self.user('alice',{'media_player.kitchen'})
        await self.publish(phase='cooking',active=True)
        self.hass.services.async_call.assert_not_awaited()

    async def test_unload_cancels_pending_ai_and_unsubscribes(self):
        await self.save(ai='ai_task.local');self.manager.start()
        entered=asyncio.Event()
        async def pending(*a,**kw):entered.set();await asyncio.Event().wait()
        self.generate.side_effect=pending
        self.bridge.data.update(variantFunctionalId='r',recipeTitle='Salad');self.manager.on_update()
        await entered.wait();await self.manager.close()
        self.assertEqual(self.callbacks,[]);self.hass.services.async_call.assert_not_awaited()

    async def test_websocket_uses_authenticated_user_and_subscriptions_are_private(self):
        source=ast.parse((ROOT/'custom_components/cook4me/websocket_v32.py').read_text())
        nodes=[n for n in source.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name!='async_register']
        for node in nodes:node.decorator_list=[]
        self.bridge.device_settings=self.settings;self.bridge.announcements=self.manager
        replies=[];events=[]
        conn=NS(user=self.users['alice'],send_result=lambda *a:replies.append(a),send_event=lambda *a:events.append(a),subscriptions={})
        errors=[]
        ns={'legacy':NS(_bridge=lambda *a:self.bridge,_send_error=lambda *a:errors.append(a)),
            'device_access':self.settings_mod.device_access,'choices':self.settings_mod.choices}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual handlers','exec'),ns)
        await ns['ws_device_settings'](self.hass,conn,{'id':1,'entry_id':'entry1','settings':self.prefs()})
        self.assertFalse(errors);self.assertTrue(self.settings.for_user('alice')['enabled']);self.assertFalse(self.settings.for_user('bob')['enabled'])
        await ns['ws_announcement_subscribe'](self.hass,conn,{'id':2,'entry_id':'entry1'})
        self.manager.report('bob','speaking');self.assertEqual(events,[])
        self.manager.report('alice','speaking');self.assertEqual(events[0][0],2)
        conn.subscriptions[2]();self.manager.report('alice','done');self.assertEqual(len(events),1)
        conn.user=self.user('intruder',{'sensor.cook4me_state'})
        await ns['ws_device_settings'](self.hass,conn,{'id':3,'entry_id':'entry1'})
        self.assertEqual(len(errors),1)


if __name__=='__main__':unittest.main()
