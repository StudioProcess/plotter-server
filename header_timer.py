"""Provides a Textual application header widget."""
from datetime import datetime

from rich.text import Text
from textual.widgets import Header
from textual.widgets._header import HeaderIcon, HeaderTitle, HeaderClockSpace
from textual.reactive import Reactive

class HeaderClock(HeaderClockSpace):
    """Display a clock on the right of the header."""
    
    DEFAULT_CSS = """
    HeaderClock {
        background: $foreground-darken-1 5%;
        color: $text;
        text-opacity: 85%;
        content-align: center middle;
    }
    """
    
    time_seconds: Reactive[str] = Reactive(0)
    
    def render(self):
        """Render the header clock.
    
        Returns:
            The rendered clock.
        """
        if self.time_seconds == 0: return Text('--:--')
        hours = int(self.time_seconds / 3600)
        minutes = int((self.time_seconds - 3600 * hours) / 60)
        seconds = int((self.time_seconds - 3600 * hours) % 60)
        if hours == 0:
            return Text(f'{minutes:02}:{seconds:02}')
        else:
            return Text(f'{hours:02}:{minutes:02}:{seconds:02}')

class HeaderTimer(Header):
    
    time_seconds: Reactive[str] = Reactive(0)
    """Time of the Clock in seconds."""
  
    def compose(self):
        yield HeaderIcon().data_bind(Header.icon)
        yield HeaderTitle()
        yield (
            HeaderClock().data_bind(HeaderTimer.time_seconds)
            if self._show_clock
            else HeaderClockSpace()
        )
