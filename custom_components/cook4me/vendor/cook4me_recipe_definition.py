"""Public recipe structure evidence; no account, authentication or response headers."""


def _rows(value):
    return value if isinstance(value, list) else []


def _key(value):
    if isinstance(value, dict):
        value = value.get('key') or value.get('functionalId') or value.get('id')
    return str(value)[:120] if isinstance(value, (str, int)) else None


def definition_summary(root):
    """Describe provider structure without claiming firmware compatibility."""
    raw_steps = root.get('steps')
    steps = []
    for index, step in enumerate(raw_steps if isinstance(raw_steps, list) else []):
        if not isinstance(step, dict):
            steps.append({'index': index, 'invalid': True})
            continue
        sequences = []
        for sequence in _rows(step.get('sequences')):
            if not isinstance(sequence, dict):
                sequences.append({'invalid': True})
                continue
            operations = []
            for operation in _rows(sequence.get('operations')):
                if not isinstance(operation, dict):
                    operations.append({'invalid': True})
                    continue
                parameters = operation.get('parameters')
                operations.append({'program': _key(operation.get('program')),
                    'parameterKeys': [_key(row) for row in parameters if isinstance(row, dict)] if isinstance(parameters, list) else [],
                    'nullFields': sorted(key for key in ('program', 'parameters') if operation.get(key) is None)})
            sequences.append({'applianceGroup': _key(sequence.get('applianceGroup')), 'operations': operations})
        steps.append({'index': index, 'id': _key(step.get('fid') or step.get('identifier')),
            'type': _key(step.get('type')), 'applicationText': bool(step.get('applicationDescription')),
            'applianceText': bool(step.get('applianceDescription')), 'sequences': sequences})
    groups = []
    for group in _rows(root.get('applianceGroups')):
        if isinstance(group, dict):
            key = _key(group.get('reference') or group)
            if key:
                groups.append(key)
    return {'schemaVersion': 1, 'format': 'mobile', 'applianceGroups': groups,
            'rawStepCount': len(raw_steps) if isinstance(raw_steps, list) else None,
            'steps': steps, 'firmwareCompatibility': 'unknown'}
