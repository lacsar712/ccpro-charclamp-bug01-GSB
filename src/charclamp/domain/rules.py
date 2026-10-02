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


def drawn_eligibility(clamp: Clamp) -> tuple[bool, str]:
    """
    出炭唯一门槛（抽屉按钮与保存接口共用）：

    1. 窑态字段不能已是「已出炭」；
    2. 只认最近一班峰值（不是最早一班），峰值须 ≥ 400℃。

    焖烧中（burning）且最近一班峰值达标即可出炭，不再拿剪影态把按钮灰掉。
    """
    if clamp.status == Clamp.STATUS_DRAWN:
        return False, "该窑已是已出炭状态"
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


def can_mark_clamp_drawn(clamp: Clamp) -> tuple[bool, str]:
    """抽屉按钮态：与保存接口同一套判定，不再各拿各的字段。"""
    return drawn_eligibility(clamp)


def assert_can_set_clamp_status(clamp: Clamp, new_status: str) -> None:
    allowed = {Clamp.STATUS_STACKED, Clamp.STATUS_BURNING, Clamp.STATUS_DRAWN}
    if new_status not in allowed:
        raise RuleError(f"无效状态：{new_status}")
    if new_status == Clamp.STATUS_DRAWN:
        ok, message = drawn_eligibility(clamp)
        if not ok:
            raise RuleError(message)


def counts_toward_drawn_badge(clamp: Clamp) -> bool:
    """已出炭角标：只数窑态字段已是「已出炭」的座，峰值够但仍焖烧中的不算。"""
    return clamp.status == Clamp.STATUS_DRAWN
