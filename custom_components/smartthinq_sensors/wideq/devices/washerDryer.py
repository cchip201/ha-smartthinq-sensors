"""------------------for Washer and Dryer"""

from __future__ import annotations

import base64
from copy import deepcopy
from enum import IntEnum
import json
import logging

from ..backports.functools import cached_property
from ..const import StateOptions, WashDeviceFeatures
from ..core_async import ClientAsync
from ..core_exceptions import InvalidDeviceStatus
from ..device import Device, DeviceStatus
from ..device_info import DeviceInfo, DeviceType

STATE_WM_POWER_OFF = "STATE_POWER_OFF"
STATE_WM_INITIAL = "STATE_INITIAL"
STATE_WM_PAUSE = "STATE_PAUSE"
STATE_WM_END = ["STATE_END", "STATE_COMPLETE"]
STATE_WM_ERROR_OFF = "OFF"
STATE_WM_ERROR_NO_ERROR = [
    "ERROR_NOERROR",
    "ERROR_NOERROR_TITLE",
    "No Error",
    "No_Error",
]

WM_ROOT_DATA = "washerDryer"
WM_SUB_KEYS = {"mini": "miniState", "Sub": "SubState"}

POWER_STATUS_KEY = ["State", "state"]

CMD_POWER_OFF = [[None, "WMControl"], ["PowerOff", "WMOff"], [None, None]]
CMD_WAKE_UP = [[None, "WMWakeup"], ["OperationWakeUp", "WMWakeup"], [None, None]]
CMD_PAUSE = [[None, "WMControl"], ["OperationStop", "WMStop"], [None, None]]
CMD_REMOTE_START = [
    [None, "WMStart"],
    ["OperationStart", "WMStart"],
    ["Start", "WMStart"],
]

VT_CTRL_CMD = {
    "WMOff": {"cmd": "power", "type": "ABSOLUTE", "value": "POWER_OFF"},
    "WMWakeup": {"cmd": "power", "type": "ABSOLUTE", "value": "POWER_ON"},
    "WMStop": {"cmd": "wmControl", "type": "ABSOLUTE", "value": "PAUSE"},
    "WMStart": {"cmd": "wmControl", "type": "ABSOLUTE", "value": "START"},
}
VT_CTRL_COURSE_INFO = "vt_ctrl_course_info"

BIT_FEATURES = {
    WashDeviceFeatures.ANTICREASE: ["AntiCrease", "antiCrease"],
    WashDeviceFeatures.CHILDLOCK: ["ChildLock", "childLock"],
    WashDeviceFeatures.CREASECARE: ["CreaseCare", "creaseCare"],
    WashDeviceFeatures.DAMPDRYBEEP: ["DampDryBeep", "dampDryBeep"],
    WashDeviceFeatures.DELAYSTART: ["DelayStart", "delayStart"],
    WashDeviceFeatures.DETERGENT: ["DetergentStatus", "ezDetergentState"],
    WashDeviceFeatures.DETERGENTLOW: ["DetergentRemaining", "detergentRemaining"],
    WashDeviceFeatures.DOOROPEN: ["DoorClose", "doorClose"],
    WashDeviceFeatures.DOORLOCK: ["DoorLock", "doorLock"],
    WashDeviceFeatures.HANDIRON: ["HandIron", "handIron"],
    WashDeviceFeatures.MEDICRINSE: ["MedicRinse", "medicRinse"],
    WashDeviceFeatures.PREWASH: ["PreWash", "preWash"],
    WashDeviceFeatures.REMOTESTART: ["RemoteStart", "remoteStart"],
    WashDeviceFeatures.RESERVATION: ["Reservation", "reservation"],
    WashDeviceFeatures.SELFCLEAN: ["SelfClean", "selfClean"],
    WashDeviceFeatures.SOFTENER: ["SoftenerStatus", "ezSoftenerState"],
    WashDeviceFeatures.SOFTENERLOW: ["SoftenerRemaining", "softenerRemaining"],
    WashDeviceFeatures.STEAM: ["Steam", "steam"],
    WashDeviceFeatures.STEAMSOFTENER: ["SteamSoftener", "steamSoftener"],
    WashDeviceFeatures.TURBOWASH: ["TurboWash", "turboWash"],
}

INVERTED_BITS = [WashDeviceFeatures.DOOROPEN]

_LOGGER = logging.getLogger(__name__)


class CourseType(IntEnum):
    """Washer device supported course type."""

    COURSE = 0
    SMARTCOURSE = 1
    OPCOURSE = 2
    DOWNLOADEDCOURSE = 3


_COURSE_KEYS = {
    CourseType.COURSE: [["Course", "APCourse"], ["courseType"]],
    CourseType.OPCOURSE: [["OPCourse"], ["opCourseType"]],
    CourseType.SMARTCOURSE: [
        ["SmartCourse"],
        ["smartCourseType", "downloadedCourseType"],
    ],
    CourseType.DOWNLOADEDCOURSE: [
        ["SmartCourse"],
        ["downloadedCourseType", "smartCourseType"],
    ],
}
_COURSE_TYPE = "courseType"
_CURRENT_COURSE = "Current course"
_DOWNLOAD_DEFAULT_LABEL = "Downloaded"
_DOWNLOAD_SLOT_SENTINEL = "__SMARTCOURSE_SLOT__"
_DOWNLOAD_SKIP_KEYS = {
    "Course",
    "APCourse",
    "ApCourse",
    "SmartCourse",
    "smartCourse",
    "OpCourse",
}
_OPTION_NOT_SELECTED = "Not Selected"
_OPTION_SWITCH_KEYS = {"freshCare", "wrinkleCare"}
_OPTION_LABEL_FALLBACKS = {
    "@WM_TERM_NO_SELECT_W": _OPTION_NOT_SELECTED,
    "@WM_MP_FATIU21019_OPTION_TEMP_TAP_COLD_W": "Tap Cold",
    "@WM_MP_FATIU21019_OPTION_TEMP_COLD_W": "Cold",
    "@WM_MP_FATIU21019_OPTION_TEMP_WARM_W": "Warm",
    "@WM_MP_FATIU21019_OPTION_TEMP_HOT_W": "Hot",
    "@WM_MP_FATIU21019_OPTION_TEMP_EXTRA_HOT_W": "Extra Hot",
    "@WM_MP_FATIU21019_OPTION_SPIN_NO_SPIN_W": "No Spin",
    "@WM_MP_FATIU21019_OPTION_SPIN_LOW_W": "Low",
    "@WM_MP_FATIU21019_OPTION_SPIN_MEDIUM_W": "Medium",
    "@WM_MP_FATIU21019_OPTION_SPIN_HIGH_W": "High",
    "@WM_MP_FATIU21019_OPTION_SPIN_EXTRA_HIGH_W": "Extra High",
    "@WM_MP_FATIU21019_OPTION_SOIL_LIGHT_W": "Light",
    "@WM_MP_FATIU21019_OPTION_SOIL_LIGHT_NORMAL_W": "Light/Normal",
    "@WM_MP_FATIU21019_OPTION_SOIL_NORMAL_W": "Normal",
    "@WM_MP_FATIU21019_OPTION_SOIL_NORMAL_HEAVY_W": "Normal/Heavy",
    "@WM_MP_FATIU21019_OPTION_SOIL_HEAVY_W": "Heavy",
    "@WM_DRY27_DRY_LEVEL_DAMP_W": "Damp",
    "@WM_DRY27_DRY_LEVEL_LESS_W": "Less",
    "@WM_DRY27_DRY_LEVEL_NORMAL_W": "Normal",
    "@WM_DRY27_DRY_LEVEL_MORE_W": "More",
    "@WM_DRY27_DRY_LEVEL_VERY_W": "Very",
    "@WM_DRY27_TEMP_ULTRA_LOW_W": "Low",
    "@WM_DRY27_TEMP_LOW_W": "Med. Low",
    "@WM_DRY27_TEMP_MEDIUM_W": "Medium",
    "@WM_DRY27_TEMP_MID_HIGH_W": "Med. High",
    "@WM_DRY27_TEMP_HIGH_W": "High",
}


