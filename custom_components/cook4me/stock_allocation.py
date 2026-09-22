"""Allocate shared physical lots without avoidable shortages or duplicated capacity."""
from collections import deque
from copy import deepcopy

from .inventory import (_lot_sort_key, _quantity, _unit_token, _UNIT_SCALE,
                        convert_amount, ingredient_identities, inventory_identity,
                        stock_for_ingredient)

_EPSILON = 1e-9


def _base_unit(unit):
    token = _unit_token(unit) or "pcs"
    group = _UNIT_SCALE.get(token, (token, 1))[0]
    return {"mass": "g", "volume": "ml", "count": "pcs"}.get(group, token)


def allocate_stock(stock, requests):
    """Return one allocated view per request; persistent inventory is never expanded.

    Residual edges can reassign a flexible lot when another ingredient has no
    alternative. Compatible measurements use a common base unit. FEFO controls
    the deterministic lot order, while satisfying all possible demand takes
    precedence over spending an early flexible lot on an unconstrained request.
    """
    views = [stock_for_ingredient(stock, request) for request in requests]
    wanted_identities = {
        identity
        for request in requests
        for identity in (
            set(request.get("identities") or [])
            | ingredient_identities(request)
            | ({request.get("identity")} if request.get("identity") else set())
        )
        if identity
    }
    lots = []
    for row in stock:
        for lot in row.get("lots") or []:
            identities = {
                inventory_identity(row),
                *(
                    identity
                    for link in lot.get("ingredientLinks") or []
                    for identity in ingredient_identities(link)
                ),
            }
            if not identities & wanted_identities:
                continue
            base = _base_unit(row.get("unit", ""))
            capacity = convert_amount(lot.get("quantity"), row.get("unit", ""), base)
            if capacity is not None and capacity > _EPSILON:
                lots.append((row, lot, identities, base, capacity))
    lots.sort(key=lambda item: _lot_sort_key(item[1]))

    # source -> physical lot -> recipe requirement -> sink. Reverse capacities
    # allow an earlier assignment to move to an alternative physical package.
    source = 0
    lot_start = 1
    request_start = lot_start + len(lots)
    sink = request_start + len(requests)
    graph = [[] for _ in range(sink + 1)]

    def edge(start, end, capacity):
        forward = [end, len(graph[end]), capacity]
        backward = [start, len(graph[start]), 0.0]
        graph[start].append(forward)
        graph[end].append(backward)
        return forward

    supplies = [edge(source, lot_start + index, item[4]) for index, item in enumerate(lots)]
    eligible = {}
    assignments = [[] for _ in requests]
    for index, (request, view) in enumerate(zip(requests, views)):
        amount = _quantity(request.get("quantity"))
        if not request.get("consume", True) or amount is None or view is None or view.get("unlimited"):
            continue
        unit = request.get("unit", "")
        if convert_amount(view.get("quantity"), view.get("unit", ""), unit) is None:
            continue  # Keep unknown stock and incompatible dimensions explicit.
        base = _base_unit(unit)
        demand = convert_amount(amount, unit, base)
        if demand is None:
            continue
        eligible[index] = (unit, base)
        edge(request_start + index, sink, demand)
        wanted = (
            set(request.get("identities") or [])
            | ingredient_identities(request)
            | ({request.get("identity")} if request.get("identity") else set())
        )
        for lot_index, (_, lot, identities, lot_base, capacity) in enumerate(lots):
            if not (wanted & identities) or lot_base != base or request.get("lotId") and request["lotId"] != lot.get("id"):
                continue
            forward = edge(lot_start + lot_index, request_start + index, min(capacity, demand))
            assignments[index].append((lot_index, forward))

    # Iterative augmenting paths avoid recursion limits for large inventories.
    while True:
        parents = {source: None}
        pending = deque([source])
        while pending and sink not in parents:
            node = pending.popleft()
            for index, (target, _, capacity) in enumerate(graph[node]):
                if capacity > _EPSILON and target not in parents:
                    parents[target] = (node, index)
                    pending.append(target)
        if sink not in parents:
            break
        amount = float('inf')
        node = sink
        while node != source:
            parent, index = parents[node]
            amount = min(amount, graph[parent][index][2])
            node = parent
        node = sink
        while node != source:
            parent, index = parents[node]
            forward = graph[parent][index]
            forward[2] -= amount
            graph[node][forward[1]][2] += amount
            node = parent

    for index, (unit, base) in eligible.items():
        allocated, free = [], 0.0
        for lot_index, forward in assignments[index]:
            row, lot, _, _, _ = lots[lot_index]
            amount = graph[forward[0]][forward[1]][2]
            free += supplies[lot_index][2]
            if amount > _EPSILON:
                allocated.append({**deepcopy(lot), "quantity": convert_amount(amount, base, unit),
                                  "sourceIdentity": inventory_identity(row)})
        quantity = sum(lot['quantity'] for lot in allocated)
        views[index] = {**views[index], "unit": unit, "lots": allocated, "quantity": round(quantity, 9),
                        "availableQuantity": round(quantity + (convert_amount(free, base, unit) or 0), 9)}
    return views
