import sqlite3
from datetime import datetime
from pathlib import Path
import flet as ft
import flet_charts as fch
import logging
from content.HelperStuff.nav_util import TopNav
from dateutil.relativedelta import relativedelta
from content.StatisticsStuff.chart_dta import ChartManager


logger = logging.getLogger(__name__)


class AllServerStatics(ft.Column):
    def __init__(self, page: ft.Page, content_manager):
        """Initializes libraries UI; starts asynchronous credential loading"""
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            # alignment = ft.MainAxisAlignment.CENTER

        )
        self.current_page = page
        self.content_manager = content_manager
        #self.env_file_path = Path(__file__).parent.parent / ".env"
        self.path_to_DB = Path(__file__).parent.parent / ".auth"
        self.path_to_DB_file = self.path_to_DB / "libraries_metadata.db"

        self.list_container = ft.Column()
        self.progress_bar_container = ft.Container(
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                content=ft.Row([
                    ft.ProgressRing(color=ft.Colors.ON_PRIMARY_CONTAINER),
                    ft.Text("Loading statics\nplease wait ...",color=ft.Colors.ON_PRIMARY_CONTAINER)]),
                padding=20,
                alignment=ft.Alignment.TOP_CENTER
            )
        self.controls.append(self.progress_bar_container)

        # Start initialization

        self.current_page.run_task(self.async_init)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress_bar_container.visible = True
        self.update()
        self.current_page.update()



    # ------------------------------
    # Init the Main Page
    # ------------------------------
    async def async_init(self):
        await self._create_app_bar()
        await self._fetch_data()
        static_row = await self._build_static_tiles()
        self.progress_bar_container.visible = False
        chart_container = await self._build_statistics()
        self.controls.append(static_row)
        self.controls.append(chart_container)
        self.current_page.update()

    async def _create_app_bar(self):
        """
            Creating the App Bar
        """
        await TopNav.top_nav(self.current_page, "Server Statics")
        self.current_page.update()

    async def _fetch_data(self) -> dict:
        """Return library and user statistics."""
        # Note: These dates are defined but weren't used in your original SQL query.
        # I've left them here in case you intended to add a WHERE clause.
        end = datetime.today().replace(day=1)
        start = end - relativedelta(months=11)

        try:
            with sqlite3.connect(self.path_to_DB_file) as con:
                cur = con.cursor()

                # 1. Get the single oldest library name and its creation date
                cur.execute(
                    """
                    SELECT OBJNAME, strftime('%Y-%m-%d', OBJCREATED)
                    FROM LIBRARY_METADATA
                    ORDER BY OBJCREATED ASC
                    LIMIT 1
                    """
                )
                oldest_row = cur.fetchone()
                oldest_lib_name = oldest_row[0] if oldest_row else "None"
                oldest_lib_date = oldest_row[1] if oldest_row else "0"

                # 2. Get the counts grouped by date (for months and highest_month)
                cur.execute(
                    """
                    SELECT strftime('%Y-%m-%d', OBJCREATED) as day, COUNT(OBJNAME)
                    FROM LIBRARY_METADATA
                    GROUP BY day
                    """
                )
                data = cur.fetchall()

                # 3. Get total counts
                cur.execute("SELECT COUNT(OBJNAME) FROM LIBRARY_METADATA")
                total_libraries = cur.fetchone()[0]

                cur.execute("SELECT COUNT(AUTHORIZATION_NAME) FROM USER_METADATA")
                user_count = cur.fetchone()[0]

            library_counts = {item[0]: item[1] for item in data}

            if not library_counts:
                return {
                    'oldest_library': "None",
                    'months': 0,
                    'user_data': user_count,
                    'libraries': 0,
                    'highest_month': 0,
                }

            stats = {
                # Combine the name and the date from our first query
                'oldest_library': oldest_lib_name,
                'months': len(library_counts),
                'user_data': user_count,
                'libraries': total_libraries,
                'highest_month': max(library_counts.values()),
            }
            return stats

        except Exception as exc:
            print(f"[DB] {exc}")
            return {}

        except Exception as exc:
            print(f"[DB] {exc}")
            return {}

    async def _build_static_tiles(self) -> ft.Row:
        stats = await self._fetch_data()
        PADDING_HIGHT = 25
        return ft.Row(
                    expand = True,
                    controls=[
                        ft.Card(
                            shadow_color=ft.Colors.PRIMARY_CONTAINER,
                            expand=True,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            elevation = 8,
                            content=ft.Container(
                                    padding=PADDING_HIGHT,
                                    expand = True,
                                    alignment=ft.Alignment.CENTER,
                                    content = ft.Row(
                                        [
                                            ft.ListTile(
                                                title=ft.Text("Users on System ", weight=ft.FontWeight.BOLD),
                                                subtitle=str(stats.get('user_data')),
                                                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                            )
                                        ]
                                    )
                                )
                        ),
                        ft.Card(
                            shadow_color=ft.Colors.PRIMARY_CONTAINER,
                            expand=True,
                            elevation=8,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            content=ft.Container(
                                padding=PADDING_HIGHT,
                                expand=True,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Row(
                                        [
                                            ft.ListTile(
                                                title=ft.Text("Libraries on System  ", weight=ft.FontWeight.BOLD),
                                                subtitle=str(stats.get('libraries')),
                                                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                            )
                                        ]
                                    )
                            )
                        ),
                        ft.Card(
                            shadow_color=ft.Colors.PRIMARY_CONTAINER,
                            expand=True,
                            elevation=8,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            content=ft.Container(
                                padding=PADDING_HIGHT,
                                expand=True,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Row(
                                    [
                                        ft.ListTile(
                                            title=ft.Text("Oldest library on System  ", weight=ft.FontWeight.BOLD),
                                            subtitle=str(stats.get('oldest_library')),
                                            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                        )
                                    ]
                                )
                            )
                        )

            ]
        )

    async def _build_statistics(self) -> ft.Container:

        manager = ChartManager()
        manager.get_library_data()
        manager.get_user_data()
        if not manager.lib_months or not manager.lib_counts:
            return ft.Container()


        line_points_lib = [
            fch.LineChartDataPoint(i + 1, val)
            for i, val in enumerate(manager.lib_counts)
        ]

        x_axis_labels = [
            fch.ChartAxisLabel(
                value=i + 1,
                label=ft.Text(m, size=11, opacity=0.6)
            ) for i, m in enumerate(manager.lib_months)
        ]

        main_series_lib = fch.LineChartData(
            points=line_points_lib,
            stroke_width=4,
            color=ft.Colors.PRIMARY,
            below_line_bgcolor=ft.Colors.with_opacity(
                0.2, ft.Colors.PRIMARY_CONTAINER
            ),
            curved=True,
            point=True,
        )

        chart = fch.LineChart(
            expand=True,
            data_series=[main_series_lib],
            max_y=max(manager.lib_counts) + 5,
            min_y=0,
            max_x=len(manager.lib_months),
            # min_x = 0,
            bottom_axis=fch.ChartAxis(labels=x_axis_labels, label_size=40),
            left_axis=fch.ChartAxis(label_size=40),
            horizontal_grid_lines=fch.ChartGridLines(color=ft.Colors.with_opacity(0.1, "white")),
        )

        return ft.Container(
            content=chart,
            height=400,
            padding=50,
            bgcolor=ft.Colors.BLACK12,
            border_radius=20,
            border=ft.Border.all(1, ft.Colors.WHITE10)
        )