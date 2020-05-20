from typer.testing import CliRunner

from sasstastic.cli import cli

runner = CliRunner()


def test_print_commands():
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Compile sass/scss files to css.' in result.output
