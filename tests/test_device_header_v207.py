"""Production device snapshot and subscription with controlled HA registries."""
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'custom_components/cook4me/websocket_v32.py'
class Registry:
    def __init__(self): self.device=NS(id='dev-one',name='Cook4Me',name_by_user='Kitchen cooker')
    def async_get_device(self,*,identifiers):
        assert identifiers=={('cook4me','uuid-one')}
        return self.device
class Bus:
    def __init__(self): self.listeners=[]
    def async_listen(self,name,listener):
        assert name=='device_registry_updated';self.listeners.append(listener)
        return lambda:self.listeners.remove(listener)
    def fire(self,device_id):
        for fn in list(self.listeners):fn(NS(data={'device_id':device_id}))

registry=Registry()
ha=ModuleType('homeassistant');helpers=ModuleType('homeassistant.helpers');dr=ModuleType('homeassistant.helpers.device_registry')
dr.async_get=lambda hass:hass.registry
dr.EVENT_DEVICE_REGISTRY_UPDATED='device_registry_updated';helpers.device_registry=dr
sys.modules.update({'homeassistant':ha,'homeassistant.helpers':helpers,'homeassistant.helpers.device_registry':dr})
source=ast.parse(PATH.read_text())
methods=[]
for node in source.body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in {'_header_device','_device_snapshot','ws_device_state_subscribe'}:
        node=deepcopy(node);node.decorator_list=[];methods.append(node)
ns={'callback':lambda f:f,'DOMAIN':'cook4me','dr':dr}
exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),str(PATH),'exec'),ns)

class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass=NS(registry=Registry(),bus=Bus());self.listeners=[];self.allowed=True;self.events=[];self.errors=[]
        self.bridge=NS(hass=self.hass,device_uuid='uuid-one',entry=NS(entry_id='one',title='Config entry'),data={'phase':'idle','secret':'never sent'},available=False,can_accept_recipe=False,loaded_recipe=None)
        self.bridge.async_add_listener=lambda fn:(self.listeners.append(fn) or (lambda:self.listeners.remove(fn)))
        self.connection=NS(user=NS(id='user'),subscriptions={},send_event=lambda i,s:self.events.append(deepcopy(s)),send_result=lambda *a:None)
        ns['legacy']=NS(_bridge=lambda *a:self.bridge,_send_error=lambda c,m,e:self.errors.append(str(e)))
        ns['device_read_access']=lambda *a:self.allowed
    async def subscribe(self): await ns['ws_device_state_subscribe'](self.hass,self.connection,{'id':1,'entry_id':'one'})
    def test_user_name_wins_and_no_extra_registry_data_leaks(self):
        s=ns['_device_snapshot'](self.bridge)
        self.assertEqual(s['state']['deviceName'],'Kitchen cooker')
        self.assertNotIn('secret',s['state']);self.assertNotIn('device_id',s['state'])
        self.assertFalse(s['connected'])
    def test_name_fallbacks(self):
        self.hass.registry.device.name_by_user='';self.assertEqual(ns['_device_snapshot'](self.bridge)['state']['deviceName'],'Cook4Me')
        self.hass.registry.device=None;self.assertEqual(ns['_device_snapshot'](self.bridge)['state']['deviceName'],'Config entry')
    async def test_rename_without_cooker_telemetry_updates_name(self):
        await self.subscribe();self.hass.registry.device.name_by_user='Renamed cooker';self.hass.bus.fire('dev-one')
        self.assertEqual(self.events[-1]['state']['deviceName'],'Renamed cooker');self.assertEqual(len(self.events),2)
    async def test_other_device_registry_changes_do_not_send_events(self):
        await self.subscribe();self.hass.bus.fire('unrelated');self.assertEqual(len(self.events),1)
    async def test_unauthorized_user_gets_no_name_or_subscription(self):
        self.allowed=False;await self.subscribe();self.assertEqual(self.events,[]);self.assertEqual(self.listeners,[]);self.assertEqual(self.hass.bus.listeners,[]);self.assertTrue(self.errors)
    async def test_permission_revocation_clears_name_and_removes_both_listeners(self):
        await self.subscribe();self.allowed=False;self.hass.bus.fire('dev-one')
        self.assertFalse(self.events[-1]['accessible']);self.assertEqual(self.events[-1]['state'],{})
        self.assertEqual(self.listeners,[]);self.assertEqual(self.hass.bus.listeners,[])
    async def test_unsubscribe_is_idempotent_and_stops_both_event_sources(self):
        await self.subscribe();stop=self.connection.subscriptions[1];stop();stop();self.hass.bus.fire('dev-one')
        self.assertEqual(self.listeners,[]);self.assertEqual(self.hass.bus.listeners,[]);self.assertEqual(len(self.events),1)
    async def test_removed_registry_device_drops_old_custom_name(self):
        await self.subscribe();self.hass.registry.device=None;self.hass.bus.fire('dev-one')
        self.assertEqual(self.events[-1]['state']['deviceName'],'Config entry')
    async def test_live_telemetry_keeps_current_name(self):
        await self.subscribe();self.bridge.data['phase']='cooking';self.bridge.available=True;self.listeners[0]()
        self.assertEqual(self.events[-1]['state']['phase'],'cooking');self.assertEqual(self.events[-1]['state']['deviceName'],'Kitchen cooker')

if __name__=='__main__':unittest.main()
