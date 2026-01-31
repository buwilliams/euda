import typer

app = typer.Typer(help="CLI app.")


@app.command()
def ping():
    """Simple health check."""
    typer.echo("pong")


if __name__ == "__main__":
    app()
