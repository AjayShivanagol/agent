import mesop as me


def mb_footer():
    """Minimal Mercedes-Benz footer matching the provided structure."""

    # AppBar-like footer container
    with me.box(
        style=me.Style(
            background="#000000",
            color="#FFFFFF",
            padding=me.Padding(top=16, bottom=16, left=24, right=24),
            margin=me.Margin(top="auto"),
            position="relative",
            box_shadow="0 -2px 4px rgba(0,0,0,0.2)",
        )
    ):
        # Centered max-width container
        with me.box(
            style=me.Style(
                max_width="1200px",
                margin=me.Margin.symmetric(horizontal="auto"),
                width="100%",
            )
        ):
            # Optional brand stack (hidden, as per provided markup)
            with me.box(style=me.Style(display="none")):
                with me.box(
                    style=me.Style(display="flex", align_items="center", gap="12px")
                ):
                    # Placeholder for brand icon and label
                    me.text(" ")

            # Bottom row: copyright (left) and links (right)
            with me.box(
                style=me.Style(
                    display="flex",
                    justify_content="space-between",
                    align_items="center",
                    flex_wrap="wrap",
                    gap="16px",
                    border=me.Border(top=me.BorderSide(color="transparent", width=0)),
                )
            ):
                # Left: copyright
                with me.box():
                    me.text(
                        f"© 2025 Mercedes-Benz Group AG. All rights reserved.",
                        style=me.Style(
                            font_family='"Roboto", "Helvetica", "Arial", sans-serif',
                            font_size="14px",
                            color="rgba(255,255,255,0.85)",
                        ),
                    )

                # Right: links
                with me.box():
                    with me.box(
                        style=me.Style(
                            display="flex",
                            gap="24px",
                            align_items="center",
                            flex_wrap="wrap",
                        )
                    ):
                        me.link(
                            text="Privacy Statement",
                            url="",
                            style=me.Style(
                                color="rgba(255,255,255,0.85)",
                                text_decoration="none",
                                font_family='"Roboto", "Helvetica", "Arial", sans-serif',
                                font_size="14px",
                            ),
                        )
                        me.link(
                            text="Legal Notice",
                            url="",
                            style=me.Style(
                                color="rgba(255,255,255,0.85)",
                                text_decoration="none",
                                font_family='"Roboto", "Helvetica", "Arial", sans-serif',
                                font_size="14px",
                            ),
                        )
                        me.link(
                            text="Provider",
                            url="",
                            style=me.Style(
                                color="rgba(255,255,255,0.85)",
                                text_decoration="none",
                                font_family='"Roboto", "Helvetica", "Arial", sans-serif',
                                font_size="14px",
                            ),
                        )