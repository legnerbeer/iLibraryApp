import flet as ft


def main(page: ft.Page):
    page.title = "Standalone Badge Example"

    # --- Custom Badge/Label Implementation ---
    standalone_badge = ft.Container(
        content=ft.Text(
            value="New",
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD
        ),
        bgcolor=ft.Colors.BLUE_600,  # Badge background color
        padding=ft.padding.only(left=8, right=8, top=4, bottom=4),  # Padding around the text
        border_radius=ft.border_radius.all(10),  # Rounded corners for a pill/badge shape
    )

    # --- Example with a different style ---
    notification_count = ft.Container(
        content=ft.Text(
            value="99+",
            color=ft.Colors.WHITE,
            size=10,  # Smaller text size
        ),
        width=30,  # Fixed width for a circle shape (if width/height are the same)
        height=30,
        alignment=ft.alignment.center,
        bgcolor=ft.Colors.RED_500,
        border_radius=ft.border_radius.all(15),  # Half of height/width for a perfect circle
    )

    page.add(
        ft.Text("Standalone Label using Container:", size=20),
        standalone_badge,
        ft.Divider(),
        ft.Text("Notification Count Badge:", size=20),
        notification_count
    )


ft.app(target=main)