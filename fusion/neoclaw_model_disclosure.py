"""Narrow operator-owned synthetic prompt consent, checked before any transport."""
from datetime import datetime
import re
from . import model_contracts as c
from .contracts import require

SECTIONS = (' LAST_SKILL_USE_RESULTS: ', ' HISTORY: ', ' MOST_PROMOTED_MEMORIES: ', ' TIME: ')


def dissect(raw):
    c.text(raw)
    require(raw.count(':-:-:-:') == 1, 'UNAUTHORIZED')
    system, user = raw.split(':-:-:-:')
    pieces = []
    for label in SECTIONS:
        require(system.count(label) == 1, 'UNAUTHORIZED')
        before, system = system.split(label)
        pieces.append(before)
    pieces.append(system)
    return dict(zip(('scaffold','feedback','history','memories','time','user'), [*pieces,user]))


def disclose(raw, approved):
    value = dissect(raw)
    require(value['scaffold'] == approved['scaffold'] and value['history'] == '', 'UNAUTHORIZED')
    require(value['memories'] in approved['memories'] and value['user'] in approved['users'], 'UNAUTHORIZED')
    require(type(approved['feedback_expressions']) is list and len(approved['feedback_expressions']) <= 2)
    feedback = value['feedback']
    if feedback:
        number = r'(?:0|1|0\.\d+|[1-9]\d*(?:\.\d+)?[eE]-\d+)'
        allowed = [r'\(RESULTS: \(\(COMMAND_RETURN: \(\(metta '+re.escape(expression)+
                   r'\) \(stv '+number+' '+number+r'\)\)\)\)\)' for expression in approved['feedback_expressions']]
        require(any(re.fullmatch(pattern, feedback) for pattern in allowed), 'UNAUTHORIZED')
    try: parsed = datetime.strptime(value['time'], '%Y-%m-%d %H:%M:%S')
    except ValueError: require(False, 'UNAUTHORIZED')
    require(parsed.strftime('%Y-%m-%d %H:%M:%S') == value['time'], 'UNAUTHORIZED')
    # No section may smuggle the native helper's marker-removal language. Both
    # raw and transformed ordered text have been accounted for by this consent.
    require(not any(x in raw for x in ('<tool_call>','</tool_call>','<arg_value>','</arg_value>')), 'UNAUTHORIZED')
    require(c.messages(raw) == [dict(role='system',content=raw.split(':-:-:-:')[0]),dict(role='user',content=value['user'])], 'UNAUTHORIZED')
    return value
