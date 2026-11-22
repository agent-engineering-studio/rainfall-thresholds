from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from taratura import api

from rainfall_thresholds import ITALICA_T5


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TARATURA_ENTE", "Comune di Prova")
    monkeypatch.setenv("TARATURA_REGIONE", "Liguria")
    return TestClient(api.app)


def test_the_catalogue_is_e_italica() -> None:
    assert len(api.catalogo()) == 5974


def test_config_names_the_body_and_the_rule(client: TestClient) -> None:
    c = client.get("/api/config").json()
    assert c["ente"] == "Comune di Prova" and c["regione"] == "Liguria"
    assert "non è un'allerta" in c["regola"]
    assert c["bollettino"].startswith("https://rischi.protezionecivile.gov.it")
    assert "Molise" in c["macroregioni"]["central"]


def test_an_unknown_region_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARATURA_REGIONE", "Bavaria")
    assert TestClient(api.app).get("/api/config").json()["regione"] is None


def test_the_whole_catalogue_gives_the_national_t5(client: TestClient) -> None:
    r = client.post("/api/taratura", json={"percentile": 5}).json()
    assert r["frane"] == 5974
    t = ITALICA_T5["italy"]
    assert r["soglia"]["alpha"] == pytest.approx(t.alpha, abs=1e-3)
    assert r["soglia"]["beta"] == pytest.approx(t.beta, abs=1e-4)
    assert r["riferimento"]["nome"] == "ITALICA_T5['italy']"
    assert r["sotto_soglia"]["quota"] == pytest.approx(0.05, abs=0.001)


def test_cost_is_not_measured_without_the_body_s_rain(client: TestClient) -> None:
    r = client.post("/api/taratura", json={"regioni": ["Liguria"]}).json()
    assert r["costo"]["stato"] == "non misurato"
    assert r["riferimento"]["nome"] == "ITALICA_T5['northern']"
    assert r["frane"] == 1603


def test_filters_by_month_and_type(client: TestClient) -> None:
    r = client.post(
        "/api/taratura", json={"regioni": ["Liguria"], "mesi": [10, 11], "tipi": ["SL"]}
    ).json()
    assert 0 < r["frane"] < 1603


def test_few_landslides_are_flagged_and_own_events_are_used(client: TestClient) -> None:
    eventi = [[3, 27], [5, 20], [6, 39], [10, 55], [12, 37], [24, 58]]
    r = client.post("/api/taratura", json={"eventi_ente": eventi, "regioni": ["Puglia"]}).json()
    assert r["origine"] == "eventi dell'ente" and r["frane"] == 6
    assert r["avvertenze"][0].startswith("Solo 6 frane")
    assert r["riferimento"]["nome"] == "ITALICA_T5['southern']"


def test_bad_input_is_a_400(client: TestClient) -> None:
    assert client.post("/api/taratura", json={"eventi_ente": [[0, 5]]}).status_code == 400
    assert client.post("/api/taratura", json={"regioni": ["Nessuna"]}).status_code == 400
    assert client.post("/api/costo", json={"alpha": 7, "beta": 0.5, "serie": ""}).status_code == 400
    assert client.get("/api/esporta").status_code == 400


SERIE = "\n".join(
    ["ora,mm"]
    + [f"2026-10-10T{h:02d}:00,{mm}" for h, mm in enumerate([20, 16, 21, 8, 20, 18, 5])]
    + [f"2026-10-{d:02d}T{h:02d}:00,0" for d in (10, 11) for h in range(24) if (d, h) >= (10, 7)]
    + ["2026-10-12T00:00,", "2026-10-12T01:00,", "2026-10-12T02:00,3", "2026-10-12T03:00,0"]
)


def test_cost_on_the_body_s_gauge(client: TestClient) -> None:
    t = ITALICA_T5["southern"]
    r = client.post(
        "/api/costo",
        json={
            "alpha": t.alpha,
            "beta": t.beta,
            "serie": SERIE,
            "frane": ["2026-10-10", "2025-01-01"],
        },
    ).json()
    assert r["eventi_di_pioggia"] == 2
    assert r["allerte"] == 1 and r["frane_colte"] == 1
    assert r["frane"] == 1 and r["frane_fuori_periodo"] == 1
    assert r["allerte_per_frana_colta"] == 1.0
    assert r["ore_non_misurate"] == 2
    assert "non è un'allerta" in r["regola"]


def test_cost_says_not_measured_when_nothing_is_caught(client: TestClient) -> None:
    r = client.post(
        "/api/costo", json={"alpha": 500, "beta": 0.5, "serie": SERIE, "frane": ["2026-10-10"]}
    ).json()
    assert r["frane_colte"] == 0 and r["frane_mancate"] == 1
    assert r["allerte_per_frana_colta"] == "non misurato"


def test_a_landslide_with_no_measured_rain_is_not_a_miss(client: TestClient) -> None:
    serie = "2026-10-10T00:00,\n2026-10-10T01:00,\n2026-10-10T02:00,"
    r = client.post(
        "/api/costo", json={"alpha": 7, "beta": 0.5, "serie": serie, "frane": ["2026-10-10"]}
    ).json()
    assert r["frane_senza_pioggia_misurata"] == 1 and r["frane_mancate"] == 0
    assert r["quota_eventi_in_allerta"] == "non misurato"


def test_export_is_a_yaml_block(client: TestClient) -> None:
    r = client.get("/api/esporta", params={"alpha": 6.764, "beta": 0.5057, "nome": "liguria; rm"})
    assert r.headers["content-type"].startswith("text/yaml")
    assert "liguriarm:\n  alpha: 6.764\n  beta:  0.5057\n" in r.text
    assert "non è un'allerta" in r.text


def test_health(client: TestClient) -> None:
    assert client.get("/api/salute").json() == {"ok": True, "frane": 5974}
