import typer

app = typer.Typer(help="gcal CLI app.")


@app.command()
def ping():
    """Simple health check."""
    typer.echo("pong")


if __name__ == "__main__":
    app()
