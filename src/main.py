import flet as ft
# Assuming content.all_libraries is available
from content.all_libraries import AllLibraries


async def main(page: ft.Page):
    page.theme = ft.Theme(
        use_material3=True,
        color_scheme_seed="#00ffe5"

    )

    # ---------------------------------------------------
    # Container for dynamically changing content
    # ---------------------------------------------------
    # This control will hold the current view (e.g., AllLibraries, Settings)
    page_content = ft.Container(content=ft.Text("Initializing..."))

    # ---------------------------------------------------
    # Helper: replace content instantly
    # ---------------------------------------------------
    async def clear_and_add_control(control):
        # Instead of clearing all controls on the page, we update the content
        # of the dedicated page_content container.
        page_content.content = control
        page_content.update()  # Use update_async for controls

    # Attaching the helper to page is fine, but we'll use it directly in handlers.
    # page.clear_and_add_control = clear_and_add_control # Removed: using it directly is cleaner
    # ---------------------------------------------------
    # Navigation Bar Handler
    # ---------------------------------------------------
    async def navigation_bar_changed(e):
        idx = e.control.selected_index

        if idx == 0:  # ALL LISTS
            # Load the AllLibraries content
            await clear_and_add_control(AllLibraries(
                page,
                content_manager=clear_and_add_control))
            page.title = "All Libraries"  # Update page title

        elif idx == 1:  # CATEGORIES
            await clear_and_add_control(
                ft.Container(
                    content=ft.Text("This Content (CATEGORIES) is in Development"),
                    alignment=ft.alignment.center
                )
            )
            page.title = "Categories"  # Update page title
            # page.open(ft.SnackBar(ft.Text("This Content is in Development"), show_close_icon=True))

        elif idx == 2:  # SETTINGS
            await clear_and_add_control(
                ft.Container(
                    content=ft.Text("This Content (SETTINGS) is in Development"),
                    alignment=ft.alignment.center
                )
            )
            page.title = "Settings"  # Update page title
            # page.open(ft.SnackBar(ft.Text("This Content is in Development"), show_close_icon=True))

        # Ensure the entire page updates if necessary (e.g., if title changed)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.LIBRARY_BOOKS_OUTLINED,
                selected_icon=ft.Icons.LIBRARY_BOOKS,
                label="All Libraries",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.BOOKMARK_BORDER),
                selected_icon=ft.Icon(ft.Icons.BOOKMARK),
                label="Categories",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icon(ft.Icons.SETTINGS),
                label_content=ft.Text("Settings"),
            ),
        ],
        on_change=navigation_bar_changed,
    )

    # ---------------------------------------------------
    # Initial Page Layout
    # ---------------------------------------------------
    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                # Add the content container to the Row, expanding it to fill space
                ft.Column([page_content], expand=True, alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.ADAPTIVE)
            ],
            expand=True,
        )
    )

    # ---------------------------------------------------
    # Load default content (Index 0) on startup
    # ---------------------------------------------------
    # Call the handler with an event object reflecting the default index (0)
    import types
    await navigation_bar_changed(types.SimpleNamespace(control=rail))


ft.app(main)