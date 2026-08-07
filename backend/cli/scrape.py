from typer.main import get_command

from cli.main import app

main = get_command(app)


if __name__ == "__main__":
    app()
