import typer

from .cli import main as run_tui
from .config import save_api_token

app = typer.Typer(add_completion=False, help="Watch: search and play TMDB content.")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        run_tui()


@app.command()
def set_env(token: str = typer.Argument(..., help="TMDB read access token.")):
    save_api_token(token)
    typer.echo("Saved TMDB token to ~/.config/watch-cli")
