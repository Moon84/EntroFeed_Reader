from logging import INFO, getLogger
from os import PathLike
from pathlib import Path
from tempfile import SpooledTemporaryFile

import asyncclick as click

from src.app import rss
from src.mcp import mcp  # type: ignore[attr-defined]

logger = getLogger("cli")
logger.setLevel(INFO)


@click.group
def cli():
    pass


cli.add_command(mcp)  # type: ignore[arg-type]


@cli.command()
async def backup():
    """
    Write a json-format backup of the current EntroFeed state
    to stdout. The file will also be saved in DATA_DIR.
    """
    file_path, _ = await rss.backup()

    with open(file_path, "r") as fp:
        bk = fp.read()

    click.echo(bk)


@cli.command()
@click.argument("file_path")
async def restore(file_path: PathLike):
    """
    Restore a json-format backup of the EntroFeed state
    """
    with open(Path(file_path).resolve(), "rb") as fp:
        spooled = SpooledTemporaryFile()
        spooled.write(fp.read())
        spooled.seek(0)
        await rss.restore(spooled)  # type: ignore[arg-type]


@cli.command()
async def export_opml():
    """
    Write a opml-format list of the feeds configured in EntroFeed
    to stdout. The file will also be saved in DATA_DIR.
    """
    file_path, _ = await rss.feeds_to_opml()

    with open(file_path, "r") as fp:
        bk = fp.read()

    click.echo(bk)


@cli.command()
@click.argument("file_path")
async def import_opml(file_path: PathLike):
    """
    Import an opml-formatted feed list into EntroFeed
    """
    with open(Path(file_path).resolve(), "rb") as fp:
        spooled = SpooledTemporaryFile()
        spooled.write(fp.read())
        spooled.seek(0)
        await rss.opml_to_feeds(spooled)  # type: ignore[arg-type]


@cli.command()
def load_feeds():
    """
    Load feeds from a YML-formatted feeds.yml file in the config dir
    """
    logger.info("EntroFeed CLI requested to check feeds")
    rss.load_feeds()


@cli.command()
async def check_feeds():
    """
    Check for new entries in the configured feeds
    """
    logger.info("EntroFeed CLI requested to check feeds")
    await rss.check_feeds()


@cli.command()
def load_settings():
    """
    Load settings from a YML-formatted settings.yml file in the config dir
    """
    rss.load_settings()


@cli.command()
def load_handlers():
    """
    Load handlers from a YML-formatted handlers.yml file in the config dir
    """
    rss.load_handlers()
