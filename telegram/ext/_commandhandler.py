#!/usr/bin/env python
#
# A library that provides a Python interface to the Telegram Bot API
# Copyright (C) 2015-2022
# Leandro Toledo de Souza <devs@python-telegram-bot.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].
"""This module contains the CommandHandler and PrefixHandler classes."""
import re
from typing import TYPE_CHECKING, Callable, Dict, List, Set, Optional, Tuple, TypeVar, Union

from telegram import MessageEntity, Update
from telegram.ext import filters as filters_module, Handler
from telegram._utils.types import SLTS
from telegram._utils.defaultvalue import DefaultValue, DEFAULT_FALSE
from telegram.ext._utils.types import CCT

if TYPE_CHECKING:
    from telegram.ext import Dispatcher

RT = TypeVar('RT')


class CommandHandler(Handler[Update, CCT]):
    """Handler class to handle Telegram commands.

    Commands are Telegram messages that start with ``/``, optionally followed by an ``@`` and the
    bot's name and/or some additional text. The handler will add a ``list`` to the
    :class:`CallbackContext` named :attr:`CallbackContext.args`. It will contain a list of strings,
    which is the text following the command split on single or consecutive whitespace characters.

    By default the handler listens to messages as well as edited messages. To change this behavior
    use ``~filters.UpdateType.EDITED_MESSAGE`` in the filter argument.

    Note:
        * :class:`CommandHandler` does *not* handle (edited) channel posts.

    Warning:
        When setting ``run_async`` to :obj:`True`, you cannot rely on adding custom
        attributes to :class:`telegram.ext.CallbackContext`. See its docs for more info.

    .. versionchanged:: 14.0
        :attr:`commands` is now a set and can be assinged after construction of model.

    Args:
        command (:obj:`str` | Tuple[:obj:`str`] | List[:obj:`str`] | Set[:obj:`str`]):
            The command or list of commands this handler should listen for.
            Limitations are the same as described here https://core.telegram.org/bots#commands

            .. versionchanged:: 14.0
                Added support for sets.

        callback (:obj:`callable`): The callback function for this handler. Will be called when
            :attr:`check_update` has determined that an update should be processed by this handler.
            Callback signature: ``def callback(update: Update, context: CallbackContext)``

            The return value of the callback is usually ignored except for the special case of
            :class:`telegram.ext.ConversationHandler`.
        filters (:class:`telegram.ext.BaseFilter`, optional): A filter inheriting from
            :class:`telegram.ext.filters.BaseFilter`. Standard filters can be found in
            :mod:`telegram.ext.filters`. Filters can be combined using bitwise
            operators (& for and, | for or, ~ for not).
        run_async (:obj:`bool`): Determines whether the callback will run asynchronously.
            Defaults to :obj:`False`.

    Raises:
        ValueError: when command is too long or has illegal chars.

    Attributes:
        callback (:obj:`callable`): The callback function for this handler.
        filters (:class:`telegram.ext.BaseFilter`): Optional. Only allow updates with these
            Filters.
        run_async (:obj:`bool`): Determines whether the callback will run asynchronously.

            .. versionchanged:: 14.0
                :attr:`commands` is now a set and can be assinged after construction of model.

    """

    __slots__ = ('_commands', 'filters')

    def __init__(
        self,
        command: SLTS[str],
        callback: Callable[[Update, CCT], RT],
        filters: filters_module.BaseFilter = None,
        run_async: Union[bool, DefaultValue] = DEFAULT_FALSE,
    ):
        super().__init__(callback, run_async=run_async)

        self._commands: Set = set()
        self.commands = command  # type: ignore[assignment]

        self.filters = filters if filters is not None else filters_module.UpdateType.MESSAGES

    def check_update(
        self, update: object
    ) -> Optional[Union[bool, Tuple[List[str], Optional[Union[bool, Dict]]]]]:
        """Determines whether an update should be passed to this handlers :attr:`callback`.

        Args:
            update (:class:`telegram.Update` | :obj:`object`): Incoming update.

        Returns:
            :obj:`list`: The list of args for the handler.

        """
        if isinstance(update, Update) and update.effective_message:
            message = update.effective_message

            if (
                message.entities
                and message.entities[0].type == MessageEntity.BOT_COMMAND
                and message.entities[0].offset == 0
                and message.text
                and message.get_bot()
            ):
                command = message.text[1: message.entities[0].length]
                args = message.text.split()[1:]
                command_parts = command.split('@')
                command_parts.append(message.get_bot().username)

                if not (
                    command_parts[0].lower() in self._commands
                    and command_parts[1].lower() == message.get_bot().username.lower()
                ):
                    return None

                filter_result = self.filters.check_update(update)
                if filter_result:
                    return args, filter_result
                return False
        return None

    def collect_additional_context(
        self,
        context: CCT,
        update: Update,
        dispatcher: 'Dispatcher',
        check_result: Optional[Union[bool, Tuple[List[str], Optional[bool]]]],
    ) -> None:
        """Add text after the command to :attr:`CallbackContext.args` as list, split on single
        whitespaces and add output of data filters to :attr:`CallbackContext` as well.
        """
        if isinstance(check_result, tuple):
            context.args = check_result[0]
            if isinstance(check_result[1], dict):
                context.update(check_result[1])

    def _parse_commands(self, command: SLTS[str]) -> None:
        if isinstance(command, str):
            self._commands = {command.lower()}
        else:
            self._commands = {i.lower() for i in command}

    @property
    def commands(self) -> Set[str]:
        """
        The set of commands this handler should listen for.

        Returns:
            Set[:obj:`str`]
        """
        return self._commands

    @commands.setter
    def commands(self, command: SLTS) -> None:
        self._parse_commands(command)
        for comm in self._commands:
            if not re.match(r'^[\da-z_]{1,32}$', comm):
                raise ValueError(f'Command `{comm}` is not a valid bot command')


