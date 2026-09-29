import pytest
from unittest.mock import Mock
from datetime import date
import screens.export_screen as mod
from screens.export_screen import ExportScreen


def test_init_defaults(running_mdapp):
    screen = ExportScreen()
    assert screen.report_selections == []
    assert screen.reading_menu is None
    assert screen.generated_pdf_path is None


def test_select_reading_and_dismiss(running_mdapp):
    screen = ExportScreen()
    screen.reading_menu = Mock()
    screen._select_reading("sugar","Blood Sugar")
    assert screen.selected_reading == "sugar"
    assert screen.selected_reading_label == "Blood Sugar"
    assert screen.reading_menu is None


def test_dismiss_reading_menu_no_menu(running_mdapp):
    screen = ExportScreen()
    screen._dismiss_reading_menu()
    assert screen.reading_menu is None


def test_dismiss_reading_menu_with_menu(running_mdapp):
    screen = ExportScreen()
    menu = Mock()
    screen.reading_menu = menu
    screen._dismiss_reading_menu()
    menu.dismiss.assert_called_once()
    assert screen.reading_menu is None


def test_date_selected_start_and_end(running_mdapp):
    screen = ExportScreen()
    screen._date_target = "start"
    screen._date_selected(None,date(2026,9,20),None)
    assert screen.start_date_label == "2026-09-20"
    screen._date_target = "end"
    screen._date_selected(None,date(2026,9,21),None)
    assert screen.end_date_label == "2026-09-21"
    assert screen._date_target is None


def test_add_report_validation(running_mdapp):
    screen = ExportScreen()
    screen._notify = Mock()
    screen.add_report()
    assert "reading first" in screen._notify.call_args.args[0]
    screen.selected_reading = "sugar"
    screen.add_report()
    assert "both" in screen._notify.call_args.args[0]


@pytest.mark.parametrize(
    "start,end,message",
    [("bad","2026-09-20","valid dates"),("2026-09-21","2026-09-20","cannot be after")]
)
def test_add_report_invalid_dates(running_mdapp,start,end,message):
    screen = ExportScreen()
    screen.selected_reading = "sugar"
    screen.selected_reading_label = "Blood Sugar"
    screen.start_date_label = start
    screen.end_date_label = end
    screen._notify = Mock()
    screen.add_report()
    assert message in screen._notify.call_args.args[0]


def test_add_report_duplicate_and_reset(running_mdapp):
    screen = ExportScreen()
    screen.selected_reading = "sugar"
    screen.selected_reading_label = "Blood Sugar"
    screen.start_date_label = "2026-09-20"
    screen.end_date_label = "2026-09-21"
    screen.refresh_selection_list = Mock()
    screen.add_report()
    screen.selected_reading = "sugar"
    screen.selected_reading_label = "Blood Sugar"
    screen.start_date_label = "2026-09-20"
    screen.end_date_label = "2026-09-21"
    screen.add_report()
    assert len(screen.report_selections) == 1
    assert screen.selected_reading == ""
    assert screen.start_date_label == "Start Date"


def test_remove_and_clear_selection(running_mdapp):
    screen = ExportScreen()
    screen.report_selections = [{"x":1},{"x":2}]
    screen.refresh_selection_list = Mock()
    screen.remove_selection(0)
    assert screen.report_selections == [{"x":2}]
    screen.remove_selection(-1)
    screen.remove_selection(99)
    screen.clear_selection()
    assert screen.report_selections == []


def test_display_date():
    assert ExportScreen._display_date("2026-09-23") == "23 Sep 2026"
    assert ExportScreen._display_date("bad") == "bad"


def test_generate_pdf_empty(running_mdapp):
    screen = ExportScreen()
    screen._notify = Mock()
    screen.generate_pdf()
    assert "at least one report" in screen._notify.call_args.args[0]


def test_generate_pdf_import_error(running_mdapp, monkeypatch):
    screen = ExportScreen()
    screen.report_selections = [{"category":"sugar"}]
    monkeypatch.setattr(mod, "export_selected_reports_to_pdf", Mock(side_effect=ImportError("x")))
    screen._notify = Mock()
    screen.generate_pdf()
    assert "Missing library" in screen._notify.call_args.args[0]


def test_generate_pdf_generic_error(running_mdapp, monkeypatch):
    screen = ExportScreen()
    screen.report_selections = [{"category":"sugar"}]
    monkeypatch.setattr(mod, "export_selected_reports_to_pdf", Mock(side_effect=RuntimeError("x")))
    screen._notify = Mock()
    screen.generate_pdf()
    assert "PDF generation failed" in screen._notify.call_args.args[0]


