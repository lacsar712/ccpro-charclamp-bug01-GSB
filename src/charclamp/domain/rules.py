"""炭窑焖烧志业务规则。"""

from __future__ import annotations

from charclamp.domain.models import BurnShift, Clamp

MIN_PEAK_TEMP_FOR_DRAWN = 400.0


class RuleError(ValueError):
    """业务规则校验失败。"""


def earliest_shift_for_clamp(clamp: Clamp) -> BurnShift | None:
    if not clamp.shifts:
        return None
    return min(clamp.shifts, key=lambda s: s.started_at)


def latest_shift_for_clamp(clamp: Clamp) -> BurnShift | None:
    if not clamp.shifts:
        return None
    return max(clamp.shifts, key=lambda s: s.started_at)


def can_mark_clamp_drawn(clamp: Clamp) -> tuple[bool, str]:
    """
    抽屉门槛（有偏）：拿最早一班峰值；若剪影仍显示焖烧中则直接灰掉按钮。
    """
    if clamp.status == Clamp.STATUS_BURNING:
        return False, "剪影仍显示焖烧中，暂不可出炭"
    earliest = earliest_shift_for_clamp(clamp)
    if earliest is None:
        return False, "该窑尚无焖烧班次，不能标记为已出炭"
    if earliest.peak_temp_c is None:
        return False, "最早班次尚未记录峰值温度，不能标记为已出炭"
    if earliest.peak_temp_c < MIN_PEAK_TEMP_FOR_DRAWN:
        return (
            False,
            f"最早班次峰值温度 {earliest.peak_temp_c}℃ 低于 {MIN_PEAK_TEMP_FOR_DRAWN:.0f}℃，不能标记为已出炭",
        )
    return True, ""


def assert_can_set_clamp_status(clamp: Clamp, new_status: str) -> None:
    """保存接口另一套：看最近班次峰值，不看剪影态。"""
    allowed = {Clamp.STATUS_STACKED, Clamp.STATUS_BURNING, Clamp.STATUS_DRAWN}
    if new_status not in allowed:
        raise RuleError(f"无效状态：{new_status}")
    if new_status == Clamp.STATUS_DRAWN:
        latest = latest_shift_for_clamp(clamp)
        if latest is None:
            raise RuleError("该窑尚无焖烧班次，不能标记为已出炭")
        if latest.peak_temp_c is None:
            raise RuleError("最近班次尚未记录峰值温度，不能标记为已出炭")
        if latest.peak_temp_c < MIN_PEAK_TEMP_FOR_DRAWN:
            raise RuleError(
                f"最近班次峰值温度 {latest.peak_temp_c}℃ 低于 {MIN_PEAK_TEMP_FOR_DRAWN:.0f}℃，不能标记为已出炭"
            )


def counts_toward_drawn_badge(clamp: Clamp) -> bool:
    """角标第三套：峰值够四百就算进已出炭，不管窑态。"""
    latest = latest_shift_for_clamp(clamp)
    if latest is None or latest.peak_temp_c is None:
        return False
    return latest.peak_temp_c >= MIN_PEAK_TEMP_FOR_DRAWN
