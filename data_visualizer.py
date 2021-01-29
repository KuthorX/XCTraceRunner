from snapshot_selenium import snapshot as driver
from pyecharts.charts import Line, Page
from pyecharts import options as opts
from pyecharts.render import make_snapshot
from pyecharts.globals import ThemeType
from collections import namedtuple

ParsedData = namedtuple("ParsedData", ["title", "y_label", "y_seq", "x_seq"])


def main():
    d = ParsedData(
        title="test",
        y_label="labelA",
        y_seq=[i for i in range(100)],
        x_seq=[f"{i}:{i}" for i in range(100)],
    )
    dv = DataVisualizer()
    dv.add_parsed_data(d)
    dv.render_html()


class DataVisualizer:
    def __init__(
        self,
        html_path="data_visualizer.html",
        snapshot_path="data_visualizer.png",
    ):
        self._chart = Page(
            layout=Page.SimplePageLayout,
        )
        self.html_path = html_path
        self.snapshot_path = snapshot_path

    def render_html(self):
        self._chart.render(self.html_path)

    def make_snapshot(self):
        try:
            result = make_snapshot(driver, r, self.snapshot_path)
        except Exception as e:
            print(f"make_snapshot Exception {e}")
            return False
        return result

    def add_parsed_data(
        self,
        parsed_data: ParsedData,
        width="900px",
        height="500px",
        page_title=None,
    ):
        new_chart = (
            Line(
                init_opts=opts.InitOpts(
                    theme=ThemeType.LIGHT,
                    page_title=page_title,
                    width=width,
                    height=height,
                )
            )
            .add_xaxis(parsed_data.x_seq)
            .add_yaxis(
                parsed_data.y_label,
                parsed_data.y_seq,
                is_smooth=False,
                label_opts=opts.LabelOpts(is_show=False),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=parsed_data.title),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                toolbox_opts=opts.ToolboxOpts(
                    is_show=True,
                    orient="horizontal",
                    feature=opts.ToolBoxFeatureOpts(brush=None, data_zoom=None),
                ),
                datazoom_opts=opts.DataZoomOpts(range_start=0, range_end=100),
            )
        )
        self._chart.add(new_chart)


if __name__ == "__main__":
    main()
