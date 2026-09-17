"""The device link must satisfy HA's registry contract before entity registration."""
import ast
from dataclasses import dataclass
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from yarl import URL

ROOT=Path(__file__).resolve().parents[1]
PREFIX='cook4me_entity_setup_v73'
package=types.ModuleType(PREFIX);package.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[PREFIX]=package
NS=types.SimpleNamespace

@dataclass(frozen=True,kw_only=True)
class Description:
    key:str
    name:str=''
    icon:str=''
    entity_registry_enabled_default:bool=True
    native_unit_of_measurement:str|None=None
    device_class:str|None=None


class EntityRegistrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        class Entity:pass
        class SensorEntity(Entity):pass
        class BinarySensorEntity(Entity):pass
        self.patcher=patch.dict(sys.modules,{
            'homeassistant.helpers.entity':NS(Entity=Entity,DeviceInfo=dict),
            'homeassistant.components.sensor':NS(SensorEntity=SensorEntity,SensorEntityDescription=Description,SensorDeviceClass=NS(DURATION='duration',TIMESTAMP='timestamp')),
            'homeassistant.components.binary_sensor':NS(BinarySensorEntity=BinarySensorEntity,BinarySensorDeviceClass=NS(CONNECTIVITY='connectivity',UPDATE='update')),
            'homeassistant.const':NS(UnitOfTime=NS(SECONDS='s')),
        });self.patcher.start();self.addCleanup(self.patcher.stop)
        self.sensor=importlib.import_module(PREFIX+'.sensor');self.binary=importlib.import_module(PREFIX+'.binary_sensor')
        self.bridge=NS(device_uuid='appliance-1',entry=NS(entry_id='01ENTRY'),data={'connected':True,'phase':'cooking','stepIndex':2,'currentInstruction':'Stir'},available=True,can_accept_recipe=False,loaded_recipe=None)

    async def test_primary_entities_register_with_valid_internal_device_url_and_live_values(self):
        entities=[]
        entry=NS(runtime_data=self.bridge)
        await self.sensor.async_setup_entry(None,entry,entities.extend)
        await self.binary.async_setup_entry(None,entry,entities.extend)
        for entity in entities:
            # HA validates scheme AND host before creating an entity's device.
            url=URL(entity._attr_device_info['configuration_url'])
            self.assertIn(url.scheme,{'http','https','homeassistant'})
            self.assertTrue(url.host)
            self.assertEqual(url.host,'cook4me');self.assertEqual(url.query['device'],'01ENTRY')
        self.assertEqual(len(entities),17)
        for entity in entities:
            description=getattr(entity,'entity_description',None)
            self.assertTrue(description.entity_registry_enabled_default if description else getattr(entity,'_attr_entity_registry_enabled_default',True))
        summary=next(e for e in entities if e.key=='summary')
        connected=next(e for e in entities if e.key=='connected')
        self.assertTrue(summary.entity_description.entity_registry_enabled_default)
        self.assertNotEqual(getattr(connected,'_attr_entity_registry_enabled_default',True),False)
        self.assertEqual(summary.native_value,'cooking');self.assertTrue(connected.is_on)
        self.assertEqual(summary.extra_state_attributes['currentInstruction'],'Stir')
        self.assertEqual(summary.extra_state_attributes['stepIndex'],2)
        self.bridge.available=False;self.bridge.data['connected']=False
        self.assertEqual(summary.native_value,'offline');self.assertFalse(connected.is_on)

    async def test_setup_restores_registry_before_platforms_load(self):
        sequence=[]
        async def load():sequence.append('load')
        async def start():sequence.append('start')
        async def migrate():sequence.append('migrate')
        async def platforms(*args):sequence.append('entities')
        settings=NS(async_load=load,async_consolidate_entities=migrate)
        bridge=self.bridge;bridge.async_start=start
        announcements=NS(start=lambda:sequence.append('announcements'))
        hass=NS(data={},config_entries=NS(async_forward_entry_setups=platforms))
        node=next(n for n in ast.parse((ROOT/'custom_components/cook4me/__init__.py').read_text()).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup_entry')
        node.decorator_list=[];node.returns=None
        for arg in node.args.args:arg.annotation=None
        ns={'__package__':PREFIX,'Cook4MeBridge':lambda *a:bridge,'DOMAIN':'cook4me','DATA_BRIDGES':'bridges','PLATFORMS':['sensor','binary_sensor'],
            '_register_completion_listener':lambda b:None,'update_expiry_notification':lambda b:None,'register_daily_expiry_check':lambda b:None}
        with patch.dict(sys.modules,{PREFIX+'.device_settings':NS(DeviceSettings=lambda b:settings),PREFIX+'.announcements':NS(Announcements=lambda *a:announcements)}):
            exec(compile(ast.Module(body=[node],type_ignores=[]),'actual setup','exec'),ns)
            self.assertTrue(await ns['async_setup_entry'](hass,bridge.entry))
        self.assertLess(sequence.index('load'),sequence.index('migrate'))
        self.assertLess(sequence.index('migrate'),sequence.index('entities'))


if __name__=='__main__':unittest.main()