class WMDevice(Device):
    """A higher-level interface for washer and dryer."""

    def __init__(
        self,
        client: ClientAsync,
        device_info: DeviceInfo,
        *,
        sub_device: str | None = None,
        sub_key: str | None = None,
    ):
        super().__init__(
            client,
            device_info,
            WMStatus(self, init_run_state=False),
            sub_device=sub_device,
        )
        self._sub_key = sub_key
        if sub_key:
            self._attr_unique_id += f"-{sub_key}"
            self._attr_name += f" {sub_key.capitalize()}"
        self._subkey_device = None
        self._internal_state = None
        self._run_states: list | None = None
        self._is_run_completed = False
        self._course_keys: dict[CourseType, str | None] | None = None
        self._course_infos: dict[str, str] | None = None
        self._smartcourse_infos: dict[str, str] | None = None
        self._selected_course: str | None = None
        self._downloaded_course_override: str | None = None
        self._option_overrides: dict[str, str] = {}
        self._option_maps: dict[str, dict[str, str]] = {}
        self._is_cycle_finishing = False
        self._stand_by = False
        self._remote_start_status: dict | None = None
        self._remote_start_pressed = False
        self._power_on_available: bool = None
        self._initial_bit_start: bool = False

    @cached_property
    def _state_power_off(self):
        """Return native value for power off state."""
        return self._get_runstate_key(STATE_WM_POWER_OFF)

    @cached_property
    def _state_power_on_init(self):
        """Return native value for power on init state."""
        return self._get_runstate_key(STATE_WM_INITIAL)

    @cached_property
    def _state_pause(self):
        """Return native value for pause state."""
        return self._get_runstate_key(STATE_WM_PAUSE)

    @property
    def sub_key(self) -> str | None:
        """Return device sub key."""
        return self._sub_key

    @property
    def subkey_device(self) -> Device | None:
        """Return the available sub key device."""
        return self._subkey_device

    @cached_property
    def _download_panel_label(self) -> str:
        """Return localized label for the Downloaded dial slot."""
        if self.model_info:
            if label_key := self.model_info.config_value("downloadPanelLabel"):
                text = self.get_enum_text(label_key)
                if text and text != label_key and not str(text).startswith("@"):
                    return str(text)
        return _DOWNLOAD_DEFAULT_LABEL

    @cached_property
    def course_list(self) -> list:
        """Return a list of available course."""
        course_infos = self._get_course_infos()
        return [_CURRENT_COURSE, *course_infos.keys()]

    @property
    def selected_course(self) -> str:
        """Return staged course selection, or the active course on the machine when on."""
        if self._selected_course and self._selected_course in self.course_list:
            return self._selected_course
        if self._status and self._status.is_on:
            course_infos = self._get_course_infos()
            n_key = self.get_course_key(CourseType.COURSE)
            raw_course = (
                str(self._status.as_dict.get(n_key))
                if (n_key and self._status.as_dict)
                else None
            )
            dl_ap_id = (
                self.model_info.config_value("downloadCourseAPId")
                if self.model_info
                else None
            ) or "DOWNLOAD"
            if raw_course:
                for name, cid in course_infos.items():
                    if cid == raw_course:
                        return name
                if (
                    raw_course == dl_ap_id
                    and self._download_panel_label in self.course_list
                ):
                    return self._download_panel_label
            smart_active = self._status.current_smartcourse
            if (
                smart_active
                and smart_active != StateOptions.NONE
                and self._download_panel_label in self.course_list
            ):
                return self._download_panel_label
        return _CURRENT_COURSE

    @property
    def has_downloaded_courses(self) -> bool:
        """Return True if device model defines downloadable SmartCourse entries."""
        return bool(self._get_smartcourse_infos())

    @cached_property
    def downloaded_course_list(self) -> list[str]:
        """Return list of downloadable SmartCourse display names."""
        return list(self._get_smartcourse_infos().keys())

    def _current_downloaded_course_id(self) -> str | None:
        """Return the SmartCourse ID currently stored in the device's Downloaded slot."""
        smart_map = self._get_smartcourse_infos()
        valid_ids = set(smart_map.values())
        if not valid_ids:
            return None

        data = self._status.as_dict if self._status else None
        if data:
            for ct in (CourseType.DOWNLOADEDCOURSE, CourseType.SMARTCOURSE):
                ckey = self.get_course_key(ct)
                if ckey and (val := data.get(ckey)) and str(val) in valid_ids:
                    return str(val)

        if self._downloaded_course_override in valid_ids:
            return self._downloaded_course_override

        if self.model_info:
            default_sc = self.model_info.config_value("defaultSmartCourse")
            if default_sc and str(default_sc) in valid_ids:
                return str(default_sc)
        return None

    @property
    def downloaded_course(self) -> str | None:
        """Return display name of the SmartCourse currently stored in the Downloaded slot."""
        smart_id = self._current_downloaded_course_id()
        if not smart_id:
            return None
        for name, cid in self._get_smartcourse_infos().items():
            if cid == smart_id:
                return name
        return None

    @property
    def is_dryer(self) -> bool:
        """Return True if this WMDevice is a dryer."""
        return self.device_info.type in [DeviceType.DRYER, DeviceType.TOWER_DRYER]

    def _iter_all_course_defs(self) -> list[tuple[str, dict, CourseType]]:
        """Return all Course and SmartCourse definitions from model_info."""
        if not self.model_info:
            return []
        entries: list[tuple[str, dict, CourseType]] = []
        for ct in (CourseType.COURSE, CourseType.SMARTCOURSE):
            ckey = self.get_course_key(ct)
            if not ckey:
                continue
            ref_vals = self.model_info.reference_values(ckey) or {}
            for cid, cinfo in ref_vals.items():
                if isinstance(cinfo, dict):
                    entries.append((cid, cinfo, ct))
        return entries

    def has_option_control(
        self, option_key: str, *, dryer_only: bool | None = None
    ) -> bool:
        """Return True if model defines a pre-start selectable control for option_key."""
        if dryer_only is not None and self.is_dryer != dryer_only:
            return False
        if not self.model_info or not self.model_info.is_info_v2:
            return False
        key = self.getkey(option_key)
        if not self.model_info.value_exist(key) or not self.model_info.is_enum_type(key):
            return False
        for _, cinfo, _ in self._iter_all_course_defs():
            for fn in cinfo.get("function", []):
                if fn.get("value") in (option_key, key) and fn.get("selectable"):
                    return True
        return False

    def _format_option_label(
        self, option_key: str, raw_key: str, raw_label: str
    ) -> str:
        """Format an LG enum option label into a clean display string."""
        if (
            raw_label == "@WM_TERM_NO_SELECT_W"
            or raw_key.startswith("NO_")
            or (option_key == "timeDry" and raw_key.endswith("_OFF"))
        ):
            return _OPTION_NOT_SELECTED
        text = self.get_enum_text(raw_label)
        if not text or str(text) == raw_label or str(text).startswith("@"):
            text = _OPTION_LABEL_FALLBACKS.get(str(raw_label), str(text or raw_key))
        text_str = str(text)
        if text_str.startswith("@"):
            stem = text_str.lstrip("@")
            if stem.endswith("_W"):
                stem = stem[:-2]
            for marker in ("_OPTION_TEMP_", "_OPTION_SPIN_", "_OPTION_SOIL_", "_DRY_LEVEL_", "_TEMP_"):
                if marker in stem:
                    stem = stem.split(marker, 1)[1]
                    break
            text_str = stem.replace("_", " ").title()
        if option_key == "timeDry" and text_str.isdigit():
            return f"{text_str} min"
        return text_str

    def get_option_map(self, option_key: str) -> dict[str, str]:
        """Return ordered {display_label: raw_enum_key} for a selectable option."""
        if option_key in self._option_maps:
            return self._option_maps[option_key]
        if not self.model_info or not self.model_info.is_info_v2:
            return {}
        key = self.getkey(option_key)
        if not self.model_info.value_exist(key) or not self.model_info.is_enum_type(key):
            return {}

        used_raw: set[str] = set()
        selectable_raw: set[str] = set()
        for _, cinfo, _ in self._iter_all_course_defs():
            for fn in cinfo.get("function", []):
                if fn.get("value") not in (option_key, key):
                    continue
                if fn.get("default") is not None:
                    used_raw.add(str(fn["default"]))
                for sel in fn.get("selectable") or []:
                    s_str = str(sel)
                    used_raw.add(s_str)
                    selectable_raw.add(s_str)

        val_options = self.model_info.value(key).options
        result: dict[str, str] = {}
        for raw_k, raw_lbl in val_options.items():
            is_no_select = (
                raw_lbl == "@WM_TERM_NO_SELECT_W"
                or raw_k.startswith("NO_")
                or (option_key == "timeDry" and raw_k.endswith("_OFF"))
            )
            if not is_no_select and raw_k not in used_raw:
                continue
            label = self._format_option_label(option_key, raw_k, raw_lbl)
            if label in result:
                prev_raw = result[label]
                if prev_raw not in selectable_raw and raw_k in selectable_raw:
                    result[label] = raw_k
                continue
            result[label] = raw_k

        self._option_maps[option_key] = result
        return result

    def get_option_list(self, option_key: str) -> list[str]:
        """Return ordered option display labels for HA select entity."""
        return list(self.get_option_map(option_key).keys())

    def _resolve_target_course_info(
        self, *, fallback_default: bool = False
    ) -> tuple[str | None, str | None, dict | None]:
        """Return (display_name, course_id, course_info) for staged or active course."""
        if not self.model_info:
            return (None, None, None)
        n_course_key = self.get_course_key(CourseType.COURSE)
        s_course_key = self.get_course_key(CourseType.SMARTCOURSE)
        dl_ap_id = self.model_info.config_value("downloadCourseAPId") or "DOWNLOAD"
        course_infos = self._get_course_infos()

        if self._selected_course and self._selected_course in course_infos:
            cid = course_infos[self._selected_course]
            if cid in (dl_ap_id, _DOWNLOAD_SLOT_SENTINEL) and s_course_key:
                smart_id = self._current_downloaded_course_id()
                sc_info = (
                    self._get_course_details(s_course_key, smart_id)
                    if smart_id
                    else None
                )
                if sc_info:
                    return (self.downloaded_course or self._selected_course, smart_id, sc_info)
            cinfo = self._get_course_details(n_course_key, cid) if n_course_key else None
            return (self._selected_course, cid, cinfo)

        data = self._status.as_dict if self._status else None
        if data:
            for ckey in (n_course_key, s_course_key):
                if not ckey:
                    continue
                raw_id = str(data.get(ckey))
                if ckey == n_course_key and raw_id == dl_ap_id and s_course_key:
                    smart_id = self._current_downloaded_course_id()
                    if smart_id and (
                        sc_info := self._get_course_details(s_course_key, smart_id)
                    ):
                        return (self.downloaded_course or self._download_panel_label, smart_id, sc_info)
                if cinfo := self._get_course_details(ckey, raw_id):
                    disp = next(
                        (nm for nm, val in course_infos.items() if val == raw_id),
                        raw_id,
                    )
                    return (disp, raw_id, cinfo)

        if fallback_default and n_course_key:
            def_cid = self.model_info.config_value(
                f"default{self._getcmdkey('Course')}"
            )
            if def_cid and (cinfo := self._get_course_details(n_course_key, def_cid)):
                disp = next(
                    (nm for nm, val in course_infos.items() if val == def_cid),
                    str(def_cid),
                )
                return (disp, str(def_cid), cinfo)

        return (None, None, None)

    @staticmethod
    def _course_func_entry(course_info: dict | None, option_key: str) -> dict | None:
        """Return matching function dict for option_key inside course_info."""
        if not course_info:
            return None
        for fn in course_info.get("function", []):
            if fn.get("value") == option_key:
                return fn
        return None

    def get_option_value(self, option_key: str) -> str | None:
        """Return staged, selected-course default, or live display option."""
        _ = self.select_course_enabled
        opt_map = self.get_option_map(option_key)
        if not opt_map:
            return None
        rev_map = {raw_k: lbl for lbl, raw_k in opt_map.items()}

        if (override := self._option_overrides.get(option_key)) and override in rev_map:
            return rev_map[override]

        if self._selected_course:
            _, _, cinfo = self._resolve_target_course_info()
            fn = self._course_func_entry(cinfo, option_key)
            if fn and (def_val := fn.get("default")) is not None:
                if str(def_val) in rev_map:
                    return rev_map[str(def_val)]
            if _OPTION_NOT_SELECTED in opt_map:
                return _OPTION_NOT_SELECTED

        if self._status and self._status.as_dict:
            raw_live = self._status.as_dict.get(self.getkey(option_key))
            if raw_live is not None and str(raw_live) in rev_map:
                return rev_map[str(raw_live)]

        if _OPTION_NOT_SELECTED in opt_map:
            return _OPTION_NOT_SELECTED
        return None

    def get_switch_option_value(self, option_key: str) -> bool:
        """Return staged, selected-course default, or live boolean state for an enum switch option."""
        _ = self.select_course_enabled
        if override := self._option_overrides.get(option_key):
            return str(override).endswith("_ON")

        if self._selected_course:
            _, _, cinfo = self._resolve_target_course_info()
            fn = self._course_func_entry(cinfo, option_key)
            if fn and fn.get("default") is not None:
                return str(fn["default"]).endswith("_ON")
            return False

        if self._status and self._status.as_dict:
            raw_live = self._status.as_dict.get(self.getkey(option_key))
            if raw_live is not None:
                return str(raw_live).endswith("_ON")
        return False

    def _allowed_courses_for_option(self, option_key: str) -> list[str]:
        """Return standard course display names that allow changing option_key."""
        n_course_key = self.get_course_key(CourseType.COURSE)
        if not n_course_key:
            return []
        allowed: list[str] = []
        for disp, cid in self._get_course_infos().items():
            cinfo = self._get_course_details(n_course_key, cid)
            fn = self._course_func_entry(cinfo, option_key)
            if fn and fn.get("selectable"):
                allowed.append(disp)
        return allowed

    async def set_course_option(
        self, option_key: str, display_value: str, friendly_label: str = "Option"
    ) -> None:
        """Stage a pre-start course option to be sent on the next Remote Start."""
        if not self.select_course_enabled:
            raise InvalidDeviceStatus(
                f"{friendly_label} can only be changed before starting when Remote Start is on at the machine"
            )
        opt_map = self.get_option_map(option_key)
        if display_value not in opt_map:
            raise ValueError(f"Invalid {friendly_label}: {display_value}")

        if display_value == _OPTION_NOT_SELECTED:
            self._option_overrides.pop(option_key, None)
            return

        raw_val = opt_map[display_value]

        if option_key == "timeDry":
            _, _, cur_info = self._resolve_target_course_info(fallback_default=True)
            cur_fn = self._course_func_entry(cur_info, "timeDry")
            if not (cur_fn and cur_fn.get("selectable")):
                td_courses = self._allowed_courses_for_option("timeDry")
                if td_courses:
                    self._selected_course = td_courses[0]
                    self._option_overrides.pop("dryLevel", None)

        course_name, _, cinfo = self._resolve_target_course_info(fallback_default=True)
        if cinfo:
            fn = self._course_func_entry(cinfo, option_key)
            selectable = [str(x) for x in (fn.get("selectable") or [])] if fn else []
            if not selectable:
                allowed_courses = self._allowed_courses_for_option(option_key)
                hint = (
                    f"; adjustable on {', '.join(allowed_courses)}"
                    if allowed_courses
                    else ""
                )
                raise InvalidDeviceStatus(
                    f"{course_name or 'Selected cycle'} does not allow changing {friendly_label}{hint}"
                )
            if raw_val not in selectable:
                rev_map = {rk: lbl for lbl, rk in opt_map.items()}
                allowed_labels = [rev_map[rk] for rk in selectable if rk in rev_map]
                raise InvalidDeviceStatus(
                    f"{course_name or 'Selected cycle'} allows {friendly_label}: {', '.join(allowed_labels)}"
                )

        self._option_overrides[option_key] = raw_val

    async def set_switch_option(
        self, option_key: str, turn_on: bool, friendly_label: str = "Option"
    ) -> None:
        """Stage a pre-start boolean enum option (freshCare / wrinkleCare)."""
        if not self.select_course_enabled:
            raise InvalidDeviceStatus(
                f"{friendly_label} can only be changed before starting when Remote Start is on at the machine"
            )
        key = self.getkey(option_key)
        val_options = self.model_info.value(key).options
        suffix = "_ON" if turn_on else "_OFF"
        raw_val = next((rk for rk in val_options if rk.endswith(suffix)), None)
        if not raw_val:
            raise ValueError(f"Unsupported {friendly_label} state: {turn_on}")

        course_name, _, cinfo = self._resolve_target_course_info(fallback_default=True)
        if cinfo:
            fn = self._course_func_entry(cinfo, option_key)
            selectable = [str(x) for x in (fn.get("selectable") or [])] if fn else []
            if not selectable or raw_val not in selectable:
                raise InvalidDeviceStatus(
                    f"{course_name or 'Selected cycle'} does not support changing {friendly_label}"
                )

        self._option_overrides[option_key] = raw_val

    def _apply_staged_options_to_dict(self, course_info: dict, ret_data: dict) -> None:
        """Apply valid staged pre-start option overrides onto a ThinQ2 payload dict."""
        if not self._option_overrides or not course_info:
            return
        for func_key in course_info.get("function", []):
            ckey = func_key.get("value")
            selectable = [str(x) for x in (func_key.get("selectable") or [])]
            if ckey and ckey in self._option_overrides and self._option_overrides[ckey] in selectable:
                chosen = self._option_overrides[ckey]
                ret_data[ckey] = chosen
                if ckey == "timeDry" and "moreLessTime" in ret_data:
                    tail = chosen.rsplit("_", 1)[-1]
                    if tail.isdigit():
                        ret_data["moreLessTime"] = int(tail)

    def _collect_vtctrl_staged_options(
        self, course_info: dict | None
    ) -> list[dict[str, str]]:
        """Build vtCtrl ABSOLUTE command items for valid staged pre-start overrides."""
        if not self._option_overrides or not course_info:
            return []
        items: list[dict[str, str]] = []
        for func_key in course_info.get("function", []):
            ckey = func_key.get("value")
            selectable = [str(x) for x in (func_key.get("selectable") or [])]
            if ckey and ckey in self._option_overrides and self._option_overrides[ckey] in selectable:
                out_key = "reserveTimeMinute" if ckey == "reserveTimeHour" else ckey
                items.append(
                    {
                        "cmd": out_key,
                        "type": "ABSOLUTE",
                        "value": str(self._option_overrides[ckey]),
                    }
                )
        return items

    @property
    def run_state(self) -> str:
        """Return calculated pre state."""
        if not self._run_states:
            return STATE_WM_POWER_OFF
        return self._run_states[0]

    @property
    def pre_state(self) -> str:
        """Return calculated pre state."""
        if not self._run_states:
            return STATE_WM_POWER_OFF
        return self._run_states[-1]

    @property
    def is_run_completed(self) -> bool:
        """Return device run completed state."""
        result = self._status.is_run_completed if self._status else False
        if result:
            if not self._is_run_completed:
                self._is_cycle_finishing = False
                self._is_run_completed = True
            return True

        run_state = self.run_state
        pre_state = self.pre_state
        if self._is_run_completed and STATE_WM_POWER_OFF in run_state:
            self._is_cycle_finishing = False
            return True

        if (
            (self._is_cycle_finishing or self._is_run_completed)
            and any(
                state in run_state for state in [STATE_WM_POWER_OFF, STATE_WM_INITIAL]
            )
            and not any(
                state in pre_state for state in [STATE_WM_POWER_OFF, STATE_WM_INITIAL]
            )
        ):
            if not self._is_run_completed:
                self._is_cycle_finishing = False
                self._is_run_completed = True
        else:
            self._is_run_completed = False

        return self._is_run_completed

    async def init_device_info(self) -> bool:
        """Initialize the information for the device"""
        if result := await super().init_device_info():
            self._init_subkey_device()
        return result

    def _init_subkey_device(self) -> None:
        """Initialize the available sub key device."""
        if self._sub_key or self._subkey_device or not self.model_info:
            return
        for key, val in WM_SUB_KEYS.items():
            if self.model_info.value_exist(val):
                # we check for value in the snapshot if available
                if snapshot := self.device_info.snapshot:
                    if payload := snapshot.get(self._sub_device or WM_ROOT_DATA):
                        if val not in payload:
                            continue
                self._subkey_device = WMDevice(
                    self.client,
                    self.device_info,
                    sub_device=self._sub_device,
                    sub_key=key,
                )
                return

    def update_internal_state(self, state):
        """Update internal state used by sub key device."""
        if not self._sub_key:
            return
        self._internal_state = state

    def save_run_states(self, run_state: str, is_pre_state=False) -> None:
        """Calculate the pre state based on run_state."""
        if STATE_WM_POWER_OFF in run_state:
            run_state = STATE_WM_POWER_OFF
        if not self._run_states:
            if is_pre_state:
                return
            self._run_states = [run_state]
        if is_pre_state:
            if len(self._run_states) > 1:
                self._run_states[1] = run_state
            else:
                self._run_states.append(run_state)
            return
        if run_state == self._run_states[0]:
            return
        self._run_states.insert(0, run_state)
        if len(self._run_states) > 2:
            self._run_states = self._run_states[:2]

    def getkey(self, key: str | None) -> str | None:
        """Add subkey prefix to a key if required."""
        if not (key and self._sub_key):
            return key
        return f"{self._sub_key}{key[0].upper()}{key[1:]}"

    def _getcmdkey(self, key: str | None) -> str | None:
        """Add subkey prefix to a command key if required."""
        if not (key and self._sub_key):
            return key
        return f"{self._sub_key.capitalize()}{key}"

    def _update_status(self, key, value):
        if self._status and value:
            self._status.update_status(key, value)

    def _update_opt_bit(self, opt_name: str, opt_val: str, bit_name: str, bit_val: int):
        """Update the option bit with correct value."""
        if self.model_info.is_info_v2:
            return None

        option_val = int(opt_val)
        if (bit_index := self.model_info.bit_index(opt_name, bit_name)) is not None:
            if bit_val:
                new_val = option_val | (2**bit_index)
            else:
                new_val = option_val ^ (option_val & (2**bit_index))
            return str(new_val)

        return None

    def _get_course_key(self, course_type: CourseType) -> str | None:
        """Return the course key for specific device."""
        if self.model_info.is_info_v2:
            course_type_keys = _COURSE_KEYS[course_type][1]
            for key in course_type_keys:
                if course_key := self.model_info.config_value(self.getkey(key)):
                    if self.model_info.value_exist(course_key):
                        return course_key
        else:
            course_keys = _COURSE_KEYS[course_type][0]
            for key in course_keys:
                course_key = self.getkey(key)
                if self.model_info.value_exist(course_key):
                    return course_key

        return None

    def get_course_key(self, course_type: CourseType) -> str | None:
        """Return the course key for specific device."""
        if self._course_keys is None:
            if not self.model_info:
                return None
            self._course_keys = {key: self._get_course_key(key) for key in _COURSE_KEYS}
        return self._course_keys[course_type]

    def _get_smartcourse_infos(self) -> dict[str, str]:
        """Return a dict of downloadable SmartCourse display names to IDs."""
        if self._smartcourse_infos is not None:
            return self._smartcourse_infos

        if not self.model_info:
            self._smartcourse_infos = {}
            return {}
        s_course_key = self.get_course_key(CourseType.SMARTCOURSE)
        if not s_course_key:
            self._smartcourse_infos = {}
            return {}
        smart_courses = self.model_info.reference_values(s_course_key)
        if not smart_courses:
            self._smartcourse_infos = {}
            return {}

        ret_val: dict[str, str] = {}
        for key, value in smart_courses.items():
            if not isinstance(value, dict):
                continue
            if value.get("downloadEnable") is False:
                continue
            if enum_name := value.get("name"):
                name = self.get_enum_text(enum_name)
                if name == enum_name or str(name).startswith("@"):
                    name = value.get("_comment", enum_name)
            else:
                name = value.get("_comment", key)
            ret_val[name] = key

        self._smartcourse_infos = ret_val
        return ret_val

    def _get_course_infos(self) -> dict:
        """Return a dict with available courses."""
        if self._course_infos is not None:
            return self._course_infos

        if not (course_key := self.get_course_key(CourseType.COURSE)):
            self._course_infos = {}
            return {}
        if not (course_infos := self.model_info.reference_values(course_key)):
            self._course_infos = {}
            return {}

        dl_ap_id = (
            self.model_info.config_value("downloadCourseAPId")
            if self.model_info
            else None
        ) or "DOWNLOAD"
        has_dl_entry = False
        ret_val = {}
        for key, value in course_infos.items():
            if key == dl_ap_id:
                has_dl_entry = True
            if enum_name := value.get("name"):
                name = self.get_enum_text(enum_name)
                if name == enum_name or str(name).startswith("@"):
                    name = value.get("_comment", enum_name)
            elif key == dl_ap_id:
                name = self._download_panel_label
            else:
                name = value.get("_comment", key)
            ret_val[name] = key

        if not has_dl_entry and self._get_smartcourse_infos():
            dl_label = self._download_panel_label
            if dl_label not in ret_val:
                ret_val[dl_label] = _DOWNLOAD_SLOT_SENTINEL

        self._course_infos = ret_val
        return ret_val

    def _get_course_details(self, course_key, course_id):
        """Get definition for a specific course ID."""
        if course_key is None:
            return None
        if courses := self.model_info.reference_values(course_key):
            return courses.get(course_id)
        return None

    def _prepare_course_info(
        self,
        data: dict,
        course_id: str,
        course_info: dict,
        course_type: CourseType,
        course_set: bool,
        n_course_key: str,
        s_course_key: str | None,
    ) -> dict:
        """Prepare the course info used to run the command."""

        ret_data = deepcopy(data)

        # Prepare the course data initializing option for infoV1 device
        option_keys = self.model_info.option_keys(self._sub_key)
        if not self.model_info.is_info_v2:
            for opt_name in option_keys:
                ret_data[opt_name] = data.get(opt_name, "0")

        if _COURSE_TYPE in course_info:
            ret_data[_COURSE_TYPE] = course_info[_COURSE_TYPE]

        if course_type == CourseType.COURSE:
            ret_data[n_course_key] = course_id
            if s_course_key:
                ret_data[s_course_key] = 0
        elif course_type == CourseType.SMARTCOURSE:
            ret_data[n_course_key] = 0
            ret_data[s_course_key] = course_id
            for key in ["Course", "APCourse"]:
                if key in course_info:
                    ret_data[n_course_key] = course_info[key]
                    break

        if op_course_key := self.get_course_key(CourseType.OPCOURSE):
            ref_opcourse_key = (
                "OpCourse" if self.model_info.is_info_v2 else op_course_key
            )
            if ref_opcourse_key in course_info:
                ret_data[op_course_key] = course_info[ref_opcourse_key]
            elif self.model_info.is_info_v2:
                ret_data.pop(op_course_key, None)

        for func_key in course_info.get("function", []):
            ckey = func_key.get("value")
            cdata = func_key.get("default")
            if not ckey or cdata is None:
                continue
            opt_set = False
            for opt_name in option_keys:
                if opt_name not in ret_data:
                    continue
                opt_val = ret_data[opt_name]
                new_val = self._update_opt_bit(opt_name, opt_val, ckey, int(cdata))
                if new_val is not None:
                    opt_set = True
                    if not course_set:
                        ret_data[opt_name] = new_val
                    break
            if opt_set or (course_set and ckey in ret_data):
                continue
            ret_data[ckey] = cdata

        self._apply_staged_options_to_dict(course_info, ret_data)

        if not course_set:
            ret_data[VT_CTRL_COURSE_INFO] = course_info

        _LOGGER.debug("Prepared course data: %s", ret_data)
        return ret_data

    def _update_course_info(self) -> dict:
        """
        Save information in the data payload for a specific course
        or default course if not already available.
        """
        data = None
        if self._initial_bit_start:
            data = self._remote_start_status
        elif self._status:
            self._selected_course = None
            data = self._status.as_dict

        if not data:
            raise ValueError("Course info not available")

        course_type = CourseType.COURSE
        n_course_key = self.get_course_key(CourseType.COURSE)
        s_course_key = self.get_course_key(CourseType.SMARTCOURSE)
        if self.model_info.is_info_v2:
            def_course_id = self.model_info.config_value(
                f"default{self._getcmdkey('Course')}"
            )
        else:
            def_course_id = str(self.model_info.config_value("defaultCourseId"))

        dl_ap_id = (
            self.model_info.config_value("downloadCourseAPId")
            if self.model_info
            else None
        ) or "DOWNLOAD"

        # Search valid course Info
        if self._selected_course:
            course_id = self._get_course_infos().get(self._selected_course)
        else:
            course_id = None
        course_info = None
        course_set = False
        if course_id is None:
            # check if this course is defined in data payload
            for course_key in [n_course_key, s_course_key]:
                if not course_key:
                    continue
                raw_id = str(data.get(course_key))
                if course_key == n_course_key and raw_id == dl_ap_id and s_course_key:
                    smart_id = self._current_downloaded_course_id()
                    if smart_id and (
                        sc_info := self._get_course_details(s_course_key, smart_id)
                    ):
                        course_id = smart_id
                        course_info = sc_info
                        course_type = CourseType.SMARTCOURSE
                        course_set = True
                        break
                course_id = raw_id
                if course_info := self._get_course_details(course_key, course_id):
                    if course_key == s_course_key:
                        course_type = CourseType.SMARTCOURSE
                    course_set = True
                    break
        elif course_id in (dl_ap_id, _DOWNLOAD_SLOT_SENTINEL) and s_course_key:
            smart_id = self._current_downloaded_course_id()
            if smart_id and (
                sc_info := self._get_course_details(s_course_key, smart_id)
            ):
                course_id = smart_id
                course_info = sc_info
                course_type = CourseType.SMARTCOURSE
            elif course_id != _DOWNLOAD_SLOT_SENTINEL:
                course_info = self._get_course_details(n_course_key, course_id)
        else:
            course_info = self._get_course_details(n_course_key, course_id)

        if not course_info:
            course_id = def_course_id
            course_info = self._get_course_details(n_course_key, course_id)

        if not course_info:
            raise ValueError("Course info not available")

        # Save information for specific or default course
        return self._prepare_course_info(
            data,
            course_id,
            course_info,
            course_type,
            course_set,
            n_course_key,
            s_course_key,
        )

    def _prepare_vtctrl_course_info(self) -> list:
        """Prepare course info for vtctrl command."""
        vt_cmd_data = []
        course_data = self._update_course_info()
        if course_info := course_data.get(VT_CTRL_COURSE_INFO):
            for func_key in course_info.get("function", []):
                ckey = func_key.get("value")
                defdata = func_key.get("default")
                cdata = course_data.get(ckey, defdata)
                if not ckey or cdata is None:
                    continue
                vt_cmd_data.append(
                    {"cmd": ckey, "type": "ABSOLUTE", "value": str(cdata)}
                )

        return vt_cmd_data

    def _prepare_command_v1(self, cmd, key):
        """Prepare command for specific ThinQ1 device."""
        encode = cmd.pop("encode", False)

        str_data = ""
        if "data" in cmd:
            str_data = cmd["data"]
            option_keys = self.model_info.option_keys(self._sub_key)
            status_data = self._update_course_info()

            for dt_key, dt_value in status_data.items():
                repl_key = f"{{{{{dt_key}}}}}"
                if repl_key not in str_data:
                    continue
                # for start command we set initial bit to 1
                if key and key == "Start" and dt_key in option_keys:
                    bit_val = 1 if self._initial_bit_start else 0
                    new_value = self._update_opt_bit(
                        dt_key, dt_value, "InitialBit", bit_val
                    )
                    if new_value is not None:
                        dt_value = new_value
                str_data = str_data.replace(repl_key, str(dt_value))
            _LOGGER.debug("Command data content: %s", str_data)
            if encode:
                cmd["format"] = "B64"
                str_list = json.loads(str_data)
                str_data = base64.b64encode(bytes(str_list)).decode("ascii")

        return {**cmd, "data": str_data}

    def _prepare_command_v2(self, cmd, key: str):
        """Prepare command for specific ThinQ2 device."""
        data_set = cmd.pop("data", None)
        if not data_set:
            return cmd

        res_data_set = None
        if key and "WMStart" in key and WM_ROOT_DATA in data_set:
            status_data = self._update_course_info()
            n_course_key = self.get_course_key(CourseType.COURSE)
            s_course_key = self.get_course_key(CourseType.SMARTCOURSE)
            op_course_key = self.get_course_key(CourseType.OPCOURSE)
            cmd_data_set = {}

            if _COURSE_TYPE in status_data:
                cmd_data_set[_COURSE_TYPE] = status_data[_COURSE_TYPE]

            for cmd_key, cmd_value in data_set[WM_ROOT_DATA].items():
                if cmd_key == _COURSE_TYPE:
                    continue
                if cmd_key in ["course", "Course", "ApCourse"]:
                    course_data = status_data.get(n_course_key, 0)
                    cmd_data_set[n_course_key] = course_data or "NOT_SELECTED"
                elif cmd_key in ["smartCourse", "SmartCourse"] or (
                    s_course_key and cmd_key == s_course_key
                ):
                    if s_course_key:
                        course_data = status_data.get(s_course_key, 0)
                        cmd_data_set[s_course_key] = course_data or "NOT_SELECTED"
                    else:
                        cmd_data_set[cmd_key] = "NOT_SELECTED"
                elif cmd_key in ["OpCourse"]:
                    if op_course_key:
                        if course_data := status_data.get(op_course_key):
                            cmd_data_set[op_course_key] = course_data
                    else:
                        cmd_data_set[cmd_key] = "NOT_SELECTED"
                elif cmd_key == self.getkey("initialBit"):
                    prefix = f"{self._sub_key.upper()}_" if self._sub_key else ""
                    if self._initial_bit_start:
                        cmd_data_set[cmd_key] = f"{prefix}INITIAL_BIT_ON"
                    else:
                        cmd_data_set[cmd_key] = f"{prefix}INITIAL_BIT_OFF"
                else:
                    cmd_data_set[cmd_key] = status_data.get(cmd_key, cmd_value)
            res_data_set = {WM_ROOT_DATA: cmd_data_set}

        return {
            **cmd,
            "dataKey": None,
            "dataValue": None,
            "dataSetList": res_data_set or data_set,
            "dataGetList": None,
        }

    def _prepare_command_vtctrl(self, cmd: dict, command: str):
        """Prepare vtCtrl command for specific ThinQ2 device."""
        data_set: dict = cmd.pop("data", None)
        if not data_set:
            return cmd

        cmd_data_set = {}
        vt_cmd_data = []
        if command == "WMStart" and self.model_info.config_value("uniProtocol"):
            is_paused = (
                not self._initial_bit_start
                and self._status is not None
                and self._status.internal_run_state == self._state_pause
            )
            ctrl_val = "RESUME" if is_paused else "START"
            if self._initial_bit_start and self._selected_course:
                dl_ap_id = self.model_info.config_value("downloadCourseAPId") or "DOWNLOAD"
                c_id = self._get_course_infos().get(self._selected_course)
                if c_id in (dl_ap_id, _DOWNLOAD_SLOT_SENTINEL):
                    smart_id = self._current_downloaded_course_id()
                    s_key = self.get_course_key(CourseType.SMARTCOURSE)
                    sc_info = (
                        self._get_course_details(s_key, smart_id)
                        if (s_key and smart_id)
                        else None
                    )
                    vt_cmd_data.append(
                        {"cmd": "course", "type": "ABSOLUTE", "value": str(dl_ap_id)}
                    )
                    if smart_id and sc_info:
                        vt_cmd_data.append(
                            {
                                "cmd": "downloadCourseData",
                                "type": "ABSOLUTE",
                                "value": str(smart_id),
                            }
                        )
                        base_c = (
                            sc_info.get("Course")
                            or sc_info.get("APCourse")
                            or self.model_info.config_value("defaultCourse")
                        )
                        if base_c:
                            vt_cmd_data.append(
                                {
                                    "cmd": "baseDownloadCourseData",
                                    "type": "ABSOLUTE",
                                    "value": str(base_c),
                                }
                            )
                elif c_id:
                    vt_cmd_data.append(
                        {"cmd": "course", "type": "ABSOLUTE", "value": str(c_id)}
                    )
            if self._initial_bit_start and self._option_overrides:
                _, _, target_cinfo = self._resolve_target_course_info(
                    fallback_default=True
                )
                vt_cmd_data.extend(self._collect_vtctrl_staged_options(target_cinfo))
            vt_cmd_data.append(
                {"cmd": "wmControl", "type": "ABSOLUTE", "value": ctrl_val}
            )
        else:
            if self._initial_bit_start and command == "WMStart":
                if vt_course_data := self._prepare_vtctrl_course_info():
                    vt_cmd_data = vt_course_data

            vt_cmd_data.append(VT_CTRL_CMD[command])

        ctrl_target = None if not self._sub_device else self._sub_device.upper()
        for cmd_key, cmd_val in data_set.items():
            if cmd_key == "ctrlTarget":
                cmd_data_set[cmd_key] = [ctrl_target] if ctrl_target else cmd_val
            elif cmd_key == "reqDevType":
                cmd_data_set[cmd_key] = "APP"
            elif cmd_key == "vtData":
                vt_data = {}
                for dt_key in cmd_val.keys():
                    vt_data[ctrl_target or dt_key] = vt_cmd_data
                cmd_data_set[cmd_key] = vt_data
            else:
                cmd_data_set[cmd_key] = cmd_val

        return {
            **cmd,
            "dataKey": None,
            "dataValue": None,
            "dataSetList": cmd_data_set,
            "dataGetList": None,
        }

    def _prepare_command(self, ctrl_key, command, key, value):
        """Prepare command for specific device."""
        cmd = None
        vt_ctrl = True
        if command in VT_CTRL_CMD:
            cmd = self.model_info.get_control_cmd("vtCtrl", "vtCtrl")
        if not cmd:
            vt_ctrl = False
            cmd = self.model_info.get_control_cmd(command, ctrl_key)

        if not cmd:
            return None

        if self.model_info.is_info_v2:
            if vt_ctrl:
                return self._prepare_command_vtctrl(cmd, command)
            return self._prepare_command_v2(cmd, key)
        return self._prepare_command_v1(cmd, key)

    def _get_runstate_key(self, state_name: str) -> str | None:
        """Return the run state key based on state name."""
        key = self.getkey(self._get_state_key(POWER_STATUS_KEY))
        if not self.model_info.is_enum_type(key):
            return None
        mapping = self.model_info.value(key).options
        for key, val in mapping.items():
            if state_name in val:
                return key
        return None

    @property
    def stand_by(self) -> bool:
        """Return if device is in standby mode."""
        return self._stand_by

    @property
    def remote_start_enabled(self) -> bool:
        """Return if remote start is enabled."""
        if self._remote_start_pressed or self.stand_by or not self._status.is_on:
            return False
        if self._remote_start_status is None:
            return False
        if self._status.internal_run_state in [
            self._state_power_on_init,
            self._state_pause,
        ]:
            return True
        return False

    @property
    def pause_enabled(self) -> bool:
        """Return if pause is enabled."""
        if self.stand_by or not self._status.is_on:
            return False
        if self._remote_start_status is None:
            return False
        if self._status.internal_run_state not in [
            self._state_power_on_init,
            self._state_pause,
        ]:
            return True
        return False

    @property
    def select_course_enabled(self) -> bool:
        """Return if selecr course is enabled."""
        enabled = self._initial_bit_start and self.remote_start_enabled
        if not enabled:
            if self._selected_course:
                self._selected_course = None
            if self._option_overrides:
                self._option_overrides.clear()
        return enabled

    @property
    def course_display_enabled(self) -> bool:
        """Return True when the appliance is on so active/selected course is visible."""
        if not self._status:
            return False
        return bool(self._status.is_on and not self.stand_by)

    @property
    def downloaded_course_display_enabled(self) -> bool:
        """Return True when downloaded course slot can be read or written."""
        if not (self.has_downloaded_courses and self._status and self.model_info):
            return False
        if self.download_course_enabled:
            return True
        return bool(self._status.is_on and not self.stand_by)

    @property
    def download_course_enabled(self) -> bool:
        """Return True if downloading a SmartCourse into the device slot is allowed."""
        if not (self.has_downloaded_courses and self._status and self.model_info):
            return False
        child_lock = self._status.device_features.get(WashDeviceFeatures.CHILDLOCK)
        if child_lock is None:
            cl_key = "childLock" if self.model_info.is_info_v2 else "ChildLock"
            child_lock = self._status.lookup_bit(
                self.getkey(cl_key), sub_key=self._sub_key
            )
        if child_lock == StateOptions.ON:
            return False
        if not self._status.is_on:
            return bool(
                self.model_info.is_info_v2
                and self.model_info.config_value("powerOffDownload")
                and not self.stand_by
            )
        if self._status.internal_run_state == self._state_power_on_init:
            return True
        if self._status.internal_run_state == self._state_pause:
            return self.model_info.config_value("changeCourseInPause") is not False
        return False

    async def _send_download_course(self, smart_id: str, course_info: dict) -> None:
        """Send ThinQ2 download command (vtCtrl on uniProtocol, else WMDownload)."""
        if not self.model_info or not self.model_info.is_info_v2:
            return

        if self.model_info.config_value("uniProtocol"):
            cmd = self.model_info.get_control_cmd("vtCtrl", "vtCtrl")
            if not cmd:
                raise ValueError("vtCtrl command definition not available")
            data_set = cmd.pop("data", None) or {}
            dl_ap_id = self.model_info.config_value("downloadCourseAPId") or "DOWNLOAD"
            base_course = (
                course_info.get("Course")
                or course_info.get("APCourse")
                or self.model_info.config_value("defaultCourse")
            )
            vt_cmd_data = [
                {
                    "cmd": "downloadCourseData",
                    "type": "ABSOLUTE",
                    "value": str(smart_id),
                },
                {"cmd": "course", "type": "ABSOLUTE", "value": str(dl_ap_id)},
            ]
            if base_course:
                vt_cmd_data.append(
                    {
                        "cmd": "baseDownloadCourseData",
                        "type": "ABSOLUTE",
                        "value": str(base_course),
                    }
                )
            for func_key in course_info.get("function", []):
                ckey = func_key.get("value")
                defdata = func_key.get("default")
                selectable = [str(x) for x in (func_key.get("selectable") or [])]
                if ckey in self._option_overrides and self._option_overrides[ckey] in selectable:
                    defdata = self._option_overrides[ckey]
                if not ckey or defdata is None:
                    continue
                out_key = "reserveTimeMinute" if ckey == "reserveTimeHour" else ckey
                vt_cmd_data.append(
                    {"cmd": out_key, "type": "ABSOLUTE", "value": str(defdata)}
                )

            ctrl_target = None if not self._sub_device else self._sub_device.upper()
            cmd_data_set = {}
            for cmd_key, cmd_val in data_set.items():
                if cmd_key == "ctrlTarget":
                    cmd_data_set[cmd_key] = [ctrl_target] if ctrl_target else cmd_val
                elif cmd_key == "reqDevType":
                    cmd_data_set[cmd_key] = "APP"
                elif cmd_key == "vtData":
                    vt_data = {}
                    for dt_key in cmd_val.keys():
                        vt_data[ctrl_target or dt_key] = vt_cmd_data
                    cmd_data_set[cmd_key] = vt_data
                else:
                    cmd_data_set[cmd_key] = cmd_val

            full_cmd = {
                **cmd,
                "dataKey": None,
                "dataValue": None,
                "dataSetList": cmd_data_set,
                "dataGetList": None,
            }
            await self._set_control(full_cmd)
            return

        dl_cmd_name = self._getcmdkey("WMDownload")
        cmd = self.model_info.get_control_cmd(dl_cmd_name, dl_cmd_name)
        if not cmd:
            raise ValueError(f"{dl_cmd_name} command definition not available")
        data_set = cmd.pop("data", None) or {}
        tmpl_wd = data_set.get(WM_ROOT_DATA, {})

        n_course_key = self.get_course_key(CourseType.COURSE)
        s_course_key = self.get_course_key(CourseType.SMARTCOURSE)
        op_course_key = self.get_course_key(CourseType.OPCOURSE)

        payload: dict = {}
        base_course = (
            course_info.get("Course")
            or course_info.get("APCourse")
            or "NOT_SELECTED"
        )
        if n_course_key:
            payload[n_course_key] = base_course
        if s_course_key:
            payload[s_course_key] = smart_id
        if op_course_key and "OpCourse" in course_info:
            payload[op_course_key] = course_info["OpCourse"]

        for func_key in course_info.get("function", []):
            ckey = func_key.get("value")
            defdata = func_key.get("default")
            selectable = [str(x) for x in (func_key.get("selectable") or [])]
            if ckey in self._option_overrides and self._option_overrides[ckey] in selectable:
                defdata = self._option_overrides[ckey]
            if ckey and defdata is not None:
                payload[ckey] = defdata

        if not self._sub_key:
            payload[_COURSE_TYPE] = course_info.get(_COURSE_TYPE, "SmartCourse")

        for tmpl_k, tmpl_v in tmpl_wd.items():
            if tmpl_k in _DOWNLOAD_SKIP_KEYS:
                continue
            if tmpl_k not in payload:
                payload[tmpl_k] = tmpl_v

        if "reserveTimeHour" in payload or "reserveTimeMinute" in payload:
            payload["reserveTimeHour"] = 0
            payload["reserveTimeMinute"] = 0

        prefix = f"{self._sub_key.upper()}_" if self._sub_key else ""
        payload[self.getkey("initialBit")] = f"{prefix}INITIAL_BIT_OFF"
        rs_key = self.getkey("remoteStart")
        cur_rs = (
            self._status.as_dict.get(rs_key) if self._status else None
        ) or tmpl_wd.get(rs_key, f"{prefix}REMOTE_START_OFF")
        payload[rs_key] = cur_rs

        full_cmd = {
            **cmd,
            "dataKey": None,
            "dataValue": None,
            "dataSetList": {WM_ROOT_DATA: payload},
            "dataGetList": None,
        }
        await self._set_control(full_cmd)

    async def select_downloaded_course(self, course_name: str) -> None:
        """Download a SmartCourse into the device's Downloaded slot."""
        if not self.download_course_enabled:
            raise InvalidDeviceStatus()

        smart_id = self._get_smartcourse_infos().get(course_name)
        if not smart_id:
            raise ValueError(f"Invalid downloaded course: {course_name}")
        s_course_key = self.get_course_key(CourseType.SMARTCOURSE)
        course_info = self._get_course_details(s_course_key, smart_id)
        if not course_info:
            raise ValueError(f"Downloaded course info not available: {course_name}")

        await self._send_download_course(smart_id, course_info)
        self._downloaded_course_override = smart_id

        dl_key = self.get_course_key(CourseType.DOWNLOADEDCOURSE) or s_course_key
        if dl_key:
            if self._status and isinstance(self._status._data, dict):
                self._status._data[dl_key] = smart_id
            if isinstance(self._remote_start_status, dict):
                self._remote_start_status[dl_key] = smart_id

        if self.select_course_enabled and self._download_panel_label in self.course_list:
            self._selected_course = self._download_panel_label
            self._prune_overrides_for_course(course_info)

    def _prune_overrides_for_course(self, course_info: dict | None) -> None:
        """Reset cycle-specific option overrides on course change; keep switch overrides if still selectable."""
        for k in list(self._option_overrides.keys()):
            if k not in _OPTION_SWITCH_KEYS:
                self._option_overrides.pop(k, None)
                continue
            fn = self._course_func_entry(course_info, k)
            selectable = [str(x) for x in (fn.get("selectable") or [])] if fn else []
            if self._option_overrides[k] not in selectable:
                self._option_overrides.pop(k, None)

    async def select_start_course(self, course_name: str) -> None:
        """Select a secific course for remote start."""
        if not self.select_course_enabled:
            raise InvalidDeviceStatus()

        if course_name == _CURRENT_COURSE:
            self._selected_course = None
            self._option_overrides.clear()
            return
        if course_name not in self.course_list:
            raise ValueError(f"Invalid course: {course_name}")
        if self._selected_course != course_name:
            self._selected_course = course_name
            _, _, cinfo = self._resolve_target_course_info()
            self._prune_overrides_for_course(cinfo)

    async def power_off(self):
        """Power off the device."""
        keys = self._get_cmd_keys(CMD_POWER_OFF)
        await self.set(keys[0], keys[1])
        self._remote_start_status = None
        self._update_status(POWER_STATUS_KEY, self._state_power_off)

    async def wake_up(self):
        """Wakeup the device."""
        if not self._stand_by:
            raise InvalidDeviceStatus()

        keys = self._get_cmd_keys(CMD_WAKE_UP)
        await self.set(keys[0], keys[1])
        self._stand_by = False
        self._update_status(POWER_STATUS_KEY, self._state_power_on_init)

    async def remote_start(self, course_name: str | None = None) -> None:
        """Remote start the device."""
        if not self.remote_start_enabled:
            raise InvalidDeviceStatus()

        if course_name and self._initial_bit_start:
            if (
                course_name in self.downloaded_course_list
                and course_name not in self.course_list
            ):
                await self.select_downloaded_course(course_name)
            else:
                await self.select_start_course(course_name)

        keys = self._get_cmd_keys(CMD_REMOTE_START)
        await self.set(keys[0], keys[1], key=keys[2])
        self._remote_start_pressed = True
        self._option_overrides.clear()

    async def pause(self):
        """Pause the device."""
        if not self.pause_enabled:
            raise InvalidDeviceStatus()

        keys = self._get_cmd_keys(CMD_PAUSE)
        await self.set(keys[0], keys[1])
        self._remote_start_pressed = False
        self._update_status(POWER_STATUS_KEY, self._state_pause)

    async def set(
        self, ctrl_key, command, *, key=None, value=None, data=None, ctrl_path=None
    ):
        """Set a device's control for `key` to `value`."""
        await super().set(
            self._getcmdkey(ctrl_key),
            self._getcmdkey(command),
            key=key,
            value=value,
            data=data,
            ctrl_path=ctrl_path,
        )

    def reset_status(self):
        tcl_count = None
        if self._status:
            tcl_count = self._status.tubclean_count
        self._status = WMStatus(self, tcl_count=tcl_count)
        return self._status

    def _set_remote_start_opt(self):
        """Save the status to use for remote start."""
        if self._remote_start_pressed:
            self._remote_start_pressed = False

        if self._power_on_available is None:
            if self.model_info.config_value("powerOnButtonAvailable"):
                self._power_on_available = True
            else:
                self._power_on_available = False

        if self._power_on_available:
            self._stand_by = not self._status.is_on
        else:
            stand_by = self._status.device_features.get(WashDeviceFeatures.STANDBY)
            if stand_by is None:
                standby_enable = self.model_info.config_value("standbyEnable")
                if standby_enable and not self._should_poll and not self._sub_key:
                    self._stand_by = not self._status.is_on
                else:
                    self._stand_by = False
            else:
                self._stand_by = stand_by == StateOptions.ON

        remote_start = self._status.device_features.get(WashDeviceFeatures.REMOTESTART)
        if remote_start == StateOptions.ON:
            if self._remote_start_status is None:
                self._remote_start_status = self._status.as_dict
            self._initial_bit_start = (
                self._status.internal_run_state == self._state_power_on_init
            )
        else:
            self._remote_start_status = None
            self._initial_bit_start = False

    def _set_cycle_finishing(self) -> None:
        """Calculate if the cycle is finishing because remain 1 minute."""
        if not self._status:
            return

        if (remaining_min := self._status.remaintime_min) is None:
            return

        # some devices just return minutes, so we set hour to 0 if is None
        remaining_hours = self._status.remaintime_hour or 0

        if int(remaining_hours) == 0:
            if int(remaining_min) == 1:
                self._is_cycle_finishing = True
            elif int(remaining_min) > 1:
                self._is_cycle_finishing = False

    async def poll(self) -> WMStatus | None:
        """Poll the device's current state."""

        if not self._sub_key or not self._should_poll:
            res = await self._device_poll(self._sub_device or WM_ROOT_DATA)
            if self._subkey_device and self._should_poll:
                self._subkey_device.update_internal_state(res)
        else:
            res = self._internal_state

        if not res:
            self._stand_by = False
            return None

        self._status = WMStatus(self, res)
        self._set_remote_start_opt()
        self._set_cycle_finishing()
        return self._status


