# Contributing

Contributions are welcome through issues and pull requests.

## Development

Use Python 3.13 in a virtual environment. Do not use the system Python for project tooling.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m unittest discover -s tests -v
python scripts/version.py validate
```

## Safety and privacy

Never commit KRUPS credentials, tokens, Cognito credentials, AWS IoT signed URLs, device UUIDs, or unsanitized logs. Recipe-send changes must retain the existing state and dietary/allergy safety gates.

## Versioning

HA-Cook4me uses `YYYY.M.D.BUILD`, for example `2026.9.6.1`. Increment `BUILD` for multiple releases on the same date; reset it to `1` on a new date.
