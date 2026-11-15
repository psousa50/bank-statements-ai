import httpx
import pytest


def _account(client, unique, prefix="account"):
    name = unique(prefix)
    response = client.post("/accounts", json={"name": name, "currency": "EUR"})
    assert response.status_code == 201, f"POST /accounts returned {response.status_code}: {response.text}"
    return response.json()


def _counterparty(client, unique, type="person", prefix="counterparty"):
    name = unique(prefix)
    response = client.post("/counterparties", json={"name": name, "type": type})
    assert response.status_code == 201, f"POST /counterparties returned {response.status_code}: {response.text}"
    return response.json()


@pytest.mark.behaviour("counterparties.creation.created_counterparty_appears_in_the_list")
def test_created_counterparty_appears_in_the_list(client, unique):
    created = _counterparty(client, unique, type="company")

    listed = client.get("/counterparties")
    assert listed.status_code == 200, f"GET /counterparties returned {listed.status_code}: {listed.text}"

    matching = [c for c in listed.json()["counterparties"] if c["id"] == created["id"]]
    assert matching, f"counterparty {created['id']} was created but is absent from GET /counterparties"
    assert matching[0]["name"] == created["name"]
    assert matching[0]["type"] == "company"


@pytest.mark.behaviour("counterparties.listing.requires_authentication")
def test_listing_counterparties_requires_authentication(base_url):
    with httpx.Client(base_url=base_url, timeout=30.0) as anonymous:
        response = anonymous.get("/counterparties")

    assert (
        response.status_code == 401
    ), f"GET /counterparties without a session returned {response.status_code}: {response.text}"


@pytest.mark.behaviour("counterparties.creation.duplicate_name_is_rejected")
def test_creating_a_counterparty_with_a_duplicate_name_is_rejected(client, unique):
    existing = _counterparty(client, unique)

    duplicate = client.post("/counterparties", json={"name": existing["name"], "type": "other"})

    assert duplicate.status_code == 409, (
        f"POST /counterparties with the existing name {existing['name']!r} returned "
        f"{duplicate.status_code}: {duplicate.text}"
    )


@pytest.mark.behaviour("counterparties.creation.a_counterparty_may_share_a_name_with_an_account")
def test_a_counterparty_may_share_a_name_with_an_account(client, unique):
    account = _account(client, unique)

    counterparty = client.post("/counterparties", json={"name": account["name"], "type": "company"})

    assert counterparty.status_code == 201, (
        f"a counterparty named after the account {account['name']!r} was rejected with "
        f"{counterparty.status_code}: {counterparty.text}"
    )


@pytest.mark.behaviour("counterparties.isolation.an_account_is_not_a_counterparty")
def test_accounts_do_not_appear_as_counterparties(client, unique):
    account = _account(client, unique)

    listed = client.get("/counterparties")

    assert listed.status_code == 200, f"GET /counterparties returned {listed.status_code}: {listed.text}"
    assert not [
        c for c in listed.json()["counterparties"] if c["id"] == account["id"]
    ], f"account {account['id']} named {account['name']!r} is being listed as a counterparty"


@pytest.mark.behaviour("counterparties.isolation.a_counterparty_is_not_an_account")
def test_counterparties_do_not_appear_as_accounts(client, unique):
    counterparty = _counterparty(client, unique)

    listed = client.get("/accounts")

    assert listed.status_code == 200, f"GET /accounts returned {listed.status_code}: {listed.text}"
    assert not [
        a for a in listed.json()["accounts"] if a["id"] == counterparty["id"]
    ], f"counterparty {counterparty['id']} named {counterparty['name']!r} is being listed as an account"


@pytest.mark.behaviour("transactions.other_side.a_transaction_takes_a_counterparty")
def test_a_transaction_can_be_given_a_counterparty(client, unique):
    account = _account(client, unique)
    counterparty = _counterparty(client, unique)

    created = client.post(
        "/transactions",
        json={
            "date": "2024-03-01",
            "description": unique("rent"),
            "amount": -750.00,
            "account_id": account["id"],
            "counterparty_id": counterparty["id"],
        },
    )

    assert created.status_code in (200, 201), f"POST /transactions returned {created.status_code}: {created.text}"
    body = created.json()
    assert body["counterparty_id"] == counterparty["id"]
    assert body["transfer_account_id"] is None


@pytest.mark.behaviour("transactions.other_side.a_transaction_takes_a_transfer_account")
def test_a_transaction_can_be_given_a_transfer_account(client, unique):
    account = _account(client, unique)
    savings = _account(client, unique, prefix="savings")

    created = client.post(
        "/transactions",
        json={
            "date": "2024-03-01",
            "description": unique("to savings"),
            "amount": -200.00,
            "account_id": account["id"],
            "transfer_account_id": savings["id"],
        },
    )

    assert created.status_code in (200, 201), f"POST /transactions returned {created.status_code}: {created.text}"
    body = created.json()
    assert body["transfer_account_id"] == savings["id"]
    assert body["counterparty_id"] is None


