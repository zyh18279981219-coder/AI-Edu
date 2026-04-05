if __name__ == "__main__":
    import logging
    import os
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    reload_enabled = os.getenv("APP_RELOAD", "false").lower() in {"1", "true", "yes"}
    print("项目已启动，请访问: http://localhost:8000/")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=reload_enabled)

