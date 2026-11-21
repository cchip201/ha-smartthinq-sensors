"""Tests for LG ThinQ2 Washer & Dryer pre-start option controls (backlog 1964.4 B)."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.smartthinq_sensors import DOMAIN, LGEDevice
from custom_components.smartthinq_sensors.select import (
    WASH_DEV_SELECT,
    LGESelect,
    _select_exist,
)
from custom_components.smartthinq_sensors.switch import (
    WASH_DEV_SWITCH,
    LGESwitch,
    _switch_exist,
)
from custom_components.smartthinq_sensors.wideq.device_info import DeviceInfo
from custom_components.smartthinq_sensors.wideq.devices.washerDryer import WMDevice
from custom_components.smartthinq_sensors.wideq.model_info import ModelInfoV2


WASHER_OPTS_MODEL = {
    "Info": {
        "productType": "WM",
        "country": "US",
        "modelType": "FL",
        "model": "US_Titan29_",
        "modelName": "FATIU21019",
        "networkType": "WIFI",
        "version": "0.6",
    },
    "Config": {
        "powerOffDownload": True,
        "smartCourseType": "downloadCourse",
        "downloadedCourseType": "downloadCourse",
        "courseType": "course",
        "standbyEnable": False,
        "downloadPanelLabel": "@WM_MP_FATIU21019_TERM_DOWNLOADED_W",
        "defaultCourse": "NORMAL",
        "downloadCourseAPId": "DOWNLOAD",
        "defaultSmartCourse": "SMALL_LOAD",
        "uniProtocol": True,
        "powerOnButtonAvailable": False,
    },
    "MonitoringValue": {
        "state": {
            "dataType": "enum",
            "valueMapping": {
                "POWEROFF": {"index": 0, "label": "@WM_STATE_POWER_OFF_W"},
                "INITIAL": {"index": 1, "label": "@WM_STATE_INITIAL_W"},
                "PAUSE": {"index": 2, "label": "@WM_STATE_PAUSE_W"},
                "RUNNING": {"index": 3, "label": "@WM_STATE_RUNNING_W"},
            },
        },
        "preState": {
            "dataType": "enum",
            "valueMapping": {
                "POWEROFF": {"index": 0, "label": "@WM_STATE_POWER_OFF_W"},
                "INITIAL": {"index": 1, "label": "@WM_STATE_INITIAL_W"},
                "END": {"index": 4, "label": "@WM_STATE_END_W"},
            },
        },
        "remoteStart": {
            "dataType": "enum",
            "valueMapping": {
                "REMOTE_START_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "REMOTE_START_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "childLock": {
            "dataType": "enum",
            "valueMapping": {
                "CHILDLOCK_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "CHILDLOCK_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "freshCare": {
            "dataType": "enum",
            "valueMapping": {
                "FRESHCARE_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "FRESHCARE_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "temp": {
            "dataType": "enum",
            "valueMapping": {
                "NO_TEMP": {"index": 0, "label": "@WM_TERM_NO_SELECT_W"},
                "FL27_TEMP_TAPCOLD": {
                    "index": 1,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_TAP_COLD_W",
                },
                "FL27_TEMP_COLD": {
                    "index": 2,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_COLD_W",
                },
                "FL27_TEMP_ECOWARM": {
                    "index": 3,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_ECO_WARM_W",
                },
                "FL27_TEMP_WARM": {
                    "index": 4,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_WARM_W",
                },
                "FL27_TEMP_WARMRINSE": {
                    "index": 5,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_WARM_W",
                },
                "FL27_TEMP_HOT": {
                    "index": 6,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_HOT_W",
                },
                "FL27_TEMP_EXTRAHOT": {
                    "index": 7,
                    "label": "@WM_MP_FATIU21019_OPTION_TEMP_EXTRA_HOT_W",
                },
            },
        },
        "spin": {
            "dataType": "enum",
            "valueMapping": {
                "NO_SPIN": {"index": 0, "label": "@WM_TERM_NO_SELECT_W"},
                "SPIN_DRAIN_ONLY": {
                    "index": 1,
                    "label": "@WM_MP_FATIU21019_OPTION_SPIN_NO_SPIN_W",
                },
                "SPIN_LOW": {
                    "index": 2,
                    "label": "@WM_MP_FATIU21019_OPTION_SPIN_LOW_W",
                },
                "SPIN_MEDIUM": {
                    "index": 3,
                    "label": "@WM_MP_FATIU21019_OPTION_SPIN_MEDIUM_W",
                },
                "SPIN_HIGH": {
                    "index": 4,
                    "label": "@WM_MP_FATIU21019_OPTION_SPIN_HIGH_W",
                },
                "SPIN_EXTRA_HIGH": {
                    "index": 5,
                    "label": "@WM_MP_FATIU21019_OPTION_SPIN_EXTRA_HIGH_W",
                },
            },
        },
        "soilWash": {
            "dataType": "enum",
            "valueMapping": {
                "NO_SOILWASH": {"index": 0, "label": "@WM_TERM_NO_SELECT_W"},
                "SOILWASH_LIGHT": {
                    "index": 1,
                    "label": "@WM_MP_FATIU21019_OPTION_SOIL_LIGHT_W",
                },
                "SOILWASH_LIGHT_NORMAL": {
                    "index": 2,
                    "label": "@WM_MP_FATIU21019_OPTION_SOIL_LIGHT_NORMAL_W",
                },
                "SOILWASH_NORMAL": {
                    "index": 3,
                    "label": "@WM_MP_FATIU21019_OPTION_SOIL_NORMAL_W",
                },
                "SOILWASH_NORMAL_HEAVY": {
                    "index": 4,
                    "label": "@WM_MP_FATIU21019_OPTION_SOIL_NORMAL_HEAVY_W",
                },
                "SOILWASH_HEAVY": {
                    "index": 5,
                    "label": "@WM_MP_FATIU21019_OPTION_SOIL_HEAVY_W",
                },
            },
        },
        "course": {"ref": "Course"},
        "downloadCourse": {"ref": "SmartCourse"},
    },
    "ControlWifi": {
        "vtCtrl": {
            "command": "Set",
            "data": {
                "ctrlTarget": ["UNDEFINE"],
                "reqDevType": "temp",
                "productType": "NORMAL",
                "vtData": {
                    "UNDEFINE": [{"cmd": "temp", "value": "temp", "type": "temp"}]
                },
            },
        },
    },
    "Course": {
        "NORMAL": {
            "_comment": "Normal",
            "courseType": "Course",
            "name": "@WM_MP_FATIU21019_COURSE_NORMAL_W",
            "courseValue": "NORMAL",
            "function": [
                {
                    "value": "freshCare",
                    "default": "FRESHCARE_OFF",
                    "selectable": ["FRESHCARE_OFF", "FRESHCARE_ON"],
                },
                {
                    "value": "temp",
                    "default": "FL27_TEMP_WARM",
                    "selectable": [
                        "FL27_TEMP_TAPCOLD",
                        "FL27_TEMP_COLD",
                        "FL27_TEMP_WARM",
                        "FL27_TEMP_HOT",
                        "FL27_TEMP_EXTRAHOT",
                    ],
                },
                {
                    "value": "spin",
                    "default": "SPIN_HIGH",
                    "selectable": [
                        "SPIN_DRAIN_ONLY",
                        "SPIN_LOW",
                        "SPIN_MEDIUM",
                        "SPIN_HIGH",
                        "SPIN_EXTRA_HIGH",
                    ],
                },
                {
                    "value": "soilWash",
                    "default": "SOILWASH_NORMAL",
                    "selectable": [
                        "SOILWASH_LIGHT",
                        "SOILWASH_LIGHT_NORMAL",
                        "SOILWASH_NORMAL",
                        "SOILWASH_NORMAL_HEAVY",
                        "SOILWASH_HEAVY",
                    ],
                },
            ],
        },
        "DELICATES": {
            "_comment": "Delicates",
            "courseType": "Course",
            "name": "@WM_MP_FATIU21019_COURSE_DELICATES_W",
            "courseValue": "DELICATES",
            "function": [
                {
                    "value": "freshCare",
                    "default": "FRESHCARE_OFF",
                    "selectable": ["FRESHCARE_OFF", "FRESHCARE_ON"],
                },
                {
                    "value": "temp",
                    "default": "FL27_TEMP_COLD",
                    "selectable": [
                        "FL27_TEMP_TAPCOLD",
                        "FL27_TEMP_COLD",
                        "FL27_TEMP_WARM",
                    ],
                },
                {
                    "value": "spin",
                    "default": "SPIN_MEDIUM",
                    "selectable": ["SPIN_DRAIN_ONLY", "SPIN_LOW", "SPIN_MEDIUM"],
                },
                {
                    "value": "soilWash",
                    "default": "SOILWASH_NORMAL",
                    "selectable": [
                        "SOILWASH_LIGHT",
                        "SOILWASH_LIGHT_NORMAL",
                        "SOILWASH_NORMAL",
                        "SOILWASH_NORMAL_HEAVY",
                        "SOILWASH_HEAVY",
                    ],
                },
            ],
        },
        "TUB_CLEAN": {
            "_comment": "Tub Clean",
            "courseType": "Course",
            "name": "@WM_MP_FATIU21019_COURSE_TUB_CLEAN_W",
            "courseValue": "TUB_CLEAN",
            "function": [
                {"value": "temp", "default": "NO_TEMP"},
                {"value": "spin", "default": "SPIN_MEDIUM"},
                {"value": "soilWash", "default": "NO_SOILWASH"},
            ],
        },
        "DOWNLOAD": {
            "_comment": "다운로드코스",
            "courseType": "Course",
            "courseValue": "DOWNLOAD",
        },
    },
    "SmartCourse": {
        "COLOR_CARE": {
            "_comment": "Color Care",
            "Course": "NORMAL",
            "courseType": "SmartCourse",
            "downloadEnable": True,
            "function": [
                {
                    "value": "freshCare",
                    "default": "FRESHCARE_OFF",
                    "selectable": ["FRESHCARE_OFF", "FRESHCARE_ON"],
                },
                {"value": "temp", "default": "FL27_TEMP_COLD"},
                {"value": "spin", "default": "SPIN_MEDIUM"},
                {"value": "soilWash", "default": "SOILWASH_NORMAL"},
            ],
        },
    },
}


DRYER_OPTS_MODEL = {
    "Info": {
        "productType": "WM",
        "country": "WW",
        "modelType": "Dryer",
        "model": "Titaan29 Refresh",
        "modelName": "UDV_TI4441_US",
        "networkType": "WIFI",
        "version": "0.2",
    },
    "Config": {
        "courseType": "courseDryer27inchBase",
        "smartCourseType": "smartCourseDryer27inchBase",
        "downloadedCourseType": "downloadedCourseDryer27inchBase",
        "downloadPanelLabel": "@WM_STATE_DOWNLOAD_COMPLETE_W",
        "defaultCourse": "NORMAL",
        "defaultSmartCourse": "ULTRADELICATES",
        "powerOffDownload": True,
    },
    "MonitoringValue": {
        "state": {
            "dataType": "enum",
            "valueMapping": {
                "POWEROFF": {"index": 0, "label": "@WM_STATE_POWER_OFF_W"},
                "INITIAL": {"index": 1, "label": "@WM_STATE_INITIAL_W"},
                "PAUSE": {"index": 2, "label": "@WM_STATE_PAUSE_W"},
                "DRYING": {"index": 3, "label": "@WM_STATE_DRYING_W"},
            },
        },
        "preState": {
            "dataType": "enum",
            "valueMapping": {
                "POWEROFF": {"index": 0, "label": "@WM_STATE_POWER_OFF_W"},
                "INITIAL": {"index": 1, "label": "@WM_STATE_INITIAL_W"},
            },
        },
        "remoteStart": {
            "dataType": "enum",
            "valueMapping": {
                "REMOTE_START_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "REMOTE_START_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "childLock": {
            "dataType": "enum",
            "valueMapping": {
                "CHILDLOCK_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "CHILDLOCK_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "initialBit": {
            "dataType": "enum",
            "valueMapping": {
                "INITIAL_BIT_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "INITIAL_BIT_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "wrinkleCare": {
            "dataType": "enum",
            "valueMapping": {
                "WRINKLECARE_OFF": {"index": 0, "label": "@CP_OFF_EN_W"},
                "WRINKLECARE_ON": {"index": 1, "label": "@CP_ON_EN_W"},
            },
        },
        "dryLevel": {
            "dataType": "enum",
            "valueMapping": {
                "NO_DRYLEVEL": {"index": 0, "label": "@WM_TERM_NO_SELECT_W"},
                "DRYLEVEL_DAMPDRY": {"index": 1, "label": "@WM_DRY27_DRY_LEVEL_DAMP_W"},
                "DRYLEVEL_LESSDRY": {"index": 2, "label": "@WM_DRY27_DRY_LEVEL_LESS_W"},
                "DRYLEVEL_NORMAL": {"index": 3, "label": "@WM_DRY27_DRY_LEVEL_NORMAL_W"},
                "DRYLEVEL_MOREDRY": {"index": 4, "label": "@WM_DRY27_DRY_LEVEL_MORE_W"},
                "DRYLEVEL_VERYDRY": {"index": 5, "label": "@WM_DRY27_DRY_LEVEL_VERY_W"},
            },
        },
        "temp": {
            "dataType": "enum",
            "valueMapping": {
                "NO_TEMP": {"index": 0, "label": "@WM_TERM_NO_SELECT_W"},
                "TEMP_ULTRALOW": {"index": 1, "label": "@WM_DRY27_TEMP_ULTRA_LOW_W"},
                "TEMP_LOW": {"index": 2, "label": "@WM_DRY27_TEMP_LOW_W"},
                "TEMP_MEDIUM": {"index": 3, "label": "@WM_DRY27_TEMP_MEDIUM_W"},
                "TEMP_MEDIUMHIGH": {"index": 4, "label": "@WM_DRY27_TEMP_MID_HIGH_W"},
                "TEMP_HIGH": {"index": 5, "label": "@WM_DRY27_TEMP_HIGH_W"},
            },
        },
        "timeDry": {
            "dataType": "enum",
            "valueMapping": {
                "TIMEDRY_OFF": {"index": 0, "label": "@WM_TERM_NO_SELECT_W"},
                "TIMEDRY_20": {"index": 1, "label": "20"},
                "TIMEDRY_30": {"index": 2, "label": "30"},
                "TIMEDRY_40": {"index": 3, "label": "40"},
                "TIMEDRY_50": {"index": 4, "label": "50"},
                "TIMEDRY_60": {"index": 5, "label": "60"},
            },
        },
        "courseDryer27inchBase": {"ref": "Course"},
        "smartCourseDryer27inchBase": {"ref": "SmartCourse"},
        "downloadedCourseDryer27inchBase": {"ref": "SmartCourse"},
    },
    "ControlWifi": {
        "WMStart": {
            "command": "Set",
            "data": {
                "washerDryer": {
                    "Course": "temp",
                    "temp": "NO_TEMP",
                    "timeDry": "TIMEDRY_OFF",
                    "wrinkleCare": "WRINKLECARE_OFF",
                    "childLock": "CHILDLOCK_OFF",
                    "remoteStart": "REMOTE_START_OFF",
                    "initialBit": "INITIAL_BIT_OFF",
                    "smartCourseDryer27inchBase": "temp",
                    "dryLevel": "NO_DRYLEVEL",
                    "moreLessTime": 0,
                }
            },
        },
        "WMDownload": {
            "command": "Set",
            "data": {
                "washerDryer": {
                    "courseDownloadType": "COURSEDATA",
                    "courseDownloadDataLength": 21,
                    "Course": "temp",
                    "temp": "NO_TEMP",
                    "timeDry": "TIMEDRY_OFF",
                    "wrinkleCare": "WRINKLECARE_OFF",
                    "childLock": "CHILDLOCK_OFF",
                    "remoteStart": "REMOTE_START_OFF",
                    "initialBit": "INITIAL_BIT_OFF",
                    "smartCourseDryer27inchBase": "temp",
                    "dryLevel": "NO_DRYLEVEL",
                    "moreLessTime": 0,
                }
            },
        },
    },
    "Course": {
        "NORMAL": {
            "_comment": "Normal",
            "courseType": "Course",
            "courseValue": "NORMAL",
            "function": [
                {"value": "temp", "default": "TEMP_MEDIUM"},
                {"value": "dryLevel", "default": "DRYLEVEL_NORMAL"},
                {
                    "value": "wrinkleCare",
                    "default": "WRINKLECARE_OFF",
                    "selectable": ["WRINKLECARE_OFF", "WRINKLECARE_ON"],
                },
                {"value": "moreLessTime", "default": 0},
            ],
        },
        "HEAVYDUTY": {
            "_comment": "Heavy Duty",
            "courseType": "Course",
            "courseValue": "HEAVYDUTY",
            "function": [
                {"value": "temp", "default": "TEMP_HIGH"},
                {
                    "value": "dryLevel",
                    "default": "DRYLEVEL_NORMAL",
                    "selectable": [
                        "DRYLEVEL_DAMPDRY",
                        "DRYLEVEL_LESSDRY",
                        "DRYLEVEL_NORMAL",
                        "DRYLEVEL_MOREDRY",
                        "DRYLEVEL_VERYDRY",
                    ],
                },
                {
                    "value": "wrinkleCare",
                    "default": "WRINKLECARE_OFF",
                    "selectable": ["WRINKLECARE_OFF", "WRINKLECARE_ON"],
                },
                {"value": "moreLessTime", "default": 0},
            ],
        },
        "TIMEDRY": {
            "_comment": "Time Dry",
            "courseType": "Course",
            "courseValue": "TIMEDRY",
            "function": [
                {
                    "value": "temp",
                    "default": "TEMP_HIGH",
                    "selectable": [
                        "TEMP_ULTRALOW",
                        "TEMP_LOW",
                        "TEMP_MEDIUM",
                        "TEMP_MEDIUMHIGH",
                        "TEMP_HIGH",
                    ],
                },
                {"value": "dryLevel", "default": "NO_DRYLEVEL"},
                {
                    "value": "timeDry",
                    "default": "TIMEDRY_40",
                    "selectable": [
                        "TIMEDRY_20",
                        "TIMEDRY_30",
                        "TIMEDRY_40",
                        "TIMEDRY_50",
                        "TIMEDRY_60",
                    ],
                },
                {
                    "value": "wrinkleCare",
                    "default": "WRINKLECARE_OFF",
                    "selectable": ["WRINKLECARE_OFF", "WRINKLECARE_ON"],
                },
                {"value": "moreLessTime", "default": 40},
            ],
        },
    },
    "SmartCourse": {
        "ULTRADELICATES": {
            "_comment": "Ultra Delicate",
            "Course": "DELICATE",
            "courseType": "SmartCourse",
            "downloadEnable": True,
            "function": [
                {"value": "temp", "default": "TEMP_ULTRALOW"},
                {"value": "dryLevel", "default": "DRYLEVEL_NORMAL"},
                {"value": "timeDry", "default": "TIMEDRY_OFF"},
                {"value": "wrinkleCare", "default": "WRINKLECARE_OFF"},
            ],
        },
    },
}


from .test_downloaded_courses import _make_wm_device as _make_device


def _wrap_lge_api(hass, dev: WMDevice) -> LGEDevice:
    hass.data.setdefault(DOMAIN, {})
    lge_api = LGEDevice(dev, hass)
    lge_api._state = dev.status
    lge_api._coordinator = SimpleNamespace(
        async_set_updated_data=lambda _d: None,
        async_request_refresh=AsyncMock(),
        async_add_listener=lambda *_a, **_k: (lambda: None),
    )
    return lge_api


async def test_option_entity_isolation_and_option_lists(hass):
    """Washer gets only its 4 option controls; Dryer gets only its 4 option controls."""
    washer, _ = await _make_device(
        WASHER_OPTS_MODEL,
        201,
        {
            "state": "POWEROFF",
            "preState": "END",
            "remoteStart": "REMOTE_START_OFF",
            "childLock": "CHILDLOCK_OFF",
            "course": "NOT_SELECTED",
            "downloadCourse": "COLOR_CARE",
            "freshCare": "FRESHCARE_OFF",
            "temp": "NO_TEMP",
            "spin": "NO_SPIN",
            "soilWash": "NO_SOILWASH",
        },
    )
    dryer, _ = await _make_device(
        DRYER_OPTS_MODEL,
        202,
        {
            "state": "POWEROFF",
            "preState": "POWEROFF",
            "remoteStart": "REMOTE_START_OFF",
            "childLock": "CHILDLOCK_OFF",
            "initialBit": "INITIAL_BIT_OFF",
            "courseDryer27inchBase": "NOT_SELECTED",
            "smartCourseDryer27inchBase": "NOT_SELECTED",
            "downloadedCourseDryer27inchBase": "ULTRADELICATES",
            "wrinkleCare": "WRINKLECARE_OFF",
            "dryLevel": "NO_DRYLEVEL",
            "temp": "NO_TEMP",
            "timeDry": "TIMEDRY_OFF",
        },
    )

    w_api = _wrap_lge_api(hass, washer)
    d_api = _wrap_lge_api(hass, dryer)

    w_switches = [d.key for d in WASH_DEV_SWITCH if _switch_exist(w_api, d)]
    d_switches = [d.key for d in WASH_DEV_SWITCH if _switch_exist(d_api, d)]
    assert w_switches == ["power", "fresh_care"]
    assert d_switches == ["power", "wrinkle_care"]

    w_selects = [d.key for d in WASH_DEV_SELECT if _select_exist(w_api, d)]
    d_selects = [d.key for d in WASH_DEV_SELECT if _select_exist(d_api, d)]
    assert w_selects == [
        "course_selection",
        "downloaded_course",
        "water_temp",
        "spin_speed",
        "soil_level",
    ]
    assert d_selects == [
        "course_selection",
        "downloaded_course",
        "dry_level",
        "temp_control",
        "time_dry",
    ]

    assert washer.get_option_list("temp") == [
        "Not Selected",
        "Tap Cold",
        "Cold",
        "Warm",
        "Hot",
        "Extra Hot",
    ]
    assert washer.get_option_list("spin") == [
        "Not Selected",
        "No Spin",
        "Low",
        "Medium",
        "High",
        "Extra High",
    ]
    assert washer.get_option_list("soilWash") == [
        "Not Selected",
        "Light",
        "Light/Normal",
        "Normal",
        "Normal/Heavy",
        "Heavy",
    ]
    assert dryer.get_option_list("dryLevel") == [
        "Not Selected",
        "Damp",
        "Less",
        "Normal",
        "More",
        "Very",
    ]
    assert dryer.get_option_list("temp") == [
        "Not Selected",
        "Low",
        "Med. Low",
        "Medium",
        "Med. High",
        "High",
    ]
    assert dryer.get_option_list("timeDry") == [
        "Not Selected",
        "20 min",
        "30 min",
        "40 min",
        "50 min",
        "60 min",
    ]


async def test_washer_uniprotocol_option_staging_and_cycle_constraints(hass):
    """Washer stages Fresh Care + temp/spin/soil into vtCtrl WMStart and validates cycle limits."""
    washer, client = await _make_device(
        WASHER_OPTS_MODEL,
        201,
        {
            "state": "INITIAL",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "course": "NORMAL",
            "downloadCourse": "COLOR_CARE",
            "freshCare": "FRESHCARE_OFF",
            "temp": "FL27_TEMP_WARM",
            "spin": "SPIN_HIGH",
            "soilWash": "SOILWASH_NORMAL",
        },
    )
    w_api = _wrap_lge_api(hass, washer)

    fc_sw = LGESwitch(w_api, next(d for d in WASH_DEV_SWITCH if d.key == "fresh_care"))
    temp_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "water_temp"))
    spin_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "spin_speed"))
    soil_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "soil_level"))

    assert fc_sw.available is True
    assert fc_sw.is_on is False
    assert temp_sel.current_option == "Warm"
    assert spin_sel.current_option == "High"
    assert soil_sel.current_option == "Normal"

    # Pick Delicates: defaults update to Cold / Medium, Extra Hot is rejected
    await washer.select_start_course("Delicates")
    assert temp_sel.current_option == "Cold"
    assert spin_sel.current_option == "Medium"
    with pytest.raises(HomeAssistantError, match="Delicates allows Water temp"):
        await temp_sel.async_select_option("Extra Hot")

    # Stage allowed overrides on Normal and send WMStart
    await washer.select_start_course("Normal")
    await fc_sw.async_turn_on()
    await temp_sel.async_select_option("Hot")
    await spin_sel.async_select_option("Low")
    await soil_sel.async_select_option("Heavy")
    assert fc_sw.is_on is True
    assert temp_sel.current_option == "Hot"

    await washer.remote_start()
    assert len(client.sent) == 1
    vt_items = client.sent[0]["dataSetList"]["vtData"]["UNDEFINE"]
    vt_map = {item["cmd"]: item["value"] for item in vt_items}
    assert vt_map == {
        "course": "NORMAL",
        "freshCare": "FRESHCARE_ON",
        "temp": "FL27_TEMP_HOT",
        "spin": "SPIN_LOW",
        "soilWash": "SOILWASH_HEAVY",
        "wmControl": "START",
    }
    assert vt_items[-1] == {"cmd": "wmControl", "type": "ABSOLUTE", "value": "START"}
    assert washer.is_starting is True
    assert temp_sel.current_option == "Hot"

    # Once running poll arrives, Starting… and staged overrides clear; re-arm at INITIAL for next load
    client._snapshot["washerDryer"]["state"] = "WASHING"
    await washer.poll()
    assert washer.is_starting is False
    assert washer._option_overrides == {}
    client._snapshot["washerDryer"]["state"] = "INITIAL"
    await washer.poll()
    await fc_sw.async_turn_on()
    await washer.select_downloaded_course("Color Care")
    dl_items = client.sent[-1]["dataSetList"]["vtData"]["UNDEFINE"]
    dl_map = {item["cmd"]: item["value"] for item in dl_items}
    assert dl_map["downloadCourseData"] == "COLOR_CARE"
    assert dl_map["freshCare"] == "FRESHCARE_ON"

    # Switching to Tub Clean prunes unsupported Fresh Care and rejects turning it on
    await washer.select_start_course("Tub Clean")
    assert fc_sw.is_on is False
    with pytest.raises(HomeAssistantError, match="Tub Clean does not support"):
        await fc_sw.async_turn_on()


async def test_dryer_wmstart_option_staging_and_time_dry_autoselect(hass):
    """Dryer stages wrinkleCare/dryLevel/temp/timeDry into WMStart and auto-selects Time Dry."""
    dryer, client = await _make_device(
        DRYER_OPTS_MODEL,
        202,
        {
            "state": "INITIAL",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "initialBit": "INITIAL_BIT_ON",
            "courseDryer27inchBase": "NORMAL",
            "smartCourseDryer27inchBase": "NOT_SELECTED",
            "downloadedCourseDryer27inchBase": "ULTRADELICATES",
            "wrinkleCare": "WRINKLECARE_OFF",
            "dryLevel": "DRYLEVEL_NORMAL",
            "temp": "TEMP_MEDIUM",
            "timeDry": "TIMEDRY_OFF",
        },
    )
    d_api = _wrap_lge_api(hass, dryer)

    wc_sw = LGESwitch(d_api, next(d for d in WASH_DEV_SWITCH if d.key == "wrinkle_care"))
    dl_sel = LGESelect(d_api, next(d for d in WASH_DEV_SELECT if d.key == "dry_level"))
    tc_sel = LGESelect(d_api, next(d for d in WASH_DEV_SELECT if d.key == "temp_control"))
    td_sel = LGESelect(d_api, next(d for d in WASH_DEV_SELECT if d.key == "time_dry"))

    # Normal locks dryLevel and temp, naming the adjustable courses
    with pytest.raises(HomeAssistantError, match="Heavy Duty"):
        await dl_sel.async_select_option("More")
    with pytest.raises(HomeAssistantError, match="Time Dry"):
        await tc_sel.async_select_option("Low")

    # Heavy Duty allows dryLevel + wrinkleCare
    await dryer.select_start_course("Heavy Duty")
    await wc_sw.async_turn_on()
    await dl_sel.async_select_option("More")
    assert wc_sw.is_on is True
    assert dl_sel.current_option == "More"

    await dryer.remote_start()
    payload = client.sent[-1]["dataSetList"]["washerDryer"]
    assert payload["courseDryer27inchBase"] == "HEAVYDUTY"
    assert payload["wrinkleCare"] == "WRINKLECARE_ON"
    assert payload["dryLevel"] == "DRYLEVEL_MOREDRY"
    assert payload["initialBit"] == "INITIAL_BIT_ON"

    # First INITIAL poll holds Starting… + staged picks; second INITIAL poll re-arms Start while keeping picks
    await dryer.poll()
    assert dryer.is_starting is True
    assert dl_sel.current_option == "More"
    assert wc_sw.is_on is True
    await dryer.poll()
    assert dryer.is_starting is False
    await dryer.select_start_course("Current course")
    await td_sel.async_select_option("50 min")
    assert dryer.selected_course == "Time Dry"
    assert td_sel.current_option == "50 min"
    await tc_sel.async_select_option("Low")
    assert tc_sel.current_option == "Low"

    await dryer.remote_start()
    payload_td = client.sent[-1]["dataSetList"]["washerDryer"]
    assert payload_td["courseDryer27inchBase"] == "TIMEDRY"
    assert payload_td["timeDry"] == "TIMEDRY_50"
    assert payload_td["moreLessTime"] == 50
    assert payload_td["temp"] == "TEMP_ULTRALOW"

    # While running (DRYING), controls stay available for live display and reject edits cleanly
    client._snapshot["washerDryer"].update(
        {
            "state": "DRYING",
            "initialBit": "INITIAL_BIT_OFF",
            "wrinkleCare": "WRINKLECARE_ON",
            "temp": "TEMP_HIGH",
        }
    )
    await dryer.poll()
    assert wc_sw.available is True
    assert wc_sw.is_on is True
    assert tc_sel.available is True
    assert tc_sel.current_option == "High"
    with pytest.raises(HomeAssistantError, match="Remote Start"):
        await wc_sw.async_turn_off()
    with pytest.raises(HomeAssistantError, match="Remote Start"):
        await tc_sel.async_select_option("Low")


async def test_smooth_start_holds_picks_and_shows_starting(hass):
    """After Start, fork holds staged course/options and shows Starting… until running poll (1964.6)."""
    from custom_components.smartthinq_sensors.button import BUTTON_ENTITIES, LGEButton
    from custom_components.smartthinq_sensors.wideq.const import WashDeviceFeatures

    dryer, client = await _make_device(
        DRYER_OPTS_MODEL,
        202,
        {
            "state": "INITIAL",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "initialBit": "INITIAL_BIT_ON",
            "courseDryer27inchBase": "NORMAL",
            "smartCourseDryer27inchBase": "NOT_SELECTED",
            "downloadedCourseDryer27inchBase": "ULTRADELICATES",
            "wrinkleCare": "WRINKLECARE_OFF",
            "dryLevel": "DRYLEVEL_NORMAL",
            "temp": "TEMP_MEDIUM",
            "timeDry": "TIMEDRY_OFF",
        },
    )
    d_api = _wrap_lge_api(hass, dryer)

    cs_sel = LGESelect(d_api, next(d for d in WASH_DEV_SELECT if d.key == "course_selection"))
    wc_sw = LGESwitch(d_api, next(d for d in WASH_DEV_SWITCH if d.key == "wrinkle_care"))
    dl_sel = LGESelect(d_api, next(d for d in WASH_DEV_SELECT if d.key == "dry_level"))
    tc_sel = LGESelect(d_api, next(d for d in WASH_DEV_SELECT if d.key == "temp_control"))
    start_btn = LGEButton(
        d_api,
        next(d for d in BUTTON_ENTITIES[d_api.type] if d.key == "remote_start"),
    )

    await cs_sel.async_select_option("Heavy Duty")
    await wc_sw.async_turn_on()
    await dl_sel.async_select_option("More")

    # Press Start button: button.py calls async_set_updated() immediately before the 5s poll
    await start_btn.async_press()
    d_api.cancel_post_control_refresh()

    assert dryer.is_starting is True
    assert start_btn.available is False
    assert dryer.download_course_enabled is False
    assert cs_sel.current_option == "Heavy Duty"
    assert dl_sel.current_option == "More"
    assert wc_sw.is_on is True
    assert tc_sel.current_option == "High"
    assert d_api.state.current_course == "Heavy Duty"
    assert d_api.state.device_features[WashDeviceFeatures.RUN_STATE] == "Starting…"
    assert d_api.state.device_features[WashDeviceFeatures.DRYLEVEL] == "More"
    assert d_api.state.device_features[WashDeviceFeatures.TEMPCONTROL] == "High"

    # Running poll arrives at 5s: Starting… clears and live running state takes over seamlessly
    client._snapshot["washerDryer"].update(
        {
            "state": "DRYING",
            "initialBit": "INITIAL_BIT_OFF",
            "courseDryer27inchBase": "HEAVYDUTY",
            "wrinkleCare": "WRINKLECARE_ON",
            "dryLevel": "DRYLEVEL_MOREDRY",
            "temp": "TEMP_HIGH",
        }
    )
    d_api._state = await dryer.poll()
    assert dryer.is_starting is False
    assert dryer._selected_course is None
    assert dryer._option_overrides == {}
    assert cs_sel.current_option == "Heavy Duty"
    assert dl_sel.current_option == "More"
    assert wc_sw.is_on is True
    assert d_api.state.device_features[WashDeviceFeatures.RUN_STATE] != "Starting…"


async def test_select_course_enabled_does_not_drop_staged_picks_on_poll_gap(hass):
    """Reading select_course_enabled or option values across a poll gap must not clear staged picks (1964.6)."""
    washer, client = await _make_device(
        WASHER_OPTS_MODEL,
        201,
        {
            "state": "INITIAL",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "course": "NORMAL",
            "smartCourse": "NOT_SELECTED",
            "downloadCourse": "SMALL_LOAD",
            "freshCare": "FRESHCARE_OFF",
            "temp": "FL27_TEMP_WARM",
            "spin": "SPIN_HIGH",
            "soilWash": "SOILWASH_NORMAL",
        },
    )
    w_api = _wrap_lge_api(hass, washer)
    fc_sw = LGESwitch(w_api, next(d for d in WASH_DEV_SWITCH if d.key == "fresh_care"))
    temp_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "water_temp"))
    dl_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "downloaded_course"))

    await dl_sel.async_select_option("Color Care")
    w_api.cancel_post_control_refresh()
    await fc_sw.async_turn_on()
    assert washer.selected_course == "Downloaded"

    # Simulate a transient poll gap (poll returns None) and a transient standby/disabled read
    saved_snapshot = dict(client._snapshot)
    client._snapshot = {}
    assert await washer.poll() is None
    assert fc_sw.is_on is True
    assert washer.selected_course == "Downloaded"

    # Even if select_course_enabled transiently evaluates False (e.g. stand_by blip), reading it keeps picks
    washer._stand_by = True
    assert washer.select_course_enabled is False
    assert fc_sw.is_on is True
    assert temp_sel.current_option is not None
    assert washer._selected_course == "Downloaded"
    assert washer._option_overrides == {"freshCare": "FRESHCARE_ON"}
    washer._stand_by = False

    # Restore live snapshot with Remote Start still ON: picks remain ready for Start
    client._snapshot = saved_snapshot
    await washer.poll()
    assert washer.select_course_enabled is True
    assert washer.selected_course == "Downloaded"
    assert fc_sw.is_on is True

    # Turning Remote Start OFF at the physical panel on a real poll clears staged picks
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_OFF"
    await washer.poll()
    assert washer.select_course_enabled is False
    assert washer._selected_course is None
    assert washer._option_overrides == {}


async def test_starting_timeout_and_followup_poll_reschedule(hass):
    """Starting hold expires after timeout and schedules one 3s follow-up refresh when first poll is still Standby."""
    from unittest.mock import patch
    from custom_components.smartthinq_sensors.wideq.const import WashDeviceFeatures

    washer, client = await _make_device(
        WASHER_OPTS_MODEL,
        201,
        {
            "state": "INITIAL",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "course": "NORMAL",
            "smartCourse": "NOT_SELECTED",
            "downloadCourse": "SMALL_LOAD",
            "freshCare": "FRESHCARE_OFF",
            "temp": "FL27_TEMP_WARM",
            "spin": "SPIN_HIGH",
            "soilWash": "SOILWASH_NORMAL",
        },
    )
    w_api = _wrap_lge_api(hass, washer)
    await washer.set_course_option("temp", "Hot", "Water temp")
    await washer.remote_start()
    assert washer.is_starting is True
    assert w_api.state.device_features[WashDeviceFeatures.RUN_STATE] == "Starting…"
    assert w_api.state.device_features[WashDeviceFeatures.WATERTEMP] == "Hot"

    scheduled_delays: list[float] = []
    callbacks = []

    def _fake_call_later(_hass, delay, cb):
        scheduled_delays.append(delay)
        callbacks.append(cb)
        return lambda: None

    async def _do_refresh():
        w_api._state = await washer.poll()

    w_api._coordinator.async_request_refresh = AsyncMock(side_effect=_do_refresh)

    with patch("custom_components.smartthinq_sensors.async_call_later", side_effect=_fake_call_later):
        w_api.async_schedule_post_control_refresh(delay=5.0)
        assert scheduled_delays == [5.0]
        # First poll at +5s still reads INITIAL -> keeps Starting… and schedules 3.0s follow-up
        await callbacks[0](None)
        assert washer.is_starting is True
        assert scheduled_delays == [5.0, 3.0]
        # Second poll at +8s still reads INITIAL -> clears Starting… and does NOT schedule a 3rd loop
        await callbacks[1](None)
        assert washer.is_starting is False
        assert scheduled_delays == [5.0, 3.0]

    # Timeout expiry without poll also clears Starting… and refreshes cached features
    await washer.remote_start()
    assert washer.is_starting is True
    washer._starting_until = 0.0
    assert washer.is_starting is False
    assert w_api.state.device_features[WashDeviceFeatures.RUN_STATE] != "Starting…"



async def test_reread_remote_start_before_refusing_cycle_or_option_change(hass):
    """Cycle, downloaded-course, option, and Start controls re-poll once before refusing on stale Remote Start cache (2156)."""
    from custom_components.smartthinq_sensors.button import BUTTON_ENTITIES, LGEButton
    from custom_components.smartthinq_sensors.wideq.const import StateOptions, WashDeviceFeatures

    washer, client = await _make_device(
        WASHER_OPTS_MODEL,
        201,
        {
            "state": "INITIAL",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_OFF",
            "childLock": "CHILDLOCK_OFF",
            "course": "NORMAL",
            "smartCourse": "NOT_SELECTED",
            "downloadCourse": "SMALL_LOAD",
            "freshCare": "FRESHCARE_OFF",
            "temp": "FL27_TEMP_WARM",
            "spin": "SPIN_HIGH",
            "soilWash": "SOILWASH_NORMAL",
        },
    )
    w_api = _wrap_lge_api(hass, washer)
    cs_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "course_selection"))
    dl_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "downloaded_course"))
    temp_sel = LGESelect(w_api, next(d for d in WASH_DEV_SELECT if d.key == "water_temp"))
    fc_sw = LGESwitch(w_api, next(d for d in WASH_DEV_SWITCH if d.key == "fresh_care"))
    start_btn = LGEButton(
        w_api,
        next(d for d in BUTTON_ENTITIES[w_api.type] if d.key == "remote_start"),
    )

    assert washer.select_course_enabled is False
    assert washer.remote_start_enabled is False

    # While Remote Start is genuinely OFF on the machine, re-poll still refuses with the clear message
    with pytest.raises(HomeAssistantError, match="Remote Start is on at the machine"):
        await cs_sel.async_select_option("Delicates")

    # User presses Remote Start on the washer panel between 300s polls: picking a cycle right away re-polls and succeeds
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_ON"
    await cs_sel.async_select_option("Delicates")
    assert washer.select_course_enabled is True
    assert washer.selected_course == "Delicates"
    assert w_api.state.device_features[WashDeviceFeatures.REMOTESTART] == StateOptions.ON
    assert start_btn.available is True

    # Reset cached state to stale REMOTE_START_OFF and test the 2150/2156 two-step: download cycle then select Downloaded
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_OFF"
    await washer.poll()
    assert washer.select_course_enabled is False
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_ON"
    await dl_sel.async_select_option("Color Care")
    w_api.cancel_post_control_refresh()
    assert washer.select_course_enabled is True
    assert washer.selected_course == "Downloaded"
    await cs_sel.async_select_option("Downloaded")
    assert washer.selected_course == "Downloaded"

    # Reset cached state to stale REMOTE_START_OFF and test option select, option switch, and Start button re-poll
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_OFF"
    await washer.poll()
    assert washer.select_course_enabled is False
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_ON"
    await temp_sel.async_select_option("Hot")
    assert temp_sel.current_option == "Hot"

    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_OFF"
    await washer.poll()
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_ON"
    await fc_sw.async_turn_on()
    assert fc_sw.is_on is True

    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_OFF"
    await washer.poll()
    client._snapshot["washerDryer"]["remoteStart"] = "REMOTE_START_ON"
    await start_btn.async_press()
    w_api.cancel_post_control_refresh()
    assert washer.is_starting is True
