def test_basic_plot():
    from glyphx import plot

    fig = plot(x=[1, 2, 3], y=[4, 5, 6], kind="line")
    svg = fig.render_svg()

    assert "<svg" in svg
    assert "polyline" in svg
