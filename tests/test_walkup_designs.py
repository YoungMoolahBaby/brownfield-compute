"""The walk-up's two designs (`brownfield.designs`, pass 3g step 11a): one switch names the bid set's
design, each design keeps its own files, and step 10 prices the network design whichever the bid
set's. Only the last test reads a file: Addendum 5's model, which step 10 is pinned to."""
import pytest

from brownfield import OUT_DIR, ROOT, designs
from brownfield.params import check_params, load_params, values


@pytest.fixture(scope="module")
def params():
    return load_params()


def test_the_switch_names_the_design(params):
    sw = params[designs.KEY]
    assert sw.conf == "decision" and not sw.varies and sw.source.strip()
    assert not [x for x in check_params(params) if x.startswith(designs.KEY)]
    net, edge = designs.network(params), designs.edge(params)
    assert designs.name(values(net)) == "network" and designs.name(values(edge)) == "edge"
    assert designs.name(net) == "network"  # the Param dict reads the same
    assert designs.name(values(designs.network(edge))) == "network"
    # Only the switch differs, and it stays fixed: the draws don't vary it.
    assert {k for k in params if values(net)[k] != values(edge)[k]} == {designs.KEY}
    assert not net[designs.KEY].varies and not edge[designs.KEY].varies


def test_what_each_design_has(params):
    net, edge = values(designs.network(params)), values(designs.edge(params))
    assert designs.floors(net) and not designs.floors(edge)
    assert (designs.plant_heat(net), designs.plant_heat(edge)) == ("dc", "air")
    assert designs.pv(net) and designs.prv(net) and not designs.pv(edge) and not designs.prv(edge)
    assert (designs.issue(net), designs.issue(edge)) == ("addendum-10", "addendum-11")


def test_each_design_keeps_its_own_files(params):
    net, edge = designs.paths(values(designs.network(params))), designs.paths(values(designs.edge(params)))
    assert set(net) == set(edge) and all(net[k] != edge[k] for k in net)
    # The network design's are where they always were, so its routes needn't be routed again.
    assert net["requests"] == OUT_DIR / "pass3" / "route-requests.json" and net["routes"] == OUT_DIR / "pass3" / "routes.json"
    assert net["sizes"] == ROOT / "data" / "route_sizes.json" and net["services"] == OUT_DIR / "pass3" / "services"


def test_step_10_prices_the_network_design_whatever_the_bid_sets(params, monkeypatch):
    from brownfield import baseline, cli, ranges

    with pytest.raises(SystemExit):
        baseline.run(p=values(designs.edge(params)))
    # The commands take the network design even when the params name the edge design.
    if not (OUT_DIR / "pass3" / designs.MODEL).exists():
        pytest.skip("Addendum 5's model isn't written (forge `apartment-json addendum-5`)")
    monkeypatch.setattr(cli, "load_params", lambda: designs.edge(params))
    p10, P10, _ = cli._step10()
    assert designs.name(p10) == "network" and designs.name(P10) == "network"
    # The workers rebuild each draw on the central values `ranges.draws` gives them: the design rides
    # there, fixed, and never among the inputs drawn.
    base, vary = ranges.draws(p10, 3, 7)
    assert designs.name(base) == "network" and designs.KEY not in vary


def test_the_edge_designs_own_inputs_dont_shift_step_10s_draws(params):
    """A varied input shifts every later draw of step 10's Monte Carlo (the network design's): the
    inputs only the edge design reads stay fixed until 10i draws them."""
    edge_only = [k for k in params if k.startswith("systems.co2_plant.")
                 or k in ("systems.electrical.bath_heater_va", "systems.minisplit.room_least_cfm", designs.KEY)]
    assert edge_only and not [k for k in edge_only if params[k].varies]
