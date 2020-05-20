from typer.testing import CliRunner

from sasstastic.cli import cli

runner = CliRunner()


def test_print_commands():
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Build sass/scss files to css based on a config file' in result.output
