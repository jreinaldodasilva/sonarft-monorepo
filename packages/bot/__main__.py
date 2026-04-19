"""
SonarFT Bot — Entry point for `python -m sonarft_bot`.
Starts the BotManager with CLI arguments.
"""
import asyncio
import logging

from sonarft_manager import BotManager


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s",
    )
    logger = logging.getLogger("sonarft")

    manager = BotManager(logger=logger)
    args = manager.parse_args()

    logger.info("********\nSonarFT\n********")
    logger.info(f"Library: {args.library}")
    logger.info(f"Configuration: {args.config}")

    from sonarft_bot import SonarftBot

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