@pytest.mark.behaviour("transactions.other_side.both_sides_at_once_are_rejected")
def test_a_transaction_cannot_have_both_a_counterparty_and_a_transfer_account(client, unique):
    account = _account(client, unique)
    savings = _account(client, unique, prefix="savings")
    counterparty = _counterparty(client, unique)

    created = client.post(
        "/transactions",
        json={
            "date": "2024-03-01",
            "description": unique("ambiguous"),
            "amount": -50.00,
            "account_id": account["id"],
            "counterparty_id": counterparty["id"],
            "transfer_account_id": savings["id"],
        },
    )

    assert created.status_code == 422, (
        f"a transaction with both a counterparty and a transfer account was accepted with "
        f"{created.status_code}: {created.text}"
    )


@pytest.mark.behaviour("transactions.other_side.a_counterparty_is_not_a_valid_transfer_account")
def test_a_counterparty_id_is_rejected_as_a_transfer_account(client, unique):
    account = _account(client, unique)
    counterparty = _counterparty(client, unique)

    created = client.post(
        "/transactions",
        json={
            "date": "2024-03-01",
            "description": unique("wrong side"),
            "amount": -50.00,
            "account_id": account["id"],
            "transfer_account_id": counterparty["id"],
        },
    )

    assert (
        created.status_code >= 400
    ), f"a counterparty id was accepted as transfer_account_id with {created.status_code}: {created.text}"


@pytest.mark.behaviour("accounts.conversion.a_phantom_account_becomes_a_counterparty")
def test_an_account_that_owns_nothing_can_become_a_counterparty(client, unique):
    account = _account(client, unique)
    owning_account = _account(client, unique, prefix="real")
    client.post(
        "/transactions",
        json={
            "date": "2024-03-01",
            "description": unique("paid"),
            "amount": -30.00,
            "account_id": owning_account["id"],
            "transfer_account_id": account["id"],
        },
    )

    converted = client.post(f"/accounts/{account['id']}/convert-to-counterparty", json={"type": "person"})

    assert (
        converted.status_code == 200
    ), f"converting the phantom account {account['name']!r} returned {converted.status_code}: {converted.text}"
    body = converted.json()
    assert body["counterparty"]["name"] == account["name"]
    assert body["counterparty"]["type"] == "person"
    assert body["transactions_repointed"] == 1

    assert (
        client.get(f"/accounts/{account['id']}").status_code == 404
    ), f"account {account['id']} still exists after being converted to a counterparty"


@pytest.mark.behaviour("accounts.conversion.a_real_account_is_refused")
def test_an_account_that_owns_transactions_cannot_become_a_counterparty(client, unique):
    account = _account(client, unique)
    client.post(
        "/transactions",
        json={
            "date": "2024-03-01",
            "description": unique("own"),
            "amount": -12.00,
            "account_id": account["id"],
        },
    )

    converted = client.post(f"/accounts/{account['id']}/convert-to-counterparty", json={"type": "person"})

    assert (
        converted.status_code == 409
    ), f"converting the real account {account['name']!r} returned {converted.status_code}: {converted.text}"
    assert (
        client.get(f"/accounts/{account['id']}").status_code == 200
    ), f"account {account['id']} was deleted despite the conversion being refused"


@pytest.mark.behaviour("enhancement_rules.other_side.both_sides_at_once_are_rejected")
def test_a_rule_cannot_set_both_a_counterparty_and_a_transfer_account(client, unique):
    savings = _account(client, unique, prefix="savings")
    counterparty = _counterparty(client, unique)

    created = client.post(
        "/enhancement-rules",
        json={
            "patterns": [{"normalized_description": unique("pattern"), "match_type": "exact"}],
            "counterparty_id": counterparty["id"],
            "transfer_account_id": savings["id"],
            "source": "MANUAL",
        },
    )

    assert created.status_code == 422, (
        f"a rule with both a counterparty and a transfer account was accepted with " f"{created.status_code}: {created.text}"
    )


@pytest.mark.behaviour("transactions.filtering.by_counterparty")
def test_transactions_can_be_filtered_to_one_counterparty(client, unique):
    account = _account(client, unique)
    wanted = _counterparty(client, unique, prefix="wanted")
    other = _counterparty(client, unique, prefix="other")

    for counterparty in (wanted, wanted, other):
        created = client.post(
            "/transactions",
            json={
                "date": "2024-04-01",
                "description": unique("payment"),
                "amount": -25.00,
                "account_id": account["id"],
                "counterparty_id": counterparty["id"],
            },
        )
        assert created.status_code in (200, 201), f"POST /transactions returned {created.status_code}: {created.text}"

    listed = client.get("/transactions", params={"counterparty_id": wanted["id"], "page_size": 100})

    assert listed.status_code == 200, f"GET /transactions returned {listed.status_code}: {listed.text}"
    returned = listed.json()["transactions"]
    assert returned, f"filtering by counterparty {wanted['name']!r} returned nothing"
    assert all(
        t["counterparty_id"] == wanted["id"] for t in returned
    ), "the counterparty filter returned transactions belonging to a different counterparty"
    assert len(returned) == 2
