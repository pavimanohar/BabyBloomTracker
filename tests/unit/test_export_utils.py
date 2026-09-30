from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace
import os
import pytest

import utils.export_utils as mod


def test_get_export_dir_without_running_app(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "App", None)
    monkeypatch.setattr(mod, "APP_DIR", str(tmp_path))
    result = mod.get_export_dir()
    assert result == os.path.join(str(tmp_path), "data", "exports")
    assert os.path.isdir(result)


def test_date_range_dates_single_and_multiple():
    assert list(mod.date_range_dates("2026-09-23", "2026-09-23")) == ["2026-09-23"]
    assert list(mod.date_range_dates("2026-09-23", "2026-09-25")) == [
        "2026-09-23","2026-09-24","2026-09-25"]


def test_date_range_dates_rejects_reverse():
    with pytest.raises(ValueError, match="on or after"):
        list(mod.date_range_dates("2026-09-25", "2026-09-23"))


def test_normalize_ranges_sorts_and_deduplicates():
    assert mod.normalize_ranges([
        ("2026-09-25","2026-09-25"),
        ("2026-09-23","2026-09-24"),
        ("2026-09-25","2026-09-25"),
    ]) == [("2026-09-23","2026-09-24"),("2026-09-25","2026-09-25")]


def test_normalize_ranges_rejects_reverse():
    with pytest.raises(ValueError):
        mod.normalize_ranges([("2026-09-25","2026-09-23")])


def test_range_label():
    assert mod.range_label("2026-09-23","2026-09-23") == "23 Sep 2026"
    assert mod.range_label("2026-09-23","2026-09-25") == "23 Sep 2026 – 25 Sep 2026"


def test_rows_by_date_and_slot_map():
    rows = [
        {"log_date":"2026-09-23","slot":"Before Breakfast","value":100},
        {"log_date":"2026-09-23","slot":"Before Breakfast","value":105},
        {"log_date":"2026-09-24","slot":"After Lunch","value":130},
    ]
    assert len(mod._rows_by_date(rows)["2026-09-23"]) == 2
    assert len(mod._slot_map(rows)["Before Breakfast"]) == 2


def test_format_sugar_values():
    assert mod._format_sugar_values([{"value":100},{"value":105.5},{"value":"bad"}]) == "100 / 105.5"
    assert mod._format_sugar_values([{"value":"bad"}]) == "-"


@pytest.mark.parametrize(
    "row,expected",
    [
        ({"value1":120,"value2":80},"120/80"),
        ({"value1":75,"value2":None},"75"),
        ({"value1":None,"value2":None},"-"),
        ({"value1":"120","value2":"80"},"-"),
    ],
)
def test_format_vital_value(row, expected):
    assert mod.format_vital_value(row) == expected


def test_vital_values_groups_and_ignores_missing():
    rows = [
        {"vital_type":"BP","value1":120,"value2":80},
        {"vital_type":"BP","value1":125,"value2":82},
        {"vital_type":"O2","value1":98,"value2":None},
        {"vital_type":"Pulse","value1":None,"value2":None},
    ]
    result = mod._vital_values(rows)
    assert result["Blood Pressure"] == ["120/80","125/82"]
    assert result["Oxygen (SpO2)"] == ["98"]
    assert "Pulse" not in result


def test_build_daily_sugar_sections():
    rows = [{"log_date":"2026-09-23","slot":"Before Breakfast","value":100}]
    headers, sections = mod.build_daily_sugar_sections(rows,[("2026-09-23","2026-09-24")])
    assert headers[0] == "Date"
    assert sections[0][1][0][0] == "2026-09-23"
    assert "100" in sections[0][1][0]


def test_build_daily_vitals_sections():
    rows = [{"log_date":"2026-09-23","vital_type":"BP","value1":120,"value2":80}]
    headers, sections = mod.build_daily_vitals_sections(rows,[("2026-09-23","2026-09-24")])
    assert headers == ["Date","Blood Pressure","O2","Pulse","Weight"]
    assert sections[0][1][0][1] == "120/80"
    assert sections[0][1][1][1] == "-"


def test_build_daily_generic_sections():
    rows = [{"event_date":"2026-09-23","title":"Scan","event_type":"appointment","notes":"Clinic"}]
    headers, sections = mod.build_daily_generic_sections(
        rows,[("2026-09-23","2026-09-24")],"event_date",
        [("Events","title"),("Type","event_type"),("Notes","notes")])
    assert headers == ["Date","Events","Type","Notes"]
    assert sections[0][1][0][1:] == ["Scan","appointment","Clinic"]
    assert sections[0][1][1][1:] == ["-","-","-"]

def test_build_combined_sections_all_categories():
    selected = {
        "sugar":[{"log_date":"2026-09-23","slot":"Before Breakfast","value":100}],
        "vitals":[{"log_date":"2026-09-23","vital_type":"BP","value1":120,"value2":80}],
        "medications":[{"log_date":"2026-09-23","name":"Iron","dosage":"1","scheduled_time":"09:00","taken":1}],
        "calendar":[{"event_date":"2026-09-23","title":"Scan"}],
        "consultation":[{"log_date":"2026-09-23","notes":"Fine"}],
    }

    headers, sections = mod.build_combined_sections(
        selected,
        [("2026-09-23","2026-09-23")]
    )

    row = sections[0][1][0]

    assert headers[0] == "Date"
    assert "100" in row
    assert "120/80" in row
    assert row[11] == "Iron (1) @ 09:00 — Taken"
    assert row[12] == "Scan"
    assert row[13] == "Fine"

class FakeCursor:
    def __init__(self, rows, columns):
        self._rows = rows
        self.description = [(c,) for c in columns]
    def fetchall(self):
        return self._rows


