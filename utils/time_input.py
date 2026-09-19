"""
utils/time_input.py — shared 12-hour time entry for any screen: a live
input mask (only valid "HH:MM AM/PM" characters can ever be typed) plus
a tap-to-open native time picker as a shortcut. Originally built for
the Sugar screen; factored out here so the Vitals screen (and anything
else that needs a time field later) uses the exact same, already-tested
behavior instead of a second copy of it.
"""

from datetime import datetime as _dt

from kivymd.uix.pickers import MDTimePicker


def make_time_mask_filter(field):
    """Returns an input_filter callable enforcing "HH:MM AM/PM" as it's
    typed: HH is 00-12, MM is 00-59, and the ':' / space / trailing 'M'
    are inserted automatically. Invalid characters are dropped, not
    just rejected after the fact — an out-of-range digit or a stray
    symbol never makes it into the field at all."""
    def filt(substring, from_undo=False):
        if from_undo:
            return substring
        out = ""
        for ch in substring:
            current = field.text + out
            pos = len(current)
            if pos == 0:
                if ch in "01":
                    out += ch
            elif pos == 1:
                first = current[0]
                if first == "1":
                    if ch in "012":
                        out += ch + ":"
                elif ch.isdigit():
                    out += ch + ":"
            elif pos == 2:
                continue  # ':' already auto-inserted
            elif pos == 3:
                if ch in "012345":
                    out += ch
            elif pos == 4:
                if ch.isdigit():
                    out += ch + " "
            elif pos == 5:
                continue  # space already auto-inserted
            elif pos == 6:
                if ch.lower() in ("a", "p"):
                    out += ch.upper() + "M"
            # pos >= 8 ("HH:MM AM/PM" complete): reject further input
        return out
    return filt


def bind_time_field(field):
    """Wires up both the live mask and the tap-to-open picker on a
    plain MDTextField used for 12-hour time entry. Call this once,
    right after creating the field."""
    field.input_filter = make_time_mask_filter(field)

    def open_picker(instance, is_focused):
        if not is_focused:
            return
        field.focus = False  # avoid the keyboard popping up too
        picker = MDTimePicker()
        try:
            parsed = _dt.strptime(field.text.strip(), "%I:%M %p")
            picker.set_time(parsed.time())
        except (ValueError, AttributeError):
            pass

        def on_save(picker_instance, time_obj):
            field.text = time_obj.strftime("%I:%M %p")

        picker.bind(on_save=on_save)
        picker.open()

    field.bind(focus=open_picker)


def now_12h():
    """Current time as '07:45 PM' — the default value for a fresh
    time field."""
    return _dt.now().strftime("%I:%M %p")
