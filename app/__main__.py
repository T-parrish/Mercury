from app.main import app

app.run(
    'localhost',
    5000,
    debug=app.config.DEBUG,
    auto_reload=app.config.AUTO_RELOAD,
    workers=app.config.WORKERS
)