def test_rows_for_report_selection_all_db_categories():
    db = Mock()
    db.get_sugar_range.return_value = ["sugar"]
    db.get_vitals_range.return_value = ["vitals"]
    db.conn.execute.side_effect = [
        FakeCursor([(1,"Iron")],["id","name"]),
        FakeCursor([(2,"Scan")],["id","title"]),
        FakeCursor([(3,"Note")],["id","notes"]),
    ]
    assert mod._rows_for_report_selection(db,"sugar","a","b") == ["sugar"]
    assert mod._rows_for_report_selection(db,"vitals","a","b") == ["vitals"]
    assert mod._rows_for_report_selection(db,"medications","a","b")[0]["name"] == "Iron"
    assert mod._rows_for_report_selection(db,"calendar","a","b")[0]["title"] == "Scan"
    assert mod._rows_for_report_selection(db,"consultation","a","b")[0]["notes"] == "Note"
    assert mod._rows_for_report_selection(db,"unknown","a","b") == []


@pytest.mark.parametrize("category",["sugar","vitals","medications","calendar","consultation","unknown"])
def test_report_section_categories(category):
    selection = {"category":category,"label":"Label","start":"2026-09-23","end":"2026-09-23"}
    rows = {
        "sugar":[{"log_date":"2026-09-23","slot":"Before Breakfast","value":100}],
        "vitals":[{"log_date":"2026-09-23","vital_type":"BP","value1":120,"value2":80}],
        "medications":[{"log_date":"2026-09-23","name":"Iron","dosage":"1","scheduled_time":"09:00","taken":1}],
        "calendar":[{"event_date":"2026-09-23","title":"Scan","event_type":"scan","notes":""}],
        "consultation":[{"log_date":"2026-09-23","notes":"Fine"}],
        "unknown":[],
    }[category]
    result = mod._report_section(selection, rows)
    assert result[0].startswith("Label")
    assert result[1][0] == "Date"


def test_report_section_invalid_range():
    selection = {"category":"sugar","label":"Sugar","start":"2026-09-25","end":"2026-09-23"}
    with pytest.raises(ValueError):
        mod._report_section(selection, [])


def test_generic_excel_creates_valid_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    path = mod._generic_excel(["Date","Value"], [("23 Sep", [["2026-09-23","100"]])],
                              "Test","test", [13,20], "test.xlsx")
    assert Path(path).is_file()
    from openpyxl import load_workbook
    wb = load_workbook(path)
    assert wb.active["A1"].value == "BabyBloom"
    assert wb.active["A5"].value == "2026-09-23"
    assert wb.active["B5"].value == "100"


def test_generic_pdf_creates_valid_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    path = mod._generic_pdf(["Date","Value"], [("23 Sep", [["2026-09-23","100"]])],
                            "Test","test", "test.pdf")
    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0


def test_export_wrappers(monkeypatch):
    calls = []
    monkeypatch.setattr(mod, "_generic_excel", lambda *a, **k: calls.append(("xlsx",a,k)) or "x")
    monkeypatch.setattr(mod, "_generic_pdf", lambda *a, **k: calls.append(("pdf",a,k)) or "p")
    rows = [{"log_date":"2026-09-23","slot":"Before Breakfast","value":100}]
    assert mod.export_sugar_to_excel(rows) == "x"
    assert mod.export_sugar_to_pdf(rows) == "p"
    assert len(calls) == 2


def test_vitals_export_wrappers(monkeypatch):
    calls = []
    monkeypatch.setattr(mod, "_generic_excel", lambda *a, **k: calls.append(("xlsx",a,k)) or "x")
    monkeypatch.setattr(mod, "_generic_pdf", lambda *a, **k: calls.append(("pdf",a,k)) or "p")
    rows = [{"log_date":"2026-09-23","vital_type":"O2","value1":98,"value2":None}]
    assert mod.export_vitals_to_excel(rows) == "x"
    assert mod.export_vitals_to_pdf(rows) == "p"


def test_calendar_and_notes_export_wrappers(monkeypatch):
    monkeypatch.setattr(mod, "_generic_excel", lambda *a, **k: "x")
    monkeypatch.setattr(mod, "_generic_pdf", lambda *a, **k: "p")
    events = [{"event_date":"2026-09-23","title":"Scan","event_type":"scan","notes":""}]
    notes = [{"log_date":"2026-09-23","notes":"Fine"}]
    assert mod.export_calendar_to_excel(events) == "x"
    assert mod.export_calendar_to_pdf(events) == "p"
    assert mod.export_consultation_notes_to_excel(notes) == "x"
    assert mod.export_consultation_notes_to_pdf(notes) == "p"


def test_combined_exports_empty_rejected():
    with pytest.raises(ValueError):
        mod.export_combined_to_excel({})
    with pytest.raises(ValueError):
        mod.export_combined_to_pdf({})


def test_combined_exports_delegate(monkeypatch):
    monkeypatch.setattr(mod, "_generic_excel", lambda *a, **k: "xlsx")
    monkeypatch.setattr(mod, "_generic_pdf", lambda *a, **k: "pdf")
    selected = {"sugar":[{"log_date":"2026-09-23","slot":"Before Breakfast","value":100}]}
    assert mod.export_combined_to_excel(selected) == "xlsx"
    assert mod.export_combined_to_pdf(selected) == "pdf"


def test_medications_export_delegate(monkeypatch):
    monkeypatch.setattr(mod, "_generic_excel", lambda *a, **k: "xlsx")
    rows = [{"log_date":"2026-09-23","name":"Iron","dosage":"1","scheduled_time":"09:00","taken":1}]
    assert mod.export_medications_to_excel(rows) == "xlsx"


