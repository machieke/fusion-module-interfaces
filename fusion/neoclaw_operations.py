"""Two trusted bindings, not a general execution or plug-in interface."""
from . import neoclaw_contracts as nal
from . import neoclaw_search_contracts as search
from .contracts import require

COMPOSITION = 'neoclaw-tools/2'
APPLICATION = 'controlled-native-loop/2'


def contract(profile):
    require(profile in (nal.PROFILE, search.PROFILE), 'UNSUPPORTED_PROFILE')
    return nal if profile == nal.PROFILE else search


def from_chosen(chosen):
    profiles = chosen['execution'].profiles
    require(len(profiles) == 1, 'UNSUPPORTED_PROFILE')
    return contract(next(iter(profiles)))


def argument_key(module): return 'premises' if module is nal else 'arguments'
def arguments(module, value): return nal.premises(value) if module is nal else search.arguments(value)
def content_type(module): return 'application/neoclaw-nal-result' if module is nal else search.CONTENT_TYPE