class PrefixHandler(CommandHandler):
    """Handler class to handle custom prefix commands.

    This is a intermediate handler between :class:`MessageHandler` and :class:`CommandHandler`.
    It supports configurable commands with the same options as CommandHandler. It will respond to
    every combination of :attr:`prefix` and :attr:`command`. It will add a :obj:`list` to the
    :class:`CallbackContext` named :attr:`CallbackContext.args`. It will contain a list of strings,
    which is the text following the command split on single or consecutive whitespace characters.

    Examples:

        Single prefix and command:

        .. code:: python

            PrefixHandler('!', 'test', callback)  # will respond to '!test'.

        Multiple prefixes, single command:

        .. code:: python

            PrefixHandler(['!', '#'], 'test', callback)  # will respond to '!test' and '#test'.

        Multiple prefixes and commands:

        .. code:: python

            PrefixHandler(['!', '#'], ['test', 'help'], callback)  # will respond to '!test', \
            '#test', '!help' and '#help'.


    By default the handler listens to messages as well as edited messages. To change this behavior
    use ``~filters.UpdateType.EDITED_MESSAGE``.

    Note:
        * :class:`PrefixHandler` does *not* handle (edited) channel posts.

    Warning:
        When setting ``run_async`` to :obj:`True`, you cannot rely on adding custom
        attributes to :class:`telegram.ext.CallbackContext`. See its docs for more info.

    .. versionchanged:: 14.0
        :attr:`prefixes` and :attr:`commands` are always a set and can be
        assigned with sets as well.

    Args:
        prefix (:obj:`str` | Tuple[:obj:`str`] | List[:obj:`str`] | Set[:obj:`str`]):
            The prefix(es) that will precede :attr:`command`.

            .. versionchanged:: 14.0
                Added support for sets.

        command (:obj:`str` | Tuple[:obj:`str`] | List[:obj:`str`] | Set[:obj:`str`]):
            The command or list of commands this handler should listen for.

            .. versionchanged:: 14.0
                Added support for sets.

        callback (:obj:`callable`): The callback function for this handler. Will be called when
            :attr:`check_update` has determined that an update should be processed by this handler.
            Callback signature: ``def callback(update: Update, context: CallbackContext)``

            The return value of the callback is usually ignored except for the special case of
            :class:`telegram.ext.ConversationHandler`.
        filters (:class:`telegram.ext.BaseFilter`, optional): A filter inheriting from
            :class:`telegram.ext.filters.BaseFilter`. Standard filters can be found in
            :mod:`telegram.ext.filters`. Filters can be combined using bitwise
            operators (& for and, | for or, ~ for not).
        run_async (:obj:`bool`): Determines whether the callback will run asynchronously.
            Defaults to :obj:`False`.

    Attributes:
        callback (:obj:`callable`): The callback function for this handler.
        filters (:class:`telegram.ext.BaseFilter`): Optional. Only allow updates with these
            Filters.
        run_async (:obj:`bool`): Determines whether the callback will run asynchronously.

    """

    __slots__ = ('_prefixes', '_combinations')

    def __init__(
        self,
        prefix: SLTS[str],
        command: SLTS[str],
        callback: Callable[[Update, CCT], RT],
        filters: filters_module.BaseFilter = None,
        run_async: Union[bool, DefaultValue] = DEFAULT_FALSE,
    ):

        self._prefixes: Set[str] = set()
        self._combinations: Set[str] = set()

        super().__init__(
            command,
            callback,
            filters=filters,
            run_async=run_async,
        )

        self.prefixes = prefix  # type: ignore[assignment]

    @property
    def prefixes(self) -> Set[str]:
        """
        The prefixes that will precede :attr:`commands`.

        Returns:
            Set[:obj:`str`]
        """
        return self._prefixes

    @prefixes.setter
    def prefixes(self, prefix: SLTS) -> None:
        if isinstance(prefix, str):
            self._prefixes = {prefix.lower()}
        else:
            self._prefixes = set(prefix)
        self._build_commands()

    @CommandHandler.commands.setter  # type: ignore[attr-defined,misc]
    def commands(self, command: SLTS) -> None:
        self._parse_commands(command)
        self._build_commands()

    def _build_commands(self) -> None:
        self._combinations = {
            x.lower() + y.lower() for x in self._prefixes for y in self._commands
        }

    def check_update(
        self, update: object
    ) -> Optional[Union[bool, Tuple[List[str], Optional[Union[bool, Dict]]]]]:
        """Determines whether an update should be passed to this handlers :attr:`callback`.

        Args:
            update (:class:`telegram.Update` | :obj:`object`): Incoming update.

        Returns:
            :obj:`list`: The list of args for the handler.

        """
        if isinstance(update, Update) and update.effective_message:
            message = update.effective_message

            if message.text:
                text_list = message.text.split()
                if text_list[0].lower() not in self._combinations:
                    return None
                filter_result = self.filters.check_update(update)
                if filter_result:
                    return text_list[1:], filter_result
                return False
        return None