def test_delete_export(tmp_path):
    path = tmp_path / "x.pdf"
    path.write_text("x")
    assert mod.delete_export(str(path)) is True
    assert not path.exists()
    assert mod.delete_export(str(path)) is True


def test_delete_export_os_error(monkeypatch):
    monkeypatch.setattr(mod.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(mod.os, "remove", Mock(side_effect=OSError("no")))
    assert mod.delete_export("x") is False


def test_write_media_store_copy_non_android(monkeypatch, tmp_path):
    monkeypatch.setitem(__import__("sys").modules, "kivy.utils", Mock(platform="linux"))
    path = tmp_path / "x.pdf"
    path.write_bytes(b"x")
    assert mod._write_media_store_copy(str(path), "application/pdf") is None


def test_save_to_public_downloads_none_when_media_copy_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_write_media_store_copy", lambda *a: None)
    assert mod.save_to_public_downloads(str(tmp_path/"x.pdf"), "application/pdf") is None


def test_share_exported_file_desktop_success(monkeypatch, tmp_path):
    share = Mock()
    monkeypatch.setitem(__import__("sys").modules, "plyer", SimpleNamespace(share=share))
    monkeypatch.setattr(mod, "_write_media_store_copy", lambda *a: None)
    monkeypatch.setitem(__import__("sys").modules, "kivy.utils", SimpleNamespace(platform="linux"))
    assert mod.share_exported_file("x.pdf","application/pdf") is True
    share.share.assert_called_once()


def test_share_exported_file_desktop_failure(monkeypatch):
    share = Mock()
    share.share.side_effect = RuntimeError("x")
    monkeypatch.setitem(__import__("sys").modules, "plyer", SimpleNamespace(share=share))
    monkeypatch.setitem(__import__("sys").modules, "kivy.utils", SimpleNamespace(platform="linux"))
    assert mod.share_exported_file("x.pdf","application/pdf") is False


def test_open_exported_file_non_android(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "kivy.utils", SimpleNamespace(platform="linux"))
    assert mod.open_exported_file("x.pdf","application/pdf") is False


def test_pdf_branding_without_logo(monkeypatch, running_mdapp):
    from reportlab.lib.styles import getSampleStyleSheet
    elements = []
    monkeypatch.setattr(mod.os.path, "isfile", lambda p: False)
    mod._pdf_branding(elements, getSampleStyleSheet(), "Subtitle")
    assert len(elements) == 3


def test_export_sugar_report_pdf_empty_rejected():
    with pytest.raises(ValueError, match="No blood sugar"):
        mod._export_sugar_report_pdf([], "2026-09-23", "2026-09-23")


def test_export_sugar_report_pdf_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    rows = [
        {"id":2,"log_date":"2026-09-24","value":120,"reading_time":"10:00","fasting":0,
         "slot":"After Lunch","previous_meal_time":"08:00","notes":"ok"},
        {"id":1,"log_date":"2026-09-23","value":100,"reading_time":"08:00","fasting":1,
         "slot":"Before Breakfast","previous_meal_time":"","notes":""},
    ]
    path = mod._export_sugar_report_pdf(rows,"2026-09-23","2026-09-24","sugar.pdf")
    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0


def test_export_selected_reports_empty():
    with pytest.raises(ValueError):
        mod.export_selected_reports_to_pdf([])


def test_export_selected_reports_invalid_range(monkeypatch):
    monkeypatch.setattr(mod.Database, "instance", classmethod(lambda cls: Mock()))
    with pytest.raises(ValueError, match="Start Date"):
        mod.export_selected_reports_to_pdf([{
            "category":"vitals","label":"Vitals","start":"2026-09-25","end":"2026-09-23"
        }])


def test_export_selected_reports_sugar_special_path(monkeypatch, tmp_path):
    db = Mock()
    monkeypatch.setattr(mod.Database, "instance", classmethod(lambda cls: db))
    monkeypatch.setattr(mod, "_rows_for_report_selection", lambda *a: [{"value":100}])
    monkeypatch.setattr(mod, "_export_sugar_report_pdf", lambda *a, **k: "sugar.pdf")
    assert mod.export_selected_reports_to_pdf([{
        "category":"sugar","label":"Blood Sugar","start":"2026-09-23","end":"2026-09-23"
    }]) == "sugar.pdf"

# ---------------------------------------------------------------------------
# Additional coverage: export directory / Android MediaStore / sharing /
# opening / exception paths
# ---------------------------------------------------------------------------

def test_get_export_dir_with_running_app(monkeypatch, tmp_path):
    app = SimpleNamespace(user_data_dir=str(tmp_path / "appdata"))
    monkeypatch.setattr(mod, "App", SimpleNamespace(get_running_app=lambda: app))

    result = mod.get_export_dir()

    assert result == os.path.join(str(tmp_path / "appdata"), "exports")
    assert os.path.isdir(result)


class FakeContentValues:
    def __init__(self, fail_pending=False):
        self.values = {}
        self.fail_pending = fail_pending

    def put(self, key, value):
        if self.fail_pending and key == "IS_PENDING":
            raise RuntimeError("pending unsupported")
        self.values[key] = value


class FakeOutputStream:
    def __init__(self, fail_write=False):
        self.data = b""
        self.closed = False
        self.fail_write = fail_write

    def write(self, data):
        if self.fail_write:
            raise RuntimeError("write failed")
        self.data += data

    def close(self):
        self.closed = True


class FakeResolver:
    def __init__(
        self,
        uri="content://babybloom/1",
        output_stream=None,
        fail_insert=False,
        fail_delete=False,
        fail_update=False,
    ):
        self.uri = uri
        self.output_stream = output_stream
        self.fail_insert = fail_insert
        self.fail_delete = fail_delete
        self.fail_update = fail_update
        self.deleted = []
        self.updated = []
        self.inserted = []

    def insert(self, collection, values):
        if self.fail_insert:
            raise RuntimeError("insert failed")
        self.inserted.append((collection, values))
        return self.uri

    def openOutputStream(self, uri):
        return self.output_stream

    def delete(self, uri, where, args):
        if self.fail_delete:
            raise RuntimeError("delete failed")
        self.deleted.append((uri, where, args))

    def update(self, uri, values, where, args):
        if self.fail_update:
            raise RuntimeError("update failed")
        self.updated.append((uri, values, where, args))


class FakeContext:
    def __init__(self, resolver, fail_start=False):
        self.resolver = resolver
        self.fail_start = fail_start
        self.started = []

    def getContentResolver(self):
        return self.resolver

    def startActivity(self, intent):
        if self.fail_start:
            raise RuntimeError("startActivity failed")
        self.started.append(intent)


class FakePythonActivity:
    def __init__(self, context):
        self.mActivity = context


class FakeIntent:
    ACTION_SEND = "ACTION_SEND"
    ACTION_VIEW = "ACTION_VIEW"
    EXTRA_STREAM = "EXTRA_STREAM"
    FLAG_GRANT_READ_URI_PERMISSION = 1
    FLAG_ACTIVITY_NEW_TASK = 2

    def __init__(self, action):
        self.action = action
        self.type = None
        self.extras = []
        self.flags = []
        self.clip_data = None
        self.data = None

    def setType(self, value):
        self.type = value

    def putExtra(self, key, value):
        self.extras.append((key, value))

    def addFlags(self, value):
        self.flags.append(value)

    def setClipData(self, value):
        self.clip_data = value

    def setDataAndType(self, uri, mime_type):
        self.data = (uri, mime_type)

    @classmethod
    def createChooser(cls, intent, title):
        chooser = cls("CHOOSER")
        chooser.intent = intent
        chooser.title = title
        return chooser


class FakeClipData:
    @classmethod
    def newRawUri(cls, label, uri):
        return (label, uri)


def install_fake_android(
    monkeypatch,
    resolver,
    *,
    content_values_cls=FakeContentValues,
    intent_cls=FakeIntent,
    context=None,
):
    if context is None:
        context = FakeContext(resolver)

    python_activity = FakePythonActivity(context)

    classes = {
        "org.kivy.android.PythonActivity": python_activity,
        "android.content.ContentValues": content_values_cls,
        "android.provider.MediaStore$MediaColumns":
            SimpleNamespace(
                DISPLAY_NAME="DISPLAY_NAME",
                MIME_TYPE="MIME_TYPE",
                RELATIVE_PATH="RELATIVE_PATH",
                IS_PENDING="IS_PENDING",
            ),
        "android.provider.MediaStore$Downloads":
            SimpleNamespace(EXTERNAL_CONTENT_URI="DOWNLOADS"),
        "android.content.Intent": intent_cls,
        "android.content.ClipData": FakeClipData,
    }

    jnius_module = SimpleNamespace(
        autoclass=lambda name: classes[name],
        cast=lambda _type, value: value,
    )

    monkeypatch.setitem(
        __import__("sys").modules,
        "jnius",
        jnius_module,
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "kivy.utils",
        SimpleNamespace(platform="android"),
    )

    return context


def test_write_media_store_copy_android_success(monkeypatch, tmp_path):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"PDF-DATA")

    stream = FakeOutputStream()
    resolver = FakeResolver(output_stream=stream)
    install_fake_android(monkeypatch, resolver)

    uri = mod._write_media_store_copy(
        str(source),
        "application/pdf",
    )

    assert uri == "content://babybloom/1"
    assert stream.data == b"PDF-DATA"
    assert stream.closed is True
    assert resolver.deleted == []
    assert len(resolver.updated) == 1


