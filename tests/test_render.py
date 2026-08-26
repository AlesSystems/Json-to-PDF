from datetime import date
from html import unescape

from json_to_pdf.model import JsonNumber
from json_to_pdf.render import RenderContext, humanize_key, render_html


CTX = RenderContext("Exam Results", "results.json", date(2026, 8, 26))


def test_humanizes_labels_without_changing_values() -> None:
    assert humanize_key("correctAnswer") == "Correct Answer"
    html = render_html({"correctAnswer": "HTTPStatus2"}, CTX)
    assert "Correct Answer" in html
    assert "HTTPStatus2" in html


def test_selects_table_only_for_narrow_short_rows() -> None:
    table = render_html([{"subject": "A", "total": JsonNumber("2")}], CTX)
    cards = render_html(
        [{"a": "x", "b": "y", "c": "z", "d": "q", "e": "too wide"}], CTX
    )
    assert '<table class="records">' in table
    assert 'class="record-card"' in cards


def test_escapes_all_untrusted_text() -> None:
    html = render_html({"<img src=x>": "<script>https://example.test</script>"}, CTX)
    assert "<script>" not in html and "<img src=x>" not in html
    assert "&lt;script&gt;https://example.test&lt;/script&gt;" in html


def test_renders_scalar_object_fields_as_definition_rows_in_source_order() -> None:
    html = render_html(
        {"first_name": "Ada", "exam-score": JsonNumber("9.50e+1")}, CTX
    )
    assert '<table class="definition">' in html
    assert html.index("First name") < html.index("Ada") < html.index("Exam score")
    assert "9.50e+1" in html


def test_interleaves_nested_and_scalar_fields_in_source_order() -> None:
    html = render_html(
        {"details": {"name": "Ece"}, "score": JsonNumber("10")}, CTX
    )
    assert html.index("Details") < html.index("Ece") < html.index("Score")
    assert html.index("Score") < html.index("<td>10</td>")


def test_four_columns_are_a_table_and_five_columns_are_cards() -> None:
    four = render_html([{"a": "1", "b": "2", "c": "3", "d": "4"}], CTX)
    five = render_html(
        [{"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}], CTX
    )
    assert '<table class="records"><thead>' in four
    assert '<div class="record-card">' in five


def test_table_cell_length_boundary_is_60_characters() -> None:
    sixty = render_html([{"answer": "x" * 60}], CTX)
    sixty_one = render_html([{"answer": "x" * 61}], CTX)
    assert '<table class="records">' in sixty
    assert 'class="record-card"' in sixty_one


def test_table_total_width_boundary_is_120_characters() -> None:
    at_limit = render_html(
        [{"a": "a" * 30, "b": "b" * 30, "c": "c" * 30, "d": "d" * 30}],
        CTX,
    )
    over_limit = render_html(
        [{"a": "a" * 31, "b": "b" * 30, "c": "c" * 30, "d": "d" * 30}],
        CTX,
    )
    assert '<table class="records">' in at_limit
    assert 'class="record-card"' in over_limit


def test_different_fields_and_nested_values_use_record_cards() -> None:
    different = render_html([{"a": "1"}, {"b": "2"}], CTX)
    nested = render_html([{"a": {"nested": "value"}}], CTX)
    assert different.count('class="record-card"') == 2
    assert 'class="record-card"' in nested
    assert "Nested" in nested and "value" in nested


def test_primitive_arrays_are_ordered_lists_with_literal_scalar_spelling() -> None:
    html = render_html(
        [None, True, False, JsonNumber("-0.50e+2"), "son"], CTX
    )
    assert (
        "<ol><li>null</li><li>true</li><li>false</li>"
        "<li>-0.50e+2</li><li>son</li></ol>"
    ) in html


def test_nested_values_are_titled_and_mixed_arrays_are_numbered() -> None:
    nested = render_html({"student_details": {"name": "Ece"}}, CTX)
    mixed = render_html(["start", {"result": "done"}, [JsonNumber("3")]], CTX)
    assert "<h2>Student details</h2>" in nested
    assert "<h2>Item 1</h2>" in mixed
    assert "<h2>Item 2</h2>" in mixed
    assert "<h2>Item 3</h2>" in mixed


def test_long_turkish_text_is_preserved_as_literal_content() -> None:
    text = "İstanbul'da ölçme değerlendirme çalışması: ğüşöçı " * 8
    html = render_html({"açıklama": text}, CTX)
    assert text in unescape(html)


def test_every_untrusted_context_and_data_field_is_inert() -> None:
    context = RenderContext(
        'Title "<& <a href="https://evil.test">',
        'file:///tmp/x"><img src="https://evil.test/x">',
        CTX.generated_on,
    )
    html = render_html(
        {
            '<a href="file:///etc/passwd">': "https://example.test/?a=1&b=2",
            "quoted": '"<&',
            "image": '<img src="file:///secret">',
            "script": "<script>alert(1)</script>",
        },
        context,
    )
    lowered = html.lower()
    assert "<a " not in lowered
    assert "<img" not in lowered
    assert "<script" not in lowered
    assert "<link" not in lowered
    assert "@import" not in lowered
    assert "file:///" in html and "https://example.test/" in html
    assert "&quot;" in html and "&lt;" in html and "&amp;" in html


def test_document_has_one_title_and_uses_the_bundled_font() -> None:
    html = render_html({"result": "ok"}, CTX)
    assert html.count("<h1>") == 1
    assert "font-family: 'Noto Sans'" in html
