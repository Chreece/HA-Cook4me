# GitHub repository setup

Repository name: `HA-Cook4me`

Recommended description:
> Home Assistant integration for KRUPS/Tefal Cook4Me with cloud monitoring, Recipe Hub, pantry/diet recommendations and AI-assisted cook-along recipes.

Recommended topics:
- home-assistant
- homeassistant
- hacs
- custom-integration
- cook4me
- cookeo
- krups
- tefal
- recipe
- smart-home

The repository must be public for normal HACS use.

After creating it, push this tree and create the first release tag:

```bash
git init
git add .
git commit -m "HA-Cook4me 2026.9.6.1"
git branch -M main
git remote add origin git@github.com:Chreece/HA-Cook4me.git
git push -u origin main
git tag 2026.9.6.1
git push origin 2026.9.6.1
```

The release workflow creates `HA-Cook4me.zip` and publishes the GitHub Release automatically.
