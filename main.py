if __name__ == "__main__":
    import logging
    import os
    import sys
    from pathlib import Path

    import uvicorn

    project_root = Path(__file__).resolve().parent
    backend_root = project_root / "backend"
    for path in (project_root, backend_root):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    os.chdir(backend_root)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    reload_enabled = os.getenv("APP_RELOAD", "false").lower() in {"1", "true", "yes"}
    print("项目已启动，请访问: http://localhost:8000/")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=reload_enabled)