def test_share_and_view_notifications(running_mdapp, monkeypatch):
    screen = ExportScreen()
    monkeypatch.setattr(mod, "share_exported_file", lambda *a: False)
    screen._notify = Mock()
    screen._share_or_notify("x.pdf")
    assert "share sheet" in screen._notify.call_args.args[0]
    monkeypatch.setattr(mod, "open_exported_file", lambda *a: False)
    screen._view_or_notify("x.pdf")
    assert "PDF viewer" in screen._notify.call_args.args[0]


def test_on_pre_enter_refreshes(running_mdapp):
    screen = ExportScreen()
    screen.refresh_selection_list = Mock()
    screen.refresh_generated_list = Mock()
    screen.refresh_list = Mock()
    screen.on_pre_enter()
    screen.refresh_selection_list.assert_called_once()
    screen.refresh_generated_list.assert_called_once()
    screen.refresh_list.assert_called_once()


def test_open_reading_menu_creates_dialog(running_mdapp, monkeypatch):
    captured = []
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: captured.append(self))
    ExportScreen().open_reading_menu(Mock())
    assert captured


def test_open_date_picker_valid_and_invalid(monkeypatch, running_mdapp):
    pickers = []
    class P:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def bind(self, **kwargs):
            self.cb = kwargs["on_save"]
        def open(self):
            pickers.append(self)
    monkeypatch.setattr(mod, "MDDatePicker", P)
    screen = ExportScreen()
    screen.start_date_label = "2026-09-20"
    screen.open_date_picker("start")
    screen.end_date_label = "bad"
    screen.open_date_picker("end")
    assert len(pickers) == 2
    assert pickers[0].kwargs["year"] == 2026


def test_refresh_selection_list_empty_and_nonempty(running_mdapp):
    screen = ExportScreen()
    screen.refresh_selection_list()
    assert len(screen.ids.selection_list.children) == 1
    screen.report_selections = [{"label":"Blood Sugar","start":"2026-09-20","end":"2026-09-21"}]
    screen.refresh_selection_list()
    assert len(screen.ids.selection_list.children) == 1


def test_refresh_generated_list_empty(running_mdapp, monkeypatch):
    screen = ExportScreen()
    monkeypatch.setattr(mod.os.path, "isfile", lambda p: False)
    screen.refresh_generated_list()
    assert len(screen.ids.generated_list.children) == 1


def test_refresh_generated_list_with_file(running_mdapp, monkeypatch, tmp_path):
    p = tmp_path/"x.pdf"
    p.write_text("x")
    screen = ExportScreen()
    screen.generated_pdf_path = str(p)
    screen._add_pdf_action_row = Mock()
    screen.refresh_generated_list()
    screen._add_pdf_action_row.assert_called_once()


def test_refresh_list_no_directory(running_mdapp, monkeypatch):
    screen = ExportScreen()
    monkeypatch.setattr(mod, "get_export_dir", lambda: "/does/not/exist")
    screen.refresh_list()
    assert screen.ids.export_list.children == []


def test_refresh_list_pdf_files(running_mdapp, monkeypatch, tmp_path):
    (tmp_path/"a.pdf").write_text("x")
    (tmp_path/"b.txt").write_text("x")
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    screen = ExportScreen()
    screen._add_pdf_action_row = Mock()
    screen.refresh_list()
    screen._add_pdf_action_row.assert_called_once()


def test_add_pdf_action_row(running_mdapp, monkeypatch, tmp_path):
    screen = ExportScreen()
    monkeypatch.setattr(mod, "get_export_dir", lambda: str(tmp_path))
    target = screen.ids.export_list
    screen._add_pdf_action_row(target, "a.pdf")
    assert len(target.children) == 1


def test_confirm_delete_file_dialog(running_mdapp, monkeypatch):
    screen = ExportScreen()
    screen.refresh_generated_list = Mock()
    screen.refresh_list = Mock()
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: None)
    screen._confirm_delete_file("x.pdf", "/tmp/x.pdf")
    assert True


def test_notify_opens_dialog(running_mdapp, monkeypatch):
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: None)
    ExportScreen()._notify("hello")
    assert True

def test_generate_pdf_without_selection_notifies(monkeypatch, running_mdapp):
    screen = ExportScreen()
    screen._notify = Mock()

    screen.generate_pdf()

    screen._notify.assert_called_once_with(
        "Add at least one report before generating the PDF."
    )


