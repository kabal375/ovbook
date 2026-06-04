import typer

app = typer.Typer()


@app.command()
def convert():
    """Convert a book into structured markdown chunks for OpenViking."""
    typer.echo("ovbook convert — not yet implemented")


def main():
    app()


if __name__ == "__main__":
    main()