class WMStatus(DeviceStatus):
    """
    Higher-level information about a WM current status.

    :param device: The Device instance.
    :param data: JSON data from the API.
    """

    _device: WMDevice

    def __init__(
        self,
        device: WMDevice,
        data: dict | None = None,
        *,
        tcl_count: str | None = None,
        init_run_state=True,
    ):
        """Initialize device status."""
        super().__init__(device, data)
        self._internal_run_state = None
        self._run_state = None
        self._pre_state = None
        self._process_state = None
        self._error = None
        self._tcl_count = tcl_count
        if init_run_state:
            # we call get_run_state to update device states
            self._get_run_state()

    def _getkeys(self, keys: str | list[str]) -> str | list[str]:
        """Add subkey prefix to a key or a list of keys if required."""
        if isinstance(keys, list):
            return [self._device.getkey(key) for key in keys]
        return self._device.getkey(keys)

    def _get_run_state(self):
        """Get current run state."""
        if not self._run_state:
            curr_key = self._get_data_key(self._getkeys(POWER_STATUS_KEY))
            state = self.lookup_enum(curr_key)
            if not state:
                self._internal_run_state = None
                self._run_state = STATE_WM_POWER_OFF
            else:
                self._internal_run_state = self._data[curr_key]
                self._run_state = state
            self._device.save_run_states(self._run_state)
        return self._run_state

    def _get_pre_state(self):
        """Get previous run state."""
        if not self._pre_state:
            keys = self._getkeys(["PreState", "preState"])
            if not (key := self.get_model_info_key(keys)):
                return None
            run_state = self._get_run_state()
            state = self.lookup_enum(key)
            if not state:
                self._pre_state = STATE_WM_POWER_OFF
            elif state == run_state:
                self._pre_state = self._device.pre_state
            else:
                self._pre_state = state
                self._device.save_run_states(state, True)
        return self._pre_state

    def _get_process_state(self):
        """Get current process state."""
        if not self._process_state:
            keys = self._getkeys(["ProcessState", "processState"])
            if not (key := self.get_model_info_key(keys)):
                return None
            state = self.lookup_enum(key)
            if not state:
                self._process_state = StateOptions.NONE
            else:
                self._process_state = state
        return self._process_state

    def _get_error(self):
        """Get current error."""
        if not self._error:
            keys = self._getkeys(["Error", "error"])
            if (error := self.lookup_enum(keys)) is None:
                error = self.lookup_reference(keys, ref_key="title")
            if not error:
                self._error = STATE_WM_ERROR_OFF
            else:
                self._error = error
        return self._error

    def update_status(self, key, value):
        """Update device status."""
        if not super().update_status(self._getkeys(key), value):
            return False
        self._run_state = None
        return True

    @property
    def internal_run_state(self):
        """Return internal representation for run state."""
        self._get_run_state()
        return self._internal_run_state

    @property
    def is_on(self):
        """Return if device is on."""
        run_state = self._get_run_state()
        return STATE_WM_POWER_OFF not in run_state

    @property
    def is_dryer(self):
        """Return if device is a dryer."""
        if self._device.device_info.type in [DeviceType.DRYER, DeviceType.TOWER_DRYER]:
            return True
        return False

    @property
    def is_run_completed(self):
        """Return if run is completed."""
        run_state = self._get_run_state()
        pre_state = self._get_pre_state()
        if pre_state is None:
            pre_state = self._get_process_state() or StateOptions.NONE

        if any(state in run_state for state in STATE_WM_END) or (
            STATE_WM_POWER_OFF in run_state
            and any(state in pre_state for state in STATE_WM_END)
        ):
            return True

        return False

    @property
    def is_error(self):
        """Return if an error is present."""
        if not self.is_on:
            return False
        error = self._get_error()
        if error in STATE_WM_ERROR_NO_ERROR or error == STATE_WM_ERROR_OFF:
            return False
        return True

    @property
    def current_course(self):
        """Return current course."""
        if not (course_key := self._device.get_course_key(CourseType.COURSE)):
            return StateOptions.NONE
        dl_ap_id = (
            self._device.model_info.config_value("downloadCourseAPId")
            if self._device.model_info
            else None
        ) or "DOWNLOAD"
        curr_key = self._get_data_key(course_key)
        if curr_key and self._data.get(curr_key) == dl_ap_id:
            smart = self.current_smartcourse
            if smart and smart != StateOptions.NONE:
                return smart
        course = self.lookup_reference(course_key, ref_key="name")
        text = self._device.get_enum_text(course)
        if text and text != StateOptions.NONE:
            return text
        smart = self.current_smartcourse
        if smart and smart != StateOptions.NONE:
            return smart
        return StateOptions.NONE

    @property
    def current_smartcourse(self):
        """Return current active smartcourse."""
        s_key = self._device.get_course_key(CourseType.SMARTCOURSE)
        dl_key = self._device.get_course_key(CourseType.DOWNLOADEDCOURSE)
        c_key = self._device.get_course_key(CourseType.COURSE)
        dl_ap_id = (
            self._device.model_info.config_value("downloadCourseAPId")
            if self._device.model_info
            else None
        ) or "DOWNLOAD"
        curr_c_key = self._get_data_key(c_key) if c_key else None
        is_dl_slot_selected = bool(
            curr_c_key and self._data.get(curr_c_key) == dl_ap_id
        )
        if s_key and s_key != dl_key:
            smart_course = self.lookup_reference(s_key, ref_key="name")
            text = self._device.get_enum_text(smart_course)
            if text and text != StateOptions.NONE:
                return text
        if is_dl_slot_selected:
            for key in (s_key, dl_key):
                if key:
                    smart_course = self.lookup_reference(key, ref_key="name")
                    text = self._device.get_enum_text(smart_course)
                    if text and text != StateOptions.NONE:
                        return text
        return StateOptions.NONE

    def _get_time_info(self, keys: list[str]):
        """Return time info for specific key."""
        if self.is_info_v2:
            if not self.is_on:
                return 0
            return self.int_or_none(self._data.get(self._getkeys(keys[1])))
        return self.lookup_range(self._getkeys((keys[0])))

    @property
    def initialtime_hour(self):
        """Return hour initial time."""
        return self._get_time_info(["Initial_Time_H", "initialTimeHour"])

    @property
    def initialtime_min(self):
        """Return minute initial time."""
        return self._get_time_info(
            [["Initial_Time_M", "Initial_Time"], "initialTimeMinute"]
        )

    @property
    def remaintime_hour(self):
        """Return hour remaining time."""
        return self._get_time_info(["Remain_Time_H", "remainTimeHour"])

    @property
    def remaintime_min(self):
        """Return minute remaining time."""
        return self._get_time_info(
            [["Remain_Time_M", "Remain_Time"], "remainTimeMinute"]
        )

    @property
    def reservetime_hour(self):
        """Return hour reserved time."""
        return self._get_time_info(["Reserve_Time_H", "reserveTimeHour"])

    @property
    def reservetime_min(self):
        """Return minute reserved time."""
        return self._get_time_info(
            [["Reserve_Time_M", "Reserve_Time"], "reserveTimeMinute"]
        )

    @property
    def run_state(self):
        """Return current run state."""
        run_state = self._get_run_state()
        if STATE_WM_POWER_OFF in run_state:
            run_state = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.RUN_STATE, run_state)

    @property
    def pre_state(self):
        """Return previous run state."""
        pre_state = self._get_pre_state()
        if pre_state is None:
            return None
        if STATE_WM_POWER_OFF in pre_state:
            pre_state = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.PRE_STATE, pre_state)

    @property
    def process_state(self):
        """Return current process state."""
        process = self._get_process_state()
        if process is None:
            return None
        if not self.is_on:
            process = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.PROCESS_STATE, process)

    @property
    def error_msg(self):
        """Return current error message."""
        if not self.is_error:
            error = StateOptions.NONE
        else:
            error = self._get_error()
        return self._update_feature(WashDeviceFeatures.ERROR_MSG, error)

    @property
    def spin_option_state(self):
        """Return spin option state."""
        keys = self._getkeys(["SpinSpeed", "spin"])
        if not (key := self.get_model_info_key(keys)):
            return None
        spin_speed = self.lookup_enum(key)
        if not spin_speed:
            spin_speed = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.SPINSPEED, spin_speed)

    @property
    def water_temp_option_state(self):
        """Return water temperature option state."""
        keys = self._getkeys(["WTemp", "WaterTemp", "temp"])
        if not (key := self.get_model_info_key(keys)):
            return None
        if self.key_exist("temp") and self.is_dryer:
            return None
        water_temp = self.lookup_enum(key)
        if not water_temp:
            water_temp = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.WATERTEMP, water_temp)

    @property
    def rinse_mode_option_state(self):
        """Return rinse mode option state."""
        keys = self._getkeys(["RinseOption", "rinse"])
        if not (key := self.get_model_info_key(keys)):
            return None
        rinse_mode = self.lookup_enum(key)
        if not rinse_mode:
            rinse_mode = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.RINSEMODE, rinse_mode)

    @property
    def dry_level_option_state(self):
        """Return dry level option state."""
        keys = self._getkeys(["DryLevel", "dryLevel"])
        if not (key := self.get_model_info_key(keys)):
            return None
        dry_level = self.lookup_enum(key)
        if not dry_level:
            dry_level = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.DRYLEVEL, dry_level)

    @property
    def temp_control_option_state(self):
        """Return temperature control option state."""
        keys = self._getkeys(["TempControl", "tempControl", "temp"])
        if not (key := self.get_model_info_key(keys)):
            return None
        if self.key_exist("temp") and not self.is_dryer:
            return None
        temp_control = self.lookup_enum(key)
        if not temp_control:
            temp_control = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.TEMPCONTROL, temp_control)

    @property
    def time_dry_option_state(self):
        """Return time dry option state."""
        keys = self._getkeys("TimeDry")
        if not (key := self.get_model_info_key(keys)):
            return None
        time_dry = self.lookup_enum(key)
        if not time_dry:
            time_dry = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.TIMEDRY, time_dry, False)

    @property
    def eco_hybrid_option_state(self):
        """Return eco hybrid option state."""
        keys = self._getkeys(["EcoHybrid", "ecoHybrid"])
        if not (key := self.get_model_info_key(keys)):
            return None
        eco_hybrid = self.lookup_enum(key)
        if not eco_hybrid:
            eco_hybrid = StateOptions.NONE
        return self._update_feature(WashDeviceFeatures.ECOHYBRID, eco_hybrid)

    @property
    def tubclean_count(self):
        """Return tub clean counter."""
        key = self._getkeys("TCLCount")
        if self.is_info_v2:
            if (result := self.int_or_none(self._data.get(key))) is None:
                return None
        else:
            if not self.get_model_info_key(key):
                return None
            result = self._data.get(key)
            if result is None:
                result = self._tcl_count or "N/A"
        return self._update_feature(WashDeviceFeatures.TUBCLEAN_COUNT, result, False)

    @property
    def standby_state(self):
        """Return standby state."""
        status = None
        keys = self._getkeys(["Standby", "standby"])
        if key := self.get_model_info_key(keys):
            status = self.lookup_enum(key)
        if not status and not self.is_info_v2:
            status = self.lookup_bit(keys[0], sub_key=self._device.sub_key)
        if not (status or key):
            return None
        if not status:
            status = StateOptions.OFF
        return self._update_feature(WashDeviceFeatures.STANDBY, status)

    def _update_bit_features(self):
        """Update features related to bit status."""
        index = 1 if self.is_info_v2 else 0
        for feature, keys in BIT_FEATURES.items():
            invert = feature in INVERTED_BITS
            status = self.lookup_bit(
                self._getkeys(keys[index]), sub_key=self._device.sub_key, invert=invert
            )
            self._update_feature(feature, status, False)

    def _update_features(self):
        _ = [
            self.run_state,
            self.pre_state,
            self.process_state,
            self.error_msg,
            self.spin_option_state,
            self.water_temp_option_state,
            self.rinse_mode_option_state,
            self.dry_level_option_state,
            self.temp_control_option_state,
            # self.time_dry_option_state,
            self.eco_hybrid_option_state,
            self.tubclean_count,
            self.standby_state,
        ]
        self._update_bit_features()
