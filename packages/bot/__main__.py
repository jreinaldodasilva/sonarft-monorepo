"""
SonarFT Bot — Entry point for `python -m sonarft_bot`.
Starts the BotManager with CLI arguments.
"""
import argparse
import asyncio
import logging

from sonarft_manager import BotManager


def _parse_args():
    parser = argparse.ArgumentParser(description="SonarFT")
    parser.add_argument("-l", "--library", type=str, default="ccxtpro",
                        help="The library to use for trading.")
    parser.add_argument("-c", "--config", type=str, default="config_1",
                        help="The configuration to use from config.json.")
    return parser.parse_args()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s",
    )
    logger = logging.getLogger("sonarft")
    args = _parse_args()

    BotManager(logger=logger)

    logger.info("********\nSonarFT\n********")
    logger.info(f"Library: {args.library}")
    logger.info(f"Configuration: {args.config}")

    from sonarft_bot import SonarftBot  # noqa: E402

    bot = SonarftBot(args.library, logger=logger)
    botid = await bot.create_bot(args.config)
    if botid is None:
        logger.error("Bot creation failed — exiting")
        return

    logger.info(f"Bot {botid} created — starting run loop")
    await bot.run_bot()
    logger.info(f"Bot {botid} exited")


if __name__ == "__main__":
    asyncio.run(main())