def test_write_media_store_copy_android_pending_failure_is_ignored(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"PDF-DATA")

    stream = FakeOutputStream()
    resolver = FakeResolver(output_stream=stream)

    class PendingFailContentValues(FakeContentValues):
        def put(self, key, value):
            if key == "IS_PENDING":
                raise RuntimeError("pending unsupported")
            super().put(key, value)

    install_fake_android(
        monkeypatch,
        resolver,
        content_values_cls=PendingFailContentValues,
    )

    uri = mod._write_media_store_copy(
        str(source),
        "application/pdf",
    )

    assert uri == "content://babybloom/1"
    assert stream.data == b"PDF-DATA"


def test_write_media_store_copy_android_insert_returns_none(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    resolver = FakeResolver(uri=None)
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None


def test_write_media_store_copy_android_output_stream_none(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    resolver = FakeResolver(output_stream=None)
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None

    assert resolver.deleted == [
        ("content://babybloom/1", None, None)
    ]


def test_write_media_store_copy_android_write_failure_cleans_up(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    stream = FakeOutputStream(fail_write=True)
    resolver = FakeResolver(output_stream=stream)
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None

    assert stream.closed is True
    assert resolver.deleted == [
        ("content://babybloom/1", None, None)
    ]


def test_write_media_store_copy_android_write_failure_delete_failure(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    stream = FakeOutputStream(fail_write=True)
    resolver = FakeResolver(
        output_stream=stream,
        fail_delete=True,
    )
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None

    assert stream.closed is True


def test_write_media_store_copy_android_outer_exception(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    class ExplodingContentValues:
        def __init__(self):
            raise RuntimeError("ContentValues unavailable")

    resolver = FakeResolver()
    install_fake_android(
        monkeypatch,
        resolver,
        content_values_cls=ExplodingContentValues,
    )

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None


def test_write_media_store_copy_android_update_failure_is_ignored(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    stream = FakeOutputStream()
    resolver = FakeResolver(
        output_stream=stream,
        fail_update=True,
    )
    install_fake_android(monkeypatch, resolver)

    uri = mod._write_media_store_copy(
        str(source),
        "application/pdf",
    )

    assert uri == "content://babybloom/1"
    assert stream.data == b"x"


def test_save_to_public_downloads_success(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mod,
        "_write_media_store_copy",
        lambda *args: "content://babybloom/123",
    )

    result = mod.save_to_public_downloads(
        str(tmp_path / "report.pdf"),
        "application/pdf",
    )

    assert result == "Downloads/BabyBloom/report.pdf"


def test_share_exported_file_android_success(monkeypatch, tmp_path):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    resolver = FakeResolver(
        output_stream=FakeOutputStream(),
    )
    context = install_fake_android(monkeypatch, resolver)

    assert mod.share_exported_file(
        str(source),
        "application/pdf",
    ) is True

    assert len(context.started) == 1
    chooser = context.started[0]
    assert chooser.title == "Share BabyBloom PDF"


def test_share_exported_file_android_media_store_failure(monkeypatch):
    resolver = FakeResolver()
    install_fake_android(monkeypatch, resolver)

    monkeypatch.setattr(
        mod,
        "_write_media_store_copy",
        lambda *args: None,
    )

    assert mod.share_exported_file(
        "report.pdf",
        "application/pdf",
    ) is False


def test_share_exported_file_android_start_activity_failure(
    monkeypatch,
):
    resolver = FakeResolver()
    context = install_fake_android(
        monkeypatch,
        resolver,
        context=FakeContext(
            resolver,
            fail_start=True,
        ),
    )

    monkeypatch.setattr(
        mod,
        "_write_media_store_copy",
        lambda *args: "content://babybloom/1",
    )

    assert mod.share_exported_file(
        "report.pdf",
        "application/pdf",
    ) is False


def test_open_exported_file_android_success(monkeypatch):
    resolver = FakeResolver()
    context = install_fake_android(monkeypatch, resolver)

    monkeypatch.setattr(
        mod,
        "_write_media_store_copy",
        lambda *args: "content://babybloom/1",
    )

    assert mod.open_exported_file(
        "report.pdf",
        "application/pdf",
    ) is True

    assert len(context.started) == 1
    intent = context.started[0]
    assert intent.action == FakeIntent.ACTION_VIEW
    assert intent.data == (
        "content://babybloom/1",
        "application/pdf",
    )


def test_open_exported_file_android_media_store_failure(monkeypatch):
    resolver = FakeResolver()
    install_fake_android(monkeypatch, resolver)

    monkeypatch.setattr(
        mod,
        "_write_media_store_copy",
        lambda *args: None,
    )

    assert mod.open_exported_file(
        "report.pdf",
        "application/pdf",
    ) is False


def test_open_exported_file_android_start_activity_failure(monkeypatch):
    resolver = FakeResolver()
    install_fake_android(
        monkeypatch,
        resolver,
        context=FakeContext(
            resolver,
            fail_start=True,
        ),
    )

    monkeypatch.setattr(
        mod,
        "_write_media_store_copy",
        lambda *args: "content://babybloom/1",
    )

    assert mod.open_exported_file(
        "report.pdf",
        "application/pdf",
    ) is False

# ---------------------------------------------------------------------------
# Additional coverage: report sections / combined exports / real PDF paths
# ---------------------------------------------------------------------------

def test_report_section_medications_all_statuses():
    selection = {
        "category": "medications",
        "label": "Medications",
        "start": "2026-09-23",
        "end": "2026-09-24",
    }

    rows = [
        {
            "log_date": "2026-09-23",
            "name": "",
            "dosage": "",
            "scheduled_time": "",
            "taken": 1,
        },
        {
            "log_date": "2026-09-23",
            "name": "Iron",
            "dosage": "1",
            "scheduled_time": "09:00",
            "taken": 0,
        },
        {
            "log_date": "2026-09-23",
            "name": "Vitamin",
            "dosage": "1",
            "scheduled_time": "12:00",
            "taken": None,
        },
    ]

    label, headers, sections = mod._report_section(selection, rows)

    assert label.startswith("Medications")
    assert headers == [
        "Date",
        "Medication",
        "Dosage",
        "Time",
        "Status",
    ]

    assert sections[0][1:] == ["-", "-", "-", "Taken"]
    assert sections[1][1:] == ["Iron", "1", "09:00", "Not taken"]
    assert sections[2][1:] == ["Vitamin", "1", "12:00", "-"]

    # The second date has no records.
    assert sections[-1] == [
        "2026-09-24",
        "-",
        "-",
        "-",
        "-",
    ]


def test_report_section_calendar_and_consultation_empty_dates():
    calendar_selection = {
        "category": "calendar",
        "label": "Calendar",
        "start": "2026-09-23",
        "end": "2026-09-24",
    }

    label, headers, sections = mod._report_section(
        calendar_selection,
        [],
    )

    assert label.startswith("Calendar")
    assert headers == ["Date", "Event", "Type", "Notes"]
    assert sections[0] == [
        "2026-09-23",
        "-",
        "-",
        "-",
    ]

    consultation_selection = {
        "category": "consultation",
        "label": "Consultation",
        "start": "2026-09-23",
        "end": "2026-09-24",
    }

    _, headers, sections = mod._report_section(
        consultation_selection,
        [],
    )

    assert headers == ["Date", "Notes"]
    assert sections[1] == ["2026-09-24", "-"]


def test_build_combined_sections_each_optional_category_independently():
    ranges = [("2026-09-23", "2026-09-24")]

    category_rows = {
        "sugar": [{
            "log_date": "2026-09-23",
            "slot": "Before Breakfast",
            "value": 100,
        }],
        "vitals": [{
            "log_date": "2026-09-23",
            "vital_type": "BP",
            "value1": 120,
            "value2": 80,
        }],
        "medications": [{
            "log_date": "2026-09-23",
            "name": "Iron",
            "dosage": "1",
            "scheduled_time": "09:00",
            "taken": 0,
        }],
        "calendar": [{
            "event_date": "2026-09-23",
            "title": "Scan",
        }],
        "consultation": [{
            "log_date": "2026-09-23",
            "notes": "Fine",
        }],
    }

    for category, rows in category_rows.items():
        headers, sections = mod.build_combined_sections(
            {category: rows},
            ranges,
        )

        assert headers[0] == "Date"
        assert len(sections) == 1
        assert len(sections[0][1]) == 2


def test_export_selected_reports_non_sugar_success(monkeypatch):
    db = Mock()
    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    monkeypatch.setattr(
        mod,
        "_rows_for_report_selection",
        lambda *args: [],
    )

    monkeypatch.setattr(
        mod,
        "_pdf_branding",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        mod,
        "get_export_dir",
        lambda: str(Path.cwd()),
    )

    # Use a temporary output filename and exercise the actual generic
    # combined-report PDF path.
    output = Path.cwd() / "test_combined_report.pdf"

    try:
        result = mod.export_selected_reports_to_pdf(
            [{
                "category": "vitals",
                "label": "Vitals",
                "start": "2026-09-23",
                "end": "2026-09-23",
            }],
            filename=output.name,
        )

        assert Path(result).is_file()
        assert Path(result).stat().st_size > 0
    finally:
        if output.exists():
            output.unlink()


def test_export_combined_to_excel_real_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod,
        "get_export_dir",
        lambda: str(tmp_path),
    )

    selected = {
        "sugar": [{
            "log_date": "2026-09-23",
            "slot": "Before Breakfast",
            "value": 100,
        }],
    }

    path = mod.export_combined_to_excel(
        selected,
        filename="combined.xlsx",
    )

    assert Path(path).is_file()


def test_export_combined_to_pdf_real_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod,
        "get_export_dir",
        lambda: str(tmp_path),
    )

    selected = {
        "sugar": [{
            "log_date": "2026-09-23",
            "slot": "Before Breakfast",
            "value": 100,
        }],
    }

    path = mod.export_combined_to_pdf(
        selected,
        filename="combined.pdf",
    )

    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0


def test_export_medications_to_excel_not_taken_value(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod,
        "get_export_dir",
        lambda: str(tmp_path),
    )

    rows = [{
        "log_date": "2026-09-23",
        "name": "Iron",
        "dosage": "1",
        "scheduled_time": "09:00",
        "taken": 0,
    }]

    path = mod.export_medications_to_excel(
        rows,
        filename="medications.xlsx",
    )

    assert Path(path).is_file()


def test_generic_excel_logo_failure_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod,
        "get_export_dir",
        lambda: str(tmp_path),
    )

    monkeypatch.setattr(
        mod.os.path,
        "isfile",
        lambda path: path == mod.LOGO_PATH,
    )

    class FailingImage:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("image failure")

    import openpyxl.drawing.image

    monkeypatch.setattr(
        openpyxl.drawing.image,
        "Image",
        FailingImage,
    )

    path = mod._generic_excel(
        ["Date", "Value"],
        [("23 Sep", [["2026-09-23", "100"]])],
        "Test",
        "test",
        [13, 20],
        "logo_failure.xlsx",
    )

    assert Path(path).is_file()


def test_pdf_branding_logo_failure_falls_back(monkeypatch):
    from reportlab.lib.styles import getSampleStyleSheet

    monkeypatch.setattr(
        mod.os.path,
        "isfile",
        lambda path: path == mod.LOGO_PATH,
    )

    class FailingImage:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("logo failure")

    import reportlab.platypus

    monkeypatch.setattr(
        reportlab.platypus,
        "Image",
        FailingImage,
    )

    elements = []
    mod._pdf_branding(
        elements,
        getSampleStyleSheet(),
        "Subtitle",
    )

    assert len(elements) == 3

# ---------------------------------------------------------------------------
# Final uncovered-line / exception-path coverage
# ---------------------------------------------------------------------------

def test_write_media_store_copy_handles_kivy_utils_import_error(monkeypatch, tmp_path):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "kivy.utils":
            raise ImportError("kivy utils unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    result = mod._write_media_store_copy(
        str(tmp_path / "test.pdf"),
        "application/pdf",
    )

    assert result is None


def test_share_exported_file_handles_kivy_utils_import_error(monkeypatch, tmp_path):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "kivy.utils":
            raise ImportError("kivy utils unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    result = mod.share_exported_file(
        str(tmp_path / "test.pdf"),
        "application/pdf",
    )

    assert result is False


def test_open_exported_file_handles_kivy_utils_import_error(monkeypatch, tmp_path):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "kivy.utils":
            raise ImportError("kivy utils unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    result = mod.open_exported_file(
        str(tmp_path / "test.pdf"),
        "application/pdf",
    )

    assert result is False


def test_generic_excel_generates_filename_when_filename_is_none(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    path = mod._generic_excel(
        ["Date", "Value"],
        [
            (
                "2026-09-23",
                [["2026-09-23", "100"]],
            )
        ],
        "Test Report",
        "test_report",
        [15, 20],
        filename=None,
    )

    assert Path(path).exists()
    assert Path(path).name.startswith("test_report_")
    assert Path(path).suffix == ".xlsx"


def test_generic_pdf_generates_filename_when_filename_is_none(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    path = mod._generic_pdf(
        ["Date", "Value"],
        [
            (
                "2026-09-23",
                [["2026-09-23", "100"]],
            )
        ],
        "Test Report",
        "test_report",
        filename=None,
    )

    assert Path(path).exists()
    assert Path(path).name.startswith("test_report_")
    assert Path(path).suffix == ".pdf"


def test_build_combined_sections_skips_medication_with_empty_name():
    selected_rows = {
        "medications": [
            {
                "log_date": "2026-09-23",
                "name": "",
                "dosage": "1",
                "scheduled_time": "09:00",
                "taken": "1",
            },
            {
                "log_date": "2026-09-23",
                "name": "Iron",
                "dosage": "1",
                "scheduled_time": "10:00",
                "taken": "1",
            },
        ]
    }

    headers, sections = mod.build_combined_sections(
        selected_rows,
        [("2026-09-23", "2026-09-23")],
    )

    row = sections[0][1][0]

    assert "Iron (1) @ 10:00 — Taken" in row
    assert not any("09:00" in str(value) for value in row)

def test_export_blood_sugar_to_pdf_generates_filename_when_none(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    rows = [
        {
            "id": 1,
            "log_date": "2026-09-23",
            "reading_time": "08:00",
            "slot": "Fasting",
            "value": 95,
            "fasting": 1,
        }
    ]

    path = mod.export_sugar_to_pdf(
        rows,
        ranges=[("2026-09-23", "2026-09-23")],
        filename=None,
    )

    assert Path(path).exists()
    assert Path(path).name.startswith("sugar_log_")
    assert Path(path).suffix == ".pdf"

def test_blood_sugar_pdf_logo_failure_uses_text_fallback(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    monkeypatch.setattr(mod.os.path, "isfile", lambda path: True)

    class BrokenImage:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("logo failed")

    monkeypatch.setattr("reportlab.platypus.Image", BrokenImage)

    rows = [
        {
            "id": 1,
            "log_date": "2026-09-23",
            "reading_time": "08:00",
            "slot": "Fasting",
            "value": 95,
            "fasting": 1,
        }
    ]

    path = mod.export_sugar_to_pdf(
        rows,
        ranges=[("2026-09-23", "2026-09-23")],
        filename="logo_failure.pdf",
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

def test_blood_sugar_pdf_logo_failure_uses_text_fallback(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    monkeypatch.setattr(mod.os.path, "isfile", lambda path: True)

    class BrokenImage:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("logo failed")

    monkeypatch.setattr("reportlab.platypus.Image", BrokenImage)

    rows = [
        {
            "id": 1,
            "log_date": "2026-09-23",
            "reading_time": "08:00",
            "slot": "Fasting",
            "value": 95,
            "fasting": 1,
        }
    ]

    path = mod.export_sugar_to_pdf(
        rows,
        ranges=[("2026-09-23", "2026-09-23")],
        filename="logo_failure.pdf",
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

def test_blood_sugar_pdf_fmt_num_none_branch(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    rows = [
        {
            "id": 1,
            "log_date": "2026-09-23",
            "reading_time": "08:00",
            "slot": "Fasting",
            "value": "invalid",
            "fasting": 1,
        }
    ]

    path = mod.export_sugar_to_pdf(
        rows,
        ranges=[("2026-09-23", "2026-09-23")],
        filename="none_numeric.pdf",
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

def test_export_selected_reports_invalid_date_range():
    selection = {
        "category": "sugar",
        "start": "not-a-date",
        "end": "2026-09-23",
    }

    with pytest.raises(
        ValueError,
        match="No blood sugar readings found for the selected date range",
    ):
        mod.export_selected_reports_to_pdf([selection])

def test_export_sugar_report_pdf_generates_filename_when_none(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    rows = [
        {
            "log_date": "2026-09-23",
            "slot": "Fasting",
            "value": 95,
            "reading_time": "08:00",
            "fasting": 1,
        }
    ]

    path = mod._export_sugar_report_pdf(
        rows,
        "2026-09-23",
        "2026-09-23",
        filename=None,
    )

    assert Path(path).exists()
    assert Path(path).name.startswith("blood_sugar_log_")
    assert Path(path).suffix == ".pdf"

def test_export_sugar_report_pdf_generates_filename_when_none(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    rows = [
        {
            "log_date": "2026-09-23",
            "slot": "Fasting",
            "value": 95,
            "reading_time": "08:00",
            "fasting": 1,
        }
    ]

    path = mod._export_sugar_report_pdf(
        rows,
        "2026-09-23",
        "2026-09-23",
        filename=None,
    )

    assert Path(path).exists()
    assert Path(path).name.startswith("blood_sugar_log_")
    assert Path(path).suffix == ".pdf"

def test_export_sugar_report_pdf_none_value_uses_dash(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    rows = [
        {
            "log_date": "2026-09-23",
            "slot": "Fasting",
            "value": None,
            "reading_time": "08:00",
            "fasting": 1,
        }
    ]

    path = mod._export_sugar_report_pdf(
        rows,
        "2026-09-23",
        "2026-09-23",
        filename="none_value.pdf",
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

def test_export_selected_reports_invalid_date_range():
    selections = [
        {
            "category": "vitals",
            "label": "Vitals",
            "start": "not-a-date",
            "end": "2026-09-23",
        }
    ]

    with pytest.raises(ValueError, match="Invalid report date range"):
        mod.export_selected_reports_to_pdf(selections)

def test_export_selected_reports_invalid_date_range():
    selections = [
        {
            "category": "vitals",
            "label": "Vitals",
            "start": "not-a-date",
            "end": "2026-09-23",
        }
    ]

    with pytest.raises(ValueError, match="Invalid report date range"):
        mod.export_selected_reports_to_pdf(selections)

def test_export_sugar_report_pdf_logo_failure_uses_text_fallback(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    monkeypatch.setattr(mod.os.path, "isfile", lambda path: True)

    rows = [
        {
            "log_date": "2026-09-23",
            "slot": "Fasting",
            "value": 95,
            "reading_time": "08:00",
            "fasting": 1,
        }
    ]

    original_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        result = original_import(name, globals, locals, fromlist, level)

        if name == "reportlab.platypus" and "Image" in fromlist:
            original_image = result.Image
            call_count = {"value": 0}

            class SelectiveBrokenImage:
                def __new__(cls, *args, **kwargs):
                    call_count["value"] += 1

                    # The first Image() call is the header/logo image.
                    if call_count["value"] == 1:
                        raise RuntimeError("forced logo failure")

                    # Allow subsequent Image() calls to work normally.
                    return original_image(*args, **kwargs)

            class PatchedPlatypus:
                pass

            for attr in dir(result):
                try:
                    setattr(PatchedPlatypus, attr, getattr(result, attr))
                except Exception:
                    pass

            PatchedPlatypus.Image = SelectiveBrokenImage
            return PatchedPlatypus

        return result

    monkeypatch.setattr("builtins.__import__", fake_import)

    path = mod._export_sugar_report_pdf(
        rows,
        "2026-09-23",
        "2026-09-23",
        filename="logo_failure.pdf",
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

def test_export_selected_reports_generates_filename_when_none(
    monkeypatch, isolated_database, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    selections = [
        {
            "category": "vitals",
            "label": "Vitals",
            "start": "2026-09-23",
            "end": "2026-09-23",
        }
    ]

    path = mod.export_selected_reports_to_pdf(
        selections,
        filename=None,
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0
    assert Path(path).name.startswith("babybloom_report_")
    assert Path(path).suffix == ".pdf"


def test_export_sugar_report_pdf_missing_logo_uses_text_fallback(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    monkeypatch.setattr(mod.os.path, "isfile", lambda path: False)

    rows = [
        {
            "log_date": "2026-09-23",
            "slot": "Fasting",
            "value": 95,
            "reading_time": "08:00",
            "fasting": 1,
        }
    ]

    path = mod._export_sugar_report_pdf(
        rows,
        "2026-09-23",
        "2026-09-23",
        filename="missing_logo.pdf",
    )

    assert Path(path).exists()
    assert Path(path).stat().st_size > 0

def test_export_utils_handles_missing_kivy_app_import(monkeypatch):
    import builtins
    import importlib
    import sys

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "kivy.app":
            raise ImportError("forced missing kivy.app")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    module_name = "utils.export_utils"

    original_module = sys.modules.pop(module_name, None)

    try:
        reloaded = importlib.import_module(module_name)

        assert reloaded.App is None

    finally:
        sys.modules.pop(module_name, None)

        if original_module is not None:
            sys.modules[module_name] = original_module
        else:
            importlib.import_module(module_name)


def test_write_media_store_copy_android_close_failure_is_caught(
    monkeypatch, tmp_path
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    class CloseFailStream(FakeOutputStream):
        def close(self):
            raise RuntimeError("close failed")

    stream = CloseFailStream()
    resolver = FakeResolver(output_stream=stream)
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source), "application/pdf"
    ) is None


def test_generic_excel_missing_logo_branch(monkeypatch, tmp_path):
    monkeypatch.setattr(mod.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))

    rows = [{"event_date": "2026-09-23", "title": "Scan"}]
    path = mod._generic_excel(
        ["Date", "Events"],
        [("2026-09-23", [["2026-09-23", "Scan"]])],
        "Events",
        "events",
        [15, 20],
        "events.xlsx",
    )

    assert Path(path).is_file()


def test_pdf_branding_without_subtitle_branch(running_mdapp, monkeypatch):
    from reportlab.lib.styles import getSampleStyleSheet

    elements = []
    monkeypatch.setattr(mod.os.path, "isfile", lambda path: False)

    mod._pdf_branding(elements, getSampleStyleSheet(), None)

    assert len(elements) == 2


def test_write_media_store_copy_android_open_stream_exception_leaves_stream_none(
    monkeypatch, tmp_path
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    class OpenStreamFailResolver(FakeResolver):
        def openOutputStream(self, uri):
            raise RuntimeError("open stream failed")

    resolver = OpenStreamFailResolver()
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None

    assert resolver.deleted == [
        ("content://babybloom/1", None, None)
    ]


def test_write_media_store_copy_android_close_exception(
    monkeypatch, tmp_path
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    class CloseFailOutputStream(FakeOutputStream):
        def close(self):
            self.closed = True
            raise RuntimeError("close failed")

    stream = CloseFailOutputStream()
    resolver = FakeResolver(output_stream=stream)
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None

    assert stream.closed is True


def test_write_media_store_copy_android_null_output_stream(
    monkeypatch, tmp_path
):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")

    class NullOutputStreamResolver(FakeResolver):
        def openOutputStream(self, uri):
            return None

    resolver = NullOutputStreamResolver()
    install_fake_android(monkeypatch, resolver)

    assert mod._write_media_store_copy(
        str(source),
        "application/pdf",
    ) is None

    assert resolver.deleted == [
        ("content://babybloom/1", None, None)
    ]
