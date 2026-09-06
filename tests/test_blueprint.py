"""The blueprint's own invariants. These fail loudly so an edited weight cannot slip through."""

from ccarp import blueprint as bp_mod


def test_real_blueprint_is_sound(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert bp_mod.check(bp) == []


def test_weights_sum_to_one(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert abs(sum(d.weight for d in bp.domains) - 1.0) < 1e-9


def test_items_sum_to_63_and_match_rounding(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert bp.total_items == 63
    for d in bp.domains:
        assert d.items == round(d.weight * 63), d.id


def test_thirty_eight_objectives(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert len(bp.objective_ids) == 38


def test_bad_weight_is_caught(tmp_blueprint):
    _, mutate = tmp_blueprint
    path = mutate(lambda raw: raw["domains"][0].__setitem__("weight", 0.18))
    errors = bp_mod.check(bp_mod.load(path))
    assert any("weights sum" in e for e in errors)


def test_bad_item_count_is_caught(tmp_blueprint):
    _, mutate = tmp_blueprint
    path = mutate(lambda raw: raw["domains"][0].__setitem__("items", 12))
    errors = bp_mod.check(bp_mod.load(path))
    assert any("sum to 64" in e for e in errors)
    assert any("d1: items=12" in e for e in errors)


def test_objective_in_wrong_domain_is_caught(tmp_blueprint):
    _, mutate = tmp_blueprint
    path = mutate(lambda raw: raw["domains"][0]["objectives"][0].__setitem__("id", "2.9"))
    errors = bp_mod.check(bp_mod.load(path))
    assert any("does not belong to domain d1" in e for e in errors)