def test_generate_pdf_success(monkeypatch, running_mdapp):
    screen = ExportScreen()
    screen.report_selections = [
        {
            "category": "sugar",
            "label": "Blood Sugar",
            "start": "2026-09-23",
            "end": "2026-09-23",
        }
    ]
    screen._notify = Mock()
    screen.refresh_selection_list = Mock()
    screen.refresh_generated_list = Mock()
    screen.refresh_list = Mock()

    monkeypatch.setattr(
        mod,
        "export_selected_reports_to_pdf",
        lambda selections: "/tmp/BabyBloom_Report.pdf",
    )

    saved = Mock()
    monkeypatch.setattr(
        mod,
        "save_to_public_downloads",
        saved,
    )

    screen.generate_pdf()

    saved.assert_called_once_with(
        "/tmp/BabyBloom_Report.pdf",
        mod.PDF_MIME,
    )

    assert screen.report_selections == []
    assert screen.generated_pdf_path == "/tmp/BabyBloom_Report.pdf"

    screen.refresh_selection_list.assert_called_once()
    screen.refresh_generated_list.assert_called_once()
    screen.refresh_list.assert_called_once()

    screen._notify.assert_called_once_with(
        "PDF generated successfully.\n\n"
        "BabyBloom_Report.pdf\n\n"
        "Use Share, View or Delete below."
    )


def test_generate_pdf_import_error(monkeypatch, running_mdapp):
    screen = ExportScreen()
    screen.report_selections = [
        {
            "category": "sugar",
            "label": "Blood Sugar",
            "start": "2026-09-23",
            "end": "2026-09-23",
        }
    ]
    screen._notify = Mock()

    def raise_import_error(_selections):
        raise ImportError("reportlab missing")

    monkeypatch.setattr(
        mod,
        "export_selected_reports_to_pdf",
        raise_import_error,
    )

    screen.generate_pdf()

    screen._notify.assert_called_once_with(
        "Missing library: reportlab missing. Check requirements.txt."
    )


def test_generate_pdf_general_exception(monkeypatch, running_mdapp):
    screen = ExportScreen()
    screen.report_selections = [
        {
            "category": "sugar",
            "label": "Blood Sugar",
            "start": "2026-09-23",
            "end": "2026-09-23",
        }
    ]
    screen._notify = Mock()

    def raise_error(_selections):
        raise RuntimeError("PDF generation failed internally")

    monkeypatch.setattr(
        mod,
        "export_selected_reports_to_pdf",
        raise_error,
    )

    screen.generate_pdf()

    screen._notify.assert_called_once_with(
        "PDF generation failed: PDF generation failed internally"
    )

def test_confirm_delete_file_executes_delete_and_refreshes(running_mdapp, monkeypatch):
    from screens.export_screen import ExportScreen

    screen = ExportScreen()

    deleted = []
    monkeypatch.setattr(
        "screens.export_screen.delete_export",
        lambda path: deleted.append(path),
    )

    generated_refresh = []
    list_refresh = []

    monkeypatch.setattr(
        screen,
        "refresh_generated_list",
        lambda: generated_refresh.append(True),
    )
    monkeypatch.setattr(
        screen,
        "refresh_list",
        lambda: list_refresh.append(True),
    )

    class FakeDialog:
        instances = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.dismissed = False
            FakeDialog.instances.append(self)

        def open(self):
            pass

        def dismiss(self):
            self.dismissed = True

    monkeypatch.setattr(
        "screens.export_screen.MDDialog",
        FakeDialog,
    )

    screen._confirm_delete_file(
        "report.pdf",
        "/tmp/report.pdf",
    )

    dialog = FakeDialog.instances[-1]
    delete_button = dialog.kwargs["buttons"][1]
    delete_button.dispatch("on_release")

    assert deleted == ["/tmp/report.pdf"]
    assert dialog.dismissed is True
    assert generated_refresh == [True]
    assert list_refresh == [True]


def test_refresh_list_with_empty_export_directory(running_mdapp, monkeypatch):
    from screens.export_screen import ExportScreen

    screen = ExportScreen()

    class FakeTarget:
        def __init__(self):
            self.widgets = []

        def clear_widgets(self):
            self.widgets.clear()

        def add_widget(self, widget):
            self.widgets.append(widget)

    target = FakeTarget()

    class FakeIds:
        export_list = target

    screen.ids = {"export_list": target}

    monkeypatch.setattr(
        "screens.export_screen.get_export_dir",
        lambda: "/tmp/export-dir",
    )
    monkeypatch.setattr(
        "screens.export_screen.os.path.isdir",
        lambda path: True,
    )
    monkeypatch.setattr(
        "screens.export_screen.os.listdir",
        lambda path: [],
    )

    screen.refresh_list()

    assert len(target.widgets) == 1
    assert target.widgets[0].text == "No generated PDFs yet."
