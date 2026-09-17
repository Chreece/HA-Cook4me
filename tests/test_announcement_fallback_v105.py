"""AI outages cannot suppress deterministic speech or bypass delivery checks."""
import asyncio
from copy import deepcopy
import unittest

import test_device_announcements_v72 as previous
NS = previous.NS


class AnnouncementFallbackTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = previous.AnnouncementTests.asyncSetUp
    user = previous.AnnouncementTests.user
    update_entity = previous.AnnouncementTests.update_entity
    add_listener = previous.AnnouncementTests.add_listener
    data = previous.AnnouncementTests.data
    prefs = previous.AnnouncementTests.prefs
    save = previous.AnnouncementTests.save
    publish = previous.AnnouncementTests.publish

    async def test_unavailable_saved_ai_can_be_saved_enabled_and_tested(self):
        await self.save(ai='ai_task.local')
        self.ai.available = False
        prefs = await self.settings.async_save(self.users['alice'], {'steps': False})
        self.assertEqual(prefs['ai'], 'ai_task.local')
        self.assertTrue(prefs['enabled'])
        await self.manager.test(self.users['alice'])
        self.generate.assert_not_awaited()
        call = self.hass.services.async_call.call_args
        self.assertEqual(call.args[2]['message'], self.mod.PHRASES['el']['test'])
        self.assertEqual(call.args[2]['language'], 'el_GR')
        self.assertEqual(call.kwargs['context'].user_id, 'alice')
        self.assertEqual(self.manager.status['alice']['state'], 'done')

    async def test_fixed_state_and_test_messages_do_not_need_available_ai(self):
        await self.save(ai='ai_task.local')
        await self.manager.test(self.users['alice'])
        await self.publish(phase='cooking', active=True)
        self.generate.assert_not_awaited()
        self.assertEqual(self.hass.services.async_call.call_args.args[2]['message'], 'Μαγείρεμα')

    async def test_unavailable_ai_uses_original_recipe_and_steps_then_recovers(self):
        await self.save(ai='ai_task.local')
        self.ai.available = False
        text = 'Stir 2 times. Cook for 5 minutes at 100°C.'
        await self.publish(variantFunctionalId='r', recipeTitle='Porridge', stepFunctionalId='s1', stepIndex=0, currentInstruction=text)
        message = self.hass.services.async_call.call_args.args[2]['message']
        self.assertIn('Η συνταγή φορτώθηκε: Porridge', message)
        self.assertIn('Βήμα 1. '+text, message)
        self.generate.assert_not_awaited()
        self.ai.available = True
        self.generate.return_value = NS(data={'text': 'Βήμα 2. Σερβίρετε 4 μερίδες.'})
        await self.publish(stepFunctionalId='s2', stepIndex=1, currentInstruction='Serve 4 portions.')
        self.assertEqual(self.generate.await_count, 1)
        self.assertEqual(self.hass.services.async_call.call_args.args[2]['message'], 'Βήμα 2. Σερβίρετε 4 μερίδες.')

    async def test_ai_failure_timeout_and_invalid_text_fall_back_without_caching(self):
        prefs = await self.save(ai='ai_task.local')
        original = deepcopy(prefs)
        for failure in (RuntimeError('provider offline'), TimeoutError('provider timeout'), {'text': 'Cook for 9 minutes'}, {'text': ''}):
            self.generate.side_effect = failure if isinstance(failure, Exception) else None
            self.generate.return_value = NS(data=failure)
            await self.manager.speak(self.users['alice'], prefs, 'Cook for 2 minutes')
            self.assertEqual(self.hass.services.async_call.call_args.args[2]['message'], 'Cook for 2 minutes')
            self.assertEqual(self.manager.status['alice']['state'], 'done')
            self.assertEqual(self.manager.cache, {})
            self.assertEqual(prefs, original)

    async def test_failed_translation_rechecks_stale_steps_and_speaker_permissions(self):
        prefs = await self.save(ai='ai_task.local')
        async def stale(*args, **kwargs):
            self.bridge.data['stepFunctionalId'] = 'newer'
            raise RuntimeError('provider failed')
        self.generate.side_effect = stale
        await self.publish(variantFunctionalId='r', recipeTitle='Soup', stepFunctionalId='s1', currentInstruction='Cook for 2 minutes')
        self.hass.services.async_call.assert_not_awaited()
        async def revoke(*args, **kwargs):
            self.users['alice'] = self.user('alice', {'media_player.kitchen'})
            raise RuntimeError('provider failed')
        self.generate.side_effect = revoke
        await self.manager.speak(self.users['alice'], prefs, 'Cook for 2 minutes')
        self.hass.services.async_call.assert_not_awaited()

    async def test_cancellation_never_speaks_fallback_and_tts_failures_remain_errors(self):
        prefs = await self.save(ai='ai_task.local')
        self.generate.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.manager.speak(self.users['alice'], prefs, 'Cook for 2 minutes')
        self.hass.services.async_call.assert_not_awaited()
        self.ai.available = False
        self.tts.available = False
        with self.assertRaisesRegex(ValueError, 'TTS'):
            await self.manager.speak(self.users['alice'], prefs, 'Cook for 2 minutes')
        self.hass.services.async_call.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
