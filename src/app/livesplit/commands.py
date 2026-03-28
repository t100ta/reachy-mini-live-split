"""LiveSplit Server コマンド定数。"""

PING = "ping"
GET_SPLIT_INDEX = "getsplitindex"
GET_CURRENT_SPLIT_NAME = "getcurrentsplitname"
GET_CURRENT_TIMER_PHASE = "getcurrenttimerphase"
GET_CURRENT_TIME = "getcurrenttime"
GET_ATTEMPT_COUNT = "getattemptcount"


def get_delta(comparison: str = "Personal Best") -> str:
    """comparison を指定した getdelta コマンド文字列を返す。"""
    return f"getdelta {comparison}"
