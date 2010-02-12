# -*- coding: utf-8 -*-
"""The ScriptsPony package"""

# Monkeypatch to prevent webflash from escaping HTML
import webflash
webflash.html_escape = lambda s:s
