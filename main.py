import uvicorn


def main() -> None:
    """
    Development entrypoint to run the FastAPI app with autoreload.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
