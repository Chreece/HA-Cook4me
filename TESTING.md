# v0.3.0 test checklist

1. Restart Home Assistant and verify Cook4Me config entry loads.
2. Confirm sidebar contains **Cook4Me**.
3. Confirm default entities include `Connected` and merged `State`.
4. Open Recipe Hub > Official recipes and search a known recipe.
5. Open recipe details and verify ingredients/steps load.
6. With the Cook4Me at an empty/home state, send an official recipe and verify it appears on the appliance.
7. Leave a recipe loaded and verify another send is blocked before MQTT publish.
8. Set vegetarian/vegan/pescatarian and verify blocked recipes cannot be sent.
9. Add an allergy (e.g. dairy/milk) and verify matching recipes are blocked.
10. Populate pantry/fridge items and verify For my fridge shows coverage and missing ingredients.
11. Create a manual recipe and verify it appears under My recipes as cook-along only.
12. Configure/select a Home Assistant Conversation AI agent, generate a recipe, and verify it is stored only after profile validation.
13. Leave the panel open and verify live Cook4Me header state refreshes without erasing text being typed into forms.
