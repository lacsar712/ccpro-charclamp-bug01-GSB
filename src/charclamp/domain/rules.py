"""炭窑焖烧志业务规则。"""

from __future__ import annotations

from charclamp.domain.models import BurnShift, Clamp

MIN_PEAK_TEMP_FOR_DRAWN = 400.0


class RuleError(ValueError):
    """业务规则校验失败。"""


def latest_shift_for_clamp(clamp: Clamp) -> BurnShift | None:
    if not clamp.shifts:
        return None
    return max(clamp.shifts, key=lambda s: s.started_at)


def can_mark_clamp_drawn(clamp: Clamp) -> tuple[bool, str]:
    """
    出炭门槛（全站唯一口径）：只认最近一班峰值 + 当前窑态字段。
    窑态须为焖烧中，且最近一班峰值已记录并 ≥ 400℃。
    """
    if clamp.status == Clamp.STATUS_DRAWN:
        return False, "该窑已是已出炭状态"
    if clamp.status != Clamp.STATUS_BURNING:
        return False, "窑态不在焖烧中，不能标记为已出炭"
    latest = latest_shift_for_clamp(clamp)
    if latest is None:
        return False, "该窑尚无焖烧班次，不能标记为已出炭"
    if latest.peak_temp_c is None:
        return False, "最近班次尚未记录峰值温度，不能标记为已出炭"
    if latest.peak_temp_c < MIN_PEAK_TEMP_FOR_DRAWN:
        return (
            False,
            f"最近班次峰值温度 {latest.peak_temp_c}℃ 低于 {MIN_PEAK_TEMP_FOR_DRAWN:.0f}℃，不能标记为已出炭",
        )
    return True, ""


def assert_can_set_clamp_status(clamp: Clamp, new_status: str) -> None:
    """保存接口与抽屉同一套口径：出炭只认最近一班峰值 + 窑态字段。"""
    allowed = {Clamp.STATUS_STACKED, Clamp.STATUS_BURNING, Clamp.STATUS_DRAWN}
    if new_status not in allowed:
        raise RuleError(f"无效状态：{new_status}")
    if new_status == Clamp.STATUS_DRAWN:
        ok, msg = can_mark_clamp_drawn(clamp)
        if not ok:
            raise RuleError(msg)


def counts_toward_drawn_badge(clamp: Clamp) -> bool:
    """角标唯一口径：只数窑态已是已出炭的座。"""
    return clamp.status == Clamp.STATUS_DRAWN
