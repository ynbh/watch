import subprocess
from pathlib import Path

import typer

from .cli import main as run_tui
from .config import save_api_token

app = typer.Typer(add_completion=False, help="Watch: search and play TMDB content.")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context, web: bool = typer.Option(False, "--web", help="Launch the web app.")):
    if ctx.invoked_subcommand is None:
        if web:
            repo_root = Path(__file__).resolve().parents[2]
            subprocess.run(
                [
                    "uvicorn",
                    "web.app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=repo_root,
                check=False,
            )
            return
        run_tui()


@app.command()
def set_env(token: str = typer.Argument(..., help="TMDB read access token.")):
    save_api_token(token)
    typer.echo("Saved TMDB token to ~/.config/watch-cli")
