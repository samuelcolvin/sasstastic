from typer.testing import CliRunner

from sasstastic.cli import cli

runner = CliRunner()


def test_print_commands():
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Fantastic SASS and SCSS compilation' in result.output
