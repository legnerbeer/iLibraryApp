import flet as ft

class TopNav:
    @staticmethod
    async def top_nav(page:ft.Page, title:str):
        page.appbar = ft.AppBar(
            title=ft.Column(
                controls=[
                    ft.Text(title),

                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND),
            actions=[
                # Reference the instance variable here
                ft.Text(f"Server: {await ft.SharedPreferences().get('server')}"),
                ft.Container(width=60),
            ]
        )
