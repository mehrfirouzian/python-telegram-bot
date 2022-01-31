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
"""This module contains the ChosenInlineResultHandler class."""
import re
from typing import Optional, TypeVar, Union, TYPE_CHECKING, Pattern, Match, cast

from telegram import Update
from telegram._utils.defaultvalue import DEFAULT_TRUE
from telegram._utils.types import DVInput
from telegram.ext import Handler
from telegram.ext._utils.types import CCT, HandlerCallback

RT = TypeVar('RT')

if TYPE_CHECKING:
    from telegram.ext import CallbackContext, Application


class ChosenInlineResultHandler(Handler[Update, CCT]):
    """Handler class to handle Telegram updates that contain a chosen inline result.

    Warning:
        When setting ``block`` to :obj:`True`, you cannot rely on adding custom
        attributes to :class:`telegram.ext.CallbackContext`. See its docs for more info.

    Args:
        callback (:obj:`callable`): The callback function for this handler. Will be called when
            :attr:`check_update` has determined that an update should be processed by this handler.
            Callback signature: ``def callback(update: Update, context: CallbackContext)``

            The return value of the callback is usually ignored except for the special case of
            :class:`telegram.ext.ConversationHandler`.
        block (:obj:`bool`, optional): Determines whether the return value of the callback should
            be awaited before processing the next handler in
            :meth:`telegram.ext.Application.process_update`. Defaults to :obj:`True`.
        pattern (:obj:`str` | `Pattern`, optional): Regex pattern. If not :obj:`None`, ``re.match``
            is used on :attr:`telegram.ChosenInlineResult.result_id` to determine if an update
            should be handled by this handler. This is accessible in the callback as
            :attr:`telegram.ext.CallbackContext.matches`.

            .. versionadded:: 13.6

    Attributes:
        callback (:obj:`callable`): The callback function for this handler.
        block (:obj:`bool`): Determines whether the return value of the callback should be
            awaited before processing the next handler in
            :meth:`telegram.ext.Application.process_update`.
        pattern (`Pattern`): Optional. Regex pattern to test
            :attr:`telegram.ChosenInlineResult.result_id` against.

            .. versionadded:: 13.6

    """

    __slots__ = ('pattern',)

    def __init__(
        self,
        callback: HandlerCallback[Update, CCT, RT],
        block: DVInput[bool] = DEFAULT_TRUE,
        pattern: Union[str, Pattern] = None,
    ):
        super().__init__(callback, block=block)

        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        self.pattern = pattern

    def check_update(self, update: object) -> Optional[Union[bool, object]]:
        """Determines whether an update should be passed to this handlers :attr:`callback`.

        Args:
            update (:class:`telegram.Update` | :obj:`object`): Incoming update.

        Returns:
            :obj:`bool`

        """
        if isinstance(update, Update) and update.chosen_inline_result:
            if self.pattern:
                match = re.match(self.pattern, update.chosen_inline_result.result_id)
                if match:
                    return match
            else:
                return True
        return None

    def collect_additional_context(
        self,
        context: 'CallbackContext',
        update: Update,
        application: 'Application',
        check_result: Union[bool, Match],
    ) -> None:
        """This function adds the matched regex pattern result to
        :attr:`telegram.ext.CallbackContext.matches`.
        """
        if self.pattern:
            check_result = cast(Match, check_result)
            context.matches = [check_result]