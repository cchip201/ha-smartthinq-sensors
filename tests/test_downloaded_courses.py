"""Tests for LG ThinQ2 Washer & Dryer downloaded SmartCourse selection and start (backlog 1964)."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import pytest

from custom_components.smartthinq_sensors.device_helpers import LGEWashDevice
from custom_components.smartthinq_sensors.select import WASH_DEV_SELECT, _select_exist
from custom_components.smartthinq_sensors.wideq.core_exceptions import InvalidDeviceStatus
from custom_components.smartthinq_sensors.wideq.device_info import DeviceInfo
from custom_components.smartthinq_sensors.wideq.devices.washerDryer import WMDevice
from custom_components.smartthinq_sensors.wideq.model_info import ModelInfo


WASHER_MODEL_DATA = {
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
                {"value": "temp", "default": "FL27_TEMP_WARM"},
                {"value": "spin", "default": "SPIN_HIGH"},
                {"value": "reserveTimeHour", "default": 0},
            ],
        },
        "TOWELS": {
            "_comment": "Towels",
            "courseType": "Course",
            "name": "@WM_MP_FATIU21019_COURSE_TOWELS_W",
            "courseValue": "TOWELS",
            "function": [
                {"value": "temp", "default": "FL27_TEMP_WARM"},
                {"value": "spin", "default": "SPIN_EXTRA_HIGH"},
            ],
        },
        "DOWNLOAD": {
            "_comment": "다운로드코스",
            "courseType": "Course",
            "courseValue": "DOWNLOAD",
        },
    },
    "SmartCourse": {
        "SMALL_LOAD": {
            "_comment": "SmallLoad",
            "courseType": "SmartCourse",
            "Course": "SMALL_LOAD",
            "name": "@WM_US_FL_SMARTCOURSE_SMALL_LOAD_W",
            "downloadEnable": True,
            "courseValue": "SMALL_LOAD",
            "function": [
                {"value": "temp", "default": "FL27_TEMP_WARM"},
                {"value": "spin", "default": "SPIN_HIGH"},
                {"value": "reserveTimeHour", "default": 0},
            ],
        },
        "COLOR_CARE": {
            "_comment": "ColorCare",
            "courseType": "SmartCourse",
            "Course": "NORMAL",
            "name": "@WM_US_FL_SMARTCOURSE_COLOR_CARE_W",
            "downloadEnable": True,
            "courseValue": "COLOR_CARE",
            "function": [
                {"value": "temp", "default": "FL27_TEMP_COLD"},
                {"value": "spin", "default": "SPIN_MEDIUM"},
                {"value": "reserveTimeHour", "default": 0},
            ],
        },
        "DENIM": {
            "_comment": "Denim",
            "courseType": "SmartCourse",
            "Course": "NORMAL",
            "name": "@WM_US_FL_SMARTCOURSE_DENIM_W",
            "downloadEnable": True,
            "courseValue": "DENIM",
            "function": [
                {"value": "temp", "default": "FL27_TEMP_COLD"},
                {"value": "spin", "default": "SPIN_MEDIUM"},
                {"value": "reserveTimeHour", "default": 0},
            ],
        },
    },
}

DRYER_MODEL_DATA = {
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
        "defaultSmartCourse": "SUPERDRY",
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
                "WRINKLECARE": {"index": 5, "label": "@WM_STATE_WRINKLECARE_W"},
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
                    "childLock": "CHILDLOCK_OFF",
                    "easyIron": "EASYIRON_OFF",
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
            "name": "@WM_DRY27_COURSE_NORMAL_W",
            "function": [
                {"value": "temp", "default": "TEMP_MEDIUM"},
                {"value": "dryLevel", "default": "DRYLEVEL_NORMAL"},
                {"value": "moreLessTime", "default": 0},
            ],
        },
    },
    "SmartCourse": {
        "ULTRADELICATES": {
            "_comment": "Ultra Delicates",
            "courseType": "SmartCourse",
            "courseValue": "ULTRADELICATES",
            "Course": "ULTRA_DELICATES",
            "name": "@WM_US_DR_SMARTCOURSE_ULTRA_DELICATES_W",
            "downloadEnable": True,
            "function": [
                {"value": "temp", "default": "TEMP_ULTRALOW"},
                {"value": "dryLevel", "default": "DRYLEVEL_NORMAL"},
                {"value": "timeDry", "default": "TIMEDRY_OFF"},
                {"value": "moreLessTime", "default": 0},
            ],
        },
        "DENIM": {
            "_comment": "Denim",
            "courseType": "SmartCourse",
            "courseValue": "DENIM",
            "Course": "KHAKIJEAN",
            "name": "@WM_US_DR_SMARTCOURSE_DENIM_W",
            "downloadEnable": True,
            "function": [
                {"value": "temp", "default": "TEMP_MEDIUM"},
                {"value": "dryLevel", "default": "DRYLEVEL_NORMAL"},
                {"value": "timeDry", "default": "TIMEDRY_OFF"},
                {"value": "moreLessTime", "default": 0},
            ],
        },
    },
}

LANG_PACK = {
    "pack": {
        "@WM_MP_FATIU21019_TERM_DOWNLOADED_W": "Downloaded",
        "@WM_STATE_DOWNLOAD_COMPLETE_W": "Downloaded",
        "@WM_MP_FATIU21019_COURSE_NORMAL_W": "Normal",
        "@WM_MP_FATIU21019_COURSE_TOWELS_W": "Towels",
        "@WM_US_FL_SMARTCOURSE_SMALL_LOAD_W": "Small Load",
        "@WM_US_FL_SMARTCOURSE_COLOR_CARE_W": "Color Care",
        "@WM_US_FL_SMARTCOURSE_DENIM_W": "Denim",
        "@WM_DRY27_COURSE_NORMAL_W": "Normal",
        "@WM_US_DR_SMARTCOURSE_ULTRA_DELICATES_W": "Ultra Delicate",
        "@WM_US_DR_SMARTCOURSE_DENIM_W": "Denim",
    }
}

LOCAL_PACK = {
    "@WM_STATE_POWER_OFF_W": "STATE_POWER_OFF",
    "@WM_STATE_INITIAL_W": "STATE_INITIAL",
    "@WM_STATE_PAUSE_W": "STATE_PAUSE",
    "@WM_STATE_RUNNING_W": "Running",
    "@WM_STATE_DRYING_W": "Drying",
    "@WM_STATE_END_W": "STATE_END",
    "@WM_STATE_WRINKLECARE_W": "Wrinkle Care",
    "@CP_OFF_EN_W": "off",
    "@CP_ON_EN_W": "on",
}


class _FakeClient:
    def __init__(self, snapshot: dict):
        self.emulation = False
        self.sent: list[dict] = []
        self._snapshot = snapshot
        self.session = SimpleNamespace(
            device_v2_controls=self._device_v2_controls,
        )

    async def _device_v2_controls(
        self, device_id, ctrl_key, command=None, key=None, value=None, *, ctrl_path=None
    ):
        self.sent.append(deepcopy(ctrl_key))
        return {}

    async def refresh_auth(self):
        return None

    async def refresh(self, refresh_gateway=False):
        return None

    async def refresh_devices(self):
        return None

    def get_device(self, device_id):
        return SimpleNamespace(snapshot=deepcopy(self._snapshot))


async def _make_wm_device(
    model_data: dict, dev_type: int, wd_state: dict
) -> tuple[WMDevice, _FakeClient]:
    snap = {"washerDryer": deepcopy(wd_state)}
    client = _FakeClient(snap)
    dev_info = DeviceInfo(
        {
            "deviceId": f"dev-{dev_type}",
            "alias": "Washer" if dev_type == 201 else "Dryer",
            "deviceType": dev_type,
            "platformType": "thinq2",
            "networkType": "02",
            "modelName": model_data["Info"]["modelName"],
            "snapshot": snap,
        }
    )
    dev = WMDevice(client, dev_info)
    dev._model_data = deepcopy(model_data)
    dev._model_info = ModelInfo.get_model_info(dev._model_data)
    dev._model_lang_pack = deepcopy(LANG_PACK)
    dev._product_lang_pack = {"pack": {}}
    dev._local_lang_pack = deepcopy(LOCAL_PACK)
    await dev.poll()
    return dev, client


async def test_washer_uniprotocol_poweroff_download_and_start():
    """Washer translates DOWNLOAD to Downloaded, downloads via vtCtrl when off, and starts SmartCourse via uniProtocol."""
    dev, client = await _make_wm_device(
        WASHER_MODEL_DATA,
        201,
        {
            "state": "POWEROFF",
            "preState": "END",
            "remoteStart": "REMOTE_START_OFF",
            "childLock": "CHILDLOCK_OFF",
            "course": "NOT_SELECTED",
            "downloadCourse": "COLOR_CARE",
        },
    )

    assert dev.course_list == ["Current course", "Normal", "Towels", "Downloaded"]
    assert "다운로드코스" not in dev.course_list
    assert dev.downloaded_course_list == ["Small Load", "Color Care", "Denim"]
    assert dev.downloaded_course == "Color Care"
    assert dev.download_course_enabled is True
    assert dev.select_course_enabled is False

    # Download Denim while washer is powered off
    await dev.select_downloaded_course("Denim")
    assert dev.downloaded_course == "Denim"
    assert len(client.sent) == 1
    dl_cmd = client.sent[0]
    assert dl_cmd["ctrlKey"] == "vtCtrl"
    assert dl_cmd["command"] == "Set"
    vt_items = dl_cmd["dataSetList"]["vtData"]["UNDEFINE"]
    assert vt_items[:3] == [
        {"cmd": "downloadCourseData", "type": "ABSOLUTE", "value": "DENIM"},
        {"cmd": "course", "type": "ABSOLUTE", "value": "DOWNLOAD"},
        {"cmd": "baseDownloadCourseData", "type": "ABSOLUTE", "value": "NORMAL"},
    ]
    assert {"cmd": "reserveTimeMinute", "type": "ABSOLUTE", "value": "0"} in vt_items
    assert all(item["cmd"] != "wmControl" for item in vt_items)

    # Now arm Remote Start in INITIAL state, pick Small Load, and press Start
    client.sent.clear()
    client._snapshot = {
        "washerDryer": {
            "state": "INITIAL",
            "preState": "POWEROFF",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "course": "NORMAL",
            "downloadCourse": "DENIM",
        }
    }
    await dev.poll()
    assert dev.select_course_enabled is True

    await dev.select_downloaded_course("Small Load")
    assert dev.downloaded_course == "Small Load"
    assert dev.selected_course == "Downloaded"

    await dev.remote_start()
    assert len(client.sent) == 2
    start_cmd = client.sent[1]
    assert start_cmd["dataSetList"]["vtData"]["UNDEFINE"] == [
        {"cmd": "course", "type": "ABSOLUTE", "value": "DOWNLOAD"},
        {"cmd": "downloadCourseData", "type": "ABSOLUTE", "value": "SMALL_LOAD"},
        {"cmd": "baseDownloadCourseData", "type": "ABSOLUTE", "value": "SMALL_LOAD"},
        {"cmd": "wmControl", "type": "ABSOLUTE", "value": "START"},
    ]


async def test_washer_uniprotocol_standard_course_and_pause_resume():
    """Washer uniProtocol sends cmd=course on standard start and wmControl=RESUME from PAUSE."""
    dev, client = await _make_wm_device(
        WASHER_MODEL_DATA,
        201,
        {
            "state": "INITIAL",
            "preState": "POWEROFF",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "course": "NORMAL",
            "downloadCourse": "COLOR_CARE",
        },
    )
    await dev.select_start_course("Towels")
    await dev.remote_start()
    assert client.sent[0]["dataSetList"]["vtData"]["UNDEFINE"] == [
        {"cmd": "course", "type": "ABSOLUTE", "value": "TOWELS"},
        {"cmd": "wmControl", "type": "ABSOLUTE", "value": "START"},
    ]

    # Running disables download_course_enabled; PAUSE resumes with RESUME
    client.sent.clear()
    client._snapshot = {
        "washerDryer": {
            "state": "RUNNING",
            "preState": "INITIAL",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "course": "DOWNLOAD",
            "downloadCourse": "COLOR_CARE",
        }
    }
    await dev.poll()
    assert dev.download_course_enabled is False
    wrapper = LGEWashDevice(SimpleNamespace(state=dev.status, device=dev))
    assert wrapper.current_course == "Color Care"

    client._snapshot["washerDryer"]["state"] = "PAUSE"
    await dev.poll()
    await dev.remote_start()
    assert client.sent[0]["dataSetList"]["vtData"]["UNDEFINE"] == [
        {"cmd": "wmControl", "type": "ABSOLUTE", "value": "RESUME"},
    ]


async def test_dryer_wmdownload_and_wmstart_smartcourse():
    """Dryer reads downloadedCourseDryer27inchBase when off, downloads via WMDownload, and starts via WMStart."""
    dev, client = await _make_wm_device(
        DRYER_MODEL_DATA,
        202,
        {
            "state": "POWEROFF",
            "preState": "WRINKLECARE",
            "remoteStart": "REMOTE_START_OFF",
            "childLock": "CHILDLOCK_OFF",
            "initialBit": "INITIAL_BIT_OFF",
            "courseDryer27inchBase": "NOT_SELECTED",
            "smartCourseDryer27inchBase": "NOT_SELECTED",
            "downloadedCourseDryer27inchBase": "ULTRADELICATES",
        },
    )

    assert dev.course_list == ["Current course", "Normal", "Downloaded"]
    assert dev.downloaded_course_list == ["Ultra Delicate", "Denim"]
    assert dev.downloaded_course == "Ultra Delicate"
    assert dev.download_course_enabled is True

    await dev.select_downloaded_course("Denim")
    assert dev.downloaded_course == "Denim"
    dl_cmd = client.sent[0]
    assert dl_cmd["ctrlKey"] == "WMDownload"
    assert dl_cmd["command"] == "Set"
    wd = dl_cmd["dataSetList"]["washerDryer"]
    assert wd["courseDryer27inchBase"] == "KHAKIJEAN"
    assert wd["smartCourseDryer27inchBase"] == "DENIM"
    assert wd["courseType"] == "SmartCourse"
    assert wd["courseDownloadType"] == "COURSEDATA"
    assert wd["initialBit"] == "INITIAL_BIT_OFF"
    assert "Course" not in wd

    # Arm Remote Start in INITIAL state, verify SmartCourse WMStart & standard course NOT_SELECTED
    client.sent.clear()
    client._snapshot = {
        "washerDryer": {
            "state": "INITIAL",
            "preState": "POWEROFF",
            "remoteStart": "REMOTE_START_ON",
            "childLock": "CHILDLOCK_OFF",
            "initialBit": "INITIAL_BIT_ON",
            "courseDryer27inchBase": "NORMAL",
            "smartCourseDryer27inchBase": "NOT_SELECTED",
            "downloadedCourseDryer27inchBase": "DENIM",
        }
    }
    await dev.poll()
    await dev.select_start_course("Downloaded")
    await dev.remote_start()
    start_wd = client.sent[0]["dataSetList"]["washerDryer"]
    assert start_wd["courseDryer27inchBase"] == "KHAKIJEAN"
    assert start_wd["smartCourseDryer27inchBase"] == "DENIM"
    assert start_wd["courseType"] == "SmartCourse"
    assert start_wd["initialBit"] == "INITIAL_BIT_ON"

    # Standard course sets smartCourseDryer27inchBase to NOT_SELECTED (not integer 0)
    client.sent.clear()
    dev._remote_start_pressed = False
    await dev.select_start_course("Normal")
    await dev.remote_start()
    std_wd = client.sent[0]["dataSetList"]["washerDryer"]
    assert std_wd["courseDryer27inchBase"] == "NORMAL"
    assert std_wd["smartCourseDryer27inchBase"] == "NOT_SELECTED"

    # Child lock blocks download
    client._snapshot["washerDryer"]["childLock"] = "CHILDLOCK_ON"
    await dev.poll()
    assert dev.download_course_enabled is False
    with pytest.raises(InvalidDeviceStatus):
        await dev.select_downloaded_course("Ultra Delicate")


async def test_select_exist_respects_has_downloaded_courses():
    """downloaded_course select entity is created only when model defines SmartCourse."""
    dl_desc = next(d for d in WASH_DEV_SELECT if d.key == "downloaded_course")
    dev_with = SimpleNamespace(device=SimpleNamespace(has_downloaded_courses=True))
    dev_without = SimpleNamespace(device=SimpleNamespace(has_downloaded_courses=False))
    assert _select_exist(dev_with, dl_desc) is True
    assert _select_exist(dev_without, dl_desc) is False
