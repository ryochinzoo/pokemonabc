from __future__ import annotations

import collections
import gzip
import json
import math
import pickle
import struct
from pathlib import Path

import policy_features as pf
from strategic_policy import agent as strategic_agent

# Kaggle executes submitted source with ``exec`` and may not define __file__.
# Resolve the packaged directory without assuming normal module import semantics.
if "__file__" in globals():
    BASE = Path(globals()["__file__"]).resolve().parent
else:
    _base_candidates = (Path("/kaggle_simulations/agent"), Path.cwd())
    BASE = next(
        (candidate for candidate in _base_candidates
         if (candidate / "models/policy_ensemble.bin.gz").is_file()),
        Path.cwd(),
    )
DECK = list(pf.DECK)

with gzip.open(BASE / "models/feature_schema.pkl.gz", "rb") as f:
    SCHEMA = pickle.load(f)
INTENT_TO_ID = {
    str(k): int(v)
    for k, v in json.loads((BASE / "final_schema.json").read_text(encoding="utf-8"))["intent_to_id"].items()
}

_RECORD = struct.Struct("<hBBBee")

def _load_ensemble(path: Path):
    raw = gzip.decompress(path.read_bytes())
    if raw[:4] != b"PTC2":
        raise ValueError("Unsupported policy asset")
    pos = 4
    model_count = raw[pos]
    pos += 1
    models = {}
    for _ in range(model_count):
        name_len = raw[pos]
        pos += 1
        name = raw[pos : pos + name_len].decode("ascii")
        pos += name_len
        tree_count = struct.unpack_from("<H", raw, pos)[0]
        pos += 2
        trees = []
        for _ in range(tree_count):
            node_count = raw[pos]
            pos += 1
            nodes = []
            for _ in range(node_count):
                nodes.append(_RECORD.unpack_from(raw, pos))
                pos += _RECORD.size
            trees.append(nodes)
        models[name] = trees
    if pos != len(raw):
        raise ValueError("Policy asset has trailing bytes")
    return models

MODELS = _load_ensemble(BASE / "models/policy_ensemble.bin.gz")
_HISTORY = []


def _reset():
    global _HISTORY
    _HISTORY = []


def _route(context: int):
    if context == 0:
        return "main"
    if context == 7:
        return "c7"
    if context in (3, 5, 8):
        return "low"
    if context in (13, 15, 16, 21, 22, 40, 43):
        return "mid"
    if context in (1, 2, 4, 27, 30, 34, 37, 38, 41):
        return "easy"
    return None


def _transform(row):
    maps = SCHEMA["category_maps"]
    values = []
    for name in SCHEMA["features"]:
        value = row.get(name, 0)
        if name in maps:
            try:
                value = value.item()
            except Exception:
                pass
            value = maps[name].get(value, -1)
        try:
            values.append(float(value))
        except Exception:
            values.append(float("nan"))
    return values


def _score(values, trees):
    total = 0.0
    for nodes in trees:
        node_index = 0
        while True:
            feature, flags, left, right, threshold, leaf_value = nodes[node_index]
            if flags & 1:
                total += leaf_value
                break
            value = values[feature]
            if math.isnan(value):
                node_index = left if flags & 2 else right
            else:
                node_index = left if value <= threshold else right
    return total


def _legal(action, select, option_count):
    minimum = int(select.get("minCount", 0) or 0)
    maximum = int(select.get("maxCount", 0) or 0)
    return (
        minimum <= len(action) <= maximum
        and len(action) == len(set(action))
        and all(isinstance(index, int) and 0 <= index < option_count for index in action)
    )


def _model_action(obs):
    select = obs.get("select") or {}
    options = select.get("option") or []
    option_count = len(options)
    selected_count = min(option_count, int(select.get("maxCount", 0) or 0))
    if selected_count <= 0:
        return [], []

    context = int(select.get("context", -1) if select.get("context") is not None else -1)
    model_name = _route(context)
    if model_name is None:
        return None, [pf.semantic(obs, option) for option in options]

    state = pf.base_state(obs, [])
    semantics = [pf.semantic(obs, option) for option in options]
    semantic_keys = [
        (item["type"], item["source_id"], item["target_id"], item["attack_id"], item["area"], item["inplay_area"])
        for item in semantics
    ]
    counts = collections.Counter(semantic_keys)
    seen = collections.Counter()
    previous = {}
    scores = []

    for position, (option, item, key) in enumerate(zip(options, semantics, semantic_keys)):
        duplicate_rank = seen[key]
        seen[key] += 1
        row, _ = pf.option_row(obs, state, option, position, item, counts[key], duplicate_rank)
        values = _transform(row)
        values.extend(
            [
                float(INTENT_TO_ID.get(pf.intent_text(item), -1)),
                float(previous.get("type", -1)),
                float(previous.get("source_id", 0)),
                float(previous.get("target_id", 0)),
                float(previous.get("attack_id", 0)),
                0.0,
            ]
        )
        scores.append(_score(values, MODELS[model_name]))

    order = sorted(range(option_count), key=lambda index: (-scores[index], index))
    return sorted(order[:selected_count]), semantics


def agent(obs):
    global _HISTORY
    if not obs or obs.get("select") is None:
        _reset()
        try:
            strategic_agent(obs)
        except Exception:
            pass
        return list(DECK)

    select = obs.get("select") or {}
    options = select.get("option") or []
    option_count = len(options)

    try:
        fallback = strategic_agent(obs)
    except Exception:
        fallback = []

    try:
        action, semantics = _model_action(obs)
    except Exception:
        action, semantics = None, [pf.semantic(obs, option) for option in options]

    chosen = fallback if action is None else action
    if not _legal(chosen, select, option_count):
        chosen = fallback
    if not _legal(chosen, select, option_count):
        chosen = list(range(min(option_count, int(select.get("maxCount", 0) or 0))))

    _HISTORY = (_HISTORY + [semantics[index] for index in chosen if 0 <= index < option_count])[-8:]
    return chosen
