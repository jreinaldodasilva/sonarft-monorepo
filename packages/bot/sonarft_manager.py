"""
Sonarft Bots Manager Module
"""
import argparse
import asyncio

from sonarft_bot import BotCreationError, SonarftBot
from sonarft_helpers import sanitize_client_id


# ### BotManager Class - ##########################################
class BotManager:
    """
    Bots Management Class
    """

    def __init__(self, logger=None):
        """
        Initializes BotManager with an empty bots dictionary, clients dictionary and lock object.

        Parameters:
        logger (logging.Logger): An optional logger object to log messages.
        """
        self._bots = {}
        self._clients = {}
        self._lock = asyncio.Lock()
        self.logger = logger

    async def add_bot_instance(self, client_id, botid, bot):
        """
        Adds a new bot instance to the _bots dictionary and,
        stores the bot id.

        Parameters:
        client_id (str): The client id to associate the new bot with.
        botid (str): The unique identifier for the bot.
        bot (SonarftBot): An instance of the SonarftBot class.
        """
        client_id = sanitize_client_id(client_id)
        async with self._lock:
            self._bots[botid] = bot
            self._clients.setdefault(client_id, []).append(botid)

    async def remove_bot_instance(self, botid):
        """
        Removes a bot instance from _bots dictionary and its botid from the _clients dictionary.
        Calls stop_bot() outside the lock to avoid blocking other operations during network I/O.

        Parameters:
        botid (str): The unique identifier for the bot.
        """
        bot = None
        async with self._lock:
            if botid in self._bots:
                bot = self._bots.pop(botid)
                for _client_id, bot_list in self._clients.items():
                    if botid in bot_list:
                        bot_list.remove(botid)
        # stop_bot() performs network I/O (cancel tasks, close connections)
        # — called outside the lock so other operations are not blocked
        if bot:
            await bot.stop_bot()

    def _get_bot_unsafe(self, botid):
        """Non-locking bot lookup — only call while already holding self._lock."""
        return self._bots.get(botid)

    async def get_bot_instance(self, botid):
        """
        Returns a bot instance from the _bots dictionary.
        """
        async with self._lock:
            return self._get_bot_unsafe(botid)

    async def set_update(self, botid, update_data) -> bool:
        async with self._lock:
            sonarft = self._get_bot_unsafe(botid)
            if not sonarft:
                if self.logger:
                    self.logger.warning("Bot {botid} not found. Update failed.")
                return False
            sonarft.set_update(update_data)
            return True

    async def get_update(self, botid):
        async with self._lock:
            sonarft = self._get_bot_unsafe(botid)
            if not sonarft:
                if self.logger:
                    self.logger.warning("Bot {botid} not found. Cannot get update.")
                return None
            return sonarft.get_update()

    def get_botids(self, client_id):
        """
        Returns a list of bot ids associated with a client id.

        Parameters:
        client_id (str): The client id to retrieve the bot ids for.

        Returns:
        list: A list of bot ids.
        """
        return self._clients.get(client_id, [])

    def parse_args(self):
        """
        Parse command-line arguments for SonarFT
        """
        parser = argparse.ArgumentParser(description="SonarFT")
        parser.add_argument(
            "-l",
            "--library",
            type=str,
            default="ccxtpro",
            help="The library to use for trading.",
        )
        parser.add_argument(
            "-c",
            "--config",
            type=str,
            default="config_1",
            help="The configuration to use from the config.json file.",
        )
        return parser.parse_args()

    async def create_bot(self, client_id):
        """
        Creates a new bot, adds the bot instance to the _bots dictionary, stores the botid,
        amd rum the bot.

        Parameters:
        client_id (str): The client id to associate the new bot with.
        """
        client_id = sanitize_client_id(client_id)
        args = self.parse_args()

        self.logger.info("********\nSonarFT\n********")
        self.logger.info("Library: {args.library}")
        self.logger.info("Configuration: {args.config}")
        botid = None
        try:

            # Create a new bot instance
            sonarft = SonarftBot(args.library, logger=self.logger)
            botid = await sonarft.create_bot(args.config)

            # Store the new bot instance and the botid
            await self.add_bot_instance(client_id, botid, sonarft)
            self.logger.info(
                f"Bot: {botid} successfully stored for client: {client_id}."
            )
            self.logger.info("Bot CREATED!")

        except BotCreationError as error:
            self.logger.error("Bot creation error: {error}")
            if botid:
                await self.remove_bot(botid)
            return

        return botid

    async def run_bot(self, botid):
        """
        Run the created bot.

        Parameters:
        sonarft
        botid
        """
        try:
            # Run the bot
            sonarft = await self.get_bot_instance(botid)
            self.logger.info("Running {sonarft} - {botid}")
            if not sonarft:
                return

            await sonarft.run_bot()
            sonarft.stop_bot_flag = False
        except BotRunError as error:
            self.logger.error("Bot run error: {error}")
            if botid:
                await self.remove_bot(botid)

    async def pause_bot(self, botid: str) -> None:
        """
        Pause a running bot without removing it from the registry.
        The bot can be resumed by calling run_bot() again.

        Parameters:
        botid (str): The unique identifier for the bot.
        """
        sonarft = await self.get_bot_instance(botid)
        if not sonarft:
            if self.logger:
                self.logger.warning("pause_bot: Bot {botid} not found.")
            return
        await sonarft.pause_bot()
        if self.logger:
            self.logger.info("Bot {botid} paused.")

    async def resume_bot(self, botid: str) -> None:
        """
        Resume a paused bot by resetting its stop event and restarting the run loop.

        Parameters:
        botid (str): The unique identifier for the bot.
        """
        sonarft = await self.get_bot_instance(botid)
        if not sonarft:
            if self.logger:
                self.logger.warning("resume_bot: Bot {botid} not found.")
            return
        sonarft.resume_bot()
        await sonarft.run_bot()
        if self.logger:
            self.logger.info("Bot {botid} resumed.")

    async def reload_parameters(self, client_id: str, new_parameters: dict) -> None:
        """
        Hot-reload trading parameters into all running bots owned by client_id.
        Only safe numeric/flag parameters are applied; exchange/symbol config is not changed.
        """
        client_id = sanitize_client_id(client_id)
        botids = self.get_botids(client_id)
        for botid in botids:
            async with self._lock:
                bot = self._get_bot_unsafe(botid)
                if bot:
                    bot.apply_parameters(new_parameters)
                    if self.logger:
                        self.logger.info(
                            f"Hot-reloaded parameters for bot {botid} (client {client_id})"
                        )

    async def remove_bot(self, botid):
        """
        Removes a bot if it exists.

        Parameters:
        botid (str): The unique identifier for the bot.
        """
        sonarft = await self.get_bot_instance(botid)
        self.logger.info("Removing {sonarft} - {botid}")
        if not sonarft:
            return

        await self.remove_bot_instance(botid)
        self.logger.info("Bot REMOVED!")


class BotRunError(Exception):
    """Raised when there's an issue during the bot run phase."""

    def __init__(self, message="Failed to run the bot."):
        self.message = message
        super().__init__(self.message)
