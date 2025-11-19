import uuid

import pytest
import pytest_asyncio

from app.db.models import Repository, Service, Interaction, EdgeType, Scan, ScanStatus, ScanTarget


@pytest_asyncio.fixture
async def graph_test_data(session_maker):
    async with session_maker() as session:
        repo_id = uuid.uuid4()
        service_a_id = uuid.uuid4()
        service_b_id = uuid.uuid4()
        scan_id = uuid.uuid4()

        unique_repo_name = f"owner/repo-{str(uuid.uuid4())[:8]}"

        repo = Repository(
            id=repo_id,
            full_name=unique_repo_name,
            html_url="https://github.com/owner/repo",
            owner="owner",
            default_branch="main",
        )
        service_a = Service(
            id=service_a_id,
            name="orders",
            repo_id=repo_id,
            language="python",
        )
        service_b = Service(
            id=service_b_id,
            name="payments",
            repo_id=repo_id,
            language="go",
        )
        interaction = Interaction(
            source_service_id=service_a_id,
            target_service_id=service_b_id,
            edge_type=EdgeType.HTTP,
            http_method="GET",
            http_url="/payments/status",
            confidence=0.9,
        )

        scan = Scan(
            id=scan_id,
            user_id="tester",
            status=ScanStatus.SUCCESS,
        )
        scan_target = ScanTarget(
            scan_id=scan_id,
            repo_id=repo_id,
        )

        session.add_all([repo, service_a, service_b, interaction, scan, scan_target])
        await session.commit()

    return {
        "repo_full_name": repo.full_name,
        "scan_id": scan_id,
    }


@pytest.mark.asyncio
async def test_get_graph_by_repo(client, auth_cookies, graph_test_data):
    response = await client.get(
        f"/graph?repos={graph_test_data['repo_full_name']}",
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) == 2
    assert {node["name"] for node in payload["nodes"]} == {"orders", "payments"}
    assert len(payload["links"]) == 1
    assert payload["links"][0]["kind"] == "HTTP"


@pytest.mark.asyncio
async def test_get_graph_by_scan(client, auth_cookies, graph_test_data):
    response = await client.get(
        f"/graph?scan_id={graph_test_data['scan_id']}",
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) == 2
    assert len(payload["links"]) == 1


@pytest.mark.asyncio
async def test_get_graph_requires_authentication(client):
    response = await client.get("/graph")
    assert response.status_code == 401
