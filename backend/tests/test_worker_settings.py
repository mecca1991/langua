def test_worker_settings_importable():
    from app.worker.settings import WorkerSettings
    assert hasattr(WorkerSettings, "functions")
    assert hasattr(WorkerSettings, "redis_settings")

def test_worker_settings_has_functions():
    from app.worker.settings import WorkerSettings
    assert isinstance(WorkerSettings.functions, list)
    assert len(WorkerSettings.functions) >= 1
