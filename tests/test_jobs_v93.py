"""Focused checks for the v93 progress window's real cancellation backend."""
import ast
import asyncio
import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/cook4me'
spec = importlib.util.spec_from_file_location('jobs_v93', ROOT / 'job_runtime.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
JobRegistry = module.JobRegistry


def functions(filename, names, namespace):
    nodes = [node for node in ast.parse((ROOT / filename).read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), filename, 'exec'), namespace)
    return namespace


class JobTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.registry = JobRegistry()
        self.results, self.errors = [], []
        self.connection = NS(user=NS(id='alice'), send_result=lambda *args:self.results.append(args),
                             send_error=lambda *args:self.errors.append(args))
        self.hass = NS(data={'cook4me':{'ui_jobs':{'registry':self.registry, 'commands':{}}}})
        self.api = functions('websocket_v36.py', ['ws_job_run', 'ws_job_cancel'], {
            'asyncio':asyncio, 'DOMAIN':'cook4me',
            'legacy':NS(_send_error=lambda connection, msg, exc:connection.send_error(msg['id'], 'error', str(exc)))})

    async def test_cancel_stops_running_job_and_prevents_late_write(self):
        started = asyncio.Event()
        async def command(hass, connection, msg):
            started.set()
            await asyncio.Event().wait()
            self.fail('Cancelled job committed a late result')
        self.hass.data['cook4me']['ui_jobs']['commands']['cook4me/test'] = (lambda x:x, command)
        task = asyncio.create_task(self.api['ws_job_run'](self.hass, self.connection,
            {'id':1,'job_id':'one','request':{'type':'cook4me/test'}}))
        await started.wait()
        await self.api['ws_job_cancel'](self.hass, self.connection, {'id':2,'job_id':'one'})
        await asyncio.wait_for(task, 1)
        self.assertEqual(self.errors, [(1, 'job_cancelled', 'Job cancelled')])
        self.assertEqual(self.results, [(2, {'cancelled':True,'requestsStopped':1})])
        self.assertFalse(next(iter(self.registry.jobs.values()))['tasks'])

    async def test_queued_cancellation_releases_lane_for_next_job(self):
        lock, waiting = asyncio.Lock(), asyncio.Event()
        await lock.acquire()
        async def queued():
            async with self.registry.run(self.connection, 'queued'):
                waiting.set()
                async with lock:
                    self.fail('Cancelled queued job ran')
        task = asyncio.create_task(queued()); await waiting.wait()
        self.registry.cancel(self.connection, 'queued')
        with self.assertRaises(asyncio.CancelledError):
            await task
        lock.release()
        async with self.registry.run(self.connection, 'next'):
            await asyncio.wait_for(lock.acquire(), 1)
            lock.release()

    async def test_cancellation_is_connection_scoped_even_for_same_user_and_job_id(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def work():
            async with self.registry.run(self.connection, 'same'):
                started.set(); await release.wait()
        task = asyncio.create_task(work()); await started.wait()
        for user in ['alice', 'bob']:
            other = NS(user=NS(id=user))
            self.assertEqual(self.registry.cancel(other, 'same'), 0)
        self.assertFalse(task.done());release.set();await task

    async def test_cancel_before_start_and_between_batches_blocks_future_requests(self):
        self.registry.cancel(self.connection, 'early')
        with self.assertRaises(asyncio.CancelledError):
            async with self.registry.run(self.connection, 'early'):
                self.fail('Pre-cancelled job started')
        async with self.registry.run(self.connection, 'batch'):
            pass
        self.registry.cancel(self.connection, 'batch')
        with self.assertRaises(asyncio.CancelledError):
            async with self.registry.run(self.connection, 'batch'):
                self.fail('Next batch started after cancellation')

    async def test_original_schema_authorization_and_response_id_are_preserved(self):
        validated = []
        def schema(msg):
            validated.append(msg.copy())
            if msg.get('extra'):
                raise ValueError('extra keys not allowed')
            return msg
        async def guarded(hass, connection, msg):
            if connection.user.id != 'admin':
                raise ValueError('not authorized')
            connection.send_result(msg['id'], 'ok')
        self.hass.data['cook4me']['ui_jobs']['commands']['cook4me/guarded'] = (schema, guarded)
        request = {'type':'cook4me/guarded', 'id':999}
        await self.api['ws_job_run'](self.hass, self.connection, {'id':3,'job_id':'secure','request':request})
        self.assertEqual(validated[0]['id'], 3)
        self.assertIn('not authorized', self.errors[-1][2]);self.assertEqual(self.results, [])
        await self.api['ws_job_run'](self.hass, self.connection, {'id':4,'job_id':'secure','request':{**request,'extra':1}})
        self.assertIn('extra keys', self.errors[-1][2])
        await self.api['ws_job_run'](self.hass, self.connection, {'id':5,'job_id':'secure','request':{'type':'homeassistant/restart'}})
        self.assertEqual(self.errors[-1][1], 'job_unsupported')

    def test_registration_never_unwraps_outer_permission_wrappers(self):
        async def async_handler(*args): pass
        def scheduled(*args): pass
        scheduled.__wrapped__ = async_handler
        scheduled._ws_command = 'cook4me/safe'
        scheduled._ws_schema = lambda x:x
        def admin_guard(*args): pass
        admin_guard.__wrapped__ = scheduled
        admin_guard._ws_command = 'cook4me/admin'
        admin_guard._ws_schema = lambda x:x
        self.hass.data['websocket_api'] = {'cook4me/safe':(scheduled, lambda x:x), 'cook4me/admin':(admin_guard, lambda x:x), 'homeassistant/other':(scheduled, lambda x:x)}
        register = functions('websocket_v36.py', ['async_register'], {
            'inspect':inspect, 'WS_DOMAIN':'websocket_api',
            '__package__':'cook4me', 'DOMAIN':'cook4me', 'JobRegistry':JobRegistry,
            'websocket_api':NS(async_register_command=lambda *args:None), 'ws_job_run':None,'ws_job_cancel':None})
        register['async_register'](self.hass)
        self.assertEqual(set(self.hass.data['cook4me']['ui_jobs']['commands']), {'cook4me/safe'})


if __name__ == '__main__':
    unittest.main()
