"""Record the current M11 API admission boundary until custody is integrated."""


def test_m11_frontend_routes_are_not_served_before_lifecycle_registration(harness):
    routes = {
        (method, route.path)
        for route in harness.app.routes
        for method in getattr(route, "methods", ())
    }
    expected = {
        ("POST", "/api/projects/{project_id}/joint-members"),
        ("POST", "/api/projects/{project_id}/joint-datasets"),
        ("GET", "/api/projects/{project_id}/joint-datasets/{dataset_id}"),
        ("GET", "/api/projects/{project_id}/joint-results"),
        ("GET", "/api/projects/{project_id}/joint-results/{job_id}"),
        ("GET", "/api/projects/{project_id}/joint-results/{job_id}/export"),
    }
    assert expected.isdisjoint(routes)
